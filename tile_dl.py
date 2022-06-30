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


def markup_tile(lat_tile_float, lon_tile_float, tile_filename, markup_filename, color='blue'):

    im = Image.open(tile_filename)
    im = im.convert('RGB')

    dr = ImageDraw.Draw(im)
    line_color = ImageColor.getrgb(color)

    if lat_tile_float is not None:
        x_rem = lat_tile_float - math.floor(lat_tile_float)
        x_tile_offset = int(x_rem * 256)
        dr.line([(x_tile_offset, 0), (x_tile_offset, im.size[0])], fill=line_color, width=1)

    if lon_tile_float is not None:
        y_rem = lon_tile_float - math.floor(lon_tile_float)
        y_tile_offset = int(y_rem * 256)
        dr.line([(0, y_tile_offset), (im.size[1], y_tile_offset)], fill=line_color, width=1)

    im.save(markup_filename, 'PNG')


def main(args):
    logging.debug(args)
    lat_deg = float(args['--lat'])
    lon_deg = float(args['--long'])
    zoom = float(args['--zoom'])
    mark_loc = args['--mark-loc']

    coord = osm.Coordinate(lon_deg, lat_deg)
    tile = osm.coordinate_to_tile_point(coord, zoom)

    x_tile = int(tile.x)
    y_tile = int(tile.y)

    timestamp = int(time.time())
    tile_filename = '%d_%d_%d.%d.png' % (zoom, x_tile, y_tile, timestamp)
    markup_filename = '%d_%d_%d.%d.marked.png' % (zoom, x_tile, y_tile, timestamp)

    osm.download_tile(tile, tile_filename)

    if mark_loc:
        markup_tile(tile.x, tile.y, tile_filename, markup_filename, 'red')

    # Use "open" to display image for viewing
    sh.open(markup_filename) # pylint: disable=E1101


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))

