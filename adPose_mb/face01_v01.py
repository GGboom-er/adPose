# coding:utf-8

import json

from pyfbsdk import *


def find_obj_by_name(name):
    obj_list = FBComponentList()
    FBFindObjectsByName(name, obj_list)
    for obj in obj_list:
        return obj


def delete_by_name(name):
    obj = find_obj_by_name(name)
    if obj is not None:
        obj.FBDelete()


def add_attr():
    delete_by_name("Cube")
    cube = FBModelCube("Cube")
    cube.Show = True
    cube.PropertyCreate('My Double', FBPropertyType.kFBPT_double, 'Number', True, True, None)
    attr = cube.PropertyList.Find('My Double')
    assert isinstance(attr, FBPropertyAnimatableDouble)
    attr.SetMuted(True)


def create_constraints(typ, name):
    lMgr = FBConstraintManager()
    for lIdx in range(lMgr.TypeGetCount()):
        if typ == lMgr.TypeGetName(lIdx):
            delete_by_name(name)
            constraint = lMgr.TypeCreateConstraint(lIdx)
            constraint.Name = name
            return constraint


def reference_append(node, name, obj):
    for i in range(node.ReferenceGroupGetCount()):
        if node.ReferenceGroupGetName(i) != name:
            continue
        node.ReferenceAdd(i, obj)


def blend_01():
    delete_by_name("base_cube")
    base_cube = FBModelCube("base_cube")
    base_cube.Show = True

    delete_by_name("src_a")
    src_a = FBModelCube("src_a")
    src_a.Show = True

    delete_by_name("src_b")
    src_b = FBModelCube("src_b")
    src_b.Show = True

    delete_by_name("dst")
    dst = FBModelCube("dst")
    dst.Show = True

    # weight_cube = FBModelCube("weight_cube")
    # for i in range(2):
    #     weight_cube.PropertyCreate("weight%03d" % i, FBPropertyType.kFBPT_double, 'Number', True, True, None)

    blend = create_constraints("M - Transform Blend", "BlendConstraint")
    reference_append(blend, "Base Object", base_cube)
    reference_append(blend, "Target Object", src_a)
    reference_append(blend, "Target Object", src_b)
    # reference_append(blend, "Weight Object", weight_cube)
    reference_append(blend, "Constrain", dst)

    blend.Active = True


def blend_02():
    pass


def get_sdk_layer_ctrl(relation, name, data):
    w = 500
    h = 100
    if name in data:
        return data[name]
    src_node = find_obj_by_name(str(name))
    if src_node is None:
        return
    src_box = relation.SetAsSource(src_node)
    src_box.UseGlobalTransforms = False
    relation.SetBoxPosition(src_box, w * 0, h * len(data))
    data[name] = src_box
    return src_box


def relation_info():
    relation = find_obj_by_name("Relation")
    for box in relation.Boxes:
        print box.Name


def FindAnimationNode(pParent, pName):
    u"""
    :param pParent: 节点
    :param pName: 属性名
    :return: 按名称获取动画节点
    """
    for lNode in pParent.Nodes:
        if lNode.Name == pName:
            return lNode


def FindAnimationNodeByLabel(pParent, pName):
    for lNode in pParent.Nodes:
        if lNode.Label == pName:
            return lNode


def connect(src_node, src_attr, dst_node, dst_attr):
    u"""
    :param src_node: 输出节点名
    :param src_attr: 输出节点属性
    :param dst_node: 输入节点名
    :param dst_attr: 输出节点属性
    :return:
    将src_node的src_attr属性连接到dst_node的dst_attr上
    """
    src = FindAnimationNode(src_node.AnimationNodeOutGet(), src_attr)
    if src is None:
        src = FindAnimationNodeByLabel(src_node.AnimationNodeOutGet(), src_attr)
    dst = FindAnimationNode(dst_node.AnimationNodeInGet(), dst_attr)
    if dst is None:
        dst = FindAnimationNodeByLabel(dst_node.AnimationNodeInGet(), dst_attr)
    FBConnect(
        src,
        dst
    )


def get_sdk_layer_attr(relation, ctrl_box, ctrl_name, attr_name, attr_data):
    w = 500
    h = 100
    split_attr = [trs+xyz for trs in "trs" for xyz in "xyz"]
    if attr_name not in split_attr:
        return FindAnimationNode(ctrl_box.AnimationNodeOutGet(), attr_name)
    key = ctrl_name + "_" + attr_name[0]
    if key in attr_data:
        vector_to_number = attr_data[key]
    else:
        vector_to_number = relation.CreateFunctionBox('Converters', 'Vector To Number')
        relation.SetBoxPosition(vector_to_number, w * 1, h * len(attr_data))
        src_attr = dict(t="Lcl Translation", r="Lcl Rotation", s="Lcl Scaling")[attr_name[0]]
        connect(ctrl_box, src_attr, vector_to_number, "V")
        attr_data[key] = vector_to_number
    return FindAnimationNode(vector_to_number.AnimationNodeOutGet(), attr_name[1].upper())


def set_attr(box, name, value):
    u"""
    :param box: 节点
    :param name: 名称
    :param value: 数值
    :return:设置节点属性值
    """
    attr = FindAnimationNode(box.AnimationNodeInGet(), name)
    if attr is None:
        attr = FindAnimationNodeByLabel(box.AnimationNodeInGet(), name)
    attr.WriteData(value)


def face_layer_sdk():
    path = "D:/work/mb_face/mb_face.json"
    with open(path, "r") as fp:
        data = json.load(fp)
    w = 500
    h = 100
    delete_by_name("MBFaceSdkLayer")
    relation = FBConstraintRelation("MBFaceSdkLayer")
    ctrl_data = {}
    attr_data = {}
    sdk_data = {}
    i = 0
    for sdk in data["sdk_layer_data"]["sdk_data"]:
        ctrl_box = get_sdk_layer_ctrl(relation, sdk["ctrl_name"], ctrl_data)
        attr = get_sdk_layer_attr(relation, ctrl_box, sdk["ctrl_name"], sdk["attr_name"], attr_data)
        sdk2 = relation.CreateFunctionBox('My Macros', 'sdk2')
        relation.SetBoxPosition(sdk2, w * 2, int(h * i*1.4))
        i += 1
        FBConnect(
            attr,
            FindAnimationNodeByLabel(sdk2.AnimationNodeInGet(), "time")
        )
        default_value = sdk["default_value"]
        value = sdk["value"]
        if default_value > value:
            set_attr(sdk2, "time1", [value])
            set_attr(sdk2, "time2", [default_value])
            set_attr(sdk2, "value1", [1])
            set_attr(sdk2, "value2", [0])
        else:
            set_attr(sdk2, "time1", [default_value])
            set_attr(sdk2, "time2", [value])
            set_attr(sdk2, "value1", [0])
            set_attr(sdk2, "value2", [1])
        sdk_data[sdk["target_name"]] = sdk2

    additive_data = {}
    for layer_trs in data["sdk_layer_data"]["layer_trs"]:
        joint_name = layer_trs["joint_name"]
        trs = layer_trs["trs"]
        target_name = layer_trs["target_name"]
        base_trs = data["sdk_layer_data"]["base_trs"][joint_name]
        tid = [0, 1, 2]
        rid = [3, 4, 5, 6]
        sid = [7, 8, 9]
        if joint_name not in additive_data:
            # if len(additive_data) > 3:
            #     continue
            wi = len(additive_data) + 2
            hi = 0
            additive = relation.CreateFunctionBox('My Macros', 'additiveTransform')
            relation.SetBoxPosition(additive, int(w * wi * 1.8), int(h * hi * 3.2))
            set_attr(additive, "baseTranslation", [base_trs[i] for i in tid])
            set_attr(additive, "additiveTranslation", [trs[i]-base_trs[i] for i in tid])
            additive_data[joint_name] = dict(
                additive=additive,
                wi=wi,
                hi=hi,
                joint_name=joint_name
            )
            connect(sdk_data[target_name], "value", additive, "weight")
        else:
            additive_data[joint_name]["hi"] += 1
            hi = additive_data[joint_name]["hi"]
            wi = additive_data[joint_name]["wi"]
            old_additive = additive_data[joint_name]["additive"]
            additive = relation.CreateFunctionBox('My Macros', 'additiveTransform')
            relation.SetBoxPosition(additive, int(w * wi * 1.8), int(h * hi * 3.2))
            connect(old_additive, "OutputTranslation", additive, "baseTranslation")
            set_attr(additive, "additiveTranslation", [trs[i]-base_trs[i] for i in tid])
            connect(sdk_data[target_name], "value", additive, "weight")
            additive_data[joint_name]["additive"] = additive
    for joint_name in additive_data.keys():
        hi = additive_data[joint_name]["hi"]
        wi = additive_data[joint_name]["wi"]
        hi += 1
        old_additive = additive_data[joint_name]["additive"]
        joint = find_obj_by_name(str(joint_name))
        dst_box = relation.ConstrainObject(joint)
        relation.SetBoxPosition(dst_box, int(w * wi * 1.8), int(h * hi * 3.2))
        dst_box.UseGlobalTransforms = False
        connect(old_additive, "OutputTranslation", dst_box, "Lcl Translation")
    relation.Active = True


def face_03():
    pass


def main():
    # relation_info()
    face_layer_sdk()