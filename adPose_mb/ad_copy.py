from pyfbsdk import *
import copy


def find_node_by_name(name):
    obj_list = FBComponentList()
    FBFindObjectsByName(name, obj_list)
    for obj in obj_list:
        return obj


def delete_node(node):
    while len(node.Children) > 0:
        delete_node(node.Children[-1])
    node.FBDelete()


def delete_node_by_name(name):
    node = find_node_by_name(name)
    if node is not None:
        delete_node(node)


def dup_joint(joint, name, parent):
    dup_jnt = copy.copy(joint)
    dup_jnt.Name = name
    parent.ConnectSrc(dup_jnt)
    attr_list = ["Lcl Rotation",  "Lcl Translation"]
    # for attr in dup_jnt.PropertyList:
    #     print attr.Name
    for attr in attr_list:
        dup_jnt.PropertyList.Find(attr).Data = joint.PropertyList.Find(attr).Data


def copy_joint(joint, prefix):
    parent = find_node_by_name("MB_Control_"+joint.Parent.Name)
    if parent is None:
        parent = joint.Parent
    print parent.Name
    dup_joint(joint, prefix+joint.Name, parent)
    for child in joint.Children:
        copy_joint(child, prefix)


def main():
    delete_node_by_name("MB_Control_Roots")
    root = find_node_by_name("Roots")
    copy_joint(root, "MB_Control_")

    # delete_node_by_name()

