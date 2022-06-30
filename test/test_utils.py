import sys
import os
  
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib import utils  # pylint: disable=E0401


def test_get_track_geo_extents():
    in_list = [
        {
            'lat': 1.0,
            'lon': 1.0,
        },
        {
            'lat': 9.0,
            'lon': 9.0,
        },
        {
            'lat': 5.0,
            'lon': 5.0,
        },
        {
            'lat': 5.0,
            'lon': 5.0,
        },        
    ]
    extents = utils.get_track_geo_extents(iter(in_list))
    assert extents.lat_min == 1.0
    assert extents.lat_max == 9.0
    assert extents.lat_min == 1.0
    assert extents.lat_max == 9.0
    