# coding:utf-8
from maya.OpenMaya import *
import pymel.core as pm
import os
from .api_lib import bs_api
from maya import cmds

def load_ocd_plug():
    version = int(round(float(pm.about(q=1, v=1))))
    for name in ["ocd", "SSDR2"]:  # "ad_pose_bs"
        path = os.path.abspath(__file__+"/../plug-ins/maya%04d/%s.mll" % (version, name))
        if not os.path.isfile(path):
            continue
        if pm.pluginInfo(name, q=1, l=1):
            continue
        pm.loadPlugin(path)


def get_fn_mesh_by_name(name):
    selection_list = MSelectionList()
    selection_list.add(name)
    dag_path = MDagPath()
    selection_list.getDagPath(0, dag_path)
    fn_mesh = MFnMesh(dag_path)
    return fn_mesh


def get_polygon_points_by_name(name, points):
    fn_mesh = get_fn_mesh_by_name(name)
    fn_mesh.getPoints(points)


def set_polygon_points_by_name(name, points):
    fn_mesh = get_fn_mesh_by_name(name)
    fn_mesh.setPoints(points)


def get_bs_ipt_ict(bs, index):
    selection_list = MSelectionList()
    selection_list.add(bs)
    depend_node = MObject()
    selection_list.getDependNode(0, depend_node)
    fn_depend_node = MFnDependencyNode(depend_node)
    iti = fn_depend_node.findPlug("it").elementByLogicalIndex(0).child(0).elementByLogicalIndex(index).child(0).\
        elementByLogicalIndex(6000)
    ipt = iti.child(3)
    ict = iti.child(4)
    return ipt, ict


def matrix_set_data(matrix, data):
    for i in range(4):
        for j in range(4):
            MScriptUtil.setDoubleArray(matrix[i], j, data[i][j])


def get_bs_ids_points(polygon, name):
    ids = MIntArray()
    points = MPointArray()
    bs = get_bs(polygon)
    if not bs.hasAttr(name):
        return ids, points
    index = bs.attr(name).logicalIndex()
    ipt, ict = get_bs_ipt_ict(bs.name(), index)
    fn_component_list = MFnComponentListData(ict.asMObject())
    for i in range(fn_component_list.length()):
        fn_component = MFnSingleIndexedComponent(fn_component_list[i])
        _ids = MIntArray()
        fn_component.getElements(_ids)
        for j in range(_ids.length()):
            ids.append(_ids[j])
    fn_points = MFnPointArrayData(ipt.asMObject())
    fn_points.copyTo(points)
    return ids, points


def set_bs_ids_points(polygon, name, ids, points):
    bs = get_bs(polygon)
    add_target(polygon, name)
    index = bs.attr(name).logicalIndex()
    ipt, ict = get_bs_ipt_ict(bs.name(), index)
    fn_component = MFnSingleIndexedComponent()
    fn_component_obj = fn_component.create(MFn.kMeshVertComponent)
    fn_component.addElements(ids)
    fn_component_list = MFnComponentListData()
    fn_component_list_obj = fn_component_list.create()
    fn_component_list.add(fn_component_obj)
    fn_points = MFnPointArrayData()
    fn_points_obj = fn_points.create(points)
    ict.setMObject(fn_component_list_obj)
    ipt.setMObject(fn_points_obj)


def is_polygon(polygon):
    if polygon.type() != "transform":
        return False
    shape = polygon.getShape()
    if not shape:
        return False
    if shape.type() != "mesh":
        return False
    return True


def get_child_polygons(group):
    polygons = group.listRelatives(ad=1, type="transform")
    polygons.insert(0, group)
    return [poly for poly in polygons if is_polygon(poly)]


def get_name_polygon_by_hierarchy(group):
    data = {}
    polygons = group.listRelatives(ad=1, type="transform")
    polygons.insert(0, group)
    length = len(group.fullPath()) + 1
    for polygon in polygons:
        name = "|" + polygon.fullPath()[length:]
        if not is_polygon(polygon):
            continue
        data[name] = polygon
    return data


def get_polygon_matrix_by_root(*roots):
    return get_polygon_matrix_by_map([get_name_polygon_by_hierarchy(root) for root in roots])


def get_name_polygon_by_short_name(polygons):
    return {polygon.name().split("|")[-1]:polygon for polygon in polygons}


def get_polygon_matrix_by_polygons(*polygons):
    return get_polygon_matrix_by_map([get_name_polygon_by_short_name(poly) for poly in polygons])


def get_polygon_matrix_by_map(name_polygons):
    polygon_matrix = []
    for name in name_polygons[0].keys():
        polygons = [name_polygon.get(name, None) for name_polygon in name_polygons]
        if None in polygons:
            continue
        polygon_matrix.append(polygons)
    return polygon_matrix


def get_bs(polygon):
    bs = polygon.listHistory(type="blendShape")
    if bs:
        bs = bs[0]
    else:
        try:
            bs = pm.blendShape(polygon, automatic=True, n=polygon.name().split("|")[-1] + "_bs")[0]
        except TypeError:
            dup = polygon.duplicate()[0]
            bs = pm.blendShape(dup, polygon, frontOfChain=1, n=polygon.name().split("|")[-1] + "_bs")[0]
            pm.delete(dup)
            delete_target(bs.weight[0])
    return bs


def find_bs(polygon):
    bs = polygon.listHistory(type="blendShape")
    if bs:
        return bs[0]


def add_target(polygon, name):
    bs = get_bs(polygon)
    if bs.hasAttr(name):
        return
    ids = [bs.weight.elementByPhysicalIndex(i).logicalIndex() for i in range(bs.weight.numElements())]
    index = -1
    while True:
        index += 1
        if index not in ids:
            break
    bs.weight[index].set(1)
    pm.aliasAttr(name, bs.weight[index])
    bs_api.init_target(bs.name(), index)


def delete_target(weight_attr):
    index = weight_attr.logicalIndex()
    bs = weight_attr.node()
    pm.aliasAttr(weight_attr, rm=1)
    pm.removeMultiInstance(weight_attr, b=1)
    pm.removeMultiInstance(bs.it[0].itg[index], b=1)


def get_orig(polygon):
    # for shape in polygon.getShapes():
    #     if shape.io.get():
    #         if not shape.outputs(type="groupParts"):
    #             pm.delete(shape)
    # for shape in polygon.getShapes():
    #     if shape.io.get():
    #         if shape.outputs(type="groupParts"):
    #             return shape
    orig_list = [shape for shape in polygon.getShapes() if shape.io.get()]
    orig_list.sort(key=lambda x: len(set(x.outputs())))
    if orig_list:
        return orig_list[-1]


def edit_target(target, base, name):
    bs = get_bs(base)
    if not bs.hasAttr(name):
        return
    index = bs.attr(name).logicalIndex()
    orig = get_orig(base)
    bs_api.edit_target(bs.name(), index, target.name(), base.name(), orig.name())


def bridge_connect(attr, dst):
    name = attr.name(includeNode=False)
    add_target(dst, name)
    bs = get_bs(dst)
    if bs.attr(name) not in attr.outputs(p=1):
        attr.connect(bs.attr(name), f=1)


def bridge_connect_edit(attr, src, dst):
    bridge_connect(attr, dst)
    edit_target(src, dst, attr.name(includeNode=False))


def edit_static_target(target, base, name):
    bs = get_bs(base)
    if not bs.hasAttr(name):
        return
    index = bs.attr(name).logicalIndex()
    orig = base.getShape()
    bs_api.edit_static_target(bs.name(), index, target.name(), base.name())


def bridge_static_connect_edit(attr, src, dst):
    bridge_connect(attr, dst)
    edit_static_target(src, dst, attr.name(includeNode=False))


def check_null_by_id(bs, index):
    ict = "{bs}.it[0].itg[{index}].iti[6000].ict".format(**locals())
    return bool(cmds.getAttr(ict))
    # if cmds.getAttr(ict):
    #     return
    # cmds.sculptTarget(bs, e=1, regenerate=1, target=index)
    # igt = "{bs}.it[0].itg[{index}].iti[6000].igt".format(**locals())
    # target_polygon_name = cmds.listConnections(igt, s=1, d=1)[0]
    # cmds.delete(target_polygon_name)


def _mirror_targets(bs, src_indexes, dst_indexes):
    for src_id, dst_id in zip(src_indexes, dst_indexes):
        if not check_null_by_id(bs, src_id):
            continue
        pm.blendShape(bs, e=1, rtd=[0, dst_id])
        pm.blendShape(bs, e=1, cd=[0, src_id, dst_id])
        pm.blendShape(bs, e=1, ft=[0, dst_id], sa="X", ss=1)


def mirror_targets(polygon, names):
    bs = get_bs(polygon)
    src_indexes = []
    dst_indexes = []
    for src, dst in names:
        if not bs.hasAttr(src):
            continue
        if not bs.hasAttr(dst):
            continue
        src_indexes.append(bs.attr(src).logicalIndex())
        dst_indexes.append(bs.attr(dst).logicalIndex())
    orig = get_orig(polygon)
    try:
        _mirror_targets(bs.name(), src_indexes, dst_indexes)
    except KeyError:
        bs_api.mirror_targets(bs.name(), orig.name(), src_indexes, dst_indexes)


def get_blend_shape_data(polygon, target_names):
    data = []
    bs = get_bs(polygon)
    for target_name in target_names:
        if not bs.hasAttr(target_name):
            continue
        api_ids, api_points = get_bs_ids_points(polygon, target_name)
        ids = [int(api_ids[i]) for i in range(api_ids.length())]
        points = [[float(getattr(api_points[i], xyz)) for xyz in "xyz"] for i in range(api_points.length())]
        data.append(dict(
            target_name=target_name,
            ids=ids,
            points=points,
        ))
    return data


def get_blend_shape_data_use_scale(polygon, target_names):
    data = []
    bs = get_bs(polygon)
    scale = polygon.s.get()
    for target_name in target_names:
        if not bs.hasAttr(target_name):
            continue
        api_ids, api_points = get_bs_ids_points(polygon, target_name)
        ids = [int(api_ids[i]) for i in range(api_ids.length())]
        points = [[float(getattr(api_points[i], xyz)*getattr(scale, xyz)) for xyz in "xyz"]
                  for i in range(api_points.length())]
        data.append(dict(
            target_name=target_name,
            ids=ids,
            points=points,
        ))
    return data


def set_blend_shape_by_py_data(polygon, target_name, ids, points):
    bs = get_bs(polygon)
    if not bs.hasAttr(target_name):
        return
    api_ids = MIntArray()
    for i in ids:
        api_ids.append(i)
    api_points = MPointArray()
    for p in points:
        api_point = MPoint(*p)
        api_points.append(api_point)
    set_bs_ids_points(polygon, target_name, api_ids, api_points)


def set_blend_shape_data(polygon, data):
    for row in data:
        set_blend_shape_by_py_data(polygon, **row)


def delete_selected_targets(target_names):
    for polygon in pm.selected(type="transform"):
        if not is_polygon(polygon):
            continue
        bs = get_bs(polygon)
        for target_name in target_names:
            if bs.hasAttr(target_name):
                delete_target(bs.attr(target_name))


class LEditTargetJob(object):

    def __init__(self, src, dst, name):
        self.del_job()
        bs = get_bs(dst)
        self.index = bs.attr(name).logicalIndex()
        self.bs_name = bs.name()
        self.target_name = src.name()
        polygon_name = dst.name()
        orig_name = get_orig(dst).name()
        bs_api.cache_target(self.bs_name, self.index, polygon_name, orig_name)
        attr_name = src.getShape().outMesh.name()
        pm.scriptJob(attributeChange=[attr_name, self])

    def __repr__(self):
        return self.__class__.__name__

    def __call__(self):
        bs_api.set_target(self.bs_name, self.index, self.target_name)

    def add_job(self):
        self.del_job()

    @classmethod
    def del_job(cls):
        for job in pm.scriptJob(listJobs=True):
            if repr(cls.__name__) in job:
                pm.scriptJob(kill=int(job.split(":")[0]))


def get_bs_igt_ict(bs, index):
    selection_list = MSelectionList()
    selection_list.add(bs)
    depend_node = MObject()
    selection_list.getDependNode(0, depend_node)
    fn_depend_node = MFnDependencyNode(depend_node)
    iti = fn_depend_node.findPlug("it").elementByLogicalIndex(0).child(0).elementByLogicalIndex(index).child(0).\
        elementByLogicalIndex(6000)
    igt = iti.child(0)
    ict = iti.child(4)
    return igt, ict


def is_target_null(bs, name):
    index = bs.attr(name).logicalIndex()
    igt, ict = get_bs_igt_ict(bs.name(), index)
    if bs.attr(igt.name()[len(bs.name())+1:]).inputs():
        return False
    try:
        fn_component_list = MFnComponentListData(ict.asMObject())
    except:
        return True
    for i in range(fn_component_list.length()):
        fn_component = MFnSingleIndexedComponent(fn_component_list[i])
        _ids = MIntArray()
        fn_component.getElements(_ids)
        for j in range(_ids.length()):
            return False
    return True


def clear_un_use_bs():
    clear_list = []
    for bs in pm.ls(type="blendShape"):
        if bs.isReferenced():
            continue
        for target_name in bs.weight.elements():
            if is_target_null(bs, target_name):
                clear_list.append(bs.name()+"."+target_name)
                delete_target(bs.attr(target_name))
    return clear_list


def delete_bs_for_points(target_names):
    mesh_list = pm.ls(type="mesh", sl=1, o=1)
    for mesh in mesh_list:
        polygon = mesh.getParent()
        data_raw = get_blend_shape_data(polygon, target_names)
        vertices = pm.ls(sl=1, fl=1)
        vertices_id_list = []
        for vtx in vertices:
            if not isinstance(vtx, pm.general.MeshVertex):
                continue
            if vtx.node() != mesh:
                continue
            vertices_id_list.append(vtx.index())
        data_edited = data_raw
        for target_name_num in range(len(target_names)):
            for vtx_id in vertices_id_list:
                if vtx_id in data_edited[target_name_num]['ids']:
                    vtx_id_index = data_edited[target_name_num]['ids'].index(vtx_id)
                    data_edited[target_name_num]['points'].pop(vtx_id_index)
                    data_edited[target_name_num]['ids'].pop(vtx_id_index)
        set_blend_shape_data(polygon, data_edited)


def init_targets(target_names):
    polygon_list = pm.ls("*Driver", type="transform", o=1) + pm.ls(sl=1, type="transform", o=1)
    polygon_list = filter(is_polygon, polygon_list)
    for polygon in polygon_list:
        bs = get_bs(polygon)
        for target_name in target_names:
            if not bs.hasAttr(target_name):
                return
            index = bs.attr(target_name).logicalIndex()
            bs_api.init_target(bs.name(), index)


def custom_mirror(target_names):
    if len(target_names) != 2:
        return
    polygon_list = pm.ls("*Driver", type="transform", o=1) + pm.ls(sl=1, type="transform", o=1)
    polygon_list = filter(is_polygon, polygon_list)
    target_mirrors = [target_names]
    for polygon in polygon_list:
        for src, dst in target_mirrors:
            add_target(polygon, dst)
        mirror_targets(polygon, target_mirrors)


def cache_bs():
    pass


def load_bs():
    pass


def copy_bs_link(src_polygon, dst_polygon, target_names):
    src_bs = get_bs(src_polygon)
    dst_bs = get_bs(dst_polygon)
    for target_name in target_names:
        if not src_bs.hasAttr(target_name):
            continue
        add_target(dst_polygon, target_name)
        in_attr = src_bs.attr(target_name).inputs(p=1)
        if not in_attr:
            continue
        in_attr = in_attr[0]
        if in_attr.isConnectedTo(dst_bs.attr(target_name)):
            continue
        in_attr.connect(dst_bs.attr(target_name))


def copy_bs(src_polygon, dst_polygon, ids, target_names):
    copy_bs_link(src_polygon, dst_polygon, target_names)
    src_bs = get_bs(src_polygon)
    dst_bs = get_bs(dst_polygon)
    src_indexes = []
    dst_indexes = []
    for target_name in target_names:
        if not src_bs.hasAttr(target_name):
            continue
        src_indexes.append(src_bs.attr(target_name).logicalIndex())
        dst_indexes.append(dst_bs.attr(target_name).logicalIndex())
    if not src_indexes:
        return
    reload(bs_api)
    bs_api.cache_target_points(src_bs.name(), src_indexes)
    bs_api.load_cache_target_points(dst_bs.name(), dst_indexes, ids)


def get_polygon(node):
    if node.type() == "mesh":
        node = node.getParent()
    if is_polygon(node):
        return node


def get_two_polygon_ids():
    polygons = filter(bool, map(get_polygon, pm.ls(sl=1, o=1)))
    if len(polygons) != 2:
        return None, None, None
    src_polygon, dst_polygon = polygons
    ids = [vtx.index() for vtx in pm.ls(sl=1, fl=1) if isinstance(vtx, pm.general.MeshVertex)]
    return src_polygon, dst_polygon, ids


def tool_copy_bs(target_names):
    src_polygon, dst_polygon, ids = get_two_polygon_ids()
    copy_bs(src_polygon, dst_polygon, ids, target_names)


def tool_part_warp_copy(warp_copy_fun):
    def part_warp_copy_fun(*args):
        src_polygon, dst_polygon, ids = get_two_polygon_ids()
        pm.select(src_polygon, dst_polygon)
        if not ids:
            return warp_copy_fun(*args)
        dst_bs = get_bs(dst_polygon)
        dst_indexes = []
        for target_name in args[0]:
            add_target(dst_polygon, target_name)
            dst_indexes.append(dst_bs.attr(target_name).logicalIndex())
        bs_api.cache_target_points(dst_bs.name(), dst_indexes)
        warp_copy_fun(*args)
        keep_ids = range(dst_polygon.getShape().numVertices())
        for i in ids:
            keep_ids.remove(i)
        # keep_ids
        bs_api.load_cache_target_points(dst_bs.name(), dst_indexes, keep_ids)
    return part_warp_copy_fun


def tool_copy_targets(target_names):
    polygons = list(filter(is_polygon, pm.ls(sl=1, type="transform")))
    src_target_name = target_names.pop(0)
    for polygon in polygons:
        bs = find_bs(polygon)
        if not bs:
            return
        if not bs.hasAttr(src_target_name):
            continue
        src_id = bs.attr(src_target_name).logicalIndex()
        for dst_target_name in target_names:
            if not bs.hasAttr(dst_target_name):
                continue
            dst_id = bs.attr(dst_target_name).logicalIndex()
            pm.blendShape(bs, e=1, rtd=[0, dst_id])
            pm.blendShape(bs, e=1, cd=[0, src_id, dst_id])

