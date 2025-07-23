# coding:utf-8
from .general_ui import *
from . import facs
from functools import partial


class TargetList(QListWidget):

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionMode(self.ExtendedSelection)
        self.menu = QMenu(self)
        self.menu.addAction(u"修改", self.edit_target)
        self.menu.addAction(u"添加", self.add_sdk)
        self.menu.addAction(u"组合", self.add_comb)
        self.menu.addAction(u"插入", self.add_ib)
        self.menu.addAction(u"删除", self.delete_targets)
        self.menu.addAction(u"镜像", self.mirror_target)
        self.menu.addAction(u"自定义镜像", self.custom_mirror)

        self.menu.addAction(u"layer", self.edit_static_target)

        warp_menu = self.menu.addMenu(u"包裹")
        warp_menu.addAction(u"layer", partial(self.warp, True))
        warp_menu.addAction(u"skin", partial(self.warp, False))
        self.itemDoubleClicked.connect(self.set_pose)
        self.text = u""

    def set_pose(self):
        facs.set_pose_by_targets(self.selected_targets())

    def selected_targets(self):
        return [item.text() for item in self.selectedItems()]

    def contextMenuEvent(self, event):
        self.menu.exec_(event.globalPos())

    def reload(self):
        self.clear()
        self.addItems(facs.get_targets())
        self.query()

    def edit_target(self):
        targets = self.selected_targets()
        if len(targets) != 1:
            return pm.warning("please selected only one target")
        facs.edit_target(targets[0])

    def edit_static_target(self):
        targets = self.selected_targets()
        if len(targets) != 1:
            return pm.warning("please selected only one target")
        facs.edit_static_target(targets[0])

    def add_sdk(self):
        facs.add_sdk_by_selected()
        self.reload()

    def add_comb(self):
        facs.add_comb(self.selected_targets())
        self.reload()

    def add_ib(self):
        targets = self.selected_targets()
        if len(targets) != 1:
            return pm.warning("please selected only one target")
        facs.add_ib(targets[0])
        self.reload()

    def delete_targets(self):
        facs.delete_targets(self.selected_targets())
        self.reload()

    def mirror_target(self):
        facs.mirror_targets(self.selected_targets())
        self.reload()

    def custom_mirror(self):
        facs.custom_mirror(self.selected_targets())
        self.reload()

    def query(self):
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
        if self.text:
            self.query()
        else:
            self.reload()

    def warp(self, static):
        facs.warp_copy(self.selected_targets(), static)


class FaceTargetEditTool(Tool):
    button_text = u"面部驱动"

    def __init__(self, parent=None):
        Tool.__init__(self, parent=parent)
        self.query = MayaObjLayouts(u"搜索：", 40)
        self.query.line.setReadOnly(False)
        self.slider = TargetSlider()
        self.list = TargetList(self)
        self.kwargs_layout.addLayout(self.slider)
        self.kwargs_layout.addLayout(self.query)
        self.kwargs_layout.addWidget(self.list)
        self.slider.slider.valueChanged.connect(self.set_ib_pose_by_targets)
        self.query.line.textChanged.connect(self.list.set_text)
        # self.query.line.textChanged.connect(self.list.set_text)

    def set_ib_pose_by_targets(self, value):
        facs.set_pose_by_targets(self.list.selected_targets(), value, False)
        pm.refresh()

    def apply(self):
        targets = self.list.selected_targets()
        if len(targets) != 1:
            return pm.warning("please selected only one target")
        facs.face_sdk(targets[0])



window = None


def show():
    global window
    if window is None:
        window = FaceTargetEditTool()
    window.show()
    window.list.reload()
