# coding:utf-8
from maya.OpenMaya import *
from maya.OpenMayaAnim import *


def str_to_dag_path(name, dag_path):
    selection_list = MSelectionList()
    selection_list.add(name)
    selection_list.getDagPath(0, dag_path)


def str_to_depend_node(name, depend_node):
    selection_list = MSelectionList()
    selection_list.add(name)
    selection_list.getDependNode(0, depend_node)


def get_mesh_points(polygon_name,  points):
    dag_path = MDagPath()
    str_to_dag_path(polygon_name, dag_path)
    fn_mesh = MFnMesh(dag_path)
    fn_mesh.getPoints(points)


def set_mesh_points(polygon_name,  points):
    dag_path = MDagPath()
    str_to_dag_path(polygon_name, dag_path)
    fn_mesh = MFnMesh(dag_path)
    fn_mesh.setPoints(points)


def get_ipt_ict(bs_name, index):
    depend_node = MObject()
    str_to_depend_node(bs_name, depend_node)
    fn_depend_node = MFnDependencyNode(depend_node)
    iti = fn_depend_node.findPlug("it").elementByLogicalIndex(0).child(0).elementByLogicalIndex(index).child(0).\
        elementByLogicalIndex(6000)
    ipt = iti.child(iti.numChildren()-2)
    ict = iti.child(iti.numChildren()-1)
    return ipt, ict


def set_plug_ids(plug, ids):
    fn_ids = MFnSingleIndexedComponent()
    ids_obj = fn_ids.create(MFn.kMeshVertComponent)
    fn_ids.addElements(ids)
    fn_components = MFnComponentListData()
    obj = fn_components.create()
    fn_components.add(ids_obj)
    plug.setMObject(obj)


def set_plug_points(plug, points):
    fn_points = MFnPointArrayData()
    obj = fn_points.create(points)
    plug.setMObject(obj)


def set_bs_id_points(bs_name, index, ids, points):
    ipt, ict = get_ipt_ict(bs_name, index)
    set_plug_points(ipt, points)
    set_plug_ids(ict, ids)


def set_bs_points(bs_name, index, all_points):
    ids = MIntArray()
    points = MPointArray()
    vtx_length = all_points.length()
    for vtx_id in range(vtx_length):
        if all_points[vtx_id].distanceTo(MPoint()) < 0.00001:
            continue
        ids.append(vtx_id)
        points.append(all_points[vtx_id])
    set_bs_id_points(bs_name, index, ids, points)


def get_plug_points(plug, points):
    fn_points = MFnPointArrayData(plug.asMObject())
    points.copy(fn_points.array())


def get_plug_ids(plug, ids):
    fn_components = MFnComponentListData(plug.asMObject())
    component_length = fn_components.length()
    for component_id in range(component_length):
        fn_ids = MFnSingleIndexedComponent(fn_components[component_id])
        append_ids = MIntArray()
        fn_ids.getElements(append_ids)
        ids_length = append_ids.length()
        for i in range(ids_length):
            ids.append(append_ids[i])


def get_id_points(bs_name, index, ids, points):
    ipt, ict = get_ipt_ict(bs_name, index)
    get_plug_points(ipt, points)
    get_plug_ids(ict, ids)


def get_mirror_id_point_map(bs_name, index, id_point_map):
    ids = MIntArray()
    points = MPointArray()
    get_id_points(bs_name, index, ids, points)
    length = ids.length()
    for i in range(length):
        id_point_map[ids[i]] = MVector(-points[i].x, points[i].y, points[i].z)


def init_target(bs_name, index):
    set_bs_id_points(bs_name, index, MIntArray(), MPointArray())


invert_shape_matrix_cache = MMatrixArray()


def save_invert_shape_matrix(polygon_name, orig_name):
    polygon_points = MPointArray()
    orig_points = MPointArray()
    get_mesh_points(polygon_name, polygon_points)
    get_mesh_points(orig_name, orig_points)
    vtx_length = orig_points.length()
    invert_shape_matrix_cache.setLength(vtx_length)
    for xyz_id in range(3):
        offset_points = MPointArray(orig_points)
        for vtx_id in range(vtx_length):
            offset = [orig_points[vtx_id].x, orig_points[vtx_id].y, orig_points[vtx_id].z]
            offset[xyz_id] += 1
            offset_points.set(MPoint(*offset), vtx_id)
        set_mesh_points(orig_name, offset_points)
        get_mesh_points(polygon_name, offset_points)
        for vtx_id in range(vtx_length):
            offset = offset_points[vtx_id] - polygon_points[vtx_id]
            MScriptUtil.setDoubleArray(invert_shape_matrix_cache[vtx_id][xyz_id],  0, offset.x)
            MScriptUtil.setDoubleArray(invert_shape_matrix_cache[vtx_id][xyz_id],  1, offset.y)
            MScriptUtil.setDoubleArray(invert_shape_matrix_cache[vtx_id][xyz_id],  2, offset.z)
            MScriptUtil.setDoubleArray(invert_shape_matrix_cache[vtx_id][xyz_id],  3, 0.0)
    set_mesh_points(orig_name, orig_points)
    for vtx_id in range(vtx_length):
        MScriptUtil.setDoubleArray(invert_shape_matrix_cache[vtx_id][3], 0, polygon_points[vtx_id].x)
        MScriptUtil.setDoubleArray(invert_shape_matrix_cache[vtx_id][3], 1, polygon_points[vtx_id].y)
        MScriptUtil.setDoubleArray(invert_shape_matrix_cache[vtx_id][3], 2, polygon_points[vtx_id].z)
        MScriptUtil.setDoubleArray(invert_shape_matrix_cache[vtx_id][3], 3, 1.0)
        invert_shape_matrix_cache.set(invert_shape_matrix_cache[vtx_id].inverse(), vtx_id)


def cache_target(bs_name, index, polygon_name, orig_name):
    init_target(bs_name, index)
    save_invert_shape_matrix(polygon_name, orig_name)


def set_target(bs_name, index, target_name):
    points = MPointArray()
    get_mesh_points(target_name, points)
    vtx_length = points.length()
    for vtx_id in range(vtx_length):
        points.set(points[vtx_id] * invert_shape_matrix_cache[vtx_id], vtx_id)
    set_bs_points(bs_name, index, points)


def edit_target(bs_name, index, target_name, polygon_name, orig_name):
    cache_target(bs_name, index, polygon_name, orig_name)
    set_target(bs_name, index, target_name)


def edit_static_target(bs_name, index, target_name, polygon_name):
    init_target(bs_name, index)
    polygon_points = MPointArray()
    get_mesh_points(polygon_name, polygon_points)
    target_points = MPointArray()
    get_mesh_points(target_name, target_points)
    vtx_length = target_points.length()
    points = MPointArray(vtx_length)
    for vtx_id in range(vtx_length):
        vector = target_points[vtx_id]-polygon_points[vtx_id]
        point = MPoint(vector)
        points.set(point, vtx_id)
    set_bs_points(bs_name, index, points)


def dot(list1, list2):
    return sum([elem1*elem2 for elem1, elem2 in zip(list1, list2)])


def matrix_dot_list(matrix, list2):
    return [dot(list1, list2) for list1 in matrix]


def sub_list(list1, list2):
    return [elem1-elem2 for elem1, elem2 in zip(list1, list2)]


def liner_regression(data_x, data_y):
    u"""
    函数：y = b1*x1+b2*x2+b3*x3 ..... + bn * xn
    :param data_x:  函数中一组x的值/maya中每个蒙皮模型的坐标
    :param data_y: 函数中一组y的值/maya中变形模型的坐标。
    :return: slopes斜率/maya中的权重值。
    """
    slopes_length = len(data_x[0])
    slopes = [1.0/slopes_length] * slopes_length
    for i in range(10):
        for slope_index in range(slopes_length):
            other_slope_sum = 1.0 - slopes[slope_index]
            if other_slope_sum < 0.0001:
                edit_scale_list = [-1.0/(slopes_length-1)] * slopes_length
            else:
                edit_scale_list = [-slope/other_slope_sum for slope in slopes]
            # edit_scale_list 所有骨骼权重修改比例的列表
            # edit_weight 骨骼权重修改量
            edit_scale_list[slope_index] = 1.0
            xs = matrix_dot_list(data_x, edit_scale_list)
            ys = sub_list(data_y, matrix_dot_list(data_x, slopes))
            dot_xs = dot(xs, xs)
            if dot_xs < 0.00001:
                continue
            edit_weight = dot(xs, ys) / dot(xs, xs)
            slopes = [slope+edit_weight*offset_weight for slope, offset_weight in zip(slopes, edit_scale_list)]
            slopes = [max(min(slope, 1.0), 0) for slope in slopes]
            sum_slopes = sum(slopes)
            slopes = [slope/sum_slopes for slope in slopes]
    return slopes


def mirror_targets(bs_name, orig_name, src_indexes, dst_indexes):
    print "py, mirror"
    dag_path = MDagPath()
    str_to_dag_path(orig_name, dag_path)
    fn_mesh = MFnMesh(dag_path)
    points = MPointArray()
    fn_mesh.getPoints(points)
    vtx_length = points.length()
    iw_data = [[] for _ in range(vtx_length)]
    util = MScriptUtil()
    ptr = util.asIntPtr()
    for vtx_id in range(vtx_length):
        mirror_point = MPoint(-points[vtx_id].x, points[vtx_id].y, points[vtx_id].z)
        closest_point = MPoint()
        fn_mesh.getClosestPoint(mirror_point, closest_point, MSpace.kTransform, ptr)
        face_id = util.getInt(ptr)
        face_vtx_ids = MIntArray()
        fn_mesh.getPolygonVertices(face_id, face_vtx_ids)

        face_vtx_length = face_vtx_ids.length()
        min_distance = 0.001
        closest_vtx_id = -1
        for vtx_arr_id in range(face_vtx_length):
            face_vtx_id = face_vtx_ids[vtx_arr_id]
            next_distance = points[face_vtx_id].distanceTo(mirror_point)
            if next_distance < min_distance:
                min_distance = next_distance
                closest_vtx_id = face_vtx_id
        if closest_vtx_id == -1:
            data_x = [[], [], []]
            for vtx_arr_id in range(face_vtx_length):
                face_vtx_id = face_vtx_ids[vtx_arr_id]
                data_x[0].append(points[face_vtx_id].x)
                data_x[1].append(points[face_vtx_id].y)
                data_x[2].append(points[face_vtx_id].z)
            ws = liner_regression(data_x, [mirror_point.x, mirror_point.y, mirror_point.z])
            for vtx_arr_id in range(face_vtx_length):
                face_vtx_id = face_vtx_ids[vtx_arr_id]
                iw_data[vtx_id].append((face_vtx_id, ws[vtx_arr_id]))
        else:
            iw_data[vtx_id].append((closest_vtx_id, 1.0))
    for src_target_i, dst_target_i in zip(src_indexes, dst_indexes):
        id_point_map = {}
        get_mirror_id_point_map(bs_name, src_target_i, id_point_map)
        dst_points = MPointArray(vtx_length)
        for vtx_id in range(vtx_length):
            dst_point = MPoint()
            for mirror_i, mirror_w in iw_data[vtx_id]:
                dst_point += MVector(id_point_map.get(mirror_i, MPoint())) * mirror_w
            dst_points.set(dst_point, vtx_id)

        set_bs_points(bs_name, dst_target_i, dst_points)


_CACHE_ID_POINT_MAPS = []


def get_bs_id_point_map(bs_name, target_index):
    id_point_map = dict()
    ids = MIntArray()
    points = MPointArray()
    get_id_points(bs_name, target_index, ids, points)
    for i in range(ids.length()):
        id_point_map[ids[i]] = points[i]
    return id_point_map


def set_bs_id_point_map(bs_name, target_index, id_point_map):
    ids = MIntArray()
    points = MPointArray()
    for i, point in id_point_map.items():
        if MVector(point).length() < 0.00001:
            continue
        ids.append(i)
        print i
        points.append(point)
    set_bs_id_points(bs_name, target_index, ids, points)


def cache_target_points(bs_name, target_indexes):
    global _CACHE_ID_POINT_MAPS
    _CACHE_ID_POINT_MAPS = []
    target_length = len(target_indexes)
    for target_id in range(target_length):
        _CACHE_ID_POINT_MAPS.append(get_bs_id_point_map(bs_name, target_indexes[target_id]))


def load_cache_target_points(bs_name, target_indexes, ids):
    global _CACHE_ID_POINT_MAPS
    target_length = len(target_indexes)
    for target_id in range(target_length):
        target_index = target_indexes[target_id]
        cache_id_point_map = _CACHE_ID_POINT_MAPS[target_id]
        if not ids:
            set_bs_id_point_map(bs_name, target_index, cache_id_point_map)
            continue
        id_point_map = get_bs_id_point_map(bs_name, target_index)
        for i in ids:
            id_point_map[i] = cache_id_point_map.get(i, MPoint())
        set_bs_id_point_map(bs_name, target_index, id_point_map)


def api_invert_target_normal(polygon_name, orig_name, repair_polygon, target_polygon_name):

    dag_path = MDagPath()
    str_to_dag_path(repair_polygon, dag_path)
    src_fn_mesh = MFnMesh(dag_path)

    dag_path = MDagPath()
    str_to_dag_path(target_polygon_name, dag_path)
    dst_fn_mesh = MFnMesh(dag_path)

    save_invert_shape_matrix(polygon_name, orig_name)
    for i in range(src_fn_mesh.numVertices()):
        normal = MVector()
        src_fn_mesh.getVertexNormal(i, normal)
        normal *= invert_shape_matrix_cache[i]
        dst_fn_mesh.setVertexNormal(normal, i)
