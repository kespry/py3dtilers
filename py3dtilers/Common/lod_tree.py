from ..Common import LodNode, Lod1Node, LoaNode, Groups


class LodTree():
    """
    The LodTree contains the root node(s) of the LOD hierarchy and the centroid of the whole tileset
    """
    def __init__(self, objects_to_tile, also_create_lod1=False, also_create_loa=False, polygons_path=None, with_texture=False):
        """
        create_lod_tree takes an instance of ObjectsToTile (which contains a collection of ObjectToTile) and creates nodes
        In order to reduce the number of .b3dm, it also groups the objects (ObjectToTile instances) in different ObjectsToTileWithGeometry
        An ObjectsToTileWithGeometry contains an ObjectsToTile (the ObjectToTile(s) in the group) and an optional ObjectsToTile which is its own geometry
        """
        root_nodes = list()

        groups = self.group_features(objects_to_tile, polygons_path)

        for group in groups:
            node = LodNode(group.objects_to_tile, 1)
            node.with_texture = with_texture
            root_node = node
            if also_create_lod1:
                lod1_node = Lod1Node(group.objects_to_tile, 5)
                lod1_node.add_child_node(root_node)
                root_node = lod1_node
            if group.with_geometry:
                loa_node = LoaNode(group.objects_to_tile, 20, group.additional_points, group.points_dict)
                loa_node.add_child_node(root_node)
                root_node = loa_node

            root_nodes.append(root_node)

        self.root_nodes = root_nodes
        self.centroid = objects_to_tile.get_centroid()

    def set_centroid(self, centroid):
        self.centroid = centroid

    def group_features(self, objects_to_tile, polygons_path=None):
        """
        Group objects_to_tile to reduce the number of tiles
        """
        groups = Groups(objects_to_tile, polygons_path)
        return groups.get_groups_as_list()
