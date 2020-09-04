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
    x_tiles = 2
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

    x1 = xil
    y1 = yil
    x2 = xih
    y2 = yih

    # The mapping can invert the magnitude of the numbers
    xsl = min(xdeg2scaled(xih, zoom_factor), xdeg2scaled(xil, zoom_factor))     # x scaled lo
    xsh = max(xdeg2scaled(xih, zoom_factor), xdeg2scaled(xil, zoom_factor))     # x scaled hi
    ysl = min(ydeg2scaled(yih, zoom_factor), ydeg2scaled(yil, zoom_factor))     # y scaled lo
    ysh = max(ydeg2scaled(yih, zoom_factor), ydeg2scaled(yil, zoom_factor))     # y scaled hi

    print('xsh:', xsh)
    print('xsl:', xsl)
    print('ysh:', ysh)
    print('ysl:', ysl)

    xtl = int(xsl)     # x tile lo
    xth = int(xsh)     # x tile hi
    ytl = int(ysl)     # y tile lo
    yth = int(ysh)     # y tile hi

    file_map = {}

    for lon_tile in range(xtl, xth + 1):
        for lat_tile in range(ytl, yth + 1):
            key = (lon_tile, lat_tile)
            print(lon_tile, lat_tile)
            output_filename = 'tile_%06d_%06d_%02d.png' % (lon_tile, lat_tile, zoom_factor)
            file_map[key] = output_filename
            tile_dl.get_tile(lat_tile, lon_tile, zoom_factor, output_filename)

    print(file_map)

    for lon_tile in range(xtl, xth + 1):
        for lat_tile in range(ytl, yth + 1):
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

            if xsl > lon_tile and xsl < lon_tile + 1 and ysl > lat_tile and ysl < lat_tile + 1:
                print('xsl:', xsl)
                print('lon_tile:', lon_tile)
                print('ysl:', ysl)
                print('lat_tile:', lat_tile)

                x_offset = (xsl - math.floor(xsl)) * 256
                y_offset = (ysl - math.floor(ysl)) * 256

                dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)
                dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

            if xsh > lon_tile and xsh < lon_tile + 1 and ysh > lat_tile and ysh < lat_tile + 1:
                print('xsh:', xsh)
                print('lon_tile:', lon_tile)
                print('ysh:', ysh)
                print('lat_tile:', lat_tile)

                x_offset = (xsh - math.floor(xsh)) * 256
                y_offset = (ysh - math.floor(ysh)) * 256

                dr.line([(x_offset, 0), (x_offset, 255)], fill=color, width=1)
                dr.line([(0, y_offset), (255, y_offset)], fill=color, width=1)

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

    im_full.save('output2.png')


if __name__ == '__main__':
    main()
