from collections import namedtuple
import logging

from lib import openstreetmaps as osm

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)-s')
log = logging.getLogger(__name__)

# Coordinate = namedtuple("Coordinate", "lon lat")
# TilePoint = namedtuple("TilePoint", "x y zoom")
# PixelPoint = namedtuple("PixelPoint", "x y")
CoordinateExtents = namedtuple("CoordinateExtents", "lon_max lon_min lat_max lat_min")


def calculate_best_zoom_factor(points_list, margin_px, output_x_px, output_y_px, ):
    extents = get_track_geo_extents(points_list)
    
    pass


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

    return CoordinateExtents(lon_max, lon_min, lat_max, lat_min)


def maximize_zoom(track_extents, output_x_px, output_y_px, boundary_pixels=20, zoom_max=19):
    log.info('maximize_zoom - track_extents: %s, output: (%d, %d)' % (repr(track_extents), output_x_px, output_y_px))

    # Bounding corners of the bounding box in coordinate space
    coord_lo = osm.Coordinate(track_extents.lat_min, track_extents.lon_min)
    coord_hi = osm.Coordinate(track_extents.lat_max, track_extents.lon_max)

    # Loop until either x or y has exceeded zoom for given output dimensions - take previous zoom
    for zoom in range(zoom_max + 1):
        pixel_lo = osm.coordinate_to_pixel_point(coord_lo, zoom)
        pixel_hi = osm.coordinate_to_pixel_point(coord_hi, zoom)

        x_size_pixel = pixel_hi.x - pixel_lo.x
        y_size_pixel = pixel_hi.y - pixel_lo.y
        if (x_size_pixel + (2 * boundary_pixels)) >= output_x_px or (y_size_pixel + (2 * boundary_pixels)) >= output_y_px:
            break

    zoom_target = zoom - 1 # last zoom value
    log.info('--> zoom_target: %d' % (zoom_target))
    pixel_lo = osm.coordinate_to_pixel_point(coord_lo, zoom_target)
    pixel_hi = osm.coordinate_to_pixel_point(coord_hi, zoom_target)
    x_size_pixel = pixel_hi.x - pixel_lo.x
    y_size_pixel = pixel_hi.y - pixel_lo.y
    log.info('--> pixel_lo: %s' % repr(pixel_lo))
    log.info('--> pixel_hi: %s' % repr(pixel_hi))
    log.info('--> x_size_pixel:  %f' % (x_size_pixel))
    log.info('--> y_size_pixel:  %f' % (y_size_pixel))

    return zoom_target
