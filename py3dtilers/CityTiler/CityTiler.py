import argparse

from py3dtiles import BoundingVolumeBox, TriangleSoup

from ..Common import create_tileset
from .citym_cityobject import CityMCityObjects, CityMCityObject
from .citym_building import CityMBuildings
from .citym_relief import CityMReliefs
from .citym_waterbody import CityMWaterBodies
from .database_accesses import open_data_base


def parse_command_line():
    # arg parse
    text = '''A small utility that build a 3DTiles tileset out of the content
               of a 3DCityDB database.'''
    parser = argparse.ArgumentParser(description=text)

    # adding positional arguments
    parser.add_argument('db_config_path',
                        nargs='?',
                        default='CityTilerDBConfig.yml',
                        type=str,  # why precise this if it is the default config ?
                        help='path to the database configuration file')

    parser.add_argument('object_type',
                        nargs='?',
                        default='building',
                        type=str,
                        choices=['building', 'relief', 'water'],
                        help='identify the object type to seek in the database')

    parser.add_argument('--loa',
                        nargs='*',
                        type=str,
                        help='identity which loa to create')

    # adding optional arguments
    parser.add_argument('--with_BTH',
                        dest='with_BTH',
                        action='store_true',
                        help='Adds a Batch Table Hierarchy when defined')

    result = parser.parse_args()
    if(result.loa is not None and len(result.loa) == 0):
        result.loa = ['polygons']

    return result

def from_3dcitydb(cursor, objects_type, loa_path=None):
    """
    :param cursor: a database access cursor.
    :param objects_type: a class name among CityMCityObject derived classes.
                        For example, objects_type can be "CityMBuilding".

    :return: a tileset.
    """
    cityobjects = CityMCityObjects.retrieve_objects(cursor, objects_type)
    
    if not cityobjects:
        raise ValueError(f'The database does not contain any {objects_type} object')

    for cityobject in cityobjects:
        id = '(' + str(cityobject.get_database_id()) + ')'
        cursor.execute(objects_type.sql_query_geometries(id))
        for t in cursor.fetchall():
            geom_as_string = t[1]
            cityobject.geom = TriangleSoup.from_wkb_multipolygon(geom_as_string)
            cityobject.set_box()

    # surfaces = list()
    # for cityobject in cityobjects:
    #     id = '(' + str(cityobject.get_database_id()) + ')'
    #     cursor.execute(objects_type.sql_query_geometries(id))
    #     for t in cursor.fetchall():
    #         surface_id = t[0]
    #         geom_as_string = t[1]
    #         if geom_as_string is not None:
    #             surface = CityMCityObject(surface_id)
    #             try:
    #                 surface.geom = TriangleSoup.from_wkb_multipolygon(geom_as_string)
    #                 surface.set_box()
    #                 surfaces.append(surface)
    #             except ValueError:
    #                 continue
    # objets_to_tile = CityMCityObjects(surfaces)

    with_loa = loa_path is not None

    return create_tileset(cityobjects, also_create_lod1=True, also_create_loa=with_loa, loa_path=loa_path)

def main():
    """
    :return: no return value

    this function creates a repository name "junk_object_type" where the
    tileset is stored.
    """
    args = parse_command_line()
    cursor = open_data_base(args.db_config_path)

    if args.object_type == "building":
        objects_type = CityMBuildings
        if args.with_BTH:
            CityMBuildings.set_bth()
    elif args.object_type == "relief":
        objects_type = CityMReliefs
    elif args.object_type == "water":
        objects_type = CityMWaterBodies
        
    loa_path = None
    if args.loa is not None:
        loa_path = args.loa[0]

    tileset = from_3dcitydb(cursor, objects_type, loa_path)

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
    tileset.get_root_tile().set_bounding_volume(BoundingVolumeBox())
    if args.object_type == "building":
        tileset.write_to_directory('junk_buildings')
    elif args.object_type == "relief":
        tileset.write_to_directory('junk_reliefs')
    elif args.object_type == "water":
        tileset.write_to_directory('junk_water_bodies')


if __name__ == '__main__':
    main()
