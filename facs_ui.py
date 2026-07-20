# coding:utf-8
from .general_ui import *
from . import facs
from functools import partial
from maya import cmds

class TargetList(QListWidget):

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionMode(ExtendedSelection)
        self.menu = QMenu(self)
        self.menu.addAction(u"添加/修改", self.add_edit_target)
        self.menu.addAction(u"删除", self.delete_targets)
        self.menu.addAction(u"镜像", self.mirror_target)
        self.menu.addAction(u"传递", partial(self.warp, False))
        self.itemDoubleClicked.connect(self.set_pose)
        self.text = u""

    def set_pose(self):
        facs.all_to_zero()
        facs.to_targets(self.selected_targets())

    def selected_targets(self):
        return [item.text() for item in self.selectedItems()]

    def contextMenuEvent(self, event):
        self.menu.exec_(event.globalPos())

    def reload(self):
        self.clear()
        self.addItems(facs.get_targets())
        self.query()

    def add_edit_target(self):
        facs.auto_add_edit_target(self.text.split(","))
        self.reload()


    def delete_targets(self):
        facs.delete_targets(self.selected_targets())
        self.reload()

    def mirror_target(self):
        facs.mirror_targets(self.selected_targets())
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

    def setItemHidden(self, item, hidden):
        if not hasattr(QListWidget, "setItemHidden"):
            item.setHidden(hidden)
        else:
            QListWidget.setItemHidden(self, item, hidden)

    def set_text(self, text):
        self.text = text
        self.query()

    def update_objs(self, text):
        self.set_text(text)
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
        self.query.objChanged.connect(self.list.update_objs)
        self.slider.button.clicked.connect(self.esc)

    def set_ib_pose_by_targets(self, value):
        facs.to_targets(self.list.selected_targets(), value)

    def apply(self):
        text = self.query.line.text().strip()
        jnts = text.split(",") if text else []

        if not jnts:
            selected = self.list.selected_targets()
            if selected:
                target_name = selected[0]
                if facs.bs.is_on_duplicate_edit():
                    facs.bs.finish_duplicate_edit(lambda x: facs.to_targets([x]))
                else:
                    def _add_target(_target_name):
                        bridge = facs.get_bridge()
                        facs.auto_add_target(facs.find_add_sdk_data(facs.get_real_ctrls([])), target_name, "base")
                        return bridge + "." + _target_name
                    def _set_target(_target_name):
                        if not facs.target_is_base(_target_name):
                            facs.to_targets([_target_name])
                    facs.bs.auto_duplicate_edit([target_name], _add_target, _set_target)
                self._update_button_state()
                self.list.reload()
                return

        facs.auto_apply(jnts)
        self._update_button_state()
        self.list.reload()

    def _update_button_state(self):
        """★ 根据场景状态切换按钮外观"""
        if facs.bs.is_on_duplicate_edit():
            target_name = facs.bs.get_editing_target_name() or "?"
            self.button.setText(u"结束修改: %s" % target_name)
            self.button.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold;")
            self.button.setContextMenuPolicy(Qt.CustomContextMenu)
            try:
                self.button.customContextMenuRequested.disconnect(self._show_cancel_menu)
            except (RuntimeError, TypeError):
                pass
            self.button.customContextMenuRequested.connect(self._show_cancel_menu)
        else:
            self.button.setText(u"面部驱动")
            self.button.setStyleSheet("")
            self.button.setContextMenuPolicy(Qt.DefaultContextMenu)
            try:
                self.button.customContextMenuRequested.disconnect(self._show_cancel_menu)
            except (RuntimeError, TypeError):
                pass

    def _show_cancel_menu(self, pos):
        target_name = facs.bs.get_editing_target_name() or "?"
        menu = QMenu(self.button)
        menu.addAction(u"放弃 %s 的修改" % target_name, self._cancel_edit)
        menu.exec_(self.button.mapToGlobal(pos))

    def _cancel_edit(self):
        facs.bs.cancel_duplicate_edit()
        self._update_button_state()
        self.list.reload()

    def showNormal(self):
        QDialog.showNormal(self)
        self._update_button_state()

    @staticmethod
    def esc():
        facs.esc()



window = None


def show():
    global window
    if window is None:
        window = FaceTargetEditTool()
    window.show()
    window._update_button_state()
    window.list.reload()
