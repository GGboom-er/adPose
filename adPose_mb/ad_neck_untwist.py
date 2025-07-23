# coding:utf-8
from ad_base import *


def delete_all_node_by_name(name, cls="Components"):
    u"""
    :param name: 节点名称
    :param cls: 节点类型
    :return:
    按名称删除节点
    """
    node = find_by_name(name, cls)
    if node is not None:
        DestroyModel(node)


def create_untwist(parent):
    parent = find_by_name(parent)
    if not parent:
        return
    # pre_ro
    if parent.Name.endswith("_M"):
        untwist_skin = find_by_name(parent.Name[:-1] + "No_Twist_Skin")
        space = parent.Parent
    else:
        untwist_skin = find_by_name(parent.Name + "_No_Twist_Skin")
        # space = find_by_name(parent.Name.replace("Part1", "").replace("Part2", ""))
        space = parent.Parent
    if untwist_skin is None:
        return

    pre = parent.PropertyList.Find("PreRotation").Data
    # # 组
    delete_all_node_by_name(parent.Name + "_unTwist_Driver")
    grp = FBModelNull(parent.Name + "_unTwist_Driver")
    driver_system = find_by_name("Driver_system")
    if driver_system:
        grp.Parent = find_by_name("Driver_system")
    # 定位器
    local_rotate = FBModelNull(parent.Name + "_Rotate")
    local_aim = FBModelNull(parent.Name + "_Aim")
    local_swing = FBModelNull(parent.Name + "_Swing")
    local_untwist = FBModelNull(parent.Name + "_UnTwist")

    # X轴向量, 组层级
    local_aim.PropertyList.Find("Lcl Translation").Data = FBVector3d(1, 0, 0)
    local_rotate.Parent = grp
    local_swing.Parent = grp
    local_aim.Parent = local_rotate
    local_untwist.Parent = local_rotate

    # AimConstraints
    delete_node_by_name("CHAR_Deformation_MB_Control_" + parent.Name + "_unTwist_Aim")

    aim_constraint = create_constraints("Aim", "CHAR_Deformation_" + parent.Name + "_unTwist_Aim")
    aim_constraint.PropertyList.Find("World Up Type").Data = 4
    aim_constraint.PropertyList.Find("Constrained Object").append(local_swing)
    aim_constraint.PropertyList.Find("Aim At Object").append(local_aim)
    aim_constraint.Active = True
    # parent rotation connect to local
    delete_node_by_name("CHAR_Deformation_MB_Control_" + parent.Name + "_rotation")
    relation = create_constraints("Relation", "CHAR_Deformation_" + parent.Name + "_Lcl_rotation")

    parent_box = relation.SetAsSource(parent)
    parent_box.UseGlobalTransforms = True
    relation.SetBoxPosition(parent_box, 400, 100)

    parent_parent_box = relation.SetAsSource(space)
    parent_box.UseGlobalTransforms = True
    relation.SetBoxPosition(parent_parent_box, 400, 200)

    relative = relation.CreateFunctionBox("Rotation", "Global To Local")
    relation.SetBoxPosition(relative, 400, 300)

    relative2 = relation.CreateFunctionBox("Rotation", "Global To Local")
    relation.SetBoxPosition(relative2, 400, 400)

    rotate_box = relation.ConstrainObject(local_rotate)
    rotate_box.UseGlobalTransforms = True
    relation.SetBoxPosition(rotate_box, 400, 500)

    connect(parent_box, "Rotation", relative, "Global Rot")
    connect(parent_parent_box, "Rotation", relative, "Base")
    connect(relative, "Local Rot", relative2, "Global Rot")

    set_attr(relative2, "Base", [pre[0], pre[1], pre[2]])
    connect(relative2, "Local Rot", rotate_box, "Rotation")
    relation.Active = True
    # Swing to unTwist rotation
    delete_node_by_name("CHAR_Deformation_MB_Control_" + parent.Name + "_Rotation")
    ro_constraint = create_constraints("Rotation", "CHAR_Deformation_" + parent.Name + "_Rotation")
    ro_constraint.PropertyList.Find("Constrained Object").append(local_untwist)
    ro_constraint.PropertyList.Find("Source").append(local_swing)
    ro_constraint.Active = True
    # locater to real joint
    delete_node_by_name("CHAR_Deformation_MB_Control_" + parent.Name + "_unTwist")
    unTwist_relation = create_constraints("Relation", "CHAR_Deformation_" + parent.Name + "_unTwist")

    unTwist_box = unTwist_relation.SetAsSource(local_untwist)
    unTwist_box.UseGlobalTransforms = False
    unTwist_relation.SetBoxPosition(unTwist_box, 400, 100)

    real_joint = unTwist_relation.ConstrainObject(untwist_skin)
    real_joint.UseGlobalTransforms = False
    unTwist_relation.SetBoxPosition(real_joint, 400, 200)

    connect(unTwist_box, "Lcl Rotation", real_joint, "Lcl Rotation")
    unTwist_relation.Active = True
    untwist = find_by_name(untwist_skin.Name[:-5])
    if untwist is None:
        return
    p_c = create_constraints("Parent/Child", "CHAR_Deformation_" + parent.Name + "_Parent")
    p_c.PropertyList.Find("Constrained Object (Child)").append(untwist)
    p_c.PropertyList.Find("Source (Parent)").append(untwist_skin)
    p_c.Active = True


def main():
    joints = [
        "Neck_M", "NeckPart1_M", "ElbowPart1_R", "ElbowPart2_R", "KneePart1_R", "KneePart2_R", "ElbowPart1_L",
        "ElbowPart2_L", "KneePart1_L", "KneePart2_L"]
    for joint in joints:
        create_untwist(joint)
    # create_untwist("Neck_M")
    # create_untwist("NeckPart1_M")
    # create_untwist("KneePart2_L")
    # create_untwist("KneePart1_L")
