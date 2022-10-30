#!/usr/bin/env python3
'''
create_overview_video.py - Create track overview video from GPX data

Usage:
  create_overview_video.py <gpx-data> [--output=<filename>] [--tile-cache=<directory>] [--grid-lines] [--viewport-x=<pixels>] [--viewport-y=<pixels>] [--fps=<fps>]

Options:
  -h --help                 Show this screen.
  --output=<filename>       Output filename [default: output.mp4].
  --tile-cache=<directory>  Tile cache directory [default: tiles].
  --grid-lines              Add tile lon/lat gridlines to output.
  --viewport-x=<pixels>     Output video viewport x dimension pixels [default: 1022].
  --viewport-y=<pixels>     Output video viewport x dimension pixels [default: 1022].
  --fps=<fps>               Frames per second of output video [default: 25].
'''
# TODO: For timing offsets between the GPX data and video, need to support: tstart, tstop
import sys
import logging
import os
import math
import copy
import shutil
import datetime
from dateutil.tz import tzlocal

logging.basicConfig(level=logging.INFO, format='(%(threadName)-10s) %(message)-s')

from openstreetmaps_tiler import openstreetmaps as osm
from openstreetmaps_tiler import gpx
from openstreetmaps_tiler import utils

try:
    from docopt import docopt
    from PIL import Image
    from PIL import ImageDraw, ImageColor, ImageFont
    import cv2
except ImportError as e:
    installs = ['docopt', 'Pillow', 'opencv-python']
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


def generate_base_background_image(boundary_coord_extents, track_extents, zoom, tile_directory, draw_grid=False):
    ''' Generate base background image and reference pixel point for image corner '''
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
    im_full = None
    for lon_tile in range(tile_ref_lo.x, tile_ref_hi.x + 1):
        im_row = None
        for lat_tile in range(tile_ref_lo.y, tile_ref_hi.y + 1):
            key = (lon_tile, lat_tile)
            log.debug(lon_tile, lat_tile)

            im = Image.open(file_map[key]).convert('RGB')

            if draw_grid:
                # Add lon/lat grid lines to tiles for debugging
                tile_current = osm.TilePoint(lon_tile, lat_tile, zoom)
                geo_current = osm.tile_point_to_coordinate(tile_current)

                dr = ImageDraw.Draw(im)
                color = ImageColor.getrgb('brown')
                dr.line([(0, 0), (0, 255)], fill=color, width=1)
                dr.line([(0, 0), (255, 0)], fill=color, width=1)

                lon_deg_min = geo_current.lon
                lat_deg_min = geo_current.lat

                font = ImageFont.load_default()
                dr.text([(127, 10)], '%f' % lat_deg_min, font=font, fill=color)
                dr.text([(10, 127)], '%f' % lon_deg_min, font=font, fill=color)

            if im_row is None:
                im_row = im
            else:
                im_join = im
                im_row = utils.join_images_vertical(im_row, im_join)

        if im_full is None:
            im_full = im_row
        else:
            im_full = utils.join_images_horizontal(im_full, im_row)

    if draw_grid:
        # Draw boundary lines
        dr = ImageDraw.Draw(im_full)
        im_width, im_height = im_full.size
        color = ImageColor.getrgb('black')

        x_offset = (tile_lo.x - math.floor(tile_ref_lo.x)) * 256
        dr.line([(x_offset, 0), (x_offset, im_height)], fill=color, width=1)

        y_offset = (tile_lo.y - math.floor(tile_ref_lo.y)) * 256
        dr.line([(0, y_offset), (im_width, y_offset)], fill=color, width=1)

        x_offset = (tile_hi.x - math.floor(tile_ref_lo.x)) * 256
        dr.line([(x_offset, 0), (x_offset, im_height)], fill=color, width=1)

        y_offset = (tile_hi.y - math.floor(tile_ref_lo.y)) * 256
        dr.line([(0, y_offset), (im_width, y_offset)], fill=color, width=1)

        # Draw track extent lines
        color = ImageColor.getrgb('red')

        track_tile_extents = track_extents.to_tile_extents(zoom)
        track_lo = track_tile_extents.lo()
        track_hi = track_tile_extents.hi()

        x_offset = (track_lo.x - math.floor(tile_ref_lo.x)) * 256
        dr.line([(x_offset, 0), (x_offset, im_height)], fill=color, width=1)

        y_offset = (track_lo.y - math.floor(tile_ref_lo.y)) * 256
        dr.line([(0, y_offset), (im_width, y_offset)], fill=color, width=1)

        x_offset = (track_hi.x - math.floor(tile_ref_lo.x)) * 256
        dr.line([(x_offset, 0), (x_offset, im_height)], fill=color, width=1)

        y_offset = (track_hi.y - math.floor(tile_ref_lo.y)) * 256
        dr.line([(0, y_offset), (im_width, y_offset)], fill=color, width=1)


    # output_file = 'bozo'
    # im_full.save(output_file + '.raw.png')

    return im_full, osm.tile_point_to_pixel_point(tile_ref_lo)


def generate_image_track_pixel_coordinates(image_pixel_ref, zoom, gpx_track_points, scale_factor=1.0):
    track_pixel_points = map(lambda p: osm.coordinate_to_pixel_point(osm.Coordinate(p['lon'], p['lat']), zoom), gpx_track_points)
    image_track_pixel_coords = list(map(lambda q: ((q.x - image_pixel_ref.x) * scale_factor, (q.y - image_pixel_ref.y) * scale_factor), track_pixel_points))
    return image_track_pixel_coords


def generate_scaled_track_pixel_points_with_timestamp(image_pixel_ref, zoom, gpx_track_points, scale_factor=1.0):
    track_points = []
    for gpx_point in gpx_track_points:
        p = osm.coordinate_to_pixel_point(osm.Coordinate(gpx_point['lon'], gpx_point['lat']), zoom)
        timestamp  = gpx_point['time']
        image_offset_pixel_point = (p.x - image_pixel_ref.x) * scale_factor, (p.y - image_pixel_ref.y) * scale_factor, timestamp
        track_points.append(image_offset_pixel_point)

    return track_points


def draw_track_points(im_background, image_pixel_coords):
    color = ImageColor.getrgb('blue')
    dr = ImageDraw.Draw(im_background)
    dr.point(image_pixel_coords, fill=color)

    return im_background


def generate_map_video(background_image, track_points, output_file, fps=25, start_time=None):
    image = cv2.imread(background_image)
    height, width, _ = image.shape
    log.debug(height, width)

    if start_time is None:
        start_time = track_points[0][2]
    finish_time =  track_points[-1][2]

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
    video = cv2.VideoWriter(output_file, fourcc, float(fps), (width, height))

    xpos = int(round(track_points[0][0], 0))
    ypos = int(round(track_points[0][1], 0))
    tpos = track_points[0][2] - start_time
    tpos_last = tpos
    tpos_adj = tpos

    xlast = xpos
    ylast = ypos

    for frame in range(frame_start, frame_finish):
        update_period = 1000
        if frame % update_period == 0:
            log.info('%3.2f %d %d' % (frame / fps, frame, frames))

        current_time = frame / fps

        while tpos_adj < current_time and len(track_points) > 0:
            point = track_points.pop(0)
            xpos = point[0]
            ypos = point[1]
            xpos = int(round(point[0], 0))
            ypos = int(round(point[1], 0))
            tpos = point[2] - start_time
            if tpos == tpos_last:
                tpos_adj += 1/18
            else:
                tpos_last = tpos
                tpos_adj = tpos

            xlast = xpos
            ylast = ypos

        frame = copy.copy(image)

        cv2.circle(frame, (xlast, ylast), 15, color, thickness)
        video.write(frame)

    video.release()


def main():
    start_time = datetime.now(tzlocal())
    args = docopt(__doc__)

    gpx_filename = args['<gpx-data>']
    output_file = args['--output']
    tile_directory = args['--tile-cache']
    grid_lines = args['--grid-lines']
    pixels_x = int(args['--viewport-x'])
    pixels_y = int(args['--viewport-y'])
    fps = int(args['--fps'])

    margin_pixels = 10

    background_file = output_file + '.background.png'
    output_temp_file = output_file + '.temp.mp4'

    log.info('start_time: %s' % start_time.isoformat())

    log.info('gpx_filename: %s' % gpx_filename)
    log.info('output_file:  %s' % output_file)

    # Get GPX data
    with open(gpx_filename) as fd:
        gpx_raw = fd.read()
    gpx_data = gpx.Gpx(gpx_raw)

    # Calculate best zoom factor
    track_extents = utils.get_track_geo_extents(gpx_data.all_points())
    zoom, boundary_coord_extents = utils.maximize_zoom(track_extents, pixels_x, pixels_y, margin_pixels)

    # Calculate expanded boundary extents
    adjusted_boundary_coord_extents, final_scale_factor = calculate_adjusted_boundary_extents(boundary_coord_extents, zoom, margin_pixels, pixels_x, pixels_y)

    log.debug('final_scale_factor: %r' % final_scale_factor)

    # Generate base background image
    im_full, image_pixel_ref = generate_base_background_image(adjusted_boundary_coord_extents, track_extents, zoom, tile_directory, grid_lines)

    # Draw track points (image, points)
    image_track_pixel_coords = generate_image_track_pixel_coordinates(image_pixel_ref, zoom, gpx_data.all_points())
    im_full = draw_track_points(im_full, image_track_pixel_coords)

    # Scale and crop image to final dimensions
    boundary_pixel_extents = adjusted_boundary_coord_extents.to_pixel_extents(zoom)
    crop_box = [
        boundary_pixel_extents.lo().x - image_pixel_ref.x,
        boundary_pixel_extents.lo().y - image_pixel_ref.y,
        boundary_pixel_extents.hi().x - image_pixel_ref.x,
        boundary_pixel_extents.hi().y - image_pixel_ref.y,
    ]
    im_full_crop = im_full.crop(crop_box)

    im_full_resize = im_full_crop.resize((pixels_x, pixels_y), Image.Resampling.LANCZOS)
    im_full_resize.save(background_file)

    # Generate video
    track_timestamp_pixel_points = generate_scaled_track_pixel_points_with_timestamp(boundary_pixel_extents.lo(), zoom, gpx_data.all_points(), final_scale_factor)
    generate_map_video(background_file, track_timestamp_pixel_points, output_temp_file, fps=fps, start_time=gpx_data.start_time())

    # Copy over temp file to final filename
    shutil.move(output_temp_file, output_file)

    end_time = datetime.now(tzlocal())
    total_time = end_time - start_time
    log.info('end_time: %s' % end_time.isoformat())
    log.info('total_time(s): %0.3f' % total_time.total_seconds())


if __name__ == '__main__':
    main()

