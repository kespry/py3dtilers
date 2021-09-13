import unittest

from py3dtiles import BoundingVolumeBox, TemporalBoundingVolume

from py3dtilers.CityTiler.temporal_graph import TemporalGraph
from py3dtilers.CityTiler.database_accesses import open_data_bases
from py3dtilers.CityTiler.CityTemporalTiler import combine_nodes_with_buildings_from_3dcitydb, from_3dcitydb, build_temporal_tile_set


class Args():
    def __init__(self):
        self.temporal_graph = ["tests/city_temporal_tiler_test_data/graph_2009-2012.json"]
        self.db_config_path = ["tests/city_temporal_tiler_test_data/test_config_2009.yml",
                               "tests/city_temporal_tiler_test_data/test_config_2012.yml"]
        self.time_stamps = ["2009", "2012"]


class Test_Tile(unittest.TestCase):

    def test_temporal(self):
        cli_args = Args()
        graph = TemporalGraph(cli_args)
        graph.reconstruct_connectivity()

        graph.display_characteristics('   ')
        graph.simplify(display_characteristics=True)

        cursors = open_data_bases(cli_args.db_config_path)
        time_stamped_cursors = dict()
        for index in range(len(cursors)):
            time_stamped_cursors[cli_args.time_stamps[index]] = cursors[index]
        all_buildings = combine_nodes_with_buildings_from_3dcitydb(
            graph,
            cursors,
            cli_args)

        tile_set = from_3dcitydb(time_stamped_cursors, all_buildings)

        tile_set.get_root_tile().set_bounding_volume(BoundingVolumeBox())
        tile_set.get_root_tile().get_bounding_volume().add_extension(TemporalBoundingVolume())

        temporal_tile_set = build_temporal_tile_set(graph)
        tile_set.add_extension(temporal_tile_set)

        [cursor.close() for cursor in cursors]

        tile_set.write_to_directory("tests/city_temporal_tiler_test_data/junk/temporal")
