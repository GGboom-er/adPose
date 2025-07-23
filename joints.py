# coding:utf-8
import pymel.core as pm
import math
from maya.OpenMaya import *
from maya.OpenMayaAnim import *
from  maya import cmds
from . import config
from . import bs as bs_api
from .general_ui import *
from . import ADPose


def dot_qq(q1, q2):
    return q1.x * q2.x + q1.y * q2.y + q1.z * q2.z + q1.w * q2.w


def mul_qd(q, w):
    return pm.datatypes.Quaternion(q.x*w, q.y*w, q.z*w, q.w*w)


def add_qq(q1, q2):
    return pm.datatypes.Quaternion(q1.x + q2.x, q1.y + q2.y, q1.z + q2.z, q1.w + q2.w)


def slerp(q1, q2, t):
    cos_a = dot_qq(q1, q2)
    if cos_a < 0:
        cos_a = - cos_a
        mul_qd(q2, -1)
    if cos_a > 0.999999999:
        w1, w2 = 1-t, t
    else:
        sin_a = math.sqrt(1-cos_a*cos_a)
        a = math.atan2(sin_a, cos_a)
        in_sin_a = 1.0/sin_a
        w1 = math.sin((1-t)*a) * in_sin_a
        w2 = math.sin(t * a) * in_sin_a
    return add_qq(mul_qd(q1, w1), mul_qd(q2, w2))


def matrix_to_position_rotation(matrix):
    trans = pm.datatypes.TransformationMatrix(matrix)
    translate = trans.getTranslation("world")
    rotation = trans.getRotation().asQuaternion()
    return translate, rotation


def position_rotation_to_matrix(position, rotation):
    trnas = pm.datatypes.TransformationMatrix(rotation.matrix)
    trnas.setTranslation(position, space="world")
    return trnas.matrix


def ray_point(polygon, matrix, direction, point):
    dag_path = MDagPath()
    selection = MSelectionList()
    selection.add(polygon.name())
    selection.getDagPath(0, dag_path)
    fn_mesh = MFnMesh(dag_path)
    pm_ray_source = pm.datatypes.Point(0, 0, 0) * matrix
    pm_ray_direction = pm.datatypes.Vector(*direction) * matrix
    ray_source = MFloatPoint(*pm_ray_source)
    ray_direction = MFloatVector(*pm_ray_direction)
    hit_point = MFloatPoint()
    hit = fn_mesh.closestIntersection(ray_source, ray_direction, None, None, None, MSpace.kWorld, 10000, None, None,
                                      hit_point, None, None, None, None, None)
    if hit:
        return pm.datatypes.Point(hit_point[0], hit_point[1], hit_point[2])
    else:
        return point


def create_direction_joint(polygon, joint, i, matrix):
    direction = [[0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1], None][i]
    suffix = ["_ty_plus", "_ty_minus", "_tz_plus", "_tz_minus", "_half"][i]
    deform_joint = pm.joint(joint, n="corrective_" + joint.name()+suffix)
    deform_joint.setMatrix(matrix, ws=1)
    deform_joint.radius.set(joint.radius.get())
    if direction is None:
        point = pm.datatypes.Point(0, 0, 0.006) * matrix
    else:
        radius = pm.softSelect(q=1, ssd=1)
        point = pm.datatypes.Point(direction[0] * radius, direction[1]* radius, direction[2]* radius) * matrix
        if polygon:
            point = ray_point(polygon, matrix, direction, point)
    deform_joint.setTranslation(point, ws=1)
    return deform_joint


def find_mirror_joint(joint):
    joints = pm.ls(config.get_rl_names(joint.name().split("|")[-1].split(":")[-1]), type="joint")
    if len(joints) != 1:
        return
    return joints[0]


def create_joint(polygon, joint, directions, rotate_offset):
    matrix = joint.getMatrix(ws=1)
    if rotate_offset:
        parent_matrix = joint.getParent().getMatrix(ws=1)
        local_matrix = joint.getMatrix(ws=0)
        position, rotation = matrix_to_position_rotation(local_matrix)
        half_rotation = slerp(rotation, pm.datatypes.Quaternion(0, 0, 0, 1), 0.5)
        matrix = position_rotation_to_matrix(position, half_rotation) * parent_matrix
    deform_joints = []
    for i, direction in enumerate(directions):
        if direction:
            deform_joint = create_direction_joint(polygon, joint, i, matrix)
            deform_joints.append(deform_joint)
    return deform_joints


def world_fip_matrix(matrix):
    matrix.a01 *= -1
    matrix.a11 *= -1
    matrix.a21 *= -1
    matrix.a02 *= -1
    matrix.a12 *= -1
    matrix.a22 *= -1
    matrix.a30 *= -1
    return matrix


def mirror_joints(joints=None):
    if joints is None:
        joints = pm.ls(sl=1, type="joint")
    parent_joints = {}
    for joint in joints:
        parent = joint.getParent()
        if parent.type() != "joint":
            continue
        parent_joints.setdefault(parent, []).append(joint)
    for parent, children in parent_joints.items():
        mirror_parent = find_mirror_joint(parent)
        if not mirror_parent:
            continue
        for child in children:
            name = child.name().replace(parent.name(), mirror_parent.name())
            if "_plus" in name:
                name = name.replace("_plus", "_minus")
            elif "_minus" in name:
                name = name.replace("_minus", "_plus")
            if name == child.name():
                name = child.name()+"_mirror"
            if pm.ls(name, type="joint"):
                mirror_joint = pm.ls(name, type="joint")[0]
            else:
                mirror_joint = pm.joint(mirror_parent, name=name)
            mirror_joint.radius.set(child.radius.get())
            mirror_joint.setMatrix(world_fip_matrix(child.getMatrix(ws=1)), ws=1)


def mirror_selected_joints():
    src, dst = pm.selected(type="joint")
    src.setMatrix(world_fip_matrix(dst.getMatrix(ws=1)), ws=1)


def create_joints(polygon, joints, directions, rotate_offset, mirror):
    deform_joints = []
    for joint in joints:
        deform_joints += create_joint(polygon, joint, directions, rotate_offset)
    if mirror:
        mirror_joints(deform_joints)


def create_attach(prefix, parent, i, pl):
    msa = pm.group(em=1, p=parent, n=prefix+"Attach")
    pm.createNode("cMuscleSurfAttach", p=msa, n=prefix+"AttachShape")
    pl.worldMesh.connect(msa.surfIn)
    msa.rotateOrder.connect(msa.inRotOrder)
    msa.outTranslate.connect(msa.translate)
    msa.outRotate.connect(msa.rotate)
    msa.edgeIdx1.set(i * 4 + 0)
    msa.edgeIdx2.set(i * 4 + 3)
    msa.uLoc.set(0.5)
    msa.vLoc.set(0.5)
    return msa


def create_plane(name, parent, transforms, r):
    u"""
    :param name: 前缀
    :param parent: 父对象
    :param transforms: 空组
    :param r: 半径
    :return: 面片模型
    """
    pl = pm.polyPlane(w=1, h=1, sx=1, sy=1, ch=1)[0]
    pl.r.set(90, 0, 90)
    pl.s.set(r, r, r)
    pm.makeIdentity(apply=1, r=1, s=1)
    planes = []
    for transform in transforms:
        dup = pl.duplicate()[0]
        dup.setMatrix(transform.getMatrix(ws=1), ws=1)
        planes.append(dup)
    pm.delete(pl)
    if len(planes) > 1:
        pl = pm.polyUnite(planes, ch=0)[0]
    else:
        pl = planes[0]
        pm.makeIdentity(pl, apply=1, t=1, r=1, s=1)
    pl.setParent(parent)
    pl.rename(name)
    pl.v.set(0)
    return pl


def sdk_group():
    if pm.objExists("PlaneSdkSystem"):
        group = pm.PyNode("PlaneSdkSystem")
    else:
        group = pm.group(em=1, n="PlaneSdkSystem")
    group.inheritsTransform.set(0)
    return group


def action_group():
    if pm.objExists("PlaneSdkAttaches"):
        group = pm.PyNode("PlaneSdkAttaches")
    else:
        group = pm.group(em=1, n="PlaneSdkAttaches", p=sdk_group())
    group.inheritsTransform.set(0)
    return group


def get_shape(polygon):
    for shape in polygon.getShapes():
        if not shape.io.get():
            return shape


def assert_geometry(geometry=None, shape_type="mesh"):
    u"""
    :param geometry: 几何体
    :param shape_type: 形节点类型
    :return:
    判断物体是否为集合体
    """
    if geometry is None:
        selected = pm.selected(o=1)
        if len(selected) == 0:
            return pm.warning("please select a " + shape_type)
        geometry = selected[0]
    if geometry.type() == shape_type:
        return geometry.getParent()
    if geometry.type() != "transform":
        return pm.warning("please select a " + shape_type)
    shape = get_shape(geometry)
    if not shape:
        return pm.warning("please select a " + shape_type)
    if shape.type() != shape_type:
        return pm.warning("please select a " + shape_type)
    return geometry


def get_skin_cluster(polygon=None):
    u"""
    :param polygon: 多边形
    :return: 蒙皮节点
    """
    if polygon is None:
        polygon = assert_geometry(shape_type="mesh")
    if polygon is None:
        return
    for history in polygon.history(type="skinCluster"):
        return history
    pm.warning("\ncan not find skinCluster")


def get_weight_data(polygon):
    polygon = assert_geometry(polygon, shape_type="mesh")
    if polygon is None:
        return
    sk = get_skin_cluster(polygon)
    joints = sk.getInfluence()
    indices = MIntArray()
    indices.setLength(len(joints))
    for i, _ in enumerate(joints):
        indices[i] = i
    selected = MSelectionList()
    selected.add(sk.name())
    selected.add(get_shape(polygon).name()+".vtx[*]")
    depend_node = MObject()
    selected.getDependNode(0, depend_node)
    fn_skin = MFnSkinCluster(depend_node)
    path = MDagPath()
    components = MObject()
    weights = MDoubleArray()
    selected.getDagPath(1, path, components)
    fn_skin.getWeights(path, components, indices, weights)
    return weights, len(joints), polygon.getShape().numVertices()


def set_weight_data(polygon=None, weights=None):
    polygon = assert_geometry(polygon, shape_type="mesh")
    if polygon is None:
        return pm.warning("can not find polygon")
    sk = get_skin_cluster(polygon)
    joints = sk.getInfluence()
    indices = MIntArray()
    indices.setLength(len(joints))
    for i, _ in enumerate(joints):
        indices[i] = i
    selected = MSelectionList()
    selected.add(sk.name())
    selected.add(get_shape(polygon).name()+".vtx[*]")
    depend_node = MObject()
    selected.getDependNode(0, depend_node)
    fn_skin = MFnSkinCluster(depend_node)
    path = MDagPath()
    components = MObject()
    selected.getDagPath(1, path, components)
    fn_skin.setWeights(path, components, indices, weights)


def init_plane_weights(plane=None):
    weights, joint_len, vtx_len = get_weight_data(plane)
    for face_id in range(vtx_len/4):
        for joint_id in range(joint_len):
            sum_weights = 0.0
            for i in range(4):
                vtx_id = face_id * 4 + i
                weight_id = vtx_id * joint_len + joint_id
                weight = weights[weight_id]
                sum_weights += weight
            weight = sum_weights / 4.0
            for i in range(4):
                vtx_id = face_id * 4 + i
                weight_id = vtx_id * joint_len + joint_id
                weights[weight_id] = weight
    set_weight_data(plane, weights)


def half_plane_skin(plane):
    weights, joint_len, vtx_len = get_weight_data(plane)
    for face_id in range(int(vtx_len / 4)):
        for joint_id in range(joint_len):
            for i in range(4):
                vtx_id = face_id * 4 + i
                weight_id = vtx_id * joint_len + joint_id
                weights[weight_id] = 0.5
    set_weight_data(plane, weights)

# ---------plane------------


def is_polygon(polygon_name):
    if not cmds.objExists(polygon_name):
        return False
    if cmds.objectType(polygon_name) != "transform":
        return False
    shapes = cmds.listRelatives(polygon_name, s=1)
    if not shapes:
        return False
    if cmds.objectType(shapes[0]) != "mesh":
        return False
    return True


def get_plane_bs_driver_data(plane):
    bs = bs_api.get_bs(plane)
    data = []
    for target_name in bs.weight.elements():
        inputs = bs.attr(target_name).inputs(p=1)
        if len(inputs) != 1:
            continue
        data.append(dict(
            target_name=target_name,
            input_attr=inputs[0].name()
        ))
    return data


def set_plane_bs_drive(plane, target_name, input_attr):
    bs = bs_api.get_bs(plane)
    if not bs.hasAttr(target_name):
        return
    if bs.attr(target_name).inputs():
        return
    pm.connectAttr(input_attr, bs.attr(target_name))


def set_plane_bs_driver_data(plane, data):
    bs = bs_api.get_bs(plane)
    for row in data:
        set_plane_bs_drive(bs, **row)
    return data


def get_plane_bs_target_data(plane):
    bs = bs_api.get_bs(plane)
    return bs_api.get_blend_shape_data(plane, bs.weight.elements())


def set_plane_bs_target_data(plane, data):
    for row in data:
        bs_api.add_target(plane, row["target_name"])
    bs_api.set_blend_shape_data(plane, data)


def get_plane_weight_data(plane):
    from .sdr_lib import api_core as _api_core
    weights = _api_core.get_py_weights(plane.name())
    joints = cmds.skinCluster(get_skin_cluster(plane).name(), q=1, influence=1)
    return dict(
        weights=weights,
        joints=joints
    )


def set_plane_skin_data(plane, joints, weights):
    pm.skinCluster(joints, plane, tsb=1)
    from .sdr_lib import api_core as _api_core
    _api_core.set_py_weights(plane.name(), weights)


def get_plane_attach_data(plane):
    attaches = plane.getShape().worldMesh[0].outputs(type="cMuscleSurfAttach")
    data = []
    for att in attaches:
        data.append(dict(
            name=att.name(),
            edgeIdx1=att.edgeIdx1.get(),
            edgeIdx2=att.edgeIdx1.get()
        ))
    return data


def set_plane_attach_data(plane, name, edgeIdx1, edgeIdx2):
    att = pm.PyNode(name)
    plane.getShape().worldMesh[0].connect(att.surfIn, f=1)
    att.edgeIdx1.set(edgeIdx1)
    att.edgeIdx2.set(edgeIdx2)


def get_face_target_data(i, target_name, ids, points):
    current_ids, current_points = [], []
    for current_id, current_point in zip(ids, points):
        if i != current_id // 4:
            continue
        current_id -= i * 4
        current_ids.append(current_id)
        current_points.append(current_point)
    return dict(
        ids=current_ids,
        points=current_points,
        target_name=target_name
    )


def get_face_attach_data(i, attach):
    data = []
    for row in attach:
        if row["edgeIdx1"]//4 != i:
            continue
        data.append(dict(
            name=row["name"],
            edgeIdx1=0,
            edgeIdx2=3
        ))
    return data


def get_face_weights(i, joints, weights):
    return dict(
        joints=joints,
        weights=weights[i*4:i*4+4]
    )


def get_face_data(i, weights, driver, target, attach):
    weights = get_face_weights(i, **weights)
    target = [get_face_target_data(i, **row) for row in target]
    attach = get_face_attach_data(i, attach)
    return dict(
        weights=weights,
        driver=driver,
        target=target,
        attach=attach
    )


def get_split_data(plane_data):
    plane_count = len(plane_data["weights"]["weights"])/4
    return [get_face_data(i, **plane_data) for i in range(plane_count)]


def get_plane_data(plane):
    return dict(
        weights=get_plane_weight_data(plane),
        driver=get_plane_bs_driver_data(plane),
        target=get_plane_bs_target_data(plane),
        attach=get_plane_attach_data(plane)
    )


def set_plane_data(plane, weights, driver, target, attach):
    set_plane_skin_data(plane, **weights)
    set_plane_bs_target_data(plane, target)
    set_plane_bs_driver_data(plane, driver)
    for row in attach:
        set_plane_attach_data(plane, **row)


def split_plane():
    # comb blend shape
    plane = pm.PyNode("BodyDeformSdkPlane")
    planes = pm.polySeparate(pm.duplicate(plane)[0], ch=0)
    data = get_plane_data(plane)
    split_data = get_split_data(data)
    for face_plane, face_data in zip(planes, split_data):
        set_plane_data(face_plane, **face_data)


def remove_drive_by_selected():
    joints = pm.selected(type="joint")
    # joints = [pm.PyNode("corrective_ElbowPart2_L_02_sdr")]
    attaches = []
    for joint in joints:
        for pc in joint.tx.inputs(type="parentConstraint"):
            for att in pc.target[0].targetTranslate.inputs(type="transform"):
                if att.name() in attaches:
                    continue
                attaches.append(att.name())
    plane = pm.PyNode("BodyDeformSdkPlane")
    dup_plane = pm.duplicate(plane)[0]
    planes = pm.polySeparate(dup_plane, ch=0)
    data = get_plane_data(plane)
    split_data = get_split_data(data)
    new_planes = []
    for face_plane, face_data in zip(planes, split_data):
        attach = face_data["attach"]
        if not attach:
            continue
        if attach[0]["name"] in attaches:
            continue
        new_planes.append(face_plane)
        set_plane_data(face_plane, **face_data)
    pm.delete(attaches)
    pm.delete(plane)
    if len(new_planes) == 0:
        pm.delete(dup_plane)
        return
    if len(new_planes) == 1:
        new_plane = new_planes[0]
    else:
        new_plane = comb_plane_dk(new_planes)
    pm.delete(dup_plane)
    new_plane.setParent("PlaneSdkSystem")
    new_plane.rename("BodyDeformSdkPlane")
    create_target_plane(new_plane)


def comb_plane_dk(planes=None):
    if len(planes) <= 1:
        return pm.warning("can not find plane")
    group = sdk_group()
    # combine planes
    dup_pls = []
    for polygon in planes:
        dup = polygon.duplicate()[0]
        for s in dup.getShapes():
            if s.io.get():
                pm.delete(s)
        dup.setParent(w=1)
        dup_pls.append(dup)
    combine_polygon = pm.polyUnite(dup_pls, ch=0)[0]
    combine_polygon.setParent(group)
    combine_polygon.v.set(0)
    # comb blend shape
    bs_names = []
    bs_inputs = []
    for pl in planes:
        bs = bs_api.get_bs(pl)
        for name in bs.weight.elements():
            if name in bs_names:
                continue
            bs_names.append(name)
            inputs = bs.attr(name).inputs(p=1)
            if len(inputs) == 1:
                bs_inputs.append(inputs[0])
            else:
                bs_inputs.append(None)

    for index, name in enumerate(bs_names):
        ids = MIntArray()
        points = MPointArray()
        count = 0
        for pl in planes:
            _ids, _points = bs_api.get_bs_ids_points(pl, name)
            for i in range(_ids.length()):
                ids.append(_ids[i]+count)
            for i in range(_points.length()):
                points.append(_points[i])
            count += pl.getShape().numEdges()
        bs_api.add_target(combine_polygon, name)
        bs_api.set_bs_ids_points(combine_polygon, name, ids, points)
        attr = bs_inputs[index]
        if attr is None:
            continue
        bs_api.bridge_connect(attr, combine_polygon)
    # replace attach
    count = 0
    for pl in planes:
        attaches = pl.getShape().worldMesh[0].outputs(type="cMuscleSurfAttach")
        for att in attaches:
            combine_polygon.getShape().worldMesh[0].connect(att.surfIn, f=1)
            att.edgeIdx1.set(att.edgeIdx1.get() + count)
            att.edgeIdx2.set(att.edgeIdx2.get() + count)
        count += pl.getShape().numVertices()
    # comb weights
    joints = []
    for polygon in planes:
        sks = polygon.getShape().inputs(type="skinCluster")
        if sks:
            sk = sks[0]

            influences = sk.influenceObjects()
            for jnt in influences:
                if jnt not in joints:
                    joints.append(jnt)
    if not joints:
        return
    combine_sk = pm.skinCluster(joints, combine_polygon, tsb=1)
    weights = []
    for polygon in planes:
        sks = polygon.getShape().inputs(type="skinCluster")
        number = polygon.getShape().numVertices()
        wts = []
        if sks:
            sk = sks[-1]
        else:
            sk = None
        for jnt in joints:
            if sk is None:
                if jnt.name().split("|")[-1] == "StaticSkin":
                    wts.append([1.0] * number)
                else:
                    wts.append([0.0] * number)
            else:
                influences = sk.influenceObjects()
                if jnt in influences:
                    wts.append(list(sk.getWeights(sk.getGeometry()[0], influences.index(jnt))))
                else:
                    wts.append([0.0] * number)
        weights.extend([w for ws in zip(*wts) for w in ws])
    combine_sk.setWeights(combine_sk.getGeometry()[0], range(len(joints)), weights)
    # comb bs
    name = planes[0].name()
    pm.delete(planes)
    combine_polygon.rename(name)
    return combine_polygon


def create_plane_by_joints(joints):
    group = sdk_group()
    skins = []
    for joint in joints:
        skin = joint.getParent()
        if skin.type() != "joint":
            continue
        if skin not in skins:
            skins.append(skin)
        skin = skin.getParent()
        if skin.type() != "joint":
            continue
        if skin not in skins:
            skins.append(skin)
    plane = create_plane("Temp_PL", group, joints, 0.1)
    _attach_group = action_group()
    for i, joint in enumerate(joints):
        attach = create_attach(joint.name()+"Attach", _attach_group, i, plane)
        attach.v.set(0)
        pm.parent(pm.parentConstraint(attach, joint), attach)
    pm.skinCluster(skins, plane, tsb=1, mi=2)
    if len(skins) == 2:
        half_plane_skin(plane)
    return plane


def create_plane_by_selected():
    joints = pm.selected(type="joint")
    skin_joints = {}
    for joint in joints:
        if joint.tx.inputs(type="parentConstraint"):
            continue
        skin = joint.getParent()
        if skin.type() != "joint":
            continue
        skin_joints.setdefault(skin, []).append(joint)
    planes = []
    for joints in skin_joints.values():
        plane = create_plane_by_joints(joints)
        planes.append(plane)
    if pm.objExists("BodyDeformSdkPlane"):
        planes.insert(0, pm.PyNode("BodyDeformSdkPlane"))
    else:
        planes[0].rename("BodyDeformSdkPlane")
    if len(planes) > 1:
        plane = comb_plane_dk(planes)
    else:
        plane = planes[0]
    create_target_plane(plane)


def create_target_plane(plane):
    attaches = []
    for attach in plane.getShape().outputs(type="cMuscleSurfAttach"):
        attaches.append(attach)

    def key(_attach):
        return _attach.edgeIdx1.get()

    attaches = list(sorted(attaches, key=key))
    joints = []
    for attach in attaches:
        joint = attach.t.outputs(type="parentConstraint")[0].constraintTranslateX.outputs(type="joint")[0]
        joints.append(joint)
    group = sdk_group()
    if pm.objExists("*|PlaneSdkSystem|BodyDeformSdkTarget"):
        pm.delete("*|PlaneSdkSystem|BodyDeformSdkTarget")
    target = create_plane("BodyDeformSdkTarget", group, joints, 0.1)
    skin = pm.skinCluster(joints, target, mi=1, tsb=1)
    target.inheritsTransform.set(0)
    wts = []
    for i in range(len(joints)):
        for j in range(4):
            for k in range(len(joints)):
                if i == k:
                    wts.append(1)
                else:
                    wts.append(0)
    skin.setWeights(skin.getGeometry()[0], range(len(joints)),  wts)


def create_joint_test():
    polygon = pm.PyNode("body")
    joints = [pm.PyNode("Wrist_L")]
    directions = [True, True, True, True, False]
    rotate_offset = True
    mirror = True
    create_joints(polygon, joints, directions, rotate_offset, mirror)


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
        parents = pm.ls(self.parents.get_joints(), type="joint")

        directions = [check.isChecked() for check in self.directions]
        rotate_offset = self.kwargs[0].isChecked()
        mirror = self.kwargs[1].isChecked()
        create_joints(polygon, parents, directions, rotate_offset, mirror)


def body_deform_sdk(joints=None):
    target = pm.ls("*|PlaneSdkSystem|BodyDeformSdkTarget", type="transform")
    driver = pm.ls("*|PlaneSdkSystem|BodyDeformSdkPlane", type="transform")
    if len(target) != 1:
        return pm.warning("can not find target")
    if len(driver) != 1:
        return pm.warning("can not find driver")
    driven_joints = find_driven_joints()
    scales = [joint.scale.get() for joint in driven_joints]
    temp = target[0].duplicate()[0]
    pm.select(temp, driver[0])
    driver_attr = ADPose.ADPoses.auto_edit_by_selected_target(joints)
    for joint, scale in zip(driven_joints, scales):
        joint.scale.set(scale)
        edit_weight_blend(driver_attr, joint.sx)
        joint.scale.set(scale)
        edit_weight_blend(driver_attr, joint.sy)
        joint.scale.set(scale)
        edit_weight_blend(driver_attr, joint.sz)


def edit_weight_blend(driver_attr, driven_attr):
    new_value = driven_attr.get()
    # remove old sdk
    inputs = driven_attr.inputs()
    if inputs:
        bt = inputs[0]
        for i in range(bt.input.numElements()):
            input_attr = bt.input.elementByPhysicalIndex(i)
            if driver_attr in input_attr.inputs(p=1):
                index = input_attr.logicalIndex()
                pm.removeMultiInstance(bt.weight[index], b=1)
                pm.removeMultiInstance(bt.input[index], b=1)
        if not bt.inputs():
            pm.delete(bt)
    # get old value
    inputs = driven_attr.inputs()
    if inputs:
        pm.dgdirty(inputs[0])
        old_value = driven_attr.get()
    else:
        old_value = 1
    # sdk
    edit_value = new_value - old_value
    if abs(edit_value) < 0.0001:
        return
    if inputs:
        bt = inputs[0]
    else:
        bt = pm.createNode("blendWeighted", n=driven_attr.name(includeNode=False))
        bt.output.connect(driven_attr)
        bt.weight[0].set(1)
        bt.input[0].set(1)
    ids = [bt.input.elementByPhysicalIndex(i).logicalIndex() for i in range(bt.input.numElements())]
    index = 0
    while True:
        index += 1
        if index not in ids:
            break
    driver_attr.connect(bt.input[index])
    bt.weight[index].set(edit_value)
    pm.dgdirty(bt)


def create_fk(joint, fk=None):
    link_joints = pm.listRelatives(joint)
    if joint.getParent():
        link_joints.append(joint.getParent())
    p = joint.getTranslation(space="world")
    if link_joints:
        lengths = [(p-jnt.getTranslation(space="world")).length() for jnt in link_joints]
        r = sum(lengths)/len(lengths) * 0.7
    else:
        r = 1
    n = joint.name().split("|")[-1]
    group = pm.group(em=1, p=fk, n="Zero"+n)
    fk = pm.circle(ch=0, nr=[1, 0, 0])[0]
    fk.rename("FK"+n)
    fk.setParent(group)
    fk.t.set(0, 0, 0)
    fk.r.set(0, 0, 0)
    fk.s.set(r, r, r)
    group.setMatrix(joint.getMatrix(ws=1), ws=1)
    group.s.set(1, 1, 1)
    pm.makeIdentity(fk, s=1, apply=1)
    shape = fk.getShape()
    shape.overrideEnabled.set(True)
    shape.overrideColor.set(17)
    pm.parent(pm.parentConstraint(fk, joint, mo=1), fk)
    for child in pm.listRelatives(joint, type="joint"):
        create_fk(child, fk)


def create_temp_fk():
    joints = pm.ls(sl=1, type="joint")
    if len(joints) != 1:
        return pm.warning("please selected one root joint")
    joint = joints[0]
    pm.delete(pm.ls("|ADPOseTempFK"))
    fk = pm.group(em=1, n="ADPOseTempFK")
    create_fk(joint, fk)


def create_node(typ, n):
    if pm.objExists(n):
        # 防止引用的情况发生
        node = pm.PyNode(n)
        if node.isReferenced():
            return create_node(typ, n+"_reference")
        pm.delete(node)
    return pm.createNode(typ, n=n)


def create_offset_prod(driver, driven, prefix):
    dpm = create_node("decomposeMatrix", prefix + "_DPM")
    driver.worldMatrix[0].connect(dpm.inputMatrix)
    matrix = driven.getMatrix(ws=1) * driver.getMatrix(ws=1).inverse()
    qua = pm.datatypes.TransformationMatrix(matrix).getRotationQuaternion()
    prod = create_node("quatProd", prefix+"_prod")
    prod.input1Quat.set(*qua)
    dpm.outputQuat.connect(prod.input2Quat)
    return prod


def create_half_joint(driver_a, driver_b, driven):
    prefix = driven.name()
    prod_a = create_offset_prod(driver_a, driven, prefix+"_A")
    prod_b = create_offset_prod(driver_b, driven, prefix+"_B")

    qua_blend = create_node("quatSlerp", prefix + "_blend")
    prod_a.outputQuat.connect(qua_blend.input1Quat)
    prod_b.outputQuat.connect(qua_blend.input2Quat)
    qua_blend.inputT.set(0.5)

    parent_inverse = create_node("decomposeMatrix", prefix + "_ParentInverse_DPM")
    driven.parentInverseMatrix[0].connect(parent_inverse.inputMatrix)

    prod = create_node("quatProd", prefix+"_prod")
    qua_blend.outputQuat.connect(prod.input1Quat)
    parent_inverse.outputQuat.connect(prod.input2Quat)

    euler = create_node("quatToEuler", prefix + "_euler")
    prod.outputQuat.connect(euler.inputQuat)
    euler.inputRotateOrder.set(driven.rotateOrder.get())
    euler.outputRotate.connect(driven.rotate)


def tool_create_half_joint():
    create_half_joint(*pm.ls(sl=1, type="joint"))


def find_driven_joints():
    groups = pm.ls("PlaneSdkSystem|PlaneSdkAttaches")
    if not len(groups) == 1:
        return []
    group = groups[0]
    joints = []
    for att in group.listRelatives(ad=1, type="cMuscleSurfAttach"):
        for pc in att.getParent().t.outputs(type="parentConstraint"):
            for jnt in pc.constraintTranslateX.outputs(type="joint"):
                if jnt not in joints:
                    joints.append(jnt)
    return joints

