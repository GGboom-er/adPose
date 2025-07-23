# coding:utf-8
from functools import partial

try:
    from PySide.QtGui import *
    from PySide.QtCore import *
except ImportError:
    from PySide2.QtGui import *
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
from . import tool
from maya import cmds


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


def q_add(lay, *args):
    for arg in args:
        if isinstance(arg, QWidget):
            lay.addWidget(arg)
        else:
            lay.addLayout(arg)
    return lay


def q_button(label, action):
    but = QPushButton(label)
    but.clicked.connect(action)
    return but


def q_spin(value, min_value, max_value):
    spin = QSpinBox()
    spin.setRange(min_value, max_value)
    spin.setValue(value)
    return spin


def q_label(label, width):
    label = QLabel(label)
    label.setFixedWidth(width)
    label.setAlignment(Qt.AlignRight)
    return label


def q_object(get_object):
    line = QLineEdit()

    def load_obj():
        line.setText(get_object())
    return line,  q_add(
        QHBoxLayout(),
        line,
        q_button("<<", load_obj)
    )


def get_item_names(list_weight):
    return [list_weight.item(i).text() for i in range(list_weight.count())]


def q_list(get_items):
    object_list = QListWidget()
    object_list.setSelectionMode(object_list.ExtendedSelection)

    def add_objects():
        object_list.addItems([item for item in get_items() if item not in get_item_names(object_list)])

    def del_objects():
        if not object_list.selectedItems():
            return
        old_items = get_item_names(object_list)
        selected_items = [item.text() for item in object_list.selectedItems()]
        new_items = [item for item in old_items if item not in selected_items]
        object_list.clear()
        object_list.addItems(new_items)

    return object_list, q_add(
        QVBoxLayout(),
        q_add(
            QHBoxLayout(),
            q_button(u"添加", add_objects),
            q_button(u"删除", del_objects),
        ),
        object_list
    )


class PartDeformToSkinTool(QDialog):

    def __init__(self, parent, get_targets):
        QDialog.__init__(self, parent)
        self.setWindowTitle(u"局部修形转骨骼")
        self.setLayout(QVBoxLayout())
        self.deform_polygon, deform_polygon = q_object(tool.get_selected_polygon)
        self.skin_polygon, skin_polygon = q_object(tool.get_selected_polygon)
        self.target_names, target_names = q_list(get_targets)
        self.unlock_joints, unlock_joints = q_list(partial(cmds.ls, sl=1, type="joint"))
        self.new_joint_count = q_spin(4, 0, 100)
        self.max_influence = q_spin(4, 1, 100)
        self.iter_count = q_spin(15, 5, 60)
        self.duplicate = QCheckBox()
        self.duplicate.setChecked(True)
        self.scale = QCheckBox()
        w = 60
        q_add(
            self.layout(),
            q_add(QHBoxLayout(), q_label(u"变形模型：", w), deform_polygon) ,
            q_add(QHBoxLayout(), q_label(u"蒙皮模型：", w), skin_polygon),
            q_add(QVBoxLayout(), q_label(u"解锁骨骼：", w), unlock_joints),
            q_add(QVBoxLayout(), q_label(u"修形姿势：", w), target_names),
            q_add(QHBoxLayout(), q_label(u"新增骨骼：", w), self.new_joint_count),
            q_add(QHBoxLayout(), q_label(u"最大影响：", w), self.max_influence),
            q_add(QHBoxLayout(), q_label(u"迭代次数：", w), self.iter_count),
            q_add(QHBoxLayout(), q_label(u"复制模型：", w), self.duplicate),
            q_add(QHBoxLayout(), q_label(u"使用缩放：", w), self.scale),
            q_button(u"解算", self.apply)
        )

    def apply(self):
        tool.part_deform_to_skin(
            deform_polygon=self.deform_polygon.text(),
            skin_polygon=self.skin_polygon.text(),
            target_names=get_item_names(self.target_names),
            unlock_joints=get_item_names(self.unlock_joints),
            max_influence=self.max_influence.value(),
            new_joint_count=self.new_joint_count.value(),
            iter_count=self.iter_count.value(),
            duplicate=self.duplicate.isChecked(),
            scale=self.scale.isChecked()
        )
        self.deform_polygon.text()


window = None


def show():
    global window
    if window is None:
        window = PartDeformToSkinTool()
    window.show()
