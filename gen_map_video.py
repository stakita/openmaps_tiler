#!/usr/bin/env python3
'''gen_map_video.py
Generate map video.

Usage:
  gen_waveform_slider.py <background_image> <points_json> [--output=<OUTPUT_FILE>] [--fps=<FPS>] [--tstart=<TIME>] [--tfinish=<TIME>]
  gen_waveform_slider.py (-h | --help)

Options:
  -h --help                 Show this screen.
  --output=<OUTPUT_FILE>    Output file name [default: map.avi]
  --fps=<FPS>               Override frames per second [default: 24]
'''
import sys
import numpy as np
import copy
import datetime
import json
import time

try:
    import cv2
except ImportError as e:
    sys.stderr.write('Error: %s\nTry:\n    pip install opencv-python\n' % e)
    sys.exit(1)


try:
    from docopt import docopt
except ImportError as e:
    sys.stderr.write('Error: %s\nTry:\n    pip3 install --user docopt\n' % e)
    sys.exit(1)


def load_points_file(filename):
    with open(filename) as fd:
        body = fd.read()
    points_data = json.loads(body)
    return points_data


def get_start_time(points):
    time_string = points[0][2]
    return get_timestamp(time_string)


def get_finish_time(points):
    time_string = points[-1][2]
    return get_timestamp(time_string)


def get_timestamp(time_string):
    # dt = datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%f%z")
    dt = datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S%z")
    return dt.timestamp()


def generate_map_video(background_image, points_json_file, output_file, fps, tstart, tfinish):
    image = cv2.imread(background_image)
    height, width, _ = image.shape
    print(height, width)

    points = load_points_file(points_json_file)

    start_time = get_start_time(points)
    finish_time =  get_finish_time(points)

    print(start_time)
    print(finish_time)
    total_seconds = finish_time - start_time
    # total_seconds = 10
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

    # fourcc = cv2.VideoWriter_fourcc(*'MP42')
    fourcc = cv2.VideoWriter_fourcc(*'H264')
    video = cv2.VideoWriter(output_file, fourcc, float(fps), (width, height))

    xpos = points[0][0]
    ypos = points[0][1]
    tpos = get_timestamp(points[0][2]) - start_time
    tpos_last = tpos
    tpos_adj = tpos

    xlast = xpos
    ylast = ypos
    tlast = tpos

    t0 = t1 = t2 = t3 = t4 = t5 = 0
    s1 = s2 = s3 = s4 = s5 = 0

    for frame in range(frame_start, frame_finish):
        t0 = time.time()
        update_period = 1000
        if frame % update_period == 0:
            frame_total = frame + 1
            # print('%3.2f %d %d' % (frame / 24, frame, frames))
            print('%3.2f %d %d  a1 = %f, a2 = %f, a3 = %f, a4 = %f, a5 = %f' % (frame / 24, frame, frames, s1 / frame_total, s2 / frame_total, s3 / frame_total, s4 / frame_total, s5 / frame_total))

        current_time = frame / 24.0

        t1 = time.time()

        while tpos_adj < current_time and len(points) > 0:
            point = points.pop(0)
            xpos = point[0]
            ypos = point[1]
            tpos = get_timestamp(point[2]) - start_time
            if tpos == tpos_last:
                tpos_adj += 1/18
            else:
                tpos_last = tpos
                tpos_adj = tpos

            xlast = xpos
            ylast = ypos
            tlast = tpos

        t2 = time.time()
        frame = copy.copy(image)

        t3 = time.time()
        cv2.circle(frame, (xlast, ylast), 15, color, thickness)
        t4 = time.time()
        video.write(frame)
        t5 = time.time()

        s1 += t1 - t0
        s2 += t2 - t1
        s3 += t3 - t2
        s4 += t4 - t3
        s5 += t5 - t4

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
