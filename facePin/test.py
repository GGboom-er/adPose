from maya import cmds
from .core import FacePin
import random


def random_tr(joint):
    for tr, s in zip("tr", [3, 30]):
        for xyz in "xyz":
            cmds.setAttr(joint + "." + tr + xyz, random.uniform(-1.0, 1.0)*s)


def create_joint():
    joint = cmds.joint(None)
    cmds.toggle(joint, la=1)
    random_tr(joint)
    return joint


def test_pin_build():
    cmds.file(new=1, f=1)
    fp = FacePin("MFace")
    joints = [create_joint() for i in range(4)]
    for joint in joints:
        fp.add_pin(joint, cmds.xform(joint, q=1, ws=1, m=1))
    fp.build()
    return fp


def same_matrix(a, b):
    assert all([abs(v1-v2) < 0.0001 for v1, v2 in zip(cmds.xform(a, q=1, ws=1, m=1), cmds.xform(b, q=1, ws=1, m=1))])


def test_re_pin_rebuild():
    test_pin_build()
    fp = FacePin("MFace").load()
    joints = [create_joint() for i in range(4)]
    for joint in joints:
        fp.add_pin(joint, cmds.xform(joint, q=1, ws=1, m=1))
    fp.build()
    same_matrix("joint1Pin", "joint1")
    same_matrix("joint8Pin", "joint8")


def test_add_cluster():
    cmds.file(new=1, f=1)
    fp = FacePin("MFace")
    joints = [create_joint() for i in range(4)]
    clusters = [create_joint() for i in range(2)]
    for joint in joints:
        fp.add_pin(joint, cmds.xform(joint, q=1, ws=1, m=1))
    for cluster in clusters:
        fp.add_cluster(cluster, cmds.xform(cluster, q=1, ws=1, m=1))
    fp.set_layer("ClusterA", clusters[0])
    fp.set_layer("ClusterB", clusters[1])
    fp.set_weight(clusters[0], joints[0], 1.0)
    fp.set_weight(clusters[0], joints[1], 0.5)
    fp.set_weight(clusters[1], joints[2], 1.0)
    fp.set_weight(clusters[1], joints[1], 0.5)
    fp.build()


def test_re_cluster():
    test_add_cluster()
    fp = FacePin("MFace").load()
    joints = [create_joint() for i in range(4)]
    clusters = [create_joint() for i in range(2)]
    for joint in joints:
        fp.add_pin(joint, cmds.xform(joint, q=1, ws=1, m=1))
    for cluster in clusters:
        fp.add_cluster(cluster, cmds.xform(cluster, q=1, ws=1, m=1))
    fp.set_layer("ClusterA", clusters[0])
    fp.set_layer("ClusterB", clusters[1])
    fp.set_weight(clusters[0], joints[0], 1.0)
    fp.set_weight(clusters[0], joints[1], 0.5)
    fp.set_weight(clusters[1], joints[2], 1.0)
    fp.set_weight(clusters[1], joints[1], 0.5)
    fp.set_weight(clusters[0], fp.pins[1], 0.5)
    fp.set_weight(clusters[0], fp.pins[2], 0.5)
    fp.build()


def check_pins(fp):
    for pin in fp.pins:
        same_matrix(pin, pin+"Pin")


def test_remove_pin():
    test_add_cluster()
    fp = FacePin("MFace").load()
    fp.remove_pin(fp.pins[0])
    fp.build()
    check_pins(fp)


def test_remove_cluster():
    test_add_cluster()
    fp = FacePin("MFace").load()
    cluster = list(fp.clusters.keys())[0]
    fp.remove_cluster(cluster)
    fp.build()


def doit():
    pass
