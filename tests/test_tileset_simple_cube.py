import unittest
import numpy as np
from py3dtiles import B3dm, GlTF, TriangleSoup, TileSet, TileForReal


class TestTileBuilder(unittest.TestCase, object):

    @staticmethod
    def build_cuboid_as_binary_triangles_array(org_x, org_y, org_z, dx, dy, dz):
        # Vertices order is such that normals are pointing outwards of the cube.
        # Each face of the cube is made of two triangles.
        return [
            # Lower face (parallel to Ox-Oy plane i.e. horizontal)
            [np.array([org_x + dx, org_y,      org_z     ], dtype=np.float32),
             np.array([org_x     , org_y,      org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z     ], dtype=np.float32)],
            [np.array([org_x,      org_y,      org_z     ], dtype=np.float32),
             np.array([org_x,      org_y + dy, org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z     ], dtype=np.float32)],
            # Upper face (parallel to Ox-Oy plane i.e. horizontal)
            [np.array([org_x,      org_y,      org_z + dz], dtype=np.float32),
             np.array([org_x + dx, org_y,      org_z + dz], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z + dz], dtype=np.float32)],
            [np.array([org_x,      org_y + dy, org_z + dz], dtype=np.float32),
             np.array([org_x,      org_y,      org_z + dz], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z + dz], dtype=np.float32)],
            # Side face parallel to the Ox-Oz plane (vertical),
            [np.array([org_x,      org_y,      org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y,      org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y,      org_z + dz], dtype=np.float32)],
            [np.array([org_x,      org_y,      org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y,      org_z + dz], dtype=np.float32),
             np.array([org_x,      org_y,      org_z + dz], dtype=np.float32)],
            # Other side face parallel to the Ox-Oz plane,
            [np.array([org_x,      org_y + dy, org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z + dz], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z     ], dtype=np.float32)],
            [np.array([org_x,      org_y + dy, org_z     ], dtype=np.float32),
             np.array([org_x,      org_y + dy, org_z + dz], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z + dz], dtype=np.float32)],
            # Side face parallel to the Oy-Oz plane (vertical)
            [np.array([org_x,      org_y,      org_z     ], dtype=np.float32),
             np.array([org_x,      org_y,      org_z + dz], dtype=np.float32),
             np.array([org_x,      org_y + dy, org_z + dz], dtype=np.float32)],
            [np.array([org_x,      org_y,      org_z     ], dtype=np.float32),
             np.array([org_x,      org_y + dy, org_z + dz], dtype=np.float32),
             np.array([org_x,      org_y + dy, org_z     ], dtype=np.float32)],
            # Other side face parallel to the Oy-Oz plane (vertical)
            [np.array([org_x + dx, org_y,      org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z + dz], dtype=np.float32),
             np.array([org_x + dx, org_y,      org_z + dz], dtype=np.float32)],
            [np.array([org_x + dx, org_y,      org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z     ], dtype=np.float32),
             np.array([org_x + dx, org_y + dy, org_z + dz], dtype=np.float32)],
        ]

    def test_build(self):
        # Define a TriangleSoup setting up some geometry
        ts = TriangleSoup()
        triangles = TestTileBuilder.build_cuboid_as_binary_triangles_array(
                                    -178.1, -12.845, 300.0, 100., 200., 300.)
        triangles.extend(
                    TestTileBuilder.build_cuboid_as_binary_triangles_array(
                                      -8.1, -1.8, 300.0, 200., 300., 100.) )
        ts.triangles = [triangles]

        # Define a tile that will hold the geometry
        tile = TileForReal()
        tile.set_bounding_volume(ts.getBoxBoundingVolumeAlongAxis())

        # Build a tile content (with B3dm formatting) out of the geometry
        # held in the TriangleSoup:
        arrays = [{
            'position': ts.getPositionArray(),
            'normal':   ts.getNormalArray(),
            'bbox':     ts.getBboxAsFloat()
        }]
        transform = np.identity(4).flatten('F')
        glTF = GlTF.from_binary_arrays(arrays, transform)
        tile_content = B3dm.from_glTF(glTF)
        tile.set_content(tile_content)

        # Define the tileset that will hold the (single) tile
        tile_set = TileSet()
        tile_set.add_tile(tile)
        tile_set.add_asset_extras("Py3dTiles TestTileBuilder example.")
        tile_set.write_to_directory('junk')
