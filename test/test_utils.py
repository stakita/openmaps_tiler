import sys
import os
import math
  
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib import utils  # pylint: disable=E0401


def test_get_track_geo_extents():
    in_list = [
        {'lat': 1.0, 'lon': 1.0 },
        {'lat': 9.0, 'lon': 1.0 },
        {'lat': 5.0, 'lon': 5.0 },
        {'lat': 1.0, 'lon': 9.0 },
    ]
    extents = utils.get_track_geo_extents(iter(in_list))
    assert math.isclose(extents.lo().lon, 1.0)
    assert math.isclose(extents.hi().lon, 9.0)
    assert math.isclose(extents.lo().lat, 1.0)
    assert math.isclose(extents.hi().lat, 9.0)


    in_list = [
        {'lat': -33.870868842232625, 'lon': 151.20503342941282 },
        {'lat': -33.85904467277486, 'lon': 151.211802126524 },
    ]

    extents = utils.get_track_geo_extents(iter(in_list))

    assert math.isclose(extents.lo().lat, -33.870868842232625)
    assert math.isclose(extents.hi().lat, -33.85904467277486)
    assert math.isclose(extents.lo().lon, 151.20503342941282)
    assert math.isclose(extents.hi().lon, 151.211802126524)


def test_maximize_zoom():
    zoom_expected = 16

    in_list = [
        {'lat': -33.870868842232625, 'lon': 151.20503342941282 },
        {'lat': -33.85904467277486, 'lon': 151.211802126524 },
    ]
    output_x_px = output_y_px = 1000
    extents = utils.get_track_geo_extents(iter(in_list))

    zoom, boundary_extents = utils.maximize_zoom(extents, output_x_px, output_y_px)

    assert zoom == zoom_expected
    assert math.isclose(boundary_extents.lo().lon, 151.20460427597044)
    assert math.isclose(boundary_extents.lo().lat, -33.87122516577023)
    assert math.isclose(boundary_extents.hi().lon, 151.21223127996637)
    assert math.isclose(boundary_extents.hi().lat, -33.85868829839835)


# TODO: add tests: extents classes