# coding:utf-8
from maya.api.OpenMaya import *
from . import config
from .general_ui import *
from .facePin.core import *
from . import tools

def matrix_to_position_rotation(matrix):
    trans = MTransformationMatrix(matrix)
    translate = list(matrix)[12:15]
    rotation = trans.rotation(True)
    return translate, rotation


def position_rotation_to_matrix(position, rotation):
    m = list(rotation.asMatrix())
    m[12:15] = position
    return MMatrix(m)


def api_ls(*names):
    selection_list = MSelectionList()
    for name in names:
        selection_list.add(name)
    return selection_list


def ray_point(polygon, matrix, direction, point):
    fn_mesh = MFnMesh(api_ls(polygon).getDagPath(0))
    ray_source = MFloatPoint(MPoint(0, 0, 0) * matrix)
    ray_direction = MFloatVector(MVector(*direction) * matrix)
    result = fn_mesh.closestIntersection(ray_source, ray_direction, MSpace.kWorld, 10000, False)
    if result:
        return result[0]
    else:
        return point


def create_direction_joint(polygon, joint, i, matrix):
    direction = [[0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1], None][i]
    suffix = ["_ty_plus", "_ty_minus", "_tz_plus", "_tz_minus", "_half"][i]
    joint_name = joint if isinstance(joint, str) else joint
    short_name = joint_name.split("|")[-1]
    deform_joint = cmds.joint(joint, n="corrective_" + short_name + suffix)
    cmds.xform(deform_joint, m=list(matrix), ws=1)

    radius = cmds.getAttr(joint + ".radius")
    cmds.setAttr(deform_joint + ".radius", radius)

    if direction is None:
        point = MPoint(0, 0, 0.006) * matrix
    else:
        soft_radius = cmds.softSelect(q=1, ssd=1)
        point = MPoint(direction[0] * soft_radius, direction[1] * soft_radius, direction[2] * soft_radius) * matrix
        if polygon:
            point = ray_point(polygon, matrix, direction, point)
    cmds.xform(deform_joint, t=[point.x, point.y, point.z], ws=1)
    return deform_joint


def find_mirror_joint(joint):
    joint_name = joint if isinstance(joint, str) else joint
    short_name = joint_name.split("|")[-1].split(":")[-1]
    joints = cmds.ls(config.get_rl_names(short_name), type="joint") or []
    if len(joints) != 1:
        return None
    return joints[0]


def create_joint(polygon, joint, directions, rotate_offset):
    matrix_list = cmds.xform(joint, q=True, m=True, ws=1)
    matrix = MMatrix(matrix_list)
    if rotate_offset:
        parent = cmds.listRelatives(joint, p=True)
        if parent:
            parent_matrix_list = cmds.xform(parent[0], q=True, m=True, ws=1)
            parent_matrix = MMatrix(parent_matrix_list)
            local_matrix_list = cmds.xform(joint, q=True, m=True, ws=0)
            local_matrix = MMatrix(local_matrix_list)
            position, rotation = matrix_to_position_rotation(local_matrix)
            half_rotation = MQuaternion.slerp(MQuaternion(0, 0, 0, 1), rotation, 0.5)
            matrix = position_rotation_to_matrix(position, half_rotation) * parent_matrix
    deform_joints = []
    for i, direction in enumerate(directions):
        if direction:
            deform_joint = create_direction_joint(polygon, joint, i, matrix)
            deform_joints.append(deform_joint)
    return deform_joints


def world_fip_matrix(matrix):
    # 创建一个新的矩阵列表
    m = list(matrix)
    m[1] *= -1
    m[5] *= -1
    m[9] *= -1
    m[2] *= -1
    m[6] *= -1
    m[10] *= -1
    m[12] *= -1
    return m

def get_parent(joint):
    parents = cmds.listRelatives(joint, p=True)
    if not parents:
        return None
    parent = parents[0]
    return parent

def mirror_joints(joints=None):
    if joints is None:
        joints = cmds.ls(sl=1, type="joint") or []
    parent_joints = {}
    for joint in joints:
        parent = get_parent(joint)
        parent_joints.setdefault(parent, []).append(joint)
    for parent, children in parent_joints.items():
        if not parent:
            mirror_parent = None
        else:
            mirror_parent = find_mirror_joint(parent)
        if not mirror_parent:
            mirror_parent = parent
        for child in children:
            names = config.get_rl_names(child)
            if names:
                name = names[0]
            else:
                name = child + "_mirror"
            existing = cmds.ls(name, type="joint") or []
            if existing:
                mirror_joint = existing[0]
            else:
                mirror_joint = cmds.joint(mirror_parent, name=name)
            radius = cmds.getAttr(child + ".radius")
            cmds.setAttr(mirror_joint + ".radius", radius)
            child_matrix_list = cmds.xform(child, q=True, m=True, ws=1)
            child_matrix = MMatrix(child_matrix_list)
            cmds.xform(mirror_joint, m=world_fip_matrix(child_matrix), ws=1)


def mirror_selected_joints():
    selected = cmds.ls(sl=True, type="joint") or []
    if len(selected) < 2:
        return
    src, dst = selected[0], selected[1]
    dst_matrix_list = cmds.xform(dst, q=True, m=True, ws=1)
    dst_matrix = MMatrix(dst_matrix_list)
    cmds.xform(src, m=world_fip_matrix(dst_matrix), ws=1)


def create_joints(polygon, joints, directions, rotate_offset, mirror):
    deform_joints = []
    for joint in joints:
        deform_joints += create_joint(polygon, joint, directions, rotate_offset)
    if mirror:
        mirror_joints(deform_joints)


class CreateJointTool(Tool):
    title = u"创建骨骼"
    button_text = u"创建"

    def __init__(self, parent=None):
        Tool.__init__(self, parent=get_host_app())
        self.polygon = MayaObjLayout(u"模型：", 40)
        self.kwargs_layout.addLayout(self.polygon)
        self.parents = JointList()
        self.kwargs_layout.addLayout(self.parents)
        self.directions = [QCheckBox(tex) for tex in ["+y", "-y", "+z", "-z", "center"]]
        self.kwargs_layout.addLayout(h_layout(*self.directions))
        self.kwargs = [QCheckBox(tex) for tex in [u"旋转偏移", u"镜像"]]
        self.kwargs_layout.addLayout(h_layout(*self.kwargs))
        for check in self.directions+self.kwargs:
            check.setChecked(True)
        self.directions[4].setChecked(False)

    def apply(self):
        polygon = self.polygon.obj
        parents = cmds.ls(self.parents.get_joints(), type="joint") or []
        directions = [check.isChecked() for check in self.directions]
        rotate_offset = self.kwargs[0].isChecked()
        mirror = self.kwargs[1].isChecked()
        create_joints(polygon, parents, directions, rotate_offset, mirror)



class BodyDeform(object):

    def __init__(self):
        self.fp = FacePin("adPoseJointDeform")
        self.fp.body = True

    def add_selected_joints(self, joints, clusters=None, weights=None):
        self.fp.load()
        for i, joint in enumerate(joints):
            self.fp.add_pin(joint, cmds.xform(joint, q=1, ws=1, m=1))
            if clusters is None:
                parent = (cmds.listRelatives(joint, p=1) or [None])[0]
                if parent and cmds.nodeType(joint) == "joint":
                    self.fp.set_follow(parent, joint, 1.0)
                    parent = (cmds.listRelatives(parent, p=1) or [None])[0]
                    if parent and cmds.nodeType(joint) == "joint":
                        self.fp.set_follow(parent, joint, 1.0)
            else:
                for cluster, weight in zip(clusters, weights[i]):
                    self.fp.set_follow(cluster, joint, weight)
        self.fp.build()
        self.constraint_joints(joints)

    @staticmethod
    def constraint_joints(joints):
        for joint in joints:
            pc = joint + "_parentConstraint"
            if cmds.objExists(pc):
                cmds.delete(pc)
            pc = cmds.parentConstraint(joint + "Pin", joint, n=pc)
            cmds.parent(pc, joint + "Pin")

    def edit_target(self, edit_target_fun):
        src, dst = self.fp.driver_name(), self.fp.plane_name()
        if not cmds.objExists(dst):
            return
        if not cmds.objExists(src):
            return
        temp = cmds.duplicate(src, n="temp_"+src)[0]
        try:
            cmds.select(temp, dst)
            edit_target_fun()
        except Exception as e:
            import traceback
            traceback.print_exc()
            cmds.warning(u"Pin变形驱动编辑失败: %s" % e)
        finally:
            cmds.delete(temp)

    def remove_selected_joints(self, joints):
        self.fp.load()
        joint_matrix = {joint: cmds.xform(joint, q=1, ws=0, m=1) for joint in joints}
        for joint in joints:
            self.fp.remove_pin(joint)
        for joint, matrix in joint_matrix.items():
            cmds.xform(joint, m=matrix, ws=0)
        self.fp.build()

    def load_joint_driver_data(self, data):
        tools.set_blend_shape_sdk_data(data["bs_sdk"])
        joints = self.create_joints(data)
        self.fp.load()
        self.fp.update_data(data)
        self.fp.build()
        self.constraint_joints(joints)

    @staticmethod
    def create_joints(data):
        joints = []
        for joint in data["pins"]:
            if cmds.objExists(joint):
                continue
            joint = cmds.joint(data.get('parents', dict()).get(joint), n=joint)
            joints.append(joint)
            matrix = data.get("pin_matrices", dict()).get(joint)
            cmds.xform(joint, ws=1, m=matrix)
        return joints

    def get_joint_driver_data(self):
        self.fp.load()
        # base data
        data = self.fp.get_all_data()
        # parent data
        parents = dict()
        for joint in self.fp.pins:
            if not cmds.objExists(joint):
                parents[joint] = None
                continue
            parent_nodes = cmds.listRelatives(joint, p=1)
            if not parent_nodes:
                parents[joint] = None
                continue
            parents[joint] = parent_nodes[0]
        data["parents"] = parents
        # sdk data
        if cmds.objExists(self.fp.plane_name()):
            cmds.select(self.fp.plane_name())
            data["bs_sdk"] = tools.get_blend_shape_sdk_data()
            data["bs_sdk"]["bs_data"] = []
        return data


def tool_add_selected_joints():
    joints = cmds.ls(sl=1, type="joint")
    BodyDeform().add_selected_joints(joints)


def tool_edit_target(edit_target_fun):
    BodyDeform().edit_target(edit_target_fun)


def tool_remove_selected_joints():
    joints = cmds.ls(sl=1, type="joint")
    BodyDeform().remove_selected_joints(joints)


def tool_get_joint_driver_data():
    return BodyDeform().get_joint_driver_data()


def tool_load_joint_driver_data(data):
    BodyDeform().load_joint_driver_data(data)
