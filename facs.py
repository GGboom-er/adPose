# coding:utf-8
"""
FACS 面部动作编码系统模块
已从 pymel 迁移到 maya.cmds
"""
from maya import cmds
from . import config
import re
from . import bs
import json


def get_target_name(node, attr_name, default, value):
    """获取目标名称"""
    if value > default:
        suffix = "max"
    else:
        suffix = "min"
    ctrl_name = node.split("|")[-1].split(":")[-1]
    return "_".join([ctrl_name, attr_name, suffix])

def get_ctrl_sdk_data(ctrl, data=None):
    if data is None:
        data = []
    for trs in "trs":
        for xyz in "xyz":
            attr_name = trs + xyz
            attr = ctrl + "." + attr_name
            value = cmds.getAttr(attr)
            default = dict(t=0, r=0, s=1)[trs]
            if abs(default - value) < 0.001:
                continue
            target_name = get_target_name(ctrl, attr_name, default, value)
            data.append(dict(attr=attr, value=value, default_value=default, target_name=target_name))
    # 用户定义属性
    ud_attrs = cmds.listAttr(ctrl, ud=True) or []
    for attr_name in ud_attrs:
        attr = ctrl + "." + attr_name
        attr_type = cmds.addAttr(attr, q=True, at=True)
        if attr_type != "double":
            continue
        default = cmds.addAttr(attr, q=True, dv=True)
        value = cmds.getAttr(attr)
        if abs(default - value) < 0.001:
            continue
        target_name = get_target_name(ctrl, attr_name, default, value)
        data.append(dict(attr=attr, value=value, default_value=default, target_name=target_name))


def find_add_sdk_data(ctrls):
    """查找添加 SDK 数据"""
    data = []
    for ctrl in ctrls:
        get_ctrl_sdk_data(ctrl, data)
    return data


def get_bridge():
    """获取或创建桥接节点"""
    if cmds.objExists("CtrlAttrBsSdkBridge"):
        return "CtrlAttrBsSdkBridge"
    else:
        return cmds.group(em=True, n="CtrlAttrBsSdkBridge")


def add_sdk(attr, target_name, default_value, value):
    """添加 SDK"""
    bridge = get_bridge()
    if cmds.attributeQuery(target_name, node=bridge, exists=True):
        return
    cmds.addAttr(bridge, ln=target_name, min=0, max=1, at="double", k=True)
    bridge_attr = bridge + "." + target_name
    cmds.setDrivenKeyframe(bridge_attr, cd=attr, dv=default_value, v=0, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(bridge_attr, cd=attr, dv=value, v=1, itt="linear", ott="linear")


def add_sdk_by_selected():
    """对选择的控制器添加驱动"""
    for kwargs in find_add_sdk_data(cmds.ls(sl=True, type="transform") or []):
        add_sdk(**kwargs)


def rest_ctrl(ctrl):
    """重置控制器"""
    for trs in "trs":
        attr = ctrl + "." + trs
        if cmds.listConnections(attr, s=True, d=False):
            continue
        if cmds.getAttr(attr, l=True):
            continue
        for xyz in "xyz":
            attr = ctrl + "." + trs + xyz
            if cmds.listConnections(attr, s=True, d=False):
                continue
            if cmds.getAttr(attr, l=True):
                continue
            default = dict(t=0, r=0, s=1)[trs]
            cmds.setAttr(attr, default)
    # 用户定义属性
    ud_attrs = cmds.listAttr(ctrl, ud=True) or []
    for attr_name in ud_attrs:
        attr = ctrl + "." + attr_name
        attr_type = cmds.addAttr(attr, q=True, at=True)
        if attr_type != "double":
            continue
        if cmds.listConnections(attr, s=True, d=False):
            continue
        if cmds.getAttr(attr, l=True):
            continue
        default = cmds.addAttr(attr, q=True, dv=True)
        cmds.setAttr(attr, default)


def get_ib_by_targets(ib_names):
    """根据目标名称获取 IB 值"""
    for ib_name in ib_names:
        match = re.match(".+_IB([0-9]{2})$", ib_name)
        if match is None:
            continue
        ib = int(match.groups()[0])
        return ib
    return 60

def to_base_target(target_name, ib=60):
    bridge = get_bridge()
    data = get_base_sdk_data(bridge, target_name)
    if data is None:
        return
    ctrl, attr, default, value = data
    bw = ib/60.0
    cmds.setAttr(attr, default * (1 - bw) + value * bw)

def to_comb_target(target_name, ib=60):
    base_targets = target_name.split("_COMB_")
    for base_target in base_targets:
        to_base_target(base_target, ib)


def to_ib_target(target_name, ib=60):
    base_target = target_name[:-5]
    if target_is_comb(base_target):
        to_comb_target(base_target, ib=ib)
    else:
        _ib = get_ib_by_targets([target_name])
        to_base_target(base_target, ib=_ib*ib/60.0)

def to_targets(target_names, ib=60):
    for target in target_names:
        if target_is_base(target):
            to_base_target(target, ib=ib)
        elif target_is_ib(target):
            to_ib_target(target, ib=ib)
        elif target_is_comb(target):
            to_comb_target(target, ib=ib)


def get_targets():
    """获取所有目标"""
    if not cmds.objExists("CtrlAttrBsSdkBridge"):
        return []
    bridge = get_bridge()
    ud_attrs = cmds.listAttr(bridge, ud=True) or []
    return ud_attrs


def get_selected_polygons():
    """获取选中的多边形"""
    polygons = []
    for polygon in cmds.ls(sl=True, type="transform") or []:
        shapes = cmds.listRelatives(polygon, s=True, ni=True)
        if not shapes:
            continue
        if cmds.nodeType(shapes[0]) != "mesh":
            continue
        polygons.append(polygon)
    return polygons


def edit_target(target_name):
    """编辑目标"""
    selected = get_selected_polygons()
    if len(selected) != 2:
        cmds.warning("please selected two polygon")
        return
    bridge = get_bridge()
    if not cmds.attributeQuery(target_name, node=bridge, exists=True):
        cmds.warning("can not find " + target_name)
        return
    src, dst = selected
    attr = bridge + "." + target_name
    bs.bridge_connect_edit(attr, src, dst)

def exists_target(target_name):
    bridge = get_bridge()
    attr = bridge + "." + target_name
    return cmds.objExists(attr)

def edit_static_target(target_name):
    """编辑静态目标"""
    selected = get_selected_polygons()
    if len(selected) != 2:
        cmds.warning("please selected two polygon")
        return
    bridge = get_bridge()
    if not cmds.attributeQuery(target_name, node=bridge, exists=True):
        cmds.warning("can not find " + target_name)
        return
    src, dst = selected
    attr = bridge + "." + target_name
    bs.bridge_static_connect_edit(attr, src, dst)


def add_comb(target_names):
    """添加组合目标"""
    comb_name = "_COMB_".join(list(sorted(target_names)))
    bridge = get_bridge()
    if cmds.attributeQuery(comb_name, node=bridge, exists=True):
        return
    for target_name in target_names:
        if not cmds.attributeQuery(target_name, node=bridge, exists=True):
            cmds.warning("can not find " + target_name)
            return
        attr = bridge + "." + target_name
        if not cmds.listConnections(attr, s=True, d=False):
            cmds.warning("can not find " + target_name + " inputs")
            return
    cmds.addAttr(bridge, ln=comb_name, min=0, max=1, at="double", k=True)
    com = cmds.createNode("combinationShape", n=comb_name)
    cmds.connectAttr(com + ".outputWeight", bridge + "." + comb_name)
    cmds.setAttr(com + ".combinationMethod", 1)
    for i, target_name in enumerate(target_names):
        attr = bridge + "." + target_name
        input_attrs = cmds.listConnections(attr, s=True, d=False, p=True) or []
        if input_attrs:
            cmds.connectAttr(input_attrs[0], com + ".inputWeight[{}]".format(i))


def update_ib(target_name):
    """更新 IB"""
    bridge = get_bridge()
    if not cmds.attributeQuery(target_name, node=bridge, exists=True):
        cmds.warning("can not find " + target_name)
        return
    ibs = []
    for ib_name in get_targets():
        match = re.match(target_name + "_IB([0-9]{2})$", ib_name)
        if match is None:
            continue
        ib = int(match.groups()[0])
        ibs.append(ib)
    ibs = list(sorted(ibs))
    ibs = [0] + ibs + [60]
    for i in range(len(ibs) - 2):
        ib_name = target_name + "_IB%02d" % ibs[i + 1]
        attr = bridge + "." + ib_name
        inputs = cmds.listConnections(attr, s=True, d=False) or []
        if inputs:
            cmds.delete(inputs)
        cd = bridge + "." + target_name
        for dv, v in zip([1.0 / 60.0 * ibs[i + j] for j in range(3)], [0, 1, 0]):
            cmds.setDrivenKeyframe(attr, cd=cd, dv=dv, v=v, itt="linear", ott="linear")


def add_ib_by_ib_name(ib_name):
    """添加 IB"""
    bridge = get_bridge()
    target_name = ib_name[:-5]
    if cmds.attributeQuery(ib_name, node=bridge, exists=True):
        return ib_name
    cmds.addAttr(bridge, ln=ib_name, min=0, max=1, at="double", k=True)
    update_ib(target_name)
    return ib_name

def get_ib_target(target_name):
    bridge = get_bridge()
    if re.match(".+_IB[0-9]{2}$", target_name):
        return None
    if not cmds.attributeQuery(target_name, node=bridge, exists=True):
        return None
    attr = bridge + "." + target_name
    value = cmds.getAttr(attr)
    ib = int(round(value * 60))
    if ib == 60:
        return None
    if ib == 0:
        return None
    ib_name = target_name + "_IB%02d" % ib
    return ib_name


def add_current_ib(target_name):
    """添加 IB 目标"""
    ib_name = get_ib_target(target_name)
    if not ib_name:
        return
    add_ib_by_ib_name(ib_name)


def delete_base_target(target_name):
    bridge = get_bridge()
    attr = bridge + "." + target_name
    if not cmds.objExists(attr):
        return
    bs_nodes = cmds.listConnections(attr, s=False, d=True, type="blendShape") or []
    for bs_node in bs_nodes:
        bs.delete_target(bs_node, target_name)
    cmds.deleteAttr(attr)


def delete_ib_target(target_name):
    delete_base_target(target_name)
    update_ib(target_name[:-5])


def split_targets(target_names):
    type_targets = dict(
        base=[],
        comb=[],
        ib=[]
    )
    for target in target_names:
        if target_is_base(target):
            type_targets["base"].append(target)
        elif target_is_ib(target):
            type_targets["ib"].append(target)
        elif target_is_comb(target):
            type_targets["comb"].append(target)
    return type_targets

def delete_targets(target_names):
    """删除多个目标"""
    all_targets = get_targets()
    all_type = split_targets(all_targets)
    del_type = split_targets(target_names)

    for del_base in del_type["base"]:
        for comb in all_type["comb"]:
            # 检查这个 comb 是否包含待删除的 base 目标
            if del_base not in comb.split("_COMB_"):
                continue
            if comb in del_type["comb"]:
                continue
            del_type["comb"].append(comb)

    for del_comb in del_type["comb"]+del_type["base"]:
        for ib in all_type["ib"]:
            # 检查这个 ib 是否对应待删除的 comb
            if del_comb not in ib:
                continue
            if ib in del_type["ib"]:
                continue
            del_type["ib"].append(ib)

    for ib_target in del_type["ib"]:
        delete_ib_target(ib_target)
    for comb_target in del_type["comb"]:
        delete_base_target(comb_target)
    for base_target in del_type["base"]:
        delete_base_target(base_target)


def reset_face_ctrl():
    """重置面部控制器"""
    for ctrl in cmds.ls("FCtrl*", "*Control", type="transform") or []:
        full_path = cmds.ls(ctrl, l=True)
        if full_path and "FaceGroup" not in full_path[0]:
            continue
        rest_ctrl(ctrl)

def find_mirror_ctrl(ctrl):
    """查找镜像控制器"""
    ctrl_name = ctrl.split("|")[-1].split(":")[-1]
    ctrl_list = cmds.ls(config.get_rl_names(ctrl_name)) or []
    if len(ctrl_list) != 1:
        return None
    return ctrl_list[0]


def get_base_sdk_data(bridge, target_name):
    """获取基础 SDK 数据"""
    attr = bridge + "." + target_name
    uu = cmds.listConnections(attr, s=True, d=False, type="animCurveUU") or []
    if len(uu) != 1:
        return None
    uu = uu[0]
    input_attrs = cmds.listConnections(uu, s=True, d=False, p=True) or []
    if len(input_attrs) != 1:
        return None
    input_attr = input_attrs[0]
    ctrl = input_attr.split(".")[0]
    ctrl_type = cmds.nodeType(ctrl)
    if ctrl_type == "unitConversion":
        input_attrs2 = cmds.listConnections(ctrl, s=True, d=False, p=True) or []
        if len(input_attrs2) != 1:
            return None
        input_attr = input_attrs2[0]
        ctrl = input_attr.split(".")[0]
    node, attr = input_attr.split(".")
    sn = cmds.attributeQuery(attr, node=node, sn=True)
    input_attr = node+"."+sn

    if target_name[-4:] == "_max":
        value = cmds.keyframe(uu, floatChange=True, q=True, index=(1, 1))
        default_value = cmds.keyframe(uu, floatChange=True, q=True, index=(0, 0))
    else:
        value = cmds.keyframe(uu, floatChange=True, q=True, index=(0, 0))
        default_value = cmds.keyframe(uu, floatChange=True, q=True, index=(1, 1))
    if value and default_value:
        return ctrl, input_attr, default_value[0], value[0]
    return None


def add_mirror_base_target(bridge, target_name):
    """添加镜像基础目标"""
    result = get_base_sdk_data(bridge, target_name)
    if result is None:
        return None
    ctrl, attr, default_value, value = result
    mirror_ctrl = find_mirror_ctrl(ctrl)
    if mirror_ctrl is None:
        return None
    attr_name = attr.split(".")[-1]
    mirror_attr = mirror_ctrl + "." + attr_name
    target_name = get_target_name(mirror_ctrl, attr_name, default_value, value)
    if not cmds.attributeQuery(target_name, node=bridge, exists=True):
        add_sdk(mirror_attr, target_name, default_value, value)
    return target_name

def add_mirror_comb_target(bridge, comb_target):
    target_names = [name for name in comb_target.split("_COMB_") if name]
    mirror_target_names = []
    for base_target in target_names:
        mirror_target_name = add_mirror_base_target(bridge, base_target)
        if mirror_target_name is None:
            mirror_target_names.append(base_target)
        else:
            mirror_target_names.append(mirror_target_name)
    mirror_target_names = list(sorted(mirror_target_names))
    mirror_target_name = "_COMB_".join(mirror_target_names)
    add_comb(mirror_target_names)
    return mirror_target_name

def add_mirror_ib_target(bridge, ib_target):
    base_target = ib_target[:-5]
    if target_is_comb(base_target):
        mirror_target_name = add_mirror_comb_target(bridge, base_target)
    else:
        mirror_target_name = add_mirror_base_target(bridge, base_target)
    ib = get_ib_by_targets([ib_target])
    ib_name = mirror_target_name + "_IB%02d" % ib
    add_ib_by_ib_name(ib_name)
    return ib_name


def mirror_targets(target_names):
    """镜像目标"""
    polygons = get_selected_polygons()
    driver = cmds.ls("*|Planes|Driver", type="transform") or []
    if len(driver) == 1:
        polygons.append(driver[0])

    type_targets = split_targets(target_names)
    for ib_target in type_targets["ib"]:
        base_target = ib_target[:-5]
        if target_is_comb(base_target):
            if base_target not in type_targets["comb"]:
                type_targets["comb"].append(base_target)
        elif target_is_base(base_target):
            if base_target not in type_targets["base"]:
                type_targets["base"].append(base_target)

    for comb_target in type_targets["comb"]:
        base_targets = comb_target.split("_COMB_")
        for base_target in base_targets:
            if base_target not in type_targets["base"]:
                type_targets["base"].append(base_target)

    bridge = get_bridge()
    target_mirrors = []
    for base_target in type_targets["base"]:
        mirror_target = add_mirror_base_target(bridge, base_target)
        target_mirrors.append([base_target, mirror_target])
    for base_target in type_targets["comb"]:
        mirror_target = add_mirror_comb_target(bridge, base_target)
        target_mirrors.append([base_target, mirror_target])
    for base_target in type_targets["ib"]:
        mirror_target = add_mirror_ib_target(bridge, base_target)
        target_mirrors.append([base_target, mirror_target])

    for polygon in polygons:
        _bs = bs.find_bs(polygon)
        if not _bs:
            continue
        for src, dst in target_mirrors:
            if not cmds.attributeQuery(src, node=_bs, exists=True):
                continue
            bs.bridge_connect(bridge + "." + dst, polygon)
        bs.mirror_targets(polygon, target_mirrors)


def get_sdk_data():
    """获取 SDK 数据"""
    bridge = get_bridge()
    data = []
    ud_attrs = cmds.listAttr(bridge, ud=True) or []
    for attr_name in ud_attrs:
        if attr_name[-4:-2] == "IB":
            data.append(dict(
                typ="ib",
                target_name=attr_name
            ))
        elif "_COMB_" in attr_name:
            data.append(dict(
                typ="comb",
                target_names=[name for name in attr_name.split("_COMB_") if name],
                target_name=attr_name
            ))
        else:
            result = get_base_sdk_data(bridge, attr_name)
            if result:
                ctrl, attr, default_value, value = result
                data.append(dict(
                    typ="base",
                    ctrl=ctrl,
                    attr=attr.split(".")[-1],
                    default_value=default_value,
                    value=value,
                    target_name=attr_name
                ))
    return data


def set_sdk_data(data):
    """设置 SDK 数据"""
    for row in data:
        if row["typ"] == "base":
            ctrl_list = cmds.ls(row["ctrl"], type="transform") or []
            if len(ctrl_list) != 1:
                continue
            ctrl = ctrl_list[0]
            add_sdk(
                attr=ctrl + "." + row["attr"],
                target_name=row["target_name"],
                default_value=row["default_value"],
                value=row["value"],
            )
    for row in data:
        if row["typ"] == "comb":
            add_comb(row["target_names"])
    for row in data:
        if row["typ"] == "ib":
            add_ib_by_ib_name(row["target_name"])


def get_driver_polygon():
    """获取驱动多边形"""
    driver = cmds.ls("*|Planes|Driver", type="transform") or []
    if len(driver) != 1:
        cmds.warning("can not find driver")
        return None
    return driver[0]


def warp_copy(targets=None):
    """包裹复制"""
    all_to_zero()
    polygons = get_selected_polygons()
    if not len(polygons) == 2:
        cmds.warning("please selected two polygon")
        return
    if not targets:
        targets = get_targets()
    src, dst = polygons
    cmds.refresh()
    warp = cmds.duplicate(dst)[0]
    cmds.select(warp, src)
    from maya import mel
    mel.eval('CreateWrap')
    for target in targets:
        to_targets([target], 60)
        cmds.select(warp, dst)
        edit_target(target)
        to_targets([target], 0)
    cmds.delete(warp)



def is_base_target(data):
    if len(data) != 1:
        return False
    target_name = data[0]["target_name"]
    if not exists_target(target_name):
        return True
    if get_ib_target(target_name):
        return False
    else:
        return True

def is_ib_target(data):
    if len(data) != 1:
        return False
    target_name = data[0]["target_name"]
    if not exists_target(target_name):
        return False
    if get_ib_target(target_name):
        return True
    else:
        return False

def is_comb_target(data):
    if len(data) < 2:
        return False
    bridge = get_bridge()
    attrs = [bridge+"."+row["target_name"] for row in data]
    for attr in attrs:
        if not cmds.objExists(attr):
            return False
        value = cmds.getAttr(attr)
        if abs(value - 1) > 0.001:
            return False
    return True


def is_comb_ib(data):
    if len(data) < 2:
        return False
    bridge = get_bridge()
    target_names = [row["target_name"] for row in data]
    comb_name = "_COMB_".join(list(sorted(target_names)))
    attr = bridge + "." + comb_name
    if not cmds.objExists(attr):
        return False
    attrs = [bridge+"."+row["target_name"] for row in data]
    values = []
    for attr in attrs:
        if not cmds.objExists(attr):
            return False
        values.append(cmds.getAttr(attr))
    ibs = [int(round(value * 60)) for value in values]
    for ib in ibs:
        if ib != ibs[0]:
            return False
    if ibs[0] == 0 or ibs[0] == 60:
        return False
    return True


def get_auto_target_name_by_data(data):
    if is_base_target(data):
        return data[0]["target_name"], "base"
    elif is_ib_target(data):
        return get_ib_target(data[0]["target_name"]), "ib"
    elif is_comb_target(data):
        target_names = [row["target_name"] for row in data]
        comb_name = "_COMB_".join(list(sorted(target_names)))
        return comb_name, "comb"
    elif is_comb_ib(data):
        target_names = [row["target_name"] for row in data]
        comb_name = "_COMB_".join(list(sorted(target_names)))
        comb_ib_target = get_ib_target(comb_name)
        return comb_ib_target, "ib"
    return "", ""


def auto_add_target(data, target_name, target_type):
    if target_type == "base":
        add_sdk(**data[0])
    elif target_type == "comb":
        add_comb([row["target_name"] for row in data])
    elif target_type == "ib":
        add_ib_by_ib_name(target_name)

def get_real_ctrls(query):
    ctrls, _ = get_use_ctrls_datas()
    ctrls = cmds.ls(query + ctrls)
    ctrls = list(set(ctrls))
    return ctrls

def auto_add_edit_target(query):
    polygons = bs.get_selected_polygons()
    ctrls = get_real_ctrls(query)
    data = find_add_sdk_data(ctrls)

    target_name, target_type = get_auto_target_name_by_data(data)
    if not target_name:
        return
    auto_add_target(data, target_name, target_type)
    if len(polygons) != 2:
        return
    cmds.select(polygons)
    edit_target(target_name)


def auto_apply(query):
    """自动应用"""
    selected = cmds.ls(sl=1)
    ctrls = get_real_ctrls(query)
    data = find_add_sdk_data(ctrls)
    target_name, target_type = get_auto_target_name_by_data(data)

    if not target_name:
        return

    def _add_target(_target_name):
        bridge = get_bridge()
        auto_add_target(data, target_name, target_type)
        return bridge + "." + _target_name

    def _set_target(_target_name):
        if not target_is_base(_target_name):
            to_targets([_target_name])

    cmds.select(cmds.ls(selected))
    bs.auto_duplicate_edit([target_name], _add_target, _set_target)


import re

def target_is_ib(target):
    return bool(re.search(r"_IB\d+$", target))

def target_is_comb(target):
    return "_COMB_" in target

def target_is_base(target):
    return not target_is_ib(target) and not target_is_comb(target)


def get_use_ctrls_datas():
    bridge = get_bridge()
    ctrls = []
    datas = []
    for target in get_targets():
        attr = bridge + "." + target
        if abs(cmds.getAttr(attr))<0.0001:
            continue
        if not target_is_base(target):
            continue
        data = get_base_sdk_data(bridge, target)
        datas.append(data)
        ctrl = data[0]
        if ctrl not in ctrls:
            ctrls.append(ctrl)
    return ctrls, datas


def all_to_zero():
    ctrls, datas = get_use_ctrls_datas()
    identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    for ctrl in ctrls:
        cmds.xform(ctrl, m=identity, ws=False)
    for data in datas:
        ctrl, attr, default_value, value = data
        cmds.setAttr(attr, default_value)


def esc():
    if bs.is_on_duplicate_edit():
        bs.finish_duplicate_edit(lambda x:x)
    all_to_zero()
