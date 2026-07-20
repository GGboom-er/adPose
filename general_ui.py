# coding:utf-8
"""
通用 UI 组件模块
已从 pymel 迁移到 maya.cmds
"""
try:
    from PySide6.QtGui import *
    from PySide6.QtCore import *
    from PySide6.QtWidgets import *
    PYSIDE_VERSION = 6
except ImportError:
    try:
        from PySide2.QtGui import *
        from PySide2.QtCore import *
        from PySide2.QtWidgets import *
        PYSIDE_VERSION = 2
    except ImportError:
        from PySide.QtGui import *
        from PySide.QtCore import *
        PYSIDE_VERSION = 1

# PySide6 兼容性：SelectionMode
if PYSIDE_VERSION == 6:
    ExtendedSelection = QAbstractItemView.SelectionMode.ExtendedSelection
else:
    ExtendedSelection = QAbstractItemView.ExtendedSelection

from maya import cmds
from maya.OpenMayaUI import MQtUtil
import json
import os

if PYSIDE_VERSION == 6:
    import shiboken6 as shiboken
elif PYSIDE_VERSION == 2:
    import shiboken2 as shiboken
else:
    import shiboken


def get_host_app():
    """获取 Maya 主窗口"""
    pointer = MQtUtil.mainWindow()
    if pointer is None:
        return None
    return shiboken.wrapInstance(int(pointer), QWidget)


def button(text, fun):
    """创建按钮"""
    but = QPushButton(text)
    but.clicked.connect(fun)
    return but


class PrefixWeight(QHBoxLayout):
    """带前缀标签的布局"""
    def __init__(self, label, weight, width=60):
        QHBoxLayout.__init__(self)
        prefix = QLabel(label)
        prefix.setFixedWidth(width)
        prefix.setAlignment(Qt.AlignRight)
        self.addWidget(prefix)
        self.addWidget(weight)


class Tool(QDialog):
    """工具对话框基类"""
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
        cmds.undoInfo(openChunk=True)
        try:
            self.apply()
        except Exception:
            cmds.undoInfo(closeChunk=True)
            raise
        cmds.undoInfo(closeChunk=True)

    def showNormal(self):
        QDialog.showNormal(self)
        self.show_update()

    def show_update(self):
        pass


class MayaObjLayout(QHBoxLayout):
    """Maya 对象选择布局"""
    objChanged = Signal(u"".__class__)

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

    def set_obj(self, obj):
        """设置对象 - obj 现在是字符串"""
        self.obj = obj
        # 兼容字符串和旧的 PyNode
        if isinstance(obj, str):
            self.line.setText(obj)
        else:
            self.line.setText(str(obj))

    def load_selected(self):
        selected = cmds.ls(sl=True, o=True) or []
        if len(selected) == 1:
            self.set_obj(selected[0])
        else:
            self.clear()
        self.objChanged.emit(self.line.text())

    def clear(self):
        self.obj = None
        self.line.clear()


class MayaObjLayouts(MayaObjLayout):
    """多对象选择布局"""

    def load_selected(self):
        selected = cmds.ls(sl=True) or []
        self.line.setText(",".join(selected))
        self.objChanged.emit(self.line.text())


class Number(QSpinBox):
    """数字输入框"""

    def __init__(self, _min, _max, _def):
        QSpinBox.__init__(self)
        self.setRange(_min, _max)
        self.setValue(_def)


def layout_adds(lay, *args):
    """向布局添加多个组件"""
    for arg in args:
        if isinstance(arg, QWidget):
            lay.addWidget(arg)
        else:
            lay.addLayout(arg)
    return lay


def h_layout(*args):
    """创建水平布局"""
    return layout_adds(QHBoxLayout(), *args)


class TargetSlider(QHBoxLayout):
    """目标滑块控件"""

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
    """骨骼列表控件"""

    def __init__(self):
        QVBoxLayout.__init__(self)
        self.addLayout(h_layout(button(u"添加骨骼", self.add_joints), button(u"删除骨骼", self.del_joints)))
        self.list = QListWidget()
        self.list.setSelectionMode(ExtendedSelection)
        self.addWidget(self.list)

    def add_joints(self):
        joints = self.get_joints()
        for joint in cmds.ls(sl=True, type="joint") or []:
            if joint in joints:
                continue
            joints.append(joint)
        self.list.clear()
        self.list.addItems(joints)

    def del_joints(self):
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.indexFromItem(item).row())

    def get_joints(self):
        return [self.list.item(i).text() for i in range(self.list.count())]


def write_json_data(path, data):
    """写入 JSON 数据"""
    with open(path, "w") as fp:
        json.dump(data, fp, indent=4)


def read_json_data(path):
    """读取 JSON 数据"""
    with open(path, "r") as fp:
        return json.load(fp)


def default_scene_path():
    """获取默认场景路径"""
    scene_name = cmds.file(q=True, sn=True) or ""
    base_path, _ = os.path.splitext(scene_name)
    default_path = base_path + ".json"
    return default_path


def save_data_ui(get_default_path, get_data):
    """保存数据 UI"""
    default_path = get_default_path()
    path, _ = QFileDialog.getSaveFileName(get_host_app(), "Export", default_path, "Json (*.json)")
    if not path:
        return
    data = get_data()
    write_json_data(path, data)
    QMessageBox.about(get_host_app(), u"提示", u"导出成功！")


def load_data_ui(get_default_path, load_data):
    """加载数据 UI"""
    default_path = get_default_path()
    path, _ = QFileDialog.getOpenFileName(get_host_app(), "Load Poses", default_path, "Json (*.json)")
    if not path:
        return
    data = read_json_data(path)
    load_data(data)
    QMessageBox.about(get_host_app(), u"提示", u"导入成功！")
