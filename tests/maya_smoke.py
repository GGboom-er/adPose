"""Non-saving regression for exact mirrored pose matrices in the open Maya scene."""

import math

from maya import cmds

from adPose import ADPose


IDENTITY = [
    1.0, 0.0, 0.0, 0.0,
    0.0, 1.0, 0.0, 0.0,
    0.0, 0.0, 1.0, 0.0,
    0.0, 0.0, 0.0, 1.0,
]


def _matrix(node):
    return [
        float(value) for value in cmds.xform(
            node, query=True, matrix=True, objectSpace=True
        )
    ]


def _position(node):
    return [
        float(value) for value in cmds.xform(
            node, query=True, translation=True, worldSpace=True
        )
    ]


def _matrix_error(first, second):
    return max(abs(a - b) for a, b in zip(first, second))


def _blendshape_state():
    return {
        node: {
            "aliases": cmds.aliasAttr(node, query=True) or [],
            "incoming": cmds.listConnections(
                node, source=True, destination=False, plugs=True,
                connections=True
            ) or [],
        }
        for node in cmds.ls(type="blendShape") or []
    }


def _saved_mirror_pairs():
    pairs = []
    for target in ADPose.ADPoses.get_targets():
        if "_L_a" not in target or not ADPose.target_is_pose(target):
            continue
        source_ad, source_pose = ADPose.ADPoses.target_to_ad_pose(target)
        if source_ad.get_saved_pose_matrix(source_pose) is None:
            continue
        mirrored = ADPose.ADPoses.targets_to_mirror([target])
        if len(mirrored) != 1 or mirrored[0][0] == mirrored[0][1]:
            continue
        destination = mirrored[0][1]
        destination_data = ADPose.ADPoses.targets_to_ad_poses([destination])
        if len(destination_data) != 1:
            continue
        destination_ad, destination_poses = destination_data[0]
        if len(destination_poses) != 1:
            continue
        if destination_ad.get_saved_pose_matrix(destination_poses[0]) is None:
            continue
        pairs.append((target, destination))
    return pairs


def _controls():
    controls = []
    for joint in cmds.ls("*.angle", objectsOnly=True, type="joint") or []:
        ad = ADPose.ADPoses.load_by_name(joint)
        if ad and ad.control not in controls:
            controls.append(ad.control)
    return controls


def _joint_pairs(source_joint):
    pairs = []
    descendants = cmds.listRelatives(
        source_joint, allDescendents=True, type="joint"
    ) or []
    for source in [source_joint] + descendants:
        short_name = source.split("|")[-1]
        if "_L" not in short_name or "RBF" in short_name:
            continue
        destination = ADPose.find_node_by_name(short_name.replace("_L", "_R"))
        if destination:
            pairs.append((source, destination))
    return pairs


def run():
    """Run mirror/driver checks and restore the open scene without saving."""
    target_pairs = _saved_mirror_pairs()
    if not target_pairs:
        raise RuntimeError("No saved L/R adPose matrix pairs found in the scene")

    controls = _controls()
    control_matrices = {control: _matrix(control) for control in controls}
    selection = cmds.ls(selection=True, long=True) or []
    blendshapes = _blendshape_state()
    report = {}
    blendshapes_unchanged = False
    controls_restored = False

    cmds.undoInfo(openChunk=True, chunkName="adPoseMayaSmoke")
    try:
        for source, destination in target_pairs:
            source_ad, source_pose = ADPose.ADPoses.target_to_ad_pose(source)
            destination_ad, destination_pose = ADPose.ADPoses.target_to_ad_pose(
                destination
            )
            source_matrix = source_ad.get_saved_pose_matrix(source_pose)
            destination_matrix = destination_ad.get_saved_pose_matrix(
                destination_pose
            )

            for control in controls:
                cmds.xform(control, matrix=IDENTITY, objectSpace=True)
            ADPose.ADPoses.set_pose_by_target(source, 60)
            source_positions = {
                joint: _position(joint)
                for joint, _ in _joint_pairs(source_ad.joint)
            }

            for control in controls:
                cmds.xform(control, matrix=IDENTITY, objectSpace=True)
            ADPose.ADPoses.set_pose_by_target(destination, 60)
            position_errors = []
            for source_joint, destination_joint in _joint_pairs(source_ad.joint):
                source_position = source_positions[source_joint]
                expected = [
                    -source_position[0], source_position[1], source_position[2]
                ]
                actual = _position(destination_joint)
                position_errors.append(math.sqrt(sum(
                    (value - target) ** 2
                    for value, target in zip(actual, expected)
                )))

            weight_60 = float(cmds.getAttr(
                destination_ad.reference + "." + destination
            ))
            for control in controls:
                cmds.xform(control, matrix=IDENTITY, objectSpace=True)
            ADPose.ADPoses.set_pose_by_target(destination, 59)
            weight_59 = float(cmds.getAttr(
                destination_ad.reference + "." + destination
            ))

            matrix_error = _matrix_error(source_matrix, destination_matrix)
            position_error = max(position_errors or [0.0])
            if matrix_error > 1e-10:
                raise AssertionError("{} matrix error {}".format(
                    destination, matrix_error
                ))
            if abs(weight_60 - 1.0) > 1e-6:
                raise AssertionError("{} weight at 60 is {}".format(
                    destination, weight_60
                ))
            if position_error > 1e-5:
                raise AssertionError("{} mirror error {}".format(
                    destination, position_error
                ))
            if not 0.9 <= weight_59 <= 1.0:
                raise AssertionError("{} discontinuous weight at 59: {}".format(
                    destination, weight_59
                ))
            report[destination] = {
                "matrix_error": matrix_error,
                "position_error": position_error,
                "weight_59": weight_59,
                "weight_60": weight_60,
            }
    finally:
        for control, matrix in control_matrices.items():
            if cmds.objExists(control):
                cmds.xform(control, matrix=matrix, objectSpace=True)
        if selection:
            cmds.select(selection, replace=True)
        else:
            cmds.select(clear=True)
        cmds.undoInfo(closeChunk=True)
        blendshapes_unchanged = blendshapes == _blendshape_state()
        controls_restored = not any(
            _matrix_error(_matrix(control), matrix) > 1e-7
            for control, matrix in control_matrices.items()
            if cmds.objExists(control)
        )
        cmds.undo()
        if selection:
            cmds.select(selection, replace=True)
        else:
            cmds.select(clear=True)

    if not blendshapes_unchanged:
        raise AssertionError("BlendShape aliases or incoming connections changed")
    if not controls_restored:
        raise AssertionError("Control matrices were not restored")
    return {"status": "SUCCESS", "count": len(report), "targets": report}


if __name__ == "__main__":
    print(run())
