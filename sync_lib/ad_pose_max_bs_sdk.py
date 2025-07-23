# -*- coding: utf-8 -*-#
import re

import MaxPlus
from pymxs import runtime as rt


def check_max_script(cmd):
    if cmd.startswith("."):
        cmd = cmd[1:]
    if cmd.startswith(" "):
        cmd = cmd[1:]
    if cmd.endswith(" "):
        cmd = cmd[:-1] + "()"
    return cmd


def m_eval(fmt, *args):
    cmd = check_max_script(fmt.format(*args))
    MaxPlus.Core.EvalMAXScript(cmd)


def check_arg(arg):
    if isinstance(arg, bool):
        return str(arg).lower()
    elif isinstance(arg, str):
        if not re.match("^\w+$", arg):
            return arg
        return '"%s"' % arg
    elif isinstance(arg, MaxPlus.INode):
        return "$" + arg.GetName()
    return str(arg)


class MS(object):

    def __init__(self, max_script=""):
        self.__MS__ = check_max_script(max_script)

    def __getattribute__(self, item):
        if item.startswith("__") and item.endswith("__"):
            return object.__getattribute__(self, item)
        elif hasattr(MS, item):
            return object.__getattribute__(self, item)
        else:
            return MS("{0}.{1}".format(self, item))

    def __getitem__(self, item):
        return MS("{0}[{1}]".format(self, item))

    def __repr__(self):
        return self.__MS__

    def __str__(self):
        return self.__MS__

    def __call__(self, *args):
        return MS("{0} {1}".format(self, " ".join(map(check_arg, args))))

    def __setattr__(self, key, value):
        if key == "__MS__":
            object.__setattr__(self, key, value)
        else:
            m_eval('{0}.{1} = {2}', self, key, check_arg(value))

    def to(self, cls):
        if cls == MaxPlus.INode:
            return MaxPlus.INode.GetINodeByName(self.name.to(str))
        else:
            m_eval('py_mx_runtime_rt = {0}', self)
        return cls(rt.py_mx_runtime_rt)


ms = MS()


def all_children(parent, result):
    for child in parent.Children:
        all_children(child, result)
        result.append(child)


def all_nodes():
    result = []
    all_children(MaxPlus.Core.GetRootNode(), result)
    return result


def find_all(is_find):
    return filter(is_find, all_nodes())


def find_by_typ(typ):
    return find_all(lambda x: x.GetBaseObject().GetClassName() == typ)


def create_group(name, parent=None):
    ms.point_group = ms.point()
    ms.point_group.name = name
    ms.point_group.Box = False
    ms.point_group.cross = False
    ms.point_group.axistripod = False
    ms.point_group.centermarker = False
    if parent is not None:
        ms.point_group.parent = parent
    return ms("$"+name)


def get_bs_target_ids():
    polygons = find_by_typ("Editable Poly")
    bs_target_id = []
    for polygon in polygons:
        bs = ms(polygon).Modifiers["morpher"]
        if bs.to(str) == "None":
            continue
        target_id = dict()
        target_count = ms.WM3_NumberOfChannels(bs).to(int)
        for i in range(target_count):
            if not ms.WM3_MC_HasData(bs, i).to(bool):
                continue
            target_name = ms.WM3_MC_GetName(bs, i).to(str)
            target_id[target_name] = i
        bs_target_id.append([bs, target_id])
    return bs_target_id


def targets_to_joint_pose(targets):
    joint_ads = dict()
    for curve in targets:
        match = re.match(r"^(?P<joint>\w+)_a(?P<a>[0-9]{1,3})_d(?P<d>[0-9]{1,3})$", curve)
        if not match:
            continue
        group_dict = match.groupdict()
        joint_ads.setdefault(group_dict["joint"], set()).add((int(group_dict["a"]), int(group_dict["d"])))
    return joint_ads


def create_orientation_constraint(src, dst):
    dst.rotation.controller = ms.orientation_constraint()
    dst.rotation.controller.appendTarget(src, 100).to(bool)
    dst.rotation.controller.local_world = 1


def create_position_constraint(src, dst):
    dst.pos.controller = ms.position_constraint()
    dst.pos.controller.appendTarget(src, 100).to(bool)


def create_x_axis(joint, root):
    prefix = joint.name.to(str) + "_ad_"
    pre_inverse = create_group(prefix+"pre_inverse", root)
    local_orientation = create_group(prefix+"local_orientation", pre_inverse)
    local_x_axis = create_group(prefix+"local_x_axis", local_orientation)
    pre_inverse.to(MaxPlus.INode).SetLocalRotation(joint.to(MaxPlus.INode).GetLocalRotation().Inverse())
    local_x_axis.to(MaxPlus.INode).SetLocalPosition(MaxPlus.Point3(1, 0, 0))
    create_orientation_constraint(joint, local_orientation)
    x_axis = create_group(prefix + "x_axis", root)
    create_position_constraint(local_x_axis, x_axis)
    return x_axis


def direction_sdk_data(d, ds):
    ds = list(ds)
    if 0 in ds:
        ds.append(360)
    if 360 in ds:
        ds.append(0)
    _ds = list(sorted(set(list(ds) + [d - 90, d + 90])))
    i = _ds.index(d)
    keys = [_ds[i + j] for j in [-1, 0, 1]]
    values = [0.0, 1.0, 0.0]
    if keys[0] < 0:
        keys += [k+360 for k in keys]
        values += values
    elif keys[-1] > 360:
        keys = [k-360 for k in keys] + keys
        values += values
    for i in range(3):
        if keys[1] <= 0:
            keys.pop(0)
            values.pop(0)
        if keys[-2] >= 360:
            keys.pop(-1)
            values.pop(-1)
    if (keys[0] < 0) and (keys[1] > 0):
        t1, v1 = keys[0], values[0]
        t2, v2 = keys[1], values[1]
        v = v1 + v2 * (0.0-t1)/(t2-t1)
        keys[0] = 0
        values[0] = v
    if (keys[-1] > 360) and (keys[-2] < 360):
        t1, v1 = keys[-2], values[-2]
        t2, v2 = keys[-1], values[-1]
        v = v1 + v2 * (0.0-t1)/(t2-t1)
        keys[-1] = 360
        values[-1] = v
    return keys, values


def angle_sdk_data(a, _as):
    _as = list(sorted(set(_as+[0, 180])))
    i = _as.index(a)
    keys = [_as[i + j] for j in [-1, 0, 1]]
    values = [0, 1, 0]
    if keys[-1] == 180:
        values[-1] = 1
    return keys, values


def sdk_scripts_lines(driver, driven, time_values):
    # 生成驱动关键帧的表达式
    fmt = "{driven} += " \
          "(if {driver} <= {st:.6f} then {st:.6f} else if {driver} >= {et:.6f} then {et:.6f} else {driver})*{slope:.6f}"
    lines = []
    intercept = time_values[0][1]
    for i in range(len(time_values)-1):
        st, sv = time_values[i]
        et, ev = time_values[i+1]
        if abs(sv-ev) < 0.00001:
            continue
        slope = float(ev-sv) / (et-st)
        lines.append(fmt.format(**locals()))
        intercept -= st * slope
    lines.insert(0, "{driven} = {intercept:.6f}".format(**locals()))
    return lines


def ad_bs_sdk(x_axis, target_name, angle_tvs, direction_tvs, bs_target_id):
    script_lines = ["angle = acos(x_axis_pos.Value.x)"]
    script_lines += sdk_scripts_lines("angle", "angle_driven", angle_tvs)
    script_lines.append("direction = x_axis_pos.Value.y*x_axis_pos.Value.y+x_axis_pos.Value.z*x_axis_pos.Value.z")
    script_lines.append("direction = pow direction 0.5")
    script_lines.append("direction = if direction > 0.0000001 then direction else 1")
    script_lines.append("direction = acos(x_axis_pos.Value.y / direction)")
    script_lines.append("direction = if x_axis_pos.Value.z < 0.000000 then 360 - direction else direction")
    script_lines += sdk_scripts_lines("direction", "direction_driven", direction_tvs)
    script_lines.append("result = angle_driven*direction_driven*100")
    script = '"%s"' % "\r\n".join(script_lines)
    ms.float_script_controller = ms.float_script()
    ms.float_script_controller.AddObject("x_axis_pos", x_axis.pos.controller).to(str)
    ms.float_script_controller.script = script
    tx_script = create_group(target_name+"_tx_script", "$ADPoseSystem")
    tx_script.centermarker = True
    tx_script.pos.controller.X_Position.controller = ms.float_script_controller
    for bs, target_id in bs_target_id:
        if target_name not in target_id:
            continue
        bs[target_id[target_name]].controller = ms.float_script_controller


def doit():
    root = create_group("ADPoseSystem")
    bs_target_id = get_bs_target_ids()
    targets = list(set(sum([target_id.keys() for _, target_id in bs_target_id], [])))
    joint_poses = targets_to_joint_pose(targets)
    for joint_name, poses in joint_poses.items():
        joint = ms("$"+joint_name)
        if joint.to(str) == "undefined":
            continue
        x_axis = create_x_axis(joint, root)
        d_a_dict = {}
        for a, d in poses:
            d_a_dict.setdefault(d, []).append(a)
        ds = d_a_dict.keys()
        for d, _as in d_a_dict.items():
            keys, values = direction_sdk_data(d, ds)
            direction_tvs = zip(keys, values)
            for a in _as:
                keys, values = angle_sdk_data(a, _as)
                angle_tvs = zip(keys, values)
                target_name = "{joint_name}_a{a}_d{d}".format(**locals())
                ad_bs_sdk(x_axis, target_name, angle_tvs, direction_tvs, bs_target_id)


if __name__ == '__main__':
    doit()
