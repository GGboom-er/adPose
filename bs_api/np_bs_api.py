import numpy as np

def core_invert_blendshape_m33(offset_x, offset_y, offset_z, base, m33):
    offset_x, offset_y, offset_z, base, m33 = map(np.ctypeslib.as_array, [offset_x, offset_y, offset_z, base, m33])
    m33 = m33.reshape(-1, 3, 3)
    m33[:, 0, :] = (offset_x - base).reshape(-1, 3)
    m33[:, 1, :] = (offset_y - base).reshape(-1, 3)
    m33[:, 2, :] = (offset_z - base).reshape(-1, 3)
    m33[:] = np.linalg.inv(m33)


def core_invert_points(base, target, m33, points):
    base, target, m33, points = map(np.ctypeslib.as_array, [base, target, m33, points])
    world_v = (target - base).reshape(-1, 3)
    m33 = m33.reshape(-1, 3, 3)
    points[:] = np.einsum("ij,ijk->ik", world_v, m33).reshape(-1)


def core_zip_points(points, ids):
    point_count = len(points) // 3
    points = np.ctypeslib.as_array(points).reshape(-1, 3)
    use_slice = np.linalg.norm(points, axis=1) > 1e-5
    full_ids = np.arange(point_count, dtype=np.int32)
    use_ids = full_ids[use_slice]
    use_length = len(use_ids)
    ids[:use_length] = use_ids
    use_points = points[use_slice]
    points[:use_length] = use_points
    return use_length


def core_unzip_points(points, ids, full_points):
    points, ids, full_points = map(np.ctypeslib.as_array, [points, ids, full_points])
    full_points = full_points.reshape(-1, 3)
    full_points[:] = 0.0
    full_points[ids] = points.reshape(-1, 4)[:, :3]


def core_remove_points(points, ids):
    points, ids = map(np.ctypeslib.as_array, [points, ids])
    points = points.reshape(-1, 3)
    points[ids] = 0.0