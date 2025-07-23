#encoding=UTF-8
from pyfbsdk import FBMessageBox, FBApplication, FBVideoGrabber, FBVideoRenderDepth, FBVideoRenderDepth, FBVideoCodecManager, FBVideoCodecMode
from pyfbsdk import FBTime, FBModel, FBModelCube, FBCamera, FBCameraSwitcher, FBRenderer, FBScene, FBSystem, FBVector3d, FBPlayerControl
from pyfbsdk import *
from pyfbsdk_additions import *
import sys
#-------------------------------------------other Custom Module----------------------------------------------------
def GetMBpath() :
    appPath = FBSystem().ApplicationPath #默认返回路径  C:\Program Files\Autodesk\MotionBuilder 2018\bin\x64
    return appPath[0:appPath.index('bin')]#return  C:\Program Files\Autodesk\MotionBuilder 2018\

sys.path.append(GetMBpath()+r"bin\config\Scripts\MyTools\YiQiToolPackage")#
from MBQuaternion import *
from MBUtility import *
from pyfbsdk_additions import *

from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2 import shiboken2 as MB_Shib

import os
from os import environ, listdir
from collections import OrderedDict
#------------------------------------------------fun---------------------------------------------------

# def create_remap():
#     remap = create_constraints("Relation", "ReMap")
#     remap.CreateFunctionBox('Macro Input')
#
#
# def create_driver_key_macro():
def find_by_name(name, cls="Components"):
    u"""
    :param name: 名字
    :param cls: 类型
    :return:
    通过名字获取物体
    """
    nodes = filter(lambda x: x.Name == name, getattr(FBSystem().Scene, cls))
    for node in nodes:
        return node


def delete_node_by_name(name, cls="Components"):
    u"""
    :param name: 节点名称
    :param cls: 节点类型
    :return:
    按名称删除节点
    """
    node = find_by_name(name, cls)
    if node is not None:
        node.FBDelete()


def FindAnimationNode(pParent, pName):
    u"""
    :param pParent: 节点
    :param pName: 属性名
    :return: 按名称获取动画节点
    """
    for lNode in pParent.Nodes:
        if lNode.Name == pName:
            return lNode


def connect(src_node, src_attr, dst_node, dst_attr):
    u"""
    :param src_node: 输出节点名
    :param src_attr: 输出节点属性
    :param dst_node: 输入节点名
    :param dst_attr: 输出节点属性
    :return:
    将src_node的src_attr属性连接到dst_node的dst_attr上
    """
    FBConnect(
        FindAnimationNode(src_node.AnimationNodeOutGet(), src_attr),
        FindAnimationNode(dst_node.AnimationNodeInGet(), dst_attr)
    )


def set_attr(box, name, value):
    u"""
    :param box: 节点
    :param name: 名称
    :param value: 数值
    :return:设置节点属性值
    """
    attr = FindAnimationNode(box.AnimationNodeInGet(), name)
    attr.WriteData(value)


def create_constraints(typ, name):
    """
    Aim
    Expression
    Multi Referential
    OR - Position from Position
    Parent/Child
    Path
    Position
    Range
    Relation
    Rigid Body
    3 Points
    Rotation
    Scale
    Mapping
    Chain IK
    Spline IK
    创建约束
    """
    lMgr = FBConstraintManager()
    for lIdx in range(lMgr.TypeGetCount()):
        if typ == lMgr.TypeGetName(lIdx):
            delete_node_by_name(name, "Constraints")
            constraint = lMgr.TypeCreateConstraint(lIdx)
            constraint.Name = name
            return constraint


def create_macro_remap_sdk():
    NODE_W = 300
    NODE_H = 100
    remap = create_constraints("Relation", "ReMap")

    old_min = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(old_min, NODE_W * 0, NODE_H * 2)

    _min = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(_min, NODE_W * 0, NODE_H * 3)

    old_max = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(old_max, NODE_W * 0, NODE_H * 0)

    _max = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(_max, NODE_W * 0, NODE_H * 1)

    old_value = remap.CreateFunctionBox('Macro Tools', 'Macro Input Number')
    remap.SetBoxPosition(old_value, NODE_W * 0, NODE_H * 4)

    max_sub_min = remap.CreateFunctionBox('Number', 'Subtract (a - b)')
    remap.SetBoxPosition(max_sub_min, NODE_W * 1, NODE_H * 0)

    omax_sub_omin = remap.CreateFunctionBox('Number', 'Subtract (a - b)')
    remap.SetBoxPosition(omax_sub_omin, NODE_W * 1, NODE_H * 1)

    ovalue_sub_omin = remap.CreateFunctionBox('Number', 'Subtract (a - b)')
    remap.SetBoxPosition(ovalue_sub_omin, NODE_W * 1, NODE_H * 2)

    mult = remap.CreateFunctionBox('Number', 'Multiply (a x b)')
    remap.SetBoxPosition(mult, NODE_W * 2, NODE_H * 0)

    divide = remap.CreateFunctionBox('Number', 'Divide (a/b)')
    remap.SetBoxPosition(divide, NODE_W * 2, NODE_H * 1)

    _add = remap.CreateFunctionBox('Number', 'Add (a + b)')
    remap.SetBoxPosition(_add, NODE_W * 3, NODE_H * 0)

    is_greater = remap.CreateFunctionBox('Number', 'Is Greater (a > b)')
    remap.SetBoxPosition(is_greater, NODE_W * 4, NODE_H * 0)

    is_less = remap.CreateFunctionBox('Number', 'Is Less (a < b)')
    remap.SetBoxPosition(is_less, NODE_W * 4, NODE_H * 1)

    condition1 = remap.CreateFunctionBox('Number', 'If Cond Then A Else B')
    remap.SetBoxPosition(condition1, NODE_W * 5, NODE_H * 0)

    condition2 = remap.CreateFunctionBox('Number', 'If Cond Then A Else B')
    remap.SetBoxPosition(condition2, NODE_W * 5, NODE_H * 1)

    out_value = remap.CreateFunctionBox('Macro Tools', 'Macro Output Number')
    remap.SetBoxPosition(out_value, NODE_W * 6, NODE_H * 0)


    connect(_max, 'Input', max_sub_min, 'a')
    connect(_min, 'Input', max_sub_min, 'b')
    connect(old_max, 'Input', omax_sub_omin, 'a')
    connect(old_min, 'Input', omax_sub_omin, 'b')
    connect(old_value, 'Input', ovalue_sub_omin, 'a')
    connect(old_min, 'Input', ovalue_sub_omin, 'b')
    connect(max_sub_min, 'Result', mult, 'a')
    connect(ovalue_sub_omin, 'Result', mult, 'b')
    connect(mult, 'Result', divide, 'a')
    connect(omax_sub_omin, 'Result', divide, 'b')
    connect(_min, 'Input', _add, 'a')
    connect(divide, 'Result', _add, 'b')
    connect(old_value, 'Input', is_greater, 'a')
    connect(old_max, 'Input', is_greater, 'b')
    connect(old_value, 'Input', is_less, 'a')
    connect(old_min, 'Input', is_less, 'b')
    connect(_max, 'Input', condition1, 'a')
    connect(_min, 'Input', condition2, 'a')
    connect(is_greater, 'Result', condition1, 'Cond')
    connect(is_less, 'Result', condition2, 'Cond')
    connect(condition1, 'Result', condition2, 'b')
    connect(_add, 'Result', condition1, 'b')
    connect(condition2, 'Result', out_value, 'Output')

    return remap


def create_remap_node(parent, w, h):
    remap = parent.CreateFunctionBox('My Macros', 'ReMap')
    parent.SetBoxPosition(remap, w, h)
    node_port = {}
    for name, item in zip(["Old_Min", "Min", "Old_Max", "Max", "Input_Value"], remap.AnimationNodeInGet().Nodes):
        node_port[name] = item
    node_port["Output_value"] = remap.AnimationNodeOutGet().Nodes[0]
    return node_port


def create_macro_3key_value_sdk():
    NODE_W = 300
    NODE_H = 100
    driver_key = create_constraints('Relation', 'Driver_3_key_sdk')

    ovalue_0 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(ovalue_0, NODE_W * 0, NODE_H * 0)

    value_0 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(value_0, NODE_W * 0, NODE_H * 1)

    ovalue_1 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(ovalue_1, NODE_W * 0, NODE_H * 2)

    value_1 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(value_1, NODE_W * 0, NODE_H * 3)

    ovalue_2 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(ovalue_2, NODE_W * 0, NODE_H * 4)

    value_2 = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(value_2, NODE_W * 0, NODE_H * 5)

    input_value = driver_key.CreateFunctionBox("Macro Tools", "Macro Input Number")
    driver_key.SetBoxPosition(input_value, NODE_W * 0, NODE_H * 6)

    remap0 = create_remap_node(driver_key, NODE_W * 1, NODE_H * 0)

    remap1 = create_remap_node(driver_key, NODE_W * 1, NODE_H * 1)

    sub0 = driver_key.CreateFunctionBox('Number', 'Subtract (a - b)')
    driver_key.SetBoxPosition(sub0, NODE_W * 1, NODE_H * 2)

    add_node = driver_key.CreateFunctionBox("Number", "Add (a + b)")
    driver_key.SetBoxPosition(add_node, NODE_W * 2, NODE_H * 0)

    out_value = driver_key.CreateFunctionBox("Macro Tools", "Macro Output Number")
    driver_key.SetBoxPosition(out_value, NODE_W * 3, NODE_H * 0)

    FBConnect(FindAnimationNode(value_0.AnimationNodeOutGet(), 'Input'), remap0["Min"])
    FBConnect(FindAnimationNode(value_1.AnimationNodeOutGet(), 'Input'), remap0["Max"])
    FBConnect(FindAnimationNode(ovalue_0.AnimationNodeOutGet(), 'Input'), remap0["Old_Min"])
    FBConnect(FindAnimationNode(ovalue_1.AnimationNodeOutGet(), 'Input'), remap0["Old_Max"])
    FBConnect(FindAnimationNode(input_value.AnimationNodeOutGet(), 'Input'), remap0["Input_Value"])
    remap1["Min"].WriteData([0])
    connect(value_2, 'Input', sub0, 'a')
    connect(value_1, 'Input', sub0, 'b')
    FBConnect(FindAnimationNode(sub0.AnimationNodeOutGet(), 'Result'), remap1["Max"])
    FBConnect(FindAnimationNode(ovalue_1.AnimationNodeOutGet(), 'Input'), remap1["Old_Min"])
    FBConnect(FindAnimationNode(ovalue_2.AnimationNodeOutGet(), 'Input'), remap1["Old_Max"])
    FBConnect(FindAnimationNode(input_value.AnimationNodeOutGet(), 'Input'), remap1["Input_Value"])
    FBConnect(remap0["Output_value"], FindAnimationNode(add_node.AnimationNodeInGet(), 'a'))
    FBConnect(remap1["Output_value"], FindAnimationNode(add_node.AnimationNodeInGet(), 'b'))
    connect(add_node, 'Result', out_value, 'Output')


def create_driver_3d_node(parent, w, h, key_value):
    driver_3d = parent.CreateFunctionBox('My Macros', 'Driver_3_key_sdk')
    parent.SetBoxPosition(driver_3d, w, h)
    nodes = driver_3d.AnimationNodeInGet().Nodes
    for i in range(len(key_value)):
        nodes[i*2].WriteData([key_value[i][0]])
        nodes[i*2+1].WriteData([key_value[i][1]])
    return {"Input_value": nodes[-1], "Output_value": driver_3d.AnimationNodeOutGet().Nodes[0]}


create_macro_remap_sdk()
create_macro_3key_value_sdk()
relation = create_constraints('Relation', 'relation_1')
create_driver_3d_node(relation, 300, 100, [[0, 0], [90, 100], [180, 0]])


# def create_driver_3key_value():
#
