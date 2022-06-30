#!/usr/bin/env python3
'''
tile_dl.py - Tile downloader

Given a lat, long, zoom-factor, will download tile from openstreetmaps.org at the given zoom factor that contains the given location.

Usage:
  tile_dl.py --lat=<latitude> --long=<longitude> --zoom=<zoom> [--mark-loc]

Options:
  -h --help             Show this screen.
  --lat=<latitude>      Latitude of point in tile.
  --long=<longitude>    Longitude of point in tile.
  --zoom=<zoom>         Zoom factor.
  --mark-loc            Mark specified location with lat/lon lines.
'''

import math
import sys
import os
import time
import logging
from collections import namedtuple
from lib import openstreetmaps as osm

try:
    import sh
    from docopt import docopt
    from PIL import Image
    from PIL import ImageDraw, ImageColor
except ImportError as e:
    installs = ['sh', 'docopt', 'Pillow']
    sys.stderr.write('Error: %s\nTry:\n    pip install --user %s\n' % (e, ' '.join(installs)))
    sys.exit(1)


logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)-s')


def markup_tile(tile_point, tile_filename, markup_filename, color='blue'):

    im = Image.open(tile_filename)
    im = im.convert('RGB')

    dr = ImageDraw.Draw(im)
    line_color = ImageColor.getrgb(color)

    pixel_point = osm.tile_point_to_pixel_point(tile_point)

    tile_zero_point = osm.tile_reference(tile_point)
    pixel_zero_ref = osm.tile_point_to_pixel_point(tile_zero_point)

    x_offset = pixel_point.x - pixel_zero_ref.x
    y_offset = pixel_point.y - pixel_zero_ref.y

    dr.line([(x_offset, 0), (x_offset, im.size[0])], fill=line_color, width=1)

    dr.line([(0, y_offset), (im.size[1], y_offset)], fill=line_color, width=1)

    im.save(markup_filename, 'PNG')


def main(args):
    logging.debug(args)
    lat_deg = float(args['--lat'])
    lon_deg = float(args['--long'])
    zoom = float(args['--zoom'])
    mark_loc = args['--mark-loc']

    coord = osm.Coordinate(lon_deg, lat_deg)
    tile = osm.coordinate_to_tile_point(coord, zoom)
    print('tile:  ' + repr(tile))
    pixel = osm.coordinate_to_pixel_point(coord, zoom)
    print('pixel: ' + repr(pixel))

    x_tile = int(tile.x)
    y_tile = int(tile.y)

    timestamp = int(time.time())
    tile_filename = '%d_%d_%d.%d.png' % (zoom, x_tile, y_tile, timestamp)
    markup_filename = '%d_%d_%d.%d.marked.png' % (zoom, x_tile, y_tile, timestamp)

    osm.download_tile(tile, tile_filename)

    if mark_loc:
        markup_tile(tile, tile_filename, markup_filename, 'red')

    # Use "open" to display image for viewing
    sh.open(markup_filename) # pylint: disable=E1101


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))

