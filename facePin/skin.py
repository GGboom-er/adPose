# coding=utf-8
import os
from maya.api.OpenMaya import *
from maya.api.OpenMayaAnim import *
from maya import cmds


def get_skin_cluster(polygon_name):
    shapes = cmds.listRelatives(polygon_name, s=1, f=1) or []
    for skin_cluster in cmds.ls(cmds.listHistory(polygon_name), type="skinCluster"):
        for shape in cmds.skinCluster(skin_cluster, q=1, geometry=1):
            for long_shape in cmds.ls(shape, l=1):
                if long_shape in shapes:
                    return skin_cluster


def api_ls(*names):
    selection_list = MSelectionList()
    for name in names:
        selection_list.add(name)
    return selection_list


def get_weights_args(polygon_name):
    shape, components = api_ls(polygon_name + ".vtx[*]").getComponent(0)
    fn_skin = MFnSkinCluster(api_ls(get_skin_cluster(polygon_name)).getDependNode(0))
    influences = MIntArray(range(len(fn_skin.influenceObjects())))
    return fn_skin, shape, components, influences


def get_weights(polygon_name):
    fn_skin, shape, components, influences = get_weights_args(polygon_name)
    return list(fn_skin.getWeights(shape, components, influences))


def set_weights(polygon_name, weights):
    cmds.dgdirty(get_skin_cluster(polygon_name))
    fn_skin, shape, components, influences = get_weights_args(polygon_name)
    fn_skin.setWeights(shape, components, influences, MDoubleArray(weights))


def get_skin_joints(polygon):
    sk = get_skin_cluster(polygon)
    if sk is None:
        return []
    return cmds.skinCluster(sk, q=1, inf=1)


def create_skin(joints, polygon, weights):
    sk = get_skin_cluster(polygon)
    if not sk:
        sk = cmds.skinCluster(joints, polygon, tsb=1, rui=False)[0]
    cmds.setAttr(sk+".skinningMethod", 1)
    set_weights(polygon, weights)
