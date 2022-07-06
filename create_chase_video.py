#!/usr/bin/env python3
'''
create_chase_video.py - Create track chase video from GPX data

Usage:
  create_chase_video.py <gpx-data> <zoom-factor> [--output=<filename>] [--tile-cache=<directory>] [--viewport-x=<pixels>] [--viewport-y=<pixels>]

Options:
  -h --help                 Show this screen.
  --output=<filename>       Output filename [default: output.mp4].
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

logging.basicConfig(level=logging.INFO, format='(%(threadName)-10s) %(message)-s')

from lib import openstreetmaps as osm
from lib import gpx
from lib import utils

try:
    from docopt import docopt
    from PIL import Image
    from PIL import ImageDraw, ImageColor, ImageFont
    from cv2 import cv2
    import numpy as np
except ImportError as e:
    installs = ['docopt', 'Pillow', 'opencv-python', 'numpy']
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
    
    for coordinate in gpx.gpx_points_to_coordinates(gpx_data.all_points()):
        pixel_point = osm.coordinate_to_pixel_point(coordinate, zoom_factor)

        tiles_in_view = get_tiles_in_viewport(pixel_point, viewport_offsets)
        for tile in tiles_in_view:
                key = (tile.x, tile.y)
                output_filename = get_tile_path(tile, tile_directory)
                file_map[key] = output_filename
                if not os.path.exists(output_filename):
                    osm.download_tile(tile, output_filename)

    log.debug('file_map: %r' % file_map)


def get_tiles_in_viewport(pixel_point, viewport_offsets):
    tile_set = []
    # Calculate pixel offset bounding points
    pixel_lo = osm.PixelPoint(
                    pixel_point.x + viewport_offsets.x_lo,
                    pixel_point.y + viewport_offsets.y_lo,
                    pixel_point.zoom
    )
    pixel_hi = osm.PixelPoint(
                    pixel_point.x + viewport_offsets.x_hi,
                    pixel_point.y + viewport_offsets.y_hi,
                    pixel_point.zoom
    )
    # Convert to tile references
    tile_lo = osm.tile_reference(osm.pixel_point_to_tile_point(pixel_lo))
    tile_hi = osm.tile_reference(osm.pixel_point_to_tile_point(pixel_hi))
    for x in range(tile_lo.x, tile_hi.x + 1):
        for y in range(tile_lo.y, tile_hi.y + 1):
            tile = osm.TilePoint(x, y, pixel_point.zoom)
            tile_set.append(tile)

    return sorted(tile_set)
    

def get_tile_path(tile_reference, tile_directory):
    return tile_directory +'/' +'tile_%06d_%06d_%02d.png' % (tile_reference.x, tile_reference.y, tile_reference.zoom)


def annotate_tiles(gpx_data, zoom_factor, tile_directory):

    tile_set = {}

    # Determine tiles have tracks on them    
    for coordinate in map(lambda p: osm.Coordinate(p['lon'], p['lat']), gpx_data.all_points()):
        tile_ref = osm.tile_reference(osm.coordinate_to_tile_point(coordinate, zoom_factor))
        if tile_ref not in tile_set:
            tile_set[tile_ref] = []

    log.debug('tile_set: %r' % tile_set)

    # Collect all points from the track contained in that tile
    for tile in tile_set:
        for coordinate in map(lambda p: osm.Coordinate(p['lon'], p['lat']), gpx_data.all_points()):
            location_tile = osm.tile_reference(osm.coordinate_to_tile_point(coordinate, zoom_factor))
            location_pixel = osm.pixel_point_round(osm.coordinate_to_pixel_point(coordinate, zoom_factor))
            if location_tile == tile:
                if location_pixel not in tile_set[tile]:
                    tile_set[tile].append(location_pixel)

    # Process each tile drawing contained points onto tile
    for tile in tile_set:
        log.debug('processing tile: %s' % repr(tile))
        tile_pixel_ref = osm.tile_point_to_pixel_point(tile)
        image_track_pixel_coords = list(map(lambda q: ((q.x - tile_pixel_ref.x), (q.y - tile_pixel_ref.y)), tile_set[tile]))
        tile_filename = get_tile_path(tile, tile_directory)

        log.debug('image_track_pixel_coords: %r' % image_track_pixel_coords)

        im_tile = Image.open(tile_filename).convert('RGB')
        draw_track_points(im_tile, image_track_pixel_coords)
        im_tile.save(tile_filename)


def draw_track_points(im_background, image_pixel_coords):
    color = ImageColor.getrgb('blue')
    dr = ImageDraw.Draw(im_background)
    dr.point(image_pixel_coords, fill=color)

    return im_background


def generate_map_video(track_pixel_ts_pairs, output_file, tile_directory, viewport_offsets, pixels_x, pixels_y, zoom, fps=25): #, tstart, tfinish):
    '''
    Takes a list of tuples indicating track position and time: (PixelPoint(), timestamp)
    Renders video frames based on position composing frame based on tiles within the viewport.
    '''
    im_canvas = np.zeros((pixels_x, pixels_y, 3), np.uint8)

    x_portal_offset = int(pixels_x / 2)
    y_portal_offset = int(pixels_y / 2)

    start_time = track_pixel_ts_pairs[0][1]
    finish_time = track_pixel_ts_pairs[-1][1]

    log.info(start_time)
    log.info(finish_time)
    total_seconds = finish_time - start_time
    log.info(total_seconds)

    frame_start = 0
    frame_finish = int(total_seconds * fps)
    frames = int(total_seconds * fps)

    log.info('frame_start: %d %f' % (frame_start, frame_start / fps))
    log.info('frame_finish: %d %f' % (frame_finish, frame_finish / fps))

    color = (40, 40, 255)
    thickness = 3

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(output_file, fourcc, float(fps), (pixels_x, pixels_y))

    # xpos = int(round(track_points[0][0], 0))
    # ypos = int(round(track_points[0][1], 0))
    pixel_pos = track_pixel_ts_pairs[0][0]
    # TODO: confirm that track_pixel_ts_pairs[0][1] != start_time under some circumstances
    tpos = track_pixel_ts_pairs[0][1] - start_time 
    tpos_last = tpos
    tpos_adj = tpos

    pixel_pos_last = pixel_pos

    # For each frame in the sequence
    for frame in range(frame_start, frame_finish):
        update_period = 1000
        if frame % update_period == 0:
            log.info('%3.2f %d %d' % (frame / fps, frame, frames))

        # Determine the time corresponding to the frame
        current_time = frame / fps

        # If the head of the track points list is less that current time, pop items off the list
        while tpos_adj < current_time and len(track_pixel_ts_pairs) > 0:
            pixel_pos, timestamp = track_pixel_ts_pairs.pop(0)

            tpos = timestamp - start_time
            if tpos == tpos_last:
                # Telemetry is recorded at 18Hz, so if we already have a point at this time, skip ahead
                tpos_adj += 1 / 18
            else:
                tpos_last = tpos
                tpos_adj = tpos

            pixel_pos_last = pixel_pos

        image = build_image(pixel_pos_last, viewport_offsets, pixels_x, pixels_y, tile_directory)

        cv_image = np.array(image) 
        cv_image = cv_image[:, :, ::-1].copy() # Convert RGB to BGR 

        cv2.circle(cv_image, (x_portal_offset, y_portal_offset), 15, color, thickness)
        video.write(cv_image)

    video.release()


def build_image(pixel_position, viewport_offsets, pixels_x, pixels_y, tile_directory):
    viewport_tiles = get_tiles_in_viewport(pixel_position, viewport_offsets)
    log.debug('viewport_tiles: ' + repr(viewport_tiles))
    log.debug('pixel_position: ' + repr(pixel_position))
    log.debug('coord: ' + repr(osm.pixel_point_to_coordinate(pixel_position)))

    im_view = Image.new(mode="RGB", size=(pixels_x, pixels_y))

    # load and stitch all tiles for current frame
    for tile in viewport_tiles:
        tile_pixel_ref = osm.tile_point_to_pixel_point(tile)
        tile_path = get_tile_path(tile, tile_directory)
        tile_offset_x = - viewport_offsets.x_lo - int(pixel_position.x - tile_pixel_ref.x)
        tile_offset_y = - viewport_offsets.y_lo - int(pixel_position.y - tile_pixel_ref.y)
        im_tile = Image.open(tile_path)

        im_view.paste(im_tile, (tile_offset_x, tile_offset_y), mask=None)

    # im_view.show()
    return im_view


def main(args):
    gpx_filename = args['<gpx-data>']
    zoom_factor = int(args['<zoom-factor>'])
    output_file = args['--output']
    tile_directory = args['--tile-cache']
    pixels_x = int(args['--viewport-x'])
    pixels_y = int(args['--viewport-y'])

    output_temp_file = output_file + 'temp.mp4'

    log.info('gpx_filename: %s' % gpx_filename)
    log.info('output_file:  %s' % output_file)
    log.info('viewport dimensions:: (%d, %d)' % (pixels_x, pixels_y))

    # Setup: Pre calculations
    offsets = ViewportOffsets(
                int(-(pixels_x / 2)),
                int(-(pixels_y / 2)),
                int((pixels_x / 2)),
                int((pixels_y / 2))
    )

    # Setup: Load GPX data
    gpx_data = load_gpx_data(gpx_filename)

    # Download tiles
    download_tiles(gpx_data, zoom_factor, offsets, tile_directory)

    # Annotate tiles
    annotate_tiles(gpx_data, zoom_factor, tile_directory)

    # Compose video
    track_coordinate_ts_pairs = gpx.gpx_points_to_coordinate_timestamp_tuples(gpx_data.all_points())
    track_pixel_ts_pairs = list(map(lambda t: (osm.coordinate_to_pixel_point(t[0], zoom_factor), t[1]), track_coordinate_ts_pairs))
    generate_map_video(track_pixel_ts_pairs, output_temp_file, tile_directory, offsets, pixels_x, pixels_y, zoom_factor)

    # Copy over temp file to final filename
    shutil.move(output_temp_file, output_file)


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))

