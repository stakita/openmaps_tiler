import math
import tile_dl

try:
    from PIL import Image
    from PIL import ImageDraw, ImageColor, ImageFont
except ImportError as e:
    sys.stderr.write('Error: %s\nTry:\n    pip install --user Pillow\n' % e)
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


def xdeg2scaled(lon_deg, zoom):
    n = 2.0 ** zoom
    xfloat = (lon_deg + 180.0) / 360.0 * n

    return xfloat

def ydeg2scaled(lat_deg, zoom):
    n = 2.0 ** zoom
    lat_rad = math.radians(lat_deg)
    yfloat = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n

    return yfloat


def xdeg2num(lon_deg, zoom):
    # n = 2.0 ** zoom
    # xfloat = (lon_deg + 180.0) / 360.0 * n
    # xtile = int(xfloat)
    return int(xdeg2scaled(lon_deg, zoom))


def ydeg2num(lat_deg, zoom):
    # n = 2.0 ** zoom
    # lat_rad = math.radians(lat_deg)
    # yfloat = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    # ytile = int(yfloat)
    return int(ydeg2scaled(lat_deg, zoom))


def xindex2lon(xindex, zoom):
    n = 2.0 ** zoom
    lon_deg = (xindex / n * 360) - 180.0
    return lon_deg


def yindex2lat(yindex, zoom):
    n = 2.0 ** zoom
    lat_deg = math.degrees(math.atan(math.sinh((- (yindex / n * 2.0) + 1.0) * math.pi)))
    return lat_deg


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


def find_best_zoom(xl, xh, yl, yh, xtiles, ytiles, zoom_max=19):
    print('xl: %f, xh: %f, yl: %f, yh: %f, xtiles: %f, ytiles: %f, zoom_max: %f' % (xl, xh, yl, yh, xtiles, ytiles, zoom_max))
    # loop until either x or y has sufficient tile coverage
    for zoom in range(zoom_max + 1):
        print('zoom:', zoom)
        xsl = xdeg2scaled(xl, zoom) # x scaled lo
        xsh = xdeg2scaled(xh, zoom) # x scaled hi
        ysl = ydeg2scaled(yl, zoom) # y scaled lo
        ysh = ydeg2scaled(yh, zoom) # y scaled hi

        print('xsl:', xsl)
        print('xsh:', xsh)
        print('ysl:', ysl)
        print('ysh:', ysh)

        if (ysh - ysl) > ytiles:
            print('find_best_zoom: y max')
            return zoom
        if (xsh - xsl) > xtiles:
            print('find_best_zoom: x max')
            return zoom
    return zoom_max


def main():
    x1 = -122.1143822
    y1 = 37.4566362

    x2 = -122.1108545
    y2 = 37.4528755

    xil = min(x1, x2) # x input lo
    xih = max(x1, x2) # x input hi
    yil = min(y1, y2) # y input lo
    yih = max(y1, y2) # y input hi
    xis = xih - xil # x input span
    yis = yih - yil # x input span

    border_factor = 1.2
    x_tiles = 3
    y_tiles = 1
    # x_tiles = 1
    # y_tiles = 1
    zoom_max = 19

    print('xil:', xil)
    print('xih:', xih)
    print('yil:', yil)
    print('yih:', yih)
    print('xis:', xis)
    print('yis:', yis)

    zoom_factor = find_best_zoom(xil, xih, yih, yil, x_tiles, y_tiles)
    print('zoom_factor:', zoom_factor)

    # desired_aspect_ratio = 1408 / 872
    # aspect_ratio = xis / yis
    # print('desired_aspect_ratio:', desired_aspect_ratio)
    # print('aspect_ratio:', aspect_ratio)

    # if aspect_ratio < desired_aspect_ratio:
    #     print('fix x')
    #     new_x_span = xis * desired_aspect_ratio / aspect_ratio
    #     print('new_x_span:', new_x_span)
    #     x_mid = (xih + xil) / 2
    #     print('x_mid:', x_mid)
    #     xel = x_mid - (new_x_span / 2) # x extent lo
    #     xeh = x_mid + (new_x_span / 2) # x extent hi
    #     yel = yil                      # y extent lo
    #     yeh = yih                      # y extent hi
    # else:
    #     print('fix y')
    #     new_y_span = yis * aspect_ratio / desired_aspect_ratio
    #     print('new_y_span:', new_y_span)
    #     y_mid = (yih + yil) / 2
    #     print('y_mid:', y_mid)
    #     yel = y_mid - (new_y_span / 2) # y extent lo
    #     yeh = y_mid + (new_y_span / 2) # y extent hi
    #     xel = xil                      # x extent lo
    #     xeh = xih                      # x extent hi

    # print('yel:', yel)
    # print('yeh:', yeh)
    # print('xel:', xel)
    # print('xeh:', xeh)

    # xes = xeh - xel # x extent span
    # yes = yeh - yel # x extent span

    # extent_aspect_ratio = xes / yes
    # print('extent_aspect_ratio:', extent_aspect_ratio)

    x1 = xil
    y1 = yil
    x2 = xih
    y2 = yih

    print('-' * 80)


    x_angle_diff = abs(abs(x1) - abs(x2))

    x_zoom_angle = (x_angle_diff * border_factor) / x_tiles
    print(x_zoom_angle)
    x_zoom_factor = zoom_factor_bounded(x_zoom_angle, zoom_max)
    print(x_zoom_factor)
    print('x_zoom_factor:', x_zoom_factor)

    x_tile_angle = zoom_tile_angle(x_zoom_factor)
    print('x_tile_angle:', x_tile_angle)

    print('x_angle_diff:', x_angle_diff)
    x_tiles = math.ceil(x_angle_diff / x_tile_angle)

    print('x_tiles:', x_tiles)


    print('-' * 80)

    y_angle_diff = abs(abs(y1) - abs(y2))

    y_zoom_angle = (abs(abs(y1) - abs(y2)) * border_factor) / y_tiles
    print(y_zoom_angle)
    y_zoom_factor = zoom_factor_bounded(y_zoom_angle, zoom_max)
    print(y_zoom_factor)
    print('zoom_factor:', y_zoom_factor)

    y_tile_angle = zoom_tile_angle(y_zoom_factor)
    print('y_tile_angle:', y_tile_angle)

    print('y_angle_diff:', y_angle_diff)
    y_tiles = math.ceil(y_angle_diff / y_tile_angle)

    print('y_tiles:', y_tiles)


    print('=' * 80)

    zoom_factor = min(x_zoom_factor, y_zoom_factor)
    print('zoom_factor', zoom_factor)

    x_lo_scaled = xdeg2scaled(xil, zoom_factor)
    x_hi_scaled = xdeg2scaled(xih, zoom_factor)
    y_lo_scaled = ydeg2scaled(yil, zoom_factor)
    y_hi_scaled = ydeg2scaled(yih, zoom_factor)

    x1_tile = xdeg2num(x1, zoom_factor)
    x2_tile = xdeg2num(x2, zoom_factor)
    print('x1_tile:', x1_tile)
    print('x2_tile:', x2_tile)

    x_hi = max(x1_tile, x2_tile)
    x_lo = min(x1_tile, x2_tile)

    print('x_hi:', x_hi)
    print('x_lo:', x_lo)

    y1_tile = ydeg2num(y1, zoom_factor)
    y2_tile = ydeg2num(y2, zoom_factor)
    print('y1_tile:', y1_tile)
    print('y2_tile:', y2_tile)

    y_hi = max(y1_tile, y2_tile)
    y_lo = min(y1_tile, y2_tile)

    print('y_hi:', y_hi)
    print('y_lo:', y_lo)

    file_map = {}

    for lon_tile in range(x_lo, x_hi + 1):
        for lat_tile in range(y_lo, y_hi + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            output_filename = 'tile_%06d_%06d_%02d.png' % (lon_tile, lat_tile, zoom_factor)
            file_map[key] = output_filename
            tile_dl.get_tile(lat_tile, lon_tile, zoom_factor, output_filename)

    print(file_map)

    for lon_tile in range(x_lo, x_hi + 1):
        for lat_tile in range(y_lo, y_hi + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            im = Image.open(file_map[key]).convert('RGB')
            dr = ImageDraw.Draw(im)
            color = ImageColor.getrgb('red')
            dr.line([(0, 0), (0, 255)], fill=color, width=1)
            dr.line([(0, 0), (255, 0)], fill=color, width=1)
            font = ImageFont.load_default()
            lon_deg_min = xindex2lon(lon_tile, zoom_factor)
            lat_deg_min = yindex2lat(lat_tile, zoom_factor)
            lon_deg_max = xindex2lon(lon_tile + 1, zoom_factor)
            lat_deg_max = yindex2lat(lat_tile + 1, zoom_factor)
            dr.text([(127, 10)], '%f' % lat_deg_min, font=font, fill=color)
            dr.text([(10, 127)], '%f' % lon_deg_min, font=font, fill=color)

            color = ImageColor.getrgb('blue')

            print('x_lo_scaled:', x_lo_scaled)
            print('lon_tile:', lon_tile)
            print('y_lo_scaled:', y_lo_scaled)
            print('lat_tile:', lat_tile)

            if x_lo_scaled > lon_tile and x_lo_scaled < lon_tile + 1 and y_lo_scaled > lat_tile and y_lo_scaled < lat_tile + 1:
                x_offset = (x_lo_scaled - math.floor(x_lo_scaled)) * 256
                y_offset = (y_lo_scaled - math.floor(y_lo_scaled)) * 256

                dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)
                dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

            if x_hi_scaled > lon_tile and x_hi_scaled < lon_tile + 1 and y_hi_scaled > lat_tile and y_hi_scaled < lat_tile + 1:
                x_offset = (x_hi_scaled - math.floor(x_hi_scaled)) * 256
                y_offset = (y_hi_scaled - math.floor(y_hi_scaled)) * 256

                dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)
                dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

    # x_hi_scaled = xdeg2scaled(x_hi_deg)
    # y_lo_scaled = ydeg2scaled(y_lo_deg)
    # y_hi_scaled = ydeg2scaled(y_hi_deg)

            # color = ImageColor.getrgb('red')
            # dr.line([(0, 0), (0, 255)], fill=color, width=1)
            # dr.line([(0, 0), (255, 0)], fill=color, width=1)

            im.save(file_map[key])


    im_full = None
    for lon_tile in range(x_lo, x_hi + 1):
        im_row = None
        for lat_tile in range(y_lo, y_hi + 1):
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

    im_full.save('output2.png')


if __name__ == '__main__':
    main()
