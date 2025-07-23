# coding:utf-8
from .general_ui import *
from .ADPose import ADPoses
from . import bs
from . import joints
from . import twist
import re


def is_twist(target):
    match = re.match(r"^(?P<joint>\w+)_twistX_(plus|minus)[0-9]{1,3}$", target)
    return bool(match)


def is_swing(target):
    match = re.match("(.+)_a([0-9]{1,3})_d([0-9]{1,3})", target)
    return bool(match)


class TargetList(QListWidget):
    mirrorTargets = Signal(list)

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.text = ""
        self.swing = True
        self.twist = True
        self.setSelectionMode(self.ExtendedSelection)
        self.menu = QMenu(self)
        add_menu = self.menu.addMenu(u"添加")
        add_menu.addAction(u"swing", self.add_swing)
        add_menu.addAction(u"twist", self.add_twist)
        self.menu.addAction(u"修改", self.edit_target)
        self.menu.addAction(u"镜像", self.mirror_targets)
        self.menu.addAction(u"传递", self.wrap_copy_targets)
        self.menu.addAction(u"删除", self.delete_targets)

        self.itemDoubleClicked.connect(self.set_pose)

    def add_swing(self):
        ADPoses.auto_add_target(self.text.split(","))
        self.reload()

    def add_twist(self):
        twist.add_target(self.text)
        self.reload()

    def selected_targets(self):
        return [item.text() for item in self.selectedItems()]

    def update_swing(self, swing):
        self.swing = swing
        self.reload()

    def update_twist(self, _twist):
        self.twist = _twist
        self.reload()

    def reload(self):
        self.clear()
        if self.swing:
            self.addItems(ADPoses.get_targets())
        if self.twist:
            self.addItems(twist.get_targets())
        self.query()

    def contextMenuEvent(self, event):
        self.menu.exec_(event.globalPos())

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

    def update_query(self, text):
        self.text = text
        self.query()

    def current_target(self):
        targets = self.selected_targets()
        if len(targets) != 1:
            return pm.warning("please selected only one target")
        return targets[0]

    def set_pose(self):
        target_name = self.current_target()
        if not target_name:
            return
        if is_swing(target_name):
            ADPoses.set_pose_by_targets([target for target in self.selected_targets() if is_swing(target)])
        elif is_twist(target_name):
            ADPoses.all_to_zero()
            twist.to_target(self.current_target(), 60)

    def edit_target(self):
        target_name = self.current_target()
        if not target_name:
            return
        if is_swing(target_name):
            ADPoses.set_pose_by_targets([target_name])
            ADPoses.auto_edit_by_selected_target(self.text.split(","))
        elif is_twist(target_name):
            twist.edit_target(self.current_target())

    def get_group_targets(self):
        targets = self.selected_targets()
        swings = list(filter(is_swing, targets))
        twists = list(filter(is_twist, targets))
        return swings, twists

    def wrap_copy_targets(self):
        swings, twists = self.get_group_targets()
        selected = pm.selected()
        bs.tool_part_warp_copy(ADPoses.warp_copy_targets)(swings)
        pm.select(selected)
        bs.tool_part_warp_copy(twist.wrap_copy_targets_twist)(twists)

    def mirror_targets(self):
        swings, twists = self.get_group_targets()
        ADPoses.mirror_by_targets(swings)
        twist.mirror_targets(twists)
        self.reload()

    def delete_targets(self):
        swings, twists = self.get_group_targets()
        ADPoses.delete_by_targets(swings)
        twist.del_targets(twists)
        self.reload()


class MainEditTool(Tool):
    button_text = u"复制/修改"

    def __init__(self, parent=None):
        Tool.__init__(self, parent)
        self.query = MayaObjLayouts(u"搜索：", 40)
        self.query.line.setReadOnly(False)
        self.slider = TargetSlider()
        self.list = TargetList(self)
        self.kwargs_layout.addLayout(self.slider)
        self.kwargs_layout.addLayout(self.query)

        self.swing = QCheckBox()
        self.twist = QCheckBox()
        swing_layout = QHBoxLayout()
        swing_layout.addLayout(PrefixWeight(u"swing:", self.swing, 40))
        swing_layout.addLayout(PrefixWeight(u"twist:", self.twist, 40))
        # swing_layout.addStretch()
        self.kwargs_layout.addLayout(swing_layout)

        self.kwargs_layout.addWidget(self.list)
        self.query.line.textChanged.connect(self.list.update_query)
        self.query.button.clicked.connect(self.list.reload)
        self.slider.slider.valueChanged.connect(self.set_ib_pose_by_targets)
        self.slider.button.clicked.connect(self.esc)
        self.twist.setChecked(True)
        self.swing.setChecked(True)
        self.twist.stateChanged.connect(self.list.update_twist)
        self.swing.stateChanged.connect(self.list.update_swing)

    def apply(self):
        target_name = self.list.current_target()
        if not target_name:
            return
        if is_swing(target_name):
            ADPoses.set_pose_by_targets([target_name])
            ADPoses.auto_apply(self.list.text.split(","))
        elif is_twist(target_name):
            twist.auto_apply(target_name)

    def set_ib_pose_by_targets(self, value):
        target_name = self.list.current_target()
        if not target_name:
            return
        if is_swing(target_name):
            swings = [target for target in self.list.selected_targets() if is_swing(target)]
            ADPoses.set_pose_by_targets(swings, [], value)
        elif is_twist(target_name):
            ADPoses.all_to_zero()
            twist.to_target(self.list.current_target(), value)
        pm.refresh()

    def esc(self):
        ADPoses.auto_edit(False)
        twist.auto_edit()
        self.set_ib_pose_by_targets(0)
        ADPoses.all_to_zero()
