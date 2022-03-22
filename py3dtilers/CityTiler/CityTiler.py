import numpy as np

from ..Common import Tiler
from .citym_cityobject import CityMCityObjects
from .citym_building import CityMBuildings
from .citym_relief import CityMReliefs
from .citym_waterbody import CityMWaterBodies
from .citym_bridge import CityMBridges
from .database_accesses import open_data_base


class CityTiler(Tiler):
    """
    The CityTiler can read 3DCityDB databases and create 3DTiles.
    The database can contain buildings, bridges, relief or water bodies.
    """

    def __init__(self):
        super().__init__()

        # adding positional arguments
        self.parser.add_argument('--db_config_path',
                                 nargs='*',
                                 default=['py3dtilers/CityTiler/CityTilerDBConfig.yml'],
                                 type=str,
                                 help='Path(es) to the database configuration file(s)')

        self.parser.add_argument('--type',
                                 nargs='?',
                                 default='building',
                                 type=str,
                                 choices=['building', 'relief', 'water', 'bridge'],
                                 help='identify the object type to seek in the database')

        # adding optional arguments
        self.parser.add_argument('--with_BTH',
                                 dest='with_BTH',
                                 action='store_true',
                                 help='Adds a Batch Table Hierarchy when defined')

        self.parser.add_argument('--split_surfaces',
                                 dest='split_surfaces',
                                 action='store_true',
                                 help='Keeps the surfaces of the cityObjects split when defined')

    def get_output_dir(self):
        """
        Return the directory name for the tileset.
        """
        if self.args.output_dir is None:
            if self.args.type == "building":
                return "junk_buildings"
            elif self.args.type == "relief":
                return "junk_reliefs"
            elif self.args.type == "water":
                return "junk_water_bodies"
            elif self.args.type == "bridge":
                return "junk_bridges"
            else:
                return "junk"
        else:
            return self.args.output_dir

    def set_features_centroid(self, cursor, cityobjects, objects_type):
        """
        Get the surfaces of all the cityobjects and transform them into TriangleSoup.
        Surfaces of the same cityObject are merged into one geometry.
        :param cursor: a database access cursor.
        :param cityobjects: the CityGML objects found in the database.
        :param objects_type: a class name among CityMCityObject derived classes.
        """
        cityobjects_with_centroid = list()
        for cityobject in cityobjects:
            try:
                id = cityobject.get_database_id()
                cursor.execute(objects_type.sql_query_centroid(id))
                centroid = cursor.fetchall()
                if centroid is not None:
                    cityobject.centroid = np.array([centroid[0].st_x, centroid[0].st_y, centroid[0].st_z])
                    cityobjects_with_centroid.append(cityobject)
            except AttributeError:
                continue
            except ValueError:
                continue
        cityobjects.objects = cityobjects_with_centroid

    def from_3dcitydb(self, cursor, objects_type):
        """
        Create a 3DTiles tileset from the objects contained in a database.
        :param cursor: a database access cursor.
        :param objects_type: a class name among CityMCityObject derived classes.
                            For example, objects_type can be "CityMBuilding".

        :return: a tileset.
        """
        print('Retrieving city objects from database...')
        cityobjects = CityMCityObjects.retrieve_objects(cursor, objects_type)
        print(len(cityobjects), f'city objects of type \'{objects_type.__name__}\' found in the database.')

        if not cityobjects:
            raise ValueError(f'The database does not contain any {objects_type.__name__} object')

        self.set_features_centroid(cursor, cityobjects, objects_type)

        kd_tree_max = 25 if self.args.with_texture else 500
        extension_name = None
        if CityMBuildings.is_bth_set():
            extension_name = "batch_table_hierarchy"
        return self.create_tileset_from_geometries(cityobjects, extension_name=extension_name, kd_tree_max=kd_tree_max)


def main():
    """
    Run the CityTiler: create a 3DTiles tileset from the CityGML objcts contained in a 3DCityDB database.
    The tileset is writen in 'junk_<object_type>/' by default.
    :return: no return value
    """
    city_tiler = CityTiler()
    city_tiler.parse_command_line()
    args = city_tiler.args

    print('Connecting to database...')
    cursor = open_data_base(args.db_config_path[0])

    if args.type == "building":
        objects_type = CityMBuildings
        if args.with_BTH:
            CityMBuildings.set_bth()
    elif args.type == "relief":
        objects_type = CityMReliefs
    elif args.type == "water":
        objects_type = CityMWaterBodies
    elif args.type == "bridge":
        objects_type = CityMBridges

    objects_type.set_cursor(cursor)

    tileset = city_tiler.from_3dcitydb(cursor, objects_type)

    # A shallow attempt at providing some traceability on where the resulting
    # data set comes from:
    cursor.execute('SELECT inet_client_addr()')
    server_ip = cursor.fetchone()[0]
    cursor.execute('SELECT current_database()')
    database_name = cursor.fetchone()[0]
    origin = f'This tileset is the result of Py3DTiles {__file__} script '
    origin += f'run with data extracted from database {database_name} '
    origin += f' obtained from server {server_ip}.'
    tileset.add_asset_extras(origin)

    cursor.close()
    tileset.write_as_json(city_tiler.get_output_dir())


if __name__ == '__main__':
    main()
