# coding:utf-8
u"""
一些mb的基础操作
"""
from pyfbsdk import *
import re
from functools import partial


def find_all_node_by_cls(cls):
    u"""
    :param cls: 类型
    :return:
    按类型获取场景内所有节点
    """
    return filter(lambda x: x is not None and x.Is(cls.TypeInfo), FBSystem().Scene.Components)


def find_all_mesh():
    u"""
    :return:
    获取场景内所有蒙皮
    """
    return filter(lambda x: x.Geometry is not None and len(x.Deformers) != 0, find_all_node_by_cls(FBModel))


def find_by_name(name, cls="Components"):
    u"""
    :param name: 名字
    :param cls: 类型
    :return:
    通过名字获取物体
    """
    nodes = filter(lambda x: x.Name == name, getattr(FBSystem().Scene, cls))
    for node in nodes:
        return node


def find_by_field(name, cls="Components"):
    u"""
    :param name: 字段
    :param cls: 类型
    :return:
    获取所有名称包含name的物体
    """
    return filter(lambda x: name in x.Name, getattr(FBSystem().Scene, cls))


def get_name_joint():
    u"""
    :return: {name:joint, ...}
    获取骨骼名字，物体的键值对。
    """
    nodes = find_all_node_by_cls(FBModelSkeleton)
    return {node.Name: node for node in nodes}


def FindAnimationNode(pParent, pName):
    u"""
    :param pParent: 节点
    :param pName: 属性名
    :return: 按名称获取动画节点
    """
    for lNode in pParent.Nodes:
        if lNode.Name == pName:
            return lNode


def delete_node_by_name(name, cls="Components"):
    u"""
    :param name: 节点名称
    :param cls: 节点类型
    :return:
    按名称删除节点
    """
    node = find_by_name(name, cls)
    if node is not None:
        node.FBDelete()


def DestroyModel(pModel):
    u"""
    :param pModel: model
    :return:
    删除物体和物体所有子层级
    """
    while len(pModel.Children) > 0:
        DestroyModel(pModel.Children[-1])
    pModel.FBDelete()


def connect(src_node, src_attr, dst_node, dst_attr):
    u"""
    :param src_node: 输出节点名
    :param src_attr: 输出节点属性
    :param dst_node: 输入节点名
    :param dst_attr: 输出节点属性
    :return:
    将src_node的src_attr属性连接到dst_node的dst_attr上
    """
    FBConnect(
        FindAnimationNode(src_node.AnimationNodeOutGet(), src_attr),
        FindAnimationNode(dst_node.AnimationNodeInGet(), dst_attr)
    )


def SetMacroOutputName(box, name):
    u"""
    :param box:
    :param name:
    :return:
    修改macro输出名，这个是错误的，暂时没找到正确的方法
    """
    FindAnimationNode(box.AnimationNodeInGet(), "Output").Name = name


def ListAnimNodeAttr(box):
    u"""
    :param box:
    :return:
    打印节点属性
    """
    for attr in box.AnimationNodeOutGet().Nodes:
        print attr.Name
    for attr in box.AnimationNodeInGet().Nodes:
        print attr.Name


def ListModelAttr(node):
    u"""
    :param node:
    :return:
    打印物体属性
    """
    for attr in node.PropertyList:
        print attr.Name


def box_info():
    relation = find_by_name("Relation", "Constraints")
    for box in relation.Boxes:
        print box.Name
        ListAnimNodeAttr(box)


def set_attr(box, name, value):
    u"""
    :param box: 节点
    :param name: 名称
    :param value: 数值
    :return:设置节点属性值
    """
    attr = FindAnimationNode(box.AnimationNodeInGet(), name)
    attr.WriteData(value)


def create_constraints(typ, name):
    """
    Aim
    Expression
    Multi Referential
    OR - Position from Position
    Parent/Child
    Path
    Position
    Range
    Relation
    Rigid Body
    3 Points
    Rotation
    Scale
    Mapping
    Chain IK
    Spline IK
    创建约束
    """
    lMgr = FBConstraintManager()
    for lIdx in range(lMgr.TypeGetCount()):
        if typ == lMgr.TypeGetName(lIdx):
            delete_node_by_name(name, "Constraints")
            constraint = lMgr.TypeCreateConstraint(lIdx)
            constraint.Name = name
            return constraint


def parent_constraint(src, dst):
    u"""
    :param src: 约束物体
    :param dst: 被约束物体
    :return:
    创建父子约束
    """
    constraint = create_constraints("Parent/Child", "CHAR_Deformation_"+dst.Name+"Parent")
    constraint.PropertyList.Find("Source (Parent)").append(src)
    constraint.PropertyList.Find("Constrained object (Child)").append(dst)
    constraint.Active = True


def aim_node_connect(src, dst):
    u"""
    :param src: 约束物体
    :param dst: 被约束物体
    :return:
    创建目标约束
    """
    constraint = create_constraints("Aim", "CHAR_Deformation_"+dst.Name+"Aim")
    constraint.PropertyList.Find("Constrained object").append(dst)
    constraint.PropertyList.Find("Aim At Object").append(src)
    constraint.PropertyList.Find("WorldUpType").Data = 4
    constraint.Active = True
    constraint.PropertyList.Find("AimVector").Data = FBVector3d(1, 0, 0)


def rotation_constraint(src_list, weights, dst):
    u"""
    :param src_list: 约束物体列表
    :param weights: 约束权重列表
    :param dst: 被约束物体
    :return:
    创建src_list对dst的旋转约束，并设置权重值未weights
    """
    constraint = create_constraints("Rotation", "CHAR_Deformation_"+dst.Name+"Rotation")
    for src, weight in zip(src_list, weights):
        constraint.PropertyList.Find("Source").append(src)
        constraint.PropertyList.Find(src.Name+".Weight").Data = weight*100
    constraint.PropertyList.Find("Constrained object").append(dst)
    constraint.Active = True
    ListModelAttr(constraint)


def create_sdk(relation, w, h, key_value):
    u"""
    :param relation: 图
    :param w: 宽
    :param h: 高
    :param key_value: [[time, value], ...]
    :return:

    """
    sdk = relation.CreateFunctionBox('Other', 'FCurve Number (%)')
    relation.SetBoxPosition(sdk, w, h)
    curve = sdk.GetOutConnector(0).FCurve
    curve.Keys[0].Time.SetFrame(key_value[0][0])
    curve.Keys[0].Value = key_value[0][1]
    curve.Keys[1].Time.SetFrame(key_value[1][0])
    curve.Keys[1].Value = key_value[1][1]
    for t, v in key_value[1:]:
        tim = FBTime()
        tim.SetFrame(t)
        curve.KeyAdd(tim, v)
    for key in curve.Keys:
        key.TangentMode = FBTangentMode.kFBTangentModeAuto
        key.TangentConstantMode = FBTangentConstantMode.kFBTangentConstantModeNormal
        key.Interpolation = FBInterpolation.kFBInterpolationLinear
    return sdk


def create_macro_remap_sdk():
    NODE_W = 300
    NODE_H = 100
    remap = create_constraints("Relation", "ReMap")

    old_min = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(old_min, NODE_W * 0, NODE_H * 2)

    _min = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(_min, NODE_W * 0, NODE_H * 3)

    old_max = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(old_max, NODE_W * 0, NODE_H * 0)

    _max = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(_max, NODE_W * 0, NODE_H * 1)

    old_value = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(old_value, NODE_W * 0, NODE_H * 4)

    max_sub_min = remap.CreateFunctionBox('Number', 'Subtract (a - b)')
    remap.SetBoxPosition(max_sub_min, NODE_W * 1, NODE_H * 0)

    omax_sub_omin = remap.CreateFunctionBox('Number', 'Subtract (a - b)')
    remap.SetBoxPosition(omax_sub_omin, NODE_W * 1, NODE_H * 1)

    ovalue_sub_omin = remap.CreateFunctionBox('Number', 'Subtract (a - b)')
    remap.SetBoxPosition(ovalue_sub_omin, NODE_W * 1, NODE_H * 2)

    mult = remap.CreateFunctionBox('Number', 'Multiply (a x b)')
    remap.SetBoxPosition(mult, NODE_W * 2, NODE_H * 0)

    divide = remap.CreateFunctionBox('Number', 'Divide (a/b)')
    remap.SetBoxPosition(divide, NODE_W * 2, NODE_H * 1)

    _add = remap.CreateFunctionBox('Number', 'Add (a + b)')
    remap.SetBoxPosition(_add, NODE_W * 3, NODE_H * 0)

    is_greater = remap.CreateFunctionBox('Number', 'Is Greater (a > b)')
    remap.SetBoxPosition(is_greater, NODE_W * 4, NODE_H * 0)

    is_less = remap.CreateFunctionBox('Number', 'Is Less (a < b)')
    remap.SetBoxPosition(is_less, NODE_W * 4, NODE_H * 1)

    condition1 = remap.CreateFunctionBox('Number', 'If Cond Then A Else B')
    remap.SetBoxPosition(condition1, NODE_W * 5, NODE_H * 0)

    condition2 = remap.CreateFunctionBox('Number', 'If Cond Then A Else B')
    remap.SetBoxPosition(condition2, NODE_W * 5, NODE_H * 1)

    out_value = remap.CreateFunctionBox('Macro Tools', 'Macro Output Number')
    remap.SetBoxPosition(out_value, NODE_W * 6, NODE_H * 0)


    connect(_max, 'Input', max_sub_min, 'a')
    connect(_min, 'Input', max_sub_min, 'b')
    connect(old_max, 'Input', omax_sub_omin, 'a')
    connect(old_min, 'Input', omax_sub_omin, 'b')
    connect(old_value, 'Input', ovalue_sub_omin, 'a')
    connect(old_min, 'Input', ovalue_sub_omin, 'b')
    connect(max_sub_min, 'Result', mult, 'a')
    connect(ovalue_sub_omin, 'Result', mult, 'b')
    connect(mult, 'Result', divide, 'a')
    connect(omax_sub_omin, 'Result', divide, 'b')
    connect(_min, 'Input', _add, 'a')
    connect(divide, 'Result', _add, 'b')
    connect(old_value, 'Input', is_greater, 'a')
    connect(old_max, 'Input', is_greater, 'b')
    connect(old_value, 'Input', is_less, 'a')
    connect(old_min, 'Input', is_less, 'b')
    connect(_max, 'Input', condition1, 'a')
    connect(_min, 'Input', condition2, 'a')
    connect(is_greater, 'Result', condition1, 'Cond')
    connect(is_less, 'Result', condition2, 'Cond')
    connect(condition1, 'Result', condition2, 'b')
    connect(_add, 'Result', condition1, 'b')
    connect(condition2, 'Result', out_value, 'Output')

    return remap


def create_remap_node(parent, w, h):
    remap = parent.CreateFunctionBox('My Macros', 'ReMap')
    parent.SetBoxPosition(remap, w, h)
    node_port = {}
    for name, item in zip(["Old_Min", "Min", "Old_Max", "Max", "Input_Value"], remap.AnimationNodeInGet().Nodes):
        node_port[name] = item
    node_port["Output_value"] = remap.AnimationNodeOutGet().Nodes[0]
    return node_port


def create_macro_3key_value_sdk():
    NODE_W = 300
    NODE_H = 100
    driver_key = create_constraints('Relation', 'Driver_3_key_sdk')

    ovalue_0 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(ovalue_0, NODE_W * 0, NODE_H * 0)

    value_0 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(value_0, NODE_W * 0, NODE_H * 1)

    ovalue_1 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(ovalue_1, NODE_W * 0, NODE_H * 2)

    value_1 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(value_1, NODE_W * 0, NODE_H * 3)

    ovalue_2 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(ovalue_2, NODE_W * 0, NODE_H * 4)

    value_2 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(value_2, NODE_W * 0, NODE_H * 5)

    input_value = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(input_value, NODE_W * 0, NODE_H * 6)

    remap0 = create_remap_node(driver_key, NODE_W * 1, NODE_H * 0)

    remap1 = create_remap_node(driver_key, NODE_W * 1, NODE_H * 1)

    sub0 = driver_key.CreateFunctionBox('Number', 'Subtract (a - b)')
    driver_key.SetBoxPosition(sub0, NODE_W * 1, NODE_H * 2)

    add_node = driver_key.CreateFunctionBox("Number", "Add (a + b)")
    driver_key.SetBoxPosition(add_node, NODE_W * 2, NODE_H * 0)

    out_value = driver_key.CreateFunctionBox("Macro Tools", "Macro Output Number")
    driver_key.SetBoxPosition(out_value, NODE_W * 3, NODE_H * 0)

    FBConnect(FindAnimationNode(value_0.AnimationNodeOutGet(), 'Input'), remap0["Min"])
    FBConnect(FindAnimationNode(value_1.AnimationNodeOutGet(), 'Input'), remap0["Max"])
    FBConnect(FindAnimationNode(ovalue_0.AnimationNodeOutGet(), 'Input'), remap0["Old_Min"])
    FBConnect(FindAnimationNode(ovalue_1.AnimationNodeOutGet(), 'Input'), remap0["Old_Max"])
    FBConnect(FindAnimationNode(input_value.AnimationNodeOutGet(), 'Input'), remap0["Input_Value"])
    remap1["Min"].WriteData([0])
    connect(value_2, 'Input', sub0, 'a')
    connect(value_1, 'Input', sub0, 'b')
    FBConnect(FindAnimationNode(sub0.AnimationNodeOutGet(), 'Result'), remap1["Max"])
    FBConnect(FindAnimationNode(ovalue_1.AnimationNodeOutGet(), 'Input'), remap1["Old_Min"])
    FBConnect(FindAnimationNode(ovalue_2.AnimationNodeOutGet(), 'Input'), remap1["Old_Max"])
    FBConnect(FindAnimationNode(input_value.AnimationNodeOutGet(), 'Input'), remap1["Input_Value"])
    FBConnect(remap0["Output_value"], FindAnimationNode(add_node.AnimationNodeInGet(), 'a'))
    FBConnect(remap1["Output_value"], FindAnimationNode(add_node.AnimationNodeInGet(), 'b'))
    connect(add_node, 'Result', out_value, 'Output')


def create_driver_3d_node(parent, w, h, key_value):
    driver_3d = parent.CreateFunctionBox('My Macros', 'Driver_3_key_sdk')
    parent.SetBoxPosition(driver_3d, w, h)
    nodes = driver_3d.AnimationNodeInGet().Nodes
    for i in range(len(key_value)):
        nodes[i*2].WriteData([key_value[i][0]])
        nodes[i*2+1].WriteData([key_value[i][1]])
    return {"Input_value": nodes[-1], "Output_value": driver_3d.AnimationNodeOutGet().Nodes[0]}

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


if __name__ == '__main__':
    main()
