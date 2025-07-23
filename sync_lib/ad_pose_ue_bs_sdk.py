import unreal
import re
import math


@unreal.uclass()
class getContentBrowser(unreal.GlobalEditorUtilityBase):
    pass


def get_selected_asset():
    editor_util = getContentBrowser()
    return editor_util.get_selected_assets()


def get_selected_skeletal_mesh():
    for sel in get_selected_asset():
        if isinstance(sel, unreal.SkeletalMesh):
            return sel


def create_rbf_bp(skeletal_mesh):
    factory = unreal.ControlRigBlueprintFactory()
    return factory.create_control_rig_from_skeletal_mesh_or_skeleton(skeletal_mesh)


def get_ad_pose_data(hierarchy_modifier):
    # get joints and targets
    joints = []
    targets = []
    elem_keys = hierarchy_modifier.get_elements()
    for elem_key in elem_keys:
        typ = elem_key.get_editor_property("type")
        name = str(elem_key.get_editor_property("name"))
        if typ == unreal.RigElementType.CURVE:
            targets.append(name)
        elif typ == unreal.RigElementType.BONE:
            bone = hierarchy_modifier.get_bone(elem_key)
            transform = bone.get_editor_property("local_transform")
            joints.append(name)
    # re joint ad
    joint_ads = dict()
    for curve in targets:
        match = re.match(r"^(?P<joint>\w+)_a(?P<a>[0-9]{1,3})_d(?P<d>[0-9]{1,3})$", curve)
        if not match:
            continue
        group_dict = match.groupdict()
        joint = group_dict["joint"]
        if joint not in joints:
            continue
        joint_ads.setdefault(group_dict["joint"], set()).add((int(group_dict["a"]), int(group_dict["d"])))
    return joint_ads


def create_struct_node(controller, cls, i, j):
    size = 400
    node = controller.add_struct_node(
        script_struct=getattr(unreal, cls)().static_struct(),
        method_name="Execute",
        position=[int(size*j), int(size*i)],
        node_name=cls)
    return node


def create_if_node(controller, typ, i, j):
    size = 400
    path = controller.get_path_name().split(":")[0]+":RigVMModel"
    return controller.add_if_node(typ, path, [size*j, size*i], "if")


def graph_info(controller):
    graph = controller.get_graph()
    for node in graph.get_select_nodes():
        node = graph.find_node_by_name(node)
        # print(node.get_pins())
        # pin = node.find_pin("curve")
        # print(pin)
        # value = "(EditorCurveData=(Keys=((Time=0,Value=0),(Time=0.5,Value=1),(Time=1,Value=0))))"
        # controller.set_pin_default_value(pin.get_pin_path(), value)
        # print(type(node))
        # print(node)
        print(node.get_script_struct())
        print(node.get_method_name())
        print(node.get_struct_default_value())
        # print(node.get_node_path())


def create_angle_direction_collection(controller, data):
    items = create_struct_node(controller, "RigUnit_CollectionItems", 2, -2)
    controller.set_array_pin_size(items.find_pin("Items").get_pin_path(), len(data.keys()))
    for i, name in enumerate(data.keys()):
        controller.set_pin_default_value(items.find_pin("Items.{i}.Type".format(i=i)).get_pin_path(), "Bone")
        controller.set_pin_default_value(items.find_pin("Items.{i}.Name".format(i=i)).get_pin_path(), name)

    begin = create_struct_node(controller, "RigUnit_BeginExecution", 1, -2)
    loop = create_struct_node(controller, "RigUnit_CollectionLoop", 1, -1)
    controller.add_link(items.find_pin("Collection").get_pin_path(),
                        loop.find_pin("Collection").get_pin_path())
    controller.add_link(begin.find_pin("ExecuteContext").get_pin_path(),
                        loop.find_pin("ExecuteContext").get_pin_path())

    bone = create_struct_node(controller, "RigUnit_GetTransform", 1, 0)
    initial = create_struct_node(controller, "RigUnit_GetTransform", 2, 0)
    controller.set_pin_default_value(bone.find_pin("Space").get_pin_path(), "LocalSpace")
    controller.set_pin_default_value(initial.find_pin("Space").get_pin_path(), "LocalSpace")
    controller.set_pin_default_value(initial.find_pin("bInitial").get_pin_path(), "true")
    controller.add_link(loop.find_pin("Item").get_pin_path(),
                        bone.find_pin("Item").get_pin_path())
    controller.add_link(loop.find_pin("Item").get_pin_path(),
                        initial.find_pin("Item").get_pin_path())

    relative = create_struct_node(controller, "RigUnit_MathTransformMakeRelative", 1, 1)
    controller.add_link(bone.find_pin("Transform").get_pin_path(),
                        relative.find_pin("Global").get_pin_path())
    controller.add_link(initial.find_pin("Transform").get_pin_path(),
                        relative.find_pin("Parent").get_pin_path())

    rotate = create_struct_node(controller, "RigUnit_MathQuaternionRotateVector", 1, 2)
    controller.set_pin_default_value(rotate.find_pin("Vector.X").get_pin_path(), "1.0")
    controller.add_link(relative.find_pin("Local.Rotation").get_pin_path(),
                        rotate.find_pin("Quaternion").get_pin_path())

    angle = create_struct_node(controller, "RigUnit_MathVectorAngle", 1, 4)
    controller.set_pin_default_value(angle.find_pin("B.X").get_pin_path(), "1.0")
    controller.add_link(rotate.find_pin("Result").get_pin_path(),
                        angle.find_pin("A").get_pin_path())
    greater = create_struct_node(controller, "RigUnit_MathFloatGreater", 1, 3)
    direction = create_struct_node(controller, "RigUnit_MathVectorAngle", 1.5, 3)
    sub = create_struct_node(controller, "RigUnit_MathFloatSub", 2.0, 3)

    condition = create_if_node(controller, "float",  2, 4)
    controller.set_pin_default_value(direction.find_pin("B.Y").get_pin_path(), "-1.0")
    controller.add_link(rotate.find_pin("Result.Y").get_pin_path(),
                        direction.find_pin("A.Y").get_pin_path())
    controller.add_link(rotate.find_pin("Result.Z").get_pin_path(),
                        direction.find_pin("A.Z").get_pin_path())
    controller.add_link(rotate.find_pin("Result.Z").get_pin_path(),
                        greater.find_pin("A").get_pin_path())
    controller.set_pin_default_value(sub.find_pin("A").get_pin_path(), "%.6f" % (math.pi*2))
    controller.add_link(greater.find_pin("Result").get_pin_path(),
                        condition.find_pin("Condition").get_pin_path())
    controller.add_link(direction.find_pin("Result").get_pin_path(),
                        sub.find_pin("B").get_pin_path())
    controller.add_link(sub.find_pin("Result").get_pin_path(),
                        condition.find_pin("False").get_pin_path())
    controller.add_link(direction.find_pin("Result").get_pin_path(),
                        condition.find_pin("True").get_pin_path())

    angle_scale = create_struct_node(controller, "RigUnit_MathFloatDiv", 1, 5)
    direction_scale = create_struct_node(controller, "RigUnit_MathFloatDiv", 2, 5)
    controller.set_pin_default_value(angle_scale.find_pin("B").get_pin_path(), "%.6f" % (math.pi*2.0 / 360.0))
    controller.set_pin_default_value(direction_scale.find_pin("B").get_pin_path(), "%.6f" % (math.pi*2.0 / 360.0))
    controller.add_link(angle.find_pin("Result").get_pin_path(),
                        angle_scale.find_pin("A").get_pin_path())
    controller.add_link(condition.find_pin("Result").get_pin_path(),
                        direction_scale.find_pin("A").get_pin_path())

    angle_concat = create_struct_node(controller, "RigUnit_NameConcat", 1.5, 5)
    direction_concat = create_struct_node(controller, "RigUnit_NameConcat", 2.5, 5)
    controller.set_pin_default_value(angle_concat.find_pin("B").get_pin_path(), "_Angle")
    controller.set_pin_default_value(direction_concat.find_pin("B").get_pin_path(), "_Direction")
    controller.add_link(loop.find_pin("Item.Name").get_pin_path(),
                        angle_concat.find_pin("A").get_pin_path())
    controller.add_link(loop.find_pin("Item.Name").get_pin_path(),
                        direction_concat.find_pin("A").get_pin_path())

    angle_ctrl = create_struct_node(controller, "RigUnit_SetControlFloat", 1, 6)
    direction_ctrl = create_struct_node(controller, "RigUnit_SetControlFloat", 2, 6)
    controller.add_link(angle_scale.find_pin("Result").get_pin_path(),
                        angle_ctrl.find_pin("FloatValue").get_pin_path())
    controller.add_link(direction_scale.find_pin("Result").get_pin_path(),
                        direction_ctrl.find_pin("FloatValue").get_pin_path())
    controller.add_link(angle_concat.find_pin("Result").get_pin_path(),
                        angle_ctrl.find_pin("Control").get_pin_path())
    controller.add_link(direction_concat.find_pin("Result").get_pin_path(),
                        direction_ctrl.find_pin("Control").get_pin_path())
    controller.add_link(loop.find_pin("ExecuteContext").get_pin_path(),
                        angle_ctrl.find_pin("ExecuteContext").get_pin_path())
    controller.add_link(angle_ctrl.find_pin("ExecuteContext").get_pin_path(),
                        direction_ctrl.find_pin("ExecuteContext").get_pin_path())
    return loop.find_pin("Completed").get_pin_path()


def get_ctrl_name_list(hierarchy_modifier):
    elem_keys = hierarchy_modifier.get_elements()
    controls = []
    for elem_key in elem_keys:
        typ = elem_key.get_editor_property("type")
        name = str(elem_key.get_editor_property("name"))
        if typ == unreal.RigElementType.CONTROL:
            controls.append(name)
    return controls


def update_ad_pose_ctrl(hierarchy_modifier, data):
    controls = get_ctrl_name_list(hierarchy_modifier)
    for joint_name in data.keys():
        for suffix in ["_Angle", "_Direction"]:
            ctrl_name = joint_name + suffix
            if ctrl_name in controls:
                continue
            hierarchy_modifier.add_control(ctrl_name, unreal.RigControlType.FLOAT)


def direction_sdk_data(d, ds):
    ds = list(ds)
    if 0 in ds:
        ds.append(360)
    if 360 in ds:
        ds.append(0)
    _ds = list(sorted(set(list(ds) + [d - 90, d + 90])))
    i = _ds.index(d)
    keys = [_ds[i + j] for j in [-1, 0, 1]]
    values = [0, 1, 0]
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


def create_bs_sdk(controller, execute, data):
    pose_joints = {}
    for joint, pose in data.items():
        pose = tuple(sorted(pose))
        pose_joints.setdefault(pose, []).append(joint)
    i = 4

    for poses, joints in pose_joints.items():
        items = create_struct_node(controller, "RigUnit_CollectionItems", i+0, -2)
        controller.set_array_pin_size(items.find_pin("Items").get_pin_path(), len(joints))
        for j, name in enumerate(joints):
            controller.set_pin_default_value(items.find_pin("Items.{i}.Type".format(i=j)).get_pin_path(), "Bone")
            controller.set_pin_default_value(items.find_pin("Items.{i}.Name".format(i=j)).get_pin_path(), name)
        loop = create_struct_node(controller, "RigUnit_CollectionLoop", i+0, -1)
        controller.add_link(items.find_pin("Collection").get_pin_path(),
                            loop.find_pin("Collection").get_pin_path())
        controller.add_link(execute, loop.find_pin("ExecuteContext").get_pin_path())
        execute = loop.find_pin("Completed").get_pin_path()
        angle_concat = create_struct_node(controller, "RigUnit_NameConcat", i + 0, 0)
        direction_concat = create_struct_node(controller, "RigUnit_NameConcat", i + 1, 0)
        controller.add_link(loop.find_pin("Item.Name").get_pin_path(),
                            angle_concat.find_pin("A").get_pin_path())
        controller.add_link(loop.find_pin("Item.Name").get_pin_path(),
                            direction_concat.find_pin("A").get_pin_path())
        controller.set_pin_default_value(angle_concat.find_pin("B").get_pin_path(), "_Angle")
        controller.set_pin_default_value(direction_concat.find_pin("B").get_pin_path(), "_Direction")

        angle_ctrl = create_struct_node(controller, "RigUnit_GetControlFloat", i+0, 1)
        direction_ctrl = create_struct_node(controller, "RigUnit_GetControlFloat", i+1, 1)

        controller.add_link(angle_concat.find_pin("Result").get_pin_path(),
                            angle_ctrl.find_pin("Control").get_pin_path())
        controller.add_link(direction_concat.find_pin("Result").get_pin_path(),
                            direction_ctrl.find_pin("Control").get_pin_path())
        remap_i = 0
        sum_i = 0
        mul_i = 0

        d_a_dict = {}
        for a, d in poses:
            d_a_dict.setdefault(d, []).append(a)
        ds = d_a_dict.keys()
        a_sdk_dict = {}
        loop_execute = loop.find_pin("ExecuteContext").get_pin_path()
        for d, _as in d_a_dict.items():
            keys, values = direction_sdk_data(d, ds)
            remap_i, sum_i, direction_sdk = create_sdk(controller, remap_i, sum_i, i, direction_ctrl, keys, values)
            for a in _as:
                keys, values = angle_sdk_data(a, _as)
                _key = tuple(list(sorted(keys)))
                if _key in a_sdk_dict:
                    angle_sdk = a_sdk_dict[_key]
                else:
                    remap_i, sum_i, angle_sdk = create_sdk(controller, remap_i, sum_i, i, angle_ctrl, keys, values)
                    a_sdk_dict[_key] = angle_sdk
                mul = create_struct_node(controller, "RigUnit_MathFloatMul", i + mul_i, 4)
                controller.add_link(angle_sdk, mul.find_pin("A").get_pin_path())
                controller.add_link(direction_sdk, mul.find_pin("B").get_pin_path())

                curve_concat = create_struct_node(controller, "RigUnit_NameConcat", i + mul_i, 5)
                controller.add_link(loop.find_pin("Item.Name").get_pin_path(),
                                    curve_concat.find_pin("A").get_pin_path())
                name = "_a{a}_d{d}".format(**locals())
                controller.set_pin_default_value(curve_concat.find_pin("B").get_pin_path(), name)

                curve = create_struct_node(controller, "RigUnit_SetCurveValue", i + mul_i, 6)
                controller.add_link(curve_concat.find_pin("Result").get_pin_path(),
                                    curve.find_pin("Curve").get_pin_path())
                controller.add_link(mul.find_pin("Result").get_pin_path(),
                                    curve.find_pin("Value").get_pin_path())
                controller.add_link(loop_execute, curve.find_pin("ExecuteContext").get_pin_path())
                loop_execute = curve.find_pin("ExecuteContext").get_pin_path()
                mul_i += 1.0/3
        i = i+math.ceil(max(2, remap_i, mul_i, sum_i))


def create_sdk(controller, remap_i, sum_i, i, driver, keys, values):
    remaps = []
    for j in range(len(keys)-1):
        if values[j] == values[j+1]:
            continue
        remap = create_struct_node(controller, "RigUnit_MathFloatRemap", i + remap_i, 2)
        remap_i += 0.5
        remaps.append(remap)
        controller.set_pin_default_value(remap.find_pin("SourceMinimum").get_pin_path(), "%.6f" % (keys[j]))
        controller.set_pin_default_value(remap.find_pin("SourceMaximum").get_pin_path(), "%.6f" % (keys[j+1]))
        controller.set_pin_default_value(remap.find_pin("bClamp").get_pin_path(), "true")
        if j == 0:
            controller.set_pin_default_value(remap.find_pin("TargetMinimum").get_pin_path(), "%.6f" % (values[j]))
            controller.set_pin_default_value(remap.find_pin("TargetMaximum").get_pin_path(), "%.6f" % (values[j+1]))
        else:
            controller.set_pin_default_value(remap.find_pin("TargetMinimum").get_pin_path(), "%.6f" % 0)
            value = values[j+1]-values[j]
            controller.set_pin_default_value(remap.find_pin("TargetMaximum").get_pin_path(), "%.6f" % value)
        controller.add_link(driver.find_pin("FloatValue").get_pin_path(),
                            remap.find_pin("Value").get_pin_path())
    result = remaps[0].find_pin("Result").get_pin_path()
    for remap in remaps[1:]:
        add = create_struct_node(controller, "RigUnit_MathFloatAdd", i + sum_i, 3)
        sum_i += 1.0/3
        controller.add_link(result, add.find_pin("A").get_pin_path())
        controller.add_link(remap.find_pin("Result").get_pin_path(),
                            add.find_pin("B").get_pin_path())
        result = add.find_pin("Result").get_pin_path()
    return remap_i, sum_i, result


def doit():
    """
    :return:
from importlib import reload
import ad_pose_ue_bs_sdk
reload(ad_pose_ue_bs_sdk)
ad_pose_ue_bs_sdk.doit()
    """
    control_rig_bp = get_selected_asset()[0]
    hierarchy_modifier = control_rig_bp.get_hierarchy_modifier()
    controller = control_rig_bp.get_editor_property("controller")
    data = get_ad_pose_data(hierarchy_modifier)
    update_ad_pose_ctrl(hierarchy_modifier, data)
    execute = create_angle_direction_collection(controller, data)
    graph_info(controller)
    create_bs_sdk(controller, execute, data)


if __name__ == '__main__':
    doit()
