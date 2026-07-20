# coding=utf-8
"""
UV 姿势网格工具模块
已从 pymel 迁移到 maya.cmds
"""
from . import ADPose
from .general_ui import *
from . import bs
from maya import cmds


class QGrid(QWidget):
    ControlMode, XMode, YMode, MoveMode = range(4)
    controlChanged = Signal(list)
    posesChanged = Signal(list)
    editChanged = Signal(list)
    XChanged = Signal(int)
    YChanged = Signal(int)

    def __init__(self):
        QWidget.__init__(self)
        self.mode = self.MoveMode
        self.setMouseTracking(True)
        self.scale = 2
        self.setFixedSize(QSize(180*self.scale+1, 360*self.scale+1))
        self.__poses = []
        self.__control = [90, 180]
        self.__edit = None
        self.__control_x = None
        self.__control_y = None
        self.__adsorb = False
        self.__grid = False
        self.__shift = False  # ★ Shift 精细模式
        self.step_size = 10   # ★ 默认步长 10 度

    def paintEvent(self, event):
        QWidget.paintEvent(self, event)
        painter = QPainter(self)

        # background
        painter.setBrush(QBrush(QColor(80, 80, 80), Qt.SolidPattern))
        painter.setPen(QPen(QColor(50, 50, 50), 1, Qt.SolidLine))
        painter.drawRect(0, 0, self.width(), self.height())

        # ★ 主网格线（45度分割）- 加粗为 2px
        painter.setPen(QPen(QColor(110, 110, 110), 2, Qt.DotLine))
        for i in range(5):
            w = self.scale * 45 * i
            painter.drawLine(w, 0, w, self.height())
        for i in range(9):
            h = self.scale * 45 * i
            painter.drawLine(0, h, self.width(), h)

        # ★ 步长细分网格（如果步长 < 45）
        if self.step_size < 45:
            painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DotLine))
            for i in range(0, 181, self.step_size):
                w = self.scale * i
                if i % 45 != 0:  # 不覆盖主网格
                    painter.drawLine(w, 0, w, self.height())
            for i in range(0, 361, self.step_size):
                h = self.scale * i
                if i % 45 != 0:
                    painter.drawLine(0, h, self.width(), h)

        # ★ 控制十字线 - 加粗为 3px
        painter.setPen(QPen(QColor(60, 60, 60), 3, Qt.SolidLine))
        painter.drawLine(self.__control[0] * self.scale, 0, self.__control[0] * self.scale, self.height())
        painter.drawLine(0, self.__control[1] * self.scale, self.width(), self.__control[1] * self.scale)

        # control line highlight (when hovering axis)
        painter.setPen(QPen(QColor(60, 200, 60), 3, Qt.SolidLine))
        if self.__control_x is not None:
            painter.drawLine(self.__control[0] * self.scale, 0, self.__control[0] * self.scale, self.height())
        if self.__control_y is not None:
            painter.drawLine(0, self.__control[1] * self.scale, self.width(), self.__control[1] * self.scale)

        # ★ Pose 点 - 放大为 6px
        painter.setPen(QPen(QColor(219, 148, 86), 0, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(219, 148, 86), Qt.SolidPattern))
        for p in self.__poses:
            painter.drawEllipse(QPoint(p[0]*self.scale, p[1]*self.scale), 6, 6)

        # ★ 当前选中的 Pose 点 - 红色 + 外圈光晕
        if self.__control in self.__poses:
            # 外圈光晕
            painter.setPen(QPen(QColor(255, 80, 80, 100), 2, Qt.SolidLine))
            painter.setBrush(QBrush(QColor(255, 80, 80, 60), Qt.SolidPattern))
            painter.drawEllipse(QPoint(self.__control[0] * self.scale, self.__control[1] * self.scale), 12, 12)
            # 实心红点
            painter.setPen(QPen(QColor(225, 0, 0), 0, Qt.SolidLine))
            painter.setBrush(QBrush(QColor(225, 0, 0), Qt.SolidPattern))
            painter.drawEllipse(QPoint(self.__control[0] * self.scale, self.__control[1] * self.scale), 6, 6)

        # ★ 当前坐标文字提示
        painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.SolidLine))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(5, 15, u"angle: %d  dir: %d" % (self.__control[0], self.__control[1]))
        if self.__shift:
            painter.drawText(5, 30, u"[精细模式]")
        elif self.__grid:
            painter.drawText(5, 30, u"[X:45°吸附]")
        elif self.__adsorb:
            painter.drawText(5, 30, u"[V:Pose吸附]")

        painter.end()

    def _snap_to_step(self, x, y):
        """★ 按步长 snap 坐标（Shift 时步长为 1）"""
        step = 1 if self.__shift else max(1, self.step_size)
        x = int(round(float(x) / step)) * step
        y = int(round(float(y) / step)) * step
        return max(0, min(x, 180)), max(0, min(y, 360))

    def mousePressEvent(self, event):
        self.setFocus()
        if self.__control_x is not None:
            self.mode = self.XMode
            return
        elif self.__control_y is not None:
            self.mode = self.YMode
            return
        else:
            self.mode = self.ControlMode
            pos = event.pos()
            x, y = int(round(float(pos.x()) / self.scale)), int(round(float(pos.y()) / self.scale))
            x, y = self._snap_to_step(x, y)
            self.set_control([x, y])
            self.update()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        x, y = int(round(float(pos.x()) / self.scale)), int(round(float(pos.y()) / self.scale))
        x, y = max(0, min(x, 180)), max(0, min(y, 360))
        pose = [x, y]
        if self.__grid:
            x = int(round(float(x) / 45)) * 45
            y = int(round(float(y) / 45)) * 45
            pose = [x, y]
        elif not self.__shift:
            # ★ 默认按步长吸附
            x, y = self._snap_to_step(x, y)
            pose = [x, y]
        if self.__adsorb and self.__poses:
            distance_pose = {((pose[0]-p[0])**2 + (pose[1]-p[1])**2)**0.5: p for p in self.__poses}
            pose = distance_pose[min(distance_pose.keys())]
            x, y = pose
        if self.mode == self.MoveMode:
            # edit point
            if pose in self.__poses:
                self.__edit = pose
                return self.update()
            else:
                self.__edit = None
            # control
            if x == self.__control[0] and y != self.__control[1]:
                self.__control_x = x
            else:
                self.__control_x = None
            if x != self.__control[0] and y == self.__control[1]:
                self.__control_y = y
            else:
                self.__control_y = None
        elif self.mode == self.YMode:
            self.__control_y = y
            self.set_y(y)
        elif self.mode == self.XMode:
            self.__control_x = x
            self.set_x(x)
        elif self.mode == self.ControlMode:
            self.set_control(list(pose))
        self.update()

    def mouseReleaseEvent(self, event):
        self.mode = self.MoveMode

    def keyPressEvent(self, event):
        QWidget.keyPressEvent(self, event)
        if event.key() == Qt.Key_V:
            self.__adsorb = True
        elif event.key() == Qt.Key_X:
            self.__grid = True
        elif event.key() == Qt.Key_Shift:
            self.__shift = True
        self.update()

    def keyReleaseEvent(self, event):
        QWidget.keyReleaseEvent(self, event)
        self.__adsorb = False
        self.__grid = False
        self.__shift = False
        self.update()

    def set_x(self, x):
        if self.__control[0] == x:
            return
        self.__control[0] = x
        self.XChanged.emit(x)
        self.controlChanged.emit(self.__control)
        self.update()

    def set_y(self, y):
        if self.__control[1] == y:
            return
        self.__control[1] = y
        self.YChanged.emit(y)
        self.controlChanged.emit(self.__control)
        self.update()

    def set_control(self, control):
        if self.__control == control:
            return
        x_emit = self.__control[0] != control[0]
        y_emit = self.__control[1] != control[1]
        self.__control = control
        if x_emit:
            self.XChanged.emit(control[0])
        if y_emit:
            self.YChanged.emit(control[1])
        self.__control = control
        self.controlChanged.emit(self.__control)
        if control in self.__poses:
            self.editChanged.emit(control)
        self.update()

    def set_poses(self, poses):
        self.__poses = poses
        self.update()


class UVPoseTool(Tool):
    button_text = u"复制/修改"

    def __init__(self):
        Tool.__init__(self)
        self.joint = MayaObjLayout(u"骨骼:", 40)
        self.kwargs_layout.addLayout(self.joint)

        # ★ 步长控制行
        step_layout = QHBoxLayout()
        step_label = QLabel(u"步长:")
        step_label.setFixedWidth(40)
        step_label.setAlignment(Qt.AlignRight)
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 45)
        self.step_spin.setValue(10)
        self.step_spin.setSuffix(u"°")
        step_layout.addWidget(step_label)
        step_layout.addWidget(self.step_spin)
        # 快捷键提示
        hint = QLabel(u"  V:吸附  X:45°  Shift:精细")
        hint.setStyleSheet("color: #888; font-size: 10px;")
        step_layout.addWidget(hint)
        step_layout.addStretch()
        self.kwargs_layout.addLayout(step_layout)

        line_layout = QHBoxLayout()
        x_line = QSpinBox()
        x_line.setPrefix("angle:")
        x_line.setRange(0, 180)
        y_line = QSpinBox()
        y_line.setPrefix("direction:")
        y_line.setRange(0, 360)
        line_layout.addStretch()
        line_layout.addWidget(x_line)
        line_layout.addStretch()
        line_layout.addWidget(y_line)
        line_layout.addStretch()

        self.kwargs_layout.addLayout(line_layout)
        self.grid = QGrid()
        self.kwargs_layout.addWidget(self.grid)
        self.grid.XChanged.connect(x_line.setValue)
        x_line.valueChanged.connect(self.grid.set_x)
        self.grid.YChanged.connect(y_line.setValue)
        y_line.valueChanged.connect(self.grid.set_y)
        self.grid.controlChanged.connect(self.set_control)
        self.pose = None
        self.joint.objChanged.connect(self.load)
        # ★ 步长同步到网格
        self.step_spin.valueChanged.connect(self._on_step_changed)

    def _on_step_changed(self, value):
        self.grid.step_size = value
        self.grid.update()

    def set_control(self, pose):
        if not isinstance(self.pose, ADPose.ADPoses):
            return
        self.pose.set_pose(pose)
        cmds.refresh()

    def load(self, name):
        if not name:
            return
        self.pose = ADPose.ADPoses.load_by_name(name)
        self.reload()

    def reload(self):
        if self.pose is None:
            return
        self.grid.set_poses([list(p) for p in self.pose.get_poses()])
        self.grid.set_control(list(self.pose.get_control_pose()))
        self.grid.update()

    def apply(self):
        """★ 改为复制/修改工作流（与 List 页签对齐）"""
        if not isinstance(self.pose, ADPose.ADPoses):
            return

        if bs.is_on_duplicate_edit():
            # 第二次点击：结束编辑写回
            bs.finish_duplicate_edit(lambda x: ADPose.ADPoses.set_pose_by_targets([x]))
        else:
            # 第一次点击：进入复制编辑模式
            pose = self.pose.get_control_pose(init=False)
            target_name = self.pose.target_name(pose)

            def add_target(_target_name):
                return self.pose.add_pose(pose)

            def set_target(_target_name):
                ADPose.ADPoses.set_pose_by_targets([_target_name], all_targets=[])

            bs.auto_duplicate_edit([target_name], add_target, set_target)

        self._update_button_state()
        self.reload()

    def _update_button_state(self):
        """★ 按钮状态切换"""
        if bs.is_on_duplicate_edit():
            target_name = bs.get_editing_target_name() or "?"
            self.button.setText(u"结束修改: %s" % target_name)
            self.button.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold;")
            self.button.setContextMenuPolicy(Qt.CustomContextMenu)
            try:
                self.button.customContextMenuRequested.disconnect(self._show_cancel_menu)
            except (RuntimeError, TypeError):
                pass
            self.button.customContextMenuRequested.connect(self._show_cancel_menu)
        else:
            self.button.setText(u"复制/修改")
            self.button.setStyleSheet("")
            self.button.setContextMenuPolicy(Qt.DefaultContextMenu)
            try:
                self.button.customContextMenuRequested.disconnect(self._show_cancel_menu)
            except (RuntimeError, TypeError):
                pass

    def _show_cancel_menu(self, pos):
        target_name = bs.get_editing_target_name() or "?"
        menu = QMenu(self.button)
        menu.addAction(u"放弃 %s 的修改" % target_name, self._cancel_edit)
        # ★ 保留旧的"直接添加"作为高级功能
        menu.addSeparator()
        menu.addAction(u"直接添加（选两个模型）", self._legacy_add)
        menu.exec_(self.button.mapToGlobal(pos))

    def _cancel_edit(self):
        bs.cancel_duplicate_edit()
        self._update_button_state()
        self.reload()

    def _legacy_add(self):
        """旧版添加逻辑：选两个模型直接写入"""
        if not isinstance(self.pose, ADPose.ADPoses):
            return
        pose = self.pose.edit_by_selected_ctrl_pose()
        if not pose:
            return
        self.reload()

    def showNormal(self):
        QDialog.showNormal(self)
        self._update_button_state()
        self.show_update()
