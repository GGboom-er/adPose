from adPose2 import ADPose
import pymel.core as pm


def key_poses():
    joints = pm.selected(type="joint")
    t = 0
    target_names = []
    ctrls = []
    for ad, pose_list in ADPose.ADPoses.targets_to_ad_poses(ADPose.ADPoses.get_targets()):
        ctrl = ad.control
        ctrls.append(ctrl)
        pm.setKeyframe(ctrl, t=t, v=0, at='rx')
        pm.setKeyframe(ctrl, t=t, v=0, at='ry')
        pm.setKeyframe(ctrl, t=t, v=0, at='rz')
        for pose in pose_list:
            target_names.append(ad.target_name(pose))
            print ad.target_name(pose)
            t += 1
            matrix = ADPose.pose_to_matrix(pose)
            trans_matrix = pm.datatypes.TransformationMatrix(matrix)
            rotate = trans_matrix.getRotation()
            rotate.setDisplayUnit("degrees")
            rotate.reorderIt(ctrl.rotateOrder.get())
            pm.setKeyframe(ctrl, t=t, v=rotate.x, at='rx')
            pm.setKeyframe(ctrl, t=t, v=rotate.y, at='ry')
            pm.setKeyframe(ctrl, t=t, v=rotate.z, at='rz')
        pm.setKeyframe(ctrl, t=t+1, v=0, at='rx')
        pm.setKeyframe(ctrl, t=t+1, v=0, at='ry')
        pm.setKeyframe(ctrl, t=t+1, v=0, at='rz')
    pm.playbackOptions(e=1, min=1, ast=1, max=t, aet=t)
    pm.bakeResults(joints, t="1:%i" % t, simulation=1)
    pm.cutKey(ctrls, clear=1, time=":")
    for ctrl in ctrls:
        ctrl.r.set(0, 0, 0)


if __name__ == '__main__':
    key_poses()





