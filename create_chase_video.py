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


log = logging.getLogger(__name__)


def main(args):
    gpx_filename = args['<gpx-data>']
    zoom_factor = args['<zoom-factor>']
    output_file = args['--output']
    tile_directory = args['--tile-cache']
    pixels_x = int(args['--viewport-x'])
    pixels_y = int(args['--viewport-y'])

    output_temp_file = output_file + '_'

    log.info('gpx_filename: %s' % gpx_filename)
    log.info('output_file:  %s' % output_file)
    log.info('viewport dimensions:: (%d, %d)' % (pixels_x, pixels_y))

    # Pre calculations

    # # Get GPX data
    # with open(gpx_filename) as fd:
    #     gpx_raw = fd.read()
    # gpx_data = gpx.Gpx(gpx_raw)

    # Download tiles

    # Annotate tiles

    # Compose video

    # Copy over temp file to final filename
    # shutil.move(output_temp_file, output_file)


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))

