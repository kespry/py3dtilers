# -*- coding: utf-8 -*-
import os
from os import listdir
import numpy as np
import json
from shapely.geometry import LinearRing, LineString
from earclip import triangulate

from ..Common import ObjectToTile, ObjectsToTile


# The GeoJson file contains the ground surface of urban elements, mainly buildings.
# Those elements are called "features", each feature has its own ground coordinates.
# The goal here is to take those coordinates and create a box from it.
# To do this, we compute the center of the lower face
# Then we create the triangles of this face
# and duplicate it with a Z offset to create the upper face
# Then we create the side triangles to connect the upper and the lower faces
class Geojson(ObjectToTile):

    n_feature = 0

    # Default height will be used if no height is found when parsing the data
    default_height = 2

    def __init__(self, id=None):
        super().__init__(id)

        self.height = 0
        """How high we extrude the polygon when creating the 3D geometry"""

        self.vertices = list()
        self.triangles = list()

        self.polygons = list()

    def find_coordinate_index(self, coordinates, value):
        for i, coord in enumerate(coordinates):
            if coord[0] == value[0]:
                if coord[1] == value[1]:
                    return i
        return None

    def line_intersect(self, l1_start, l1_end, l2_start, l2_end):
        """
        https://stackoverflow.com/questions/64463369/intersection-of-two-infinite-lines-specified-by-points
        Find the intersection between 2 lines, each line is defined by 2 points
        """
        p1_start = np.asarray(l1_start)
        p1_end = np.asarray(l1_end)
        p2_start = np.asarray(l2_start)
        p2_end = np.asarray(l2_end)

        p = p1_start
        r = (p1_end - p1_start)
        q = p2_start
        s = (p2_end - p2_start)

        t = np.cross(q - p, s) / (np.cross(r, s))
        i = p + t * r
        return i.tolist()

    def get_parallel_offset(self, start_point, end_point, offset=3):
        line = LineString([start_point, end_point])
        po_left = list(line.parallel_offset(offset, 'left', join_style=2, resolution=1).coords)
        po_right = list(line.parallel_offset(offset, 'right', join_style=2, resolution=1).coords)
        return po_left, po_right

    def buffer_line_string(self, coordinates):
        """
        Take a line string as coordinates

        Return: a buffered polygon
        """
        polygon = [None] * (len(coordinates) * 2)

        po_1_left, po_1_right = self.get_parallel_offset(coordinates[0], coordinates[1], offset=3)
        polygon[0] = [po_1_left[0][0], po_1_left[0][1], coordinates[0][2]]
        polygon[(len(coordinates) * 2) - 1] = [po_1_right[1][0], po_1_right[1][1], coordinates[0][2]]

        po_2_left, po_2_right = self.get_parallel_offset(coordinates[len(coordinates) - 2], coordinates[len(coordinates) - 1], offset=3)
        polygon[len(coordinates) - 1] = [po_2_left[1][0], po_2_left[1][1], coordinates[len(coordinates) - 1][2]]
        polygon[len(coordinates)] = [po_2_right[0][0], po_2_right[0][1], coordinates[len(coordinates) - 1][2]]

        for i in range(0, len(coordinates) - 2):
            po_1_left, po_1_right = self.get_parallel_offset(coordinates[i], coordinates[i + 1], offset=3)
            po_2_left, po_2_right = self.get_parallel_offset(coordinates[i + 1], coordinates[i + 2], offset=3)

            intersection_left = self.line_intersect(po_1_left[0], po_1_left[1], po_2_left[0], po_2_left[1])
            intersection_right = self.line_intersect(po_1_right[0], po_1_right[1], po_2_right[0], po_2_right[1])
            polygon[i + 1] = [intersection_left[0], intersection_left[1], coordinates[i + 1][2]]
            polygon[len(polygon) - 2 - i] = [intersection_right[0], intersection_right[1], coordinates[i + 1][2]]

        return polygon

    def parse_geojson(self, feature, properties, is_roof):
        """
        Parse a feature of the .geojson file to extract the height and the coordinates of the feature.
        """
        # Current feature number (used for debug)
        Geojson.n_feature += 1

        # If precision is equal to 9999, it means Z values of the features are missing, so we skip the feature
        prec_name = properties[properties.index('prec') + 1]
        if prec_name != 'NONE':
            if prec_name in feature['properties']:
                if feature['properties'][prec_name] >= 9999.:
                    return False
            else:
                print("No propertie called " + prec_name + " in feature " + str(Geojson.n_feature))

        height_name = properties[properties.index('height') + 1]
        if height_name.replace('.', '', 1).isdigit():
            self.height = float(height_name)
        else:
            if height_name in feature['properties']:
                if feature['properties'][height_name] > 0:
                    self.height = feature['properties'][height_name]
                else:
                    return False
            else:
                print("No propertie called " + height_name + " in feature " + str(Geojson.n_feature) + ". Set height to default value (" + str(Geojson.default_height) + ").")
                self.height = Geojson.default_height

        if feature['geometry']['type'] == 'Polygon':
            coords = feature['geometry']['coordinates'][0][:-1]
            if is_roof:
                for coord in coords:
                    coord[2] -= self.height
            self.polygons.append(coords)

        if feature['geometry']['type'] == 'MultiPolygon':
            for polygon in feature['geometry']['coordinates'][0]:
                coords = polygon[:-1]
                # Check if the coordinates are clockwise. If they are clockwise, the polygon is a hole, so we skip it
                if not LinearRing(coords).is_ccw:
                    if is_roof:
                        for coord in coords:
                            coord[2] -= self.height
                    self.polygons.append(coords)

        if feature['geometry']['type'] == 'MultiLineString':
            coords = feature['geometry']['coordinates'][0]
            self.polygons.append(self.buffer_line_string(coords))

        if feature['geometry']['type'] == 'LineString':
            coords = feature['geometry']['coordinates']
            self.polygons.append(self.buffer_line_string(coords))

        return True

    def parse_geom(self, create_obj=False):
        """
        Creates the 3D extrusion of the feature.
        """
        height = self.height

        # Contains the triangles vertices. Used to create 3D tiles
        triangles = list()
        # Contains the triangles vertices index. Used to create Objs
        triangles_id = list()

        vertex_offset = 0

        for coordinates in self.polygons:

            length = len(coordinates)
            vertices = [None] * (2 * length)

            for i, coord in enumerate(coordinates):
                vertices[i] = np.array([coord[0], coord[1], coord[2]], dtype=np.float32)
                vertices[i + length] = np.array([coord[0], coord[1], coord[2] + height], dtype=np.float32)

            # Triangulate the feature footprint
            poly_triangles = triangulate(coordinates)

            # Create upper face triangles
            for tri in poly_triangles:
                upper_tri = [np.array([coord[0], coord[1], coord[2] + height], dtype=np.float32) for coord in tri]
                triangles.append(upper_tri)

            # Create side triangles
            for i in range(0, length):
                triangles.append([vertices[i], vertices[length + i], vertices[length + ((i + 1) % length)]])
                triangles.append([vertices[i], vertices[length + ((i + 1) % length)], vertices[((i + 1) % length)]])

            # If the obj creation flag is defined, create triangles for the obj
            if create_obj:
                for tri in poly_triangles:
                    lower_tri = [self.find_coordinate_index(coordinates, coord) + vertex_offset for coord in reversed(tri)]
                    triangles_id.append(lower_tri)
                    upper_tri = [self.find_coordinate_index(coordinates, coord) + length + vertex_offset for coord in tri]
                    triangles_id.append(upper_tri)

                for i in range(0, length):
                    triangles_id.append([i, length + i, length + ((i + 1) % length)])
                    triangles_id.append([i, length + ((i + 1) % length), ((i + 1) % length)])

                vertex_offset += len(vertices)

                # keep vertices and triangles in order to create Obj model
                self.vertices.extend(vertices)
                self.triangles.extend(triangles_id)

        self.geom.triangles.append(triangles)

        self.set_box()

        return True

    def get_geojson_id(self):
        return super().get_id()

    def set_geojson_id(self, id):
        return super().set_id(id)


class Geojsons(ObjectsToTile):
    """
        A decorated list of ObjectsToTile type objects.
    """

    def __init__(self, objects=None):
        super().__init__(objects)

    @staticmethod
    def retrieve_geojsons(path, properties, obj_name, is_roof):
        """
        :param path: a path to a directory

        :return: a list of geojson.
        """

        features = list()
        geometries = Geojsons()

        # Used only when creating an .obj model
        vertices = list()
        triangles = list()
        vertice_offset = 1
        center = [0, 0, 0]

        files = []

        if(os.path.isdir(path)):
            geojson_dir = listdir(path)
            for geojson_file in geojson_dir:
                file_path = os.path.join(path, geojson_file)
                if(os.path.isfile(file_path)):
                    if(".geojson" in geojson_file or ".json" in geojson_file):
                        files.append(file_path)
        else:
            files.append(path)

        # Reads and parse every features from the file(s)
        for geojson_file in files:
            print("Reading " + geojson_file)
            # Get id from its name
            id = geojson_file.replace('json', '')
            with open(geojson_file) as f:
                gjContent = json.load(f)

            k = 0
            for feature in gjContent['features']:

                if "ID" in feature['properties']:
                    feature_id = feature['properties']['ID']
                else:
                    feature_id = id + str(k)
                    k += 1
                geojson = Geojson(feature_id)
                if(geojson.parse_geojson(feature, properties, is_roof)):
                    features.append(geojson)

        create_obj = obj_name is not None

        for feature in features:
            # Create geometry as expected from GLTF from an geojson file
            if(feature.parse_geom(create_obj)):
                geometries.append(feature)

                if create_obj:
                    # Add triangles and vertices to create an obj
                    for vertice in feature.vertices:
                        vertices.append(vertice)
                    for triangle in feature.triangles:
                        triangles.append([v + vertice_offset for v in triangle])
                    vertice_offset += len(feature.vertices)
                    centroid = feature.get_centroid()
                    for i in range(0, len(centroid)):
                        center[i] += centroid[i]

        if create_obj:
            center[:] = [c / len(geometries) for c in center]
            file_name = obj_name
            f = open(os.path.join(file_name), "w")
            f.write("# " + file_name + "\n")

            for vertice in vertices:
                f.write("v " + str(vertice[0] - center[0]) + " " + str(vertice[1] - center[1]) + " " + str(vertice[2] - center[2]) + "\n")

            for triangle in triangles:
                f.write("f " + str(int(triangle[0])) + " " + str(int(triangle[1])) + " " + str(int(triangle[2])) + "\n")

        return geometries
