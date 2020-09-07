#!/usr/bin/env python3
'''
tile_dl.py - Tile downloader

Usage:
  tile_dl.py --lat=<latitude> --long=<longitude> --zoom=<zoom> [--line-lat=<lat>] [--line-long=<long>] [--mark-loc]

Options:
  -h --help             Show this screen.
  --lat=<latitude>      Latitude of point in tile.
  --long=<longitude>    Longitude of point in tile.
  --zoom=<zoom>         Zoom factor.
  --line-lat=<lat>      Latitude to draw line.
  --line-long=<long>    Longitude to draw line.
  --mark-loc            Mark specified location.
'''

import math
import sys
import os
import time
import logging

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)-s')

try:
    import sh
except ImportError as e:
    sys.stderr.write('Error: %s\nTry:\n    pip install --user sh\n' % e)
    sys.exit(1)

try:
    from docopt import docopt
except ImportError as e:
    sys.stderr.write('Error: %s\nTry:\n    pip install --user docopt\n' % e)
    sys.exit(1)

try:
    from PIL import Image
    from PIL import ImageDraw, ImageColor
except ImportError as e:
    sys.stderr.write('Error: %s\nTry:\n    pip install --user Pillow\n' % e)
    sys.exit(1)


def scale_lat_to_zoom(lat_deg, zoom):
    n = 2.0 ** zoom
    lat_rad = math.radians(lat_deg)
    lat_scale_float = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n

    return lat_scale_float


def scale_lon_to_zoom(lon_deg, zoom):
    n = 2.0 ** zoom
    long_scale_float = (lon_deg + 180.0) / 360.0 * n

    return long_scale_float


def scale_to_zoom(lat_deg, lon_deg, zoom):
    long_scale_float = scale_lon_to_zoom(lon_deg, zoom)
    lat_scale_float = scale_lat_to_zoom(lat_deg, zoom)

    return long_scale_float, lat_scale_float


def get_tile(lat_tile, lon_tile, zoom, output_filename):
    print('run curl ' + ' '.join(['https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, lon_tile, lat_tile), '--output', output_filename]))
    sh.curl('https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, lon_tile, lat_tile), '--output', output_filename)
    # sh.open(output_filename)


def markup_tile(lat_tile_float, lon_tile_float, tile_filename, markup_filename, color='blue'):

    im = Image.open(tile_filename)
    im = im.convert('RGB')

    dr = ImageDraw.Draw(im)
    line_color = ImageColor.getrgb(color)

    if lat_tile_float is not None:
        x_rem = lat_tile_float - math.floor(lat_tile_float)
        x_tile_offset = int(x_rem * 256)
        dr.line([(x_tile_offset, 0), (x_tile_offset, im.size[0])], fill=color, width=1)

    if lon_tile_float is not None:
        y_rem = lon_tile_float - math.floor(lon_tile_float)
        y_tile_offset = int(y_rem * 256)
        dr.line([(0, y_tile_offset), (im.size[1], y_tile_offset)], fill=color, width=1)

    im.save(markup_filename, 'PNG')


def main(args):
    logging.debug(args)
    lat_deg = float(args['--lat'])
    lon_deg = float(args['--long'])
    zoom = float(args['--zoom'])
    line_latitude = None if args['--line-lat'] is None else float(args['--line-lat'])
    line_longitude = None if args['--line-long'] is None else float(args['--line-long'])
    mark_loc = args['--mark-loc']

    long_tile_float, lat_tile_float = scale_to_zoom(lat_deg, lon_deg, zoom)

    x_tile = int(long_tile_float)
    y_tile = int(lat_tile_float)

    timestamp = int(time.time())
    tile_filename = '%d_%d_%d.%d.png' % (zoom, x_tile, y_tile, timestamp)
    markup_filename = '%d_%d_%d.%d.marked.png' % (zoom, x_tile, y_tile, timestamp)

    get_tile(y_tile, x_tile, zoom, tile_filename)

    line_scaled_latitude = None
    line_scaled_longitude = None
    if line_latitude:
        line_scaled_latitude = scale_lat_to_zoom(line_latitude, zoom)
    if line_longitude:
        line_scaled_longitude = scale_lat_to_zoom(line_longitude, zoom)

    markup_tile(line_scaled_longitude, line_scaled_latitude, tile_filename, markup_filename)

    if mark_loc:
        markup_tile(long_tile_float, lat_tile_float, markup_filename, markup_filename, 'black')

    sh.open(markup_filename)


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))

