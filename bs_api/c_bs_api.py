# coding:utf-8
from ctypes import *
import os

# 加载C++编译的动态库
# lib_path = os.path.join(os.path.dirname(__file__), 'bs_api.so')  # Linux
lib_path = os.path.join(os.path.dirname(__file__), 'bs_api.dll')  # Windows
bs_lib = CDLL(lib_path)

# 函数签名定义
bs_lib.invert_blendshape_m33.argtypes = [
    POINTER(c_double),  # offset_x
    POINTER(c_double),  # offset_y
    POINTER(c_double),  # offset_z
    POINTER(c_double),  # base
    POINTER(c_double),  # m33
    c_int               # point_count
]
bs_lib.invert_blendshape_m33.restype = None

bs_lib.invert_points.argtypes = [
    POINTER(c_double),  # base
    POINTER(c_double),  # target
    POINTER(c_double),  # m33
    POINTER(c_double),  # points
    c_int               # point_count
]
bs_lib.invert_points.restype = None

bs_lib.zip_points.argtypes = [
    POINTER(c_double),  # points
    POINTER(c_int),     # ids
    c_int               # point_count
]
bs_lib.zip_points.restype = c_int

bs_lib.unzip_points.argtypes = [
    POINTER(c_double),  # points
    POINTER(c_int),     # ids
    POINTER(c_double),  # full_points
    c_int,              # use_count
    c_int               # point_count
]
bs_lib.unzip_points.restype = None

bs_lib.remove_points.argtypes = [
    POINTER(c_double),  # points
    POINTER(c_int),     # ids
    c_int,              # point_count
    c_int               # remove_count
]
bs_lib.remove_points.restype = None


# Python包装函数
def core_invert_blendshape_m33(offset_x, offset_y, offset_z, base, m33):
    """使用C++实现的invert_blendshape_m33"""
    point_count = len(base) // 3
    bs_lib.invert_blendshape_m33(
        offset_x, offset_y, offset_z, base, m33, point_count
    )


def core_invert_points(base, target, m33, points):
    """使用C++实现的invert_points"""
    point_count = len(base) // 3
    bs_lib.invert_points(base, target, m33, points, point_count)


def core_zip_points(points, ids):
    """使用C++实现的zip_points"""
    point_count = len(points) // 3
    use_length = bs_lib.zip_points(points, ids, point_count)
    return use_length


def core_unzip_points(points, ids, full_points):
    """使用C++实现的unzip_points"""
    use_count = len(ids)
    point_count = len(full_points) // 3
    bs_lib.unzip_points(points, ids, full_points, use_count, point_count)


def core_remove_points(points, ids):
    """使用C++实现的remove_points"""
    point_count = len(points) // 3
    remove_count = len(ids)
    bs_lib.remove_points(points, ids, point_count, remove_count)