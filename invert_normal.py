# coding:utf-8
from maya import cmds
from . import ADPose
from .api_lib import bs_api

# def copy_normal(src_polygon, dst_polygon):
#     src_fn_mesh = get_fn_mesh(src_polygon)
#     dst_fn_mesh = get_fn_mesh(dst_polygon)
#     for i in range(src_fn_mesh.numVertices()):
#         normal = MVector()
#         src_fn_mesh.getVertexNormal(i, normal)
#         dst_fn_mesh.setVertexNormal(normal, i)


# def test_normal():
#     cache_target("debug", "debugShapeOrig")
#     src_fn_mesh = get_fn_mesh("final")
#     dst_fn_mesh = get_fn_mesh("debugShapeOrig")
#     for i in range(src_fn_mesh.numVertices()):
#         normal = MVector()
#         src_fn_mesh.getVertexNormal(i, normal)
#         normal *= invert_shape_matrix_cache[i]
#         dst_fn_mesh.setVertexNormal(normal, i)


def get_attr_index(node, attr):
    parent_attr = cmds.attributeQuery(attr, node=node, ln=1)
    parent_name = "{node}.{parent_attr}".format(**locals())
    elem_names = cmds.listAttr(parent_name, m=1)
    elem_indexes = cmds.getAttr(parent_name, mi=1)
    if attr in elem_names:
        return elem_indexes[elem_names.index(attr)]
    return 0


def rebuild_target(bs_name, target_name):
    index = get_attr_index(bs_name, target_name)
    cmds.sculptTarget(bs_name, e=1, regenerate=1, target=index)
    igt_name = "{bs_name}.it[0].itg[{index}].iti[6000].igt".format(**locals())
    target_polygon_name = cmds.listConnections(igt_name, s=1, d=1)[0]
    polygon_name = cmds.listRelatives(cmds.blendShape(bs_name, q=1, g=1)[0], p=1)[0]
    _target_polygon_name = polygon_name + "_RepairNormal_" + target_name
    if target_polygon_name != _target_polygon_name:
        target_polygon_name = cmds.rename(target_polygon_name, _target_polygon_name)
    cmds.setAttr(target_polygon_name+".v", 0)
    return target_polygon_name


def get_orig(polygon):
    orig_list = [shape for shape in cmds.listRelatives(polygon, s=1) if cmds.getAttr(shape+".io")]
    orig_list.sort(key=lambda x: len(set(cmds.listConnections(x, s=0, d=1))))
    print orig_list
    if orig_list:
        return orig_list[-1]


# def repair_target_normal():
#     bs_name = "PL019C_HD_C_02_bs"
#     polygon_name = cmds.listRelatives(cmds.blendShape(bs_name, q=1, g=1)[0], p=1)[0]
#     target_name = "Shoulder_L_a90_d0"
#     target_polygon_name = rebuild_target(bs_name, target_name)
#     temp_normal_polygon = cmds.duplicate(polygon_name, n="temp_normal_"+polygon_name)[0]
#     cmds.select(temp_normal_polygon)
#     cmds.polyNormalPerVertex(ufn=True)
#     orig_name = get_orig(polygon_name)
#     src_fn_mesh = get_fn_mesh(temp_normal_polygon)
#     dst_fn_mesh = get_fn_mesh(target_polygon_name)
#     cmds.setAttr(bs_name+".envelope", 0)
#     cache_target(polygon_name, orig_name)
#     for i in range(src_fn_mesh.numVertices()):
#         normal = MVector()
#         src_fn_mesh.getVertexNormal(i, normal)
#         normal *= invert_shape_matrix_cache[i]
#         dst_fn_mesh.setVertexNormal(normal, i)
#     cmds.delete(temp_normal_polygon)


def is_shape(polygon_name, typ="mesh"):
    # 判断物体是否存在
    if not cmds.objExists(polygon_name):
        return False
    # 判断类型是否为transform
    if cmds.objectType(polygon_name) != "transform":
        return False
    # 判断是否有形节点
    shapes = cmds.listRelatives(polygon_name, s=1, f=1)
    if not shapes:
        return False
    # 判断形节点类型是否时typ
    if cmds.objectType(shapes[0]) != typ:
        return False
    return True


def get_selected_polygons():
    return filter(is_shape, cmds.ls(sl=1, type="transform"))


def set_pose(target_name):
    ADPose.ADPoses.set_pose_by_targets([target_name])


def find_bs(polygon):
    for bs in cmds.ls(cmds.listHistory(polygon), type="blendShape") or []:
        return bs


def get_repair_polygons(polygons):
    repair_polygons = []
    comb_polygons = []
    for polygon in polygons:
        repair_polygons.append(cmds.duplicate(polygon, n="repair_"+polygon)[0])
        comb_polygons.append(cmds.duplicate(polygon, n="comb_"+polygon)[0])
    if len(comb_polygons) > 1:
        comb_polygon = cmds.polyUnite(comb_polygons, n="temp_comb_repair_normal_polygon", ch=0)[0]
        cmds.delete(cmds.ls(comb_polygons))
    else:
        comb_polygon = comb_polygons[0]
    cmds.polyMergeVertex(comb_polygon+".vtx[*]", d=0.001, ch=0)
    cmds.polyNormalPerVertex(comb_polygon, ufn=True)
    cmds.polySoftEdge(comb_polygon, a=180, ch=0)
    cmds.select(comb_polygon, )
    for repair_polygon in repair_polygons:
        cmds.select(comb_polygon, repair_polygon)
        cmds.transferAttributes(transferNormals=1)
        cmds.select(repair_polygon)
        cmds.DeleteHistory()
    cmds.delete(comb_polygon)
    return repair_polygons


def invert_target_normal(polygon_name, repair_polygon, target_name):
    bs_name = find_bs(polygon_name)
    if not bs_name:
        return
    if not cmds.objExists(bs_name+"."+target_name):
        return
    target_polygon_name = rebuild_target(bs_name, target_name)
    orig_name = get_orig(polygon_name)
    bs_api.invert_target_normal(polygon_name, orig_name, repair_polygon, target_polygon_name)


def repair_normal_targets(target_names):
    polygons = get_selected_polygons()
    if not len(polygons):
        return
    bs_nodes = list(filter(bool, map(find_bs, polygons)))
    if not len(bs_nodes):
        return
    for target_name in target_names:
        set_pose(target_name)
        map(lambda x: cmds.setAttr(x+".envelope", 1), bs_nodes)
        repair_polygons = get_repair_polygons(polygons)
        map(lambda x: cmds.setAttr(x + ".envelope", 0), bs_nodes)
        for polygon, repair_polygon in zip(polygons, repair_polygons):
            invert_target_normal(polygon, repair_polygon, target_name)
        map(lambda x: cmds.setAttr(x + ".envelope", 1), bs_nodes)
        cmds.delete(repair_polygons)
    ADPose.ADPoses.all_to_zero()


def test_rn():
    cmds.select("PL019C_HD_C_01")
    repair_normal_targets(["Shoulder_L_a90_d0"])


def doit():
    test_rn()

