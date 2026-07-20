# coding:utf-8
"""
工具模块
已从 pymel 迁移到 maya.cmds
"""
from . import bs, facs
from . import ADPose
from .general_ui import *
from . import twist
import pickle


def get_blend_shape_sdk_data():
    """获取 blendShape SDK 数据"""
    polygons = bs.get_selected_polygons()
    exist_target_names = []
    for polygon in polygons:
        _bs = bs.find_bs(polygon)
        if not _bs:
            continue
        for name in bs.get_bs_target_names(_bs):
            if name not in exist_target_names:
                exist_target_names.append(name)
    ad_target_names = [target_name for target_name in ADPose.ADPoses.get_targets() if target_name in exist_target_names]
    ad_pose = list(ad_target_names)
    twist_data = twist.get_twist_data()
    sdk_data = facs.get_sdk_data()

    all_target_names = ADPose.ADPoses.get_targets() + twist.get_targets() + facs.get_targets()
    all_target_names = [target for target in all_target_names if target in exist_target_names]
    bs_data = []
    for polygon in polygons:
        _bs = bs.get_bs(polygon)
        targets = []
        for name in bs.get_bs_target_names(_bs):
            if name not in all_target_names:
                continue
            targets.append(bs.get_bs_target_data(_bs, name))
        bs_data.append(dict(
            polygon_name=polygon.split("|")[-1].split(":")[-1],
            targets=targets
        ))
    data = dict(
        ad_pose=ad_pose,
        bs_data=bs_data,
        sdk_data=sdk_data,
        twist_data=twist_data,
    )
    return data


def find_polygon_by_name(name):
    """根据名称查找多边形"""
    polygons = cmds.ls(name, type="transform") or []
    polygons = [p for p in polygons if bs.is_polygon(p)]
    if len(polygons) > 0:
        return polygons[0]
    return None

def set_blend_shape_sdk_data(data, cover=False):
    """加载 blendShape SDK 数据"""
    polygons = bs.get_selected_polygons()
    polygon_names = [row["polygon_name"] for row in data["bs_data"]]
    if len(polygons) != len(polygon_names):
        polygons = [find_polygon_by_name(name) for name in polygon_names]
        polygons = list(filter(bool, polygons))
    ADPose.ADPoses.load_targets(data["ad_pose"], cover)
    twist.set_twist_data(data["twist_data"])
    facs.set_sdk_data(data["sdk_data"])
    for polygon, bs_data in zip(polygons, data["bs_data"]):
        _bs = bs.get_bs(polygon)
        for target_data in bs_data["targets"]:
            bs.set_bs_target_data(_bs, target_data)



def export_blend_shape_sdk_data(path):
    """导出 blendShape SDK 数据 UI"""
    data = get_blend_shape_sdk_data()
    with open(path, "wb") as fp:
        pickle.dump(data, fp)


def load_blend_shape_sdk_data(path, cover=False):
    with open(path, "rb") as fp:
        data = pickle.load(fp)
    set_blend_shape_sdk_data(data, cover=cover)


def export_blend_shape_sdk_data_ui():
    """导出 blendShape SDK 数据 UI"""
    default_path = default_scene_path()
    path, _ = QFileDialog.getSaveFileName(get_host_app(), "Export To Unity", default_path, "pickle (*.pkl)")
    if not path:
        return
    export_blend_shape_sdk_data(path)
    QMessageBox.about(get_host_app(), u"提示", u"导出成功！")


def load_blend_shape_sdk_data_ui(cover=False):
    """加载 blendShape SDK 数据 UI"""
    default_path = default_scene_path()
    path, _ = QFileDialog.getOpenFileName(get_host_app(), "Load Poses", default_path, "pickle (*.pkl)")
    if not path:
        return
    load_blend_shape_sdk_data(path, cover)
    QMessageBox.about(get_host_app(), u"提示", u"导入成功！")