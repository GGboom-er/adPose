# coding=utf-8
from .general_ui import *
from .config import ConfigTool
from .targets import TargetEditTool
from .grid import UVPoseTool
from .facs_ui import FaceTargetEditTool
from .twist_ui import TwistTargetEditTool
from . import bs
from . import ADPose
from . import tools
from . import little
from . import joints

class ADPoseTool(QDialog):

    def __init__(self):
        QDialog.__init__(self, get_host_app())
        self.setObjectName("ADPoseTool")
        self.setWindowTitle(u"ADPose")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 2, 0, 0)
        if hasattr(layout, 'setMargin'):
            layout.setMargin(5)
        self.setLayout(layout)
        self.config = ConfigTool(self)
        menu_bar = QMenuBar()
        layout.setMenuBar(menu_bar)

        self.list = TargetEditTool(self)
        self.face = FaceTargetEditTool(self)
        self.grid = UVPoseTool()
        self.twist = TwistTargetEditTool(self)

        self.tab = QTabWidget(self)
        layout.addWidget(self.tab)
        self.tab.addTab(self.list, u"列表")
        self.tab.addTab(self.grid, u"网格")
        self.tab.addTab(self.face, u"表情")
        self.tab.addTab(self.twist, u"twist")
        self.setBaseSize(10, 10)
        self.tab.currentChanged.connect(self.button_refresh)
        tool_menu = menu_bar.addMenu(u"工具")
        tool_menu.addAction(u"配置", self.config.showNormal)
        tool_menu.addAction(u"冻结骨骼旋转值", ADPose.free_joints)
        tool_menu.addAction(u"重置目标体", self.init_targets)
        tool_menu.addAction(u"自定义镜像", self.custom_mirror)
        tool_menu.addAction(u"导出BS和驱动", tools.export_blend_shape_sdk_data_ui)
        tool_menu.addAction(u"导入BS和驱动", tools.load_blend_shape_sdk_data_ui)
        tool_menu.addAction(u"合并模型并保留蒙皮BS", bs.comb_skin_bs)
        tool_menu.addAction(u"使用热盒模式", little.open_tool)

        self.create_joint_tool = joints.CreateJointTool(self)
        joints_menu = menu_bar.addMenu(u"骨骼")
        joints_menu.addAction(u"创建骨骼", self.create_joint_tool.showNormal)
        joints_menu.addAction(u"镜像骨骼", joints.mirror_joints)
        joints_menu.addAction(u"为骨骼创建Pin驱动", lambda: (joints.tool_add_selected_joints(), self.list.list.reload()))
        joints_menu.addAction(u"移除骨骼Pin驱动", lambda: (joints.tool_remove_selected_joints(), self.list.list.reload()))
        joints_menu.addAction(u"导出驱动", lambda : save_data_ui(default_scene_path, joints.tool_get_joint_driver_data))
        joints_menu.addAction(u"导入驱动", lambda : load_data_ui(default_scene_path, joints.tool_load_joint_driver_data))


    def button_refresh(self):
        if self.tab.currentIndex() == 0:
            self.list.list.reload()
        elif self.tab.currentIndex() == 1:
            self.grid.grid.set_control([0, 0])
            self.grid.reload()
        elif self.tab.currentIndex() == 2:
            self.face.list.reload()
        elif self.tab.currentIndex() == 3:
            self.twist.list.reload()


    def get_selected_targets_list(self):
        if self.tab.currentIndex() == 0:
            return self.list.list.selected_targets()
        elif self.tab.currentIndex() == 1:
            return []
        elif self.tab.currentIndex() == 2:
            return self.face.list.selected_targets()
        elif self.tab.currentIndex() == 3:
            return self.twist.list.selected_targets()
        return []

    def init_targets(self):
        bs.init_targets(self.get_selected_targets_list())

    def custom_mirror(self):
        bs.custom_mirror(self.get_selected_targets_list())



window = None


def show():
    global window
    if window is None:
        window = ADPoseTool()
    window.show()
    window.tab.setCurrentIndex(0)
    # 检测上次未完成的编辑残留
    leftover = bs.check_leftover_edit()
    if leftover:
        bs.show_edit_hud(leftover)
        reply = QMessageBox.question(
            window, u"ADPose",
            u"检测到上次未完成的编辑：%s\n\n点击 Yes 完成写入，点击 No 放弃修改。" % leftover,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            bs.finish_duplicate_edit(ADPose.ADPoses.set_pose_by_target)
        else:
            bs.cancel_duplicate_edit()
        window.list.list.reload()


def show_in_maya():
    global window
    from maya import cmds, mel
    # 清理旧窗口
    for ctrl_name in ["adpose_dock", "uvPoseTool_dock", "ADPoseTool", "UVPoseTool"]:
        if cmds.control(ctrl_name, query=True, exists=True):
            cmds.deleteUI(ctrl_name)
    # 创建独立窗口
    window = ADPoseTool()
    window.show()
    window.tab.setCurrentIndex(0)
    # 检测上次未完成的编辑残留
    leftover = bs.check_leftover_edit()
    if leftover:
        bs.show_edit_hud(leftover)
        reply = QMessageBox.question(
            window, u"ADPose",
            u"检测到上次未完成的编辑：%s\n\n点击 Yes 完成写入，点击 No 放弃修改。" % leftover,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            bs.finish_duplicate_edit(ADPose.ADPoses.set_pose_by_target)
        else:
            bs.cancel_duplicate_edit()
        window.list.list.reload()
