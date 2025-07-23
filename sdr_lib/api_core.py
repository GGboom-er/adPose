from maya.OpenMaya import *
from maya.OpenMayaAnim import *
from maya import cmds


def get_dag_path_by_name(name):
    selection_list = MSelectionList()
    selection_list.add(name)
    dag_path = MDagPath()
    selection_list.getDagPath(0, dag_path)
    return dag_path


def get_fn_skin_by_name(name):
    selection_list = MSelectionList()
    selection_list.add(name)
    depend_node = MObject()
    selection_list.getDependNode(0, depend_node)
    fn_skin = MFnSkinCluster(depend_node)
    return fn_skin


def get_fn_mesh_by_name(name):
    selection_list = MSelectionList()
    selection_list.add(name)
    dag_path = MDagPath()
    selection_list.getDagPath(0, dag_path)
    fn_mesh = MFnMesh(dag_path)
    return fn_mesh


def get_dag_path_component_by_name(name):
    selection_list = MSelectionList()
    selection_list.add(name)
    dag_path = MDagPath()
    components = MObject()
    selection_list.getDagPath(0, dag_path, components)
    return dag_path, components


def set_weights(polygon_name, skin_cluster_name, indices, weights):
    MGlobal.executeCommand("dgdirty %s;" % skin_cluster_name)
    skin_polygon_path, skin_polygon_components = get_dag_path_component_by_name(polygon_name + ".vtx[*]")
    fn_skin = get_fn_skin_by_name(skin_cluster_name)
    fn_skin.setWeights(skin_polygon_path, skin_polygon_components, indices, weights)


def get_weights(polygon_name, skin_cluster_name, indices, weights):
    skin_polygon_path, skin_polygon_components = get_dag_path_component_by_name(polygon_name + ".vtx[*]")
    fn_skin = get_fn_skin_by_name(skin_cluster_name)
    fn_skin.getWeights(skin_polygon_path, skin_polygon_components, indices, weights)


def py_to_m_array(cls, _list):
    result = cls()
    for elem in _list:
        result.append(elem)
    return result


def get_points(polygon_name):
    fn_mesh = get_fn_mesh_by_name(polygon_name)
    points = MPointArray()
    fn_mesh.getPoints(points, MSpace.kWorld)
    return points


def set_points(polygon_name, points):
    fn_mesh = get_fn_mesh_by_name(polygon_name)
    m_points = MPointArray()
    for point in points:
        m_points.append(MPoint(*point))
    fn_mesh.setPoints(m_points, MSpace.kWorld)


def get_ids_weights(polygon_name, skin_cluster_name, indices, vtx_ids, weights):
    fn_component = MFnSingleIndexedComponent()
    skin_polygon_components = fn_component.create(MFn.kMeshVertComponent)
    fn_component.addElements(vtx_ids)
    skin_polygon_path = get_dag_path_by_name(polygon_name)
    fn_skin = get_fn_skin_by_name(skin_cluster_name)
    fn_skin.getWeights(skin_polygon_path, skin_polygon_components, indices, weights)


def set_ids_weights(polygon_name, skin_cluster_name, indices, vtx_ids, weights):
    MGlobal.executeCommand("dgdirty %s;" % skin_cluster_name)
    fn_component = MFnSingleIndexedComponent()
    skin_polygon_components = fn_component.create(MFn.kMeshVertComponent)
    fn_component.addElements(vtx_ids)
    skin_polygon_path = get_dag_path_by_name(polygon_name)
    fn_skin = get_fn_skin_by_name(skin_cluster_name)
    fn_skin.setWeights(skin_polygon_path, skin_polygon_components, indices, weights)


def get_py_weights(polygon_name):
    skin_cluster_name = cmds.ls(cmds.listHistory(polygon_name), type="skinCluster")[0]
    fn_skin = get_fn_skin_by_name(skin_cluster_name)
    joints = MDagPathArray()
    fn_skin.influenceObjects(joints)
    joint_length = joints.length()
    weights = MDoubleArray()
    indices = py_to_m_array(MIntArray, range(joint_length))
    get_weights(polygon_name, skin_cluster_name, indices, weights)
    vtx_length = int(round(weights.length()/joints.length()))
    weights = [weights[i] for i in range(weights.length())]
    weights = [weights[joint_length*vtx_id:joint_length*(vtx_id+1)] for vtx_id in range(vtx_length)]
    return weights


def set_py_weights(polygon_name, weights):
    skin_cluster_name = cmds.ls(cmds.listHistory(polygon_name), type="skinCluster")[0]
    fn_skin = get_fn_skin_by_name(skin_cluster_name)
    joints = MDagPathArray()
    fn_skin.influenceObjects(joints)
    joint_length = joints.length()
    indices = py_to_m_array(MIntArray, range(joint_length))
    weights = sum(weights, [])
    api_weights = MDoubleArray()
    for w in weights:
        api_weights.append(w)
    set_weights(polygon_name, skin_cluster_name, indices, api_weights)


def get_py_points(polygon_name):
    points = get_points(polygon_name)
    return [[points[i].x, points[i].y, points[i].z, 1] for i in range(points.length())]


def set_py_part_weight(polygon_name, indices, vtx_ids, weights):
    skin_cluster_name = cmds.ls(cmds.listHistory(polygon_name), type="skinCluster")[0]
    indices = py_to_m_array(MIntArray, indices)
    weights = py_to_m_array(MDoubleArray, sum(weights, []))
    vtx_ids = py_to_m_array(MIntArray,vtx_ids)
    set_ids_weights(polygon_name, skin_cluster_name, indices, vtx_ids, weights)
