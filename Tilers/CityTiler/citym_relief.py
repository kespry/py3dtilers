# -*- coding: utf-8 -*-
from citym_cityobject import CityMCityObject, CityMCityObjects


class CityMRelief(CityMCityObject):
    """
    Implementation of the Digital Terrain Model (DTM) objects from the CityGML model.
    """
    def __init__(self):
        super().__init__()


class CityMReliefs(CityMCityObjects):
    """
    Implementation of the Digital Terrain Model (DTM) objects from the CityGML model.
    """
    def __init__(self):
        super().__init__()

    @staticmethod
    def sql_query_objects(reliefs):
        """

        :param reliefs:
        :return:
        """
        if not reliefs:

            # No specific relief were sought. We thus retrieve all the ones
            # we can find in the database:
            query = "SELECT relief_feature.id, BOX3D(cityobject.envelope) " + \
                    "FROM relief_feature JOIN cityobject ON relief_feature.id=cityobject.id"

        else:
            relief_gmlids = [n.get_gml_id() for n in reliefs]
            relief_gmlids_as_string = "('" + "', '".join(relief_gmlids) + "')"
            query = "SELECT relief_feature.id, BOX3D(cityobject.envelope) " + \
                    "FROM relief_feature JOIN cityobject ON relief_feature.id=cityobject.id" + \
                    "WHERE cityobject.gmlid IN " + relief_gmlids_as_string

        return query

    @staticmethod
    def sql_query_geometries(offset, reliefs_ids=None):
        """
        reliefs_ids is unused
        :return:
        """
        # cityobjects_ids contains ids of reliefs
        query = \
            "SELECT relief_feature.id, ST_AsBinary(ST_Multi(ST_Collect( " + \
            "ST_Translate(surface_geometry.geometry, " + \
            str(-offset[0]) + ", " + str(-offset[1]) + ", " + str(-offset[2]) + \
            ")))) " + \
            "FROM relief_feature JOIN relief_feat_to_rel_comp " + \
            "ON relief_feature.id=relief_feat_to_rel_comp.relief_feature_id " + \
            "JOIN tin_relief " + \
            "ON relief_feat_to_rel_comp.relief_component_id=tin_relief.id " + \
            "JOIN surface_geometry ON surface_geometry.root_id=tin_relief.surface_geometry_id " + \
            "GROUP BY relief_feature.id "

        return query
