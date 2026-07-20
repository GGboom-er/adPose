# coding:utf-8
"""
adPose 完整调用代码 · Maya 2025
在 Maya Script Editor (Python) 中执行

前提条件：
  - 场景中有蒙皮模型（mesh + skinCluster）
  - 骨骼和 FK 控制器满足命名约定：
    骨骼 Shoulder_L  →  控制器 FKShoulder_L
    左 {name}_L  ↔  右 {name}_R
  - 命名约定可通过 config 窗口修改
"""
from maya import cmds

# ================================================================
# 0. 安装和导入
# ================================================================
import sys
from pathlib import Path

# 如果 adPose 不在 Maya 的 scripts 目录，需要手动添加父目录路径
# 方式 A：adPose 在 Maya scripts 目录下，不需要下面这行
# 方式 B：adPose 在自定义路径
adpose_parent_dir = str(Path(__file__).resolve().parent.parent)
if adpose_parent_dir not in sys.path:
    sys.path.insert(0, adpose_parent_dir)

import adPose
from adPose import ui, ADPose, bs, facs, twist, joints, tools, config, little


# ================================================================
# 1. 打开 UI 窗口（最简单的用法，推荐新手用 UI 操作）
# ================================================================
def open_ui():
    """打开 ADPose 主界面"""
    ui.show_in_maya()


# ================================================================
# 2. 姿态修正 · ADPose 核心功能（代码调用）
# ================================================================

# --- 2.1 创建单关节修正 ---
def create_pose_correction(joint_name):
    """
    在当前关节姿态下创建修正目标体

    用法：
      1. 先用 FK 控制器将骨骼摆到目标姿态
      2. 选中模型
      3. 调用此函数（首次创建编辑副本，第二次保存修正）
    示例：
      cmds.setAttr("FKShoulder_L.rz", 90)
      cmds.select("body_mesh")
      create_pose_correction("Shoulder_L")
      # → 出现编辑副本，雕刻修正体
      # → 再次调用保存：
      create_pose_correction("Shoulder_L")
    """
    ADPose.ADPoses.auto_apply(joint_name)


# --- 2.2 完成编辑并重置 ---
def finish_editing():
    """
    完成当前编辑（保存修正体）并重置所有控制器到零位

    用法：雕刻完成后调用
    """
    ADPose.ADPoses.esc()


# --- 2.3 查看所有已创建的修正目标 ---
def list_all_targets():
    """列出所有 ADPose 修正目标名"""
    targets = ADPose.ADPoses.get_targets()
    print("=== ADPose 目标列表 ===")
    for i, t in enumerate(targets):
        print(f"  {i+1}. {t}")
    return targets


# --- 2.4 切换到指定姿态预览 ---
def preview_pose(target_name, strength=60):
    """
    预览某个修正目标的效果

    参数:
      target_name: 目标名，如 "Shoulder_L_a90_d0"
      strength: 强度 0-60，60=满强度，30=50%
    """
    ADPose.ADPoses.set_pose_by_targets([target_name], [], strength)


# --- 2.5 创建组合修正（多关节） ---
def create_combo_correction(joint_names):
    """
    创建多关节组合修正

    用法：
      1. 将多个骨骼同时摆到目标姿态
      2. 选中模型
      3. 调用此函数
    示例：
      cmds.setAttr("FKShoulder_L.rz", 90)
      cmds.setAttr("FKElbow_L.rz", 90)
      cmds.select("body_mesh")
      create_combo_correction(["Shoulder_L", "Elbow_L"])
      # → 雕刻组合修正
      create_combo_correction(["Shoulder_L", "Elbow_L"])
    """
    ADPose.ADPoses.auto_apply(joint_names)


# --- 2.6 插入中间修正（In-Between） ---
def insert_inbetween(joint_names):
    """
    在已有修正目标的中间角度插入修正

    用法：
      1. 先创建好最大角度的目标（如 90°）
      2. 将关节摆到中间角度（如 45°）
      3. 调用此函数
    """
    ADPose.ADPoses.auto_insert_pose(joint_names)


# --- 2.7 镜像目标 ---
def mirror_targets(target_names):
    """
    将目标从一侧镜像到另一侧（L ↔ R）

    用法：
      cmds.select("body_mesh")
      mirror_targets(["Shoulder_L_a90_d0"])
    """
    ADPose.ADPoses.mirror_by_targets(target_names)


# --- 2.8 传递目标到另一个模型（Wrap） ---
def transfer_targets(target_names):
    """
    将目标体传递到另一个模型

    用法：先选源模型，再选目标模型
      cmds.select("body_mesh", "body_mesh_new")
      transfer_targets(["Shoulder_L_a90_d0", "Shoulder_L_a90_d180"])
    """
    ADPose.ADPoses.warp_copy_targets(target_names)


# --- 2.9 删除目标 ---
def delete_targets(target_names):
    """
    删除指定目标（会自动清理关联的 COMB 和 IB）

    用法：
      delete_targets(["Shoulder_L_a90_d0"])
    """
    ADPose.ADPoses.delete_by_targets(target_names)


# --- 2.10 重置目标体（重新计算反转 BS） ---
def reinit_targets(target_names):
    """
    重新计算目标体的反转 BlendShape 增量

    用法：修正体位置不对时使用
      cmds.select("body_mesh")
      reinit_targets(["Shoulder_L_a90_d0"])
    """
    bs.init_targets(target_names)


# --- 2.11 冻结骨骼旋转值 ---
def freeze_joint_rotations():
    """
    将选中模型的骨骼旋转值转入 jointOrient

    用法：
      cmds.select("body_mesh")
      freeze_joint_rotations()
    """
    ADPose.free_joints()


# ================================================================
# 3. FACS 表情系统
# ================================================================

# --- 3.1 创建表情修正 ---
def create_face_correction(ctrl_names):
    """
    用控制器属性创建表情修正

    用法：
      1. 调整面部控制器到目标表情（如 ctrlBrow_L.ty = 1）
      2. 选中头部模型
      3. 调用此函数
    示例：
      cmds.setAttr("ctrlBrow_L.translateY", 1)
      cmds.select("head_mesh")
      create_face_correction(["ctrlBrow_L"])
      # → 出现编辑副本，雕刻表情
      # → 再次调用保存：
      create_face_correction(["ctrlBrow_L"])
    """
    facs.auto_apply(ctrl_names)


# --- 3.2 直接用已雕刻好的模型编辑表情 ---
def apply_sculpted_face(ctrl_names):
    """
    已经有雕刻好的副本时直接应用

    用法：
      cmds.select("sculpted_head", "head_mesh")
      apply_sculpted_face(["ctrlBrow_L"])
    """
    facs.auto_add_edit_target(ctrl_names)


# --- 3.3 查看所有表情目标 ---
def list_face_targets():
    """列出所有 FACS 表情目标"""
    targets = facs.get_targets()
    print("=== FACS 表情目标 ===")
    for i, t in enumerate(targets):
        print(f"  {i+1}. {t}")
    return targets


# --- 3.4 预览表情 ---
def preview_face(target_names, strength=60):
    """
    预览表情效果

    示例：
      preview_face(["ctrlBrow_L_ty_max"])
    """
    facs.to_targets(target_names, ib=strength)


# --- 3.5 镜像表情 ---
def mirror_face_targets(target_names):
    """
    镜像表情到对侧

    用法：
      cmds.select("head_mesh")
      mirror_face_targets(["ctrlBrow_L_ty_max"])
    """
    facs.mirror_targets(target_names)


# --- 3.6 传递表情到另一模型 ---
def transfer_face_targets(target_names=None):
    """
    传递表情到另一个模型

    用法：
      cmds.select("head_mesh_old", "head_mesh_new")
      transfer_face_targets()
    """
    facs.warp_copy(target_names)


# --- 3.7 删除表情目标 ---
def delete_face_targets(target_names):
    """删除表情目标"""
    facs.delete_targets(target_names)


# --- 3.8 完成表情编辑 ---
def finish_face_editing():
    """完成表情编辑并重置"""
    facs.esc()


# ================================================================
# 4. Twist 扭转修正
# ================================================================

# --- 4.1 创建扭转修正 ---
def create_twist_correction(joint_name):
    """
    创建扭转修正目标

    用法：
      1. 旋转控制器 X 轴到目标角度
      2. 选中模型
      3. 调用此函数
    示例：
      cmds.setAttr("FKForearm_L.rx", 60)
      cmds.select("body_mesh")
      create_twist_correction("Forearm_L")
      # → 雕刻修正
      create_twist_correction("Forearm_L")
    """
    twist.auto_apply(joint_name)


# --- 4.2 直接添加扭转目标（已有雕刻） ---
def add_twist_target(joint_name):
    """
    直接在当前扭转值处添加目标，如果选中了两个模型则编辑

    用法：
      cmds.setAttr("FKForearm_L.rx", 60)
      twist.add_edit_target(joint_name)
    """
    twist.add_edit_target(joint_name)


# --- 4.3 查看所有扭转目标 ---
def list_twist_targets():
    """列出所有 Twist 扭转目标"""
    targets = twist.get_targets()
    print("=== Twist 扭转目标 ===")
    for i, t in enumerate(targets):
        print(f"  {i+1}. {t}")
    return targets


# --- 4.4 预览扭转 ---
def preview_twist(target_name, strength=60):
    """预览扭转效果"""
    twist.to_target(target_name, ib=strength)


# --- 4.5 插入扭转中间体 ---
def insert_twist_inbetween(joint_name):
    """
    在已有扭转目标的中间角度插入修正

    用法：
      cmds.setAttr("FKForearm_L.rx", 30)  # 已有 60° 的目标
      insert_twist_inbetween("Forearm_L")
    """
    twist.auto_insert_pose(joint_name)


# --- 4.6 镜像扭转 ---
def mirror_twist_targets(target_names):
    """
    镜像扭转目标

    用法：
      cmds.select("body_mesh")
      mirror_twist_targets(["Forearm_L_twistX_plus60"])
    """
    twist.mirror_targets(target_names)


# --- 4.7 传递扭转目标 ---
def transfer_twist_targets(target_names):
    """
    传递扭转目标到另一模型

    用法：
      cmds.select("body_mesh_old", "body_mesh_new")
      transfer_twist_targets(twist.get_targets())
    """
    twist.wrap_copy_targets_twist(target_names)


# --- 4.8 完成扭转编辑 ---
def finish_twist_editing():
    """完成扭转编辑并重置"""
    twist.esc()


# ================================================================
# 5. 骨骼工具
# ================================================================

# --- 5.1 创建修正骨骼 ---
def create_corrective_joints(polygon, joint_names,
                              directions=(True, True, True, True, True),
                              rotate_offset=True, mirror=True):
    """
    在网格表面创建修正骨骼

    参数：
      polygon: 模型名
      joint_names: 父骨骼名列表
      directions: 5 个方向开关 (ty+, ty-, tz+, tz-, center)
      rotate_offset: 是否使用旋转偏移
      mirror: 是否镜像创建
    示例：
      create_corrective_joints("body_mesh", ["Shoulder_L"])
    """
    joints.create_joints(polygon, joint_names, directions, rotate_offset, mirror)


# --- 5.2 镜像骨骼 ---
def mirror_corrective_joints():
    """
    镜像选中的修正骨骼

    用法：选中骨骼后调用
    """
    joints.mirror_joints()


# --- 5.3 添加骨骼到驱动系统 ---
def add_joints_to_driver():
    """
    将选中骨骼加入面部钉驱动系统

    用法：选中修正骨骼后调用
    """
    joints.tool_add_selected_joints()


# --- 5.4 从驱动系统移除骨骼 ---
def remove_joints_from_driver():
    """从驱动系统移除选中骨骼"""
    joints.tool_remove_selected_joints()


# --- 5.5 编辑骨骼驱动目标 ---
def edit_joint_target(joint_names):
    """
    编辑修正骨骼的驱动目标

    用法：
      1. 调整关节到目标姿态
      2. 移动修正骨骼到期望位置
      3. 调用此函数
    示例：
      cmds.setAttr("FKShoulder_L.rz", 90)
      cmds.setAttr("corrective_Shoulder_L_ty_plus.t", -1, 1, 0)
      edit_joint_target(["Shoulder_L"])
    """
    joints.tool_edit_target(
        lambda: ADPose.ADPoses.auto_edit_by_selected_target(joint_names)
    )


# --- 5.6 导出/导入骨骼驱动数据 ---
def export_joint_drivers():
    """导出骨骼驱动数据（JSON，通过文件对话框）"""
    from adPose.general_ui import save_data_ui, default_scene_path
    save_data_ui(default_scene_path, joints.tool_get_joint_driver_data)


def import_joint_drivers():
    """导入骨骼驱动数据（JSON，通过文件对话框）"""
    from adPose.general_ui import load_data_ui, default_scene_path
    load_data_ui(default_scene_path, joints.tool_load_joint_driver_data)


# ================================================================
# 6. 导入/导出全部数据
# ================================================================

# --- 6.1 导出全部（BS + SDK + Twist）→ .pkl ---
def export_all():
    """导出所有 BlendShape + SDK 数据（弹出文件对话框）"""
    tools.export_blend_shape_sdk_data_ui()


def export_all_to_path(path):
    """
    导出到指定路径

    示例：
      export_all_to_path(r"D:/work/my_project/correctives.pkl")
    """
    cmds.select(cmds.ls(type="transform"))  # 确保选中模型
    tools.export_blend_shape_sdk_data(path)


# --- 6.2 导入全部 ---
def import_all():
    """导入 BlendShape + SDK 数据（弹出文件对话框）"""
    tools.load_blend_shape_sdk_data_ui()


def import_all_from_path(path):
    """
    从指定路径导入

    示例：
      import_all_from_path(r"D:/work/my_project/correctives.pkl")
    """
    tools.load_blend_shape_sdk_data(path)


# --- 6.3 合并模型并保留蒙皮和 BS ---
def combine_meshes_keep_bs():
    """
    合并多个模型，保留蒙皮和 BlendShape

    用法：选中要合并的模型后调用
    """
    bs.comb_skin_bs()


# ================================================================
# 7. 命名配置
# ================================================================

def show_config():
    """打开命名配置窗口"""
    from adPose.config import ConfigTool
    tool = ConfigTool()
    tool.show()


def get_ctrl_from_joint(joint_name):
    """
    根据当前命名规则，查找骨骼对应的控制器

    示例：
      print(get_ctrl_from_joint("Shoulder_L"))  # → FKShoulder_L
    """
    return config.get_ctrl_names(joint_name)


def get_mirror_name(name):
    """
    获取镜像名

    示例：
      print(get_mirror_name("Shoulder_L"))  # → ['Shoulder_R']
    """
    return config.get_rl_names(name)


# ================================================================
# 8. 热盒模式（视口内快捷操作）
# ================================================================

def start_hotbox():
    """启动热盒模式 → Ctrl+左键弹出标记菜单"""
    little.open_tool()


def stop_hotbox():
    """关闭热盒模式"""
    little.close_tool()


# ================================================================
# 9. 完整工作流示例
# ================================================================

def demo_full_workflow():
    """
    完整工作流演示（需要场景中有蒙皮模型和 FK 控制器）

    这是一个教学用的流程说明，不会直接执行
    """
    print("""
    ╔══════════════════════════════════════════════════╗
    ║          adPose 完整工作流程示例                 ║
    ╠══════════════════════════════════════════════════╣
    ║                                                  ║
    ║  第一步：打开 UI                                 ║
    ║    open_ui()                                     ║
    ║                                                  ║
    ║  第二步：创建修正（代码方式）                     ║
    ║    # 摆姿态                                      ║
    ║    cmds.setAttr("FKShoulder_L.rz", 90)           ║
    ║    # 选模型                                      ║
    ║    cmds.select("body_mesh")                      ║
    ║    # 创建编辑副本                                ║
    ║    create_pose_correction("Shoulder_L")          ║
    ║    # 雕刻修正体...                               ║
    ║    # 保存修正                                    ║
    ║    create_pose_correction("Shoulder_L")          ║
    ║                                                  ║
    ║  第三步：镜像                                    ║
    ║    cmds.select("body_mesh")                      ║
    ║    mirror_targets(["Shoulder_L_a90_d0"])         ║
    ║                                                  ║
    ║  第四步：创建组合修正                            ║
    ║    cmds.setAttr("FKShoulder_L.rz", 90)           ║
    ║    cmds.setAttr("FKElbow_L.rz", 90)              ║
    ║    cmds.select("body_mesh")                      ║
    ║    create_combo_correction(["Shoulder_L",        ║
    ║                             "Elbow_L"])          ║
    ║    # 雕刻 → 再次调用保存                         ║
    ║    create_combo_correction(["Shoulder_L",        ║
    ║                             "Elbow_L"])          ║
    ║                                                  ║
    ║  第五步：表情修正（FACS）                        ║
    ║    cmds.setAttr("ctrlBrow_L.ty", 1)              ║
    ║    cmds.select("head_mesh")                      ║
    ║    create_face_correction(["ctrlBrow_L"])        ║
    ║    # 雕刻 → 再次调用保存                         ║
    ║    create_face_correction(["ctrlBrow_L"])        ║
    ║                                                  ║
    ║  第六步：扭转修正                                ║
    ║    cmds.setAttr("FKForearm_L.rx", 60)            ║
    ║    cmds.select("body_mesh")                      ║
    ║    create_twist_correction("Forearm_L")          ║
    ║    # 雕刻 → 再次调用保存                         ║
    ║    create_twist_correction("Forearm_L")          ║
    ║                                                  ║
    ║  第七步：导出备份                                ║
    ║    export_all()                                  ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝
    """)


# ================================================================
# 执行入口：直接打开 UI
# ================================================================
if __name__ == "__main__":
    open_ui()
