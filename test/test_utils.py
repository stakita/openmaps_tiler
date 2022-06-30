import sys
import os
  
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
    assert extents.lon_min == 1.0
    assert extents.lon_max == 9.0
    assert extents.lat_min == 1.0
    assert extents.lat_max == 9.0


    in_list = [
        {'lat': 151.20503342941282, 'lon': -33.870868842232625 },
        {'lat': 151.211802126524, 'lon': -33.85904467277486 },
    ]

    extents = utils.get_track_geo_extents(iter(in_list))

    assert extents.lon_min == -33.870868842232625
    assert extents.lon_max == -33.85904467277486
    assert extents.lat_min == 151.20503342941282
    assert extents.lat_max == 151.211802126524


def test_maximize_zoom():
    zoom_expected = 17

    in_list = [
        {'lat': 151.20503342941282, 'lon': -33.870868842232625 },
        {'lat': 151.211802126524, 'lon': -33.85904467277486 },
    ]
    output_x_px = output_y_px = 1000
    extents = utils.get_track_geo_extents(iter(in_list))

    zoom = utils.maximize_zoom(extents, output_x_px, output_y_px)

    assert zoom == zoom_expected
    