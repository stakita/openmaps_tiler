import sys
import os
import math

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from openstreetmaps_tiler import openstreetmaps as osm  # pylint: disable=E0401


def test_coordinate_to_tile_point():
    c = osm.Coordinate(151.20503342941282, -33.85904467277486) # Observatory hill - Sydney

    t = osm.coordinate_to_tile_point(c, 0)
    assert math.isclose(t.x, 0.9200139817483689)
    assert math.isclose(t.y, 0.600059617392878)

    t = osm.coordinate_to_tile_point(c, 19)
    assert math.isclose(t.x, 482352.29046288884)
    assert math.isclose(t.y, 314604.05668367725)


def test_coordinate_to_pixel_point():
    c = osm.Coordinate(151.20503342941282, -33.85904467277486) # Observatory hill - Sydney

    p = osm.coordinate_to_pixel_point(c, 0)
    assert math.isclose(p.x, 235.52357932758244)
    assert math.isclose(p.y, 153.61526205257678)
    p = osm.coordinate_to_pixel_point(c, 19)
    assert math.isclose(p.x, 123482186.35849954)
    assert math.isclose(p.y, 80538638.51102138)


def test_tile_point_to_coordinate():
    c_expected = osm.Coordinate(151.20503342941282, -33.85904467277486) # Observatory hill - Sydney

    t = osm.TilePoint(0.9200139817483689, 0.600059617392878, 0)
    c = osm.tile_point_to_coordinate(t)
    assert math.isclose(c.lat, c_expected.lat)
    assert math.isclose(c.lon, c_expected.lon)

    t = osm.TilePoint(482352.29046288884, 314604.05668367725, 19)
    c = osm.tile_point_to_coordinate(t)
    assert math.isclose(c.lat, c_expected.lat)
    assert math.isclose(c.lon, c_expected.lon)


def test_pixel_point_to_coordinate():
    c_expected = osm.Coordinate(151.20503342941282, -33.85904467277486) # Observatory hill - Sydney

    p = osm.PixelPoint(235.52357932758244, 153.61526205257678, 0)
    c = osm.pixel_point_to_coordinate(p)
    assert math.isclose(c.lon, c_expected.lon)
    assert math.isclose(c.lat, c_expected.lat)

    p = osm.PixelPoint(123482186.35849954, 80538638.51102138, 19)
    c = osm.pixel_point_to_coordinate(p)
    assert math.isclose(c.lon, c_expected.lon)
    assert math.isclose(c.lat, c_expected.lat)


def test_tile_point_to_pixel_point():
    p_expected = osm.PixelPoint(235.52357932758244, 153.61526205257678, 0)
    t = osm.TilePoint(0.9200139817483689, 0.600059617392878, 0)
    p = osm.tile_point_to_pixel_point(t)
    assert math.isclose(p.x, p_expected.x)
    assert math.isclose(p.y, p_expected.y)
    assert p.zoom == p_expected.zoom

    p_expected = osm.PixelPoint(123482186.35849954, 80538638.51102138, 19)
    t = osm.TilePoint(482352.29046288884, 314604.05668367725, 19)
    p = osm.tile_point_to_pixel_point(t)
    assert math.isclose(p.x, p_expected.x)
    assert math.isclose(p.y, p_expected.y)
    assert p.zoom == p_expected.zoom


def test_tile_reference():
    t = osm.TilePoint(0.9200139817483689, 0.600059617392878, 0)
    r = osm.tile_reference(t)
    assert r.x == 0
    assert r.y == 0
    assert r.zoom == 0

    t = osm.TilePoint(482352.29046288884, 314604.05668367725, 19)
    r = osm.tile_reference(t)
    assert r.x == 482352
    assert r.y == 314604
    assert r.zoom == 19
