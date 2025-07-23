# coding:utf-8
from maya import cmds
from maya.api.OpenMaya import *
from .api_lib import bs_api


class Shape(object):
    mesh = "mesh"
    nurbsSurface = "nurbsSurface"
    nurbsCurve = "nurbsCurve"


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


def find_bs(polygon):
    # 查找 模型 blend shape
    shapes = set(cmds.listRelatives(polygon, s=1))
    for bs in cmds.ls(cmds.listHistory(polygon), type="blendShape"):
        if cmds.blendShape(bs, q=1, g=1)[0] in shapes:
            return bs


def get_bs(polygon):
    bs = find_bs(polygon)
    if bs is None:
        bs = cmds.blendShape(polygon, automatic=True, n=polygon.split("|")[-1] + "_bs")[0]
    return bs


def get_orig(polygon):
    orig_list = [shape for shape in cmds.listRelatives(polygon, s=1) if cmds.getAttr(shape+'.io')]
    orig_list.sort(key=lambda x: len(set(cmds.listConnections(x, s=0, d=1, ) or [])))
    if orig_list:
        return orig_list[-1]
    else:
        return cmds.listRelatives(polygon, s=1)[0]


def get_index(node, alias_name):
    if node is None:
        return
    parent_attr = cmds.attributeQuery(alias_name, node=node, ln=1)
    parent_name = "{node}.{parent_attr}".format(**locals())
    elem_names = cmds.listAttr(parent_name, m=1)
    elem_indexes = cmds.getAttr(parent_name, mi=1)
    if alias_name in elem_names:
        return elem_indexes[elem_names.index(alias_name)]


def check_bs(fun):
    def check_fun(bs, *args, **kwargs):
        if not bs:
            return 
        if is_shape(bs):
            bs = get_bs(bs)
        return fun(bs, *args, **kwargs)
    return check_fun


@check_bs
def get_bs_attr(bs, target):
    return bs + "." + target


def check_target(fun):
    def check_fun(bs, target, *args, **kwargs):
        if not cmds.objExists(get_bs_attr(bs, target)):
            return
        fun(bs, target, *args, **kwargs)
    return check_fun


@check_bs
def add_target(bs, target):
    if cmds.objExists(get_bs_attr(bs, target)):
        return 
    elem_indexes = cmds.getAttr(bs+".weight", mi=1) or []
    index = len(elem_indexes)
    for i in range(index):
        if i == elem_indexes[i]:
            continue
        index = i
        break
    bs_attr = bs+'.weight[%i]' % index
    cmds.setAttr(bs+'.weight[%i]' % index, 1)
    cmds.aliasAttr(target, bs_attr)
    bs_api.init_target(bs, index)


@check_bs
@check_target
def mirror_target(bs, src, dst):
    src_id = get_index(bs, src)
    add_target(bs, dst)
    dst_id = get_index(bs, dst)
    symmetric_cache = {key: cmds.symmetricModelling(q=1, **{key: True}) for key in ["s", "t", "ax", "a"]}
    if src_id != dst_id:
        cmds.blendShape(bs, e=1, rtd=[0, dst_id])
        cmds.blendShape(bs, e=1, cd=[0, src_id, dst_id])
        cmds.blendShape(bs, e=1, ft=[0, dst_id], sa="X", ss=1)
    else:
        cmds.blendShape(bs, e=1, md=0, mt=[0, dst_id], sa="X", ss=1)
    for key, value in symmetric_cache.items():
        cmds.symmetricModelling(**{key: value})


def edit_target(src, dst, target):
    add_target(dst, target)
    bs = find_bs(dst)
    index = get_index(bs, target)
    bs_api.edit_target(bs, index, src, dst, get_orig(dst))


@check_bs
@check_target
def delete_target(bs, target):
    index = get_index(bs, target)
    cmds.aliasAttr(get_bs_attr(bs, target), rm=1)
    cmds.removeMultiInstance(bs + ".weight[%i]" % index, b=1)
    cmds.removeMultiInstance(bs + ".it[0].itg[%i]" % index, b=1)


def check_connect_attr(src, dst):
    if not cmds.isConnected(src, dst):
        cmds.connectAttr(src, dst, f=1)


def get_target(attr):
    return attr.split(".")[-1]


@check_bs
def connect_target(bs, attr):
    target = get_target(attr)
    add_target(bs, target)
    check_connect_attr(attr, bs + '.' + target)


def get_selected_polygons():
    return list(filter(is_shape, cmds.ls(sl=1, o=1)))


def get_selected_blend_shapes():
    return list(filter(bool, map(find_bs, get_selected_polygons())))


def mirror_connect_selected_targets(target_mirrors):
    for bs in get_selected_blend_shapes():
        for src, attr in target_mirrors:
            src_id = get_index(bs, src)
            if src_id is None:
                continue
            connect_target(bs, attr)
            dst = get_target(attr)
            mirror_target(bs, src, dst)


def edit_connect_target(attr, src, dst):
    connect_target(dst, attr)
    target = get_target(attr)
    edit_target(src, dst, target)


def edit_connect_selected_target(attr):
    polygons = get_selected_polygons()
    if len(polygons) != 2:
        return
    edit_connect_target(attr, *polygons)


def delete_selected_targets(targets):
    for bs in get_selected_blend_shapes():
        for target in targets:
            delete_target(bs, target)


def delete_connect_targets(attr):
    for output_attr in cmds.listConnections(attr, s=0, d=1, p=1):
        if output_attr.count(".") != 1:
            continue
        bs, target = output_attr.split(".")
        if cmds.nodeType(bs) != "blendShape":
            continue
        delete_target(bs, target)


class LEditTargetJob(object):

    def __init__(self, src, dst, target):
        self.del_job()
        self.bs = get_bs(dst)
        self.index = get_index(self.bs, target)
        self.src = src
        bs_api.cache_target(self.bs, self.index, dst, get_orig(dst))
        cmds.scriptJob(attributeChange=[cmds.listRelatives(src, s=1)[0] + ".outMesh", self])

    def __repr__(self):
        return self.__class__.__name__

    def __call__(self):
        bs_api.set_target(self.bs, self.index, self.src)

    def add_job(self):
        self.del_job()

    @classmethod
    def del_job(cls):
        for job in cmds.scriptJob(listJobs=True):
            if repr(cls.__name__) in job:
                cmds.scriptJob(kill=int(job.split(":")[0]))


def finish_duplicate_edit(set_pose_by_target):
    LEditTargetJob.del_job()
    root = "|lush_duplicate_edit"
    if not cmds.objExists(root):
        return
    for target_group in cmds.listRelatives(root):
        if target_group[:5] != "edit_":
            continue
        target = target_group[5:]
        set_pose_by_target(target)
        for src in cmds.listRelatives(target_group):
            if not is_shape(src):
                continue
            dst = src[len(target)+1:]
            if not is_shape(dst):
                continue
            uu = cmds.ls(cmds.listConnections(dst+".v", s=1, d=0), type=["animCurveUU", "blendWeighted"])
            if uu:
                cmds.delete(uu)
            cmds.setAttr(dst+".v", True)
            edit_target(src, dst, target)
    cmds.delete(root)


def wireframe_planes():
    panels = cmds.getPanel(all=True)
    for panel in panels:
        if cmds.modelPanel(panel, ex=1):
            try:
                cmds.modelEditor(panel, e=1, wireframeOnShaded=True)
            except RuntimeError:
                pass
    cmds.select(cl=1)


def duplicate_polygon_by_target(target, polygon):
    root = "lush_duplicate_edit"
    parent = "edit_"+target
    name = target + "_" + polygon.split("|")[-1]
    if not cmds.objExists(root):
        cmds.group(em=1, n=root)
    if not cmds.objExists("|lush_duplicate_edit|"+parent):
        cmds.group(em=1, n=parent, p=root)
    if cmds.objExists(name):
        return name
    dup = cmds.duplicate(polygon, n=name)[0]
    for shape in cmds.listRelatives(dup, s=1):
        if cmds.getAttr(shape + '.io'):
            cmds.delete(shape)
    cmds.parent(dup, parent)
    for shape in cmds.listRelatives(dup, s=1):
        cmds.setAttr(shape + '.overrideEnabled', True)
        cmds.setAttr(shape + '.overrideColor', 13)
    return dup


def driver_polygon_vis(attr, polygon, dup):
    cmds.setDrivenKeyframe(polygon + ".v", cd=attr, dv=0.0, v=1, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(polygon + ".v", cd=attr, dv=0.99, v=1, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(polygon + ".v", cd=attr, dv=1.0, v=0, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(dup + ".v", cd=attr, dv=0.0, v=0, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(dup + ".v", cd=attr, dv=0.99, v=0, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(dup + ".v", cd=attr, dv=1.0, v=1, itt="linear", ott="linear")


def duplicate_polygon(attr, polygon):
    target = get_target(attr)
    dup = duplicate_polygon_by_target(target, polygon)
    driver_polygon_vis(attr, polygon, dup)
    return dup


def duplicate_edit_polygon(attr, polygon):
    dup = duplicate_polygon(attr, polygon)
    target = get_target(attr)
    connect_target(polygon, attr)
    LEditTargetJob(dup, polygon, target)
    wireframe_planes()


def connect_polygons(attrs, polygons):
    for polygon in polygons:
        for attr in attrs:
            connect_target(polygon, attr)


def duplicate_edit_selected_polygons(attrs, set_pose_by_target):
    polygons = get_selected_polygons()
    if len(polygons) == 0:
        return
    if len(attrs) == 0:
        return
    connect_polygons(attrs, polygons)
    for attr in attrs:
        target = get_target(attr)
        set_pose_by_target(target)
        for polygon in polygons:
            duplicate_polygon(attr, polygon)
    duplicate_edit_polygon(attrs[0], polygons[0])


def is_on_duplicate_edit():
    return cmds.objExists("lush_duplicate_edit")


def auto_duplicate_edit(attrs, set_pose_by_target):
    if is_on_duplicate_edit():
        finish_duplicate_edit(set_pose_by_target)
    else:
        duplicate_edit_selected_polygons(attrs, set_pose_by_target)


def auto_duplicate_edit2(target_names, add_pose_by_target, set_pose_by_target):
    if is_on_duplicate_edit():
        finish_duplicate_edit(set_pose_by_target)
    else:
        duplicate_edit_selected_polygons2(target_names, add_pose_by_target, set_pose_by_target)


def duplicate_edit_selected_polygons2(target_names, add_pose_by_target, set_pose_by_target):
    polygons = get_selected_polygons()
    if len(polygons) == 0:
        return
    if len(target_names) == 0:
        return
    all_dup_polygons = []
    for target_name in target_names:
        set_pose_by_target(target_name)
        dup_polygons = []
        for polygon in polygons:
            dup = duplicate_polygon_by_target(target_name, polygon)
            dup_polygons.append(dup)
        all_dup_polygons.append(dup_polygons)
    attrs = []
    for target_name in target_names:
        set_pose_by_target(target_name)
        attrs.append(add_pose_by_target(target_name))
    print ("----------------------")
    print (attrs)

    connect_polygons(attrs, polygons)
    duplicate_edit_polygon(attrs[0], polygons[0])
    LEditTargetJob(all_dup_polygons[0][0], polygons[0], target_names[0])
    wireframe_planes()


def get_connect_data(polygons, targets):
    data = []
    for polygon in polygons:
        bs = find_bs(polygon)
        if not bs:
            continue
        targets_data = []
        for target in targets:
            if not cmds.objExists(get_bs_attr(bs, target)):
                continue
            driver_attr = (cmds.listConnections(get_bs_attr(bs, target), s=1, d=0, p=1) or [None])[0]
            targets_data.append(dict(
                target_name=target,
                driver_attr=driver_attr
            ))
        data.append(dict(
            targets_data=targets_data,
            polygon_name=polygon
        ))
    return data


def set_connect_data(polygons, data):
    for polygon, polygon_data in zip(polygons, data):
        for target_data in polygon_data["targets_data"]:
            add_target(polygon, target_data["target_name"])
            if target_data["driver_attr"] is None:
                continue
            if not cmds.objExists(target_data["driver_attr"]):
                continue
            connect_target(polygon, target_data["driver_attr"])


def export_targets(polygons, targets, path):
    bs_api.export_targets(polygons, targets, path)


def load_targets(polygons, path):
    bs_api.load_targets(polygons, path)


def get_selected_bs_data(targets, path):
    path = path.replace(".json", ".cbs")
    polygons = get_selected_polygons()
    data = get_connect_data(polygons, targets)
    export_targets(polygons, targets, path)
    return data


def check_data_polygons(data_polygons):
    exist_polygons = get_selected_polygons()
    if len(exist_polygons) == len(data_polygons):
        polygon_names = exist_polygons
    else:
        polygon_names = list(filter(is_shape, data_polygons))
    return polygon_names


def set_selected_bs_data(data, path):
    path = path.replace(".json", ".cbs")
    polygons = check_data_polygons([row["polygon_name"] for row in data])
    load_targets(polygons, path)


def get_selected_polygon_ids():
    sel = MGlobal.getActiveSelectionList()
    assert isinstance(sel, MSelectionList)
    for i in range(sel.length()):
        dag_path, component = sel.getComponent(i)
        if component.apiTypeStr != "kMeshVertComponent":
            return
        ids = list(MFnSingleIndexedComponent(component).getElements())
        polygon = cmds.listRelatives(dag_path.partialPathName(), p=1)[0]
        return polygon, ids


def delete_vtx_targets(targets):
    polygon, ids = get_selected_polygon_ids()
    bs = find_bs(polygon)
    if bs is None:
        return
    indexes = [get_index(bs, target) for target in targets]
    indexes = [i for i in indexes if i is not None]
    add_target(bs, "lush_temp_null_target")
    bs_api.cache_target_points(bs, [get_index(bs, "lush_temp_null_target")]*len(indexes))
    bs_api.load_cache_target_points(bs, indexes, ids)
    delete_target(bs, "lush_temp_null_target")
