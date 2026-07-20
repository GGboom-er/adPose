# coding:utf-8
"""
扭曲变形模块
已从 pymel 迁移到 maya.cmds
"""
import re
import time
from maya import cmds
import math
from . import bs
from . import config


def find_node_by_name(name):
    """根据名称查找节点"""
    nodes = cmds.ls(name)
    if len(nodes) == 1:
        return nodes[0]
    print("can not find " + name)
    return None


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


def find_ctrl_by_joint(joint):
    """根据骨骼查找控制器"""
    joint_name = joint.split("|")[-1].split(":")[-1]
    ctrl_list = cmds.ls(config.get_ctrl_names(joint_name), type="transform") or []
    ctrl_list.sort(key=lambda x: len(x))
    if len(ctrl_list) > 0:
        return ctrl_list[0]
    return None


def find_mirror_joint(joint):
    """查找镜像骨骼"""
    joint_name = joint.split("|")[-1].split(":")[-1]
    joints = cmds.ls(config.get_rl_names(joint_name), type="joint") or []
    if len(joints) != 1:
        return None
    return joints[0]


class Twist(object):
    """扭曲变形类"""

    def __init__(self, **kwargs):
        self.ctrl = None
        self.axis = "X"
        self.joint = kwargs.get("joint")
        self.find_ctrl(kwargs.get("ctrl"))
        self.init_angle()

    @property
    def twist_name(self):
        return "twist{self.axis}".format(**locals())

    @property
    def twist_ctrl_scale(self):
        return "twistCtrlScale{self.axis}".format(**locals())

    def find_ctrl(self, ctrl=None):
        if ctrl is not None:
            self.ctrl = ctrl
            return self.ctrl
        if self.ctrl is not None:
            return self.ctrl
        self.ctrl = find_ctrl_by_joint(self.joint)
        return self.ctrl

    def update_twist_ctrl_scale(self):
        if cmds.attributeQuery(self.twist_ctrl_scale, node=self.joint, exists=True):
            return
        ctrl = self.find_ctrl()
        if ctrl is None:
            return
        joint_value = cmds.getAttr(self.joint + "." + self.twist_name)
        ctrl_value = cmds.getAttr(self.ctrl + ".r" + self.axis.lower())
        if abs(joint_value) < 1.0:
            return
        if abs(ctrl_value) < 1.0:
            return
        twist_scale = ctrl_value / joint_value
        cmds.addAttr(self.joint, ln=self.twist_ctrl_scale, k=True, at="double")
        cmds.setAttr(self.joint + "." + self.twist_ctrl_scale, twist_scale)

    def init_angle(self):
        prefix = self.joint + "_X_"
        vector = [1, 0, 0]
        attr = "outputAxisX"
        if cmds.attributeQuery(self.twist_name, node=self.joint, exists=True):
            return
        is_opm = bool(cmds.listConnections(self.joint + ".offsetParentMatrix", s=True, d=False))
        if is_opm:
            # OPM 模式：由于 joint.matrix 是静态的，我们需要计算 joint.matrix * joint.offsetParentMatrix
            mult_curr = cmds.createNode("multMatrix", n=prefix + "currentMatrix")
            cmds.connectAttr(self.joint + ".matrix", mult_curr + ".matrixIn[0]")
            cmds.connectAttr(self.joint + ".offsetParentMatrix", mult_curr + ".matrixIn[1]")

            decomp = cmds.createNode("decomposeMatrix", n=prefix + "rotateMatrixDecompose")
            cmds.connectAttr(mult_curr + ".matrixSum", decomp + ".inputMatrix")
            rotate_matrix_attr = mult_curr + ".matrixSum"
        else:
            # 传统模式：从通道读取旋转
            rotate_matrix = cmds.createNode("composeMatrix", n=prefix + "rotateMatrix")
            cmds.connectAttr(self.joint + ".rotate", rotate_matrix + ".inputRotate")
            rotate_matrix_attr = rotate_matrix + ".outputMatrix"

        swing_vector = cmds.createNode("pointMatrixMult", n=prefix + "swingVector")
        cmds.setAttr(swing_vector + ".inPoint", *vector)
        cmds.connectAttr(rotate_matrix_attr, swing_vector + ".inMatrix")

        swing_angle = cmds.createNode("angleBetween", n=prefix + "angleBetween")
        cmds.connectAttr(swing_vector + ".output", swing_angle + ".vector2")
        cmds.setAttr(swing_angle + ".vector1", *vector)

        swing_quat = cmds.createNode("eulerToQuat", n=prefix + "swingQuat")
        cmds.connectAttr(swing_angle + ".euler", swing_quat + ".inputRotate")

        swing_inverse = cmds.createNode("quatInvert", n=prefix + "swingInverse")
        cmds.connectAttr(swing_quat + ".outputQuat", swing_inverse + ".inputQuat")

        rotate_quat = cmds.createNode("decomposeMatrix", n=prefix + "rotateQuat")
        cmds.connectAttr(rotate_matrix_attr, rotate_quat + ".inputMatrix")

        twist_quat = cmds.createNode("quatProd", n=prefix + "twistQuat")
        cmds.connectAttr(rotate_quat + ".outputQuat", twist_quat + ".input1Quat")
        cmds.connectAttr(swing_inverse + ".outputQuat", twist_quat + ".input2Quat")

        axis_angle = cmds.createNode("quatToAxisAngle", n=prefix + "axisAngle")
        cmds.connectAttr(twist_quat + ".outputQuat", axis_angle + ".inputQuat")

        angle_unit = cmds.createNode("unitConversion", n=prefix + "angleUnit")
        cmds.setAttr(angle_unit + ".conversionFactor", 180 / math.pi)
        cmds.connectAttr(axis_angle + ".outputAngle", angle_unit + ".input")

        multiply = cmds.createNode("multiplyDivide", n=prefix + "multiply")
        cmds.connectAttr(angle_unit + ".output", multiply + ".input1X")
        cmds.setAttr(multiply + ".input2X", -1)

        condition = cmds.createNode("condition", n=prefix + "condition")
        cmds.connectAttr(axis_angle + "." + attr, condition + ".firstTerm")
        cmds.setAttr(condition + ".operation", 2)
        cmds.connectAttr(angle_unit + ".output", condition + ".colorIfTrueR")
        cmds.connectAttr(multiply + ".outputX", condition + ".colorIfFalseR")
        cmds.addAttr(self.joint, ln=self.twist_name, k=True, at="double", min=0, max=1)
        cmds.connectAttr(condition + ".outColorR", self.joint + "." + self.twist_name)

    def value_to_target_name(self, value):
        if abs(value) < 1:
            return None
        joint_name = self.joint.split("|")[-1].split(":")[-1]
        abs_value = abs(int(round(value)))
        if value > 0:
            plus_minus = "plus"
        else:
            plus_minus = "minus"
        name = "{joint_name}_{self.twist_name}_{plus_minus}{abs_value}".format(**locals())
        return name

    def add_current_target(self):
        target_name = self.add_target_by_value(cmds.getAttr(self.joint + "." + self.twist_name))
        if not cmds.attributeQuery("twistCtrlScale", node=self.joint, exists=True):
            self.update_twist_ctrl_scale()
        return self.joint + "." + target_name

    def get_current_target(self):
        target_name = self.value_to_target_name(cmds.getAttr(self.joint + "." + self.twist_name))
        return target_name

    def has_target(self, target):
        return cmds.objExists(self.joint+"."+target)

    def add_target_by_value(self, value):
        target_name = self.value_to_target_name(value)
        if not cmds.attributeQuery(target_name, node=self.joint, exists=True):
            values = self.get_values()
            values.append(value)
            self.update_values(values)
        return target_name

    def edit_target(self, target_name):
        if not cmds.attributeQuery(target_name, node=self.joint, exists=True):
            return
        if abs(cmds.getAttr(self.joint + "." + target_name) - 1) > 0.01:
            return
        polygons = get_selected_polygons()
        src, dst = polygons
        bs.bridge_connect_edit(self.joint + "." + target_name, src, dst)

    def update_values(self, values):
        sort_values = sorted(values + [-180.0, 0, 180.0])
        for value in values:
            if value in [-180.0, 0, 180.0]:
                continue
            name = self.value_to_target_name(value)
            if not cmds.attributeQuery(name, node=self.joint, exists=True):
                cmds.addAttr(self.joint, ln=name, k=True, at="double", min=0, max=1)
            i = sort_values.index(value)
            attr = self.joint + "." + name
            # 删除输入连接
            inputs = cmds.listConnections(attr, s=True, d=False) or []
            if inputs:
                cmds.delete(inputs)
            cd = self.joint + "." + self.twist_name
            cmds.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i - 1], v=0, itt="linear", ott="linear")
            cmds.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i], v=1, itt="linear", ott="linear")
            cmds.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i + 1], v=0, itt="linear", ott="linear")
            if sort_values[i - 1] == -180.0:
                cmds.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i - 1], v=1, itt="linear", ott="linear")
            if sort_values[i + 1] == 180.0:
                cmds.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i + 1], v=1, itt="linear", ott="linear")

    def get_value_by_target(self, target_name):
        if not cmds.attributeQuery(target_name, node=self.joint, exists=True):
            return None
        attr = self.joint + "." + target_name
        uu = cmds.listConnections(attr, s=True, d=False, type="animCurveUU") or []
        if len(uu) != 1:
            return None
        value = cmds.keyframe(uu[0], floatChange=True, q=True, index=(1, 1))
        if value:
            return value[0]
        return None

    def get_values(self):
        values = []
        joint_name = self.joint.split("|")[-1].split(":")[-1]
        prefix = "{joint_name}_{self.twist_name}_".format(**locals())
        attrs = cmds.listAttr(self.joint, ud=True) or []
        for attr_name in attrs:
            if not attr_name.startswith(prefix):
                continue
            value = self.get_value_by_target(attr_name)
            if value is None:
                continue
            values.append(value)
        return values

    def delete_targets(self, targets):
        for target_name in targets:
            attr = self.joint + "." + target_name
            # 删除连接的 blendShape 目标
            bs_nodes = cmds.listConnections(attr, s=False, d=True, type="blendShape") or []
            for bs_node in bs_nodes:
                bs.delete_target(bs_node, target_name)
            # 删除输入连接
            inputs = cmds.listConnections(attr, s=True, d=False) or []
            if inputs:
                cmds.delete(inputs)
            cmds.deleteAttr(attr)
        self.update_values(self.get_values())

    def to_target(self, target_name, ib):
        if self.find_ctrl() is None:
            return
        if not cmds.attributeQuery(target_name, node=self.joint, exists=True):
            return
        attr = self.joint + "." + target_name
        uu = cmds.listConnections(attr, s=True, d=False, type="animCurveUU") or []
        if len(uu) != 1:
            return
        value = cmds.keyframe(uu[0], floatChange=True, q=True, index=(1, 1))
        if not value:
            return
        value = value[0]
        scale = 1.0
        if cmds.attributeQuery(self.twist_ctrl_scale, node=self.joint, exists=True):
            scale = cmds.getAttr(self.joint + "." + self.twist_ctrl_scale)
        real_value = value * ib / 60.0 * scale
        cmds.setAttr(self.ctrl + ".r", 0, 0, 0)
        cmds.setAttr(self.ctrl + ".r" + self.axis.lower(), real_value)

    def mirror_target(self, target_names, polygons):
        names = []
        mirror_joint = find_mirror_joint(self.joint)
        if mirror_joint is None:
            return names
        mirror = Twist(joint=mirror_joint)
        for target_name in target_names:
            value = self.get_value_by_target(target_name)
            if value is None:
                return names
            mirror_target_name = mirror.add_target_by_value(value)
            names.append([target_name, mirror_target_name])
            for polygon in polygons:
                bs.bridge_connect(mirror.joint + "." + mirror_target_name, polygon)
        if cmds.attributeQuery(mirror.twist_ctrl_scale, node=mirror.joint, exists=True):
            return names
        if not cmds.attributeQuery(self.twist_ctrl_scale, node=self.joint, exists=True):
            return names
        cmds.addAttr(mirror.joint, ln=mirror.twist_ctrl_scale, k=True, at="double")
        cmds.setAttr(mirror.joint + "." + mirror.twist_ctrl_scale,
                     cmds.getAttr(self.joint + "." + self.twist_ctrl_scale))
        return names

    def get_targets(self):
        joint_name = self.joint
        axis = self.axis
        target_re = r"^{joint_name}_twist{axis}_(plus|minus)[0-9]+$".format(**locals())
        target_names = []
        attrs = cmds.listAttr(self.joint) or []
        for attr_name in attrs:
            if re.match(target_re, attr_name):
                target_names.append(attr_name)
        return target_names


def get_joints_by_joint_query(joint_query):
    """根据查询获取骨骼列表"""
    ls_field = [field for field in joint_query.split(",") if field]
    if len(ls_field) == 0:
        return []
    return cmds.ls(ls_field, type="joint") or []


def get_twist(joint_query, ctrl=None):
    """添加目标"""
    if not cmds.pluginInfo("matrixNodes", q=True, l=True):
        cmds.loadPlugin("matrixNodes")
    if not cmds.pluginInfo("quatNodes", q=True, l=True):
        cmds.loadPlugin("quatNodes")
    joints = get_joints_by_joint_query(joint_query)
    has_rotate_joints = []
    for joint in joints:
        rotate = cmds.getAttr(joint + ".r")[0]
        rotate_sum = sum([abs(xyz) for xyz in rotate])
        if rotate_sum > 0.00001:
            has_rotate_joints.append(joint)
    if len(has_rotate_joints) != 1:
        cmds.warning("please load one rotate joint")
        return
    joint = has_rotate_joints[0]
    if ctrl is not None:
        ctrl = find_node_by_name(ctrl)
    twist = Twist(joint=joint, ctrl=ctrl)
    return twist


def edit_target(target_name):
    """编辑目标"""
    joint = get_joint_by_target(target_name)
    if joint is None:
        return
    Twist(joint=joint).edit_target(target_name)


def add_edit_target(joint_query):
    polygons = get_selected_polygons()
    twist = get_twist(joint_query)
    if twist is None:
        return
    target = twist.get_current_target()

    if not twist.has_target(target):
        twist.add_current_target()
    else:
        twist.to_target(target, 60)
    if not len(polygons) == 2:
        return
    cmds.select(polygons)
    twist.edit_target(target)


def auto_insert_pose(joint_query):
    twist = get_twist(joint_query)
    if twist is None:
        return
    target_name = twist.get_current_target()
    if target_name is None:
        return
    polygons = []
    for target in twist.get_targets():
        attr = twist.joint + "." + target
        for _bs in cmds.listConnections(attr, type="blendShape") or []:
            geo = cmds.blendShape(_bs, q=True, g=True)
            parent = cmds.listRelatives(geo[0], p=1)
            if not parent:
                continue
            polygon = parent[0]
            polygons.append(polygon)
    if not polygons:
        return
    dup_polygons = []
    for polygon in polygons:
        dup_polygons.append(cmds.duplicate(polygon)[0])
    attr = twist.add_current_target()
    for src, dst in zip(dup_polygons, polygons):
        bs.bridge_connect_edit(attr, src, dst)
    cmds.delete(dup_polygons)


def get_joint_by_target(target):
    """根据目标名称获取骨骼"""
    if not target:
        return None
    match = re.match(r"^(?P<joint>\w+)_twistX_(plus|minus)[0-9]{1,3}$", target)
    if not match:
        return None
    joint_name = match.groupdict()["joint"]
    return find_node_by_name(joint_name)



def to_target(target_name, ib=60):
    """设置目标姿势"""
    joint = get_joint_by_target(target_name)
    if joint is None:
        return
    Twist(joint=joint).to_target(target_name, ib)


def del_targets(target_names):
    """删除目标"""
    for target_name in target_names:
        joint = get_joint_by_target(target_name)
        if joint is None:
            continue
        Twist(joint=joint).delete_targets([target_name])


def mirror_targets(target_names):
    """镜像目标"""
    polygons = get_selected_polygons()
    joint_targets = {}
    for target_name in target_names:
        joint = get_joint_by_target(target_name)
        if joint is None:
            continue
        joint_targets.setdefault(joint, []).append(target_name)
    target_mirrors = []
    for joint, names in joint_targets.items():
        target_mirrors += Twist(joint=joint).mirror_target(names, polygons)
    for polygon in polygons:
        bs.mirror_targets(polygon, target_mirrors)


def get_targets():
    """获取所有扭曲目标"""
    axis = "X"
    target_names = []
    for joint in cmds.ls(type="joint") or []:
        if not cmds.attributeQuery("twist" + axis, node=joint, exists=True):
            continue
        joint_name = joint.split("|")[-1].split(":")[-1]
        target_re = r"^{joint_name}_twist{axis}_(plus|minus)[0-9]+$".format(**locals())
        attrs = cmds.listAttr(joint) or []
        for attr_name in attrs:
            if re.match(target_re, attr_name):
                target_names.append(attr_name)
    return target_names



def create_group(n="|FaceGroup|SkeletonGroup", d=False, v=None, i=None):
    """创建组"""
    if d:
        if cmds.objExists(n):
            cmds.delete(n)
    if cmds.objExists(n):
        return n
    fields = n.split("|")
    n = fields.pop(-1)
    if len(fields) > 1:
        result = cmds.group(em=True, n=n, p=create_group("|".join(fields)))
    else:
        result = cmds.group(em=True, n=n)
    if v is not None:
        cmds.setAttr(result + ".v", v)
    if i is not None:
        cmds.setAttr(result + ".inheritsTransform", i)
    return result


def get_twist_data():
    """获取扭曲数据"""
    axis = "X"
    data = []
    for joint in cmds.ls(type="joint") or []:
        if not cmds.attributeQuery("twist" + axis, node=joint, exists=True):
            continue
        twist = Twist(joint=joint)
        joint_name = joint.split("|")[-1].split(":")[-1]
        target_re = r"^{joint_name}_twist{axis}_(plus|minus)[0-9]+$".format(**locals())
        attrs = cmds.listAttr(joint) or []
        for attr_name in attrs:
            if re.match(target_re, attr_name):
                value = twist.get_value_by_target(attr_name)
                data.append(dict(
                    target_name=attr_name,
                    joint_name=joint,
                    value=value,
                ))
    return data


def set_twist_data(data):
    """设置扭曲数据"""
    for row in data:
        if not cmds.objExists(row["joint_name"]):
            continue
        joint = row["joint_name"]
        twist = Twist(joint=joint)
        if not cmds.attributeQuery(twist.twist_ctrl_scale, node=twist.ctrl, exists=True):
            cmds.setAttr(twist.ctrl + ".rx", 90)
            twist.update_twist_ctrl_scale()
            cmds.setAttr(twist.ctrl + ".rx", 0)
        twist.add_target_by_value(row["value"])


def wrap_copy_targets_twist(targets):
    """包裹复制扭曲目标"""
    polygons = get_selected_polygons()
    if not len(polygons) == 2:
        cmds.warning("please selected two polygon")
        return
    src, dst = polygons
    all_to_zero()
    cmds.refresh()
    wrap = cmds.duplicate(dst)[0]
    bs.get_orig(wrap)
    cmds.select(wrap, src)
    from maya import mel
    mel.eval('CreateWrap')
    for target in targets:
        to_target(target, 60)
        cmds.select(wrap, dst)
        edit_target(target)
        cmds.refresh()
        to_target(target, 0)
    cmds.delete(wrap)


def auto_apply(joints):
    """自动应用"""
    selected = cmds.ls(sl=1)
    twist = get_twist(joints)
    if twist is None:
        return
    target_name = twist.get_current_target()
    if target_name is None:
        if bs.is_on_duplicate_edit():
            bs.finish_duplicate_edit(to_target)
        return
    def _add_target(_target_name):
        return twist.add_current_target()
    def _set_target(_target_name):
        pass
    cmds.select(cmds.ls(selected))
    bs.auto_duplicate_edit([target_name], _add_target, _set_target)


def all_to_zero():
    axis = "X"
    for joint in cmds.ls(type="joint") or []:
        if not cmds.attributeQuery("twist" + axis, node=joint, exists=True):
            continue
        joint_name = joint.split("|")[-1].split(":")[-1]
        target_re = r"^{joint_name}_twist{axis}_(plus|minus)[0-9]+$".format(**locals())
        attrs = cmds.listAttr(joint) or []
        for attr_name in attrs:
            if re.match(target_re, attr_name):
                ctrl = find_ctrl_by_joint(joint)
                if ctrl:
                    rotate = cmds.getAttr(ctrl + ".rotate")[0]
                    if not all([abs(i) < 0.00001 for i in rotate]):
                        identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
                        cmds.xform(ctrl, m=identity, ws=False)
                        break


def esc():
    if bs.is_on_duplicate_edit():
        bs.finish_duplicate_edit(to_target)
    all_to_zero()