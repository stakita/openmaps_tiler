#!/usr/bin/env python3
'''
zoom.py - Aggregate tile downloader and annotator

Usage:
  zoom.py <gps-metadata> [--output=<filename>] [--zoom=<factor>]

Options:
  -h --help             Show this screen.
  --output=<filename>   Output filename [default: output.png].
  --zoom=<factor>       Override zoom factor.
'''
import math
import tile_dl
import json
import sh
import sys

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


def xgeo2tile(lon_deg, zoom):
    n = 2.0 ** zoom
    xfloat = (lon_deg + 180.0) / 360.0 * n

    return xfloat

def ygeo2tile(lat_deg, zoom):
    n = 2.0 ** zoom
    lat_rad = math.radians(lat_deg)
    yfloat = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n

    return yfloat

def xtile2geo(xindex, zoom):
    n = 2.0 ** zoom
    lon_deg = (xindex / n * 360) - 180.0
    return lon_deg


def ytile2geo(yindex, zoom):
    n = 2.0 ** zoom
    lat_deg = math.degrees(math.atan(math.sinh((- (yindex / n * 2.0) + 1.0) * math.pi)))
    return lat_deg


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

def find_best_zoom(xl, xh, yl, yh, xtiles, ytiles, target_square_size, zoom_max=19):
    print('find_best_zoom - xl: %f, xh: %f, yl: %f, yh: %f, xtiles: %f, ytiles: %f, zoom_max: %f' % (xl, xh, yl, yh, xtiles, ytiles, zoom_max))
    # loop until either x or y has exceeded zoom for gien tile_square_size - take previous zoom
    for zoom in range(zoom_max + 1):
        # print('zoom:', zoom)
        # xbsl = xgeo2tile(xl, zoom) # x scaled lo
        # xbsh = xgeo2tile(xh, zoom) #a x scaled hi
        # ybsl = ygeo2tile(yl, zoom) # y scaled lo
        # ybsh = ygeo2tile(yh, zoom) # y scaled hi

        # print('xbsl:', xbsl)
        # print('xbsh:', xbsh)
        # print('ybsl:', ybsl)
        # print('ybsh:', ybsh)

        # if (ybsh - ybsl) > ytiles:
        #     print('find_best_zoom: y max')
        #     return zoom
        # if (xbsh - xbsl) > xtiles:
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


def get_boundary_extents(points_list):
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


def get_expanded_boundary_extents(xil, xih, yil, yih, zoom_factor, boundary_pixels, target_square_size):
    y_pixel_width = abs(ygeo2tile(yil, zoom_factor)*256 - ygeo2tile(yih, zoom_factor)*256)
    x_pixel_width = abs(xgeo2tile(xil, zoom_factor)*256 - xgeo2tile(xih, zoom_factor)*256)

    x_scaling = target_square_size / x_pixel_width
    y_scaling = target_square_size / y_pixel_width

    yol = ytile2geo(((ygeo2tile(yil, zoom_factor) * 256 * y_scaling) + boundary_pixels) / (256 * y_scaling), zoom_factor)
    yoh = ytile2geo(((ygeo2tile(yih, zoom_factor) * 256 * y_scaling) - boundary_pixels) / (256 * y_scaling), zoom_factor)
    xol = xtile2geo(((xgeo2tile(xil, zoom_factor) * 256 * x_scaling) - boundary_pixels) / (256 * x_scaling), zoom_factor)
    xoh = xtile2geo(((xgeo2tile(xih, zoom_factor) * 256 * x_scaling) + boundary_pixels) / (256 * x_scaling), zoom_factor)
    return xol, xoh, yol, yoh


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

    tile_directory = 'tiles'
    points = load_points_file(gps_metadata_filename)

    first_point = points.pop(0)
    start_time = first_point['time']
    print(points[0])

    xil, xih, yil, yih = (-122.1399074, -122.0867842, 37.4446023, 37.4941312)
    # xil, xih, yil, yih = get_boundary_extents(points)

    print('boundary extents:', xil, xih, yil, yih)



    xis = xih - xil # x input span
    yis = yih - yil # x input span

    border_factor = 1.2
    x_tiles = 5
    y_tiles = 4
    # x_tiles = 1
    # y_tiles = 1
    zoom_max = 19
    boundary_pixels = 20
    target_square_size = 982

    print('xil:', xil)
    print('xih:', xih)
    print('yil:', yil)
    print('yih:', yih)
    print('xis:', xis)
    print('yis:', yis)

    if zoom_override is None:
        zoom_factor = find_best_zoom(xil, xih, yih, yil, x_tiles, y_tiles, target_square_size)
    else:
        zoom_factor = int(zoom_override)
    print('zoom_factor:', zoom_factor)

    xbl, xbh, ybl, ybh = get_expanded_boundary_extents(xil, xih, yil, yih, zoom_factor, boundary_pixels, target_square_size)
    print('expanded boundary extents:', xbl, xbh, ybl, ybh)

    # x1 = xil
    # y1 = yil
    # x2 = xih
    # y2 = yih

    # Get the extent mapping of the track extents in scaled map factors
    xesl = min(xgeo2tile(xih, zoom_factor), xgeo2tile(xil, zoom_factor))     # x boundary scaled lo
    xesh = max(xgeo2tile(xih, zoom_factor), xgeo2tile(xil, zoom_factor))     # x boundary scaled hi
    yesl = min(ygeo2tile(yih, zoom_factor), ygeo2tile(yil, zoom_factor))     # y boundary scaled lo
    yesh = max(ygeo2tile(yih, zoom_factor), ygeo2tile(yil, zoom_factor))     # y boundary scaled hi

    # Get the boundary mapping of the boundary extents in scaled map factors
    xbsl = min(xgeo2tile(xbh, zoom_factor), xgeo2tile(xbl, zoom_factor))     # x boundary scaled lo
    xbsh = max(xgeo2tile(xbh, zoom_factor), xgeo2tile(xbl, zoom_factor))     # x boundary scaled hi
    ybsl = min(ygeo2tile(ybh, zoom_factor), ygeo2tile(ybl, zoom_factor))     # y boundary scaled lo
    ybsh = max(ygeo2tile(ybh, zoom_factor), ygeo2tile(ybl, zoom_factor))     # y boundary scaled hi

    print('xbsh:', xbsh)
    print('xbsl:', xbsl)
    print('ybsh:', ybsh)
    print('ybsl:', ybsl)

    xtl = int(xbsl)     # x tile lo
    xth = int(xbsh)     # x tile hi
    ytl = int(ybsl)     # y tile lo
    yth = int(ybsh)     # y tile hi

    mapped_points = get_mapped_points_array(points, zoom_factor)

    file_map = {}

    for lon_tile in range(xtl, xth + 1):
        for lat_tile in range(ytl, yth + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            output_filename = tile_directory +'/' +'tile_%06d_%06d_%02d.png' % (lon_tile, lat_tile, zoom_factor)
            file_map[key] = output_filename
            tile_dl.get_tile(lat_tile, lon_tile, zoom_factor, output_filename)

    print(file_map)

    for lon_tile in range(xtl, xth + 1):
        for lat_tile in range(ytl, yth + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            im = Image.open(file_map[key]).convert('RGB')
            dr = ImageDraw.Draw(im)

            # grid lines
            color = ImageColor.getrgb('brown')
            dr.line([(0, 0), (0, 255)], fill=color, width=1)
            dr.line([(0, 0), (255, 0)], fill=color, width=1)
            font = ImageFont.load_default()
            lon_deg_min = xtile2geo(lon_tile, zoom_factor)
            lat_deg_min = ytile2geo(lat_tile, zoom_factor)
            lon_deg_max = xtile2geo(lon_tile + 1, zoom_factor)
            lat_deg_max = ytile2geo(lat_tile + 1, zoom_factor)
            dr.text([(127, 10)], '%f' % lat_deg_min, font=font, fill=color)
            dr.text([(10, 127)], '%f' % lon_deg_min, font=font, fill=color)

            color = ImageColor.getrgb('black')

            if xbsl > lon_tile and xbsl < lon_tile + 1:
                print('xbsl:', xbsl)
                print('lon_tile:', lon_tile)
                x_offset = (xbsl - math.floor(xbsl)) * 256
                dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)

            if  ybsl > lat_tile and ybsl < lat_tile + 1:
                print('ybsl:', ybsl)
                print('lat_tile:', lat_tile)
                y_offset = (ybsl - math.floor(ybsl)) * 256
                dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

            if xbsh > lon_tile and xbsh < lon_tile + 1:
                print('xbsh:', xbsh)
                print('lon_tile:', lon_tile)
                x_offset = (xbsh - math.floor(xbsh)) * 256
                dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)

            if ybsh > lat_tile and ybsh < lat_tile + 1:
                print('ybsh:', ybsh)
                print('lat_tile:', lat_tile)
                y_offset = (ybsh - math.floor(ybsh)) * 256
                dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

            color = ImageColor.getrgb('red')

            if xesl > lon_tile and xesl < lon_tile + 1:
                print('xesl:', xesl)
                print('lon_tile:', lon_tile)
                x_offset = (xesl - math.floor(xesl)) * 256
                dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)

            if  yesl > lat_tile and yesl < lat_tile + 1:
                print('yesl:', yesl)
                print('lat_tile:', lat_tile)
                y_offset = (yesl - math.floor(yesl)) * 256
                dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

            if xesh > lon_tile and xesh < lon_tile + 1:
                print('xesh:', xesh)
                print('lon_tile:', lon_tile)
                x_offset = (xesh - math.floor(xesh)) * 256
                dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)

            if yesh > lat_tile and yesh < lat_tile + 1:
                print('yesh:', yesh)
                print('lat_tile:', lat_tile)
                y_offset = (yesh - math.floor(yesh)) * 256
                dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

            # in_tile = in_tile_fn(lon_tile, lat_tile)
            # tile_ll_points = list(filter(in_tile, mapped_points))
            # tile_inter_points = list(map(lambda x: (int(divmod(x[0], 1)[1] * 256), int(divmod(x[1], 1)[1] * 256)), tile_ll_points))

            # color = ImageColor.getrgb('blue')
            # if len(tile_inter_points) > 0:
            #     dr.point(tile_inter_points, fill=color)

            im.save(file_map[key])

    print('xtl:', xtl)
    print('xth:', xth)
    print('ytl:', ytl)
    print('yth:', yth)

    im_full = None
    for lon_tile in range(xtl, xth + 1):
        im_row = None
        for lat_tile in range(ytl, yth + 1):
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

    in_tile = in_tile_fn(lon_tile, lat_tile)
    pixel_points = mapped_to_pixel_points(mapped_points, xtl, ytl)
    pixel_points_ts = mapped_to_pixel_points(mapped_points, xtl, ytl, with_ts=True)

    color = ImageColor.getrgb('blue')

    dr = ImageDraw.Draw(im_full)
    dr.point(pixel_points, fill=color)

    im_full.save(output_file)

    gps_metadata = {
        'start_time': start_time,
        'gps_points': pixel_points_ts
    }

    # dump pixel points
    with open(output_metadata_file, 'w+') as fd:
        fd.write(json.dumps(gps_metadata))

    sh.open(output_file)


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))


