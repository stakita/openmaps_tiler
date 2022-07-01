import json
import dateutil.parser as dup


def load(filename):
    ''' Load GPS data json file and return the data with the start time reference of the first point '''
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
    dt = dup.parse(time_string)
    return dt.timestamp()


