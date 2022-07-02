#!/usr/bin/env python3
'''
create_overview_video.py - Create track overview video from GPX data

Usage:
  zoom.py <gpx-data> [--output=<filename>] [--tile-cache=<directory>] [--grid-lines]

Options:
  -h --help                 Show this screen.
  --output=<filename>       Output filename [default: output.avi].
  --tile-cache=<directory>  Tile cache directory [default: tiles].
  --grid-lines              Add tile lon/lat gridlines to ouptut.
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
import math

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
            print(lon_tile, lat_tile)

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

    return im_full, tile_ref_lo


def generate_image_track_pixel_coordinates(image_tile_ref, zoom, gpx_track_points):
    image_pixel_ref = osm.tile_point_to_pixel_point(image_tile_ref)
    track_pixel_points = map(lambda p: osm.coordinate_to_pixel_point(osm.Coordinate(p['lon'], p['lat']), zoom), gpx_track_points)
    image_track_pixel_coords = list(map(lambda q: (q.x - image_pixel_ref.x, q.y - image_pixel_ref.y), track_pixel_points))
    return image_track_pixel_coords


def draw_track_points(im_background, image_pixel_coords):
    color = ImageColor.getrgb('blue')
    dr = ImageDraw.Draw(im_background)
    dr.point(image_pixel_coords, fill=color)

    return im_background


def main(args):
    gpx_filename = args['<gpx-data>']
    output_file = args['--output']
    tile_directory = args['--tile-cache']
    grid_lines = args['--grid-lines']

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
    track_extents = utils.get_track_geo_extents(gpx_data.all_points())
    zoom, boundary_extents = utils.maximize_zoom(track_extents, pixels_x, pixels_y, margin_pixels)

    # Calculate expanded aboundary extents
    adjusted_boundary_extents, final_scale_factor = calculate_adjusted_boundary_extents(boundary_extents, zoom, margin_pixels, pixels_x, pixels_y)
    print('adjusted boundary extents: %r' % adjusted_boundary_extents)

    # Generate base background image
    im_background, image_tile_ref = generate_base_background_image(adjusted_boundary_extents, track_extents, zoom, tile_directory, grid_lines)

    # Draw track points (image, points)
    image_track_pixel_coords = generate_image_track_pixel_coordinates(image_tile_ref, zoom, gpx_data.all_points())
    im_background = draw_track_points(im_background, image_track_pixel_coords)

    im_background.save(output_file + '.resize_crop.png')

    # Scale image to final dimensions


    # Generate video
        # Load background image




if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))

