# coding:utf-8
import re
from maya import cmds, mel
from . import ADPose


SNone, SInit, SJoint, SPoseBall, SRigPolygon, STwoPolygon, SDupPolygon, SCtrl = range(8)


def exist_little():
    return cmds.objExists("|ADPoseLittleRoot")


def is_shape(obj, typ):
    if cmds.nodeType(obj) != "transform":
        return False
    shapes = cmds.listRelatives(obj, s=True, ni=True)
    if not shapes:
        return False
    if cmds.nodeType(shapes[0]) != typ:
        return False
    return True


def get_selected_type():
    selected = cmds.ls(sl=1, o=1, type=["joint", "transform"]) or []
    selected_length = len(selected)
    if selected_length == 0:
        return SNone
    if selected_length > 2:
        return SNone
    context = ["scaleSuperContext", "RotateSuperContext", "moveSuperContext", "selectSuperContext"]
    if cmds.currentCtx() not in context:
        return SNone
    if not exist_little():
        if selected_length != 1:
            return SNone
        sel = selected[0]
        if cmds.nodeType(sel) != "joint":
            return SNone
        return SInit
    if selected_length == 1:
        sel = selected[0]
        if cmds.nodeType(sel) not in ["transform", "joint"]:
            return SNone
        ad = get_ad()
        if ad is None:
            return SNone
        if cmds.nodeType(sel) == "joint":
            if ad.joint != sel:
                return SInit
            return SJoint
        if sel.startswith("ADPoseLittlePoseBall"):
            return SPoseBall
        if sel == ad.control:
            return SCtrl
        if is_shape(sel, "mesh"):
            full_path = cmds.ls(sel, l=True)[0] if cmds.ls(sel, l=True) else ""
            if "|lush_duplicate_edit" in full_path:
                return SDupPolygon
            else:
                return SRigPolygon
        return SNone
    if selected_length == 2:
        src, dst = selected
        if not is_shape(src, "mesh"):
            return SNone
        if not is_shape(dst, "mesh"):
            return SNone
        return STwoPolygon
    return SNone


class LADPoseLittleSelectedJob(object):

    def __repr__(self):
        return self.__class__.__name__

    def __call__(self):
        add_menu()

    def add_job(self):
        self.del_job()
        cmds.scriptJob(e=["SelectionChanged", self])
        cmds.scriptJob(e=["ToolChanged", self])

    @classmethod
    def del_job(cls):
        for job in cmds.scriptJob(listJobs=True) or []:
            if repr(cls.__name__) in job:
                cmds.scriptJob(kill=int(job.split(":")[0]))


ADPoseLittleMenu = "ADPoseMenu"


def del_menu():
    if cmds.popupMenu(ADPoseLittleMenu, q=1, ex=1):
        cmds.deleteUI(ADPoseLittleMenu)


def add_menu():
    del_menu()
    typ = get_selected_type()
    if typ == SNone:
        return
    menu = cmds.popupMenu(ADPoseLittleMenu, button=1, ctl=1, alt=0, sh=0, allowOptionBoxes=1, p="viewPanes", mm=1)
    cmds.menuItem(p=menu, l=u"关闭工具", rp="E", c=menu_close_tool)
    if typ == SInit:
        cmds.menuItem(p=menu, l=u"创建驱动球", rp="N", c=menu_add_driver_ball)
    cmds.menuItem(p=menu, l=u"删除驱动球", rp="N", c=menu_del_driver_ball)
    if typ in [SCtrl]:
        cmds.menuItem(p=menu, l=u"添加姿势", rp="W", c=menu_add_pose)
    if typ == SPoseBall:
        cmds.menuItem(p=menu, l=u"删除姿势", rp="SW", c=menu_del_pose)
        cmds.menuItem(p=menu, l=u"转到姿势", rp="S", c=menu_to_pose)
    if typ == SRigPolygon:
        cmds.menuItem(p=menu, l=u"复制并修改姿势", rp="NW", c=menu_dup_edit)
        cmds.menuItem(p=menu, l=u"镜像姿势", rp="SE", c=menu_mirror_pose)
    if typ == SDupPolygon:
        cmds.menuItem(p=menu, l=u"结束姿势修改", rp="NW", c=menu_edit_finish)
    if typ == STwoPolygon:
        cmds.menuItem(p=menu, l=u"修改姿势", rp="NW", c=menu_edit_pose)
        cmds.menuItem(p=menu, l=u"包裹传递", c=menu_warp_copy)


def del_driver_ball():
    nodes = cmds.ls("|ADPoseLittle*") or []
    if nodes:
        cmds.delete(nodes)
    edit_finish()


def add_driver_ball(joint=None):
    del_driver_ball()
    if joint is None:
        joints = cmds.ls(type="joint", o=1, sl=1) or []
        if not len(joints) == 1:
            return cmds.warning("please select a joint")
        joint = joints[0]
    if joint is None:
        return
    prefix = "ADPoseLittle"
    if cmds.objExists(prefix + "Root"):
        cmds.delete(prefix + "Root")
    nodes = cmds.ls(prefix + "*") or []
    if nodes:
        cmds.delete(nodes)
    root = cmds.group(em=1, n=prefix + "Root")
    parent = cmds.listRelatives(joint, p=True)
    parent = parent[0] if parent else None
    if parent is not None:
        cmds.parentConstraint(parent, root)
    back = cmds.sphere(ch=0, n=prefix + "BACK")[0]
    cmds.parent(back, root)
    joint_matrix = cmds.xform(joint, q=True, m=True, ws=True)
    cmds.xform(back, m=joint_matrix, ws=True)

    cmds.setAttr(back + ".s", 1, 1, 1)
    cmds.parent(cmds.pointConstraint(joint, back), root)
    joint_orient = cmds.getAttr(joint + ".jointOrient")[0]
    cmds.setAttr(back + ".r", *joint_orient)
    if not cmds.attributeQuery("ADPoseLittleRadius", node=joint, exists=True):
        cmds.addAttr(joint, ln="ADPoseLittleRadius", at="double", k=0, dv=1)
        cmds.setAttr(joint + ".ADPoseLittleRadius", e=1, channelBox=1)
        if parent is not None:
            parent_pos = cmds.xform(parent, q=True, t=True, ws=True)
            joint_pos = cmds.xform(joint, q=True, t=True, ws=True)
            radius = ((parent_pos[0] - joint_pos[0])**2 +
                      (parent_pos[1] - joint_pos[1])**2 +
                      (parent_pos[2] - joint_pos[2])**2) ** 0.5
            cmds.setAttr(joint + ".ADPoseLittleRadius", radius * 0.7)
    cmds.connectAttr(joint + ".ADPoseLittleRadius", back + ".scaleX")
    cmds.connectAttr(joint + ".ADPoseLittleRadius", back + ".scaleY")
    cmds.connectAttr(joint + ".ADPoseLittleRadius", back + ".scaleZ")
    back_shape = cmds.listRelatives(back, s=True, ni=True)[0]
    cmds.setAttr(back_shape + ".overrideEnabled", 1)
    cmds.setAttr(back_shape + ".overrideDisplayType", 2)
    back_lbt = cmds.shadingNode('lambert', asShader=True, n=prefix + "BAKE_LBT")
    cmds.select(cl=1)
    back_sg = cmds.sets(n=prefix + "BACK_SG", r=1)
    cmds.connectAttr(back_lbt + ".outColor", back_sg + ".surfaceShader", f=1)
    cmds.setAttr(back_lbt + ".transparency", 0.8, 0.8, 0.8, type="double3")
    cmds.sets(back, e=1, forceElement=back_sg)
    if not cmds.attributeQuery("ADPoseLittle_Axis", node=joint, exists=True):
        cmds.addAttr(joint, ln="ADPoseLittle_Axis", at="long", k=0, min=-1, max=1, dv=1)
        cmds.setAttr(joint + ".ADPoseLittle_Axis", e=1, channelBox=1)
        if cmds.getAttr(back + ".tx") < 0:
            cmds.setAttr(joint + ".ADPoseLittle_Axis", -1)
        else:
            cmds.setAttr(joint + ".ADPoseLittle_Axis", 1)
    update_pose_ball()


def update_pose_ball():
    prefix = "ADPoseLittle"
    joint = get_driver_joint()
    back_nodes = cmds.ls(prefix + "BACK") or []
    if not back_nodes:
        return
    back = back_nodes[0]
    children = cmds.listRelatives(back, type="transform") or []
    if children:
        cmds.delete(children)
    # Identity matrix as list
    identity_matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    pose_name_matrix = [["bindPose", identity_matrix]]
    ad = ADPose.ADPoses.load_by_name(joint)
    if ad is None:
        cmds.warning("ADPose not found for joint: " + joint)
        return
    for pose in ad.get_poses():
        matrix = ADPose.pose_to_matrix(pose)
        name = "_a%i_d%i" % pose
        pose_name_matrix.append([name, matrix])
    for name, matrix in pose_name_matrix:
        group = cmds.group(em=1, n=prefix + name + "_GROUP", p=back)
        cmds.xform(group, m=matrix)
        cmds.setAttr(group + ".t", 0, 0, 0)
        ball = cmds.sphere(ch=0, n=prefix + "PoseBall" + name)[0]
        cmds.parent(ball, group)
        cmds.setAttr(ball + ".r", 0, 0, 0)
        cmds.setAttr(ball + ".s", 0.05, 0.05, 0.05)
        cmds.setAttr(ball + ".t", 0, 0, 0)
        cmds.connectAttr(joint + ".ADPoseLittle_Axis", ball + ".tx")
        ball_lbt = cmds.shadingNode('lambert', asShader=True, n=prefix + name + "_LBT")
        cmds.select(cl=1)
        ball_sg = cmds.sets(n=prefix + name + "_SG", r=1)
        cmds.connectAttr(ball_lbt + ".outColor", ball_sg + ".surfaceShader", f=1)
        cmds.setAttr(ball_lbt + ".transparency", 0.5, 0.5, 0.5, type="double3")
        cmds.sets(ball, e=1, forceElement=ball_sg)
        # Calculate color based on matrix - simplified version
        # Original: ball_lbt.color.set(color * matrix)
        # For now, just set a base color
        cmds.setAttr(ball_lbt + ".color", 1, 0, 0, type="double3")
        cmds.setAttr(ball + ".t", l=True)
        cmds.setAttr(ball + ".r", l=True)
        cmds.setAttr(ball + ".s", l=True)


def close_tool():
    print("close tool")
    LADPoseLittleSelectedJob().del_job()
    del_driver_ball()
    del_menu()


def open_tool():
    close_tool()
    LADPoseLittleSelectedJob().add_job()
    add_menu()


def get_driver_joint():
    if not exist_little():
        return None
    if not cmds.objExists("ADPoseLittleBACK"):
        return None
    connections = cmds.listConnections("ADPoseLittleBACK.sx", type="joint") or []
    if not len(connections) == 1:
        return None
    joint = connections[0]
    return joint


def get_ad():
    joint = get_driver_joint()
    if joint is None:
        return None
    return ADPose.ADPoses.load_by_name(joint)


def edit_finish():
    if cmds.objExists("|adPoses"):
        ADPose.ADPoses.auto_edit()
    nodes = cmds.ls("|adPoses") or []
    if nodes:
        cmds.delete(nodes)


def menu_keep_selected(fun):
    def _fun(*args, **kwargs):
        sel = cmds.ls(sl=1) or []
        result = fun(*args, **kwargs)
        existing = cmds.ls(sel) or []
        if existing:
            cmds.select(existing)
        return result
    return _fun


def after(after_fun):
    def _add_after(fun):
        def _fun(*args, **kwargs):
            result = fun(*args, **kwargs)
            after_fun()
            return result
        return _fun
    return _add_after


@menu_keep_selected
@after(add_menu)
def menu_add_driver_ball(*args):
    add_driver_ball()


def menu_close_tool(*args):
    close_tool()


@menu_keep_selected
@after(add_menu)
def menu_del_driver_ball(*args):
    del_driver_ball()


@menu_keep_selected
@after(update_pose_ball)
def menu_add_pose(*args):
    ad = get_ad()
    if ad is None:
        return
    ad.add_pose(ad.get_control_pose())


@menu_keep_selected
@after(update_pose_ball)
def menu_del_pose(*args):
    ad = get_ad()
    if ad is None:
        return
    selected = cmds.ls(sl=1, type="transform", o=1) or []
    if not selected:
        return
    ball = selected[0]
    pattern = re.match("^ADPoseLittlePoseBall_a([0-9]{1,3})_d([0-9]{1,3})$", ball)
    if not pattern:
        return
    angle, direction = pattern.groups()
    angle, direction = int(angle), int(direction)
    ad.delete_poses([(angle, direction)])


@menu_keep_selected
@after(update_pose_ball)
def menu_edit_pose(*args):
    ad = get_ad()
    if ad is None:
        return
    ad.auto_edit_by_selected_target([ad.joint])


def menu_warp_copy(*args):
    ad = get_ad()
    if ad is None:
        return
    targets = [ad.target_name(pose) for pose in ad.get_poses()]
    ad.warp_copy_targets(targets)


def menu_dup_edit(*args):
    joint = get_driver_joint()
    if joint is None:
        return
    ADPose.ADPoses.auto_apply([joint])


@after(update_pose_ball)
def menu_edit_finish(*args):
    joint = get_driver_joint()
    if joint is None:
        return
    ADPose.ADPoses.auto_apply([joint])

@menu_keep_selected
def menu_mirror_pose(*args):
    ad = get_ad()
    if ad is None:
        return
    targets = [ad.target_name(pose) for pose in ad.get_poses()]
    ad.mirror_by_targets(targets)


def menu_to_pose(*args):
    ad = get_ad()
    if ad is None:
        return
    if ad.control is None:
        return
    selected = cmds.ls(sl=1, type="transform", o=1) or []
    if not selected:
        return
    ball = selected[0]
    ball_parent = cmds.listRelatives(ball, p=True)
    if ball_parent:
        parent_matrix = cmds.xform(ball_parent[0], q=True, m=True)
        cmds.xform(ad.control, m=parent_matrix)


def test():
    close_tool()
    cmds.select("Shoulder_L")
    menu_add_driver_ball()
    cmds.select("ADPoseLittlePoseBall_a90_d90")
    menu_del_pose()
