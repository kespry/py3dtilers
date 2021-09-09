import numpy as np
from py3dtiles import BoundingVolumeBox, TriangleSoup


class ObjectToTile(object):
    """
    The base class of all object that need to be tiled, in order to be
    used with the corresponding tiler.
    """

    def __init__(self, id=None):
        """
        :param id: given identifier
        """

        self.geom = TriangleSoup()

        # The identifier of the database
        self.id = None

        # Optional application specific data to be added to the batch table for this object
        self.batchtable_data = None

        # A Bounding Volume Box object
        self.box = None

        # The centroid of the box
        self.centroid = np.array([0, 0, 0])

        self.texture = None

        self.set_id(id)

    def set_id(self, id):
        self.id = id

    def get_id(self):
        return self.id

    def set_batchtable_data(self, data):
        self.batchtable_data = data

    def get_batchtable_data(self):
        return self.batchtable_data

    def get_centroid(self):
        return self.centroid

    def get_bounding_volume_box(self):
        return self.box

    def get_geom_as_triangles(self):
        return self.geom.triangles[0]

    def set_triangles(self, triangles):
        self.geom.triangles[0] = triangles

    def set_box(self):
        """
        Parameters
        ----------
        Returns
        -------
        """
        bbox = self.geom.getBbox()
        self.box = BoundingVolumeBox()
        self.box.set_from_mins_maxs(np.append(bbox[0], bbox[1]))

        # Set centroid from Bbox center
        self.centroid = np.array([(bbox[0][0] + bbox[1][0]) / 2.0,
                                  (bbox[0][1] + bbox[1][1]) / 2.0,
                                  (bbox[0][2] + bbox[0][2]) / 2.0])

    def get_texture(self):
        return self.texture

    def set_texture(self, texture):
        self.texture = texture

    def has_texture(self):
        return self.texture is not None


class ObjectsToTile(object):
    """
    A decorated list of ObjectsToTile type objects.
    """

    def __init__(self, objects=None):
        self.objects = list()
        if(objects):
            self.objects.extend(objects)

    def __iter__(self):
        return iter(self.objects)

    def __getitem__(self, item):
        if isinstance(item, slice):
            objects_class = self.__class__
            return objects_class(self.objects.__getitem__(item))
        # item is then an int type:
        return self.objects.__getitem__(item)

    def __add__(self, other):
        objects_class = self.__class__
        new_objects = objects_class(self.objects)
        new_objects.objects.extend(other.objects)
        return new_objects

    def append(self, obj):
        self.objects.append(obj)

    def extend(self, others):
        self.objects.extend(others)

    def get_objects(self):
        return self.objects

    def __len__(self):
        return len(self.objects)

    def get_centroid(self):
        """
        :param objects: an array containing objs

        :return: the centroid of the tileset.
        """
        centroid = [0., 0., 0.]
        for objectToTile in self:
            centroid[0] += objectToTile.get_centroid()[0]
            centroid[1] += objectToTile.get_centroid()[1]
            centroid[2] += objectToTile.get_centroid()[2]
        return [centroid[0] / len(self),
                centroid[1] / len(self),
                centroid[2] / len(self)]

    def translate_tileset(self, offset):
        """
        :param objects: an array containing geojsons
        :param offset: an offset
        :return:
        """
        # Translate the position of each geojson by an offset
        for object_to_tile in self.objects:
            new_geom = []
            for triangle in object_to_tile.get_geom_as_triangles():
                new_position = []
                for points in triangle:
                    # Must to do this this way to ensure that the new position
                    # stays in float32, which is mandatory for writing the GLTF
                    new_position.append(np.array(points - offset, dtype=np.float32))
                new_geom.append(new_position)
            object_to_tile.set_triangles(new_geom)
            object_to_tile.set_box()

    @staticmethod
    def create_batch_table_extension(extension_name, ids=None, objects=None):
        pass

    @staticmethod
    def create_bounding_volume_extension(extension_name, ids=None, objects=None):
        pass
