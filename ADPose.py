# coding:utf-8
import math
import re
from functools import wraps
from maya import cmds
from . import bs
from . import config
from maya.api.OpenMaya import *


def undo_chunk(func):
    """装饰器：将整个操作包在一个 undo chunk 中，支持完整 Ctrl+Z"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(openChunk=True, chunkName=func.__name__)
        try:
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrapper



def create_group(n="|FaceGroup|SkeletonGroup", d=False, v=None, i=None):
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


def free_joints():
    polygons = get_selected_polygons()
    skins = []
    for polygon in polygons:
        for node in cmds.listHistory(polygon) or []:
            if cmds.nodeType(node) == "skinCluster" and node not in skins:
                skins.append(node)
    joints = []
    for skin in skins:
        for joint in cmds.skinCluster(skin, q=True, inf=True) or []:
            if joint not in joints:
                joints.append(joint)
    has_rotate_joints = []
    for joint in joints:
        rotate = cmds.getAttr(joint + ".r")[0]
        rotate_sum = sum([abs(xyz) for xyz in rotate])
        if rotate_sum > 0.00001:
            has_rotate_joints.append(joint)
    for joint in has_rotate_joints:
        matrix = cmds.xform(joint, q=True, m=True, ws=False)
        trans = MTransformationMatrix(MMatrix(matrix))
        rotate = trans.rotation()
        cmds.setAttr(joint + ".jointOrient", rotate[0]/math.pi*180.0, rotate[1]/math.pi*180.0, rotate[2]/math.pi*180.0)


def find_node_by_name(name):
    nodes = cmds.ls(name) or []
    if len(nodes) == 1:
        return nodes[0]
    return None


def find_reference_node_by_name(name):
    node = find_node_by_name(name)
    if node is None:
        return None
    if cmds.referenceQuery(node, isNodeReferenced=True):
        return find_node_by_name(name+"_reference")
    return node


def get_reference_node_name(node):
    node_name = node if isinstance(node, str) else node
    if node_name.endswith("_reference"):
        re_name = node_name[:-10]
        if cmds.objExists(node_name):
            return re_name
    return node_name


def comb_target_to_targets(targets):
    new_targets = []
    for target in targets:
        if target[-5:-2] == "_IB":
            target = target[:-5]
        new_targets.append(target)
    return list(set([target for comb in new_targets for target in comb.split("_COMB_") if target]))


def get_selected_polygons():
    polygons = []
    for polygon in cmds.ls(sl=True, type="transform") or []:
        shapes = cmds.listRelatives(polygon, s=True, ni=True) or []
        if not shapes:
            continue
        if cmds.nodeType(shapes[0]) != "mesh":
            continue
        polygons.append(polygon)
    return polygons


# 会话级缓存：避免 find_ctrl_by_joint 在全场景扫描时重复执行 cmds.ls
_ctrl_cache = {}

def find_ctrl_by_joint(joint):
    joint_name = joint if isinstance(joint, str) else joint
    if joint_name in _ctrl_cache:
        return _ctrl_cache[joint_name]
    if "Part" in joint_name:
        _ctrl_cache[joint_name] = None
        return None
    short_name = joint_name.split("|")[-1].split(":")[-1]
    ctrl_list = cmds.ls(config.get_ctrl_names(short_name), type="transform") or []
    if len(ctrl_list) == 1:
        _ctrl_cache[joint_name] = ctrl_list[0]
        return ctrl_list[0]
    _ctrl_cache[joint_name] = None
    return None


def clear_ctrl_cache():
    """清除控制器查找缓存（场景切换/引用变更后调用）"""
    _ctrl_cache.clear()


def find_mirror_joint(joint):
    joint_name = joint if isinstance(joint, str) else joint
    short_name = joint_name.split("|")[-1].split(":")[-1]
    joints = cmds.ls(config.get_rl_names(short_name), type="joint") or []
    if len(joints) != 1:
        return None
    return joints[0]


def create_node(typ, n):
    if cmds.objExists(n):
        # 引用节点不能删除，改用别名
        if cmds.referenceQuery(n, isNodeReferenced=True) if cmds.objExists(n) else False:
            return create_node(typ, n + "_reference")
        cmds.delete(n)
    return cmds.createNode(typ, n=n)


def pose_to_matrix(pose):
    angle, direction = float(pose[0]), float(pose[1])
    sin = math.sin(math.pi * direction / 180)
    cos = math.cos(math.pi * direction / 180)
    data = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, cos, sin, 0.0],
        [0.0, -sin, cos, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ]
    direction_matrix = MMatrix(data)
    sin = math.sin(math.pi * angle / 180)
    cos = math.cos(math.pi * angle / 180)
    data = [
        [cos, sin, 0, 0.0],
        [-sin, cos, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ]
    angle_matrix = MMatrix(data)
    matrix = direction_matrix.inverse() * angle_matrix * direction_matrix
    return list(matrix)


def direction_distance(first, second):
    """Return the shortest distance between two directions in degrees."""
    return abs((float(first) - float(second) + 180.0) % 360.0 - 180.0)


def interpolate_pose_matrix(matrix, weight):
    """Interpolate an object-space pose matrix from the identity transform."""
    target = MTransformationMatrix(MMatrix(matrix))
    result = MTransformationMatrix()
    rotation = MQuaternion.slerp(
        MQuaternion(), target.rotation(asQuaternion=True), float(weight)
    )
    result.setRotation(rotation)
    result.setTranslation(
        target.translation(MSpace.kTransform) * float(weight), MSpace.kTransform
    )
    scale = target.scale(MSpace.kTransform)
    result.setScale(
        tuple(1.0 + (value - 1.0) * float(weight) for value in scale),
        MSpace.kTransform,
    )
    shear = target.shear(MSpace.kTransform)
    result.setShear(
        tuple(value * float(weight) for value in shear), MSpace.kTransform
    )
    return list(result.asMatrix())


def break_delete(nodes):
    for node in nodes:
        # 获取输入连接并断开
        connections = cmds.listConnections(node, c=True, p=True, d=False, s=True) or []
        for i in range(0, len(connections), 2):
            dst = connections[i]
            src = connections[i+1]
            if cmds.isConnected(src, dst):
                cmds.disconnectAttr(src, dst)
    cmds.delete(nodes)


def update_sdk(node, dvs, cd, name, keep):
    name = name.replace("-", "m")
    if cmds.attributeQuery(name, node=node, exists=True):
        if keep:
            return node + "." + name
    else:
        cmds.addAttr(node, ln=name, k=0, at="double", min=0, max=1)
    # 删除输入的 animCurveUU 节点
    inputs = cmds.listConnections(node + "." + name, type="animCurveUU", d=False, s=True) or []
    if inputs:
        break_delete(inputs)
    for dv, v in dvs:
        cmds.setDrivenKeyframe(node + "." + name, cd=cd, dv=dv, v=v, itt="linear", ott="linear")
    return node + "." + name


def get_sorted_poses(poses):
    direction_angles = {}
    for angle, direction in poses:
        direction_angles.setdefault(direction, []).append(angle)
    for direction, angles in direction_angles.items():
        direction_angles[direction] = list(sorted(angles))
    directions = list(sorted(list(direction_angles.keys())))
    poses = []
    for direction in directions:
        for angle in direction_angles[direction]:
            poses.append(tuple([angle, direction]))
    return poses


import re

def target_is_pose(target_name):
    return "_COMB_" not in target_name and "_GRID_" not in target_name


def target_is_comb(target_name):
    return "_COMB_" in target_name and not re.search(r"_IB\d+$", target_name)


def target_is_ib(target_name):
    return "_COMB_" in target_name and bool(re.search(r"_IB\d+$", target_name))


def target_is_grid(target_name):
    return "_GRID_" in target_name and bool(re.search(r"_IB\d+$", target_name))


def dup_target(target_name, polygons):
    group = create_group("|adPoses")
    cmds.setAttr(group + ".v", 1)
    edit_group = create_group("|adPoses|edit_" + target_name, d=True, v=True)
    dup_polygons = []
    for polygon in polygons:
        cmds.setAttr(polygon + ".v", 0)
        shapes = cmds.listRelatives(polygon, s=True, ni=True) or []
        if shapes:
            cmds.setAttr(shapes[0] + ".v", 1)
        dup = cmds.duplicate(polygon)[0]
        # 删除中间形状
        for shape in cmds.listRelatives(dup, s=True, f=True) or []:
            if cmds.getAttr(shape + ".io"):
                cmds.delete(shape)
        cmds.parent(dup, edit_group)
        short_name = polygon.split("|")[-1]
        dup = cmds.rename(dup, target_name + "_" + short_name)
        cmds.setAttr(dup + ".v", 1)
        for shape in cmds.listRelatives(dup, s=True, f=True) or []:
            cmds.setAttr(shape + ".overrideEnabled", True)
            cmds.setAttr(shape + ".overrideColor", 13)
        dup_polygons.append(dup)
    panels = cmds.getPanel(all=True) or []
    for panel in panels:
        if cmds.modelPanel(panel, ex=1):
            try:
                cmds.modelEditor(panel, e=1, wireframeOnShaded=True)
            except RuntimeError:
                pass
    cmds.select(cl=1)
    return dup_polygons


class ADPoses(object):

    # get install
    @classmethod
    def load_by_name(cls, name):
        joint = find_node_by_name(name)
        if joint is None:
            return None
        control = find_ctrl_by_joint(joint)
        if control is None:
            return None
        return cls(joint, control)

    @classmethod
    def get_targets(cls):
        ad_poses = []
        for joint in cmds.ls(type="joint") or []:
            if not cmds.attributeQuery("angle", node=joint, exists=True):
                continue
            ctrl = find_ctrl_by_joint(joint)
            if ctrl is None:
                continue
            ad_poses.append(cls(joint, ctrl))

        targets = []
        for ad in ad_poses:
            for pose in ad.get_poses():
                target_name = ad.target_name(pose)
                targets.append(target_name)
                comb_name = "COMB_" + target_name
                if not cmds.attributeQuery(comb_name, node=ad.reference, exists=True):
                    continue
                for node in cmds.listConnections(ad.reference + "." + comb_name, type="combinationShape") or []:
                    if target_name not in node:
                        continue
                    for attr in cmds.listAttr(node, ud=1) or []:
                        comb_target_name = attr.split(".")[-1]
                        if comb_target_name in targets:
                            continue
                        targets.append(comb_target_name)
                for curve in cmds.listConnections(ad.reference + "." + comb_name, type="animCurveUU") or []:
                    for node in cmds.listConnections(curve, type="combinationShape") or []:
                        if target_name not in node:
                            continue
                        for attr in cmds.listAttr(node, ud=1) or []:
                            grid_target_name = attr.split(".")[-1]
                            if grid_target_name in targets:
                                continue
                            targets.append(grid_target_name)
        return targets

    @classmethod
    def get_target_driver_attr(cls, target):
        """Return the read-only driver plug for a displayed target."""
        attr = None
        if target_is_grid(target):
            node = find_reference_node_by_name(target)
            if node:
                attr = node + "." + target
        elif target_is_ib(target):
            node = find_reference_node_by_name(target[:-5])
            if node:
                attr = node + "." + target
        elif target_is_comb(target):
            node = find_reference_node_by_name(target)
            if node:
                attr = node + "." + target
        elif target_is_pose(target):
            matches = cls.targets_to_ad_poses([target])
            if len(matches) == 1:
                ad, poses = matches[0]
                if len(poses) == 1:
                    attr = ad.reference + "." + target
        return attr if attr and cmds.objExists(attr) else None

    @classmethod
    def get_target_driver_values(cls, targets):
        values = {target: 0.0 for target in targets}
        for target in targets:
            attr = cls.get_target_driver_attr(target)
            if attr:
                values[target] = cmds.getAttr(attr)
        return values

    # get info by targets
    @classmethod
    def targets_to_ad_poses(cls, targets):
        data = {}
        for target in targets:
            match = re.match("(.+)_a([0-9]{1,3})_d([0-9]{1,3})", target)
            if match is None:
                continue
            joint_name, angle, direction = match.groups()
            angle, direction = int(angle), int(direction)
            data.setdefault(joint_name, []).append((angle, direction))
        ad_poses = []
        for joint_name, poses in data.items():
            joint = find_node_by_name(joint_name)
            if joint is None:
                continue
            ctrl = find_ctrl_by_joint(joint)
            if ctrl is None:
                continue
            ad = cls(joint, ctrl)
            ad_poses.append([ad, poses])
        return ad_poses

    @classmethod
    def target_to_ad_pose(cls, target):
        ad, poses = cls.targets_to_ad_poses([target])[0]
        return ad, poses[0]

    @classmethod
    def target_to_comb_ib(cls, target):
        comb_node = find_reference_node_by_name(target[:-5])
        ib = int(target[-2:])
        return comb_node, ib

    @classmethod
    def target_to_combs(cls, target):
        return [[ad, poses[0]] for ad, poses in cls.targets_to_ad_poses(target.split("_COMB_"))]

    # get target name
    def target_name(self, pose):
        angle, direction = pose
        return "{self.prefix}_a{angle}_d{direction}".format(self=self, angle=angle, direction=direction)

    def pose_matrix_name(self, pose):
        return self.target_name(pose) + "_poseMatrix"

    def get_saved_pose_matrix(self, pose):
        name = self.pose_matrix_name(pose)
        if not cmds.attributeQuery(name, node=self.reference, exists=True):
            return None
        return cmds.getAttr(self.reference + "." + name)

    def direction_is_mirrored(self):
        name = "adposeDirectionMirror"
        return (
            cmds.attributeQuery(name, node=self.reference, exists=True) and
            bool(cmds.getAttr(self.reference + "." + name))
        )

    def set_direction_mirrored(self):
        """Normalize a mirrored joint's direction to its opposite-side convention."""
        name = "adposeDirectionMirror"
        if self.direction_is_mirrored():
            return
        selection = cmds.ls(selection=True, long=True) or []
        try:
            if not cmds.attributeQuery(name, node=self.reference, exists=True):
                cmds.addAttr(self.reference, ln=name, at="bool", dv=True)
            cmds.setAttr(self.reference + "." + name, True)
            self.delete_old_angle_network()
            self.update_angle_direction()
        finally:
            if selection:
                cmds.select(selection, replace=True)
            else:
                cmds.select(clear=True)

    def detect_mirrored_direction(self, source_direction, control_matrix):
        """Detect whether the same local pose uses the opposite direction convention."""
        self.update_angle_direction()
        previous = cmds.xform(
            self.control, query=True, matrix=True, objectSpace=True
        )
        try:
            cmds.xform(
                self.control, matrix=control_matrix, objectSpace=True
            )
            observed = cmds.getAttr(self.reference + ".direction")
        finally:
            cmds.xform(
                self.control, matrix=previous, objectSpace=True
            )

        if self.direction_is_mirrored():
            observed = (360.0 - observed) % 360.0
        direct_error = direction_distance(observed, source_direction)
        inverse_error = direction_distance(
            (360.0 - observed) % 360.0, source_direction
        )
        if inverse_error <= 1.0 and inverse_error + 0.001 < direct_error:
            self.set_direction_mirrored()

    @staticmethod
    def comb_name(combs):
        return "_COMB_".join(sorted([ad.target_name(pose) for ad, pose in combs]))

    @classmethod
    def ib_name(cls, comb_name, ib):
        return comb_name + "_IB%02d" % ib

    # set ctrl
    def set_pose(self, pose):
        angle, direction = pose
        if cmds.attributeQuery("angle_direction_scale", node=self.joint, exists=True):
            angle *= cmds.getAttr(self.joint + ".angle_direction_scale")
        matrix = pose_to_matrix([angle, direction])
        cmds.xform(self.control, m=matrix, ws=False)
        joint_pose = self.get_control_pose(init=False, int_round=False)
        if abs(pose[0] - joint_pose[0]) > 0.0001 or abs(pose[1] - joint_pose[1]) > 0.0001:
            if cmds.attributeQuery("angle_direction_scale", node=self.joint, exists=True):
                return
            if abs(joint_pose[0]) < 0.0001:
                return
            scale = pose[0] / joint_pose[0]
            angle *= scale
            matrix = pose_to_matrix([angle, direction])
            cmds.xform(self.control, m=matrix, ws=False)
            joint_pose = self.get_control_pose(init=False, int_round=False)
            if abs(pose[0] - joint_pose[0]) > 0.0001 or abs(pose[1] - joint_pose[1]) > 0.0001:
                return
            cmds.addAttr(self.joint, ln="angle_direction_scale", at="double", k=1)
            cmds.setAttr(self.joint + ".angle_direction_scale", scale)

    def to_zero(self):
        rotate = cmds.getAttr(self.control + ".rotate")[0]
        if not all([abs(i) < 0.00001 for i in rotate]):
            identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
            cmds.xform(self.control, m=identity, ws=False)

    @classmethod
    def all_to_zero(cls):
        # ★ 性能优化：直接查有 angle 属性的骨骼，避免遍历全场景 971 根
        angle_plugs = cmds.ls("*.angle", objectsOnly=True, type="joint") or []
        for joint in angle_plugs:
            ctrl = find_ctrl_by_joint(joint)
            if ctrl is None:
                continue
            rotate = cmds.getAttr(ctrl + ".rotate")[0]
            if not all([abs(i) < 0.00001 for i in rotate]):
                identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
                cmds.xform(ctrl, m=identity, ws=False)

    @classmethod
    def set_pose_by_targets(cls, pose_targets, all_targets=None, ib=60):
        if all_targets is None:
            cls.all_to_zero()
        for target in pose_targets:
            if target_is_pose(target):
                cls.set_pose_by_target(target, ib)
            elif target_is_comb(target):
                cls.set_comb_pose_by_target(target, ib)
            elif target_is_ib(target):
                cls.set_ib_pose_by_target(target, ib)
            elif target_is_grid(target):
                cls.set_grid_pose_by_target(target, ib)

    @staticmethod
    def ib_target_split(ib_target, ib=60):
        ib = int(round(float(ib) * float(ib_target[-2:]) / 60))
        target = ib_target[:-5]
        return target, ib

    @classmethod
    def set_grid_pose_by_target(cls, target, ib):
        for ib_target in target.split("_GRID_"):
            cls.set_pose_by_target(*cls.ib_target_split(ib_target, ib))

    @classmethod
    def set_ib_pose_by_target(cls, target, ib):
        cls.set_comb_pose_by_target(*cls.ib_target_split(target, ib))

    @classmethod
    def set_comb_pose_by_target(cls, target, ib):
        for target_name in target.split("_COMB_"):
            cls.set_pose_by_target(target_name, ib)

    @classmethod
    def set_pose_by_target(cls, target, ib=60):
        ad, (angle, direction) = cls.target_to_ad_pose(target)
        saved_matrix = ad.get_saved_pose_matrix((angle, direction))
        if saved_matrix is not None:
            matrix = saved_matrix
            if ib != 60:
                matrix = interpolate_pose_matrix(saved_matrix, float(ib) / 60.0)
            cmds.xform(ad.control, matrix=matrix, objectSpace=True)
            return
        angle = float(angle) * ib / 60.0
        ad.set_pose((angle, direction))

    # add
    def add_comb(self, pose):
        comb_name = "COMB_" + self.target_name(pose)
        if not cmds.attributeQuery(comb_name, node=self.reference, exists=True):
            cmds.addAttr(self.reference, ln=comb_name, k=1, at="double", min=0, max=1)
        angle, direction = pose
        direction_attr = self.reference + ".direction_%i" % direction
        dvs = [[0, 0], [pose[0], 1], [180, 1]]
        angle_attr = self.update_sdk(dvs, self.reference + ".angle", "angle_%i_%i_%i" % (dvs[0][0], dvs[1][0], dvs[2][0]), True)
        bw = create_node("blendWeighted", n=self.prefix+comb_name)
        cmds.connectAttr(angle_attr, bw + ".input[0]", f=True)
        cmds.connectAttr(direction_attr, bw + ".weight[0]", f=True)
        cmds.connectAttr(bw + ".output", self.reference + "." + comb_name, f=1)

    def repair_comb(self):
        for attr in cmds.listAttr(self.reference, ud=1) or []:
            attr_name = attr.split(".")[-1]
            if not attr_name.startswith("COMB_"+self.prefix):
                continue

            target_name = attr_name[5:]
            _, pose = self.target_to_ad_pose(target_name)
            angle, direction = pose
            direction_attr = self.reference + ".direction_%i" % direction
            dvs = [[0, 0], [pose[0], 1], [180, 1]]
            angle_attr = self.update_sdk(dvs, self.reference + ".angle",
                                         "angle_%i_%i_%i" % (dvs[0][0], dvs[1][0], dvs[2][0]), True)
            comb_name = "COMB_" + self.target_name(pose)
            bw = find_reference_node_by_name(self.prefix+comb_name)
            if bw and not cmds.isConnected(angle_attr, bw + ".input[0]"):
                cmds.connectAttr(angle_attr, bw + ".input[0]", f=1)
            if bw and not cmds.isConnected(direction_attr, bw + ".weight[0]"):
                cmds.connectAttr(direction_attr, bw + ".weight[0]", f=1)

    @classmethod
    def add_combs(cls, comb_poses):
        comb_name = cls.comb_name(comb_poses)
        node = find_reference_node_by_name(comb_name)
        if node:
            if cmds.attributeQuery(comb_name, node=node, exists=True):
                inputs = cmds.listConnections(node, type="transform", p=1, d=False, s=True) or []
                if inputs:
                    return node + "." + comb_name
            cmds.delete(cmds.ls(node, type="combinationShape") or [])
        comb = create_node("combinationShape", comb_name)
        cmds.setAttr(comb + ".combinationMethod", 1)
        for i, (ad, pose) in enumerate(comb_poses):
            ad.add_comb(pose)
            cmds.connectAttr(ad.reference + ".COMB_" + ad.target_name(pose), comb + ".inputWeight[%d]" % i, f=1)
        dvs = [[0, 0], [1, 1]]
        update_sdk(comb, dvs, comb + ".outputWeight", comb_name, True)
        return comb + "." + comb_name

    @classmethod
    def add_ib(cls, comb_node, ib):
        node_name = get_reference_node_name(comb_node)
        ib_target_name = node_name + "_IB%02d" % ib
        if cmds.attributeQuery(ib_target_name, node=comb_node, exists=True):
            return comb_node + "." + ib_target_name
        if ib == 0:
            return comb_node + "." + ib_target_name
        if not cmds.attributeQuery(ib_target_name, node=comb_node, exists=True):
            cmds.addAttr(comb_node, ln=ib_target_name)
        cls.update_comb_sdk(comb_node)
        return comb_node + "." + ib_target_name

    @classmethod
    def add_grid(cls, grid_name):
        if cmds.objExists(grid_name):
            node = find_node_by_name(grid_name)
            if node and cmds.attributeQuery(grid_name, node=node, exists=True):
                return node + "." + grid_name
            else:
                cmds.delete(cmds.ls(grid_name, type="combinationShape") or [])
        comb = create_node("combinationShape", grid_name)
        for i, field in enumerate(grid_name.split("_GRID_")):
            target_name = field[:-5]
            ad, (pose, ) = cls.targets_to_ad_poses([target_name])[0]
            ad.add_comb(pose)
            driver_attr = ad.reference + ".COMB_" + ad.target_name(pose)
            v = int(field[-2:])/60.0
            dvs = [[v-0.25, 0], [v, 1], [v+0.25, 0]]
            update_sdk(comb, dvs, driver_attr, "inputWeight[%i]" % i, False)
            # 获取输入连接的属性并设置别名
            input_conns = cmds.listConnections(comb + ".inputWeight[%d]" % i, p=True, d=False, s=True) or []
            if input_conns:
                cmds.aliasAttr(field, input_conns[0])
        cmds.setAttr(comb + ".combinationMethod", 1)
        dvs = [[0, 0], [1, 1]]
        update_sdk(comb, dvs, comb + ".outputWeight", grid_name, True)
        return comb + "." + grid_name

    @classmethod
    def update_comb_sdk(cls, comb_node):
        comb_name = get_reference_node_name(comb_node)
        attr_ibs = []
        for attr in cmds.listAttr(comb_node, ud=1) or []:
            attr_name = attr.split(".")[-1]
            if attr_name == comb_name:
                ib = 60
            else:
                str_ib = attr_name[len(comb_name)+3:]
                if not str_ib.isdigit():
                    continue
                ib = int(str_ib)
            if ib == 0:
                continue
            attr_ibs.append([attr_name, ib])
        ibs = list(sorted(set([ib for _, ib in attr_ibs] + [0, 61])))
        for attr, ib in attr_ibs:
            index = ibs.index(ib)
            dvs = [[float(ibs[index + i])/60.0, v] for i, v in [[-1, 0], [0, 1], [1, 0]]]
            update_sdk(comb_node, dvs, comb_node + ".outputWeight", attr, False)

    def add_pose(self, pose, control_matrix=None):
        poses = self.get_poses()
        if pose not in poses:
            poses.append(pose)
            self.update_poses(poses)
        name = self.target_name(pose)
        if control_matrix is not None:
            matrix_name = self.pose_matrix_name(pose)
            if not cmds.attributeQuery(matrix_name, node=self.reference, exists=True):
                cmds.addAttr(self.reference, ln=matrix_name, dt="matrix")
            cmds.setAttr(self.reference + "." + matrix_name, *control_matrix, type="matrix")
        return self.reference + "." + name

    @classmethod
    def add_by_target(cls, target, control_matrix=None):
        if target_is_ib(target):
            comb, ib = cls.target_to_comb_ib(target)
            return cls.add_ib(comb, ib)
        elif target_is_comb(target):
            return cls.add_combs(cls.target_to_combs(target))
        elif target_is_grid(target):
            return cls.add_grid(target)
        elif target_is_pose(target):
            ad, pose = cls.target_to_ad_pose(target)
            return ad.add_pose(pose, control_matrix=control_matrix)

    @classmethod
    def add_by_targets(cls, target_names, polygons=None):
        for target in target_names:
            attr = cls.add_by_target(target)
            if polygons is None:
                continue
            for polygon in polygons:
                bs.bridge_connect(attr, polygon)


    # delete
    @classmethod
    def delete_comb(cls, comb_name):
        comb_node = find_reference_node_by_name(comb_name)
        if comb_node is None:
            return
        for attr in cmds.listAttr(comb_node, ud=1) or []:
            for bs_attr in cmds.listConnections(comb_node + "." + attr, type="blendShape", p=1) or []:
                bs.delete_target(bs_attr)
        joint_attrs = cmds.listConnections(comb_node, type="transform", p=1, d=False, s=True) or []
        cmds.delete(comb_node)
        for joint_attr in joint_attrs:
            if cmds.listConnections(joint_attr, type="combinationShape"):
                continue
            cmds.deleteAttr(joint_attr)

    @classmethod
    def delete_pose(cls, pose_target):
        for ad, poses in cls.targets_to_ad_poses([pose_target]):
            ad.delete_poses(poses)

    def delete_poses(self, poses):
        old_poses = self.get_poses()
        for pose in poses:
            if pose not in old_poses:
                continue
            name = self.target_name(pose)
            for bs_node in cmds.listConnections(self.reference + "." + name, type="blendShape") or []:
                if cmds.attributeQuery(name, node=bs_node, exists=True):
                    bs.delete_target(bs_node + "." + name)
            old_poses.remove(pose)
        self.update_poses(old_poses)

    @classmethod
    def delete_ib(cls, ib_name):
        if ib_name[-5:-2] != "_IB":
            return
        comb_name = ib_name[:-5]
        comb_node = find_reference_node_by_name(comb_name)
        if comb_node is None:
            return
        if not cmds.attributeQuery(ib_name, node=comb_node, exists=True):
            return
        for bs_attr in cmds.listConnections(comb_node + "." + ib_name, type="blendShape", p=1) or []:
            bs.delete_target(bs_attr)
        inputs = cmds.listConnections(comb_node + "." + ib_name, type="animCurveUU", d=False, s=True) or []
        if inputs:
            cmds.delete(inputs)
        cmds.deleteAttr(comb_node + "." + ib_name)
        cls.update_comb_sdk(comb_node)

    @staticmethod
    def split_target_names(target_names):
        type_targets = dict(
            pose=[],
            comb=[],
            ib=[]
        )
        for target_name in target_names:
            if target_is_pose(target_name):
                type_targets.setdefault("pose", []).append(target_name)
            elif target_is_comb(target_name):
                type_targets.setdefault("comb", []).append(target_name)
            elif target_is_ib(target_name):
                type_targets.setdefault("ib", []).append(target_name)
        return type_targets

    @classmethod
    @undo_chunk
    def delete_by_targets(cls, target_names):
        all_type = cls.split_target_names(cls.get_targets())
        del_type = cls.split_target_names(target_names)
        for del_base in del_type["pose"]:
            for com in all_type["comb"]:
                if del_base not in com.split("_COMB_"):
                    continue
                if com in del_type.get("comb", []):
                    continue
                del_type.setdefault("comb", []).append(com)
        for del_comb in del_type.get("comb", []):
            for ib in all_type.get("ib", []):
                if del_comb not in ib:
                    continue
                if ib in del_type.get("ib", []):
                    continue
                del_type.setdefault("ib", []).append(ib)
        for target_name in del_type.get("ib", []):
            cls.delete_ib(target_name)
        for target_name in del_type.get("comb", []):
            cls.delete_comb(target_name)
        for target_name in del_type["pose"]:
            cls.delete_pose(target_name)


    # edit
    def edit_by_selected_ctrl_pose(self):
        polygons = get_selected_polygons()
        pose = self.get_control_pose(init=False)
        attr = self.add_pose(pose)
        if not len(polygons) == 2:
            return pose
        src, dst = polygons
        bs.bridge_connect_edit(attr, src, dst)
        return pose

    @classmethod
    def edit_by_selected_target(cls, target_name):
        polygons = get_selected_polygons()
        if not len(polygons) == 2:
            return cmds.warning(u"please selected two ")
        src, dst = polygons
        attr = cls.add_by_target(target_name)
        bs.bridge_connect_edit(attr, src, dst)

    @classmethod
    def auto_edit_by_selected_target(cls, joints):
        polygons = get_selected_polygons()
        target_name = cls.get_auto_target_name(joints)
        if target_name is None:
            return
        attr = cls.add_by_target(target_name)
        if not len(polygons) == 2:
            return
        src, dst = polygons
        bs.bridge_connect_edit(attr, src, dst)
        return attr

    @classmethod
    def auto_add_target(cls, joints):
        target_name = cls.get_auto_target_name(joints)
        if target_name is None:
            return
        control_matrix = None
        if target_is_pose(target_name):
            ad, pose = cls.target_to_ad_pose(target_name)
            if not cmds.attributeQuery(ad.target_name(pose), node=ad.reference, exists=True):
                control_matrix = cmds.xform(
                    ad.control, query=True, matrix=True, objectSpace=True
                )
        cls.add_by_target(target_name, control_matrix=control_matrix)


    def get_max_pose(self):
        poses = self.get_poses()
        direction_angles = {}
        for angle, direction in poses:
            direction_angles.setdefault(direction, []).append(angle)
        max_poses = []
        for direction, angles in direction_angles.items():
            max_poses.append((max(angles), direction))
        return max_poses

    def on_pose(self):
        if not cmds.attributeQuery("angle", node=self.reference, exists=True):
            return False
        pose = self.get_control_pose(init=False)
        poses = self.get_max_pose()
        if pose in poses:
            return pose
        else:
            return False

    def comb_pose_ib(self):
        if not cmds.attributeQuery("angle", node=self.reference, exists=True):
            return None, None

        poses = self.get_poses()
        direction_angles = {}
        for angle, direction in poses:
            direction_angles.setdefault(direction, []).append(angle)
        angle, direction = self.get_control_pose(init=False)
        if direction not in direction_angles:
            return None, None
        angle = max(direction_angles[direction])
        comb_target_name = "COMB_" + self.target_name((angle, direction))
        if cmds.attributeQuery(comb_target_name, node=self.reference, exists=True):
            ib = int(round(cmds.getAttr(self.reference + "." + comb_target_name)*60.0))
            return (angle, direction), ib
        else:
            return None, None

    @staticmethod
    def get_pose_activity(ad):
        """Return a side-effect-free bone swing angle for target selection."""
        if cmds.attributeQuery("angle", node=ad.reference, exists=True):
            return cmds.getAttr(ad.reference + ".angle")
        if ad._is_opm_rig():
            parents = cmds.listRelatives(ad.joint, parent=True, fullPath=True) or []
            if (parents and cmds.objExists(ad.joint + ".bindPose") and
                    cmds.objExists(parents[0] + ".bindPose")):
                child_bind = MMatrix(cmds.getAttr(ad.joint + ".bindPose"))
                parent_bind = MMatrix(cmds.getAttr(parents[0] + ".bindPose"))
                rest_inverse = (child_bind * parent_bind.inverse()).inverse()
                local_matrix = MMatrix(cmds.getAttr(ad.joint + ".dagLocalMatrix"))
                rotation = MTransformationMatrix(rest_inverse * local_matrix).rotation(asQuaternion=True)
                twist_length = math.sqrt(rotation.x * rotation.x + rotation.w * rotation.w)
                if twist_length > 0.00000001:
                    twist = MQuaternion(
                        rotation.x / twist_length, 0.0, 0.0, rotation.w / twist_length
                    )
                    rotation = rotation * twist.inverse()
                vector = MVector(1.0, 0.0, 0.0).rotateBy(rotation)
                if vector.length() > 0.00000001:
                    cosine = max(-1.0, min(1.0, vector.x / vector.length()))
                    return math.degrees(math.acos(cosine))
        joint_rotate = cmds.getAttr(ad.joint + ".rotate")[0]
        return sum(abs(value) for value in joint_rotate)

    @staticmethod
    def get_control_activity(ad):
        """Return direct user FK activity for target routing, never for driving."""
        if cmds.listConnections(ad.control + ".offsetParentMatrix", s=True, d=False):
            return 0.0
        activity = 0.0
        for axis in "XYZ":
            attr = ad.control + ".rotate" + axis
            if cmds.listConnections(attr, s=True, d=False):
                continue
            activity += abs(cmds.getAttr(attr))
        return activity

    @classmethod
    def get_pose_target_by_ads(cls, ads, activity=None):
        activity = activity or cls.get_pose_activity
        if len(ads) > 1:
            # 首次建 target 时还没有 angle；先无副作用地选主关节，避免给 RBF 辅助关节建网络。
            ads_sorted = sorted(ads, key=activity, reverse=True)
            max_ad = ads_sorted[0]
            second_ad = ads_sorted[1]
            max_activity = activity(max_ad)
            second_activity = activity(second_ad)

            # 如果主关节旋转角度大于10度，且明显大于次关节（2倍以上），则智能过滤掉次关节
            if max_activity > 10.0 and max_activity > second_activity * 2.0:
                ad = max_ad
            else:
                print("can not find pose (multiple major joints active: {})".format([a.prefix for a in ads]))
                return None
        elif len(ads) == 1:
            ad = ads[0]
        else:
            print("can not find pose")
            return None

        pose = ad.get_control_pose(init=False)
        if pose == (0, 0):
            print("can not find pose")
            return None
        return ad.target_name(pose)

    @classmethod
    def get_comb_target_by_ads(cls, ads):
        if len(ads) <= 1:
            print("can not find comb pose")
            return None
        comb_poses = []
        for ad in ads:
            pose = ad.on_pose()
            if pose:
                comb_poses.append([ad, pose])
        if len(comb_poses) <= 1:
            print("can not find comb pose")
            return None
        return cls.comb_name(comb_poses)

    @classmethod
    def get_ib_target_by_ads(cls, ads):
        if len(ads) <= 1:
            print("can not find ib pose")
            return None
        ib_poses = dict()
        for ad in ads:
            pose, ib = ad.comb_pose_ib()
            ib_poses.setdefault(ib, []).append([ad, pose])
        if len(list(ib_poses.keys())) != 1:
            print("can not find ib pose")
            return None
        if list(ib_poses.keys())[0] is None:
            print("can not find ib pose")
            return None
        comb_poses = list(ib_poses.values())[0]
        comb_name = cls.comb_name(comb_poses)
        comb_node = find_node_by_name(comb_name)
        if comb_node is None:
            print("can not find ib pose")
            return None
        ib = list(ib_poses.keys())[0]
        return cls.ib_name(comb_name, ib)

    def get_grid_ib_name(self):
        angle, direction = self.get_control_pose(init=False, int_round=False)
        max_angles = {d: a for a, d in self.get_max_pose()}
        direction = int(round(direction))
        if direction in max_angles:
            ib = int(round(angle / max_angles[direction] * 60))
            if ib not in [30, 60, 20, 40]:
                return [None, None]
            max_target_name = self.target_name((max_angles[direction], direction))
            return max_target_name + "_IB"+str(ib)
        return None

    @classmethod
    def get_grid_target_by_ads(cls, ads):
        if len(ads) != 2:
            print("can not find grid pose")
            return None
        grid_ib_names = [ad.get_grid_ib_name() for ad in ads]
        if not all(grid_ib_names):
            print("can not find grid pose")
            return None
        grid_ib_names.sort()
        target_name = "_GRID_".join(grid_ib_names)
        return target_name


    @classmethod
    def get_auto_target_name(cls, joints):
        if joints:
            joints = cmds.ls(joints, type="joint") or []
        polygons = get_selected_polygons()
        if not joints:
            skins = []
            for polygon in polygons:
                for node in cmds.listHistory(polygon) or []:
                    if cmds.nodeType(node) == "skinCluster" and node not in skins:
                        skins.append(node)
            joints = []
            for skin in skins:
                for joint in cmds.skinCluster(skin, q=True, inf=True) or []:
                    if joint not in joints:
                        joints.append(joint)

        ads = []
        for joint in joints:
            ctrl = find_ctrl_by_joint(joint)
            if ctrl is None:
                continue
            ad = cls(joint, ctrl)
            if cls.get_pose_activity(ad) > 5.0:
                ads.append(ad)
        direct_ads = [ad for ad in ads if cls.get_control_activity(ad) > 5.0]
        active_ads = direct_ads or ads
        activity = cls.get_control_activity if direct_ads else cls.get_pose_activity

        target_name = None
        if target_name is None:
            target_name = cls.get_pose_target_by_ads(active_ads, activity)
        if target_name is None:
            target_name = cls.get_comb_target_by_ads(active_ads)
        if target_name is None:
            target_name = cls.get_ib_target_by_ads(active_ads)
        if target_name is None:
            return None
        return target_name


    @classmethod
    @undo_chunk
    def auto_apply(cls, joints):
        selected = cmds.ls(sl=1)
        target_name = cls.get_auto_target_name(joints)
        if target_name is None:
            if bs.is_on_duplicate_edit():
                bs.finish_duplicate_edit(lambda x: cls.set_pose_by_targets([x]))
            return
        control_matrix = None
        if target_is_pose(target_name):
            ad, _ = cls.target_to_ad_pose(target_name)
            control_matrix = cmds.xform(ad.control, query=True, matrix=True, objectSpace=True)

        def add_target(_target_name):
            return cls.add_by_target(_target_name, control_matrix=control_matrix)

        def set_target(_target_name):
            cls.set_pose_by_targets([_target_name], all_targets=[])

        cmds.select(cmds.ls(selected))
        bs.auto_duplicate_edit(
            [target_name], add_target, set_target, preserve_current_pose=True
        )

    @classmethod
    @undo_chunk
    def esc(cls):
        if bs.is_on_duplicate_edit():
            bs.finish_duplicate_edit(lambda x: cls.set_pose_by_targets([x]))
        cls.all_to_zero()

    @staticmethod
    def targets_to_mirror(targets):
        targets = [t for t in targets if "_COMB_" not in t]+[t for t in targets if "_COMB_" in t]
        joints = []
        for target in targets:
            for field in re.split("_COMB_|_IB[0-9]{2}", target):
                pattern = re.match("^(.+)_a([0-9]{1,3})_d([0-9]{1,3})$", field)
                if pattern is None:
                    continue
                joint, _, _ = pattern.groups()
                if joint not in joints:
                    joints.append(joint)

        replace_joints = []
        for joint_name in joints:
            joint = find_node_by_name(joint_name)
            if joint is None:
                continue
            mirror_joints = cmds.ls(config.get_rl_names(joint_name), type="joint") or []
            if len(mirror_joints) != 1:
                continue
            mirror_name = mirror_joints[0].split("|")[-1]
            replace_joints.append([joint_name, mirror_name])

        # ★ 按照名字长度降序排序，防止短名字（如 Shoulder_L）错误地替换长名字（如 Shoulder_L_Part）的子串
        replace_joints.sort(key=lambda x: len(x[0]), reverse=True)

        target_mirrors = []
        for target in targets:
            mirror = target
            for src, dst in replace_joints:
                mirror = mirror.replace(src, dst)
            target_mirrors.append([target, mirror])
        return target_mirrors

    @classmethod
    def copy_mirrored_pose_data(cls, target_mirrors):
        """Copy exact local pose matrices and normalize bilateral direction labels."""
        copied = []
        selection = cmds.ls(selection=True, long=True) or []
        try:
            for source, destination in target_mirrors:
                source_match = re.match(
                    r"^(.+)_a([0-9]{1,3})_d([0-9]{1,3})$", source
                )
                destination_match = re.match(
                    r"^(.+)_a([0-9]{1,3})_d([0-9]{1,3})$", destination
                )
                if source_match is None or destination_match is None:
                    continue
                source_data = cls.targets_to_ad_poses([source])
                destination_data = cls.targets_to_ad_poses([destination])
                if len(source_data) != 1 or len(destination_data) != 1:
                    continue
                source_ad, source_poses = source_data[0]
                destination_ad, destination_poses = destination_data[0]
                if len(source_poses) != 1 or len(destination_poses) != 1:
                    continue
                matrix = source_ad.get_saved_pose_matrix(source_poses[0])
                if matrix is None:
                    continue
                destination_ad.detect_mirrored_direction(
                    source_poses[0][1], matrix
                )
                destination_ad.add_pose(
                    destination_poses[0], control_matrix=matrix
                )
                copied.append(destination)
        finally:
            if selection:
                cmds.select(selection, replace=True)
            else:
                cmds.select(clear=True)
        return copied

    @classmethod
    @undo_chunk
    def mirror_by_targets(cls, targets):
        polygons = get_selected_polygons()
        # ★ 如果没有选中 polygon，自动从源 target 的 blendShape 连接反查关联的 polygon
        if not polygons:
            for target in targets:
                match = re.match("(.+)_a([0-9]{1,3})_d([0-9]{1,3})", target)
                if match is None:
                    continue
                joint_name = match.group(1)
                ref_node = find_reference_node_by_name(joint_name)
                if ref_node is None:
                    continue
                for bs_node in cmds.listConnections(ref_node, type="blendShape") or []:
                    geos = cmds.blendShape(bs_node, q=True, geometry=True) or []
                    for geo in geos:
                        transform = cmds.listRelatives(geo, p=True, f=True)
                        if transform:
                            t = transform[0]
                            if t not in polygons:
                                polygons.append(t)
                if polygons:
                    break
        target_mirrors = cls.targets_to_mirror(targets)
        cls.copy_mirrored_pose_data(target_mirrors)
        cls.add_by_targets([m for _, m in target_mirrors], polygons)
        for polygon in polygons:
            bs.mirror_targets(polygon, target_mirrors)

    @classmethod
    @undo_chunk
    def warp_copy_targets(cls, targets):
        polygons = get_selected_polygons()
        if not len(polygons) == 2:
            print("please selected two polygon")
            return None
        targets = [t for t in targets if "_COMB_" not in t]+[t for t in targets if "_COMB_" in t]
        src, dst = polygons
        cls.all_to_zero()
        cmds.refresh()
        warp = cmds.duplicate(dst)[0]
        bs.get_orig(warp)
        cmds.select(warp, src)
        from maya import mel
        mel.eval('CreateWrap')
        for target in targets:
            cls.set_pose_by_targets([target], all_targets=[])
            cmds.select(warp, dst)
        if not len(polygons) == 2:
            print("please selected two polygon")
            return None
        targets = [t for t in targets if "_COMB_" not in t]+[t for t in targets if "_COMB_" in t]
        src, dst = polygons
        cls.all_to_zero()
        cmds.refresh()
        warp = cmds.duplicate(dst)[0]
        bs.get_orig(warp)
        cmds.select(warp, src)
        from maya import mel
        mel.eval('CreateWrap')
        for target in targets:
            cls.set_pose_by_targets([target], all_targets=[])
            cmds.select(warp, dst)
            cls.edit_by_selected_target(target)
            cls.set_pose_by_targets([target], all_targets=[], ib=0)
        cls.all_to_zero()
        cmds.delete(warp)

    def __init__(self, joint, control):
        self.joint = joint
        self.control = control
        self.reference = joint
        self.prefix = joint.split("|")[-1] if isinstance(joint, str) else joint
        self.update_reference()

    def update_reference(self):
        u"""
        :return:
        在骨骼引用的情况下，创建一个组来代替骨骼。
        """
        reference_name = self.joint + "_Reference"
        nodes = cmds.ls(reference_name) or []
        if len(nodes) >= 1:
            self.reference = nodes[0]
            return
        is_ref = cmds.referenceQuery(self.joint, isNodeReferenced=True) if cmds.objExists(self.joint) else False
        if not is_ref:
            return
        poses = self.get_poses()
        self.reference = cmds.group(em=1, n=reference_name)
        cmds.addAttr(self.reference, ln="angle", k=1, at="double", min=0, max=180)
        cmds.addAttr(self.reference, ln="direction", k=1, at="double", min=0, max=360)
        self.update_angle_direction()
        cmds.connectAttr(self.joint + ".angle", self.reference + ".angle")
        cmds.connectAttr(self.joint + ".direction", self.reference + ".direction")
        self.update_poses(poses)
        connections = cmds.listConnections(self.joint, type="blendShape", p=1, c=1, s=False, d=True) or []
        for i in range(0, len(connections), 2):
            src = connections[i]
            dst = connections[i+1]
            dst_node = dst.split(".")[0]
            if cmds.referenceQuery(dst_node, isNodeReferenced=True):
                continue
            target_name = src.split(".")[-1]
            if cmds.attributeQuery(target_name, node=self.reference, exists=True):
                cmds.connectAttr(self.reference + "." + target_name, dst, f=1)
        for pose in poses:
            target_name = self.target_name(pose)
            comb_name = "COMB_" + target_name
            if not cmds.attributeQuery(comb_name, node=self.joint, exists=True):
                continue
            for node in cmds.listConnections(self.joint + "." + comb_name, type="combinationShape") or []:
                if target_name not in node:
                    continue
                for attr in cmds.listAttr(node, ud=1) or []:
                    comb_target_name = attr.split(".")[-1]
                    self.add_by_target(comb_target_name)

    def convert_old_to_new(self):
        old_ads = []
        bs_nodes = []
        nodes = []
        for multiply in cmds.ls(self.prefix + "*_a*_d*", type="multiplyDivide") or []:
            pattern = re.match(".+_a([0-9]{1,3})_d([0-9]{1,3})_mul", multiply)
            if pattern is None:
                continue
            nodes.append(multiply)
            angle, direction = pattern.groups()
            angle, direction = int(angle), int(direction)
            old_ads.append([angle, direction])
            for bs_node in cmds.listConnections(multiply, type="blendShape") or []:
                if bs_node not in bs_nodes:
                    bs_nodes.append(bs_node)
        convert = False
        for angle, direction in old_ads:
            name = self.target_name([angle, direction])
            if not cmds.attributeQuery(name, node=self.joint, exists=True):
                convert = True
                break
        if not convert:
            return
        cmds.delete(nodes)
        self.update_angle_direction()
        self.update_poses(old_ads)
        for pose in old_ads:
            name = self.target_name(pose)
            if not cmds.attributeQuery(name, node=self.joint, exists=True):
                continue
            for bs_node in bs_nodes:
                if not cmds.attributeQuery(name, node=bs_node, exists=True):
                    continue
                cmds.connectAttr(self.joint + "." + name, bs_node + "." + name, f=1)

    def _is_opm_rig(self):
        """检测关节是否使用 Offset Parent Matrix 绑定（offsetParentMatrix 有输入连接）"""
        return bool(cmds.listConnections(
            self.joint + ".offsetParentMatrix", s=True, d=False))

    def delete_old_angle_network(self):
        """断开并清理该关节旧的角度求值节点网络。"""
        for attr in ["angle", "direction"]:
            if cmds.attributeQuery(attr, node=self.joint, exists=True):
                conns = cmds.listConnections(self.joint + "." + attr, s=True, d=False, p=True) or []
                for conn in conns:
                    cmds.disconnectAttr(conn, self.joint + "." + attr)
        nodes_to_delete = [
            self.prefix + "_compose",
            self.prefix + "_pointMatrix",
            self.prefix + "_angle",
            self.prefix + "_angleUnit",
            self.prefix + "_direction",
            self.prefix + "_directionUnit",
            self.prefix + "_minus",
            self.prefix + "_condition",
            self.prefix + "_directionMirror",
            self.prefix + "_currentMatrix",
            self.prefix + "_deltaMatrix",
            self.prefix + "_deltaDecompose",
            self.prefix + "_twistNormalize",
            self.prefix + "_twistInverse",
            self.prefix + "_swingQuat",
            self.prefix + "_swingMatrix"
        ]
        for node in nodes_to_delete:
            if cmds.objExists(node):
                conns = cmds.listConnections(node, c=True, p=True, d=False, s=True) or []
                for i in range(0, len(conns), 2):
                    dst = conns[i]
                    src = conns[i+1]
                    if cmds.isConnected(src, dst):
                        cmds.disconnectAttr(src, dst)
                cmds.delete(node)

    def update_angle_direction(self, skip_eval_switch=False):
        if not cmds.pluginInfo("matrixNodes", q=True, loaded=True):
            cmds.loadPlugin("matrixNodes")
        is_opm_rig = self._is_opm_rig()
        if is_opm_rig and not cmds.pluginInfo("quatNodes", q=True, loaded=True):
            cmds.loadPlugin("quatNodes")

        if is_opm_rig:
            parents = cmds.listRelatives(self.joint, parent=True, fullPath=True) or []
            if not parents:
                raise RuntimeError("{} has no parent for local angle evaluation".format(self.joint))
            parent = parents[0]
            point_name = self.prefix + "_pointMatrix"
            delta_name = self.prefix + "_deltaMatrix"
            swing_matrix_name = self.prefix + "_swingMatrix"
            decompose_name = self.prefix + "_deltaDecompose"
            twist_normalize_name = self.prefix + "_twistNormalize"
            twist_inverse_name = self.prefix + "_twistInverse"
            swing_quat_name = self.prefix + "_swingQuat"
            uses_local_quaternion_swing = (
                cmds.objExists(delta_name) and
                cmds.objExists(decompose_name) and
                cmds.objExists(twist_normalize_name) and
                cmds.objExists(twist_inverse_name) and
                cmds.objExists(swing_quat_name) and
                cmds.objExists(swing_matrix_name) and
                cmds.objExists(point_name) and
                cmds.isConnected(self.joint + ".dagLocalMatrix", delta_name + ".matrixIn[1]") and
                cmds.isConnected(delta_name + ".matrixSum", decompose_name + ".inputMatrix") and
                cmds.isConnected(decompose_name + ".outputQuatX", twist_normalize_name + ".inputQuatX") and
                cmds.isConnected(decompose_name + ".outputQuatW", twist_normalize_name + ".inputQuatW") and
                cmds.isConnected(twist_normalize_name + ".outputQuat", twist_inverse_name + ".inputQuat") and
                cmds.isConnected(decompose_name + ".outputQuat", swing_quat_name + ".input1Quat") and
                cmds.isConnected(twist_inverse_name + ".outputQuat", swing_quat_name + ".input2Quat") and
                cmds.isConnected(swing_quat_name + ".outputQuat", swing_matrix_name + ".inputQuat") and
                not cmds.getAttr(swing_matrix_name + ".useEulerRotation") and
                cmds.isConnected(swing_matrix_name + ".outputMatrix", point_name + ".matrix")
            )
            if not uses_local_quaternion_swing:
                self.delete_old_angle_network()

        if cmds.attributeQuery("angle", node=self.joint, exists=True):
            # 只有当已有属性且有输入连接时才跳过，否则继续创建连接网络
            if cmds.listConnections(self.joint + ".angle", s=True, d=False):
                return
        if cmds.attributeQuery("direction", node=self.joint, exists=True):
            if cmds.listConnections(self.joint + ".direction", s=True, d=False):
                return

        if not cmds.attributeQuery("angle", node=self.joint, exists=True):
            cmds.addAttr(self.joint, ln="angle", k=1, at="double", min=0, max=180)
        if not cmds.attributeQuery("direction", node=self.joint, exists=True):
            cmds.addAttr(self.joint, ln="direction", k=1, at="double", min=0, max=360)

        if is_opm_rig:
            # === OPM 矩阵模式 ===
            # dagLocalMatrix 已包含 OPM；四元数 swing/twist 避开 Euler 90 度换解。
            if not (cmds.objExists(self.joint + ".bindPose") and
                    cmds.objExists(parent + ".bindPose")):
                raise RuntimeError("{} and its parent require bindPose matrices".format(self.joint))

            child_bind = MMatrix(cmds.getAttr(self.joint + ".bindPose"))
            parent_bind = MMatrix(cmds.getAttr(parent + ".bindPose"))
            rest_relative_inverse = (child_bind * parent_bind.inverse()).inverse()

            delta = create_node("multMatrix", n=self.prefix + "_deltaMatrix")
            cmds.setAttr(delta + ".matrixIn[0]", *list(rest_relative_inverse), type="matrix")
            cmds.connectAttr(self.joint + ".dagLocalMatrix", delta + ".matrixIn[1]")

            decompose = create_node("decomposeMatrix", n=self.prefix + "_deltaDecompose")
            cmds.connectAttr(delta + ".matrixSum", decompose + ".inputMatrix")

            twist_normalize = create_node("quatNormalize", n=self.prefix + "_twistNormalize")
            cmds.connectAttr(decompose + ".outputQuatX", twist_normalize + ".inputQuatX")
            cmds.connectAttr(decompose + ".outputQuatW", twist_normalize + ".inputQuatW")

            twist_inverse = create_node("quatInvert", n=self.prefix + "_twistInverse")
            cmds.connectAttr(twist_normalize + ".outputQuat", twist_inverse + ".inputQuat")

            swing_quat = create_node("quatProd", n=self.prefix + "_swingQuat")
            cmds.connectAttr(decompose + ".outputQuat", swing_quat + ".input1Quat")
            cmds.connectAttr(twist_inverse + ".outputQuat", swing_quat + ".input2Quat")

            swing_matrix = create_node("composeMatrix", n=self.prefix + "_swingMatrix")
            cmds.setAttr(swing_matrix + ".useEulerRotation", False)
            cmds.connectAttr(swing_quat + ".outputQuat", swing_matrix + ".inputQuat")

            point = create_node("vectorProduct", n=self.prefix + "_pointMatrix")
            cmds.setAttr(point + ".operation", 3)  # Vector Matrix Product
            cmds.setAttr(point + ".input1", 1, 0, 0, type="double3")
            cmds.setAttr(point + ".normalizeOutput", False)
            cmds.connectAttr(swing_matrix + ".outputMatrix", point + ".matrix")

        elif (cmds.attributeQuery("QRotateX", node=self.joint, exists=True) and
                cmds.attributeQuery("QRotateY", node=self.joint, exists=True) and
                cmds.attributeQuery("QRotateZ", node=self.joint, exists=True)):
            # === QRotate 自定义属性模式（矩阵绑定提取的旋转值） ===
            compose = create_node("composeMatrix", n=self.prefix + "_compose")
            cmds.connectAttr(self.joint + ".QRotateX", compose + ".inputRotateX")
            cmds.connectAttr(self.joint + ".QRotateY", compose + ".inputRotateY")
            cmds.connectAttr(self.joint + ".QRotateZ", compose + ".inputRotateZ")
            cmds.connectAttr(self.joint + ".rotateOrder", compose + ".inputRotateOrder")

            point = create_node("pointMatrixMult", n=self.prefix + "_pointMatrix")
            cmds.setAttr(point + ".inPointX", 1)
            cmds.connectAttr(compose + ".outputMatrix", point + ".inMatrix")

        else:
            # === 传统 rotateXYZ 模式 ===
            compose = create_node("composeMatrix", n=self.prefix + "_compose")
            cmds.connectAttr(self.joint + ".rotateX", compose + ".inputRotateX")
            cmds.connectAttr(self.joint + ".rotateY", compose + ".inputRotateY")
            cmds.connectAttr(self.joint + ".rotateZ", compose + ".inputRotateZ")
            cmds.connectAttr(self.joint + ".rotateOrder", compose + ".inputRotateOrder")

            point = create_node("pointMatrixMult", n=self.prefix + "_pointMatrix")
            cmds.setAttr(point + ".inPointX", 1)
            cmds.connectAttr(compose + ".outputMatrix", point + ".inMatrix")

        angle = create_node("angleBetween", n=self.prefix + "_angle")
        cmds.setAttr(angle + ".vector1", 1, 0, 0, type="double3")
        cmds.connectAttr(point + ".outputX", angle + ".vector2X")
        cmds.connectAttr(point + ".outputY", angle + ".vector2Y")
        cmds.connectAttr(point + ".outputZ", angle + ".vector2Z")

        angle_unit = create_node("unitConversion", n=self.prefix + "_angleUnit")
        cmds.setAttr(angle_unit + ".conversionFactor", 180 / math.pi)
        cmds.connectAttr(angle + ".angle", angle_unit + ".input")
        cmds.connectAttr(angle_unit + ".output", self.joint + ".angle")

        direction = create_node("angleBetween", n=self.prefix + "_direction")
        cmds.setAttr(direction + ".vector1", 0, 0, 0, type="double3")
        cmds.setAttr(direction + ".vector1", 0, 1, 0, type="double3")
        cmds.connectAttr(point + ".outputY", direction + ".vector2Y")
        cmds.connectAttr(point + ".outputZ", direction + ".vector2Z")

        direction_unit = create_node("unitConversion", n=self.prefix + "_directionUnit")
        cmds.setAttr(direction_unit + ".conversionFactor", 180 / math.pi)
        cmds.connectAttr(direction + ".angle", direction_unit + ".input")

        minus = create_node("plusMinusAverage", n=self.prefix + "_minus")
        cmds.setAttr(minus + ".input1D[0]", 360)
        cmds.setAttr(minus + ".operation", 2)
        cmds.connectAttr(direction_unit + ".output", minus + ".input1D[1]")

        condition = create_node("condition", n=self.prefix + "_condition")
        cmds.connectAttr(point + ".outputZ", condition + ".firstTerm")
        cmds.setAttr(condition + ".operation", 2)
        cmds.connectAttr(direction_unit + ".output", condition + ".colorIfTrueR")
        cmds.connectAttr(minus + ".output1D", condition + ".colorIfFalseR")
        direction_output = condition + ".outColorR"
        if self.direction_is_mirrored():
            mirror = create_node(
                "plusMinusAverage", n=self.prefix + "_directionMirror"
            )
            cmds.setAttr(mirror + ".operation", 2)
            cmds.setAttr(mirror + ".input1D[0]", 360)
            cmds.connectAttr(direction_output, mirror + ".input1D[1]")
            direction_output = mirror + ".output1D"
        cmds.connectAttr(direction_output, self.joint + ".direction")

    def update_sdk(self, dvs, cd, name, keep=1):
        return update_sdk(self.reference, dvs, cd, name, keep)

    def update_poses(self, poses):
        self.update_angle_direction()
        direction_angles = {}
        for angle, direction in poses:
            direction_angles.setdefault(direction, []).append(angle)
        for direction, angles in direction_angles.items():
            direction_angles[direction] = list(sorted(angles))
        directions = list(sorted(list(direction_angles.keys())))
        _sdk_ds = list(sorted(set([direction+offset for direction in directions for offset in [-360, 0, 360]])))
        use_attr_list = [self.reference + ".angle", self.reference + ".direction"]
        for direction in directions:
            if direction == 360:
                direction = 0
            sdk_ds = list(sorted(set(_sdk_ds+[direction+90, direction-90])))
            index = sdk_ds.index(direction)
            dvs = []
            for offset in [-360, 0, 360]:
                dvs.extend([
                    [sdk_ds[index - 1] + offset, 0],
                    [direction - 1.0 + offset, 1],
                    [direction + 1.0 + offset, 1],
                    [sdk_ds[index + 1] + offset, 0],
                ])
            direction_attr = self.update_sdk(dvs, self.reference + ".direction", "direction_%i" % direction, False)
            angles = direction_angles[direction]
            sdk_as = list(sorted(set(angles+[-1, 0, 180])))
            use_attr_list.append(direction_attr)
            for angle in angles:
                index = sdk_as.index(angle)
                dvs = [
                    [sdk_as[index - 1], 0],
                    [angle - 0.5, 1],
                    [angle + 0.5, 1],
                    [sdk_as[index + 1], 0],
                ]
                if dvs[-1][0] == 180:
                    dvs[-1][1] = 1
                angle_attr = self.update_sdk(
                    dvs,
                    self.reference + ".angle",
                    "angle_%i_%i_%i" % (sdk_as[index - 1], angle, sdk_as[index + 1]),
                    False,
                )
                name = self.target_name([angle, direction])
                if not cmds.attributeQuery(name, node=self.reference, exists=True):
                    cmds.addAttr(self.reference, ln=name, k=1, at="double", min=0, max=1)
                pose_matrix_name = self.pose_matrix_name([angle, direction])
                pose_matrix_attr = self.reference + "." + pose_matrix_name
                if cmds.attributeQuery(pose_matrix_name, node=self.reference, exists=True):
                    use_attr_list.append(pose_matrix_attr)
                inputs = cmds.listConnections(self.reference + "." + name, type="blendWeighted", d=False, s=True) or []
                if inputs:
                    cmds.delete(inputs)
                # 将bw节点名从name改为name+BW,防止出现bs目标体同名节点。
                old_bw = cmds.ls(name, type="blendWeighted") or []
                if old_bw:
                    cmds.delete(old_bw)
                bw = create_node("blendWeighted",  n=name+"BW")
                cmds.connectAttr(angle_attr, bw + ".input[0]")
                cmds.connectAttr(direction_attr, bw + ".weight[0]")
                cmds.connectAttr(bw + ".output", self.reference + "." + name)
                use_attr_list.extend([angle_attr, self.reference + "." + name])
        for attr in cmds.listAttr(self.reference, ud=1) or []:
            full_attr = self.reference + "." + attr
            if full_attr in use_attr_list:
                continue
            if not any([field in attr for field in [self.prefix, "angle", "direction"]]):
                continue
            if attr.startswith("COMB_"+self.prefix):
                continue
            inputs = cmds.listConnections(full_attr, type="multiplyDivide", d=False, s=True) or []
            if inputs:
                cmds.delete(inputs)
            for bs_attr in cmds.listConnections(full_attr, type="blendShape", p=1) or []:
                bs.delete_target(bs_attr)
            cmds.deleteAttr(full_attr)
        self.repair_comb()

    def get_control_pose(self, init=False, int_round=True):
        self.update_angle_direction()
        angle = cmds.getAttr(self.reference + ".angle")
        direction = cmds.getAttr(self.reference + ".direction")
        raw_direction = direction
        if int_round:
            angle, direction = int(round(angle)), int(round(direction))
        if abs(direction - 360) < 0.0001:
            direction = 0
        if abs(angle - 0) < 0.0001:
            direction = 0
        elif int_round:
            existing_directions = set(pose[1] for pose in self.get_poses())
            if existing_directions:
                nearest = min(
                    existing_directions,
                    key=lambda value: direction_distance(raw_direction, value),
                )
                if direction_distance(raw_direction, nearest) <= 1.0:
                    direction = nearest
        if init:
            self.set_pose([angle, direction])
        return tuple([angle, direction])

    def get_poses(self):
        poses = []
        for attr in cmds.listAttr(self.reference, ud=1) or []:
            name = attr.split(".")[-1]
            if self.prefix not in name:
                continue
            pattern = re.match("^%s_a([0-9]{1,3})_d([0-9]{1,3})$" % self.prefix, name)
            if pattern is None:
                continue
            if not cmds.attributeQuery(name, node=self.reference, exists=True):
                continue
            angle, direction = pattern.groups()
            angle, direction = int(angle), int(direction)
            poses.append(tuple([angle, direction]))
        return get_sorted_poses(poses)

    @classmethod
    def load_targets(cls, target_names, cover=False):
        data = {}
        pose_targets = list(filter(target_is_pose, target_names))
        for target_name in pose_targets:
            match = re.match("(.+)_a([0-9]{1,3})_d([0-9]{1,3})", target_name)
            if match is None:
                continue
            joint_name, angle, direction = match.groups()
            angle, direction = int(angle), int(direction)
            data.setdefault(joint_name, []).append((angle, direction))
        ad_poses = []
        for joint_name, poses in data.items():
            joint = find_node_by_name(joint_name)
            if joint is None:
                continue
            ctrl = find_ctrl_by_joint(joint)
            if ctrl is None:
                continue
            ad = cls(joint, ctrl)
            ad_poses.append([ad, poses])
        result_attr_list = []
        for ad, poses in ad_poses:
            if not cover:
                for pose in ad.get_poses():
                    if pose not in poses:
                        poses.append(pose)
            ad.update_poses(poses)
            for pose in poses:
                result_attr_list.append(ad.reference + "." + ad.target_name(pose))
        comb_targets = list(filter(target_is_comb, target_names))
        ib_targets = list(filter(target_is_ib, target_names))
        for target_name in comb_targets:
            result_attr_list.append(cls.add_by_target(target_name))
        for target_name in ib_targets:
            result_attr_list.append(cls.add_by_target(target_name))
        return result_attr_list

    @classmethod
    def clear_useless_pose(cls):
        useless_targets = []
        for target_name in cls.get_targets():
            attr = cls.add_by_target(target_name)
            if cmds.listConnections(attr, type="blendShape"):
                continue
            useless_targets.append(target_name)
        cls.delete_by_targets(useless_targets)

    @classmethod
    def auto_insert_pose(cls, joints):
        target_name = cls.get_auto_target_name(joints)
        if target_name is None:
            return
        control_matrix = None
        if target_is_pose(target_name):
            ad, pose = cls.target_to_ad_pose(target_name)
            if not cmds.attributeQuery(ad.target_name(pose), node=ad.reference, exists=True):
                control_matrix = cmds.xform(
                    ad.control, query=True, matrix=True, objectSpace=True
                )
        polygons = []
        target_names = comb_target_to_targets([target_name])
        for ad, poses in cls.targets_to_ad_poses(target_names):
            for attr in cmds.listAttr(ad.reference, ud=1) or []:
                for _bs in cmds.listConnections(ad.reference + "." + attr, type="blendShape") or []:
                    geo = cmds.blendShape(_bs, q=True, g=True)
                    if not geo:
                        continue
                    parent = cmds.listRelatives(geo[0], p=1)
                    if not parent:
                        continue
                    polygon = parent[0]
                    if polygon in polygons:
                        continue
                    if cmds.referenceQuery(polygon, isNodeReferenced=True):
                        continue
                    polygons.append(polygon)
        if not polygons:
            return
        attr = cls.add_by_target(target_name, control_matrix=control_matrix)
        cls.set_pose_by_targets([target_name])
        dup_polygons = []
        for polygon in polygons:
            dup_polygons.append(cmds.duplicate(polygon)[0])
        for src, dst in zip(dup_polygons, polygons):
            bs.bridge_connect_edit(attr, src, dst)
        cmds.delete(dup_polygons)
