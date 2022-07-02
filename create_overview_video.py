#!/usr/bin/env python3
'''
create_overview_video.py - Create track overview video from GPX data

Usage:
  zoom.py <gpx-data> [--output=<filename>] [--tile-cache=<directory>]

Options:
  -h --help                 Show this screen.
  --output=<filename>       Output filename [default: output.avi].
  --tile-cache=<directory>  Tile cache directory [default: tiles].
'''
# TODO: other options:
#   pixels_x = output x size in pixels
#   pixels_y = output y size in pixels
#   fps
#   tstart
#   tstop
import sys
import logging
import os

from lib import openstreetmaps as osm
from lib import gpx
from lib import utils

try:
    from docopt import docopt
    from PIL import Image
    from PIL import ImageDraw, ImageColor, ImageFont
except ImportError as e:
    installs = ['docopt', 'Pillow']
    sys.stderr.write('Error: %s\nTry:\n    pip install --user %s\n' % (e, ' '.join(installs)))
    sys.exit(1)


log = logging.getLogger(__name__)


def to_coordinate(gpx_point):
    return osm.Coordinate(gpx_point['lon'], gpx_point['lat'])


def calculate_best_zoom_factor(points_iter, margin_px, output_x_px, output_y_px):
    track_extents = utils.get_track_geo_extents(points_iter)
    zoom, boundary_extents = utils.maximize_zoom(track_extents, output_x_px, output_y_px, margin_px)
    return zoom, boundary_extents


def calculate_adjusted_boundary_extents(boundary_extents, zoom_factor, margin_px, output_x_px, output_y_px):
    ''' Calculate boundary coordinates and scaling factor to match output video dimensions '''
    pixel_extents = boundary_extents.to_pixel_extents(zoom_factor)

    track_size_x_px = pixel_extents.hi().x - pixel_extents.lo().x
    track_size_y_px = pixel_extents.hi().y - pixel_extents.lo().y

    track_center_x_px = (pixel_extents.hi().x + pixel_extents.lo().x) / 2
    track_center_y_px = (pixel_extents.hi().y + pixel_extents.lo().y) / 2

    scale_x = (output_x_px - (2 * margin_px)) / track_size_x_px
    scale_y = (output_y_px - (2 * margin_px)) / track_size_y_px

    log.info('scale_x: %f' % scale_x)
    log.info('scale_y: %f' % scale_y)

    scale_factor = min(scale_x, scale_y)

    log.info('scale_factor: %f' % scale_factor)

    boundary_x_px_lo = track_center_x_px - (output_x_px / 2) / scale_factor
    boundary_x_px_hi = track_center_x_px + (output_x_px / 2) / scale_factor
    boundary_y_px_lo = track_center_y_px - (output_y_px / 2) / scale_factor
    boundary_y_px_hi = track_center_y_px + (output_y_px / 2) / scale_factor

    pixel_lo = osm.PixelPoint(boundary_x_px_lo, boundary_y_px_lo, zoom_factor)
    pixel_hi = osm.PixelPoint(boundary_x_px_hi, boundary_y_px_hi, zoom_factor)

    adjusted_pixel_extents = utils.PixelExtents(pixel_lo, pixel_hi)

    return adjusted_pixel_extents.to_coordinate_extents(zoom_factor), scale_factor


def generate_base_background_image(boundary_coord_extents, track_extents, zoom, tile_directory):
    # Download all tiles coverying boundary area

    tile_extents = boundary_coord_extents.to_tile_extents(zoom)

    tile_lo = tile_extents.lo()
    tile_hi = tile_extents.hi()

    tile_ref_lo = osm.tile_reference(tile_lo)
    tile_ref_hi = osm.tile_reference(tile_hi)

    file_map = {}

    log.debug('tile_extents: %r' % tile_extents)

    for lon_tile in range(tile_ref_lo.x, tile_ref_hi.x + 1):
        for lat_tile in range(tile_ref_lo.y, tile_ref_hi.y + 1):
            key = (lon_tile, lat_tile)
            tile = osm.TilePoint(lon_tile, lat_tile, zoom)
            output_filename = tile_directory +'/' +'tile_%06d_%06d_%02d.png' % (tile.x, tile.y, tile.zoom)
            file_map[key] = output_filename
            if not os.path.exists(output_filename):
                osm.download_tile(tile, output_filename)

    log.debug('file_map: ' + repr(file_map))

    # Combine into single image
    for lon_tile in range(tile_ref_lo.x, tile_ref_hi.x + 1):
        for lat_tile in range(tile_ref_lo.y, tile_ref_hi.y + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            im = Image.open(file_map[key]).convert('RGB')

            if True:
                # grid lines
                tile_current = osm.TilePoint(lon_tile, lat_tile, zoom)
                # tile_offset = osm.TilePoint(lon_tile + 1, lat_tile + 1, zoom)

                geo_current = osm.tile_point_to_coordinate(tile_current)
                # geo_offset = osm.tile_point_to_coordinate(tile_offset)

                dr = ImageDraw.Draw(im)
                color = ImageColor.getrgb('brown')
                dr.line([(0, 0), (0, 255)], fill=color, width=1)
                dr.line([(0, 0), (255, 0)], fill=color, width=1)

                font = ImageFont.load_default()

                lon_deg_min = geo_current.lon
                lat_deg_min = geo_current.lat
                # lon_deg_max = geo_offset.lon
                # lat_deg_max = geo_offset.lat
                dr.text([(127, 10)], '%f' % lat_deg_min, font=font, fill=color)
                dr.text([(10, 127)], '%f' % lon_deg_min, font=font, fill=color)

                color = ImageColor.getrgb('black')

                # if xbtl > lon_tile and xbtl < lon_tile + 1:
                #     print('xbtl:', xbtl)
                #     print('lon_tile:', lon_tile)
                #     x_offset = (xbtl - math.floor(xbtl)) * 256
                #     dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)

                # if  ybtl > lat_tile and ybtl < lat_tile + 1:
                #     print('ybtl:', ybtl)
                #     print('lat_tile:', lat_tile)
                #     y_offset = (ybtl - math.floor(ybtl)) * 256
                #     dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

                # if xbth > lon_tile and xbth < lon_tile + 1:
                #     print('xbth:', xbth)
                #     print('lon_tile:', lon_tile)
                #     x_offset = (xbth - math.floor(xbth)) * 256
                #     dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)

                # if ybth > lat_tile and ybth < lat_tile + 1:
                #     print('ybth:', ybth)
                #     print('lat_tile:', lat_tile)
                #     y_offset = (ybth - math.floor(ybth)) * 256
                #     dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

                # color = ImageColor.getrgb('red')

                # if xesl > lon_tile and xesl < lon_tile + 1:
                #     print('xesl:', xesl)
                #     print('lon_tile:', lon_tile)
                #     x_offset = (xesl - math.floor(xesl)) * 256
                #     dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)

                # if  yesl > lat_tile and yesl < lat_tile + 1:
                #     print('yesl:', yesl)
                #     print('lat_tile:', lat_tile)
                #     y_offset = (yesl - math.floor(yesl)) * 256
                #     dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

                # if xesh > lon_tile and xesh < lon_tile + 1:
                #     print('xesh:', xesh)
                #     print('lon_tile:', lon_tile)
                #     x_offset = (xesh - math.floor(xesh)) * 256
                #     dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)

                # if yesh > lat_tile and yesh < lat_tile + 1:
                #     print('yesh:', yesh)
                #     print('lat_tile:', lat_tile)
                #     y_offset = (yesh - math.floor(yesh)) * 256
                #     dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

            im.save(file_map[key])

    im_full = None
    for lon_tile in range(tile_ref_lo.x, tile_ref_hi.x + 1):
        im_row = None
        for lat_tile in range(tile_ref_lo.y, tile_ref_hi.y + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            if im_row is None:
                im_row = Image.open(file_map[key]).convert('RGB')
            else:
                im_join = Image.open(file_map[key]).convert('RGB')
                im_row = utils.join_images_vertical(im_row, im_join)

        if im_full is None:
            im_full = im_row
        else:
            im_full = utils.join_images_horizontal(im_full, im_row)

    output_file = 'bozo'
    im_full.save(output_file + '.raw.png')


def main(args):
    gpx_filename = args['<gpx-data>']
    output_file = args['--output']
    tile_directory = args['--tile-cache']

    margin_pixels = 10
    pixels_x = 1022
    pixels_y = 1022

    log.info('gpx_filename: %s' % gpx_filename)
    log.info('output_file:  %s' % output_file)

    # Get GPX data
    with open(gpx_filename) as fd:
        gpx_raw = fd.read()
    gpx_data = gpx.Gpx(gpx_raw)

    # Calculate best zoom factor
    zoom, boundary_extents = calculate_best_zoom_factor(gpx_data.all_points(), margin_pixels, pixels_x, pixels_y)

    # Generate base background image
    generate_base_background_image(boundary_extents, zoom, tile_directory)

    # Generate background image
        # Get track bounding points
        # Determine best zoom factor based on bounding expansion
        # Get expanded coordinate bounds
        # Download tiles in range
        # Stitch to single output image
        # Return image and pixel conversion parameters

    # Draw track points (image, points)
        # Draw points

    # Generate video
        # Load background image




if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))

