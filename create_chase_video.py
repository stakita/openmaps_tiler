#!/usr/bin/env python3
'''
create_chase_video.py - Create traak chase video from GPX data

Usage:
  create_chase_video.py <gpx-data> <zoom-factor> [--output=<filename>] [--tile-cache=<directory>] [--viewport-x=<pixels>] [--viewport-y=<pixels>]

Options:
  -h --help                 Show this screen.
  --output=<filename>       Output filename [default: output.avi].
  --tile-cache=<directory>  Tile cache directory [default: tiles].
  --viewport-x=<pixels>     Output video viewport x dimension pixels [default: 1022].
  --viewport-y=<pixels>     Output video viewport x dimension pixels [default: 1022].
'''
# TODO: other options:
#   pixels_x = output x size in pixels
#   pixels_y = output y size in pixels
#   fps
#   tstart
#   tstop
#   --grid-lines
import sys
import logging
import os
import math
import copy
import shutil
from collections import namedtuple

from lib import openstreetmaps as osm
from lib import gpx
from lib import utils

try:
    from docopt import docopt
    from PIL import Image
    from PIL import ImageDraw, ImageColor, ImageFont
    from cv2 import cv2
except ImportError as e:
    installs = ['docopt', 'Pillow', 'opencv-python']
    sys.stderr.write('Error: %s\nTry:\n    pip install --user %s\n' % (e, ' '.join(installs)))
    sys.exit(1)


ViewportOffsets = namedtuple('Coordinate', 'x_lo y_lo x_hi y_hi')


log = logging.getLogger(__name__)


def load_gpx_data(gpx_filename):
    with open(gpx_filename) as fd:
        gpx_raw = fd.read()
    gpx_data = gpx.Gpx(gpx_raw)
    return gpx_data


def download_tiles(gpx_data, zoom_factor, viewport_offsets, tile_directory):
    file_map = {}
    
    for coordinate in map(lambda p: osm.Coordinate(p['lon'], p['lat']), gpx_data.all_points()):
        pixel_point = osm.coordinate_to_pixel_point(coordinate, zoom_factor)

        # Calculate pixel offset bounding points
        pixel_lo = osm.PixelPoint(
                        pixel_point.x + viewport_offsets.x_lo,
                        pixel_point.y + viewport_offsets.y_lo,
                        zoom_factor
        )
        pixel_hi = osm.PixelPoint(
                        pixel_point.x + viewport_offsets.x_hi,
                        pixel_point.y + viewport_offsets.y_hi,
                        zoom_factor
        )
        # Convert to tile references
        tile_lo = osm.tile_reference(osm.pixel_point_to_tile_point(pixel_lo))
        tile_hi = osm.tile_reference(osm.pixel_point_to_tile_point(pixel_hi))

        # Iterate through all tiles in the bounded region
        for x in range(tile_lo.x, tile_hi.x + 1):
            for y in range(tile_lo.y, tile_hi.y + 1):
                key = (x, y)
                tile = osm.TilePoint(x, y, zoom_factor)
                output_filename = get_tile_path(tile, tile_directory)
                file_map[key] = output_filename
                if not os.path.exists(output_filename):
                    osm.download_tile(tile, output_filename)

    log.info('file_map: %r' % file_map)


def get_tile_path(tile_reference, tile_directory):
    return tile_directory +'/' +'tile_%06d_%06d_%02d.png' % (tile_reference.x, tile_reference.y, tile_reference.zoom)


def annotate_tiles(gpx_data, zoom_factor, tile_directory):

    tile_set = {}

    # Determine tiles have tracks on them    
    for coordinate in map(lambda p: osm.Coordinate(p['lon'], p['lat']), gpx_data.all_points()):
        tile_ref = osm.tile_reference(osm.coordinate_to_tile_point(coordinate, zoom_factor))
        if tile_ref not in tile_set:
            tile_set[tile_ref] = []

    print('tile_set: %r' % tile_set)

    # Collect all points from the track contained in that tile
    for tile in tile_set:
        for coordinate in map(lambda p: osm.Coordinate(p['lon'], p['lat']), gpx_data.all_points()):
            location_tile = osm.tile_reference(osm.coordinate_to_tile_point(coordinate, zoom_factor))
            location_pixel = osm.pixel_point_round(osm.coordinate_to_pixel_point(coordinate, zoom_factor))
            if location_tile == tile:
                if location_pixel not in tile_set[tile]:
                    tile_set[tile].append(location_pixel)

    # print('tile_set:')
    import pprint
    pprint.pprint(tile_set)

    # Process each tile drawing contained points onto tile
    for tile in tile_set:
        print('processing tile: %s' % repr(tile))
        tile_pixel_ref = osm.tile_point_to_pixel_point(tile)
        image_track_pixel_coords = list(map(lambda q: ((q.x - tile_pixel_ref.x), (q.y - tile_pixel_ref.y)), tile_set[tile]))
        tile_filename = get_tile_path(tile, tile_directory)

        print('image_track_pixel_coords: %r' % image_track_pixel_coords)

        im_tile = Image.open(tile_filename).convert('RGB')
        draw_track_points(im_tile, image_track_pixel_coords)
        im_tile.save(tile_filename)


def draw_track_points(im_background, image_pixel_coords):
    color = ImageColor.getrgb('blue')
    dr = ImageDraw.Draw(im_background)
    dr.point(image_pixel_coords, fill=color)

    return im_background


def main(args):
    gpx_filename = args['<gpx-data>']
    zoom_factor = int(args['<zoom-factor>'])
    output_file = args['--output']
    tile_directory = args['--tile-cache']
    pixels_x = int(args['--viewport-x'])
    pixels_y = int(args['--viewport-y'])

    output_temp_file = output_file + '_'

    log.info('gpx_filename: %s' % gpx_filename)
    log.info('output_file:  %s' % output_file)
    log.info('viewport dimensions:: (%d, %d)' % (pixels_x, pixels_y))

    # Setup: Pre calculations
    offsets = ViewportOffsets(
                -(pixels_x / 2),
                -(pixels_y / 2),
                (pixels_x / 2),
                (pixels_y / 2)
    )

    # Setup: Load GPX data
    gpx_data = load_gpx_data(gpx_filename)

    # Download tiles
    download_tiles(gpx_data, zoom_factor, offsets, tile_directory)

    # Annotate tiles
    annotate_tiles(gpx_data, zoom_factor, tile_directory)

    # Compose video

    # Copy over temp file to final filename
    # shutil.move(output_temp_file, output_file)


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))

