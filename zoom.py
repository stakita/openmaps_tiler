import math

x1 = 37.4566362
y1 = -122.1143822

x2 = 37.4528755
y2 = -122.1108545

border_factor = 1.2
x_tiles = 5.5
y_tiles = 3.5
zoom_max = 20


def zoom_tile_angle(zoom):
    print('zoom_tile_angle:', zoom)
    print('2**zoom', 2**zoom)
    zoom_angle = 360 / (2**zoom)
    print('zoom_angle:', zoom_angle)
    return zoom_angle


def zoom_factor(in_zoom):

    for i in range(zoom_max + 1):
        zoom_angle = 360 / (2**i)
        if zoom_angle < in_zoom:
            return i
    return zoom_max


def xdeg2num(lon_deg, zoom):
    n = 2.0 ** zoom
    xfloat = (lon_deg + 180.0) / 360.0 * n
    xtile = int(xfloat)

    # yfloat = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    # ytile = int(yfloat)
    # print(xfloat, yfloat)
    return xtile



x_angle_diff = abs(abs(x1) - abs(x2))

x_zoom_angle = (x_angle_diff * border_factor) / x_tiles
print(x_zoom_angle)
x_zoom_factor =zoom_factor(x_zoom_angle)
print(x_zoom_factor)
print('x_zoom_factor:', x_zoom_factor)

x_tile_angle = zoom_tile_angle(x_zoom_factor)
print('x_tile_angle:', x_tile_angle)

print('x_angle_diff:', x_angle_diff)
x_tiles = math.ceil(x_angle_diff / x_tile_angle)

print('x_tiles:', x_tiles)


print('-' * 80)

y_zoom_angle = (abs(abs(y1) - abs(y2)) * border_factor) / y_tiles
print(y_zoom_angle)
y_zoom_factor =zoom_factor(y_zoom_angle)
print(y_zoom_factor)
print('zoom_factor:', y_zoom_factor)

y_tile_angle = zoom_tile_angle(y_zoom_factor)
print('y_tile_angle:', y_tile_angle)

print('=' * 80)

zoom_factor = max(x_zoom_factor, y_zoom_factor)
print('zoom_factor', zoom_factor)

x1_tile = xdeg2num(x1, x_zoom_factor)
x2_tile = xdeg2num(x2, x_zoom_factor)
print('x1_tile:', x1_tile)
print('x2_tile:', x2_tile)

