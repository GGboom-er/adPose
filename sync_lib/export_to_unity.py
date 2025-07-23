# coding:utf-8
from maya.api.OpenMaya import *
from ..general_ui import *
from .. import ADPose
from .. import twist


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


def get_unity_name(node):
    return node.fullPath()[1:].replace("|", "/")


def maya_matrix_to_unity_qua(matrix):
    matrix[1] *= -1
    matrix[2] *= -1
    matrix[4] *= -1
    matrix[8] *= -1
    r = MTransformationMatrix(matrix).rotation(asQuaternion=True)
    return dict(x=r.x, y=r.y, z=r.z, w=r.w)


def get_unity_rotation(joint):
    return maya_matrix_to_unity_qua(MMatrix(pm.xform(joint, q=True, m=True, os=True, ws=False)))


def get_unity_position(joint):
    t = pm.xform(joint, q=True, t=True)
    return dict(x=-t[0]*0.01, y=t[1]*0.01, z=t[2]*0.01)


def get_unity_bind_pose(joint):
    return dict(
        name=get_unity_name(joint),
        position=get_unity_position(joint),
        rotation=get_unity_rotation(joint)
    )


def get_unity_rotation_additive(base, target):
    if sum([base[i]*target[i] for i in "xyzw"]) < 0:
        target = {i: -target[i] for i in "xyzw"}
    return {i: target[i] - base[i] for i in "xyzw"}


def get_unity_position_additive(base, target):
    return {i: target[i] - base[i] for i in "xyz"}


def get_direction_sdk_data(current_direction, directions):
    u"""
    @param current_direction: 当前驱动的pose的方向
    @param directions:所有pose的方向
    @return: 返回驱动pose方向的驱动关键帧数据
    当旋转到当前驱动的pose的方向时，驱动数值为1，当旋转到其它pose方向时，驱动数值为0
    以current_direction为90为例，驱动数据一般如下
    time 0   value 0
    time 90  value 1
    time 180 value 0
    """
    # 偏离前驱动pose方向超过90度，数值归零，因此假定正负90度的位置，也有pose
    directions = list(directions) + [current_direction-90, current_direction, current_direction+90]
    # 0-360为一圈， 359度到1度之间的驱动，应写成-1到1和359到361，因此所有数值正负各加360以应对边界的驱动
    directions = [base + offset for base in directions for offset in [-360, 0, 360]]
    directions = list(sorted(set(directions)))
    # 当旋转到当前驱动的pose的方向时，驱动数值为1，当旋转到其它pose方向时，驱动数值为0
    times = []
    values = []
    for offset in [-360, 0, 360]:
        index = directions.index(current_direction+offset)
        times.extend([directions[index-1], directions[index], directions[index+1]])
        values.extend([0, 1, 0])
    # 移除首位连续两个连续两个不在0-360之间驱动值
    for i in range(6):
        if times[1] <= 0:
            times.pop(0)
            values.pop(0)
        if times[-2] >= 360:
            times.pop(-1)
            values.pop(-1)
    # 若首尾驱动值不在0-360之间，计算0和360的驱动值
    if (times[0] < 0) and (times[1] > 0):
        t1, v1 = times[0], values[0]
        t2, v2 = times[1], values[1]
        t = 0.0
        v = v1 + (v2-v1) * (t-t1)/(t2-t1)
        times[0] = 0
        values[0] = v
    if (times[-1] > 360) and (times[-2] < 360):
        t1, v1 = times[-2], values[-2]
        t2, v2 = times[-1], values[-1]
        t = 360.0
        v = v1 + (v2-v1) * (t-t1)/(t2-t1)
        times[-1] = 360
        values[-1] = v
    return times, values


def get_angle_sdk_data(a, _as):
    _as = list(sorted(set(_as+[0, 180])))
    i = _as.index(a)
    times = [_as[i + j] for j in [-1, 0, 1]]
    values = [0, 1, 0]
    if times[-1] == 180:
        values[-1] = 1
    return times, values


def target_to_element_targets(target_name):
    if ADPose.target_is_pose(target_name):
        return [target_name]
    elif ADPose.target_is_comb(target_name):
        return target_name.split("_COMB_") + [target_name]
    elif ADPose.target_is_ib(target_name):
        return target_name[:-5].split("_COMB_") + [target_name]
    else:
        return [target_name]


def get_pose(data, target_name):
    pm.refresh()
    additives = []
    for joint_id, bind_pose in enumerate(data["bind_poses"]):
        joint = pm.ls(bind_pose["name"].replace("/", "|"))[0]
        rotation = get_unity_rotation_additive(bind_pose["rotation"], get_unity_rotation(joint))
        position = get_unity_position_additive(bind_pose["position"], get_unity_position(joint))
        if all(map(lambda x: abs(x) < 0.0001, position.values() + rotation.values())):
            continue
        additives.append(dict(position=position, rotation=rotation, joint_id=joint_id))
    targets = []
    for mesh_id, name in enumerate(data["polygons"]):
        polygon = pm.ls(name.replace("/", "|"))[0]
        bs = polygon.listHistory(type="blendShape")
        if not bs:
            continue
        bs = bs[0]
        if not bs.hasAttr(target_name):
            continue
        for elem_target_name in target_to_element_targets(target_name):
            target_id = bs.weight.elements().index(elem_target_name)
            value = bs.attr(elem_target_name).get()
            if value < 0.0001:
                continue
            targets.append(dict(
                target_id=target_id,
                mesh_id=mesh_id,
                value=value,
            ))

    pose_id = len(data["driven_poses"])
    data["driven_poses"].append(dict(
        targets=targets,
        additives=additives,
        name=target_name,
    ))
    return pose_id


def sub_additive(additive_a, additive_b):
    dict_a = additives_to_dict(additive_a)
    dict_b = additives_to_dict(additive_b)
    ids = list(sorted(set(dict_b.keys() + dict_b.keys())))
    additives = []
    for joint_id in ids:
        rotation_a = dict_a.get(joint_id, dict()).get("rotation", dict(x=0, y=0, z=0, w=0))
        rotation_b = dict_b.get(joint_id, dict()).get("rotation", dict(x=0, y=0, z=0, w=0))
        rotation = get_unity_rotation_additive(rotation_a, rotation_b)
        position_a = dict_a.get(joint_id, dict()).get("position", dict(x=0, y=0, z=0))
        position_b = dict_b.get(joint_id, dict()).get("position", dict(x=0, y=0, z=0))
        position = get_unity_position_additive(position_a, position_b)
        if all(map(lambda x: abs(x) < 0.0001, position.values() + rotation.values())):
            continue
        additives.append(dict(position=position, rotation=rotation, joint_id=joint_id))
    return additives


def get_angle_directions(data, joint):
    if not joint.hasAttr("angle"):
        return []
    if not joint.hasAttr("direction"):
        return []
    ad = ADPose.ADPoses.load_by_name(joint.name())
    if ad is None:
        return []
    poses = ad.get_poses()
    if not poses:
        return []
    ad = ADPose.ADPoses.load_by_name(joint.name())
    direction_angles = {}
    poses = ad.get_poses()
    for angle, direction in poses:
        direction_angles.setdefault(direction, []).append(angle)
    for direction, angles in direction_angles.items():
        direction_angles[direction] = list(sorted(angles))
    directions = sorted(direction_angles.keys())
    driver_data = []
    for direction in directions:
        direction_tvs = [dict(time=t, value=v) for t, v in zip(*get_direction_sdk_data(direction, directions))]
        if direction == 360:
            direction = 0
        angles = direction_angles[direction]
        for angle in angles:
            angle_tvs = [dict(time=t, value=v) for t, v in zip(*get_angle_sdk_data(angle, angles))]
            ad.control.setMatrix(ADPose.pose_to_matrix((angle, direction)))
            name = ad.target_name((angle, direction))
            pose_id = get_pose(data, name)
            driver_data.append(dict(
                pose_id=pose_id,
                direction_curve=direction_tvs,
                angle_curve=angle_tvs
            ))
    ad.control.r.set(0, 0, 0)
    return driver_data


def get_twist_driver_data(data, joint):
    if not joint.hasAttr("twistX"):
        return []
    tw = twist.Twist(joint=joint)
    values = tw.get_values()
    sort_values = sorted(values + [-180.0, 0, 180.0])
    driver_data = []
    for value in values:
        if value in [-180.0, 0, 180.0]:
            continue
        name = tw.value_to_target_name(value)
        i = sort_values.index(value)
        twist_curve = [dict(time=sort_values[i+j-1], value=[0, 1, 0][j]) for j in range(3)]
        if sort_values[i - 1] == -180.0:
            twist_curve[0]["value"] = 1
        if sort_values[i + 1] == 180.0:
            twist_curve[2]["value"] = 1
        tw.to_target(name, 60)
        pose_id = get_pose(data, name)
        driver_data.append(dict(
            pose_id=pose_id,
            twist_curve=twist_curve
        ))
    tw.ctrl.r.set(0, 0, 0)
    return driver_data


def get_driver_joint_data(data, joint):
    angle_directions = get_angle_directions(data, joint)
    twists = get_twist_driver_data(data, joint)
    if not (angle_directions or twists):
        return
    data["limb_drives"].append(dict(
        name=get_unity_name(joint),
        rotation=get_unity_rotation(joint),
        angle_directions=angle_directions,
        twists=twists
    ))


def find_pose_id_by_name(data, name):
    for i, row in enumerate(data["driven_poses"]):
        if row["name"] == name:
            return i


def additives_to_dict(additives):
    return {additive["joint_id"]: additive for additive in additives}


def get_combine_data(data, comb_target_name):
    driver_target_names = comb_target_name.split("_COMB_")
    driver_poses = []
    for driver_target_name in driver_target_names:
        driver_pose_id = find_pose_id_by_name(data, driver_target_name)
        if driver_pose_id is None:
            return
        driver_poses.append(driver_pose_id)
    ADPose.ADPoses.set_pose_by_targets([comb_target_name], [], 60)
    pose_id = get_pose(data, comb_target_name)
    ADPose.ADPoses.set_pose_by_targets([comb_target_name], [], 0)
    return dict(
        driver_poses=driver_poses,
        pose_id=pose_id,
    )


def get_all_combine_data(data):
    target_names = ADPose.ADPoses.get_targets()
    comb_target_names = filter(ADPose.target_is_comb, target_names)
    comb_data = map(lambda x: get_combine_data(data, x), comb_target_names)
    data["combine_drives"] = list(filter(bool, comb_data))


def get_all_inbetween_data(data):
    target_names = ADPose.ADPoses.get_targets()
    comb_target_names = filter(ADPose.target_is_comb, target_names)
    inbetween_drives = []
    for comb_name in comb_target_names:
        comb_node = ADPose.find_node_by_name(comb_name)
        if comb_node is None:
            continue
        ib_target_name = dict()
        for attr in comb_node.listAttr(ud=1):
            attr_name = attr.name().split(".")[-1]
            if attr_name == comb_name:
                ib = 60
            else:
                str_ib = attr_name[len(comb_name) + 3:]
                if not str_ib.isdigit():
                    continue
                ib = int(str_ib)
            if ib == 0:
                continue
            ib_target_name[ib] = attr_name
        ibs = [0]+list(sorted(ib_target_name.keys()))
        if len(ibs) == 2:
            continue
        driver_pose = find_pose_id_by_name(data, comb_name)
        for i, ib_value in enumerate(ibs[1:-1]):
            target_name = ib_target_name[ib]
            curve = [dict(time=ibs[i+j]/60.0, value=[0, 1, 0][j]) for j in range(3)]
            ADPose.ADPoses.set_pose_by_targets([target_name], [])
            pose_id = get_pose(data, target_name)
            ADPose.ADPoses.set_pose_by_targets([target_name], [], 0)
            inbetween_drives.append(dict(
                driver_pose=driver_pose,
                inbetween_curve=curve,
                pose_id=pose_id,
            ))
        curve = [dict(time=ibs[-2] / 60.0, value=0), dict(time=ibs[-1] / 60.0, value=1)]
        inbetween_drives.append(dict(
            driver_pose=driver_pose,
            inbetween_curve=curve,
            pose_id=driver_pose,
        ))
    data["inbetween_drives"] = inbetween_drives


def find_half_blend(euler):
    for prod in euler.inputQuat.inputs(type="quatProd"):
        for blend in prod.input1Quat.inputs(type="quatSlerp"):
            return blend


def find_half_driver(attr):
    for prod in attr.inputs(type="quatProd"):
        for dpm in prod.input2Quat.inputs(type="decomposeMatrix"):
            for joint in dpm.inputMatrix.inputs(type="joint"):
                return joint


def get_half_follows():
    data = []
    for driven in pm.ls(type="joint"):
        euler_list = driven.rotate.inputs(type="quatToEuler")
        if not euler_list:
            continue
        euler = euler_list[0]
        if not euler.name().endswith("euler"):
            continue
        blend = find_half_blend(euler)
        if blend is None:
            continue
        driver_a = find_half_driver(blend.input1Quat)
        driver_b = find_half_driver(blend.input2Quat)
        if driver_a is None:
            continue
        if driver_b is None:
            continue
        offset_a = driven.getMatrix(ws=1) * driver_a.getMatrix(ws=1).inverse()
        offset_b = driven.getMatrix(ws=1) * driver_b.getMatrix(ws=1).inverse()
        data.append(dict(
            driver_a=driver_a,
            driver_b=driver_b,
            offset_a=offset_a,
            offset_b=offset_b,
            driven=driven
        ))
    return data


def maya_half_follow_to_unity(driver_a, driver_b, offset_a, offset_b, driven):
    return dict(
        driver_a=get_unity_name(driver_a),
        driver_b=get_unity_name(driver_b),
        driven=get_unity_name(driven),
        offset_a=maya_matrix_to_unity_qua(MMatrix(sum(offset_a.tolist(), []))),
        offset_b=maya_matrix_to_unity_qua(MMatrix(sum(offset_b.tolist(), []))),
        rotation=get_unity_rotation(driven),
    )


def get_unity_half_follow_data():
    return [maya_half_follow_to_unity(**row) for row in get_half_follows()]


def get_unity_data(polygon_names):
    driven_joints = find_driven_joints()
    data = dict(
        polygons=map(get_unity_name, pm.ls(polygon_names)),
        bind_poses=map(get_unity_bind_pose, driven_joints),
        driven_poses=[],
        limb_drives=[],
    )
    for joint in pm.ls(type="joint"):
        get_driver_joint_data(data, joint)
    get_all_combine_data(data)
    get_all_inbetween_data(data)
    data["half_follow_drives"] = get_unity_half_follow_data()
    return data


def write_json_data(path, data):
    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(path, "w") as fp:
        json.dump(data, fp, indent=4)


def get_save_path(default_path, ext):
    path, _ = QFileDialog.getSaveFileName(get_host_app(), "Export", default_path, "{0} (*.{0})".format(ext))
    return path


def get_open_path(default_path, ext):
    path, _ = QFileDialog.getOpenFileName(get_host_app(), "Load", default_path, "{0} (*.{0})".format(ext))
    return path


class Path(QLineEdit):
    ModeOpen, ModeSave = range(2)

    def __init__(self, root, ext, mode):
        QLineEdit.__init__(self)
        self.root = root
        self.ext = ext
        self.mode = mode

    def text(self):
        text = QLineEdit.text(self)
        if u"\\" in text:
            text = text.replace(u"\\", u"/")
        elif u"/" not in text:
            path = os.path.join(self.root, text)
            if not path.endswith(self.ext):
                path = ".".join([path, self.ext])
            if os.path.isfile(path):
                text = path.replace(u"\\", u"/")
        return text

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            return event.accept()
        event.ignore()

    def dragMoveEvent(self, event):
        pass

    def dropEvent(self, event):
        path = event.mimeData().urls()[0].path()[1:]
        _, ext = os.path.splitext(path)
        if ext != self.ext:
            return
        self.setText(path)

    def mouseDoubleClickEvent(self, event):
        QLineEdit.mouseDoubleClickEvent(self, event)
        if self.mode == self.ModeOpen:
            path = get_open_path(self.root, self.ext)
        else:
            path = get_save_path(self.root, self.ext)
        if not path:
            return
        self.setText(path)


class ExportToUnityTool(Tool):

    def __init__(self, parent):
        Tool.__init__(self, parent)
        self.polygons = MayaObjLayouts(u"模型：")
        # self.joints = MayaObjLayouts(u"骨骼：")
        self.path = Path(default_scene_path(), ".json", Path.ModeSave)
        layout_adds(self.kwargs_layout, self.polygons, PrefixWeight(u"路径：", self.path))

    def apply(self):
        polygons = self.polygons.line.text().split(",")
        # joints = self.joints.line.text().split(",")
        path = self.path.text()

        data = get_unity_data(polygons)
        write_json_data(path, data)


window = None


def show():
    global window
    if window is None:
        window = ExportToUnityTool(get_host_app())
    window.show()


def test():
    mesh_names = [u"skin"]
    joint_names = [u'corrective_Wrist_L_ty_plus',
                   u'corrective_Wrist_L_ty_minus',
                   u'corrective_Wrist_L_tz_plus',
                   u'corrective_Wrist_L_tz_minus',
                   u'Scapula_L_Pose',
                   u'Shoulder_L_pose',
                   u'Shoulder_L_comb_pose',
                   u'Shoulder_L_ib_pose']
    data = get_unity_data(mesh_names)
    write_json_data("D:/unity/study01/Assets/char/aaa.json", data)



