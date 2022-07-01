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
PixelPoint = namedtuple("PixelPoint", "x y zoom")


class ConversionException(Exception):
    pass


def coordinate_to_tile_point(coordinate, zoom):
    ''' Convert 'Coordinate' to 'TilePoint' '''
    tile_point = TilePoint(
                    _coordinate_lon_to_tile_x(coordinate.lon, zoom),
                    _coordinate_lat_to_tile_y(coordinate.lat, zoom),
                    zoom)
    return tile_point


def tile_point_to_coordinate(tile_point):
    ''' Convert 'TilePoint' to 'Coordinate' '''
    coordinate = Coordinate(
                    _tile_x_to_coordinate_lon(tile_point.x, tile_point.zoom),
                    _tile_y_to_coordinate_lat(tile_point.y, tile_point.zoom))
    return coordinate


def coordinate_to_pixel_point(coordinate, zoom):
    ''' Convert 'Coordinate' to 'PixelPoint' '''

    pixel = PixelPoint(
        _coordinate_lon_to_pixel_x(coordinate.lon, zoom),
        _coordinate_lat_to_pixel_y(coordinate.lat, zoom),
        zoom,
    )

    return pixel


def pixel_point_to_coordinate(pixel_point):
    ''' Convert 'PixelPoint' to 'Coordinate' '''

    coordinate = Coordinate(
        _pixel_x_to_coordinate_lon(pixel_point.x, pixel_point.zoom),
        _pixel_y_to_coordinate_lat(pixel_point.y, pixel_point.zoom),
    )

    return coordinate


def tile_point_to_pixel_point(tile_point):
    ''' Convert 'TilePoint' to 'Coordinate' '''
    coordinate = tile_point_to_coordinate(tile_point)
    pixel = coordinate_to_pixel_point(coordinate, tile_point.zoom)

    return pixel


def pixel_point_to_tile_point(pixel_point):
    ''' Convert 'TilePoint' to 'Coordinate' '''
    coordinate = pixel_point_to_coordinate(pixel_point)
    pixel = coordinate_to_tile_point(coordinate, pixel_point.zoom)

    return pixel


def tile_reference(tile_point):
    ''' Truncate a TilePoint object fields (possilby floats) to tile reference values (floor integers). '''
    tile_ref = TilePoint(int(tile_point.x), int(tile_point.y), int(tile_point.zoom))
    return tile_ref    


def download_tile(tile_point, output_filename):
    # Truncate to integer tile coordinates
    tile_ref = tile_reference(tile_point)
    lon_tile = tile_ref.x
    lat_tile = tile_ref.y
    zoom = tile_ref.zoom
    logging.debug('run curl ' + ' '.join(['https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, lon_tile, lat_tile), '--output', output_filename]))
    sh.curl('https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, lon_tile, lat_tile), '--output', output_filename) # pylint: disable=E1101


# Coordinate to tile scale conversions

def _coordinate_lon_to_tile_x(lon_deg, zoom):
    if lon_deg > 180 or lon_deg < -180:
        raise ConversionException('Degrees beyond conversion range: %f' % lon_deg)
    n = 2.0 ** zoom
    xfloat = (lon_deg + 180.0) / 360.0 * n

    return xfloat


def _coordinate_lat_to_tile_y(lat_deg, zoom):
    if lat_deg > 85.05113 or lat_deg < -85.05113:
        raise ConversionException('Degrees beyond conversion range: %f' % lat_deg)
    n = 2.0 ** zoom
    lat_rad = math.radians(lat_deg)
    yfloat = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n

    return yfloat


def _tile_x_to_coordinate_lon(xtile, zoom):
    n = 2.0 ** zoom
    lon_deg = (xtile / n * 360) - 180.0
    return lon_deg


def _tile_y_to_coordinate_lat(ytile, zoom):
    n = 2.0 ** zoom
    lat_deg = math.degrees(math.atan(math.sinh((- (ytile / n * 2.0) + 1.0) * math.pi)))
    return lat_deg


# Coordinate to pixel scale conversions

def _coordinate_lon_to_pixel_x(lon_deg, zoom):
    xpixel = _coordinate_lon_to_tile_x(lon_deg, zoom) * 256
    return xpixel


def _coordinate_lat_to_pixel_y(lat_deg, zoom):
    ypixel = _coordinate_lat_to_tile_y(lat_deg, zoom) * 256
    return ypixel


def _pixel_x_to_coordinate_lon(xpix, zoom):
    xtile = xpix / 256
    lon_deg = _tile_x_to_coordinate_lon(xtile, zoom)
    return lon_deg


def _pixel_y_to_coordinate_lat(ypix, zoom):
    ytile = ypix / 256
    lat_deg = _tile_y_to_coordinate_lat(ytile, zoom)
    return lat_deg


# Tile to pixel scale conversions

def _tile_x_to_pixel_x(xtile, zoom):
    xpixel = xtile * 256
    return xpixel


def _tile_y_to_pixel_y(ytile, zoom):
    ypixel = ytile * 256
    return ypixel


def _pixel_x_to_tile_x(xpix, zoom):
    xtile = xpix / 256
    return xtile


def _pixel_y_to_tile_y(ypix, zoom):
    ytile = ypix / 256
    return ytile
