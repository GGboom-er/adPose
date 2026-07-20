# coding:utf-8
import os
import json
import re

from .general_ui import *


config = None
default_config = data = [
    [u"左边", "right", ["{name}_R", "{pre}_R_{suf}"]],
    [u"右边", "left", ["{name}_L", "{pre}_L_{suf}"]],
    [u"骨骼", "joint", ["{name}", "{name}Part{i}_{RL}"]],
    [u"控制器", "ctrl", ["FK{name}", "FK{name}_{RL}"]],
]


def get_config():
    global config
    if config is not None:
        return config
    path = os.path.abspath(__file__+"/../data/config.json").replace("\\", "/")
    if os.path.isfile(path):
        with open(path) as fp:
            config = json.load(fp)
            return config
    else:
        return default_config


def get_dict_config():
    return {key: value for _, key, value in get_config()}


class ConfigTool(Tool):
    title = u"配置工具"
    button_text = u"保存配置"

    def __init__(self, parent=None):
        Tool.__init__(self, parent)
        self.weights = {}
        for label, key, _ in default_config:
            self.weights[key] = QLineEdit()
            self.kwargs_layout.addLayout(PrefixWeight(label+u"：", self.weights[key], 50))

    def apply(self):
        global config
        config = get_config()
        for row in config:
            row[2] = [field for field in self.weights[row[1]].text().split(",") if field]
        path = os.path.abspath(__file__ + "/../data/config.json").replace("\\", "/")
        with open(path, "w") as fp:
            json.dump(config, fp, indent=4)

    def show_update(self):
        for _, key, value in get_config():
            self.weights[key].setText(",".join(value))



def get_names(name, src_formats, dst_formats):
    names = []
    for src, dst in zip(src_formats, dst_formats):
        keys = re.findall(r"\{\w+\}", src)
        if not keys:
            continue
        for key in keys:
            src = src.replace(key, r"(\w+)")
        match = re.match(src+"$", name)
        if not match:
            continue
        keys = [key[1:-1] for key in keys]
        values = match.groups()
        if not len(values) == len(keys):
            continue
        new_name = dst.format(**dict(zip(keys, values)))
        names.append(new_name)
    return names


def get_ctrl_names(name):
    _config = get_dict_config()
    return get_names(name, _config["joint"], _config["ctrl"])


def get_rl_names(name):
    _config = get_dict_config()
    names = get_names(name, _config["right"], _config["left"])
    names += get_names(name, _config["left"], _config["right"])
    return names


if __name__ == '__main__':
    pass