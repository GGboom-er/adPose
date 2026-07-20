# coding:utf-8
"""
adPose 公共工具模块
提取自 ADPose.py / bs.py / facs.py / twist.py 中的重复函数。
各模块可逐步迁移到此模块。
"""
from maya import cmds
from . import config


# === 场景查询 ===

def get_selected_polygons():
    """获取当前选中的多边形 transform 节点"""
    polygons = []
    for polygon in cmds.ls(sl=True, type="transform") or []:
        shapes = cmds.listRelatives(polygon, s=True, ni=True) or []
        if not shapes:
            continue
        if cmds.nodeType(shapes[0]) != "mesh":
            continue
        polygons.append(polygon)
    return polygons


def is_polygon(polygon):
    """判断节点是否为多边形"""
    if not cmds.objExists(polygon):
        return False
    if cmds.nodeType(polygon) != "transform":
        return False
    shapes = cmds.listRelatives(polygon, s=True, ni=True)
    if not shapes:
        return False
    if cmds.nodeType(shapes[0]) != "mesh":
        return False
    return True


def find_node_by_name(name):
    """按名称精确查找唯一节点"""
    nodes = cmds.ls(name) or []
    if len(nodes) == 1:
        return nodes[0]
    return None


def find_ctrl_by_joint(joint):
    """通过骨骼查找对应控制器"""
    joint_name = joint if isinstance(joint, str) else str(joint)
    if "Part" in joint_name:
        return None
    short_name = joint_name.split("|")[-1].split(":")[-1]
    ctrl_list = cmds.ls(config.get_ctrl_names(short_name), type="transform") or []
    if len(ctrl_list) == 1:
        return ctrl_list[0]
    return None


def find_mirror_joint(joint):
    """查找镜像骨骼"""
    joint_name = joint if isinstance(joint, str) else str(joint)
    short_name = joint_name.split("|")[-1].split(":")[-1]
    joints = cmds.ls(config.get_rl_names(short_name), type="joint") or []
    if len(joints) != 1:
        return None
    return joints[0]


# === 组操作 ===

def create_group(n="|FaceGroup|SkeletonGroup", d=False, v=None, i=None):
    """递归创建层级组"""
    if d:
        if cmds.objExists(n):
            cmds.delete(n)
    if cmds.objExists(n):
        return n
    fields = n.split("|")
    n = fields.pop(-1)
    if len(fields) > 1:
        result = cmds.group(em=1, n=n, p=create_group("|".join(fields)))
    else:
        result = cmds.group(em=1, n=n)
    if v is not None:
        cmds.setAttr(result + ".v", v)
    if i is not None:
        cmds.setAttr(result + ".inheritsTransform", i)
    return result


# === 常量 ===

EPSILON = 1e-5
"""通用容差值（用于浮点比较）"""
