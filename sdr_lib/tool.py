from maya import cmds, mel
from . import api_core
from . import np_core
from .. import ADPose
from .. import joints


def f16_to_m44(f16):
    return [f16[i*4:i*4+4] for i in range(4)]


def get_joints_matrix(joints_name):
    return [f16_to_m44(cmds.xform(name, q=1, ws=1, m=1)) for name in joints_name]


def set_joints_matrix(joints_name, joints_matrix):
    for name, matrix in zip(joints_name, joints_matrix):
        cmds.xform(name, ws=1, m=sum(matrix, []))


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


def get_selected_polygon():
    for polygon in filter(is_polygon, cmds.ls(sl=1, type="transform")):
        return polygon
    return ""


def find_skin_cluster(polygon_name):
    if not is_polygon(polygon_name):
        return
    shapes = cmds.listRelatives(polygon_name, s=1)
    for skin_cluster in cmds.ls(cmds.listHistory(polygon_name), type="skinCluster"):
        for shape in cmds.skinCluster(skin_cluster, q=1, geometry=1):
            if shape in shapes:
                return skin_cluster


def get_sdr_joint(parent, i):
    n = "corrective_{0}_{1:0>2}_sdr".format(parent, i)
    if cmds.objExists(n):
        i += 1
        return get_sdr_joint(parent, i)
    else:
        cmds.joint(parent, n=n)
        return n


def clear_orig(polygon):
    for shape in cmds.listRelatives(polygon, s=1):
        if cmds.getAttr(shape+".io"):
            cmds.delete(shape)


def sort_targets(target_names):
    filters = [ADPose.target_is_pose, ADPose.target_is_comb, ADPose.target_is_ib]
    return sum([list(filter(f, target_names)) for f in filters], [])


def part_deform_to_skin(deform_polygon, skin_polygon, target_names, unlock_joints, max_influence, new_joint_count,
                        iter_count, duplicate, scale):
    # get sdr args
    ADPose.ADPoses.set_pose_by_targets([])
    skin_cluster = find_skin_cluster(skin_polygon)
    weights = api_core.get_py_weights(skin_polygon)
    joints_name = cmds.skinCluster(skin_cluster, q=1, influence=1)
    joints_bind_matrix = get_joints_matrix(joints_name)
    orig_points = api_core.get_py_points(skin_polygon)
    target_names = sort_targets(target_names)
    anis_points = []
    anis_joints_matrix = []
    for target_name in target_names:
        ADPose.ADPoses.set_pose_by_targets([target_name])
        cmds.refresh()
        anis_joints_matrix.append(get_joints_matrix(joints_name))
        anis_points.append(api_core.get_py_points(deform_polygon))
    ADPose.ADPoses.set_pose_by_targets([])
    cmds.refresh()
    indices = [joints_name.index(n) for n in unlock_joints]
    joints_bind_matrix, anis_joints_matrix, solve_vtx_ids, weights, follow_weights = np_core.run(
        np_core.part_deform_to_skin,
        orig_points=orig_points,
        joints_bind_matrix=joints_bind_matrix,
        weights=weights,
        anis_points=anis_points,
        anis_joints_matrix=anis_joints_matrix,
        unlock_joints=indices,
        max_influence=max_influence,
        new_joint_count=new_joint_count,
        iter_count=iter_count,
        scale=scale,
    )
    sdr_names = []
    for i, ws in enumerate(follow_weights):
        parent_joint = unlock_joints[ws.index(max(ws))]
        sdr_names.append(get_sdr_joint(parent_joint, i))

    set_joints_matrix(sdr_names, joints_bind_matrix)
    if duplicate:
        result_skin_polygon = cmds.duplicate(skin_polygon)[0]
        clear_orig(result_skin_polygon)
        cmds.skinCluster(joints_name+sdr_names, result_skin_polygon, tsb=1)
        cmds.select(skin_polygon, result_skin_polygon)
        mel.eval("CopySkinWeights")
    else:
        cmds.skinCluster(skin_cluster, e=1, lw=1, ai=sdr_names)
        result_skin_polygon = skin_polygon

    skin_cluster = find_skin_cluster(result_skin_polygon)
    joints_name = cmds.skinCluster(skin_cluster, q=1, influence=1)
    indices = [joints_name.index(n) for n in unlock_joints+sdr_names]
    api_core.set_py_part_weight(result_skin_polygon, indices, solve_vtx_ids, weights)

    # create plane
    cmds.select(sdr_names)
    joints.create_plane_by_selected()
    plane = "BodyDeformSdkPlane"
    # edit follow weight
    skin_cluster = find_skin_cluster(plane)
    joints_name = cmds.skinCluster(skin_cluster, q=1, influence=1)
    follow_joints = [joint for joint in unlock_joints if joint not in joints_name]
    if len(follow_joints):
        cmds.skinCluster(skin_cluster, e=1, lw=1, ai=follow_joints)
    joints_name = cmds.skinCluster(skin_cluster, q=1, influence=1)
    vtx_count = cmds.polyEvaluate(plane, v=1)
    indices = [joints_name.index(n) for n in unlock_joints]
    vtx_ids = range(vtx_count-new_joint_count*4, vtx_count, 1)
    follow_weights = [ws for ws in follow_weights for _ in range(4)]
    api_core.set_py_part_weight(plane, indices, vtx_ids, follow_weights)

    for target_name, joints_matrix in zip(target_names, anis_joints_matrix):
        ADPose.ADPoses.set_pose_by_targets([target_name])
        cmds.refresh()
        set_joints_matrix(sdr_names, joints_matrix)
        joints.body_deform_sdk(target_names)
    ADPose.ADPoses.set_pose_by_targets([])
    cmds.refresh()


def test_deform_to_skin():
    unlock_joints = ["Wrist_L", "ElbowPart2_L"]
    target_names = ["Wrist_L_a90_d0", "Wrist_L_a90_d270", "Wrist_L_a90_d90", "Wrist_L_a90_d180"]

    unlock_joints = ["ThumbFinger3_L", "ThumbFinger2_L"]
    target_names = ["ThumbFinger3_L_a90_d270"]
    deform_polygon = "skin_polygon"
    skin_polygon = "skin_polygon"
    new_joint_count = 1
    max_influence = 4
    iter_count = 15
    duplicate = True
    part_deform_to_skin(
        deform_polygon, skin_polygon, target_names, unlock_joints, max_influence, new_joint_count,
        iter_count, duplicate)


def test_svd_scale():
    src_polygon = "pCube2"
    dst_polygon = "pCube1"
    src_points = api_core.get_py_points(src_polygon)
    dst_points = api_core.get_py_points(dst_polygon)
    r = np_core.run(
        np_core.test_svd,
        src_points=src_points,
        dst_points=dst_points,
    )
    joint = cmds.joint(None)
    set_joints_matrix([joint], [r[0]])

    cmds.skinCluster(joint, src_polygon)
    set_joints_matrix([joint], [r[1]])



def doit():
    test_deform_to_skin()
    # default args

