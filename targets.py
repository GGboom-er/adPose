# coding:utf-8
from .general_ui import *
from .ADPose import ADPoses
from . import bs
from . import joints


class TargetList(QListWidget):
    mirrorTargets = Signal(list)

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionMode(self.ExtendedSelection)
        self.menu = QMenu(self)
        self.menu.addAction(u"添加/修改", self.auto_edit_by_selected_target)
        self.menu.addAction(u"插入姿势", self.auto_insert_pose)
        self.menu.addAction(u"骨骼驱动", self.auto_edit_body_deform)
        self.menu.addAction(u"删除", self.delete_targets)
        self.menu.addAction(u"镜像", self.mirror_targets)
        self.menu.addAction(u"传递", self.warp_copy_targets)
        self.itemDoubleClicked.connect(self.set_pose)
        self.text = ""
        self.reload()

    def auto_insert_pose(self):
        ADPoses.auto_insert_pose(self.text.split(","))
        self.reload()

    def auto_edit_by_selected_target(self):
        ADPoses.auto_edit_by_selected_target(self.text.split(","))
        self.reload()

    def auto_edit_body_deform(self):
        joints.body_deform_sdk(self.text.split(","))
        self.reload()

    def set_pose(self):
        ADPoses.set_pose_by_targets(self.selected_targets())

    def mirror_targets(self):
        self.mirrorTargets.emit(self.selected_targets())

    def delete_targets(self):
        ADPoses.delete_by_targets(self.selected_targets())
        self.reload()

    def selected_targets(self):
        return [item.text() for item in self.selectedItems()]

    def warp_copy_targets(self):
        bs.tool_part_warp_copy(ADPoses.warp_copy_targets)(self.selected_targets())

    def reload(self):
        self.clear()
        self.addItems(ADPoses.get_targets())
        self.query()

    def query(self):
        if not hasattr(self, "setItemHidden"):
            return
        if self.text:
            for i in range(self.count()):
                item = self.item(i)
                if any([field in item.text() for field in self.text.split(",")]):
                    self.setItemHidden(item, False)
                else:
                    self.setItemHidden(item, True)
        else:
            for i in range(self.count()):
                item = self.item(i)
                self.setItemHidden(item, False)

    def set_text(self, text):
        self.text = text
        self.query()

    def load_objs(self, text):
        self.text = text
        self.reload()
        self.query()

    def contextMenuEvent(self, event):
        self.menu.exec_(event.globalPos())

    def get_targets(self):
        return [self.item(i).text() for i in range(self.count())]


class TargetEditTool(Tool):
    button_text = u"复制/修改"

    def __init__(self, parent=None):
        Tool.__init__(self, parent)
        self.polygons = MayaObjLayouts(u"模型：", 40)
        self.query = MayaObjLayouts(u"搜索：", 40)
        self.query.line.setReadOnly(False)
        self.slider = TargetSlider()
        self.list = TargetList(self)
        self.kwargs_layout.addLayout(self.slider)
        self.kwargs_layout.addLayout(self.polygons)
        self.kwargs_layout.addLayout(self.query)
        self.kwargs_layout.addWidget(self.list)
        self.query.textChanged.connect(self.list.load_objs)
        self.query.line.textChanged.connect(self.list.set_text)
        self.list.mirrorTargets.connect(self.mirror)
        self.slider.slider.valueChanged.connect(self.set_ib_pose_by_targets)
        self.slider.button.clicked.connect(self.esc)

    def set_ib_pose_by_targets(self, value):
        ADPoses.set_pose_by_targets(self.list.selected_targets(), [], value)
        pm.refresh()

    def apply(self):
        polygons = self.get_polygons()
        if polygons is not None:
            pm.select(polygons)
        jnts = self.query.line.text().split(",")
        ADPoses.auto_apply(jnts)
        self.list.reload()

    @staticmethod
    def esc():
        ADPoses.auto_edit(False)

    def get_polygons(self):
        polygons = pm.ls(self.polygons.line.text().split(","), type="transform")
        polygons = [poly for poly in polygons if bs.is_polygon(poly)]
        if not len(polygons):
            polygons = None
        return polygons

    def mirror(self, targets):
        ADPoses.mirror_by_targets(targets)
        self.list.reload()
