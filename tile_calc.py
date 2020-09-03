import math
import sh
import sys
import os
import time
from PIL import Image
from PIL import ImageDraw

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xfloat = (lon_deg + 180.0) / 360.0 * n
    xtile = int(xfloat)
    yfloat = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    ytile = int(yfloat)
    print(xfloat, yfloat)
    return (xtile, ytile, xfloat, yfloat)

def get_zll(lat_deg, lon_deg, zoom):
    xtile, ytile, xfloat, yfloat = deg2num(lat_deg, lon_deg, zoom)
    timestamp = int(time.time())
    output_filename = '%d_%d_%d.%d.png' % (zoom, xtile, ytile, timestamp)
    output_marked_filename = '%d_%d_%d.%d.marked.png' % (zoom, xtile, ytile, timestamp)
    print('run curl ' + ' '.join(['https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, xtile, ytile), '--output', output_filename]))
    sh.curl('https://tile.openstreetmap.org/%d/%d/%d.png' % (zoom, xtile, ytile), '--output', output_filename)
    # sh.open(output_filename)

    im = Image.open(output_filename)
    dr = ImageDraw.Draw(im)

    x_rem = xfloat - xtile
    y_rem = yfloat - ytile
    x_tile_offset = int(x_rem * 256)
    y_tile_offset = int(y_rem * 256)

    dr.line([(x_tile_offset, 0), (x_tile_offset, im.size[0])], width=1)
    dr.line([(0, y_tile_offset), (im.size[1], y_tile_offset)], width=1)

    im.save(output_marked_filename, 'PNG')

    sh.open(output_marked_filename)

if __name__ == '__main__':
    get_zll(float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]))

