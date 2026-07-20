# coding:utf-8
from array import array
from .c_bs_api import *


def c_double_array(lis):
    a = array('d')
    a.fromlist(lis)
    c_arr = (c_double * len(lis)).from_buffer_copy(a)
    return c_arr


def invert_blendshape_m33(base, offset_x, offset_y, offset_z):
    base, offset_x, offset_y, offset_z = map(c_double_array, [base, offset_x, offset_y, offset_z])
    point_count = len(base)//3
    m33 = (c_double*(9*point_count))()
    core_invert_blendshape_m33(offset_x, offset_y, offset_z, base, m33)
    return m33

def invert_points(base, target, m33):
    point_count = len(base)//3
    target = c_double_array(target)
    if isinstance(base, list):
        base = c_double_array(base)
    points = (c_double*(3*point_count))()
    core_invert_points(base, target, m33, points)
    return points

def zip_points(points):
    point_count = len(points) // 3
    ids = (c_int*point_count)()
    use_length = core_zip_points(points, ids)
    ids = (c_int*use_length).from_buffer_copy(ids)
    points = ((c_double*3)*use_length).from_buffer_copy(points)
    return ids, points


def c_int_array(lis):
    a = array('i')
    a.fromlist(lis)
    c_arr = (c_int * len(lis)).from_buffer_copy(a)
    return c_arr

def c_points(points):
    c_points = ((c_double * 4) * len(points))()
    c_points[:] = points
    _c_points = (c_double * (4 * len(points))).from_buffer_copy(c_points)
    return _c_points

def unzip_points(ids, points, point_count):
    ids = c_int_array(ids)
    points = c_points(points)
    full_points = (c_double*(3*point_count))()
    core_unzip_points(points, ids, full_points)
    return full_points

def remove_points(points, ids):
    ids = c_int_array(ids)
    core_remove_points(points, ids)


def merge_points(*args):
    total = sum(len(a) for a in args)
    out = (c_double * total)()
    offset = 0
    for a in args:
        n = len(a)
        memmove(byref(out, offset * sizeof(c_double)), a, n * sizeof(c_double))
        offset += n
    return out