from collections import namedtuple

# Coordinate = namedtuple("Coordinate", "lon lat")
# TilePoint = namedtuple("TilePoint", "x y zoom")
# PixelPoint = namedtuple("PixelPoint", "x y")
CoordinateExtents = namedtuple("CoordinateExtents", "lon_max lon_min lat_max lat_min")


def calculate_best_zoom_factor(points_list, pad_percent):
    # extents = get_track_geo_extents(points_list)
    
    pass


def get_track_geo_extents(points_iter):
    ''' Calculate the maximum and minimum values of lon and lat for the track points '''

    point = next(points_iter)
    lat_max = point['lat']
    lat_min = point['lat']
    lon_max = point['lon']
    lon_min = point['lon']

    for point in points_iter:
        if point['lat'] < lat_min:
            lat_min = point['lat']
        if point['lat'] > lat_max:
            lat_max = point['lat']
        if point['lon'] < lon_min:
            lon_min = point['lon']
        if point['lon'] > lon_max:
            lon_max = point['lon']

    return CoordinateExtents(lon_max, lon_min, lat_max, lat_min)
