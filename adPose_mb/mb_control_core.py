# coding:utf-8
from ad_base import *
import ad_copy
import copy


def Callback(oCaller, pEvent):
    print "Callback Triggered"


def new_scene():
    app = FBApplication()
    app.OnFileNew.Add(Callback)
    app.FileNew()
    app.OnFileNew.Remove(Callback)


def open_file(filepath, filename):  # "D:/workspace/assets/mb_ST.fbx"
    app = FBApplication()
    app.OnFileOpen.Add(Callback)
    app.FileOpen(filepath + "/" + filename)
    app.OnFileOpen.Remove(Callback)


def select_skeleton():
    TakeName = FBSystem().CurrentTake.Name

    FBMessageBoxGetUserValue("", "", "", )


def select_model_with_children(parentModel, selectParent=True):
    # 获取对象的子对象
    children = parentModel.Children

    # 检查子对象是否存在更多的子对象
    if (len(children) > 0):

        # 循环遍历子对象
        for child in children:
            # 选择子对象
            child.Selected = True

            # 选择更多的子对象
            select_model_with_children(child)

    # 选择父对象
    parentModel.Selected = selectParent


def check_exist(num):
    if find_by_name("OK" + str(num)) is not None:
        num = num+1
        check_exist(num)
    else:
        return "OK" + str(num)


def re_order(joint):
    if not isinstance(joint, FBModel):
        return
    rotate = FBVector3d()
    joint.GetVector(rotate, FBModelTransformationType.kModelRotation, True)
    joint.PropertyList.Find("RotationOrder").Data = 0
    joint.PropertyList.Find("PreRotation").Data = FBVector3d(0, 0, 0)
    joint.SetVector(rotate, FBModelTransformationType.kModelRotation, True)


def re_order_all(joint):
    for child in joint.Children:
        re_order_all(child)
    re_order(joint)


def dup_joint(name, parent, dup):
    dup_jnt = copy.copy(dup)
    dup_jnt.Name = name

    p_c = create_constraints("Parent/Child", "P_C")
    p_c.PropertyList.Find("Constrained Object (Child)").append(dup_jnt)
    p_c.PropertyList.Find("Source (Parent)").append(dup)
    p_c.Active = True
    FBSystem().Scene.Evaluate()
    # dup_trans = FBVector3d(dup_data.Translation[0], dup_data.Translation[1], dup_data.Translation[2])
    # dup_ro = FBVector3d(dup_data.Rotation[0], dup_data.Rotation[1], dup_data.Rotation[2])
    p_c.Active = False
    p_c.FBDelete()
    # dup.GetVector(dup_trans, FBModelTransformationType.kModelTranslation, True)
    # dup.GetVector(dup_ro, FBModelTransformationType.kModelRotation, True)
    # dup_jnt.Translation = dup_trans
    # dup_jnt.Rotation = dup_ro
    dup_jnt.Parent = parent
    return dup_jnt


def create_mb_control():
    # 组
    pre_text = "MB_Control_"
    # MB_ST_Rig = FBModelNull(pre_text + "ST_Rig")
    #
    # MB_Roots = dup_joint(pre_text + find_by_name("Roots").Name, MB_ST_Rig, find_by_name("Roots"))
    #
    # MB_Root_M = dup_joint(pre_text + find_by_name("Root_M").Name, MB_Roots, find_by_name("Root_M"))

    Root_M = find_by_name("Root_M")
    MB_Hip_R = dup_joint(pre_text + "Hip_R", Root_M, find_by_name("Hip_R"))
    MB_Knee_R = dup_joint(pre_text + "Knee_R", MB_Hip_R, find_by_name("Knee_R"))
    MB_Ankle_R = dup_joint(pre_text + "Ankle_R", MB_Knee_R, find_by_name("Ankle_R"))

    MB_Hip_L = dup_joint(pre_text + "Hip_L", Root_M, find_by_name("Hip_L"))
    MB_Knee_L = dup_joint(pre_text + "Knee_L", MB_Hip_L, find_by_name("Knee_L"))
    MB_Ankle_L = dup_joint(pre_text + "Ankle_L", MB_Knee_L, find_by_name("Ankle_L"))

    Scapula_L = find_by_name("Scapula_L")
    Scapula_R = find_by_name("Scapula_R")

    MB_Shoulder_L = dup_joint(pre_text + "Shoulder_L", Scapula_L, find_by_name("Shoulder_L"))
    MB_Elbow_L = dup_joint(pre_text + "Elbow_L", MB_Shoulder_L, find_by_name("Elbow_L"))
    MB_Wrist_L = dup_joint(pre_text + "Wrist_L", MB_Elbow_L, find_by_name("Wrist_L"))

    MB_Shoulder_R = dup_joint(pre_text + "Shoulder_R", Scapula_R, find_by_name("Shoulder_R"))
    MB_Elbow_R = dup_joint(pre_text + "Elbow_R", MB_Shoulder_R, find_by_name("Elbow_R"))
    MB_Wrist_R = dup_joint(pre_text + "Wrist_R", MB_Elbow_R, find_by_name("Wrist_R"))

    MB_Shoulder_L_unTwist = dup_joint(pre_text + "Shoulder_L_unTwist", MB_Shoulder_L, find_by_name("ShoulderPart1_L"))

    MB_Wrist_L_followTwist = dup_joint(pre_text + "Wrist_L_followTwist", MB_Elbow_L, find_by_name("ElbowPart2_L"))

    MB_Shoulder_R_unTwist = dup_joint(pre_text + "Shoulder_R_unTwist", MB_Shoulder_R, find_by_name("ShoulderPart1_R"))

    MB_Wrist_R_followTwist = dup_joint(pre_text + "Wrist_R_followTwist", MB_Elbow_R, find_by_name("ElbowPart2_R"))

    MB_Hip_R_unTwist = dup_joint(pre_text + "Hip_R_unTwist", MB_Hip_R, find_by_name("HipPart1_R"))

    MB_Ankle_R_followTwist = dup_joint(pre_text + "Ankle_R_followTwist", MB_Knee_R, find_by_name("KneePart2_R"))

    MB_Hip_L_unTwist = dup_joint(pre_text + "Hip_L_unTwist", MB_Hip_L, find_by_name("HipPart1_L"))

    MB_Ankle_L_followTwist = dup_joint(pre_text + "Ankle_L_followTwist", MB_Knee_L, find_by_name("KneePart2_L"))


def get_FK_model():
    lmodelList = ("MB_Control_Ankle_L", "MB_Control_Ankle_R",
                  "MB_Control_Wrist_L", "MB_Control_Wrist_R")
    return lmodelList


def get_lock_XYmodel():
    lmodelList = ("MB_Control_Knee_R", "MB_Control_Knee_L",
                  "MB_Control_Elbow_R", "MB_Control_Elbow_L")
    return lmodelList


def get_translate_model():
    lmodelList = ("MB_Control_Shoulder_R", "MB_Control_Shoulder_L", "MB_Control_Hip_R", "MB_Control_Hip_L")
    return lmodelList


def mb_control_transfer():
    lmodelListFK = get_FK_model()
    for modelName in lmodelListFK:
        dst = modelName.replace("MB_Control_", "")
        parent_constraint(find_by_name(modelName), find_by_name(dst))
    lmodelListXYLock = get_lock_XYmodel()
    for modelName in lmodelListXYLock:
        find_by_name(modelName).PropertyList.Find("Lcl Rotation").SetMemberLocked(0, True)
        find_by_name(modelName).PropertyList.Find("Lcl Rotation").SetMemberLocked(1, True)
        find_by_name(modelName).PropertyList.Find("Rotation").SetMemberLocked(0, True)
        find_by_name(modelName).PropertyList.Find("Rotation").SetMemberLocked(1, True)
        find_by_name(modelName).PropertyList.Find("RotationMinY").Data = True
        find_by_name(modelName).PropertyList.Find("RotationMaxY").Data = True
        find_by_name(modelName).PropertyList.Find("RotationMinX").Data = True
        find_by_name(modelName).PropertyList.Find("RotationMaxX").Data = True
        dst = modelName.replace("MB_Control_", "")
        parent_constraint(find_by_name(modelName), find_by_name(dst))


def create_untwist(parent, pre_ro):
    untwist = find_by_name(parent + "_unTwist")
    parent = find_by_name(parent)
    pre = pre_ro[parent.Name.replace("MB_Control_", "")]
    # 组
    grp = FBModelNull(parent.Name + "_unTwist_Driver")
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

    parent_parent_box = relation.SetAsSource(parent.Parent)
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

    real_joint = unTwist_relation.ConstrainObject(untwist)
    real_joint.UseGlobalTransforms = False
    unTwist_relation.SetBoxPosition(real_joint, 400, 200)

    connect(unTwist_box, "Lcl Rotation", real_joint, "Lcl Rotation")
    unTwist_relation.Active = True
    return unTwist_relation


def wrist_follow_twist(parent, follow_twist, pre_ro):  # "MB_Control_Wrist_L" "MB_Control_Wrist_L_followTwist" "Wrist_L"Pre rotation
    follow_twist = find_by_name(follow_twist)
    parent = find_by_name(parent)
    pre = pre_ro[parent.Name.replace("MB_Control_", "")]

    # 组
    grp = FBModelNull(parent.Name + "_followTwist_Driver")
    grp.Parent = find_by_name("Driver_system")

    # locator
    # Lcl Rotation inverse locator, the Aim locator for the swing, swing locator
    lcl_ro_inverse = FBModelNull(parent.Name + "_LocalRotation_inverse")
    swing_aim = FBModelNull(parent.Name + "_swing_Aim")
    swing = FBModelNull(parent.Name + "_localSwing_inverse")

    # Aim parent to Lcl Rotation inverse, set xaxis
    lcl_ro_inverse.Parent = grp
    swing.Parent = grp
    swing_aim.Parent = lcl_ro_inverse
    swing_aim.PropertyList.Find("Lcl Translation").Data = FBVector3d(1, 0, 0)

    # Aim constraint
    aim_constraint = create_constraints("Aim", "CHAR_Deformation_" + parent.Name + "_Aim")
    aim_constraint.PropertyList.Find("World Up Type").Data = 4
    aim_constraint.PropertyList.Find("Constrained Object").append(swing)
    aim_constraint.PropertyList.Find("Aim At Object").append(swing_aim)
    aim_constraint.Active = True

    # relation of the rotation to Lcl rotate inverse
    inverse_rotation_relation = create_constraints("Relation", "CHAR_Deformation_" + parent.Name + "_inverseRotation")

    parent_box = inverse_rotation_relation.SetAsSource(parent)
    inverse_rotation_relation.SetBoxPosition(parent_box, 400, 100)
    parent_box.UseGlobalTransforms = True

    parent_parent_box = inverse_rotation_relation.SetAsSource(parent.Parent)
    inverse_rotation_relation.SetBoxPosition(parent_parent_box, 400, 200)
    parent_parent_box.UseGlobalTransforms = True

    local_rotation = inverse_rotation_relation.CreateFunctionBox("Rotation", "Global To Local")
    inverse_rotation_relation.SetBoxPosition(local_rotation, 400, 300)

    local_rotation_no_pre = inverse_rotation_relation.CreateFunctionBox("Rotation", "Global To Local")
    inverse_rotation_relation.SetBoxPosition(local_rotation_no_pre, 400, 400)

    inverse_gtl = inverse_rotation_relation.CreateFunctionBox("Rotation", "Global To Local")
    inverse_rotation_relation.SetBoxPosition(inverse_gtl, 400, 500)
    set_attr(inverse_gtl, "Global Rot", [0, 0, 0])

    inverse_rotation_box = inverse_rotation_relation.ConstrainObject(lcl_ro_inverse)
    inverse_rotation_relation.SetBoxPosition(inverse_rotation_box, 400, 300)
    inverse_rotation_box.UseGlobalTransforms = True

    connect(parent_box, "Rotation", local_rotation, "Global Rot")
    connect(parent_parent_box, "Rotation", local_rotation, "Base")
    connect(local_rotation, "Local Rot", local_rotation_no_pre, "Global Rot")
    set_attr(local_rotation_no_pre, "Base", [pre[0], pre[1], pre[2]])
    connect(local_rotation_no_pre, "Local Rot", inverse_gtl, "Base")
    set_attr(inverse_gtl, "Global Rot", [0, 0, 0])
    connect(inverse_gtl, "Local Rot", inverse_rotation_box, "Rotation")
    inverse_rotation_relation.Active = True

    # relation of local rotation multiply swing inverse
    swing_relation = create_constraints("Relation", "CHAR_Deformation_" + parent.Name + "_swing")

    parent_box = swing_relation.SetAsSource(parent)
    swing_relation.SetBoxPosition(parent_box, 400, 100)
    parent_box.UseGlobalTransforms = True

    parent_parent_box = swing_relation.SetAsSource(parent.Parent)
    swing_relation.SetBoxPosition(parent_parent_box, 400, 200)
    parent_parent_box.UseGlobalTransforms = True

    relative = swing_relation.CreateFunctionBox("Rotation", "Global To Local")
    swing_relation.SetBoxPosition(relative, 400, 300)

    relative2 = swing_relation.CreateFunctionBox("Rotation", "Global To Local")
    swing_relation.SetBoxPosition(relative2, 400, 400)

    mult_ltg_box = swing_relation.CreateFunctionBox("Rotation", "Local To Global")
    swing_relation.SetBoxPosition(mult_ltg_box, 800, 100)

    swing_box = swing_relation.SetAsSource(swing)
    swing_relation.SetBoxPosition(swing_box, 800, 200)
    swing_box.UseGlobalTransforms = True

    dst_box = swing_relation.ConstrainObject(follow_twist)
    swing_relation.SetBoxPosition(dst_box, 800, 300)
    dst_box.UseGlobalTransforms = False

    connect(parent_box, "Rotation", relative, "Global Rot")
    connect(parent_parent_box, "Rotation", relative, "Base")
    connect(relative, "Local Rot", relative2, "Global Rot")
    set_attr(relative2, "Base", [pre[0], pre[1], pre[2]])
    connect(relative2, "Local Rot", mult_ltg_box, "Base")
    connect(swing_box, "Rotation", mult_ltg_box, "Local Rot")
    connect(mult_ltg_box, "Global Rot", dst_box, "Lcl Rotation")
    swing_relation.Active = True

    parent_constraint(parent, find_by_name(parent.Name.replace("MB_Control_", "")))
    return swing_relation


def get_tpose_rotate(name):
    ldata = find_by_name(name).PropertyList.Find("Lcl Rotation").Data
    return ldata


def get_tpose_list():
    lposelist = []
    jointlist = ["Shoulder_L", "Shoulder_R", "Elbow_L", "Elbow_R", "Wrist_L", "Wrist_R"]
    for joint in jointlist:
        lposelist.append(get_tpose_rotate(joint))
    return lposelist


def get_pre_ro_by_name(name_list):
    pre_ro = {}
    for name in name_list:
        pre_ro[name] = find_by_name(name).PropertyList.Find("PreRotation").Data
    return pre_ro


def create_parent_constraint_more_parent(src_list, weights, dst):
    constraint = create_constraints("Parent/Child", "CHAR_Deformation_"+dst.Name+"Parent")
    for src, weight in zip(src_list, weights):
        constraint.PropertyList.Find("Source (Parent)").append(src)
        constraint.PropertyList.Find(src.Name+".Weight").Data = weight*100
    constraint.PropertyList.Find("Constrained object (Child)").append(dst)
    constraint.Snap()
    constraint.Active = True


def main():
    pre_list_untwist = ["Shoulder_L", "Shoulder_R", "Hip_L", "Hip_R"]
    pre_list_follow = ["Wrist_L", "Wrist_R", "Ankle_L", "Ankle_R"]
    untwist_pre_ro = get_pre_ro_by_name(pre_list_untwist)
    follow_pre_ro = get_pre_ro_by_name(pre_list_follow)


    FBSystem().Scene.Evaluate()
    # tpose_data = get_tpose_list()
    #
    # actpose = FBVector3d(0, 0, 0)
    # jointlist = ["Shoulder_L", "Shoulder_R", "Elbow_L", "Elbow_R", "Wrist_L", "Wrist_R"]
    # for joint in jointlist:
    #     find_by_name(joint).PropertyList.Find("Lcl Rotation").Data = actpose
    #
    FBModelNull("Driver_system")

    # 复制骨骼
    create_mb_control()
    # ad_copy.main()

    # untwist
    FBSystem().Scene.Evaluate()
    parent_list = ["MB_Control_Shoulder_L", "MB_Control_Shoulder_R", "MB_Control_Hip_L", "MB_Control_Hip_R"]
    for parent in parent_list:
        re_order_all(find_by_name(parent))
    FBSystem().Scene.Evaluate()
    for parent in parent_list:
        create_untwist(parent, untwist_pre_ro)

    # untwist 的传递
    untwist_list = [[find_by_name("MB_Control_Shoulder_L_unTwist"), find_by_name("MB_Control_Shoulder_L")],
                   [find_by_name("MB_Control_Shoulder_R_unTwist"), find_by_name("MB_Control_Shoulder_R")],
                   [find_by_name("MB_Control_Hip_L_unTwist"), find_by_name("MB_Control_Hip_L")],
                    [find_by_name("MB_Control_Hip_R_unTwist"), find_by_name("MB_Control_Hip_R")]]
    untwist_weight = [[1, 0], [0.5, 0.5], [0, 1]]
    ldstBlist = [["Shoulder_L", "ShoulderPart1_L", "ShoulderPart2_L"],
                ["Shoulder_R", "ShoulderPart1_R", "ShoulderPart2_R"],
                ["Hip_L", "HipPart1_L", "HipPart2_L"],
                ["Hip_R", "HipPart1_R", "HipPart2_R"]]
    for untwist, ldstlist in zip(untwist_list, ldstBlist):
        for weight, dst in zip(untwist_weight, ldstlist):
            create_parent_constraint_more_parent(untwist, weight, find_by_name(dst))
    # follow twist
    parent_list = ["MB_Control_Wrist_L", "MB_Control_Wrist_R", "MB_Control_Ankle_L", "MB_Control_Ankle_R"]
    follow_twist_list = ["MB_Control_Wrist_L_followTwist", "MB_Control_Wrist_R_followTwist", "MB_Control_Ankle_L_followTwist", "MB_Control_Ankle_R_followTwist"]
    for parent, follow_twist in zip(parent_list, follow_twist_list):
        wrist_follow_twist(parent, follow_twist, follow_pre_ro)

    # follow twist的传递
    followTwist_list = [[find_by_name("MB_Control_Wrist_L_followTwist"), find_by_name("MB_Control_Elbow_L")],
                    [find_by_name("MB_Control_Wrist_R_followTwist"), find_by_name("MB_Control_Elbow_R")],
                    [find_by_name("MB_Control_Ankle_L_followTwist"), find_by_name("MB_Control_Knee_L")],
                    [find_by_name("MB_Control_Ankle_R_followTwist"), find_by_name("MB_Control_Knee_R")]]
    followTwist_weight = [[0, 1], [0.5, 0.5], [1, 0]]
    ldstBlist = [["Elbow_L", "ElbowPart1_L", "ElbowPart2_L"],
                 ["Elbow_R", "ElbowPart1_R", "ElbowPart2_R"],
                 ["Knee_L", "KneePart1_L", "KneePart2_L"],
                 ["Knee_R", "KneePart1_R", "KneePart2_R"]]
    for followTwist, ldstlist in zip(followTwist_list, ldstBlist):
        followTwist[1].PropertyList.Find("RotationMinX").Data = True
        followTwist[1].PropertyList.Find("RotationMaxX").Data = True
        followTwist[1].PropertyList.Find("RotationMinY").Data = True
        followTwist[1].PropertyList.Find("RotationMaxY").Data = True
        for weight, dst in zip(followTwist_weight, ldstlist):
            create_parent_constraint_more_parent(followTwist, weight, find_by_name(dst))

    FBSystem().Scene.Evaluate()

