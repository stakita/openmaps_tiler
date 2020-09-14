#!/usr/bin/env python3
'''gen_map_video_close.py
Generate map video.

Usage:
  gen_map_video_close.py <background_image> <points_json> [--output=<OUTPUT_FILE>] [--fps=<FPS>] [--tstart=<TIME>] [--tfinish=<TIME>] [--width=<WIDTH>] [--height=<HEIGHT>]
  gen_map_video_close.py (-h | --help)

Options:
  -h --help                 Show this screen.
  --output=<OUTPUT_FILE>    Output file name [default: map.avi]
  --fps=<FPS>               Override frames per second [default: 25]
  --width=<WIDTH>           Width of output portal [default: 1022]
  --height=<HEIGHT>         Hegith of output portal [default: 1022]
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


class GenerateError(Exception):
    pass



def load_points_file(filename):
    with open(filename) as fd:
        body = fd.read()
    gps_data = json.loads(body)
    return gps_data['gps_points'], gps_data['start_time']


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


def generate_map_video(background_image, points_json_file, output_file, fps, tstart, tfinish, width, height):
    image = cv2.imread(background_image)
    bg_height, bg_width, _ = image.shape
    print(bg_height, bg_width)

    x_portal_offset = int(width / 2)
    y_portal_offset = int(height / 2)

    expected_frame_geometry = (width, height, 3)

    points, start_time_string = load_points_file(points_json_file)

    start_time = get_timestamp(start_time_string)
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
    tstring = ''
    points_index = 0

    # t0 = t1 = t2 = t3 = t4 = t5 = 0
    # s1 = s2 = s3 = s4 = s5 = 0

    for frame in range(frame_start, frame_finish):
        # t0 = time.time()
        update_period = 1000
        if frame % update_period == 0:
            frame_total = frame + 1
            print('%3.2f %d %d' % (frame / fps, frame, frames))
            # print('%3.2f %d %d  a1 = %f, a2 = %f, a3 = %f, a4 = %f, a5 = %f' % (frame / fps, frame, frames, s1 / frame_total, s2 / frame_total, s3 / frame_total, s4 / frame_total, s5 / frame_total))

        current_time = frame / fps

        # t1 = time.time()

        while tpos_adj < current_time and points_index < len(points):
            point = points[points_index]
            points_index += 1
            xpos = point[0]
            ypos = point[1]
            tstring = point[2]
            tpos = get_timestamp(point[2]) - start_time
            if tpos == tpos_last:
                tpos_adj += 1/18
            else:
                tpos_last = tpos
                tpos_adj = tpos

            xlast = xpos
            ylast = ypos
            tlast = tpos

        # text = '%d fsec=%3.2f xlast=%d ylast=%d tpos=%d tpos_adj=%3.2f timestamp=%s points_index=%d' % (frame, current_time, xlast, ylast, tpos, tpos_adj, tstring, points_index)
        # print(text)

        # position of frame in complete background image
        frame_pos_x = xlast - x_portal_offset
        frame_pos_y = ylast - y_portal_offset

        # t2 = time.time()
        frame = copy.copy(image[frame_pos_y:frame_pos_y+height, frame_pos_x:frame_pos_x+width])
        if frame.shape != expected_frame_geometry:
            raise GenerateError('Size does not match portal: %s - expected %s' % (frame.shape, expected_frame_geometry))
        # print(repr(frame.size))
        # print(repr(frame.size) + ' ' + repr(frame.shape))
        # sys.exit(0)

        # t3 = time.time()
        cv2.circle(frame, (x_portal_offset, y_portal_offset), 15, color, thickness)

        # cv2.putText(frame, text, (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.25, color=(255, 0, 0), thickness=1)
        # t4 = time.time()
        video.write(frame)
        # t5 = time.time()

        # s1 += t1 - t0
        # s2 += t2 - t1
        # s3 += t3 - t2
        # s4 += t4 - t3
        # s5 += t5 - t4

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

        width = int(args['--width'])
        height = int(args['--height'])

    except ValueError as e:
        print('Error: %s\n' % str(e))
        print(__doc__)
        return 2

    generate_map_video(background_image, points_json_file, output_file, fps, tstart, tfinish, width, height)

    return 0


if __name__ == '__main__':
    arguments = docopt(__doc__)
    sys.exit(main(arguments))
