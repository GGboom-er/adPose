# coding=utf-8
from . import ADPose
from .general_ui import *


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

    def paintEvent(self, event):
        QWidget.paintEvent(self, event)
        painter = QPainter(self)

        # background
        painter.setBrush(QBrush(QColor(120, 120, 120), Qt.SolidPattern))
        painter.setPen(QPen(QColor(0, 0, 0), 1, Qt.SolidLine))
        painter.drawRect(0, 0, self.width(), self.height())

        # grid
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DotLine))
        for i in range(5):
            w = self.scale * 45 * i
            painter.drawLine(w, 0, w, self.height())
        for i in range(9):
            h = self.scale * 45 * i
            painter.drawLine(0, h, self.width(), h)

        # control
        painter.setPen(QPen(QColor(60, 60, 60), 1, Qt.SolidLine))
        painter.drawLine(self.__control[0] * self.scale, 0, self.__control[0] * self.scale, self.height())
        painter.drawLine(0, self.__control[1] * self.scale, self.width(), self.__control[1] * self.scale)

        # control line
        painter.setPen(QPen(QColor(60, 180, 60), 1, Qt.SolidLine))
        if self.__control_x is not None:
            painter.drawLine(self.__control[0] * self.scale, 0, self.__control[0] * self.scale, self.height())
        if self.__control_y is not None:
            painter.drawLine(0, self.__control[1] * self.scale, self.width(), self.__control[1] * self.scale)

        # poses
        painter.setPen(QPen(QColor(219, 148, 86), 0, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(219, 148, 86), Qt.SolidPattern))
        for p in self.__poses:
            painter.drawEllipse(QPoint(p[0]*self.scale, p[1]*self.scale), 2, 2)
            painter.drawEllipse(QPoint(p[0]*self.scale, p[1]*self.scale), 2, 2)

        # edit pose
        painter.setPen(QPen(QColor(225, 0, 0), 0, Qt.SolidLine))
        painter.setBrush(QBrush(QColor(225, 0, 0), Qt.SolidPattern))
        if self.__control in self.__poses:
            painter.drawEllipse(QPoint(self.__control[0] * self.scale, self.__control[1] * self.scale), 2, 2)
            painter.drawEllipse(QPoint(self.__control[0] * self.scale, self.__control[1] * self.scale), 2, 2)
        painter.end()

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
            x, y = max(0, min(x, 180)), max(0, min(y, 360))
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

    def keyReleaseEvent(self, event):
        QWidget.keyReleaseEvent(self, event)
        self.__adsorb = False
        self.__grid = False

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
    button_text = u"添加/修改"

    def __init__(self):
        Tool.__init__(self)
        self.joint = MayaObjLayout(u"骨骼:", 40)
        self.kwargs_layout.addLayout(self.joint)
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
        self.joint.textChanged.connect(self.load)

    def set_control(self, pose):
        if not isinstance(self.pose, ADPose.ADPoses):
            return
        self.pose.set_pose(pose)
        pm.refresh()

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
        if not isinstance(self.pose, ADPose.ADPoses):
            return
        pose = self.pose.edit_by_selected_ctrl_pose()
        if not pose:
            return
        self.reload()



