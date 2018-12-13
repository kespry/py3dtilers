# -*- coding: utf-8 -*-
import sys
import os
from .threedtiles_notion import ThreeDTilesNotion
from .bounding_volume import BoundingVolume


class TileForReal(ThreeDTilesNotion):

    def __init__(self):
        super().__init__()
        self.attributes["boundingVolume"] = None
        self.attributes["geometricError"] = None
        self.attributes["refine"] = "ADD"
        self.attributes["content"] = None
        self.attributes["children"] = list()
        # Some possible valid properties left un-delt with
        # viewerRequestVolume
        # self.attributes["transform"] = None


        # A TileContent has an uri property that can be defined (when the
        # owning TileSet is serialized) as the path name of the file holding
        # the corresponding Tile content. Since, for the time being, the
        # TileContent class is not yet defined we use (in a kludgy way) this
        # TileForReal class to carry that duty. :(
        # FIXME: create the TileContent class and remove the following undue
        # property from this class
        self.content_pathname = None

    def set_transform(self, transform):
        """
        :param transform: a flattened transformation matrix
        :return:
        """
        self.attributes["transform"] = [round(float(e), 3) for e in transform]

    def set_bounding_volume(self, bounding_volume):
        self.attributes["boundingVolume"] = bounding_volume

    def get_bounding_volume(self):
        return self.attributes["boundingVolume"]

    def set_content(self, content):
        self.attributes["content"] = content

    def set_geometric_error(self, error):
        self.attributes["geometricError"] = error

    def set_content_uri(self, uri):
        # FIXME: refer to above comment concerning content_pathname and
        #        remove this method.
        self.content_pathname = uri

    def add_child(self, tile):
        self.attributes["children"].append(tile)

    def has_children(self):
        if 'children' in self.attributes and self.attributes["children"]:
            return True
        return False

    def get_descendants(self):
        """
        :return: the recursive (across the children tree) list of the children
                 tiles
        """
        if not self.has_children():
            print("Warning: should have checked for existing children first?")
            # It could be that prepare_for_json() did some wipe out:
            if not 'children' in self.attributes:
                return list()

        descendants = list()
        for child in self.attributes["children"]:
            # Add the child...
            descendants.append(child)
            # and if (and only if) they are grand-children then recurse
            if child.has_children():
                descendants.extend(child.get_descendants())
        return descendants

    def prepare_for_json(self):
        if not self.attributes["boundingVolume"]:
            print("Warning: defaulting Tile's unset 'Bounding Volume'.")
            # FIXME: what would be a decent default ?!
            self.attributes["boundingVolume"] = BoundingVolume()
        if not self.attributes["geometricError"]:
            print("Warning: defaulting Tile's unset 'Geometric Error'.")
            # FIXME: what would be a decent default ?!
            self.set_geometric_error(500.0)
        if not self.attributes["children"]:
            # The children list exists indeed (for technical reasons) yet it
            # happens to be still empty. This would pollute the json output
            # by adding a "children" entry followed by an empty list. In such
            # case just remove that attributes entry:
            del self.attributes["children"]
        if not self.attributes["content"]:
            self.attributes["content"] = {"uri":
              "Dummy content set by py3dtiles:ThreeDTilesNotion:prepare_for_json()"}

    def write_content(self):
        """
        Write (or overwrite) the tile _content_ to the filename designated by
        content_pathname kludgy property. Note that it is the responsibility
        of the owning Tileset to
          - set up the content_pathname
          - to deal with the Tile (because the Tile information is serialized
            within the TileSet)
        """
        if not self.content_pathname:
            print("A content_pathname is required")
            sys.exit(1)

        # Make sure the output directory exists
        target_dir = os.path.dirname(self.content_pathname)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # Write the tile content of this tile:
        content = self.attributes["content"]
        # The following is ad-hoc code for the currently existing b3dm class.
        # FIXME: have the future TileContent classe have a write method
        # and simplify the following code accordingly.
        content_file = open(self.content_pathname, 'wb')
        content_file.write(content.to_array())
        content_file.close()