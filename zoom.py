#!/usr/bin/env python3
'''
zoom.py - Aggregate tile downloader and annotator

Usage:
  zoom.py <gps-metadata> [--output=<filename>] [--zoom=<factor>] [--tile-cache=<directory>]

Options:
  -h --help                 Show this screen.
  --output=<filename>       Output filename [default: output.png].
  --zoom=<factor>           Override zoom factor.
  --tile-cache=<directory>  Tile cache directory [default: tiles].
'''
import math
import tile_dl
import json
import sh
import sys
import os

try:
    from PIL import Image
    from PIL import ImageDraw, ImageColor, ImageFont
except ImportError as e:
    sys.stderr.write('Error: %s\nTry:\n    pip install --user Pillow\n' % e)
    sys.exit(1)

try:
    from docopt import docopt
except ImportError as e:
    sys.stderr.write('Error: %s\nTry:\n    pip install --user docopt\n' % e)
    sys.exit(1)

def zoom_tile_angle(zoom):
    print('zoom_tile_angle:', zoom)
    print('2**zoom', 2**zoom)
    zoom_angle = 360 / (2**zoom)
    print('zoom_angle:', zoom_angle)
    return zoom_angle


def zoom_factor_bounded(in_zoom, zoom_max):

    for i in range(zoom_max + 1):
        zoom_angle = 360 / (2**i)
        if zoom_angle < in_zoom:
            return i
    return zoom_max

def pixel_angle(zoom):
    return (360 / 2.0 ** zoom) / 256

class ConversionException(Exception):
    pass

# Geo to tile scale conversions

def xgeo2tile(lon_deg, zoom):
    if lon_deg > 180 or lon_deg < -180:
        raise ConversionException('Degres beyond conversion range: %f' % lon_deg)
    n = 2.0 ** zoom
    xfloat = (lon_deg + 180.0) / 360.0 * n

    return xfloat

def ygeo2tile(lat_deg, zoom):
    if lat_deg > 85.05113 or lat_deg < -85.05113:
        raise ConversionException('Degres beyond conversion range: %f' % lat_deg)
    n = 2.0 ** zoom
    lat_rad = math.radians(lat_deg)
    yfloat = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n

    return yfloat

def xtile2geo(xtile, zoom):
    n = 2.0 ** zoom
    lon_deg = (xtile / n * 360) - 180.0
    return lon_deg


def ytile2geo(ytile, zoom):
    n = 2.0 ** zoom
    lat_deg = math.degrees(math.atan(math.sinh((- (ytile / n * 2.0) + 1.0) * math.pi)))
    return lat_deg

# Geo to pixel scale conversions

def xgeo2pix(lon_deg, zoom):
    xpixel = xgeo2tile(lon_deg, zoom) * 256
    return xpixel

def ygeo2pix(lat_deg, zoom):
    ypixel = ygeo2tile(lat_deg, zoom) * 256
    return ypixel

def xpix2geo(xpix, zoom):
    xtile = xpix / 256
    lon_deg = xtile2geo(xtile, zoom)
    return lon_deg


def ypix2geo(ypix, zoom):
    ytile = ypix / 256
    lat_deg = ytile2geo(ytile, zoom)
    return lat_deg

# Tile to pixel scale conversions

def xtile2pix(xtile, zoom):
    xpixel = xtile * 256
    return xpixel

def ytile2pix(ytile, zoom):
    ypixel = ytile * 256
    return ypixel

def xpix2tile(xpix, zoom):
    xtile = xpix / 256
    return xtile


def ypix2tile(ypix, zoom):
    ytile = ypix / 256
    return ytile


def xdeg2num(lon_deg, zoom):
    # n = 2.0 ** zoom
    # xfloat = (lon_deg + 180.0) / 360.0 * n
    # xtile = int(xfloat)
    return int(xgeo2tile(lon_deg, zoom))


def ydeg2num(lat_deg, zoom):
    # n = 2.0 ** zoom
    # lat_rad = math.radians(lat_deg)
    # yfloat = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    # ytile = int(yfloat)
    return int(ygeo2tile(lat_deg, zoom))



def get_concat_h(im1, im2):
    dst = Image.new('RGB', (im1.width + im2.width, im1.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (im1.width, 0))
    return dst

def get_concat_v(im1, im2):
    dst = Image.new('RGB', (im1.width, im1.height + im2.height))
    dst.paste(im1, (0, 0))
    dst.paste(im2, (0, im1.height))
    return dst


def maximize_zoom(xl, xh, yl, yh, target_square_size, boundary_pixels=20, zoom_max=19):
    print('maximize_zoom - xl: %f, xh: %f, yl: %f, yh: %f, target_square_size: %d, zoom_max: %f' % (xl, xh, yl, yh, target_square_size, zoom_max))
    # loop until either x or y has exceeded zoom for gien tile_square_size - take previous zoom
    for zoom in range(zoom_max + 1):
        xpl, xph, ypl, yph = geo_set_to_pixel(xl, xh, yl, yh, zoom)
        x_size_pixel = xph - xpl
        y_size_pixel = yph - ypl
        if (x_size_pixel + (2 * boundary_pixels)) >= target_square_size or (y_size_pixel + (2 * boundary_pixels)) >= target_square_size:
            break
    zoom_target = zoom - 1 # last zoom value
    print('--> zoom_target: %d' % (zoom_target))
    xpl, xph, ypl, yph = geo_set_to_pixel(xl, xh, yl, yh, zoom_target)
    x_size_pixel = xph - xpl
    y_size_pixel = yph - ypl
    print('--> xpl: %f' % (xpl))
    print('--> xph: %f' % (xph))
    print('--> ypl: %f' % (ypl))
    print('--> yph: %f' % (yph))
    print('--> x_size_pixel:  %f' % (x_size_pixel))
    print('--> y_size_pixel:  %f' % (y_size_pixel))

    return zoom_target


def geo_set_to_pixel(xl, xh, yl, yh, zoom):
    if xl > xh:
        raise ConversionException('x coordinate ordering incorrect: xl=%f > xh=%f' % (xl, xh))
    if yl > yh:
        raise ConversionException('y coordinate ordering incorrect: yl=%f > yh=%f' % (yl, yh))

    xpl = xgeo2pix(xl, zoom)
    xph = xgeo2pix(xh, zoom)
    # We swap these, because the y scale is magnitude inverted
    ypl = ygeo2pix(yh, zoom)
    yph = ygeo2pix(yl, zoom)

    return xpl, xph, ypl, yph


def get_expanded_boundary_geo_extents(xtgl, xtgh, ytgl, ytgh, zoom_factor, boundary_pixels, target_square_size):
    # Calculate coords for boundary extension of boundary_pixels at the scaled up size (from base zoom size)
    xtpl, xtph, ytpl, ytph = geo_set_to_pixel(xtgl, xtgh, ytgl, ytgh, zoom_factor)

    xp_track_size = xtph - xtpl
    yp_track_size = ytph - ytpl

    xp_track_center = (xtph + xtpl) / 2
    yp_track_center = (ytph + ytpl) / 2

    # scale_x = (target_square_size - (2 * boundary_pixels)) / xp_track_size
    # scale_y = (target_square_size - (2 * boundary_pixels)) / yp_track_size
    scale_x = (target_square_size - (2 * boundary_pixels)) / xp_track_size
    scale_y = (target_square_size - (2 * boundary_pixels)) / yp_track_size

    print('scale_x:', scale_x)
    print('scale_y:', scale_y)

    scale_factor = min(scale_x, scale_y)

    # return 0,0,0,0,0
    # xp_track_size = xtph - xtpl
    # yp_track_size = ytph - ytpl

    # xp_center = (xtph + xtpl) / 2
    # yp_center = (ytph + ytpl) / 2

    # scale_base = max(x_size_pixel, y_size_pixel)
    # scale_factor = target_square_size / scale_base
    print('scale_factor:', scale_factor)

    print('xtpl, xtph, ytpl, ytph:', xtpl, xtph, ytpl, ytph)

    xbpl = xp_track_center - (target_square_size / 2) / scale_factor
    xbph = xp_track_center + (target_square_size / 2) / scale_factor
    ybpl = yp_track_center - (target_square_size / 2) / scale_factor
    ybph = yp_track_center + (target_square_size / 2) / scale_factor

    print('xbpl, xbph, ybpl, ybph:', xbpl, xbph, ybpl, ybph)

    xbgl = xpix2geo(xbpl, zoom_factor)
    xbgh = xpix2geo(xbph, zoom_factor)
    ybgl = ypix2geo(ybpl, zoom_factor)
    ybgh = ypix2geo(ybph, zoom_factor)

    print('xbgl, xbgh, ybgl, ybgh:', xbgl, xbgh, ybgl, ybgh)

    return xbgl, xbgh, ybgl, ybgh, scale_factor


def find_best_zoom(xl, xh, yl, yh, xtiles, ytiles, target_square_size, zoom_max=19):
    print('find_best_zoom - xl: %f, xh: %f, yl: %f, yh: %f, xtiles: %f, ytiles: %f, zoom_max: %f' % (xl, xh, yl, yh, xtiles, ytiles, zoom_max))
    # loop until either x or y has exceeded zoom for gien tile_square_size - take previous zoom
    for zoom in range(zoom_max + 1):
        # print('zoom:', zoom)
        # xbtl = xgeo2tile(xl, zoom) # x scaled lo
        # xbth = xgeo2tile(xh, zoom) #a x scaled hi
        # ybtl = ygeo2tile(yl, zoom) # y scaled lo
        # ybth = ygeo2tile(yh, zoom) # y scaled hi

        # print('xbtl:', xbtl)
        # print('xbth:', xbth)
        # print('ybtl:', ybtl)
        # print('ybth:', ybth)

        # if (ybth - ybtl) > ytiles:
        #     print('find_best_zoom: y max')
        #     return zoom
        # if (xbth - xbtl) > xtiles:
        #     print('find_best_zoom: x max')
        #     return zoom

        x_scaled = abs(xgeo2tile(xl, zoom)*256 - xgeo2tile(xh, zoom)*256)
        y_scaled = abs(ygeo2tile(yl, zoom)*256 - ygeo2tile(yh, zoom)*256)
        if x_scaled >= target_square_size or y_scaled >= target_square_size:
            break
    zoom_target = zoom - 1 # last zoom value
    print('--> zoom_target: %d' % (zoom_target))

    return zoom_target

def load_points_file(filename):
    with open(filename) as fd:
        body = fd.read()
    points_data = json.loads(body)
    return points_data


def get_bounding_points(points_list):
    xl, xh, yl, yh = None, None, None, None

    for point in points_list:
        lat = point['lat']
        lon = point['lon']
        if xl is None:
            xl = lon
            xh = lon
            yl = lat
            yh = lat
        if lat < yl:
            yl = lat
        if lat > yh:
            yh = lat
        if lon < xl:
            xl = lon
        if lon > xh:
            xh = lon

    return xl, xh, yl, yh


def get_ll_points_array(points_list):
    raw_points = []
    for point in points_list:
        y = point['lat']
        x = point['lon']
        raw_points.append((x, y))


def get_mapped_points_array(points_list, zoom):
    mapped_points = []
    for point in points_list:
        y = ygeo2tile(point['lat'], zoom)
        x = xgeo2tile(point['lon'], zoom)
        ts = point['time']
        mapped_points.append((x, y, ts))
    return mapped_points


def get_pixel_mapped_points_array(points_list, zoom):
    mapped_points = []
    for point in points_list:
        y = ygeo2pix(point['lat'], zoom)
        x = xgeo2pix(point['lon'], zoom)
        ts = point['time']
        mapped_points.append((x, y, ts))
    return mapped_points


def get_scaled_inter_image_pixel_points_array(points_list, zoom, x_image_pixel_origin, y_image_pixel_origin, scaling_factor, with_ts=False):
    mapped_points = []
    # For each point
    for point in points_list:
        x_geo = point['lon']
        y_geo = point['lat']
        ts = point['time']
        # 1. Convert to pixel point
        # 2. Subtract the image (0, 0) pixel origin.\
        # 3. Scale raw pixel points to image scaled pixel points
        x_pix = int(round((xgeo2pix(x_geo, zoom) - x_image_pixel_origin) * scaling_factor, 0))
        y_pix = int(round((ygeo2pix(y_geo, zoom) - y_image_pixel_origin) * scaling_factor, 0))
        if with_ts:
            point = (x_pix, y_pix, ts)
        else:
            point = (x_pix, y_pix)
        mapped_points.append(point)

    return mapped_points


def in_tile_fn(xtile, ytile):
    def in_tile(point):
        xpoint, ypoint = point
        if int(xpoint) == int(xtile) and int(ypoint) == int(ytile):
            return True
    return in_tile


def mapped_to_pixel_points(mapped_points, x_base, y_base, with_ts=False):
    # x_base, y_base is coordinates of the base tile in tile map indexes
    image_points = []
    for x, y, ts in mapped_points:
        x_pix = int((x - x_base) * 256)
        y_pix = int((y - y_base) * 256)
        if with_ts:
            point = (x_pix, y_pix, ts)
        else:
            point = (x_pix, y_pix)
        image_points.append(point)
    return image_points


def main(args):

    gps_metadata_filename = args['<gps-metadata>']
    output_file = args['--output']
    output_metadata_file = output_file + '.meta.txt'
    zoom_override = args['--zoom']

    tile_directory = args['--tile-cache']
    points = load_points_file(gps_metadata_filename)

    first_point = points.pop(0)
    start_time = first_point['time']
    print(points[0])

    # xtgl, xtgh, ytgl, ytgh = (-122.1399074, -122.0867842, 37.4446023, 37.4941312)
    xtgl, xtgh, ytgl, ytgh = get_bounding_points(points)

    print('track extents:', xtgl, xtgh, ytgl, ytgh)



    xis = xtgh - xtgl # x input span
    yis = ytgh - ytgl # x input span

    border_factor = 1.2
    x_tiles = 5
    y_tiles = 4
    # x_tiles = 1
    # y_tiles = 1
    zoom_max = 19
    boundary_pixels = 20
    target_square_size = 1022

    print('xtgl:', xtgl)
    print('xtgh:', xtgh)
    print('ytgl:', ytgl)
    print('ytgh:', ytgh)
    print('xis:', xis)
    print('yis:', yis)

    if zoom_override is None:
        # zoom_factor = find_best_zoom(xtgl, xtgh, ytgh, ytgl, x_tiles, y_tiles, target_square_size)
        zoom_factor = maximize_zoom(xtgl, xtgh, ytgl, ytgh, target_square_size, boundary_pixels=boundary_pixels)
    else:
        zoom_factor = int(zoom_override)
    print('zoom_factor:', zoom_factor)

    # xbgl, xbgh, ybgl, ybgh, scale_factor = get_expanded_boundary_geo_extents(xtgl, xtgh, ytgl, ytgh, zoom_factor, boundary_pixels, target_square_size)
    # print('expanded boundary extents:', xbgl, xbgh, ybgl, ybgh)

    xbgl, xbgh, ybgl, ybgh, scale_factor = get_expanded_boundary_geo_extents(xtgl, xtgh, ytgl, ytgh, zoom_factor, boundary_pixels, target_square_size)
    print('expanded boundary extents:', xbgl, xbgh, ybgl, ybgh)

    # sys.exit(0)

    # x1 = xtgl
    # y1 = ytgl
    # x2 = xtgh
    # y2 = ytgh

    # Get the extent mapping of the track extents in scaled map factors
    xesl = min(xgeo2tile(xtgh, zoom_factor), xgeo2tile(xtgl, zoom_factor))     # x boundary scaled lo
    xesh = max(xgeo2tile(xtgh, zoom_factor), xgeo2tile(xtgl, zoom_factor))     # x boundary scaled hi
    yesl = min(ygeo2tile(ytgh, zoom_factor), ygeo2tile(ytgl, zoom_factor))     # y boundary scaled lo
    yesh = max(ygeo2tile(ytgh, zoom_factor), ygeo2tile(ytgl, zoom_factor))     # y boundary scaled hi

    # Get the mapping of boundary extent point in tile coords
    xbtl = min(xgeo2tile(xbgh, zoom_factor), xgeo2tile(xbgl, zoom_factor))     # x boundary scaled lo
    xbth = max(xgeo2tile(xbgh, zoom_factor), xgeo2tile(xbgl, zoom_factor))     # x boundary scaled hi
    ybtl = min(ygeo2tile(ybgh, zoom_factor), ygeo2tile(ybgl, zoom_factor))     # y boundary scaled lo
    ybth = max(ygeo2tile(ybgh, zoom_factor), ygeo2tile(ybgl, zoom_factor))     # y boundary scaled hi

    # Get the mapping of boundary extent point in pixel coords
    xbpl = min(xgeo2pix(xbgh, zoom_factor), xgeo2pix(xbgl, zoom_factor))     # x boundary scaled lo
    xbph = max(xgeo2pix(xbgh, zoom_factor), xgeo2pix(xbgl, zoom_factor))     # x boundary scaled hi
    ybpl = min(ygeo2pix(ybgh, zoom_factor), ygeo2pix(ybgl, zoom_factor))     # y boundary scaled lo
    ybph = max(ygeo2pix(ybgh, zoom_factor), ygeo2pix(ybgl, zoom_factor))     # y boundary scaled hi

    print('xbth:', xbth)
    print('xbtl:', xbtl)
    print('ybth:', ybth)
    print('ybtl:', ybtl)

    xbtl_i = int(xbtl)     # x tile lo
    xbth_i = int(xbth)     # x tile hi
    ybtl_i = int(ybtl)     # y tile lo
    ybth_i = int(ybth)     # y tile hi

    mapped_points = get_mapped_points_array(points, zoom_factor)

    file_map = {}

    for lon_tile in range(xbtl_i, xbth_i + 1):
        for lat_tile in range(ybtl_i, ybth_i + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            output_filename = tile_directory +'/' +'tile_%06d_%06d_%02d.png' % (lon_tile, lat_tile, zoom_factor)
            file_map[key] = output_filename
            if not os.path.exists(output_filename):
                tile_dl.get_tile(lat_tile, lon_tile, zoom_factor, output_filename)

    print(file_map)

    for lon_tile in range(xbtl_i, xbth_i + 1):
        for lat_tile in range(ybtl_i, ybth_i + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            im = Image.open(file_map[key]).convert('RGB')
            # dr = ImageDraw.Draw(im)

            # # grid lines
            # color = ImageColor.getrgb('brown')
            # dr.line([(0, 0), (0, 255)], fill=color, width=1)
            # dr.line([(0, 0), (255, 0)], fill=color, width=1)
            # font = ImageFont.load_default()
            # lon_deg_min = xtile2geo(lon_tile, zoom_factor)
            # lat_deg_min = ytile2geo(lat_tile, zoom_factor)
            # lon_deg_max = xtile2geo(lon_tile + 1, zoom_factor)
            # lat_deg_max = ytile2geo(lat_tile + 1, zoom_factor)
            # dr.text([(127, 10)], '%f' % lat_deg_min, font=font, fill=color)
            # dr.text([(10, 127)], '%f' % lon_deg_min, font=font, fill=color)

            # color = ImageColor.getrgb('black')

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

    print('xbtl_i:', xbtl_i)
    print('xbth_i:', xbth_i)
    print('ybtl_i:', ybtl_i)
    print('ybth_i:', ybth_i)

    im_full = None
    for lon_tile in range(xbtl_i, xbth_i + 1):
        im_row = None
        for lat_tile in range(ybtl_i, ybth_i + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            if im_row is None:
                im_row = Image.open(file_map[key]).convert('RGB')
            else:
                im_join = Image.open(file_map[key]).convert('RGB')
                im_row = get_concat_v(im_row, im_join)

        if im_full is None:
            im_full = im_row
        else:
            im_full = get_concat_h(im_full, im_row)

    im_full.save(output_file + '.raw.png')

    orig_width, orig_height = im_full.size

    scaled_width, scaled_height = int(round(orig_width * scale_factor, 0)), int(round(orig_height * scale_factor, 0))

    im_full_resize = im_full.resize((scaled_width, scaled_height), Image.LANCZOS)
    im_full_resize.save(output_file)




    xbtl_i_pix = xtile2pix(xbtl_i, zoom_factor)
    ybtl_i_pix = ytile2pix(ybtl_i, zoom_factor)

    inter_image_xbpl = int((xbpl - xbtl_i_pix) * scale_factor)
    inter_image_xbph = int((xbph - xbtl_i_pix) * scale_factor)
    inter_image_ybpl = int((ybpl - ybtl_i_pix) * scale_factor)
    inter_image_ybph = int((ybph - ybtl_i_pix) * scale_factor)

    print('xbpl, xbph, ybpl, ybph:', xbpl, xbph, ybpl, ybph)

    xbpl_geo = xpix2geo(xbpl, zoom_factor)
    xbph_geo = xpix2geo(xbph, zoom_factor)
    ybpl_geo = ypix2geo(ybpl, zoom_factor)
    ybph_geo = ypix2geo(ybph, zoom_factor)

    print('xbpl_geo, xbph_geo, ybpl_geo, ybph_geo:', xbpl_geo, xbph_geo, ybpl_geo, ybph_geo)

    box = inter_image_xbpl, inter_image_ybpl, inter_image_xbph, inter_image_ybph
    print('im_full_resize.size:', im_full_resize.size)
    print('crop:', box)
    im_full_resize_crop = im_full_resize.crop(box)






    # pixel_points = mapped_to_pixel_points(mapped_points, xbtl_i, ybtl_i)
    # pixel_points_ts = mapped_to_pixel_points(mapped_points, xbtl_i, ybtl_i, with_ts=True)


    print('xbtl_i_pix, ybtl_i_pix:', xbtl_i_pix, ybtl_i_pix)
    print('xbtl_i_pix_geo, ybtl_i_pix_geo:', xpix2geo(xbtl_i_pix, zoom_factor), ypix2geo(ybtl_i_pix, zoom_factor))

    scaled_image_pixel_points = get_scaled_inter_image_pixel_points_array(points, zoom_factor, xbpl, ybpl, scale_factor)
    scaled_image_pixel_points_ts = get_scaled_inter_image_pixel_points_array(points, zoom_factor, xbpl, ybpl, scale_factor, with_ts=True)

    color = ImageColor.getrgb('blue')

    dr = ImageDraw.Draw(im_full_resize_crop)
    dr.point(scaled_image_pixel_points, fill=color)


    im_full_resize_crop.save(output_file + '.resize_crop.png')




    gps_metadata = {
        'start_time': start_time,
        'gps_points': scaled_image_pixel_points_ts
    }

    # dump pixel points
    with open(output_metadata_file, 'w+') as fd:
        fd.write(json.dumps(gps_metadata))

    # sh.open(output_file)
    # sh.open(output_file + '.resize_crop.png')


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))


