# coding:utf-8
from .general_ui import *
from . import twist


class TargetList(QListWidget):
    addTarget = Signal()

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionMode(ExtendedSelection)
        self.menu = QMenu(self)
        self.menu.addAction(u"添加/修改", self.add_edit_target)
        self.menu.addAction(u"骨骼驱动", self.joint_driver)
        self.menu.addAction(u"删除", self.delete_targets)
        self.menu.addAction(u"镜像", self.mirror_targets)
        self.menu.addAction(u"传递", self.wrap_copy)
        self.itemDoubleClicked.connect(self.to_pose)
        self.text = ""

    def add_edit_target(self):
        selected = cmds.ls(sl=1)
        twist.auto_insert_pose(self.text)
        cmds.select(cmds.ls(selected))
        twist.add_edit_target(self.text)
        self.reload()

    def joint_driver(self):
        from . import joints
        joints.tool_edit_target(lambda: twist.add_edit_target(self.text))
        self.reload()

    def to_pose(self):
        twist.all_to_zero()
        twist.to_target(self.current_target(), 60)

    def selected_targets(self):
        return [item.text() for item in self.selectedItems()]

    def current_target(self):
        from maya import cmds
        targets = self.selected_targets()
        if len(targets) != 1:
            return cmds.warning("please selected only one target")
        return targets[0]

    def contextMenuEvent(self, event):
        self.menu.exec_(event.globalPos())

    def reload(self):
        self.clear()
        self.addItems(twist.get_targets())
        self.query(self.text)

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

    def setItemHidden(self, item, hidden):
        if not hasattr(QListWidget, "setItemHidden"):
            item.setHidden(hidden)
        else:
            QListWidget.setItemHidden(self, item, hidden)


    def wrap_copy(self):
        twist.wrap_copy_targets_twist(self.selected_targets())

    def load_objs(self, text):
        self.text = text
        self.reload()
        self.query(text)


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
        self.query.line.textChanged.connect(self.list.query)
        self.query.objChanged.connect(self.list.load_objs)
        self.list.addTarget.connect(self.add_target)
        self.slider.button.clicked.connect(self.esc)

    def add_target(self):
        twist.add_edit_target(self.query.line.text())
        self.list.reload()

    def set_ib_pose_by_targets(self, value):
        twist.to_target(self.list.current_target(), value)
        cmds.refresh()

    def apply(self):
        text = self.query.line.text().strip()

        if not text:
            selected = self.list.selected_targets()
            if selected:
                target_name = selected[0]
                if twist.bs.is_on_duplicate_edit():
                    twist.bs.finish_duplicate_edit(twist.to_target)
                else:
                    def _add_target(_target_name):
                        t = twist.get_twist([])
                        return t.add_current_target() if t else None
                    def _set_target(_target_name):
                        pass
                    twist.bs.auto_duplicate_edit([target_name], _add_target, _set_target)
                self._update_button_state()
                self.list.reload()
                return

        twist.auto_apply(text)
        self._update_button_state()
        self.list.reload()

    def _update_button_state(self):
        """★ 根据场景状态切换按钮外观"""
        if twist.bs.is_on_duplicate_edit():
            target_name = twist.bs.get_editing_target_name() or "?"
            self.button.setText(u"结束修改: %s" % target_name)
            self.button.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold;")
            self.button.setContextMenuPolicy(Qt.CustomContextMenu)
            try:
                self.button.customContextMenuRequested.disconnect(self._show_cancel_menu)
            except (RuntimeError, TypeError):
                pass
            self.button.customContextMenuRequested.connect(self._show_cancel_menu)
        else:
            self.button.setText(u"修形")
            self.button.setStyleSheet("")
            self.button.setContextMenuPolicy(Qt.DefaultContextMenu)
            try:
                self.button.customContextMenuRequested.disconnect(self._show_cancel_menu)
            except (RuntimeError, TypeError):
                pass

    def _show_cancel_menu(self, pos):
        target_name = twist.bs.get_editing_target_name() or "?"
        menu = QMenu(self.button)
        menu.addAction(u"放弃 %s 的修改" % target_name, self._cancel_edit)
        menu.exec_(self.button.mapToGlobal(pos))

    def _cancel_edit(self):
        twist.bs.cancel_duplicate_edit()
        self._update_button_state()
        self.list.reload()

    def showNormal(self):
        QDialog.showNormal(self)
        self._update_button_state()

    def esc(self):
        twist.esc()



window = None


def show():
    global window
    if window is None:
        window = TwistTargetEditTool(get_host_app())
    window.show()
    window._update_button_state()
    window.list.reload()