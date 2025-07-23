import re
import time

import pymel.core as pm
import math
from . import bs
from . import config


def find_node_by_name(name):
    nodes = pm.ls(name)
    if len(nodes) == 1:
        return nodes[0]
    return pm.displayInfo("can not find " + name)


def get_selected_polygons():
    polygons = []
    for polygon in pm.selected(type="transform"):
        shape = polygon.getShape()
        if shape is None:
            continue
        if shape.type() != "mesh":
            continue
        polygons.append(polygon)
    return polygons


def find_ctrl_by_joint(joint):
    ctrl_list = pm.ls(config.get_ctrl_names(joint.name().split("|")[-1].split(":")[-1]), type="transform")
    ctrl_list.sort(key=lambda x: len(x.name()))
    if len(ctrl_list) > 0:
        return ctrl_list[0]


def find_mirror_joint(joint):
    joints = pm.ls(config.get_rl_names(joint.name().split("|")[-1].split(":")[-1]), type="joint")
    if len(joints) != 1:
        return
    return joints[0]


class Twist(object):

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
        if self.joint.hasAttr(self.twist_ctrl_scale):
            return
        ctrl = self.find_ctrl()
        if ctrl is None:
            return
        joint_value = self.joint.attr(self.twist_name).get()
        ctrl_value = self.ctrl.attr("r"+self.axis.lower()).get()
        if abs(joint_value) < 1.0:
            return
        if abs(ctrl_value) < 1.0:
            return
        twist_scale = ctrl_value/joint_value
        self.joint.addAttr(self.twist_ctrl_scale, k=1, at="double")
        self.joint.attr(self.twist_ctrl_scale).set(twist_scale)

    def init_angle(self):
        prefix = self.joint.name() + "_X_"
        vector = [1, 0, 0]
        attr = "outputAxisX"
        if self.joint.hasAttr(self.twist_name):
            return
        rotate_matrix = pm.createNode("composeMatrix", n=prefix+"rotateMatrix")
        self.joint.rotate.connect(rotate_matrix.inputRotate)

        swing_vector = pm.createNode("pointMatrixMult", n=prefix+"swingVector")
        swing_vector.inPoint.set(vector)
        rotate_matrix.outputMatrix.connect(swing_vector.inMatrix)

        swing_angle = pm.createNode("angleBetween", n=prefix+"angleBetween")
        swing_vector.output.connect(swing_angle.vector2)
        swing_angle.vector1.set(vector)

        swing_quat = pm.createNode("eulerToQuat", n=prefix+"swingQuat")
        swing_angle.euler.connect(swing_quat.inputRotate)

        swing_inverse = pm.createNode("quatInvert", n=prefix+"swingInverse")
        swing_quat.outputQuat.connect(swing_inverse.inputQuat)

        rotate_quat = pm.createNode("decomposeMatrix", n=prefix+"rotateQuat")
        rotate_matrix.outputMatrix.connect(rotate_quat.inputMatrix)

        twist_quat = pm.createNode("quatProd", n=prefix+"twistQuat")
        rotate_quat.outputQuat.connect(twist_quat.input1Quat)
        swing_inverse.outputQuat.connect(twist_quat.input2Quat)

        axis_angle = pm.createNode("quatToAxisAngle", n=prefix+"axisAngle")
        twist_quat.outputQuat.connect(axis_angle.inputQuat)

        angle_unit = pm.createNode("unitConversion", n=prefix + "angleUnit")
        angle_unit.conversionFactor.set(180 / math.pi)
        axis_angle.outputAngle.connect(angle_unit.input)

        multiply = pm.createNode("multiplyDivide", n=prefix+"multiply")
        angle_unit.output.connect(multiply.input1X)
        multiply.input2X.set(-1)

        condition = pm.createNode("condition", n=prefix + "condition")
        axis_angle.attr(attr).connect(condition.firstTerm)
        condition.operation.set(2)
        angle_unit.output.connect(condition.colorIfTrueR)
        multiply.outputX.connect(condition.colorIfFalseR)
        self.joint.addAttr(self.twist_name, k=1, at="double", min=0, max=1)
        condition.outColorR.connect(self.joint.attr(self.twist_name ))

    def value_to_target_name(self, value):
        if abs(value) < 1:
            return
        joint_name = self.joint.name().split("|")[-1].split(":")[-1]
        abs_value = abs(int(round(value)))
        name = "{joint_name}_{self.twist_name}_{plus_minus}{abs_value}"
        if value > 0:
            plus_minus = "plus"
        else:
            plus_minus = "minus"
        name = name.format(**locals())
        return name

    def add_current_target(self):
        self.add_target_by_value(self.joint.attr(self.twist_name).get())
        if not self.joint.hasAttr("twistCtrlScale"):
            self.update_twist_ctrl_scale()

    def add_target_by_value(self, value):
        target_name = self.value_to_target_name(value)
        if not self.joint.hasAttr(target_name):
            values = self.get_values()
            values.append(value)
            self.update_values(values)
        return target_name

    def edit_target(self, target_name):
        if not self.joint.hasAttr(target_name):
            return
        if abs(self.joint.attr(target_name).get() - 1) > 0.01:
            return
        polygons = get_selected_polygons()
        src, dst = polygons
        bs.bridge_connect_edit(self.joint.attr(target_name), src, dst)

    def update_values(self, values):
        sort_values = sorted(values+[-180.0, 0, 180.0])
        for value in values:
            if value in [-180.0, 0, 180.0]:
                continue
            name = self.value_to_target_name(value)
            if not self.joint.hasAttr(name):
                self.joint.addAttr(name, k=1, at="double", min=0, max=1)
            i = sort_values.index(value)
            pm.delete(self.joint.attr(name).inputs())
            cd = self.joint.attr(self.twist_name)
            attr = self.joint.attr(name)
            pm.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i-1], v=0, itt="linear", ott="linear")
            pm.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i], v=1, itt="linear", ott="linear")
            pm.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i+1], v=0, itt="linear", ott="linear")
            if sort_values[i-1] == -180.0:
                pm.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i - 1], v=1, itt="linear", ott="linear")
            if sort_values[i + 1] == 180.0:
                pm.setDrivenKeyframe(attr, cd=cd, dv=sort_values[i + 1], v=1, itt="linear", ott="linear")

    def get_value_by_target(self, target_name):
        if not self.joint.hasAttr(target_name):
            return
        uu = self.joint.attr(target_name).inputs(type="animCurveUU")
        if len(uu) != 1:
            return
        uu = uu[0]
        value = pm.keyframe(uu, floatChange=1, q=1, index=1)[0]
        return value

    def get_values(self):
        values = []
        joint_name = self.joint.name().split("|")[-1].split(":")[-1]
        prefix = "{joint_name}_{self.twist_name}_".format(**locals())
        for attr in self.joint.listAttr(ud=1):
            target_name = attr.name().split(".")[-1]
            if not target_name.startswith(prefix):
                continue
            value = self.get_value_by_target(target_name)
            if value is None:
                continue
            values.append(value)
        return values

    def delete_targets(self, targets):
        for target_name in targets:
            for bs_node in self.joint.attr(target_name).outputs(type="blendShape"):
                bs.delete_target(bs_node.attr(target_name))
            pm.delete(self.joint.attr(target_name).inputs())
            pm.deleteAttr(self.joint.attr(target_name))
        self.update_values(self.get_values())

    def to_target(self, target_name, ib):
        if self.find_ctrl() is None:
            return
        if not self.joint.hasAttr(target_name):
            return
        uu = self.joint.attr(target_name).inputs(type="animCurveUU")
        if len(uu) != 1:
            return
        uu = uu[0]
        value = pm.keyframe(uu, floatChange=1, q=1, index=1)[0]
        scale = 1.0
        if self.joint.hasAttr(self.twist_ctrl_scale):
            scale = self.joint.attr(self.twist_ctrl_scale).get()
        real_value = value * ib / 60.0 * scale
        self.ctrl.r.set(0, 0, 0)
        self.ctrl.attr("r"+self.axis.lower()).set(real_value)

    def mirror_target(self, target_names, polygons):
        names = []
        mirror_joint = find_mirror_joint(self.joint)
        if mirror_joint is None:
            return names
        mirror = Twist(joint=mirror_joint)
        for target_name in target_names:
            value = self.get_value_by_target(target_name)
            if value is None:
                return
            mirror_target_name = mirror.add_target_by_value(value)
            names.append([target_name, mirror_target_name])
            for polygon in polygons:
                bs.bridge_connect(mirror.joint.attr(mirror_target_name), polygon)
        if mirror.joint.hasAttr(mirror.twist_ctrl_scale):
            return names
        if not self.joint.hasAttr(self.twist_ctrl_scale):
            return names
        mirror.joint.addAttr(mirror.twist_ctrl_scale, k=1, at="double")
        mirror.joint.attr(mirror.twist_ctrl_scale).set(self.joint.attr(self.twist_ctrl_scale).get())
        return names


def get_joints_by_joint_query(joint_query):
    ls_field = [field for field in joint_query.split(",") if field]
    if len(ls_field) == 0:
        return []
    return pm.ls(ls_field, type="joint")


def add_target(joint_query, ctrl=None):
    if not pm.pluginInfo("matrixNodes", q=1, l=1):
        pm.loadPlugin("matrixNodes")
    if not pm.pluginInfo("quatNodes", q=1, l=1):
        pm.loadPlugin("quatNodes")
    joints = get_joints_by_joint_query(joint_query)
    has_rotate_joints = []
    for joint in joints:
        rotate = sum([abs(xyz) for xyz in joint.r.get()])
        if rotate > 0.00001:
            has_rotate_joints.append(joint)
    if len(has_rotate_joints) != 1:
        return pm.warning("please load one rotate joint")
    joint = has_rotate_joints[0]
    if ctrl is not None:
        ctrl = find_node_by_name(ctrl)
    twist = Twist(joint=joint, ctrl=ctrl)
    twist.add_current_target()


def get_joint_by_target(target):
    if not target:
        return
    match = re.match(r"^(?P<joint>\w+)_twistX_(plus|minus)[0-9]{1,3}$", target)
    if not match:
        return
    joint_name = match.groupdict()["joint"]
    return find_node_by_name(joint_name)


def edit_target(target_name):
    joint = get_joint_by_target(target_name)
    if joint is None:
        return
    Twist(joint=joint).edit_target(target_name)


def to_target(target_name, ib):
    joint = get_joint_by_target(target_name)
    if joint is None:
        return
    Twist(joint=joint).to_target(target_name, ib)


def del_targets(target_names):
    for target_name in target_names:
        joint = get_joint_by_target(target_name)
        if joint is None:
            return
        Twist(joint=joint).delete_targets([target_name])


def mirror_targets(target_names):
    polygons = get_selected_polygons()
    joint_targets = {}
    for target_name in target_names:
        joint = get_joint_by_target(target_name)
        if joint is None:
            continue
        joint_targets.setdefault(joint, []).append(target_name)
    target_mirrors = []
    for joint, target_names in joint_targets.items():
        target_mirrors += Twist(joint=joint).mirror_target(target_names, polygons)
    for polygon in polygons:
        bs.mirror_targets(polygon, target_mirrors)


def get_targets():
    axis = "X"
    target_names = []
    for joint in pm.ls(type="joint"):
        if not joint.hasAttr("twist"+axis):
            continue
        joint_name = joint.name().split("|")[-1].split(":")[-1]
        target_re = r"^{joint_name}_twist{axis}_(plus|minus)[0-9]+$".format(**locals())
        for attr in joint.listAttr():
            target_name = attr.name().split(".")[-1]
            if re.match(target_re, target_name):
                target_names.append(target_name)
    return target_names


def create_group(n="|FaceGroup|SkeletonGroup", d=False, v=None, i=None):
    if d:
        if pm.objExists(n):
            pm.delete(n)
    if pm.objExists(n):
        return pm.PyNode(n)
    fields = n.split("|")
    n = fields.pop(-1)
    if len(fields) > 1:
        result = pm.group(em=1, n=n, p=create_group("|".join(fields)))
    else:
        result = pm.group(em=1, n=n)
    if v is not None:
        result.v.set(v)
    if i is not None:
        result.inheritsTransform.set(i)
    return result


def dup_target(target_name, polygons):
    create_group("|adPoses").v.set(1)
    group = create_group("|adPoses|edit_" + target_name, d=True, v=True)
    for polygon in polygons:
        polygon.v.set(0)
        dup = polygon.duplicate()[0]
        for shape in dup.getShapes():
            if shape.io.get():
                pm.delete(shape)
        dup.setParent(group)
        dup.rename(target_name+"_"+polygon.name().split("|")[-1])
        dup.v.set(1)
        for shape in dup.getShapes():
            shape.overrideEnabled.set(True)
            shape.overrideColor.set(13)
    panels = pm.getPanel(all=True)
    for panel in panels:
        if pm.modelPanel(panel, ex=1):
            pm.modelEditor(panel, e=1, wireframeOnShaded=True)
    pm.select(cl=1)


def auto_dup(target_name):
    polygons = get_selected_polygons()
    if len(polygons) == 0:
        return
    dup_target(target_name, polygons)


def edit_by_duplicate(duplicate, attr, edit=True):
    target_name = attr.name().split(".")[-1]
    src_polygons = bs.get_name_polygon_by_short_name(bs.get_child_polygons(duplicate))
    src_polygons = {k[len(target_name)+1:]: v for k, v in src_polygons.items()}
    dst_polygons = bs.get_name_polygon_by_short_name(pm.ls(src_polygons.keys()))
    for src, dst in bs.get_polygon_matrix_by_map([src_polygons, dst_polygons]):
        dst.v.set(True)
        if edit:
            bs.bridge_connect_edit(attr, src, dst)

    duplicate.v.set(0)
    duplicate.getParent().v.set(0)
    pm.select(cl=True)


def auto_edit():
    group = create_group("|adPoses")
    for duplicate in group.listRelatives():
        if not duplicate.v.get():
            continue
        target_name = duplicate.name()
        if target_name[:5] != "edit_":
            continue
        target_name = target_name[5:]
        joint = get_joint_by_target(target_name)
        edit_by_duplicate(duplicate, joint.attr(target_name), True)


def auto_apply_old(target_name):
    selected = pm.selected()
    if not pm.objExists("|adPoses"):
        create_group("|adPoses").v.set(0)
        pm.select(selected)
    group = create_group("|adPoses")
    if group.v.get():
        return auto_edit()
    else:
        return auto_dup(target_name)


def auto_apply(target_name):
    from . import bsv2
    joint = get_joint_by_target(target_name)
    bsv2.auto_duplicate_edit([joint.attr(target_name).name()], lambda x: to_target(x, 60))


def get_twist_data():
    axis = "X"
    data = []
    for joint in pm.ls(type="joint"):
        if not joint.hasAttr("twist"+axis):
            continue
        twist = Twist(joint=joint)
        joint_name = joint.name().split("|")[-1].split(":")[-1]
        target_re = r"^{joint_name}_twist{axis}_(plus|minus)[0-9]+$".format(**locals())
        for attr in joint.listAttr():
            target_name = attr.name().split(".")[-1]
            if re.match(target_re, target_name):
                joint_name = joint.name()
                value = twist.get_value_by_target(target_name)
                data.append(dict(
                    target_name=target_name,
                    joint_name=joint_name,
                    value=value,
                ))
    return data


current_time = None


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


def set_twist_data(data, polygons):
    blend_shapes = get_blend_shapes(polygons)
    for row in data:
        if not pm.objExists(row["joint_name"]):
            continue
        joint = pm.PyNode(row["joint_name"])
        twist = Twist(joint=joint)
        if not twist.ctrl.hasAttr(twist.twist_ctrl_scale):
            twist.ctrl.rx.set(90)
            twist.update_twist_ctrl_scale()
            twist.ctrl.rx.set(0)
        twist.add_target_by_value(row["value"])
        connect_all_bs(joint.attr(row["target_name"]), blend_shapes)


def wrap_copy_targets_twist(targets):
    polygons = get_selected_polygons()
    if not len(polygons) == 2:
        return pm.warning("please selected two polygon")
    targets = [t for t in targets if "_COMB_" not in t]+[t for t in targets if "_COMB_" in t]
    src, dst = polygons
    for target in targets:
        to_target(target, 0)
    pm.refresh()
    wrap = dst.duplicate()[0]
    bs.get_orig(wrap)
    pm.select(wrap, src)
    pm.mel.CreateWrap()
    for target in targets:
        to_target(target, 60)
        pm.select(wrap, dst)
        edit_target(target)
        pm.refresh()
    for target in targets:
        to_target(target,0)
    pm.delete(wrap)


def custom_mirror(target_names):
    if len(target_names) != 2:
        return
    polygons = get_selected_polygons()
    driver = pm.ls("*|Planes|Driver", type="transform")
    if len(driver) == 1:
        polygons.append(driver[0])
    target_mirrors = [target_names]
    for polygon in polygons:
        _bs = bs.get_bs(polygon)
        for src, dst in target_mirrors:
            if not _bs.hasAttr(src):
                continue
            joint = get_joint_by_target(dst)
            if _bs.hasAttr(dst):
                if joint.attr(dst).isConnectedTo(_bs.attr(dst)):
                    continue
                else:
                    bs.delete_target(_bs.attr(dst))
            bs.bridge_connect(joint.attr(dst), polygon)
        bs.mirror_targets(polygon, target_mirrors)
