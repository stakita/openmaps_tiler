#!/usr/bin/env python3
#
# 2022-06-29
# Simon M Takita <smtakita@gmail.com>
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
#

import sys
import math
from collections import namedtuple
import logging

try:
    import sh
except ImportError as e:
    installs = ['sh']
    sys.stderr.write('Error: %s\nTry:\n    pip install --user %s\n' % (e, ' '.join(installs)))
    sys.exit(1)

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)-s')


Coordinate = namedtuple("Coordinate", "lon lat")
TilePoint = namedtuple("TilePoint", "x y zoom")
PixelPoint = namedtuple("PixelPoint", "x y")


def coordinate_to_tile_point(coordinate, zoom):
    ''' Convert 'Coordinate' type to 'TilePoint' based on supplied zoom factor '''
    tile_point = TilePoint(_scale_lon_to_zoom(coordinate.lon, zoom), _scale_lat_to_zoom(coordinate.lat, zoom), zoom)
    return tile_point


def tile_instance(tile_point):
    ''' Truncate a TilePoint object fields (possilby floats) to tile reference values (floor integers). '''
    tile_ref = TilePoint(int(tile_point.x), int(tile_point.y), int(tile_point.zoom))
    return tile_ref    


def get_tile(lat_tile, lon_tile, zoom, output_filename):
    logging.debug('run curl ' + ' '.join(['https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, lon_tile, lat_tile), '--output', output_filename]))
    sh.curl('https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, lon_tile, lat_tile), '--output', output_filename) # pylint: disable=E1101


def download_tile(tile_point, output_filename):
    # Truncate to integer tile coordinates
    tile_ref = tile_instance(tile_point)
    lon_tile = tile_ref.x
    lat_tile = tile_ref.y
    zoom = tile_ref.zoom
    logging.debug('run curl ' + ' '.join(['https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, lon_tile, lat_tile), '--output', output_filename]))
    sh.curl('https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, lon_tile, lat_tile), '--output', output_filename) # pylint: disable=E1101


def _scale_lat_to_zoom(lat_deg, zoom):
    ''' Scaling of lattitude value to tile coordinate based on zoom '''
    n = 2.0 ** zoom
    lat_rad = math.radians(lat_deg)
    lat_scale_float = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n

    return lat_scale_float


def _scale_lon_to_zoom(lon_deg, zoom):
    ''' Scaling of longitude value to tile coordinate based on zoom '''
    n = 2.0 ** zoom
    long_scale_float = (lon_deg + 180.0) / 360.0 * n

    return long_scale_float


