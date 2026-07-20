from maya import cmds, mel
from .core import FacePin
from . import bs


def connect_attr(src, dst):
    if not cmds.objExists(src):
        return
    if not cmds.objExists(dst):
        return
    if not cmds.isConnected(src, dst):
        cmds.connectAttr(src, dst, f=1)


def get_unlock_joints(polygon):
    joints = cmds.skinCluster(polygon, q=1, inf=1)
    joints = [joint for joint in joints if cmds.nodeType(joint) == "joint" and not cmds.getAttr(joint+'.liw')]
    return joints


def tool_build_pin_driver_by_bs():
    src, dst = cmds.ls(sl=1, o=1)
    src_bs = cmds.ls(cmds.listHistory(src), type="blendShape")[0]
    targets = cmds.listAttr(src_bs+".weight", m=1)
    joints = get_unlock_joints(dst)
    fp = FacePin("FaceSdrPlane")
    fp.load()
    cmds.currentTime(1)
    for joint in joints:
        fp.add_pin(joint, cmds.xform(joint, ws=1, m=1, q=1))
    fp.build()
    pl = "FaceSdrPlanePlane"
    dst_bs = bs.get_bs(pl)
    for i, target in enumerate(targets):
        cmds.currentTime(i+2)
        if cmds.objExists(dst_bs+"."+target):
            cmds.setAttr(dst_bs+"."+target, 1)
        sdk_target = fp.build_target(lambda x: x)
        bs.edit_target(sdk_target, pl, target)
        if cmds.objExists(dst_bs+"."+target):
            cmds.setAttr(dst_bs+"."+target, 0)
    for joint in joints:
        mel.eval('cutKey -clear -time ":" ' + joint)
        if cmds.listConnections(joint, s=1, d=0, type="parentConstraint"):
            continue
        cmds.parent(cmds.parentConstraint(joint+"Pin", joint), joint+"Pin")


def edit_fp_target(target):
    fp = FacePin("FaceSdrPlane")
    fp.load()
    pl = "FaceSdrPlanePlane"
    sdk_target = fp.build_target(lambda x: x)
    bs.edit_target(sdk_target, pl, target)


def find_targets(max_value=0.99):
    pl = 'FaceSdrPlanePlane'
    _bs = bs.find_bs(pl)
    targets = []
    for target in cmds.listAttr(_bs+".weight", m=1):
        weight = cmds.getAttr(_bs+"."+target)
        if weight < max_value:
            continue
        targets.append(target)
    return targets


def temp_scale():
    for ctrl in cmds.ls(sl=1):
        cmds.setAttr(ctrl+".ty", 0.85)
        for target in find_targets(max_value=0.6):
            edit_fp_target(target)
        cmds.setAttr(ctrl + ".ty", 0.0)


def temp_mirror():
    pl = 'FaceSdrPlanePlane'
    _bs = bs.find_bs(pl)
    for target in find_targets():
        print (target)
        if target[-1] != "R":
            continue
        print (target[:-1] + "L", target)
        bs.mirror_target(_bs, target[:-1] + "L", target)


def temp_flip():
    pl = 'FaceSdrPlanePlane'
    _bs = bs.find_bs(pl)
    for target in find_targets():
        bs.mirror_target(_bs, target, target)


def test():
    # target = "mouthLipsTogetherD"
    # target = "mouthLipsTowardsU"
    # target = "mouthLipsTowardsU"
    # target = "mouthCornerPullL"
    # target = "mouthDimpleR"
    # target = "mouthFunnel"
    # target = "mouthSticky"
    # target = "mouthLipsPurse"
    # target = "mouthUpperLipRaise"
    # target = "mouthLowerLipDepress"
    # target = "jawOpen"
    target = "mouthCornerDepressL"
