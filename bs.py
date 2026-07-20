# coding:utf-8
"""
BlendShape 核心模块
已从 pymel 迁移到 maya.cmds
"""
from maya.api.OpenMaya import *
from maya import cmds
from .bs_api import bs_api

# ---------------bs fun--------------------


# --------------- HUD 视口提示 ----------------
_ADPOSE_HUD_NAME = 'adposeEditHUD'


def show_edit_hud(target_name):
    """在视口中显示当前正在编辑的 target 名称"""
    remove_edit_hud()
    free_block = cmds.headsUpDisplay(nextFreeBlock=5)
    cmds.headsUpDisplay(
        _ADPOSE_HUD_NAME, section=5, block=free_block,
        blockSize='large', labelFontSize='large',
        label='[ADPose] Editing: %s' % target_name)


def remove_edit_hud():
    """移除视口 HUD 提示"""
    if cmds.headsUpDisplay(_ADPOSE_HUD_NAME, exists=True):
        cmds.headsUpDisplay(_ADPOSE_HUD_NAME, remove=True)


def check_leftover_edit():
    """检测场景中是否有上次未完成的编辑残留组，返回残留的 target 名称或 None"""
    if not cmds.objExists('lush_duplicate_edit'):
        return None
    return get_editing_target_name()

def api_ls(*names):
    selection_list = MSelectionList()
    for name in names:
        selection_list.add(name)
    return selection_list

def get_bs_ipt_ict(bs, index):
    ipt_name = "{bs}.it[0].itg[{index}].iti[6000].ipt".format(**locals())
    ict_name = "{bs}.it[0].itg[{index}].iti[6000].ict".format(**locals())
    ipt_plug = api_ls(ipt_name).getPlug(0)
    ict_plug = api_ls(ict_name).getPlug(0)
    return ipt_plug, ict_plug

def set_ids_points(bs, index, ids, points):
    ipt_name = "{bs}.it[0].itg[{index}].iti[6000].ipt".format(**locals())
    ict_name = "{bs}.it[0].itg[{index}].iti[6000].ict".format(**locals())
    ipt_plug, ict_plug = get_bs_ipt_ict(bs, index)
    fn_component = MFnSingleIndexedComponent()
    fn_component.create(MFn.kMeshVertComponent)
    fn_component.addElements(ids)
    fn_component_list = MFnComponentListData()
    fn_component_list.create()
    fn_component_list.add(fn_component.object())
    ict_plug.setMObject(fn_component_list.object())
    fn_points = MFnPointArrayData()
    fn_points.create(MPointArray(points))
    ipt_plug.setMObject(fn_points.object())

def get_invert_blendshape_m33(bs, index, base, orig):
    cmds.blendShape(bs, e=1, rtd=[0, index])
    cmds.setAttr(bs+".envelope", 0)
    orig_fn_mesh = MFnMesh(api_ls(orig).getDagPath(0))
    temp_orig = cmds.group(em=1, n="temp_bs_orig"+orig.split("|")[-1])
    cmds.parent(orig, temp_orig, s=1, add=1)
    dup_temp_orig = cmds.duplicate(temp_orig, n="dup_"+temp_orig)[0]
    cmds.delete(temp_orig)
    for s in cmds.listRelatives(dup_temp_orig, f=1) or []:
        cmds.setAttr(s+".intermediateObject", 0)
    offset_fn_mesh = MFnMesh(api_ls(dup_temp_orig).getDagPath(0))
    point_data = [cmds.xform(base+".vtx[*]", q=1, ws=1, t=1)]
    for xyz in "xyz":
        cmds.setAttr(dup_temp_orig+".t"+xyz, 1)
        orig_fn_mesh.setPoints(offset_fn_mesh.getPoints(MSpace.kWorld))
        point_data.append(cmds.xform(base+".vtx[*]", q=1, ws=1, t=1))
        cmds.setAttr(dup_temp_orig+".t"+xyz, 0)
    orig_fn_mesh.setPoints(offset_fn_mesh.getPoints(MSpace.kWorld))
    cmds.delete(dup_temp_orig)
    m33 = bs_api.invert_blendshape_m33(*point_data)
    cmds.setAttr(bs+".envelope", 1)
    return m33

def get_attr_logical_index(bs, name):
    """获取属性的逻辑索引"""
    attr = "{bs}.{name}".format(**locals())
    if not cmds.objExists(attr):
        return None
    plug = api_ls(attr).getPlug(0)
    return plug.logicalIndex()

M33, BASE = None, None

def cache_target(bs, index, polygon_name, orig_name):
    """缓存某个 target 的必要信息，用于实时更新/回写。"""
    global M33, BASE
    M33 = get_invert_blendshape_m33(bs, index, polygon_name, orig_name)
    BASE = bs_api.c_double_array(cmds.xform(polygon_name+".vtx[*]", q=1, ws=1, t=1))


def set_target(bs, index, target_name):
    """把 target_name 对应的 mesh 更新到 bs 的 index target 上。"""
    points = bs_api.invert_points(BASE, cmds.xform(target_name+".vtx[*]", q=1, ws=1, t=1), M33)
    ids, points = bs_api.zip_points(points)
    set_ids_points(bs, index, ids, points)


def set_bs_ids_points(polygon, name, ids, points):
    """设置 blendShape 目标的顶点 ID 和位置"""
    bs = get_bs(polygon)
    index = get_attr_logical_index(bs, name)
    if index is None:
        return
    set_ids_points(bs, index, ids, points)


def api_edit_target(bs, index, target, base, orig):
    m33 = get_invert_blendshape_m33(bs, index, base, orig)
    target_points = cmds.xform(target + ".vtx[*]", q=1, ws=1, t=1)
    base_points = cmds.xform(base + ".vtx[*]", q=1, ws=1, t=1)
    points = bs_api.invert_points(base_points, target_points, m33)
    ids, points = bs_api.zip_points(points)
    if len(ids) == 0:
        delete_target_by_index(bs, index)
    else:
        set_ids_points(bs, index, ids, points)


def get_bs(polygon):
    """获取或创建 blendShape 节点"""
    bs_list = [n for n in cmds.listHistory(polygon) or [] if cmds.nodeType(n) == "blendShape"]
    if bs_list:
        bs = bs_list[0]
    else:
        short_name = polygon.split("|")[-1]
        # Maya < 2016 不支持 automatic 参数，回退到手动方式
        try:
            bs = cmds.blendShape(polygon, automatic=True, n=short_name + "_bs")[0]
        except TypeError:
            dup = cmds.duplicate(polygon)[0]
            bs = cmds.blendShape(dup, polygon, frontOfChain=True, n=short_name + "_bs")[0]
            cmds.delete(dup)
            # 删除第一个目标
            cmds.aliasAttr(bs + ".weight[0]", rm=True)
            cmds.removeMultiInstance(bs + ".weight[0]", b=True)
            cmds.removeMultiInstance(bs + ".it[0].itg[0]", b=True)
    return bs

def find_bs(polygon):
    """查找 blendShape 节点"""
    for node in cmds.listHistory(polygon) or []:
        if cmds.nodeType(node) == "blendShape":
            return node
    return None

def get_orig(polygon):
    """获取原始形状节点"""
    shapes = cmds.listRelatives(polygon, s=True, f=True) or []
    orig_list = []
    for shape in shapes:
        if cmds.getAttr(shape + ".intermediateObject"):
            orig_list.append(shape)
    # 按输出连接数排序
    orig_list.sort(key=lambda x: len(set(cmds.listConnections(x, s=False, d=True) or [])))
    if orig_list:
        return orig_list[-1]
    return None

def edit_target(target, base, name):
    """编辑 blendShape 目标"""
    bs = get_bs(base)
    if not cmds.attributeQuery(name, node=bs, exists=True):
        return
    index = get_attr_logical_index(bs, name)
    if index is None:
        return
    orig = get_orig(base)
    api_edit_target(bs, index, target, base, orig)


def get_next_index(bs):
    elem_indexes = cmds.getAttr(bs+".weight", mi=1) or []
    index = len(elem_indexes)
    for i in range(index):
        if i == elem_indexes[i]:
            continue
        index = i
        break
    return index

def add_bs_target(bs, name):
    if cmds.objExists(bs + "." + name):
        return
    index = get_next_index(bs)
    bs_attr = bs+'.weight[%i]' % index
    cmds.setAttr(bs+'.weight[%i]' % index, 1)
    cmds.aliasAttr(name, bs_attr)
    ipt_name = "{bs}.it[0].itg[{index}].iti[6000].ipt".format(**locals())
    ict_name = "{bs}.it[0].itg[{index}].iti[6000].ict".format(**locals())
    cmds.getAttr(ipt_name, type=1)
    cmds.getAttr(ict_name, type=1)

def add_target(polygon, name):
    """添加 blendShape 目标"""
    bs = get_bs(polygon)
    add_bs_target(bs, name)



def get_ids_points(bs, index):
    ipt = "{bs}.it[0].itg[{index}].iti[6000].ipt".format(**locals())
    ict = "{bs}.it[0].itg[{index}].iti[6000].ict".format(**locals())
    if not cmds.objExists(ipt) or not cmds.objExists(ict):
        return [], []
    try:
        obj = api_ls(ict).getPlug(0).asMObject()
    except RuntimeError as e:
        cmds.warning('get_ids_points: failed to read component data for %s[%s]: %s' % (bs, index, e))
        return [], []
    ids = []
    fn_component_list = MFnComponentListData(obj)
    for i in range(fn_component_list.length()):
        fn_component = MFnSingleIndexedComponent(fn_component_list.get(i))
        ids.extend(fn_component.getElements())
    points = cmds.getAttr(ipt)
    return ids, points


def bridge_connect(attr, dst):
    """桥接连接属性到目标"""
    # attr 格式: "node.attrName"
    parts = attr.split(".")
    name = parts[-1] if len(parts) > 1 else attr
    add_target(dst, name)
    bs = get_bs(dst)
    # 检查是否已连接
    dst_attr = "{}.{}".format(bs, name)
    connections = cmds.listConnections(dst_attr, s=True, d=False, p=True) or []
    if attr not in connections:
        cmds.connectAttr(attr, dst_attr, f=True)


def bridge_connect_edit(attr, src, dst):
    """桥接连接并编辑目标"""
    bridge_connect(attr, dst)
    parts = attr.split(".")
    name = parts[-1] if len(parts) > 1 else attr
    edit_target(src, dst, name)


def delete_target_by_index(bs, index):
    weight_attr = "{}.weight[{}]".format(bs, index)
    cmds.aliasAttr(weight_attr, rm=True)
    cmds.removeMultiInstance(weight_attr, b=True)
    cmds.removeMultiInstance("{}.it[0].itg[{}]".format(bs, index), b=True)


def delete_target(bs_or_attr, target_name=None):
    """删除 blendShape 目标
    支持两种调用方式：
    - 新方式: delete_target(bs, target_name)
    - 旧方式: delete_target(weight_attr)  # 兼容 PyNode 属性
    """
    if target_name is None:
        # 旧方式调用，bs_or_attr 是 PyNode 属性或字符串属性
        if hasattr(bs_or_attr, 'node'):
            # PyNode 属性
            bs = bs_or_attr.node().name()
            target_name = bs_or_attr.name(includeNode=False)
        else:
            # 字符串属性 "bs.targetName"
            parts = str(bs_or_attr).split(".")
            bs = parts[0]
            target_name = parts[-1]
    else:
        bs = bs_or_attr

    index = get_attr_logical_index(bs, target_name)
    if index is None:
        return
    delete_target_by_index(bs, index)

def mirror_targets(polygon, names):
    """镜像多个目标"""
    bs = get_bs(polygon)
    src_indexes = []
    dst_indexes = []
    for src, dst in names:
        if not cmds.attributeQuery(src, node=bs, exists=True):
            cmds.warning("mirror_targets: source '{}' not found on BS node '{}'".format(src, bs))
            continue
        if not cmds.attributeQuery(dst, node=bs, exists=True):
            cmds.warning("mirror_targets: destination '{}' not found on BS node '{}'".format(dst, bs))
            continue
        src_indexes.append(get_attr_logical_index(bs, src))
        dst_indexes.append(get_attr_logical_index(bs, dst))
    symmetric_cache = {key: cmds.symmetricModelling(q=1, **{key: True}) for key in ["s", "t", "ax", "a"]}
    for src_id, dst_id in zip(src_indexes, dst_indexes):
        if src_id != dst_id:
            cmds.blendShape(bs, e=1, rtd=[0, dst_id])
            cmds.blendShape(bs, e=1, cd=[0, src_id, dst_id])
            cmds.blendShape(bs, e=1, ft=[0, dst_id], sa="X", ss=1)
        else:
            cmds.blendShape(bs, e=1, md=0, mt=[0, dst_id], sa="X", ss=1)
    for k, value in symmetric_cache.items():
        cmds.symmetricModelling(**{k: value})


def init_sel_polygons_targets(target_names):
    """初始化目标"""
    polygon_list = (cmds.ls("*Driver", type="transform", o=True) or []) + (cmds.ls(sl=True, type="transform", o=True) or [])
    polygon_list = list(filter(is_polygon, polygon_list))
    for polygon in polygon_list:
        bs = get_bs(polygon)
        for target_name in target_names:
            if not cmds.attributeQuery(target_name, node=bs, exists=True):
                return
            index = get_attr_logical_index(bs, target_name)
            if index is not None:
                cmds.blendShape(bs, e=1, rtd=[0, index])


def get_selected_polygon_ids():
    sel = MGlobal.getActiveSelectionList()
    if not sel.length():
        return None, None
    dag_path, component = sel.getComponent(0)
    if component.apiTypeStr != "kMeshVertComponent":
        return None, None
    ids = MFnSingleIndexedComponent(component).getElements()
    polygon = cmds.listRelatives(dag_path.partialPathName(), p=1)[0]
    return polygon, ids


def init_sel_vtx_targets(polygon, remove_ids, target_names):
    bs = get_bs(polygon)
    point_count = cmds.polyEvaluate(polygon, vertex=1)
    for target_name in target_names:
        bs_attr = bs + "." + target_name
        if not cmds.objExists(bs_attr):
            continue
        index = get_attr_logical_index(bs, target_name)
        ids, points = get_ids_points(bs, index)
        full_points = bs_api.unzip_points(ids, points, point_count)
        remove_ids = list(remove_ids)
        bs_api.remove_points(full_points, remove_ids)
        ids, points = bs_api.zip_points(full_points)
        set_ids_points(bs, index, ids, points)


def init_targets(target_names):
    polygon, ids = get_selected_polygon_ids()
    if ids is None:
        init_sel_polygons_targets(target_names)
    else:
        init_sel_vtx_targets(polygon, ids, target_names)


def get_bs_target_names(bs):
    """获取 blendShape 的所有目标名称"""
    # aliases = cmds.aliasAttr(bs, q=True) or []
    # return [aliases[i] for i in range(0, len(aliases), 2)]
    return cmds.listAttr(bs+".weight", m=1)


def is_on_duplicate_edit():
    return cmds.objExists("lush_duplicate_edit")


class LEditTargetJob(object):

    def __init__(self, src, dst, target):
        self.del_job()
        self.bs = get_bs(dst)
        self.index = get_attr_logical_index(self.bs, target)
        self.src = src
        cache_target(self.bs, self.index, dst, get_orig(dst))
        cmds.scriptJob(attributeChange=[cmds.listRelatives(src, s=1)[0] + ".outMesh", self])

    def __repr__(self):
        return self.__class__.__name__

    def __call__(self):
        set_target(self.bs, self.index, self.src)

    def add_job(self):
        self.del_job()

    @classmethod
    def del_job(cls):
        for job in cmds.scriptJob(listJobs=True):
            if repr(cls.__name__) in job:
                cmds.scriptJob(kill=int(job.split(":")[0]))

def is_polygon(polygon):
    """判断节点是否为多边形"""
    if not cmds.objExists(polygon):
        return False
    if cmds.nodeType(polygon) != "transform":
        return False
    shapes = cmds.listRelatives(polygon, s=True, ni=True)
    if not shapes:
        return False
    if cmds.nodeType(shapes[0]) != "mesh":
        return False
    return True


def finish_duplicate_edit(set_pose_by_target):
    LEditTargetJob.del_job()
    root = "|lush_duplicate_edit"
    if not cmds.objExists(root):
        return
    try:
        for target_group in cmds.listRelatives(root) or []:
            if target_group[:5] != "edit_":
                continue
            target = target_group[5:]
            set_pose_by_target(target)
            for src in cmds.listRelatives(target_group) or []:
                if not is_polygon(src):
                    continue
                if not cmds.objExists(src+".edit_polygon_message"):
                    continue
                dst = cmds.listConnections(src+".edit_polygon_message", s=True, d=0, p=0)
                if not dst:
                    continue
                dst = dst[0]
                if not is_polygon(dst):
                    continue
                uu = cmds.ls(cmds.listConnections(dst+".v", s=1, d=0), type=["animCurveUU", "blendWeighted"])
                if uu:
                    cmds.delete(uu)
                restore_visibility(dst, src)
                edit_target(src, dst, target)
    finally:
        remove_edit_hud()
        if cmds.objExists(root):
            cmds.delete(root)


def cancel_duplicate_edit():
    """放弃当前编辑，不写入任何修改，恢复可见性、清理新建的 BS target 和临时组"""
    LEditTargetJob.del_job()
    root = "|lush_duplicate_edit"
    if not cmds.objExists(root):
        return
    # ★ 读取新创建的 target 列表（cancel 时需要清理）
    new_targets = []
    if cmds.attributeQuery("adpose_new_targets", node=root, exists=True):
        val = cmds.getAttr(root + ".adpose_new_targets") or ""
        new_targets = [t for t in val.split(",") if t]
    try:
        for target_group in cmds.listRelatives(root) or []:
            if target_group[:5] != "edit_":
                continue
            target = target_group[5:]
            for src in cmds.listRelatives(target_group) or []:
                if not is_polygon(src):
                    continue
                if not cmds.objExists(src + ".edit_polygon_message"):
                    continue
                dst = cmds.listConnections(src + ".edit_polygon_message", s=True, d=0, p=0)
                if not dst:
                    continue
                dst = dst[0]
                if not is_polygon(dst):
                    continue
                # 恢复原始网格可见性（清理 SDK 曲线，并恢复原有的连接或锁定状态）
                uu = cmds.ls(cmds.listConnections(dst + ".v", s=1, d=0), type=["animCurveUU", "blendWeighted"])
                if uu:
                    cmds.delete(uu)
                restore_visibility(dst, src)
                # ★ 清理新创建的 blendShape target（不清理已有的）
                if target in new_targets:
                    bs_node = find_bs(dst)
                    if bs_node and cmds.attributeQuery(target, node=bs_node, exists=True):
                        idx = get_attr_logical_index(bs_node, target)
                        if idx is not None:
                            # 断开连接再删除
                            attr = bs_node + "." + target
                            for conn in cmds.listConnections(attr, s=True, d=False, p=True) or []:
                                if cmds.isConnected(conn, attr):
                                    cmds.disconnectAttr(conn, attr)
                            delete_target_by_index(bs_node, idx)
    finally:
        remove_edit_hud()
        if cmds.objExists(root):
            cmds.delete(root)


def get_editing_target_name():
    """返回当前正在编辑的 target 名称，未在编辑中则返回 None"""
    root = "|lush_duplicate_edit"
    if not cmds.objExists(root):
        return None
    if cmds.attributeQuery("adpose_editing_target", node=root, exists=True):
        return cmds.getAttr(root + ".adpose_editing_target")
    # 回退：从子组名称解析
    for child in cmds.listRelatives(root) or []:
        if child[:5] == "edit_":
            return child[5:]
    return None


def get_selected_polygons():
    return list(filter(is_polygon, cmds.ls(sl=1, o=1)))


def get_target_current_weight(target_name):
    """查询指定 target 在所有 blendShape 节点上的当前权重值（0.0~1.0）"""
    for bs_node in cmds.ls(type="blendShape") or []:
        attr = bs_node + "." + target_name
        if cmds.objExists(attr):
            return cmds.getAttr(attr)
    return 0.0


def get_all_target_weights(target_names):
    """批量查询多个 target 的当前权重，返回 {target_name: weight} 字典（性能优化版）"""
    weights = {name: 0.0 for name in target_names}
    bs_nodes = cmds.ls(type="blendShape") or []
    if not bs_nodes or not target_names:
        return weights

    target_set = set(target_names)
    for bs_node in bs_nodes:
        # aliasAttr 返回 [alias, real_attr, alias, real_attr...]，极快
        aliases = cmds.aliasAttr(bs_node, q=True) or []
        for i in range(0, len(aliases), 2):
            alias = aliases[i]
            if alias in target_set:
                weights[alias] = cmds.getAttr(bs_node + "." + alias)
                target_set.remove(alias)
        if not target_set:
            break
    return weights

def duplicate_polygon_by_target(target, polygon):
    root = "lush_duplicate_edit"
    parent = "edit_"+target
    name = target + "_" + polygon.split("|")[-1].split(":")[-1]
    if not cmds.objExists(root):
        cmds.group(em=1, n=root)
    # ★ 在根节点上存储当前编辑的 target 名称（用于 UI 显示和状态查询）
    if not cmds.attributeQuery("adpose_editing_target", node=root, exists=True):
        cmds.addAttr(root, ln="adpose_editing_target", dt="string")
    cmds.setAttr(root + ".adpose_editing_target", target, type="string")
    show_edit_hud(target)
    if not cmds.objExists("|lush_duplicate_edit|"+parent):
        cmds.group(em=1, n=parent, p=root)
    if cmds.objExists(name):
        return name
    dup = cmds.duplicate(polygon, n=name)[0]
    # ★ WYSIWYG：删除复制体上的所有历史，让它变成静态雕塑
    cmds.delete(dup, ch=True)
    for shape in cmds.listRelatives(dup, s=1, f=1) or []:
        if cmds.getAttr(shape + '.io'):
            cmds.delete(shape)
    cmds.parent(dup, parent)
    for shape in cmds.listRelatives(dup, s=1, f=1) or []:
        cmds.setAttr(shape + '.overrideEnabled', True)
        cmds.setAttr(shape + '.overrideColor', 13)
    if not cmds.objExists(dup+".edit_polygon_message"):
        cmds.addAttr(dup, ln="edit_polygon_message", at="message")
    cmds.connectAttr(polygon+".v", dup+".edit_polygon_message")
    return dup


def connect_polygons(attrs, polygons):
    for attr in attrs:
        for polygon in polygons:
            bridge_connect(attr, polygon)

def store_and_unlock_visibility(src_mesh, dup_mesh):
    """保存并解锁原始网格的可见性，防止打断绑定的控制连接 (存在源 mesh 上保证稳定性)"""
    if not cmds.attributeQuery("adpose_orig_vis_lock", node=src_mesh, exists=True):
        cmds.addAttr(src_mesh, ln="adpose_orig_vis_lock", at="bool")
    cmds.setAttr(src_mesh + ".adpose_orig_vis_lock", cmds.getAttr(src_mesh + ".v", lock=True))

    conn = cmds.listConnections(src_mesh + ".v", s=True, d=False, p=True)
    if conn:
        if not cmds.attributeQuery("adpose_orig_vis_conn", node=src_mesh, exists=True):
            cmds.addAttr(src_mesh, ln="adpose_orig_vis_conn", dt="string")
        cmds.setAttr(src_mesh + ".adpose_orig_vis_conn", conn[0], type="string")
        cmds.disconnectAttr(conn[0], src_mesh + ".v")
    else:
        if not cmds.attributeQuery("adpose_orig_vis_val", node=src_mesh, exists=True):
            cmds.addAttr(src_mesh, ln="adpose_orig_vis_val", at="bool")
        cmds.setAttr(src_mesh + ".adpose_orig_vis_val", cmds.getAttr(src_mesh + ".v"))

    cmds.setAttr(src_mesh + ".v", lock=False)

def restore_visibility(src_mesh, dup_mesh):
    """恢复原始网格的可见性状态并清理暂存属性"""
    if cmds.attributeQuery("adpose_orig_vis_conn", node=src_mesh, exists=True):
        conn = cmds.getAttr(src_mesh + ".adpose_orig_vis_conn")
        if cmds.objExists(conn):
            cmds.connectAttr(conn, src_mesh + ".v", f=True)
        cmds.deleteAttr(src_mesh, at="adpose_orig_vis_conn")
    elif cmds.attributeQuery("adpose_orig_vis_val", node=src_mesh, exists=True):
        cmds.setAttr(src_mesh + ".v", cmds.getAttr(src_mesh + ".adpose_orig_vis_val"))
        cmds.deleteAttr(src_mesh, at="adpose_orig_vis_val")
    else:
        cmds.setAttr(src_mesh + ".v", True)

    if cmds.attributeQuery("adpose_orig_vis_lock", node=src_mesh, exists=True):
        if cmds.getAttr(src_mesh + ".adpose_orig_vis_lock"):
            cmds.setAttr(src_mesh + ".v", lock=True)
        cmds.deleteAttr(src_mesh, at="adpose_orig_vis_lock")

def driver_polygon_vis(attr, polygon, dup):
    store_and_unlock_visibility(polygon, dup)
    cmds.setDrivenKeyframe(polygon + ".v", cd=attr, dv=0.0, v=1, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(polygon + ".v", cd=attr, dv=0.99, v=1, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(polygon + ".v", cd=attr, dv=1.0, v=0, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(dup + ".v", cd=attr, dv=0.0, v=0, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(dup + ".v", cd=attr, dv=0.99, v=0, itt="linear", ott="linear")
    cmds.setDrivenKeyframe(dup + ".v", cd=attr, dv=1.0, v=1, itt="linear", ott="linear")

def duplicate_polygon(attr, polygon):
    target = attr.split(".")[-1]
    dup = duplicate_polygon_by_target(target, polygon)
    driver_polygon_vis(attr, polygon, dup)
    return dup


def duplicate_edit_polygon(attr, polygon):
    dup = duplicate_polygon(attr, polygon)
    target = attr.split(".")[-1]
    bridge_connect(attr, polygon)
    LEditTargetJob(dup, polygon, target)
    wireframe_planes()


def duplicate_edit_selected_polygons2(
        target_names, add_pose_by_target, set_pose_by_target, preserve_current_pose=False):
    polygons = get_selected_polygons()
    if len(polygons) == 0:
        return
    if len(target_names) == 0:
        return
    # ★ 记录哪些 target 是新创建的（cancel 时需要清理）
    new_targets = []
    for polygon in polygons:
        bs_node = find_bs(polygon)
        if bs_node:
            for target_name in target_names:
                if not cmds.attributeQuery(target_name, node=bs_node, exists=True):
                    new_targets.append(target_name)
            break
    # ★ 先设到 target pose 再复制，确保冻结的 dup 与 finish 时的 base 在同一 pose
    # dup 已冻结（delete ch=True），后续 pose 变化不影响它 = WYSIWYG
    for target_name in target_names:
        if not preserve_current_pose:
            set_pose_by_target(target_name)
        for polygon in polygons:
            duplicate_polygon_by_target(target_name, polygon)
    attrs = []
    for target_name in target_names:
        attrs.append(add_pose_by_target(target_name))
    connect_polygons(attrs, polygons)
    # ★ 在 root 节点上存储新创建的 target 列表
    root = "|lush_duplicate_edit"
    if cmds.objExists(root) and new_targets:
        if not cmds.attributeQuery("adpose_new_targets", node=root, exists=True):
            cmds.addAttr(root, ln="adpose_new_targets", dt="string")
        cmds.setAttr(root + ".adpose_new_targets", ",".join(new_targets), type="string")
    duplicate_edit_polygon(attrs[0], polygons[0])


def auto_duplicate_edit(
        target_names, add_pose_by_target, set_pose_by_target, preserve_current_pose=False):
    if is_on_duplicate_edit():
        try:
            finish_duplicate_edit(set_pose_by_target)
        except Exception as e:
            cmds.warning('finish_duplicate_edit error: %s' % e)
            import traceback; traceback.print_exc()
    else:
        try:
            duplicate_edit_selected_polygons2(
                target_names, add_pose_by_target, set_pose_by_target, preserve_current_pose
            )
        except Exception as e:
            if cmds.objExists("lush_duplicate_edit"):
                cmds.delete("lush_duplicate_edit")
            raise e

def wireframe_planes():
    panels = cmds.getPanel(all=True)
    for panel in panels:
        if cmds.modelPanel(panel, ex=1):
            try:
                cmds.modelEditor(panel, e=1, wireframeOnShaded=True)
            except RuntimeError:
                pass
    cmds.select(cl=1)


def get_bs_target_input(bs, target_name):
    """获取属性目标输入属性"""
    attr = bs + "." + target_name
    inputs = cmds.listConnections(attr, s=True, d=False, p=True) or []
    if len(inputs) != 1:
        return None
    return inputs[0]


def get_attr_target_names(polygons):
    """获取属性目标名称"""
    target_names = []
    input_attrs = []
    for polygon in polygons:
        bs = find_bs(polygon)
        if not bs:
            continue
        for target_name in get_bs_target_names(bs):
            if target_name in target_names:
                continue
            target_names.append(target_name)
            input_attrs.append(get_bs_target_input(bs, target_name))
    return list(zip(input_attrs, target_names))


def get_joints(polygons):
    """获取骨骼"""
    joints = []
    for polygon in polygons:
        for node in cmds.listHistory(polygon) or []:
            if cmds.nodeType(node) == "skinCluster":
                influences = cmds.skinCluster(node, q=True, inf=True) or []
                for joint in influences:
                    if joint not in joints:
                        joints.append(joint)
    return joints

def comb_skin_bs():
    """合并蒙皮和 blendShape"""
    polygons = get_selected_polygons()
    duplicate_polygons = [cmds.duplicate(polygon)[0] for polygon in polygons]
    joints = get_joints(polygons)
    com_polygon = cmds.polyUnite(duplicate_polygons, ch=False)[0]
    cmds.delete(cmds.ls(duplicate_polygons))
    if joints:
        cmds.skinCluster(joints, com_polygon, tsb=True, mi=1)
        cmds.select(polygons + [com_polygon])
        cmds.copySkinWeights(noMirror=True, surfaceAssociation="closestPoint", influenceAssociation="name")
    attr_target_names = get_attr_target_names(polygons)
    for input_attr, target_name in attr_target_names:
        full_point_data = []
        for polygon in polygons:
            point_count = cmds.polyEvaluate(polygon, v=True)
            bs = find_bs(polygon)
            if bs and cmds.objExists(bs+"."+target_name):
                index = get_attr_logical_index(bs, target_name)
                ids, points = get_ids_points(bs, index)
                full_points = bs_api.unzip_points(ids, points, point_count)
            else:
                full_points = bs_api.unzip_points([], [], point_count)
            full_point_data.append(full_points)
        full_points = bs_api.merge_points(*full_point_data)
        ids, points = bs_api.zip_points(full_points)
        add_target(com_polygon, target_name)
        set_bs_ids_points(com_polygon, target_name, ids, points)
        if input_attr:
            bridge_connect(input_attr, com_polygon)


def get_bs_target_data(bs, target):
    index = get_attr_logical_index(bs, target)
    if index is None:
        return None
    ids, points = get_ids_points(bs, index)
    ids = list(ids)
    driver = get_bs_target_input(bs, target)
    return dict(ids=ids, points=points, driver=driver, target=target)

def set_bs_target_data(bs, data):
    target = data["target"]
    add_bs_target(bs, target)
    set_bs_ids_points(bs, target, data["ids"], data["points"])
    dst_attr = "{}.{}".format(bs, target)
    src_attr = data["driver"]
    if not src_attr:
        return
    if not cmds.isConnected(src_attr, dst_attr):
        cmds.connectAttr(src_attr, dst_attr, f=1)


def custom_mirror(target_names):
    """自定义镜像"""
    if len(target_names) != 2:
        return
    polygon_list = (cmds.ls("*Driver", type="transform", o=True) or []) + (cmds.ls(sl=True, type="transform", o=True) or [])
    polygon_list = list(filter(is_polygon, polygon_list))
    target_mirrors = [target_names]
    for polygon in polygon_list:
        for src, dst in target_mirrors:
            add_target(polygon, dst)
        mirror_targets(polygon, target_mirrors)
