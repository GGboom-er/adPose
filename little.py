# coding:utf-8
import re
import pymel.core as pm
from maya import cmds
from . import ADPose


SNone, SInit, SJoint, SPoseBall, SRigPolygon, STwoPolygon, SDupPolygon, SCtrl = range(8)


def exist_little():
    return pm.objExists("|ADPoseLittleRoot")


def is_shape(obj, typ):
    if obj.type() != "transform":
        return False
    shape = obj.getShape()
    if not shape:
        return False
    if shape.type() != typ:
        return False
    return True


def get_selected_type():
    selected = pm.ls(sl=1, o=1, type=["joint", "transform"])
    selected_length = len(selected)
    if selected_length == 0:
        return SNone
    if selected_length > 2:
        return SNone
    context = ["scaleSuperContext", "RotateSuperContext", "moveSuperContext", "selectSuperContext"]
    if pm.currentCtx() not in context:
        return SNone
    if not exist_little():
        if selected_length != 1:
            return SNone
        sel = selected[0]
        if sel.type() != "joint":
            return SNone
        return SInit
    if selected_length == 1:
        sel = selected[0]
        if sel.type() not in ["transform", "joint"]:
            return SNone
        ad = get_ad()
        if ad is None:
            return SNone
        if sel.type() == "joint":
            if ad.joint != sel:
                return SInit
            return SJoint
        if sel.name().startswith("ADPoseLittlePoseBall"):
            return SPoseBall
        if sel == ad.control:
            return SCtrl
        if is_shape(sel, "mesh"):
            if "|adPoses" in sel.fullPath():
                return SDupPolygon
            else:
                return SRigPolygon
        return SNone
    if selected_length == 2:
        src, dst = selected
        if not is_shape(src, "mesh"):
            return SNone
        if not is_shape(src, "mesh"):
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
        pm.scriptJob(e=["SelectionChanged", self])
        pm.scriptJob(e=["ToolChanged", self])

    @classmethod
    def del_job(cls):
        for job in pm.scriptJob(listJobs=True):
            if repr(cls.__name__) in job:
                pm.scriptJob(kill=int(job.split(":")[0]))


ADPoseLittleMenu = "ADPoseMenu"


def del_menu():
    if pm.popupMenu(ADPoseLittleMenu, q=1, ex=1):
        pm.deleteUI(ADPoseLittleMenu)


def add_menu():
    del_menu()
    typ = get_selected_type()
    if typ == SNone:
        return
    menu = pm.popupMenu(ADPoseLittleMenu, button=1, ctl=1, alt=0, sh=0, allowOptionBoxes=1, p="viewPanes", mm=1)
    pm.menuItem(p=menu, l=u"关闭工具", rp="E", c=menu_close_tool)
    if typ == SInit:
        pm.menuItem(p=menu, l=u"创建驱动球", rp="N", c=menu_add_driver_ball)
    pm.menuItem(p=menu, l=u"删除驱动球", rp="N", c=menu_del_driver_ball)
    if typ in [SCtrl]:
        pm.menuItem(p=menu, l=u"添加姿势", rp="W", c=menu_add_pose)
    if typ == SPoseBall:
        pm.menuItem(p=menu, l=u"删除姿势", rp="SW", c=menu_del_pose)
        pm.menuItem(p=menu, l=u"转到姿势", rp="S", c=menu_to_pose)
    if typ == SRigPolygon:
        pm.menuItem(p=menu, l=u"复制并修改姿势", rp="NW", c=menu_dup_edit)
        pm.menuItem(p=menu, l=u"镜像姿势", rp="SE", c=menu_mirror_pose)
    if typ == SDupPolygon:
        pm.menuItem(p=menu, l=u"结束姿势修改", rp="NW", c=menu_edit_finish)
    if typ == STwoPolygon:
        pm.menuItem(p=menu, l=u"修改姿势", rp="NW", c=menu_edit_pose)
        pm.menuItem(p=menu, l=u"包裹传递", c=menu_warp_copy)


def del_driver_ball():
    pm.delete(pm.ls("|ADPoseLittle*"))
    edit_finish()


def add_driver_ball(joint=None):
    del_driver_ball()
    if joint is None:
        joints = pm.ls(type="joint", o=1, sl=1)
        if not len(joints) == 1:
            return pm.warning("please select a joint")
        joint = joints[0]
    if joint is None:
        return
    prefix = "ADPoseLittle"
    if pm.objExists(prefix + "Root"):
        pm.delete(prefix + "Root")
    pm.delete(pm.ls(prefix + "*"))
    root = pm.group(em=1, n=prefix + "Root")
    parent = joint.getParent()
    if parent is not None:
        pm.parentConstraint(parent, root)
    back = pm.sphere(ch=0, n=prefix + "BACK")[0]
    back.setParent(root)
    back.setMatrix(joint.getMatrix(ws=1), ws=1)

    back.s.set(1, 1, 1)
    pm.parent(pm.pointConstraint(joint, back), root)
    back.r.set(joint.jointOrient.get())
    if not joint.hasAttr("ADPoseLittleRadius"):
        joint.addAttr("ADPoseLittleRadius", at="double", k=0, dv=1)
        pm.setAttr(joint.ADPoseLittleRadius, e=1, channelBox=1)
        if parent is not None:
            radius = (parent.getTranslation(space="world") - joint.getTranslation(space="world")).length()
            joint.ADPoseLittleRadius.set(radius * 0.7)
    joint.ADPoseLittleRadius.connect(back.scaleX)
    joint.ADPoseLittleRadius.connect(back.scaleY)
    joint.ADPoseLittleRadius.connect(back.scaleZ)
    back.getShape().overrideEnabled.set(1)
    back.getShape().overrideDisplayType.set(2)
    back_lbt = pm.shadingNode('lambert', asShader=True, n=prefix + "BAKE_LBT")
    pm.select(cl=1)
    back_sg = pm.sets(n=prefix + "BACK_SG", r=1)
    back_lbt.outColor.connect(back_sg.surfaceShader, f=1)
    back_lbt.transparency.set(0.8, 0.8, 0.8)
    pm.sets(back_sg, e=1, forceElement=back)
    if not joint.hasAttr("ADPoseLittle_Axis"):
        joint.addAttr("ADPoseLittle_Axis", at="long", k=0, min=-1, max=1, dv=1)
        pm.setAttr(joint.ADPoseLittle_Axis, e=1, channelBox=1)
        if back.tx.get() < 0:
            joint.ADPoseLittle_Axis.set(-1)
        else:
            joint.ADPoseLittle_Axis.set(1)
    update_pose_ball()


def update_pose_ball():
    prefix = "ADPoseLittle"
    color = pm.datatypes.Vector(1, 0, 0)
    joint = get_driver_joint()
    back = pm.ls(prefix + "BACK")[0]
    pm.delete(pm.listRelatives(back, type="transform"))
    pose_name_matrix = [["bindPose", pm.datatypes.Matrix()]]
    ad = ADPose.ADPoses.load_by_name(joint.name())
    for pose in ad.get_poses():
        matrix = ADPose.pose_to_matrix(pose)
        name = "_a%i_d%i" % pose
        pose_name_matrix.append([name, matrix])
    for name, matrix in pose_name_matrix:
        group = pm.group(em=1, n=prefix + name + "_GROUP", p=back)
        group.setMatrix(matrix)
        group.t.set(0, 0, 0)
        ball = pm.sphere(ch=0, n=prefix + "PoseBall" + name)[0]
        ball.setParent(group)
        ball.r.set(0, 0, 0)
        ball.s.set(0.05, 0.05, 0.05)
        ball.t.set(0, 0, 0)
        joint.ADPoseLittle_Axis.connect(ball.tx)
        ball_lbt = pm.shadingNode('lambert', asShader=True, n=prefix + name + "_LBT")
        pm.select(cl=1)
        ball_sg = pm.sets(n=prefix + name + "_SG", r=1)
        ball_lbt.outColor.connect(ball_sg.surfaceShader, f=1)
        ball_lbt.transparency.set(0.5, 0.5, 0.5)
        pm.sets(ball_sg, e=1, forceElement=ball)
        ball_lbt.color.set(color * matrix)
        ball.t.setLocked(True)
        ball.r.setLocked(True)
        ball.s.setLocked(True)


def close_tool():
    print ("close tool")
    LADPoseLittleSelectedJob().del_job()
    del_driver_ball()
    del_menu()


def open_tool():
    close_tool()
    LADPoseLittleSelectedJob().add_job()
    add_menu()


def get_driver_joint():
    if not exist_little():
        return
    if not pm.objExists("ADPoseLittleBACK"):
        return
    joints = pm.PyNode("ADPoseLittleBACK").sx.inputs(type="joint")
    if not len(joints) == 1:
        return
    joint = joints[0]
    return joint


def get_ad():
    joint = get_driver_joint()
    if joint is None:
        return
    return ADPose.ADPoses.load_by_name(joint.name())


def edit_finish():
    if pm.objExists("|adPoses"):
        ADPose.ADPoses.auto_edit()
    pm.delete(pm.ls("|adPoses"))


def menu_keep_selected(fun):
    def _fun(*args, **kwargs):
        sel = cmds.ls(sl=1)
        result = fun(*args, **kwargs)
        pm.select(cmds.ls(sel))
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
    ball = pm.ls(sl=1, type="transform", o=1)[0]
    pattern = re.match("^ADPoseLittlePoseBall_a([0-9]{1,3})_d([0-9]{1,3})$", ball.name())
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
    ADPose.ADPoses.auto_dup([joint.name()])


@after(update_pose_ball)
def menu_edit_finish(*args):
    if pm.objExists("|adPoses"):
        ADPose.ADPoses.auto_edit()
    pm.delete(pm.ls("|adPoses"))


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
    ball = pm.ls(sl=1, type="transform", o=1)[0]
    ad.control.setMatrix(ball.getParent().getMatrix())


def test():
    close_tool()
    pm.select("Shoulder_L")
    menu_add_driver_ball()
    pm.select("ADPoseLittlePoseBall_a90_d90")
    menu_del_pose()


