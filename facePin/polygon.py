# coding:utf-8
from maya import cmds
from maya.api.OpenMaya import *


def get_points_by_matrix(matrix):
    r = 0.01
    local_points = [
        [-r, r, 0],
        [-r, -r, 0],
        [r, -r, 0],
        [r, r, 0],
    ]
    local_points = [MPoint(p) for p in local_points]
    matrix = MMatrix(matrix)
    return [p*matrix for p in local_points]


def get_polygon_points(matrices):
    return sum(map(get_points_by_matrix, matrices), [])


def get_polygon_uvs(face_count):
    us = MFloatArray()
    vs = MFloatArray()
    for face_index in range(face_count):
        u_index = face_index // 100
        v_index = face_index % 100
        step = 0.01
        u1 = u_index * step
        v1 = v_index * step
        u2 = u1 + step
        v2 = v1 + step
        for u in [u1, u1, u2, u2]:
            us.append(u)
        for v in [v1, v2, v2,v1]:
            vs.append(v)
    return us, vs


def api_ls(*names):
    selection_list = MSelectionList()
    for name in names:
        selection_list.add(name)
    return selection_list


def create_polygon_by_matrices(name, matrices):
    u"""
    通过骨骼矩阵，创建三角面片，使面片上钉毛囊的矩阵与骨骼矩阵相同。
    @param name: 面片名
    @param matrices: 矩阵
    @return:
    """
    if not cmds.objExists(name):
        name = cmds.createNode("transform", n=name, ss=True)
    shapes = cmds.listRelatives(name, s=1)
    if shapes:
        cmds.delete(shapes)
    face_count = len(matrices)
    if face_count == 0:
        return
    vertices = get_polygon_points(matrices)
    polygon_counts = MIntArray([4]*face_count)
    polygon_connects = MIntArray(range(4*face_count))
    parent = api_ls(name).getDagPath(0).node()
    fn_mesh = MFnMesh()
    us, vs = get_polygon_uvs(face_count)
    fn_mesh.create(vertices, polygon_counts, polygon_connects, us, vs, parent=parent)
    fn_mesh.assignUVs(polygon_counts, polygon_connects)
    fn_depend = MFnDependencyNode(fn_mesh.object())
    fn_depend.setName(name+"Shape")
    cmds.lockNode("initialShadingGroup", l=0, lu=0)
    cmds.sets(name, e=1, fe="initialShadingGroup")
    return name


def test_build_polygon_by_selected():
    name = "test_polygon"
    matrices = [cmds.xform(joint, q=1, ws=1, m=1) for joint in cmds.ls(sl=1)]
    create_polygon_by_matrices(name, matrices)


def doit():
    test_build_polygon_by_selected()
