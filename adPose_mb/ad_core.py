# coding:utf-8
u"""
一些关于
"""
from ad_base import *
from functools import partial
import re


def get_poses(direction, _max, number):
    direction_data = {
        u"+z": [0],
        u"-y": [90],
        u"-z": [180],
        u"+y": [270],
        u"4": [i for i in range(0, 360, 90)],  # [0, 90, 180,270]
        u"8": [i for i in range(0, 360, 45)],  # [0, 45, 90, 135, 180, 225, 270, 315]
    }
    poses = [[int(round(float(_max) / number * (i + 1))), d]
             for d in direction_data.get(direction, []) for i in range(number)]
    return poses


config = dict(
    Finger=get_poses("+y", 90, 1),
    Roll=get_poses("8", 90, 2),
    ShortRoll=get_poses("4", 40, 2),
    Limbs=[[45, 180], [90, 180], [120, 180], [140, 180]]
)


def point_to_angle_direction():
    NODE_W = 350
    NODE_H = 100
    delete_node_by_name("CHAR_Deformation_ADPoseAngleDirection", "Constraints")
    relation = FBConstraintRelation("CHAR_Deformation_ADPoseAngleDirection")

    in_point = relation.CreateFunctionBox('Macro Tools', 'Macro Input Vector')
    relation.SetBoxPosition(in_point, NODE_W * 0, NODE_H * 0)

    angle = relation.CreateFunctionBox('Vector', 'Angle')
    relation.SetBoxPosition(angle, NODE_W * 1, NODE_H * 0)
    set_attr(angle, "V2", [1, 0, 0])
    connect(in_point, "Input", angle, "V1")

    angle_divide = relation.CreateFunctionBox('Number', 'Divide (a/b)')
    relation.SetBoxPosition(angle_divide, NODE_W * 2, NODE_H * 0)
    set_attr(angle_divide, "b", [3.6])
    connect(angle, "Result", angle_divide, "a")

    vector_to_number = relation.CreateFunctionBox('Converters', 'Vector To Number')
    relation.SetBoxPosition(vector_to_number, NODE_W * 1, NODE_H * 1)
    connect(in_point, "Input", vector_to_number, "V")

    number_to_vector = relation.CreateFunctionBox('Converters', 'Number To Vector')
    relation.SetBoxPosition(number_to_vector, NODE_W * 2, NODE_H * 1)
    set_attr(number_to_vector, "X", [0.0])
    connect(vector_to_number, "Y", number_to_vector, "Y")
    connect(vector_to_number, "Z", number_to_vector, "Z")

    normalize = relation.CreateFunctionBox('Vector', 'Normalize')
    relation.SetBoxPosition(normalize, NODE_W * 3, NODE_H * 1)
    connect(number_to_vector, "Result", normalize, "Vector")

    direction = relation.CreateFunctionBox('Vector', 'Angle')
    relation.SetBoxPosition(direction, NODE_W * 4, NODE_H * 1)
    connect(normalize, "Result", direction, "V1")
    set_attr(direction, "V2", [0.0, 1.0, 0.0])

    sub = relation.CreateFunctionBox('Number', 'Subtract (a - b)')
    relation.SetBoxPosition(sub, NODE_W * 4, NODE_H * 2)
    set_attr(sub, "a", [360])
    connect(direction, "Result", sub, "b")

    greater = relation.CreateFunctionBox('Number', 'Is Greater (a > b)')
    relation.SetBoxPosition(greater, NODE_W * 4, NODE_H * 3)
    connect(vector_to_number, "Z", greater, "b")

    cond = relation.CreateFunctionBox('Number', 'IF Cond Then A Else B')
    relation.SetBoxPosition(cond, NODE_W * 5, NODE_H * 1)
    connect(direction, "Result", cond, "b")
    connect(sub, "Result", cond, "a")
    connect(greater, "Result", cond, "Cond")

    direction_divide = relation.CreateFunctionBox('Number', 'Divide (a/b)')
    relation.SetBoxPosition(direction_divide, NODE_W * 6, NODE_H * 1)
    connect(cond, "Result", direction_divide, "a")
    set_attr(direction_divide, "b", [3.60])

    out_angle = relation.CreateFunctionBox('Macro Tools', 'Macro Output Number')
    relation.SetBoxPosition(out_angle, NODE_W * 7, NODE_H * 0)
    connect(angle_divide, "Result", out_angle, "Output")

    out_direction = relation.CreateFunctionBox('Macro Tools', 'Macro Output Number')
    relation.SetBoxPosition(out_direction, NODE_W * 7, NODE_H * 1)
    connect(direction_divide, "Result", out_direction, "Output")
    relation.Active = True


def create_direction_sdk(relation, i, ds, d):
    NODE_W = 400
    NODE_H = 100
    ds = sorted(set(sum([[_d, _d + 360, _d - 360] for _d in ds] + [[d + 90, d - 90]], [])))
    key_value = {ds[ds.index(d) + o1] + o2 * 360: v for o1, v in zip([-1, 0, 1], [0, 1, 0]) for o2 in [-1, 0, 1]}
    key_value = [[key, key_value[key]] for key in sorted(key_value.keys())]
    for _ in range(10):
        if key_value[1][0] <= 0:
            key_value.pop(0)
        if key_value[-2][0] >= 360:
            key_value.pop(-1)
        if key_value[0][1] == key_value[1][1]:
            key_value.pop(0)
        if key_value[-1][1] == key_value[-2][1]:
            key_value.pop(-1)
    if key_value[0][0] != 0:
        key_value.insert(0, [0, key_value[0][1]])
    if key_value[-1][0] != 360:
        key_value.append([360, key_value[-1][1]])
    if (key_value[0][0] < 0) and (key_value[1][0] > 0):
        t1, v1 = key_value[0]
        t2, v2 = key_value[1]
        v = v1 + v2 * (0 - t1) / (t2 - t1)
        key_value[0][0] = 0
        key_value[0][1] = v
    if (key_value[-1][0] > 360) and (key_value[-2][0] < 360):
        t1, v1 = key_value[-2]
        t2, v2 = key_value[-1]
        v = v1 + v2 * (0 - t1) / (t2 - t1)
        key_value[-1][0] = 360
        key_value[-1][1] = v
    key_value = [[int(round(key / 3.6)), int(round(value * 100))] for key, value in key_value]
    d_sdk = create_sdk(relation, NODE_W * 2, i * NODE_H, key_value)
    return d_sdk


def create_angle_sdk(relation, i, _as, a, a_sdk_dict):
    NODE_W = 400
    NODE_H = 100
    _as = sorted(_as + [180, 0])
    key_value = [[_as[_as.index(a) + o], v] for o, v in zip([-1, 0, 1], [0, 1, 0])]
    if key_value[2][0] == 180:
        key_value[2][1] = 1
    if key_value[0][0] != 0:
        key_value.insert(0, [0, key_value[0][1]])
    if key_value[-1][0] != 360:
        key_value.append([360, key_value[-1][1]])
    keys = tuple(k for k, v in key_value)
    if keys in a_sdk_dict:
        return i, a_sdk_dict[keys]
    key_value = [[int(round(key / 3.6)), int(round(value * 100))] for key, value in key_value]
    for i in range(len(key_value)):
        if i == 0:
            pass
        else:
            if key_value[i][1] != key_value[i-1][1]:
                try:
                    sdk_key_value = key_value[i - 1:i + 2]
                except:
                    sdk_key_value = key_value[i - 1:]
                break
    a_sdk = create_driver_3d_node(relation, 2 * NODE_W, i * NODE_H, sdk_key_value)
    # a_sdk = create_sdk(relation, 2 * NODE_W, i * NODE_H, key_value)
    a_sdk_dict[keys] = a_sdk
    return i + 1, a_sdk


def create_ad_sdk_template(name, poses):
    NODE_W = 400
    NODE_H = 100
    relation_name = "ADPose{name}SdkTemplate".format(name=name)
    delete_node_by_name(relation_name, "Constraints")
    relation = FBConstraintRelation(relation_name)

    d_a_dict = {}
    for a, d in poses:
        d_a_dict.setdefault(d, []).append(a)
    ds = d_a_dict.keys()
    i = 0
    j = -1
    a_sdk_dict = {}

    in_point = relation.CreateFunctionBox('Macro Tools', 'Macro Input Vector')
    relation.SetBoxPosition(in_point, NODE_W * 0, NODE_H * 0)

    angle_direction = relation.CreateFunctionBox('My Macros', 'CHAR_Deformation_ADPoseAngleDirection')
    relation.SetBoxPosition(angle_direction, NODE_W * 1, NODE_H * 0)
    connect(in_point, 'Input', angle_direction, 'MacroInput0')

    for d, _as in d_a_dict.items():
        d_sdk = create_direction_sdk(relation, i, ds, d)
        connect(angle_direction, "MacroOutput1", d_sdk, "Position %")
        i += 1
        for a in _as:
            i, a_sdk = create_angle_sdk(relation, i, _as, a, a_sdk_dict)
            connect(angle_direction, "MacroOutput0", a_sdk, "Position %")
            j += 1
            multiply = relation.CreateFunctionBox('Number', "Multiply (a x b)")
            relation.SetBoxPosition(multiply, NODE_W * 3, NODE_H * j)
            connect(d_sdk, "Value", multiply, "a")
            connect(a_sdk, "Value", multiply, "b")

            divide = relation.CreateFunctionBox('Number', 'Divide (a/b)')
            relation.SetBoxPosition(divide, NODE_W * 4, NODE_H * j)
            connect(multiply, "Result", divide, "a")
            set_attr(divide, "b", [100.0])

            out_number = relation.CreateFunctionBox('Macro Tools', 'Macro Output Number')
            # target_name = "a{a}_d{d}".format(**locals())
            # SetMacroOutputName(out_number, target_name)
            relation.SetBoxPosition(out_number, NODE_W * 5, NODE_H * j)
            connect(divide, "Result", out_number, "Output")

    relation.Active = True


def get_rig_group():
    group = find_by_name("AdPoseRigGroup")
    if group is None:
        return FBModelNull("AdPoseRigGroup")
    return group


def create_ad_pose_local_point(joint):
    name = joint.Name
    rig_group = get_rig_group()

    rotate = find_by_name(name + "_AdPoseLocalRotate")
    if rotate is not None:
        DestroyModel(rotate)
    rotate = FBModelNull(name + "_AdPoseLocalRotate")
    rotate.PropertyList.Find("RotationOrder").Data = joint.PropertyList.Find("RotationOrder").Data
    vector = FBModelNull(name + "_AdPoseLocalVector")
    rotate.Parent = rig_group
    vector.Parent = rotate
    vector.PropertyList.Find("Lcl Translation").Data = FBVector3d(1, 0, 0)
    return rotate


def get_ad_poses(mesh_list, names):
    joint_ads = dict()
    for mesh in mesh_list:
        for attr in mesh.PropertyList:
            name = attr.Name
            match = re.match(r"^(?P<joint>\w+)_a(?P<a>[0-9]{1,3})_d(?P<d>[0-9]{1,3})$", name)
            if not match:
                continue
            group_dict = match.groupdict()
            joint = group_dict["joint"]
            if joint not in names:
                continue
            joint_ads.setdefault(group_dict["joint"], set()).add((int(group_dict["a"]), int(group_dict["d"])))
    for joint, poses in joint_ads.items():
        d_a_dict = {}
        for a, d in poses:
            d_a_dict.setdefault(d, []).append(a)
        new_poses = []
        for d in sorted(d_a_dict.keys()):
            for a in sorted(d_a_dict[d]):
                new_poses.append([a, d])
        joint_ads[joint] = new_poses
    return joint_ads


def create_rotate_link(links):
    NODE_W = 500
    NODE_H = 100
    delete_node_by_name("CHAR_Deformation_AdPoseLocalLink", "Constraints")
    relation = FBConstraintRelation("CHAR_Deformation_AdPoseLocalLink")
    i = 0
    for src, dst in links:
        src_box = relation.SetAsSource(src)
        src_box.UseGlobalTransforms = False
        relation.SetBoxPosition(src_box, NODE_W * 0, NODE_H * i)
        dst_box = relation.ConstrainObject(dst)
        dst_box.UseGlobalTransforms = False
        relation.SetBoxPosition(dst_box, NODE_W * 1, NODE_H * i)
        connect(src_box, 'Lcl Rotation', dst_box, 'Lcl Rotation')
        i += 1
    relation.Active = True


def ad_pose_pont_link():
    mesh_lists = find_all_mesh()
    name_joint = get_name_joint()
    ad_poses = get_ad_poses(mesh_lists, name_joint.keys())
    links = []
    for name in ad_poses.keys():
        joint = name_joint[name]
        vector = create_ad_pose_local_point(joint)
        links.append([joint, vector])
    create_rotate_link(links)


def open_blend_shape_anim(mesh):
    for attr in mesh.PropertyList:
        name = attr.Name
        match = re.match(r"^(?P<joint>\w+)_a(?P<a>[0-9]{1,3})_d(?P<d>[0-9]{1,3})$", name)
        if match:
            attr.SetAnimated(True)
        if name.endswith("TwistMinus"):
            attr.SetAnimated(True)
        if name.endswith("TwistPlus"):
            attr.SetAnimated(True)


def get_template_name(poses):
    for name, _poses in config.items():
        if poses == _poses:
            return "ADPose{name}SdkTemplate".format(name=name)


def ad_pose_sdk(relation, mesh_box_list, i):
    NODE_W = 400
    NODE_H = 100
    mesh_lists = find_all_mesh()
    # adPose sdk
    name_joint = get_name_joint()
    ad_poses = get_ad_poses(mesh_lists, name_joint.keys())
    for name, poses in ad_poses.items():
        if "b_LeftUpLeg" not in name:
            continue
        src_name = name + "_AdPoseLocalVector"
        src_node = find_by_name(src_name)
        if src_node is None:
            continue
        template_name = get_template_name(poses)
        if template_name is None:
            continue
        src_box = relation.SetAsSource(src_node)
        relation.SetBoxPosition(src_box, NODE_W * 0, NODE_H * i)
        template_sdk = relation.CreateFunctionBox('My Macros', template_name)
        relation.SetBoxPosition(template_sdk, NODE_W * 1, NODE_H * i)
        connect(src_box, 'Translation', template_sdk, 'MacroInput0')
        ListAnimNodeAttr(template_sdk)
        for mesh_box in mesh_box_list:
            for j, pose in enumerate(poses):
                angle, direction = pose
                target_name = "{name}_a{angle}_d{direction}".format(**locals())
                connect(template_sdk, 'MacroOutput%i' % j, mesh_box, target_name)
        i += 1
        if len(poses) > 3:
            i += 1
        if len(poses) > 4:
            i += 1
    relation.Active = True


def ad_pose_sdk2(relation, mesh_box_list, i):
    NODE_W = 400
    NODE_H = 100
    mesh_lists = find_all_mesh()
    # adPose sdk
    name_joint = get_name_joint()
    ad_poses = get_ad_poses(mesh_lists, name_joint.keys())
    for name, poses in ad_poses.items():
        src_name = name + "_AdPoseLocalVector"
        src_node = find_by_name(src_name)
        if src_node is None:
            continue
        src_box = relation.SetAsSource(src_node)
        relation.SetBoxPosition(src_box, NODE_W * 0, NODE_H * i)
        angle_direction = relation.CreateFunctionBox('My Macros', 'CHAR_Deformation_ADPoseAngleDirection')
        relation.SetBoxPosition(angle_direction, NODE_W * 1, NODE_H * i)
        connect(src_box, 'Translation', angle_direction, 'MacroInput0')
        d_a_dict = {}
        for a, d in poses:
            d_a_dict.setdefault(d, []).append(a)
        ds = d_a_dict.keys()
        a_sdk_dict = {}
        j = i
        for d, _as in d_a_dict.items():
            d_sdk = create_direction_sdk(relation, i, ds, d)
            connect(angle_direction, "MacroOutput1", d_sdk, "Position %")
            i += 1
            for a in _as:
                i, a_sdk = create_angle_sdk(relation, i, _as, a, a_sdk_dict)
                # connect(angle_direction, "MacroOutput0", a_sdk, "Position %")
                FBConnect(FindAnimationNode(angle_direction.AnimationNodeOutGet(), "MacroOutput0"),
                          a_sdk['Input_value'])

                multiply = relation.CreateFunctionBox('Number', "Multiply (a x b)")
                relation.SetBoxPosition(multiply, NODE_W * 3, NODE_H * j)
                connect(d_sdk, "Value", multiply, "a")
                # connect(a_sdk, "Value", multiply, "b")
                FBConnect(a_sdk['Output_value'], FindAnimationNode(multiply.AnimationNodeInGet(), "b"))

                divide = relation.CreateFunctionBox('Number', 'Divide (a/b)')
                relation.SetBoxPosition(divide, NODE_W * 4, NODE_H * j)
                connect(multiply, "Result", divide, "a")
                set_attr(divide, "b", [100.0])

                for mesh_box in mesh_box_list:
                    angle, direction = a, d
                    target_name = "{name}_a{angle}_d{direction}".format(**locals())
                    connect(divide, 'Result', mesh_box, target_name)
                j += 1
        i = max(i, j)
        i += 1
    relation.Active = True


def bs_sdk():
    NODE_W = 400
    delete_node_by_name("CHAR_Deformation_MainBlendShapeSDK", "Constraints")
    relation = FBConstraintRelation("CHAR_Deformation_MainBlendShapeSDK")
    i = 0
    mesh_box_list = []
    mesh_lists = find_all_mesh()
    for j, mesh in enumerate(mesh_lists):
        open_blend_shape_anim(mesh)
        mesh_box = relation.ConstrainObject(mesh)
        relation.SetBoxPosition(mesh_box, NODE_W * (5 + 0), 0)
        mesh_box_list.append(mesh_box)
    ad_pose_sdk2(relation, mesh_box_list, i)


def main():
    create_macro_remap_sdk()
    create_macro_3key_value_sdk()
    point_to_angle_direction()
    ad_pose_pont_link()
    bs_sdk()
