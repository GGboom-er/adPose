# coding=utf-8
from .general_ui import *
from .config import ConfigTool
from .targets import TargetEditTool
from .grid import UVPoseTool
from .facs_ui import FaceTargetEditTool
from .twist_ui import TwistTargetEditTool
from . import ocd
from . import bs
from . import ADPose
from . import joints
from . import tools
from . import little
from .main_ui import MainEditTool


class ADPoseTool(QDialog):

    def __init__(self):
        QDialog.__init__(self, get_host_app())
        self.setObjectName("UVPoseTool")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 2, 0, 0)
        try:
            layout.setMargin(5)
        except AttributeError:
            pass
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

        self.main_ui = MainEditTool()
        self.tab.addTab(self.main_ui, u"main")

        self.setBaseSize(10, 10)
        self.tab.currentChanged.connect(self.button_refresh)

        self.bake_ocd = ocd.BakeOcd(self)
        self.bake_deform = ocd.BakeDeform(self)
        tool_menu = menu_bar.addMenu(u"工具")
        tool_menu.addAction(u"配置", self.config.showNormal)
        tool_menu.addAction(u"冻结骨骼旋转值", ADPose.free_joints)
        tool_menu.addAction(u"重置目标体", self.init_targets)
        tool_menu.addAction(u"自定义镜像", self.custom_mirror)
        tool_menu.addAction(u"导出BS和驱动", tools.export_blend_shape_sdk_data_ui)
        tool_menu.addAction(u"导入BS和驱动", tools.load_blend_shape_sdk_data_ui)

        tool_menu.addAction(u"合并模型并保留蒙皮BS", tools.comb_skin_bs)

        tool_menu.addAction(u"使用热盒模式", little.open_tool)

        ocd_menu = menu_bar.addMenu(u"ocd")
        ocd_menu.addAction(u"创建ocd", ocd.create_ocd)
        ocd_menu.addAction(u"根据蒙皮创建ocd", ocd.create_ocd_by_skin)
        ocd_menu.addAction(u"烘焙修型", self.bake_deform.show)
        ocd_menu.addAction(u"烘焙ocd", self.bake_ocd.show)

        self.create_joint_tool = joints.CreateJointTool(self)
        joints_menu = menu_bar.addMenu(u"骨骼")
        joints_menu.addAction(u"创建骨骼", self.create_joint_tool.showNormal)
        joints_menu.addAction(u"镜像骨骼", joints.mirror_joints)
        joints_menu.addAction(u"创建驱动", joints.create_plane_by_selected)
        joints_menu.addAction(u"删除驱动", joints.remove_drive_by_selected)
        joints_menu.addAction(u"创建半跟随", joints.tool_create_half_joint)

        from . import sdr_lib
        self.bs_to_skin_tool = sdr_lib.ui.PartDeformToSkinTool(self, self.get_selected_targets_list)
        joints_menu.addAction(u"局部修形转骨骼", self.bs_to_skin_tool.showNormal)

        sync_menu = menu_bar.addMenu(u"多端同步")
        from .sync_lib import export_to_unity
        sync_menu.addAction(u"导出驱动到unity", export_to_unity.show)

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
        elif self.tab.currentIndex() == 4:
            self.main_ui.list.reload()


    def get_selected_targets_list(self):
        if self.tab.currentIndex() == 0:
            targets = self.list.list.selected_targets()
            return targets
        elif self.tab.currentIndex() == 1:
            return []
        elif self.tab.currentIndex() == 2:
            targets = self.face.list.selected_targets()
            return targets
        elif self.tab.currentIndex() == 3:
            targets = self.twist.list.selected_targets()
            return targets
        elif self.tab.currentIndex() == 4:
            targets = self.main_ui.list.selected_targets()
            return targets

    def del_bs_for_points_on_targets(self):
        targets = self.get_selected_targets_list()
        bs.delete_bs_for_points(targets)

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


def show_in_maya():
    global window
    if int(str(pm.about(api=True))[:4]) > 2017:
        while pm.control("uvPoseTool_dock", query=True, exists=True):
            pm.deleteUI("uvPoseTool_dock")
        while pm.control("UVPoseTool", query=True, exists=True):
            pm.deleteUI("UVPoseTool")
        dock = pm.mel.getUIComponentDockControl("Channel Box / Layer Editor", False)
        pm.workspaceControl("uvPoseTool_dock", ttc=(dock, -1), r=1, l=u"UVPoseTool", retain=True)
        window = ADPoseTool()
        pm.control(window.objectName(), e=1, p="uvPoseTool_dock")
    else:
        if window is None:
            if pm.dockControl("uvPoseTool_dock", ex=1):
                pm.deleteUI("uvPoseTool_dock")
            window = ADPoseTool()
            pm.dockControl("uvPoseTool_dock", area='right', content="UVPoseTool",
                           allowedArea=['right', 'left'], l=u"UVPose")
        pm.dockControl("uvPoseTool_dock", e=1, vis=0)
        pm.dockControl("uvPoseTool_dock", e=1, vis=1)


"""
import adPose2
reload(adPose2)
adPose2.ui.test()
"""


def test():
    pm.openFile("D:/work/adpose/part_warp/part_warp.ma", f=1)
    from ADPose import ADPoses
    from maya import cmds
    cmds.select("YS024C_HD_Body", u'YS024C_HD_Body2.vtx[2061]', u'YS024C_HD_Body2.vtx[2064]',
                u'YS024C_HD_Body2.vtx[2066]')
    bs.tool_part_warp_copy(ADPoses.warp_copy_targets)([u"Scapula_L_a40_d90"])
    ADPoses.set_pose_by_targets(["Scapula_L_a40_d90"])
    cmds.select(u'YS024C_HD_Body2.vtx[2061]', u'YS024C_HD_Body2.vtx[2064]',u'YS024C_HD_Body2.vtx[2066]')