class GeometryNode():
    """
    Each node contains an instance of FeatureList
    and a list of child nodes.
    A node will correspond to a tile of the 3dtiles tileset.
    """

    def __init__(self, feature_list=None, geometric_error=50, with_texture=False):
        """
        :param feature_list: an instance of FeatureList.
        :param geometric_error: the distance below which this node should be displayed.
        :param Boolean with_texture: if this node must keep the texture of the features or not.
        """
        self.feature_list = feature_list
        self.child_nodes = list()
        self.with_texture = with_texture
        self.geometric_error = geometric_error

    def set_child_nodes(self, nodes=list()):
        """
        Set the child nodes of this node.
        :param nodes: list of nodes
        """
        self.child_nodes = nodes

    def add_child_node(self, node):
        """
        Add a child to the child nodes.
        :param node: a node
        """
        self.child_nodes.append(node)

    def has_texture(self):
        """
        Return True if this node must keep the texture of its features.
        :return: boolean
        """
        return self.with_texture and self.geometries_have_texture()

    def geometries_have_texture(self):
        """
        Check if all the features in the node have a texture.
        :return: a boolean
        """
        return all([feature.has_texture() for feature in self.feature_list])

    def get_features(self):
        """
        Return the features in this node and the features in the child nodes (recursively).
        :return: a list of Feature
        """
        objects = [self.feature_list]
        for child in self.child_nodes:
            objects.extend(child.get_features())
        return objects

    def set_node_features_geometry(self, user_arguments=None):
        """
        Set the geometry of the features in this node and the features in the child nodes (recursively).
        """
        for features in reversed(self.get_features()):
            features.set_features_geom(user_arguments)

    def get_leaves(self):
        """
        Return the leaves of this node.
        If the node has no child, return this node.
        :return: a list of GeometryNode
        """
        if len(self.child_nodes) < 1:
            return [self]
        else:
            leaves = list()
            for node in self.child_nodes:
                leaves.extend(node.get_leaves())
            return leaves

    def get_number_of_children(self):
        """
        Return the number of children of this node.
        The count is recursive.
        :return: int
        """
        n = len(self.child_nodes)
        for child in self.child_nodes:
            n += child.get_number_of_children()
        return n
