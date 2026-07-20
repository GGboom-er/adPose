# coding:utf-8
"""
NumPy 后端的兼容适配层
当 C++ DLL 不可用时，此模块提供与 bs_api.py (C后端) 完全相同的接口，
底层使用 np_bs_api 中的 NumPy 实现。
"""
import numpy as np
from ctypes import c_double, c_int, memmove, byref, sizeof
from array import array


def c_double_array(lis):
    """将 Python list 转为 ctypes double 数组（与 C 后端接口兼容）"""
    a = array('d')
    a.fromlist(lis)
    c_arr = (c_double * len(lis)).from_buffer_copy(a)
    return c_arr


def invert_blendshape_m33(base, offset_x, offset_y, offset_z):
    """计算反转 BlendShape 的 3x3 矩阵（NumPy 实现）"""
    point_count = len(base) // 3
    base_np = np.array(base, dtype=np.float64).reshape(-1, 3)
    ox_np = np.array(offset_x, dtype=np.float64).reshape(-1, 3)
    oy_np = np.array(offset_y, dtype=np.float64).reshape(-1, 3)
    oz_np = np.array(offset_z, dtype=np.float64).reshape(-1, 3)

    m33_np = np.zeros((point_count, 3, 3), dtype=np.float64)
    m33_np[:, 0, :] = ox_np - base_np
    m33_np[:, 1, :] = oy_np - base_np
    m33_np[:, 2, :] = oz_np - base_np
    m33_np[:] = np.linalg.inv(m33_np)

    # 返回 ctypes 数组以保持接口兼容
    m33 = (c_double * (9 * point_count))()
    m33[:] = m33_np.reshape(-1).tolist()
    return m33


def invert_points(base, target, m33):
    """通过反转矩阵变换点（NumPy 实现）"""
    point_count = len(base) // 3
    base_np = np.array(base, dtype=np.float64).reshape(-1, 3)
    target_np = np.array(target, dtype=np.float64).reshape(-1, 3)
    m33_np = np.array(m33, dtype=np.float64).reshape(-1, 3, 3)

    world_v = target_np - base_np
    result = np.einsum("ij,ijk->ik", world_v, m33_np)

    points = (c_double * (3 * point_count))()
    points[:] = result.reshape(-1).tolist()
    return points


def zip_points(points):
    """压缩点数据，移除接近零的点（NumPy 实现）"""
    point_count = len(points) // 3
    pts = np.array(points, dtype=np.float64).reshape(-1, 3)
    norms = np.linalg.norm(pts, axis=1)
    mask = norms > 1e-5

    use_ids = np.where(mask)[0].astype(np.int32)
    use_points = pts[mask]
    use_length = len(use_ids)

    ids = (c_int * use_length)()
    ids[:] = use_ids.tolist()

    out_points = ((c_double * 3) * use_length)()
    for i in range(use_length):
        out_points[i][:] = use_points[i].tolist()

    return ids, out_points


def c_int_array(lis):
    """将 Python list 转为 ctypes int 数组"""
    a = array('i')
    a.fromlist(lis)
    c_arr = (c_int * len(lis)).from_buffer_copy(a)
    return c_arr


def c_points(points):
    """转换点数据为 ctypes 格式"""
    c_pts = ((c_double * 4) * len(points))()
    c_pts[:] = points
    _c_pts = (c_double * (4 * len(points))).from_buffer_copy(c_pts)
    return _c_pts


def unzip_points(ids, points, point_count):
    """解压缩点数据，恢复完整数组（NumPy 实现）"""
    full_points = (c_double * (3 * point_count))()
    full_np = np.zeros(3 * point_count, dtype=np.float64)

    if len(ids) > 0:
        ids_list = list(ids)
        pts_np = np.array(points, dtype=np.float64).reshape(-1, 4)[:, :3]
        for i, idx in enumerate(ids_list):
            full_np[idx * 3:idx * 3 + 3] = pts_np[i]

    full_points[:] = full_np.tolist()
    return full_points


def remove_points(points, ids):
    """移除指定的点（设为0）"""
    ids_list = list(ids)
    for idx in ids_list:
        points[idx * 3] = 0.0
        points[idx * 3 + 1] = 0.0
        points[idx * 3 + 2] = 0.0


def merge_points(*args):
    """合并多个点数组"""
    total = sum(len(a) for a in args)
    out = (c_double * total)()
    offset = 0
    for a in args:
        n = len(a)
        memmove(byref(out, offset * sizeof(c_double)), a, n * sizeof(c_double))
        offset += n
    return out
