# coding:utf-8
import os
from . import ADPose
from . import bs
from .general_ui import *


def load_ocd_plug():
    version = int(round(float(pm.about(q=1, v=1))))
    path = os.path.abspath(__file__+"/../plug-ins/maya%04d/ocd.mll" % version)
    if not os.path.isfile(path):
        return  # pm.warning("can not find ocd")
    if not pm.pluginInfo(path, q=1, l=1):
        pm.loadPlugin(path)


load_ocd_plug()


def clear_orig():
    for polygon in ADPose.get_selected_polygons():
        bs.get_orig(polygon)


def create_ocd():
    clear_orig()
    load_ocd_plug()
    pm.mel.create_ocd()


def create_ocd_by_skin():
    clear_orig()
    load_ocd_plug()
    pm.mel.create_ocd_by_skin()


def bake_deform(deform, skin, ad, direction, _max, number):
    direction_data = {
        u"+z": [0],
        u"-y": [90],
        u"-z": [180],
        u"+y": [270],
        u"四方向": [i for i in range(0, 360, 90)],
        u"八方向": [i for i in range(0, 360, 45)],
    }
    if direction == u"已存在":
        poses = ad.get_poses()
    else:
        poses = [[int(round(float(_max)/number*(i+1))), d]
                 for d in direction_data.get(direction, []) for i in range(number)]
    for pose in poses:
        ad.set_pose(pose)
        pm.select(deform, skin)
        pm.refresh()
        ad.edit_by_selected_ctrl_pose()
    pm.select(deform, skin)


def find_history_node(polygon, typ):
    nodes = pm.listHistory(polygon, type=typ)
    if nodes is None or len(nodes) == 0:
        return pm.warning("can not find " + typ)
    node = nodes[0]
    return node


def get_ocd_kwargs(polygon):
    ocd_node = find_history_node(polygon, "OcdNode")
    data = {}
    for attr in ocd_node.listAttr(k=1):
        if attr.type() != "float":
            continue
        k = attr.name(includeNode=False)
        v = attr.get()
        data[k] = v
    return data


def set_ocd_kwargs(deform, data):
    ocd_node = find_history_node(deform, "OcdNode")
    for k, v in data.items():
        ocd_node.attr(k).set(v)


def unlock_ocd_joints(polygon, joint):
    skin = find_history_node(polygon, "skinCluster")
    for inf in skin.influenceObjects():
        inf.liw.set(1)
    joint.liw.set(0)
    joint.getParent().liw.set(0)


def zero_ads(joints):
    ads = []
    for name in joints:
        ad = ADPose.ADPoses.load_by_name(name)
        if ad is None:
            continue
        ad.control.r.set(0, 0, 0)
        ads.append(ad)
    return ads


def bake_finger(deform, skin, joints, direction, _max, number):
    ads = zero_ads(joints)
    data = get_ocd_kwargs(deform)
    for ad in ads:
        ad.control.ry.set(90)
        pm.select(skin)
        unlock_ocd_joints(skin, ad.joint)
        pm.select(skin)
        deform, _ = pm.mel.create_ocd_by_skin()
        deform = pm.PyNode(deform)
        set_ocd_kwargs(deform, data)
        bake_deform(deform, skin, ad, direction, _max, number)
        ad.control.r.set(0, 0, 0)
        pm.delete(deform)


def bake_deforms(deform, skin, joints, direction, _max, number):
    ads = zero_ads(joints)
    for ad in ads:
        bake_deform(deform, skin, ad, direction, _max, number)
        ad.control.r.set(0, 0, 0)


class BakeDeform(Tool):
    title = u"烘焙修型"

    def __init__(self, parent):
        Tool.__init__(self, parent)
        self.deform = MayaObjLayout(u"变形模型:")
        self.skin = MayaObjLayout(u"蒙皮模型:")
        self.kwargs_layout.addLayout(self.skin)
        self.kwargs_layout.addLayout(self.deform)

        self.max = Number(0, 180, 90)
        self.kwargs_layout.addLayout(PrefixWeight(u"最大角度:", self.max))
        self.number = Number(0, 180, 1)
        self.kwargs_layout.addLayout(PrefixWeight(u"修形个数:", self.number))
        self.direction = QComboBox()
        self.direction.addItems(["+y", "-y", "+z", "-z", u"四方向", u"八方向", u"已存在"])
        self.kwargs_layout.addLayout(PrefixWeight(u"修形方向:", self.direction))
        self.joints = JointList()
        self.kwargs_layout.addLayout(self.joints)

    def apply(self):
        deform = self.deform.obj
        skin = self.skin.obj
        _max = self.max.value()
        number = self.number.value()
        direction = self.direction.currentText()
        joints = self.joints.get_joints()
        bake_deforms(deform, skin, joints, direction, _max, number)


class BakeOcd(BakeDeform):
    title = u"烘焙手指"

    def __init__(self, parent):
        BakeDeform.__init__(self, parent)
        joints = [u'PinkyFinger2_L', u'PinkyFinger3_L', u'RingFinger2_L', u'RingFinger3_L', u'MiddleFinger2_L',
                  u'MiddleFinger3_L', u'IndexFinger2_L', u'IndexFinger3_L', u'ThumbFinger3_L']
        self.joints.list.addItems(joints)

    def apply(self):
        deform = self.deform.obj
        skin = self.skin.obj
        _max = self.max.value()
        number = self.number.value()
        direction = self.direction.currentText()
        joints = self.joints.get_joints()
        bake_finger(deform, skin, joints, direction, _max, number)
