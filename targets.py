# coding:utf-8
"""
目标编辑工具模块
已从 pymel 迁移到 maya.cmds
"""
from .general_ui import *
from .ADPose import ADPoses
from . import bs
from maya import cmds


class TargetList(QListWidget):
    """目标列表控件"""
    mirrorTargets = Signal(list)

    def __init__(self, parent=None):
        QListWidget.__init__(self, parent)
        self.setSelectionMode(ExtendedSelection)
        self.menu = QMenu(self)
        self.menu.addAction(u"新建 target（自动创建）", self.new_target)
        self.menu.addAction(u"编辑 target", self.auto_edit_by_selected_target)
        self.menu.addAction(u"Pin变形驱动（编辑骨骼Pin平面）", self.joint_driver)
        self.menu.addAction(u"删除", self.delete_targets)
        self.menu.addAction(u"镜像到对侧（L↔R）", self.mirror_targets)
        self.menu.addAction(u"复制翻转X写入", self.copy_flip_targets)
        self.menu.addAction(u"传递到其他网格", self.warp_copy_targets)
        self.itemDoubleClicked.connect(self.set_pose)
        self.text = ""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(100)
        self._refresh_timer.timeout.connect(self._do_update_weights)
        self.destroyed.connect(lambda *args: self._stop_refresh())
        self.reload()

    def new_target(self):
        """新建 target：先创建不存在的 pose，再进入编辑"""
        selected = cmds.ls(sl=1)
        ADPoses.auto_insert_pose(self.text.split(","))
        cmds.select(cmds.ls(selected))
        ADPoses.auto_edit_by_selected_target(self.text.split(","))
        self.reload()

    def auto_edit_by_selected_target(self):
        """编辑已有 target（不自动创建）"""
        ADPoses.auto_edit_by_selected_target(self.text.split(","))
        self.reload()

    def joint_driver(self):
        from . import joints
        joints.tool_edit_target(lambda: ADPoses.auto_edit_by_selected_target(self.text.split(",")))
        self.reload()

    def set_pose(self):
        ADPoses.set_pose_by_targets(self.selected_targets())

    def mirror_targets(self):
        self.mirrorTargets.emit(self.selected_targets())

    def copy_flip_targets(self):
        """复制翻转X：选中两个 target，把第一个的顶点数据 X 翻转写入第二个"""
        targets = self.selected_targets()
        if len(targets) != 2:
            cmds.warning(u"需要选中 2 个 target：源 和 目标")
            return
        bs.custom_mirror(targets)
        self.reload()

    def delete_targets(self):
        targets = self.selected_targets()
        if not targets:
            return
        reply = QMessageBox.question(
            self, u"确认删除",
            u"将删除 %d 个目标:\n%s\n\n此操作不可撤销！" % (len(targets), '\n'.join(targets)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        ADPoses.delete_by_targets(targets)
        self.reload()

    def selected_targets(self):
        return [item.data(Qt.UserRole) or item.text() for item in self.selectedItems()]

    def warp_copy_targets(self):
        ADPoses.warp_copy_targets(self.selected_targets())

    @staticmethod
    def _weight_color(w):
        """0→红  0.5→黄  1→绿  线性插值"""
        w = max(0.0, min(1.0, w))
        r = int(220 * (1.0 - w) + 80 * w)
        g = int(80 * (1.0 - w) + 220 * w)
        return QColor(r, g, 80)

    @staticmethod
    def _has_pin(target_name):
        """检查 target 对应的骨骼是否已创建 Pin 驱动"""
        import re
        m = re.match(r'(.+)_a\d+_d\d+', target_name)
        if not m:
            return False
        joint_name = m.group(1)
        return cmds.objExists(joint_name + 'Pin')

    def reload(self):
        self.blockSignals(True)
        self.clear()
        all_targets = ADPoses.get_targets()
        weights = ADPoses.get_target_driver_values(all_targets)
        for target_name in all_targets:
            w = max(0.0, min(1.0, weights.get(target_name, 0.0)))
            pin_tag = u" [Pin]" if self._has_pin(target_name) else u""

            item = QListWidgetItem()
            item.setData(Qt.UserRole, target_name)
            self.addItem(item)

            # 使用自定义 widget 分离名称和权重
            widget = QWidget()
            # 设置背景透明，让 QListWidget 的蓝色选中背景能透过来
            widget.setStyleSheet("background: transparent;")
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(5, 2, 5, 2)

            name_label = QLabel(target_name)
            font = name_label.font()
            if font.pointSize() > 0:
                font.setPointSize(font.pointSize() + 2)
            elif font.pixelSize() > 0:
                font.setPixelSize(font.pixelSize() + 3)
            else:
                font.setPointSize(11)
            name_label.setFont(font)

            weight_label = QLabel(u"%.2f%s" % (w, pin_tag))
            weight_label.setFont(font)
            weight_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            layout.addWidget(name_label)
            layout.addWidget(weight_label)

            color_str = self._weight_color(w).name()
            # 在 label 上强制指定颜色，解决选中时字体变白导致无法区分状态的问题
            name_label.setStyleSheet("color: %s;" % color_str)
            weight_label.setStyleSheet("color: %s;" % color_str)

            # 保存引用以便高频刷新时快速更新
            widget.name_label = name_label
            widget.weight_label = weight_label
            widget.pin_tag = pin_tag

            item.setSizeHint(widget.sizeHint())
            self.setItemWidget(item, widget)

        self.blockSignals(False)
        self.query()
        self._start_refresh()

    def _do_update_weights(self):
        try:
            import shiboken6 as shiboken
        except ImportError:
            try:
                import shiboken2 as shiboken
            except ImportError:
                import shiboken
        try:
            if not shiboken.isValid(self): return
        except Exception:
            pass
        if self.count() == 0:
            return
        names = []
        for i in range(self.count()):
            names.append(self.item(i).data(Qt.UserRole) or '')
        weights = ADPoses.get_target_driver_values(names)
        self.blockSignals(True)
        for i in range(self.count()):
            item = self.item(i)
            name = names[i]
            w = max(0.0, min(1.0, weights.get(name, 0.0)))

            widget = self.itemWidget(item)
            if widget:
                color_str = self._weight_color(w).name()
                widget.name_label.setStyleSheet("color: %s;" % color_str)
                widget.weight_label.setStyleSheet("color: %s;" % color_str)
                widget.weight_label.setText(u"%.2f%s" % (w, widget.pin_tag))
        self.blockSignals(False)

    def _start_refresh(self):
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()

    def _stop_refresh(self):
        self._refresh_timer.stop()

    def close(self):
        self._stop_refresh()
        super(TargetList, self).close()

    def query(self):
        if self.text:
            for i in range(self.count()):
                item = self.item(i)
                target_name = item.data(Qt.UserRole) or item.text()
                if any([field in target_name for field in self.text.split(",")]):
                    item.setHidden(False)
                else:
                    item.setHidden(True)
        else:
            for i in range(self.count()):
                self.item(i).setHidden(False)

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
        return [self.item(i).data(Qt.UserRole) or self.item(i).text() for i in range(self.count())]


class TargetEditTool(Tool):
    """目标编辑工具"""
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
        self.query.objChanged.connect(self.list.load_objs)
        self.query.line.textChanged.connect(self.list.set_text)
        self.list.mirrorTargets.connect(self.mirror)
        self.slider.slider.valueChanged.connect(self.set_ib_pose_by_targets)
        self.slider.button.clicked.connect(self.esc)
        # ★ 选中 item 时自动同步滑栏到当前权重值
        self.list.itemSelectionChanged.connect(self._sync_slider)

    def _sync_slider(self):
        """读取选中 target 的真实驱动值，静默同步到滑栏。"""
        targets = self.list.selected_targets()
        if not targets:
            return
        target = targets[0]
        weight = ADPoses.get_target_driver_values([target])[target]
        slider_val = int(round(weight * 60))
        slider_val = max(0, min(60, slider_val))
        self.slider.slider.blockSignals(True)
        self.slider.box.blockSignals(True)
        self.slider.slider.setValue(slider_val)
        self.slider.box.setValue(slider_val)
        self.slider.box.blockSignals(False)
        self.slider.slider.blockSignals(False)

    def set_ib_pose_by_targets(self, value):
        ADPoses.set_pose_by_targets(self.list.selected_targets(), [], value)
        cmds.refresh()

    def apply(self):
        if bs.is_on_duplicate_edit():
            bs.finish_duplicate_edit(lambda x: ADPoses.set_pose_by_targets([x]))
            self._update_button_state()
            self.list.reload()
            return

        polygons = self.get_polygons()
        if polygons is not None:
            cmds.select(polygons)

        text = self.query.line.text().strip()
        jnts = text.split(",") if text else []

        # ★ 如果搜索框没填，但列表里选中了目标，优先直接使用选中的目标
        if not jnts:
            selected = self.list.selected_targets()
            if selected:
                target_name = selected[0]

                if bs.is_on_duplicate_edit():
                    bs.finish_duplicate_edit(lambda x: ADPoses.set_pose_by_targets([x]))
                else:
                    def add_target(_target_name):
                        return ADPoses.add_by_target(_target_name)

                    def set_target(_target_name):
                        ADPoses.set_pose_by_targets([_target_name], all_targets=[])

                    bs.auto_duplicate_edit([target_name], add_target, set_target)

                self._update_button_state()
                self.list.reload()
                return

        ADPoses.auto_apply(jnts)
        self._update_button_state()
        self.list.reload()

    def _update_button_state(self):
        """★ 根据场景状态切换按钮外观"""
        if not hasattr(self, '_cancel_connected'):
            self._cancel_connected = False
        if bs.is_on_duplicate_edit():
            target_name = bs.get_editing_target_name() or "?"
            self.button.setText(u"结束修改: %s" % target_name)
            self.button.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold;")
            self.button.setContextMenuPolicy(Qt.CustomContextMenu)
            if not self._cancel_connected:
                self.button.customContextMenuRequested.connect(self._show_cancel_menu)
                self._cancel_connected = True
        else:
            self.button.setText(u"复制/修改")
            self.button.setStyleSheet("")
            self.button.setContextMenuPolicy(Qt.DefaultContextMenu)
            if self._cancel_connected:
                self.button.customContextMenuRequested.disconnect(self._show_cancel_menu)
                self._cancel_connected = False

    def _show_cancel_menu(self, pos):
        """★ 右键菜单：放弃当前修改"""
        target_name = bs.get_editing_target_name() or "?"
        menu = QMenu(self.button)
        menu.addAction(u"放弃 %s 的修改" % target_name, self._cancel_edit)
        menu.exec_(self.button.mapToGlobal(pos))

    def _cancel_edit(self):
        """★ 放弃编辑，不写入任何修改"""
        bs.cancel_duplicate_edit()
        self._update_button_state()
        self.list.reload()

    def showNormal(self):
        """窗口显示时同步按钮状态并启动实时刷新。"""
        QDialog.showNormal(self)
        self._update_button_state()
        self.show_update()
        self.list.reload()

    def closeEvent(self, event):
        """窗口关闭时停止实时刷新。"""
        self.list._stop_refresh()
        super(TargetEditTool, self).closeEvent(event)

    @staticmethod
    def esc():
        ADPoses.esc()

    def get_polygons(self):
        """获取多边形列表"""
        polygon_names = self.polygons.line.text().split(",")
        polygons = cmds.ls(polygon_names, type="transform") or []
        polygons = [poly for poly in polygons if bs.is_polygon(poly)]
        if not len(polygons):
            polygons = None
        return polygons

    def mirror(self, targets):
        ADPoses.mirror_by_targets(targets)
        self.list.reload()
