#!/usr/bin/env python3
'''gen_map_video.py
Generate map video.

Usage:
  gen_map_video.py <background_image> <points_json> [--output=<OUTPUT_FILE>] [--fps=<FPS>] [--tstart=<TIME>] [--tfinish=<TIME>]
  gen_map_video.py (-h | --help)

Options:
  -h --help                 Show this screen.
  --output=<OUTPUT_FILE>    Output file name [default: map.avi]
  --fps=<FPS>               Override frames per second [default: 25]
'''
import sys
import numpy as np
import copy
import datetime
import json
import time
from lib import points_file

try:
    from docopt import docopt
    from cv2 import cv2
except ImportError as e:
    installs = ['docopt', 'opencv-python']
    sys.stderr.write('Error: %s\nTry:\n    pip install --user %s\n' % (e, ' '.join(installs)))
    sys.exit(1)


def generate_map_video(background_image, points_json_file, output_file, fps, tstart, tfinish):
    image = cv2.imread(background_image)
    height, width, _ = image.shape
    print(height, width)

    points, start_time_string = points_file.load(points_json_file)

    start_time = points_file.get_timestamp(start_time_string)
    finish_time =  points_file.get_finish_time(points)

    print(start_time)
    print(finish_time)
    total_seconds = finish_time - start_time
    print(total_seconds)

    if tstart:
        frame_start = int(tstart * fps)
    else:
        frame_start = 0

    if tfinish:
        tfinish_limited = min(tfinish, total_seconds)
        frame_finish = int(tfinish_limited * fps)
    else:
        frame_finish = int(total_seconds * fps)

    print('frame_start: ', frame_start, frame_start / fps)
    print('frame_finish:', frame_finish, frame_finish / fps)

    frames = int(total_seconds * fps)
    color = (40, 40, 255)
    thickness = 3

    fourcc = cv2.VideoWriter_fourcc(*'H264')
    video = cv2.VideoWriter(output_file, fourcc, float(fps), (width, height))

    xpos = points[0][0]
    ypos = points[0][1]
    tpos = points_file.get_timestamp(points[0][2]) - start_time
    tpos_last = tpos
    tpos_adj = tpos

    xlast = xpos
    ylast = ypos
    tlast = tpos

    for frame in range(frame_start, frame_finish):
        update_period = 1000
        if frame % update_period == 0:
            frame_total = frame + 1
            print('%3.2f %d %d' % (frame / fps, frame, frames))

        current_time = frame / fps

        while tpos_adj < current_time and len(points) > 0:
            point = points.pop(0)
            xpos = point[0]
            ypos = point[1]
            tpos = points_file.get_timestamp(point[2]) - start_time
            if tpos == tpos_last:
                tpos_adj += 1/18
            else:
                tpos_last = tpos
                tpos_adj = tpos

            xlast = xpos
            ylast = ypos
            tlast = tpos

        frame = copy.copy(image)

        cv2.circle(frame, (xlast, ylast), 15, color, thickness)
        video.write(frame)

    video.release()


def main(args):
    # print(repr(args))
    background_image = args['<background_image>']
    points_json_file = args['<points_json>']
    output_file = args['--output']
    try:
        fps = int(args['--fps'])
        tstart = tfinish = None
        if '--tstart' in args and args['--tstart'] is not None:
            tstart = float(args['--tstart'])
        if '--tfinish' in args and args['--tfinish'] is not None:
            tfinish = float(args['--tfinish'])
    except ValueError as e:
        print('Error: %s\n' % str(e))
        print(__doc__)
        return 2

    generate_map_video(background_image, points_json_file, output_file, fps, tstart, tfinish)

    return 0


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))
