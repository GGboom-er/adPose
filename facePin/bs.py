# coding:utf-8

from maya import cmds
from maya.api.OpenMaya import *


def find_bs(polygon):
    # 查找 模型 blend shape
    if not cmds.objExists(polygon):
        return
    shapes = set(cmds.listRelatives(polygon, s=1, f=1) or [])
    for bs in cmds.ls(cmds.listHistory(polygon), type="blendShape"):
        if cmds.ls(cmds.blendShape(bs, q=1, g=1), l=1)[0] in shapes:
            return bs


def get_bs(polygon):
    bs = find_bs(polygon)
    if bs is None:
        bs = cmds.blendShape(polygon, automatic=True, n=polygon.split("|")[-1] + "_bs")[0]
    return bs


def get_next_index(bs):
    elem_indexes = cmds.getAttr(bs+".weight", mi=1) or []
    index = len(elem_indexes)
    for i in range(index):
        if i == elem_indexes[i]:
            continue
        index = i
        break
    return index


def add_real_target(polygon, bs, target):
    if cmds.objExists(bs + "." + target):
        return
    index = get_next_index(bs)
    cmds.blendShape(bs, e=1, t=[polygon, index, target, 1])


def add_real_targets(targets, polygon):
    bs = find_bs(polygon)
    if not targets:
        return
    if bs is None:
        bs = cmds.blendShape(targets, polygon, n=polygon+"_bs")[0]
    else:
        for target in targets:
            add_real_target(polygon, bs, target)
    for target in targets:
        cmds.setAttr(bs+"."+target, 1.0)


def api_ls(*names):
    selection_list = MSelectionList()
    for name in names:
        selection_list.add(name)
    return selection_list


def get_index(bs, target):
    return api_ls(bs+"."+target).getPlug(0).logicalIndex()


def add_target(bs, target):
    if cmds.objExists(bs + "." + target):
        return
    index = get_next_index(bs)
    bs_attr = bs+'.weight[%i]' % index
    cmds.setAttr(bs+'.weight[%i]' % index, 1)
    cmds.aliasAttr(target, bs_attr)
    ipt_name = "{bs}.it[0].itg[{index}].iti[6000].ipt".format(**locals())
    ict_name = "{bs}.it[0].itg[{index}].iti[6000].ict".format(**locals())
    cmds.getAttr(ipt_name, type=1)
    cmds.getAttr(ict_name, type=1)


def mirror_target(bs, src, dst):
    if not cmds.objExists(bs + "." + src):
        return
    src_id = get_index(bs, src)
    add_target(bs, dst)
    dst_id = get_index(bs, dst)
    symmetric_cache = {k: cmds.symmetricModelling(q=1, **{k: True}) for k in ["s", "t", "ax", "a"]}
    if src_id != dst_id:
        cmds.blendShape(bs, e=1, rtd=[0, dst_id])
        cmds.blendShape(bs, e=1, cd=[0, src_id, dst_id])
        cmds.blendShape(bs, e=1, ft=[0, dst_id], sa="X", ss=1)
    else:
        cmds.blendShape(bs, e=1, md=0, mt=[0, dst_id], sa="X", ss=1)
    for k, value in symmetric_cache.items():
        cmds.symmetricModelling(**{k: value})


def get_orig(polygon):
    orig_list = [shape for shape in cmds.listRelatives(polygon, s=1, f=1) or [] if cmds.getAttr(shape+'.io')]
    orig_list.sort(key=lambda x: len(list(set(cmds.listConnections(x, s=0, d=1, ) or []))))
    if orig_list:
        return orig_list[-1]
    else:
        return cmds.listRelatives(polygon, s=1)[0]


def set_target(bs, index, ids, points):
    ipt_name = "{bs}.it[0].itg[{index}].iti[6000].ipt".format(**locals())
    ict_name = "{bs}.it[0].itg[{index}].iti[6000].ict".format(**locals())
    ipt_plug = api_ls(ipt_name).getPlug(0)
    ict_plug = api_ls(ict_name).getPlug(0)
    fn_component = MFnSingleIndexedComponent()
    fn_component.create(MFn.kMeshVertComponent)
    fn_component.addElements(ids)
    fn_component_list = MFnComponentListData()
    fn_component_list.create()
    fn_component_list.add(fn_component.object())
    ict_plug.setMObject(fn_component_list.object())
    fn_points = MFnPointArrayData()
    fn_points.create(MPointArray([p for p in points]))
    ipt_plug.setMObject(fn_points.object())


def edit_target(src, dst, target):
    bs = get_bs(dst)
    add_target(bs, target)
    index = get_index(bs, target)
    cmds.blendShape(bs, e=1, rtd=[0, index])
    cmds.setAttr(bs+".envelope", 0)
    orig = get_orig(dst)
    polygon_fn = MFnMesh(api_ls(dst).getDagPath(0))
    orig_fn = MFnMesh(api_ls(orig).getDagPath(0))
    orig_points = orig_fn.getPoints(MSpace.kObject)
    point_data = [polygon_fn.getPoints()]
    for xyz in "xyz":
        offset_points = MPointArray(orig_points)
        for i in range(len(offset_points)):
            setattr(offset_points[i], xyz, getattr(offset_points[i], xyz)+1)
        orig_fn.setPoints(offset_points)
        point_data.append(polygon_fn.getPoints())
    orig_fn.setPoints(orig_points)
    cmds.setAttr(bs+".envelope", 1)
    src_points = MFnMesh(api_ls(src).getDagPath(0)).getPoints(MSpace.kTransform)
    dst_points = MFnMesh(api_ls(dst).getDagPath(0)).getPoints(MSpace.kTransform)
    ids = MIntArray()
    points = MPointArray()
    for i in range(len(src_points)):
        vector = src_points[i] - dst_points[i]
        if vector.length() < 0.00001:
            continue
        matrix = sum([list((point_data[j+1][i] - point_data[0][i]))+[0] for j in range(3)], []) + [0, 0, 0, 1]
        point = vector * MMatrix(matrix).inverse()
        ids.append(i)
        points.append(point)
    if len(ids) == 0:
        delete_target(bs, target)
    else:
        set_target(bs, index, ids, points)


def delete_target(bs, target):
    attr = bs + "." + target
    if not cmds.objExists(attr):
        return
    index = get_index(bs, target)
    cmds.aliasAttr(attr, rm=1)
    cmds.removeMultiInstance(bs + ".weight[%i]" % index, b=1)
    cmds.removeMultiInstance(bs + ".it[0].itg[%i]" % index, b=1)


def rebuild_target(bs, target_name):
    index = get_index(bs, target_name)
    cmds.sculptTarget(bs, e=1, regenerate=1, target=index)
    igt_name = "{bs}.it[0].itg[{index}].iti[6000].igt".format(**locals())
    target_polygon_name = cmds.listConnections(igt_name, s=1, d=0)[0]
    polygon_name = cmds.listRelatives(cmds.blendShape(bs, q=1, g=1)[0], p=1)[0]
    _target_polygon_name = polygon_name + "_RepairNormal_" + target_name
    if target_polygon_name != _target_polygon_name:
        target_polygon_name = cmds.rename(target_polygon_name, _target_polygon_name)
    cmds.setAttr(target_polygon_name+".v", 0)
    return target_polygon_name


def get_ids_points(bs, index):
    ipt = "{bs}.it[0].itg[{index}].iti[6000].ipt".format(**locals())
    ict = "{bs}.it[0].itg[{index}].iti[6000].ict".format(**locals())
    if not cmds.objExists(ipt) or not cmds.objExists(ict):
        return [], []
    try:
        obj = api_ls(ict).getPlug(0).asMObject()
    except RuntimeError:
        return [], []
    ids = []
    fn_component_list = MFnComponentListData(obj)
    for i in range(fn_component_list.length()):
        fn_component = MFnSingleIndexedComponent(fn_component_list.get(0))
        ids.extend(fn_component.getElements())
    points = cmds.getAttr(ipt)
    return ids, points


def get_target_drivers(polygon):
    bs = find_bs(polygon)
    if not bs:
        return dict()
    target_drivers = dict()
    for target in cmds.listAttr(bs+".weight", m=1) or []:
        driver_attr = cmds.listConnections(bs+"."+target, s=1, d=0, p=1)
        if driver_attr:
            target_drivers[target] = driver_attr[0]
    return target_drivers


def connect_attr(src, dst):
    if not cmds.objExists(src):
        return
    if not cmds.objExists(dst):
        return
    if not cmds.isConnected(src, dst):
        cmds.connectAttr(src, dst, f=1)


def set_target_drivers(polygon, target_drivers):
    bs = find_bs(polygon)
    if not bs:
        return
    for target in cmds.listAttr(bs+".weight", m=1) or []:
        if target not in target_drivers:
            continue
        connect_attr(target_drivers[target], bs+"."+target)


def get_id_point_map(bs, index):
    ids, points = get_ids_points(bs, index)
    if not ids:
        return dict()
    return dict(zip(*get_ids_points(bs, index)))


def get_targets_id_points(polygon):
    bs = find_bs(polygon)
    if not bs:
        return dict()
    targets_id_points = dict()
    for target in cmds.listAttr(bs+".weight", m=1) or []:
        index = get_index(bs, target)
        igt_name = "{bs}.it[0].itg[{index}].iti[6000].igt".format(**locals())
        if cmds.listConnections(igt_name, s=1, d=0):
            continue
        targets_id_points[target] = get_id_point_map(bs, index)
    return targets_id_points


def set_target_id_map(bs, index, id_points):
    ids = sorted(id_points.keys())
    points = [id_points[i] for i in ids]
    set_target(bs, index, ids, points)


def set_targets_id_points(polygon, targets_id_points):
    if not targets_id_points:
        return
    bs = get_bs(polygon)
    if not bs:
        return
    for target, id_points in targets_id_points.items():
        add_target(bs, target)
        index = get_index(bs, target)
        set_target_id_map(bs, index, id_points)