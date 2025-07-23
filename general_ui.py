# coding:utf-8
try:
    from PySide.QtGui import *
    from PySide.QtCore import *
except ImportError:
    from PySide2.QtGui import *
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
try:
    import pymel.core as pm
except ImportError:
    pm = None
import json
import os


def get_host_app():
    try:
        main_window = QApplication.activeWindow()
        while True:
            last_win = main_window.parent()
            if last_win:
                main_window = last_win
            else:
                break
        return main_window
    except:
        pass


def button(text, fun):
    but = QPushButton(text)
    but.clicked.connect(fun)
    return but


class PrefixWeight(QHBoxLayout):
    def __init__(self, label, weight, width=60):
        QHBoxLayout.__init__(self)
        prefix = QLabel(label)
        prefix.setFixedWidth(width)
        prefix.setAlignment(Qt.AlignRight)
        self.addWidget(prefix)
        self.addWidget(weight)


class Tool(QDialog):
    title = u"通用应用"
    button_text = u"应用"

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(self.title)
        layout = QVBoxLayout()
        try:
            layout.setMargin(5)
        except AttributeError:
            pass
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        self.kwargs_layout = QVBoxLayout()
        try:
            self.kwargs_layout.setMargin(5)
        except AttributeError:
            pass
        self.kwargs_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.kwargs_layout)
        self.button = button(self.button_text, self.try_apply)
        layout.addWidget(self.button)

    def apply(self):
        pass

    def try_apply(self):
        pm.undoInfo(openChunk=1)
        try:
            self.apply()
        except Exception:
            pm.undoInfo(closeChunk=1)
            raise
        pm.undoInfo(closeChunk=1)

    def showNormal(self):
        QDialog.showNormal(self)
        self.show_update()

    def show_update(self):
        pass


class MayaObjLayout(QHBoxLayout):
    textChanged = Signal(u"".__class__)

    def __init__(self, label, width=60):
        QHBoxLayout.__init__(self)
        prefix = QLabel(label)
        self.addWidget(prefix)
        self.line = QLineEdit()
        self.line.setReadOnly(True)
        self.addWidget(self.line)
        self.button = QPushButton("<<")
        self.addWidget(self.button)
        prefix.setFixedWidth(width)
        prefix.setAlignment(Qt.AlignRight)
        self.button.setFixedWidth(width)
        self.obj = None
        self.button.clicked.connect(self.load_selected)

    def set_obj(self,  obj):
        self.obj = obj
        self.line.setText(obj.name())

    def load_selected(self):
        selected = pm.selected(o=1)
        if len(selected) == 1:
            self.set_obj(selected[0])
        else:
            self.clear()
        self.textChanged.emit(self.line.text())

    def clear(self):
        self.obj = None
        self.line.clear()


class MayaObjLayouts(MayaObjLayout):

    def load_selected(self):
        self.line.setText(",".join([sel.name() for sel in pm.selected()]))
        self.textChanged.emit(self.line.text())


class Number(QSpinBox):

    def __init__(self, _min, _max, _def):
        QSpinBox.__init__(self)
        self.setRange(_min, _max)
        self.setValue(_def)


def layout_adds(lay, *args):
    for arg in args:
        if isinstance(arg, QWidget):
            lay.addWidget(arg)
        else:
            lay.addLayout(arg)
    return lay


def h_layout(*args):
    return layout_adds(QHBoxLayout(), *args)


class TargetSlider(QHBoxLayout):

    def __init__(self):
        QHBoxLayout.__init__(self)
        prefix = QLabel(u"控制：")
        prefix.setFixedWidth(40)
        prefix.setAlignment(Qt.AlignRight)
        self.addWidget(prefix)
        self.slider = QSlider(Qt.Horizontal)
        self.addWidget(self.slider)
        self.slider.setRange(0, 60)
        self.box = QSpinBox()
        self.box.setRange(0, 60)
        self.addWidget(self.box)
        self.slider.valueChanged.connect(self.box.setValue)
        self.box.valueChanged.connect(self.slider.setValue)
        self.button = QPushButton(u">>")
        self.addWidget(self.button)
        self.button.setFixedWidth(40)
        self.setStretch(0, 0)
        self.setStretch(1, 1)
        self.setStretch(2, 0)


class JointList(QVBoxLayout):

    def __init__(self):
        QVBoxLayout.__init__(self)
        self.addLayout(h_layout(button(u"添加骨骼", self.add_joints), button(u"删除骨骼", self.del_joints)))
        self.list = QListWidget()
        self.list.setSelectionMode(self.list.ExtendedSelection)
        self.addWidget(self.list)

    def add_joints(self):
        joints = self.get_joints()
        for joint in pm.ls(sl=1, type="joint"):
            name = joint.name()
            if name in joints:
                continue
            joints.append(name)
        self.list.clear()
        self.list.addItems(joints)

    def del_joints(self):
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.indexFromItem(item).row())

    def get_joints(self):
        return [self.list.item(i).text() for i in range(self.list.count())]


def write_json_data(path, data):
    with open(path, "w") as fp:
        json.dump(data, fp, indent=4)


def read_json_data(path):
    with open(path, "r") as fp:
        return json.load(fp)


def default_scene_path():
    base_path, _ = os.path.splitext(pm.sceneName())
    default_path = base_path+".json"
    return default_path


def save_data_ui(get_default_path, get_data):
    default_path = get_default_path()
    path, _ = QFileDialog.getSaveFileName(get_host_app(), "Export", default_path, "Json (*.json)")
    if not path:
        return
    data = get_data()
    write_json_data(path, data)
    QMessageBox.about(get_host_app(), u"提示", u"导出成功！")


def load_data_ui(get_default_path, load_data):
    default_path = get_default_path()
    path, _ = QFileDialog.getOpenFileName(get_host_app(), "Load Poses", default_path, "Json (*.json)")
    if not path:
        return
    data = read_json_data(path)
    load_data(data)
    QMessageBox.about(get_host_app(), u"提示", u"导入成功！")

