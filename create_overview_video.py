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


def generate_base_background_image(boundary_coord_extents, zoom, tile_directory):
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

