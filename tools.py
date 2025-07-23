# coding:utf-8
from . import bs
from maya.OpenMaya import *
from . import ADPose
from .general_ui import *
from . import twist
from .api_lib import bs_api


def is_polygon(polygon):
    shape = polygon.getShape()
    if shape is None:
        return
    if shape.type() != "mesh":
        return
    return True


def get_selected_polygons():
    return list(filter(is_polygon, pm.selected(type="transform")))


def get_blend_shape_sdk_data():
    polygons = get_selected_polygons()
    exist_target_names = []
    for polygon in polygons:
        _bs = bs.get_bs(polygon)
        for name in _bs.weight.elements():
            if name not in exist_target_names:
                exist_target_names.append(name)
    ad_target_names = [target_name for target_name in ADPose.ADPoses.get_targets() if target_name in exist_target_names]
    ad_pose = list(ad_target_names)
    twist_data = twist.get_twist_data()
    all_target_names = list(ad_target_names) + [row["target_name"] for row in twist_data]
    bs_data = []
    for polygon in polygons:
        _bs = bs.get_bs(polygon)
        target_names = []
        for name in _bs.weight.elements():
            if name not in all_target_names:
                continue
            target_names.append(name)
        bs_data.append(dict(
            polygon_name=polygon.name().split("|")[-1].split(":")[-1],
            target_names=target_names
        ))
    data = dict(
        ad_pose=ad_pose,
        bs_data=bs_data,
        twist_data=twist_data,
    )
    return data


def find_polygon_by_name(name):
    polygons = list(filter(is_polygon, pm.ls(name, type="transform")))
    if len(polygons) > 0:
        return polygons[0]


def get_blend_shapes(polygons):
    blend_shapes = []
    for polygon in polygons:
        for _bs in pm.listHistory(polygon, type="blendShape"):
            blend_shapes.append(_bs)
    return blend_shapes


def connect_bs(attr, bs_node):
    target_name = attr.name().split(".")[-1]
    if not bs_node.hasAttr(target_name):
        return
    dst_attr = bs_node.attr(target_name)
    if attr.isConnectedTo(dst_attr):
        return
    attr.connect(dst_attr, f=1)


def connect_all_bs(attr, blend_shapes):
    for bs_node in blend_shapes:
        connect_bs(attr, bs_node)


def load_blend_shape_sdk_data(polygons, data, cover=False):
    polygon_names = [row["polygon_name"] for row in data["bs_data"]]
    if len(polygons) != len(polygon_names):
        polygons = [find_polygon_by_name(name) for name in polygon_names]
        polygons = list(filter(bool, polygons))
    attr_list = ADPose.ADPoses.load_targets(data["ad_pose"], cover)
    blend_shapes = get_blend_shapes(polygons)
    for attr in attr_list:
        connect_all_bs(attr, blend_shapes)
    twist.set_twist_data(data["twist_data"], polygons)


def get_joints(polygons):
    joints = []
    for polygon in polygons:
        for sk in polygon.history(type="skinCluster"):
            for joint in sk.getInfluence():
                if joint not in joints:
                    joints.append(joint)
    return joints


def get_attr_target_names(polygons):
    target_names = []
    input_attrs = []
    for polygon in polygons:
        for _bs in polygon.history(type="blendShape"):
            for target_name in _bs.weight.elements():
                if target_name in target_names:
                    continue
                inputs = _bs.attr(target_name).inputs(p=1)
                if len(inputs) != 1:
                    continue
                target_names.append(target_name)
                input_attrs.append(inputs[0])
    return list(zip(input_attrs, target_names))


def comb_skin_bs():
    polygons = get_selected_polygons()
    duplicate_polygons = [polygon.duplicate()[0] for polygon in polygons]
    joints = get_joints(polygons)
    com_polygon = pm.polyUnite(duplicate_polygons, ch=0)[0]
    pm.delete(duplicate_polygons)
    pm.skinCluster(joints, com_polygon, tsb=1, mi=1)
    pm.select(polygons, com_polygon)
    pm.copySkinWeights(noMirror=1, surfaceAssociation="closestPoint", influenceAssociation="name")
    attr_target_names = get_attr_target_names(polygons)
    for input_attr, target_name in attr_target_names:
        ids = MIntArray()
        points = MPointArray()
        comb_index = 0
        for polygon in polygons:
            if len(polygon.history(type="blendShape")) == 0:
                comb_index += polygon.numVertices()
                continue
            _bs = bs.get_bs(polygon)
            try:
                _ids, _points = bs.get_bs_ids_points(polygon, target_name)
            except:
                continue
            for i in range(_ids.length()):
                ids.append(_ids[i]+comb_index)
                points.append(_points[i])
            comb_index += polygon.numVertices()
        bs.bridge_connect(input_attr, com_polygon)
        bs.set_bs_ids_points(com_polygon, target_name, ids, points)


def export_blend_shape_sdk_data_ui():
    # save_data_ui(default_scene_path, get_blend_shape_sdk_data)
    default_path = default_scene_path()
    path, _ = QFileDialog.getSaveFileName(get_host_app(), "Export To Unity", default_path, "Json (*.json)")
    if not path:
        return

    data = get_blend_shape_sdk_data()
    polygon_names = [row["polygon_name"] for row in data["bs_data"]]
    target_names = list(set(sum([row["target_names"] for row in data["bs_data"]], [])))
    bs_path = path.replace(".json", "_CBS.json")
    write_json_data(path, data)
    bs_api.export_targets(polygon_names, target_names, bs_path)
    QMessageBox.about(get_host_app(), u"提示", u"导出成功！")


def check_polygon_name(name):
    polygons = list(filter(is_polygon, pm.ls(name, type="transform")))
    if len(polygons) == 1:
        return polygons[0].name()
    return ""


def load_blend_shape_sdk_data_ui(cover=False):
    default_path = default_scene_path()
    path, _ = QFileDialog.getOpenFileName(get_host_app(), "Load Poses", default_path, "Json (*.json)")
    if not path:
        return
    data = read_json_data(path)
    polygons = get_selected_polygons()
    polygon_names = [row["polygon_name"] for row in data["bs_data"]]
    if len(polygon_names) != polygons:
        polygon_names = [check_polygon_name(name) for name in polygon_names]
    else:
        polygon_names = [polygon.name() for polygon in polygons]
    bs_path = path.replace(".json", "_CBS.json")
    bs_api.load_targets(polygon_names, bs_path)

    load_blend_shape_sdk_data(polygons, data, cover)
    QMessageBox.about(get_host_app(), u"提示", u"导入成功！")


def test():
    path = "D:/work/ADPose/export_load_bs/RY016C.rbf.v017.json"
    data = read_json_data(path)
    polygons = get_selected_polygons()
    polygon_names = [row["polygon_name"] for row in data["bs_data"]]
    if len(polygon_names) != polygons:
        polygon_names = [check_polygon_name(name) for name in polygon_names]
    else:
        polygon_names = [polygon.name() for polygon in polygons]
    bs_path = path.replace(".json", "_CBS.json")
    bs_api.load_targets(polygon_names, bs_path)

    load_blend_shape_sdk_data(data, True)
