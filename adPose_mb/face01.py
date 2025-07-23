# coding:utf-8

import json

from pyfbsdk import *


def find_obj_by_name(name):
    obj_list = FBComponentList()
    FBFindObjectsByName(str(name), obj_list)
    for obj in obj_list:
        return obj


def delete_by_name(name):
    obj = find_obj_by_name(name)
    if obj is not None:
        obj.FBDelete()


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


def nf_to_str(ns):
    return ";".join(["%.6f" % n for n in ns])


def ni_to_str(ns):
    return ";".join([str(n) for n in ns])


def tes_to_tqs(tes):
    euler = FBVector3d(tes[3], tes[4], tes[5])
    qua = FBVector4d()
    FBRotationToQuaternion(qua, euler)
    trs = tes[:3] + list(qua) + tes[-3:]
    return trs


def dot_qua(q1, q2):
    return sum([q1[i]*q2[i] for i in range(4)])


def get_additive_trs(trs, base):
    q1 = trs[3:7]
    q2 = base[3:7]
    if dot_qua(q1, q2) < 0:
        q1 = [-v for v in q1]
    additive_q = [q1[i] - q2[i] for i in range(4)]
    additive_trs = [trs[i] - base[i] for i in range(10)]
    additive_trs = additive_trs[:3] + list(additive_q) + additive_trs[-3:]
    return additive_trs


def find_anim_node(parent, name):
    for lNode in parent.Nodes:
        if lNode.Name == name:
            return lNode
    for lNode in parent.Nodes:
        if lNode.Label == name:
            return lNode


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


def connect(src_node, src_attr, dst_node, dst_attr):
    u"""
    :param src_node: 输出节点名
    :param src_attr: 输出节点属性
    :param dst_node: 输入节点名
    :param dst_attr: 输出节点属性
    :return:
    将src_node的src_attr属性连接到dst_node的dst_attr上
    """
    src = find_anim_node(src_node.AnimationNodeOutGet(), src_attr)
    dst = find_anim_node(dst_node.AnimationNodeInGet(), dst_attr)
    FBConnect(src, dst)


def get_sdk_layer_attr(relation, ctrl_box, ctrl_name, attr_name, attr_data):
    w = 500
    h = 100
    split_attr = [trs+xyz for trs in "trs" for xyz in "xyz"]
    if attr_name not in split_attr:
        return find_anim_node(ctrl_box.AnimationNodeOutGet(), attr_name)
    key = ctrl_name + "_" + attr_name[0]
    if key in attr_data:
        vector_to_number = attr_data[key]
    else:
        vector_to_number = relation.CreateFunctionBox('Converters', 'Vector To Number')
        relation.SetBoxPosition(vector_to_number, w * 1, h * len(attr_data))
        src_attr = dict(t="Lcl Translation", r="Lcl Rotation", s="Lcl Scaling")[attr_name[0]]
        connect(ctrl_box, src_attr, vector_to_number, "V")
        attr_data[key] = vector_to_number
    return find_anim_node(vector_to_number.AnimationNodeOutGet(), attr_name[1].upper())


def set_attr(box, name, value):
    u"""
    :param box: 节点
    :param name: 名称
    :param value: 数值
    :return:设置节点属性值
    """
    attr = find_anim_node(box.AnimationNodeInGet(), name)
    attr.WriteData(value)


def create_sdk(data):
    w = 500
    h = 100
    delete_by_name("MBFaceSdkLayer")
    relation = FBConstraintRelation("MBFaceSdkLayer")
    ctrl_data = {}
    attr_data = {}
    sdk_data = {}
    i = 0
    for sdk in data:
        ctrl_box = get_sdk_layer_ctrl(relation, sdk["ctrl_name"], ctrl_data)
        attr = get_sdk_layer_attr(relation, ctrl_box, sdk["ctrl_name"], sdk["attr_name"], attr_data)
        sdk2 = relation.CreateFunctionBox('My Macros', 'sdk2')
        relation.SetBoxPosition(sdk2, w * 2, int(h * i*1.4))
        i += 1
        FBConnect(
            attr,
            find_anim_node(sdk2.AnimationNodeInGet(), "time")
        )
        default_value = sdk["default_value"]
        value = sdk["value"]
        if default_value > value:
            set_attr(sdk2, "time1", [value])
            set_attr(sdk2, "time2", [default_value])
            set_attr(sdk2, "value1", [100])
            set_attr(sdk2, "value2", [0])
        else:
            set_attr(sdk2, "time1", [default_value])
            set_attr(sdk2, "time2", [value])
            set_attr(sdk2, "value1", [0])
            set_attr(sdk2, "value2", [100])
        sdk_data[sdk["target_name"]] = sdk2
    return relation, sdk_data


def face_rig():
    w = 500
    h = 100
    path = "D:/work/mb_face/mb_face.json"
    with open(path, "r") as fp:
        data = json.load(fp)

    relation, sdk_data = create_sdk(data["sdk_data"])
    target_names = list(sorted([sdk["target_name"] for sdk in data["sdk_data"]]))
    joint_names = list(sorted(data["joint_trs"].keys()))
    ctrl_names = list(sorted(data["ctrl_trs"].keys()))
    # joint trs
    joint_trs = []
    for joint_name in joint_names:
        trs = data["joint_trs"][joint_name]
        joint_trs += tes_to_tqs(trs)
    # ctrl trs
    ctrl_trs = []
    for ctrl_name in ctrl_names:
        trs = data["ctrl_trs"][ctrl_name]
        ctrl_trs += tes_to_tqs(trs)
    # additive
    additive_ids = []
    additive_trs = []
    for row in data["additive_data"]:
        joint_name = row["joint_name"]
        trs = row["trs"]
        target_name = row["target_name"]
        joint_id = joint_names.index(joint_name)
        target_id = target_names.index(target_name)
        trs = tes_to_tqs(trs)
        base = joint_trs[joint_id*10: joint_id*10+10]
        additive_trs += get_additive_trs(trs, base)
        additive_ids += [joint_id, target_id]
    # cluster weight
    cluster_ids = []
    cluster_weights = []
    for row in data["cluster_weight_data"]:
        weight = row["weight"]
        joint_name = row["joint_name"]
        ctrl_name = row["ctrl_name"]
        joint_id = joint_names.index(joint_name)
        ctrl_id = ctrl_names.index(ctrl_name)
        cluster_ids += [joint_id, ctrl_id]
        cluster_weights.append(weight)

    blend = create_constraints("M - Transform Blend", "BlendConstraint")
    blend.PropertyList.Find('jointCount').Data = len(joint_names)
    blend.PropertyList.Find('targetCount').Data = len(target_names)
    blend.PropertyList.Find('ctrlCount').Data = len(ctrl_names)

    blend.PropertyList.Find('jointTrsStr').Data = nf_to_str(joint_trs)
    blend.PropertyList.Find('clusterWeightStr').Data = nf_to_str(cluster_weights)
    blend.PropertyList.Find('clusterIdStr').Data = ni_to_str(cluster_ids)
    blend.PropertyList.Find('additiveTrsStr').Data = nf_to_str(additive_trs)
    blend.PropertyList.Find('additiveIdStr').Data = ni_to_str(additive_ids)

    for ctrl_name in ctrl_names:
        reference_append(blend, "ctrl", find_obj_by_name(str(ctrl_name)))
        reference_append(blend, "ctrlPre", find_obj_by_name(str(ctrl_name + "Group")))
    for joint_name in joint_names:
        reference_append(blend, "joint", find_obj_by_name(str(joint_name)))

    blend.Active = True
    dst_box = relation.ConstrainObject(blend)
    relation.SetBoxPosition(dst_box, w*3, 0)
    for i, target_name in enumerate(target_names):
        sdk = sdk_data[target_name]
        name = "weight%03d" % i
        connect(sdk, "value", dst_box, name)
    relation.Active = True
    blend.Active = True


def main():
    # # relation_info()
    face_rig()
