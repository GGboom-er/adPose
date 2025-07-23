# coding:utf-8
from .general_ui import *
from . import twist


class TargetList(QListWidget):
    addTarget = Signal()

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionMode(self.ExtendedSelection)
        self.menu = QMenu(self)
        self.menu.addAction(u"修改", self.edit_target)
        self.menu.addAction(u"添加", self.addTarget.emit)
        self.menu.addAction(u"删除", self.delete_targets)
        self.menu.addAction(u"镜像", self.mirror_targets)
        self.menu.addAction(u"刷新", self.reload)
        self.menu.addAction(u"传递", self.wrap_copy)
        self.menu.addAction(u"刚性烘焙", self.rigid_bs)
        self.menu.addAction(u"自定义镜像", self.custom_mirror)
        self.itemDoubleClicked.connect(self.to_pose)
        self.text = ""

    def rigid_bs(self):
        from .. import rigid_bs
        rigid_bs.tool_bake_twist(self.selected_targets())

    def custom_mirror(self):
        twist.custom_mirror(self.selected_targets())
        self.reload()

    def to_pose(self):
        twist.to_target(self.current_target(), 60)

    def selected_targets(self):
        return [item.text() for item in self.selectedItems()]

    def current_target(self):
        targets = self.selected_targets()
        if len(targets) != 1:
            return pm.warning("please selected only one target")
        return targets[0]

    def contextMenuEvent(self, event):
        self.menu.exec_(event.globalPos())

    def reload(self):
        self.clear()
        self.addItems(twist.get_targets())
        self.query(self.text)

    def edit_target(self):
        twist.edit_target(self.current_target())

    def delete_targets(self):
        twist.del_targets(self.selected_targets())
        self.reload()

    def mirror_targets(self):
        twist.mirror_targets(self.selected_targets())
        self.reload()

    def query(self, text):
        self.text = text
        if not text:
            for i in range(self.count()):
                item = self.item(i)
                self.setItemHidden(item, False)
            return
        for i in range(self.count()):
            item = self.item(i)
            if any([field in item.text() for field in text.split(",")]):
                self.setItemHidden(item, False)
            else:
                self.setItemHidden(item, True)
                
    def wrap_copy(self):
        twist.wrap_copy_targets_twist(self.selected_targets())


class TwistTargetEditTool(Tool):
    button_text = u"修形"

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
        self.query.textChanged.connect(self.list.query)
        self.list.addTarget.connect(self.add_target)

    def add_target(self):
        twist.add_target(self.query.line.text())
        self.list.reload()

    def set_ib_pose_by_targets(self, value):
        twist.to_target(self.list.current_target(), value)
        pm.refresh()

    def apply(self):
        twist.auto_apply(self.list.current_target())


window = None


def show():
    global window
    if window is None:
        window = TwistTargetEditTool(get_host_app())
    window.show()
    window.list.reload()