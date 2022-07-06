# Utility classes and functions supporting the top-level scripts
#
# 2022-06-29
# Simon M Takita <smtakita@gmail.com>
#
# Released under GNU GENERAL PUBLIC LICENSE v3. (Use at your own risk)
#
import sys
from collections import namedtuple
import logging

from lib import openstreetmaps as osm  # pylint: disable=E0401

try:
    from PIL import Image
    # from PIL import ImageDraw, ImageColor, ImageFont
except ImportError as e:
    installs = ['Pillow']
    sys.stderr.write('Error: %s\nTry:\n    pip install --user %s\n' % (e, ' '.join(installs)))
    sys.exit(1)


logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)-s')
log = logging.getLogger(__name__)


class ConversionException(Exception):
    pass


class CoordinateExtents:

    def __init__(self, coord1, coord2):
        if coord1.lat > coord2.lat:
            self.lat_hi = coord1.lat
            self.lat_lo = coord2.lat 
        else:
            self.lat_hi = coord2.lat
            self.lat_lo = coord1.lat
        if coord1.lon > coord2.lon:
            self.lon_hi = coord1.lon
            self.lon_lo = coord2.lon
        else:
            self.lon_hi = coord2.lon
            self.lon_lo = coord1.lon             
        self._hi = osm.Coordinate(self.lon_hi, self.lat_hi)
        self._lo = osm.Coordinate(self.lon_lo, self.lat_lo)


    def hi(self):
        return self._hi


    def lo(self):
        return self._lo


    def __repr__(self):
        return '<%s _lo:%s, _hi:%s>' % (self.__class__.__name__, repr(self._lo), repr(self._hi))


    def __str__(self):
        return '%s(_lo:%s, _hi:%s)' % (self.__class__.__name__, repr(self._lo), repr(self._hi))


    def to_tile_extents(self, zoom):
        tile_point1 = osm.coordinate_to_tile_point(self._hi, zoom)
        tile_point2 = osm.coordinate_to_tile_point(self._lo, zoom)
        return TileExtents(tile_point1, tile_point2)


    def to_pixel_extents(self, zoom):
        pixel_point1 = osm.coordinate_to_pixel_point(self._hi, zoom)
        pixel_point2 = osm.coordinate_to_pixel_point(self._lo, zoom)
        return PixelExtents(pixel_point1, pixel_point2)


class TileExtents:

    def __init__(self, tile_point1, tile_point2):
        if tile_point1.zoom != tile_point2.zoom:
            raise ConversionException('Mismatch in zoom factors')
        self.zoom = tile_point1.zoom

        if tile_point1.x > tile_point2.x:
            self.x_hi = tile_point1.x
            self.x_lo = tile_point2.x
        else:
            self.x_hi = tile_point2.x
            self.x_lo = tile_point1.x

        if tile_point1.y > tile_point2.y:
            self.y_hi = tile_point1.y
            self.y_lo = tile_point2.y
        else:
            self.y_hi = tile_point2.y
            self.y_lo = tile_point1.y
        self._hi = osm.TilePoint(self.x_hi, self.y_hi, self.zoom)
        self._lo = osm.TilePoint(self.x_lo, self.y_lo, self.zoom)


    def hi(self):
        return self._hi


    def lo(self):
        return self._lo


class PixelExtents:

    def __init__(self, pixel_point1, pixel_point2):
        if pixel_point1.zoom != pixel_point2.zoom:
            raise ConversionException('Mismatch in zoom factors')
        self.zoom = pixel_point1.zoom

        if pixel_point1.x > pixel_point2.x:
            self.x_hi = pixel_point1.x
            self.x_lo = pixel_point2.x
        else:
            self.x_hi = pixel_point2.x
            self.x_lo = pixel_point1.x

        if pixel_point1.y > pixel_point2.y:
            self.y_hi = pixel_point1.y
            self.y_lo = pixel_point2.y
        else:
            self.y_hi = pixel_point2.y
            self.y_lo = pixel_point1.y
        self._hi = osm.PixelPoint(self.x_hi, self.y_hi, self.zoom)
        self._lo = osm.PixelPoint(self.x_lo, self.y_lo, self.zoom)


    def hi(self):
        return self._hi


    def lo(self):
        return self._lo


    def to_coordinate_extents(self, zoom):
        coordinate1 = osm.pixel_point_to_coordinate(self._hi)
        coordinate2 = osm.pixel_point_to_coordinate(self._lo)
        return CoordinateExtents(coordinate1, coordinate2)


def get_track_geo_extents(points_iter):
    ''' Calculate the maximum and minimum values of lon and lat for the track points '''

    point = next(points_iter)
    lat_max = point['lat']
    lat_min = point['lat']
    lon_max = point['lon']
    lon_min = point['lon']

    for point in points_iter:
        if point['lat'] < lat_min:
            lat_min = point['lat']
        if point['lat'] > lat_max:
            lat_max = point['lat']
        if point['lon'] < lon_min:
            lon_min = point['lon']
        if point['lon'] > lon_max:
            lon_max = point['lon']

    coord_lo = osm.Coordinate(lon_min, lat_min)
    coord_hi = osm.Coordinate(lon_max, lat_max)
    return CoordinateExtents(coord_lo, coord_hi)


def maximize_zoom(track_extents, output_x_px, output_y_px, boundary_pixels=20, zoom_max=19):
    log.debug('maximize_zoom - track_extents: %s, output: (%d, %d)' % (repr(track_extents), output_x_px, output_y_px))

    # Loop until either x or y has exceeded zoom for given output dimensions - take previous zoom
    for zoom in range(zoom_max + 1):
        pixel_extents = track_extents.to_pixel_extents(zoom)
        pixel_lo = pixel_extents.lo()
        pixel_hi = pixel_extents.hi()

        x_size_pixel = pixel_hi.x - pixel_lo.x
        y_size_pixel = pixel_hi.y - pixel_lo.y
        if (x_size_pixel + (2 * boundary_pixels)) >= output_x_px or (y_size_pixel + (2 * boundary_pixels)) >= output_y_px:
            break

    zoom_target = zoom - 1 # last zoom value
    log.debug('--> zoom_target: %d' % (zoom_target))
    pixel_extents = track_extents.to_pixel_extents(zoom_target)
    pixel_lo = pixel_extents.lo()
    pixel_hi = pixel_extents.hi()
    x_size_pixel = pixel_hi.x - pixel_lo.x
    y_size_pixel = pixel_hi.y - pixel_lo.y
    log.debug('--> pixel_lo: %s' % repr(pixel_lo))
    log.debug('--> pixel_hi: %s' % repr(pixel_hi))
    log.debug('--> x_size_pixel:  %f' % (x_size_pixel))
    log.debug('--> y_size_pixel:  %f' % (y_size_pixel))

    # Calculate bounding box extents
    pixel_boundary_lo = osm.PixelPoint(pixel_lo.x - boundary_pixels, pixel_lo.y - boundary_pixels, zoom_target)
    pixel_boundary_hi = osm.PixelPoint(pixel_hi.x + boundary_pixels, pixel_hi.y + boundary_pixels, zoom_target)

    coordinate_boundary_lo = osm.pixel_point_to_coordinate(pixel_boundary_lo)
    coordinate_boundary_hi = osm.pixel_point_to_coordinate(pixel_boundary_hi)

    boundary_extents = CoordinateExtents(coordinate_boundary_lo, coordinate_boundary_hi)

    return zoom_target, boundary_extents


def join_images_horizontal(im1, im2):
    dst = Image.new('RGB', (im1.width + im2.width, im1.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (im1.width, 0))
    return dst


def join_images_vertical(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (0, im1.height))
    return dst


