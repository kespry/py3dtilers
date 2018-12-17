import sys
import argparse
import yaml
import numpy as np
import psycopg2
import psycopg2.extras
import pathlib
from py3dtiles import TriangleSoup, GlTF, B3dm, BatchTableHierarchy

import json
import itertools


def ParseCommandLine():
    # arg parse
    descr = '''TODO.'''
    parser = argparse.ArgumentParser(description=descr)
    cfg_help = 'Path to the database configuration file'
    parser.add_argument('db_config_path',
                        nargs='?', default='CityTilerDBConfig.yml',
                        type=str, help=cfg_help)
    args = parser.parse_args()

    db_config = None
    with open(args.db_config_path, 'r') as db_config_file:
        try:
            db_config = yaml.load(db_config_file)
            db_config_file.close()
        except:
            print('ERROR: ', sys.exec_info()[0])
            db_config_file.close()
            sys.exit()

    # Check that db configuration is well defined
    if (   ("PG_HOST" not in db_config)
        or ("PG_USER" not in db_config)
        or ("PG_NAME" not in db_config)
        or ("PG_PORT" not in db_config)
        or ("PG_PASSWORD" not in db_config)):
        print(("ERROR: Database is not properly defined in '{0}', please refer to README.md"
              .format(args.db_config_path)))
        sys.exit()

    return db_config


def OpenDataBase(configuration):
    # Connect to database
    db = psycopg2.connect(
        "postgresql://{0}:{1}@{2}:{3}/{4}"
        .format(configuration['PG_USER'],
                configuration['PG_PASSWORD'],
                configuration['PG_HOST'],
                configuration['PG_PORT'],
                configuration['PG_NAME']),
        # fetch method will return named tuples instead of regular tuples
        cursor_factory=psycopg2.extras.NamedTupleCursor,
    )

    try:
        # Open a cursor to perform database operations
        cursor = db.cursor()
        cursor.execute('SELECT 1')
    except psycopg2.OperationalError:
        print('ERROR: unable to connect to database')
        sys.exit()

    return cursor


def parseBox2D(string):
    # 'BOX(1 2, 3 4)' -> [[1,2],[3,4]]
    return [[float(coord) for coord in point.split(' ')] for point in string[4:-1].split(',')]


def from_3dcitydb(cursor, outputDir):
    # Get all buildings
    cursor.execute('SELECT building.id, BOX2D(cityobject.envelope) FROM building JOIN cityobject ON building.id=cityobject.id WHERE building.id=building.building_root_id')
    buildings = []
    for t in cursor.fetchall():
        id = t[0]
        box = parseBox2D(t[1])
        centroid = [(box[0][0] + box[1][0]) / 2, (box[0][1] + box[1][1]) / 2]
        buildings.append((id, centroid, box))

    tiles = kd_tree(buildings, 20)

    path = pathlib.Path(outputDir).expanduser()
    pathlib.Path(path, 'tiles').mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(tiles):
        ids = tuple([b[0] for b in t])
        centroid = [sum([b[1][0] for b in t]) / len(t), sum([b[1][1] for b in t]) / len(t)]
        b3dm = create_tile(cursor, ids, centroid)
        f = open(str(path) + '/tiles/{0}.b3dm'.format(i), 'wb')
        f.write(b3dm.to_array())
        f.close()

    root = {
        "children": [],
        "geometricError": 500,
        "refine": "ADD"
    }
    tileset = {
        "asset": {"version" : "1.0", "gltfUpAxis": "Z"},
        "geometricError": 500, # TODO
        "root" : root,
    }
    globalMin = [float("inf"), float("inf"), float("inf")]
    globalMax = [-float("inf"), -float("inf"), -float("inf")]
    for i, t in enumerate(tiles):
        centroid = [sum([b[1][0] for b in t]) / len(t), sum([b[1][1] for b in t]) / len(t), 0]
        c1 = [min([b[2][0][0] for b in t]), min([b[2][0][1] for b in t]), 0]
        c2 = [max([b[2][1][0] for b in t]), max([b[2][1][1] for b in t]), 200]
        globalMin = [min(globalMin[i], c1[i]) for i in range(0,3)]
        globalMax = [max(globalMax[i], c2[i]) for i in range(0,3)]
        c1 = [c1[i] - centroid[i] for i in range(0,3)]
        c2 = [c2[i] - centroid[i] for i in range(0,3)]
        center = [(c1[i] + c2[i]) / 2 for i in range(0,3)]
        xAxis = [c2[0] - c1[0], 0, 0]
        yAxis = [0, c2[1] - c1[1], 0]
        zAxis = [0, 0, c2[2] - c1[2]]
        box = [round(x, 3) for x in center + xAxis + yAxis + zAxis]
        node = {
            "transform": [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                centroid[0], centroid[1], centroid[2], 1
            ],
            "boundingVolume": {
                "box": box
            },
            "refine": "ADD",
            "content": {
                "url": "tiles/{0}.b3dm".format(i)
            }
        }
        root["children"].append(node)

    c1 = globalMin
    c2 = globalMax
    center = [(c1[i] + c2[i]) / 2 for i in range(0,3)]
    xAxis = [c2[0] - c1[0], 0, 0]
    yAxis = [0, c2[1] - c1[1], 0]
    zAxis = [0, 0, c2[2] - c1[2]]
    box = [round(x, 3) for x in center + xAxis + yAxis + zAxis]
    root["boundingVolume"] = {
        "box": box
    }

    f = open(str(path) + '/tileset.json'.format(i), 'w')
    f.write(json.dumps(tileset))
    f.close()


def kd_tree(points, maxPoints, depth=0):
    # The module argument of 2 (in the next line) hard-wires the fact that
    # this kd_tree is in fact a 2D_tree.
    axis = depth % 2

    # Within the sorting criteria point[1] refers to the centroid of the
    # bounding boxes of the buildings. And thus, depending on the value of
    # axis, we alternatively sort on the X or Y coordinate of those centroids:
    sPoints = sorted(points, key=lambda point: point[1][axis])
    median = len(sPoints) // 2
    lPoints = sPoints[:median]
    rPoints = sPoints[median:]
    tiles = []
    if len(lPoints) > maxPoints:
        tiles.extend(kd_tree(lPoints, maxPoints, depth + 1))
        tiles.extend(kd_tree(rPoints, maxPoints, depth + 1))
    else:
        tiles.append(lPoints)
        tiles.append(rPoints)
    return tiles


def create_tile(cursor, buildingIds, offset):

    class TreeWithChildrenAndParent:
        """
        A simple hierarchy/Direct Acyclic Graph, as in
        https://en.wikipedia.org/wiki/Tree_%28data_structure%29) with both
        children and parent relationships explicitly represented (for the
        sake of retrieval efficiency) as dictionaries using some user
        defined identifier as keys. TreeWithChildrenAndParent is not
        responsible of the identifiers and simply uses them as provided
        weak references.
        """
        def __init__(self):
            """Children of a given id (given as dict key)"""
            self.hierarchy = {}
            """Parents of a given id (given as dict key)"""
            self.reverseHierarchy = {}

        def addNodeToParent(self, object_id, parent_id):
            if parent_id is not None:
                if parent_id not in self.hierarchy:
                    self.hierarchy[parent_id] = []
                self.hierarchy[parent_id].append(object_id)
                self.reverseHierarchy[object_id] = parent_id

        def getParents(self, object_id):
            if object_id in self.reverseHierarchy:
                return [self.reverseHierarchy[object_id]]
            return []

    # ##### Collect the necessary information from a 3DCityDB database:
    objects = []
    classes = set()
    hierarchy = TreeWithChildrenAndParent()

    # Get building objects' id, class and hierarchy
    cursor.execute("SELECT building.id, building_parent_id, cityobject.gmlid, cityobject.objectclass_id FROM building JOIN cityobject ON building.id=cityobject.id WHERE building_root_id IN %s", (buildingIds,))
    for t in cursor.fetchall():
        objects.append({'internalId': t[0], 'gmlid': t[2], 'class': t[3]})
        hierarchy.addNodeToParent(t[0], t[1])
        classes.add(t[3])

    # Building + descendants ids
    subBuildingIds = tuple([i['internalId'] for i in objects])

    # Get surface geometries' id and class
    # TODO: offset
    cursor.execute("SELECT cityobject.id, cityobject.gmlid, thematic_surface.building_id, thematic_surface.objectclass_id, ST_AsBinary(ST_Multi(ST_Collect(ST_Translate(surface_geometry.geometry, -%s, -%s, 0)))) FROM surface_geometry JOIN thematic_surface ON surface_geometry.root_id=thematic_surface.lod2_multi_surface_id JOIN cityobject ON thematic_surface.id=cityobject.id WHERE thematic_surface.building_id IN %s GROUP BY surface_geometry.root_id, cityobject.id, cityobject.gmlid, thematic_surface.building_id, thematic_surface.objectclass_id", (offset[0], offset[1], subBuildingIds,))
    for t in cursor.fetchall():
        if t[4] is None:
            # Some thematic surface may have no geometry (cityGML exporter bug?): ignore them
            continue
        objects.append({'internalId': t[0], 'gmlid': t[1], 'class': t[3], 'geometry': t[4]})
        hierarchy.addNodeToParent(t[0], t[2])
        classes.add(t[3])

    geometricInstances = [(o['internalId'], o) for o in objects if 'geometry' in o]

    # ##### Proceed with encoding the geometries within a gltf (objects without
    # geometries are thus simply dropped out):
    arrays = []
    for object_id, obj in geometricInstances:
        geom = TriangleSoup.from_wkb_multipolygon(obj['geometry'])
        if len(geom.triangles[0]) != 0:
            arrays.append({
                'position': geom.getPositionArray(),
                'normal': geom.getNormalArray(),
                'bbox': [[float(i) for i in j] for j in geom.getBbox()]
            })
        else:
            # Weed out those objects that are deprived from a real geometry,
            # in order for further treatments not having to deal with them
            del geometricInstances[object_id]

    gltf = GlTF.from_binary_arrays(arrays, np.identity(4).flatten('F'))

    # ##### Proceed with the creation of a BathTableHierarchy:
    bth = BatchTableHierarchy()

    # Get class names
    classDict = {}
    cursor.execute("SELECT id, classname FROM objectclass")
    for t in cursor.fetchall():
        # TODO: allow custom fields to be added (here + in queries)
        classDict[t[0]] = (t[1], ['gmlid'])

    # Create each respective class
    for c in classes:
        bth.add_class(classDict[c][0], classDict[c][1])

    # The constructed BatchTableHierarchy encodes the semantics of the
    # geometrical objects but also of non geometrical objects:
    nonGeometricInstances = [(o['internalId'], o)
                             for o in objects if 'geometry' not in o]

    # Positioning index in the constructed BatchTableHierarchy
    objectPosition = {}
    for i, (object_id, _) in enumerate(itertools.chain(geometricInstances,
                                                       nonGeometricInstances)):
        objectPosition[object_id] = i

    # First insert objects with geometries and then objects without geometry
    # (each object having its respective class attributes)
    for object_id, obj in itertools.chain(geometricInstances,
                                          nonGeometricInstances):
        bth.add_class_instance(
            classDict[obj['class']][0],
            obj,
            [objectPosition[id] for id in hierarchy.getParents(object_id)])

    # Eventually wrap the geometries together with the BatchTableHierarchy
    # within a B3dm:
    return B3dm.from_glTF(gltf, bth)


if __name__ == '__main__':
    cursor = OpenDataBase(ParseCommandLine())
    from_3dcitydb(cursor, 'junk')
