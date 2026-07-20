# coding=utf-8
"""
# 使用python list dict缓存pin姿势，cluster权重等信息
# 绑定时修改数据修改缓存，不实际创建模型，蒙皮，融合变形
# 绑定完毕后再根据缓存信息实例化模型，蒙皮，融合变形。
# 方便绑定的修改，重建。
"""
from maya import cmds
from .polygon import create_polygon_by_matrices
from .pin import link_pin
from . import bs
from .skin import create_skin, get_weights, get_skin_joints


def create_node(typ, name, parent=None):
    if cmds.objExists(name):
        return name
    if parent is not None:
        return cmds.createNode(typ, n=name, p=parent, ss=True)
    else:
        return cmds.createNode(typ, n=name, ss=True)


def create_group(name, parent=None):
    return create_node("transform", name, parent)


def add_attr(node, attr, *args, **kwargs):
    node_attr = node + "." + attr
    if cmds.objExists(node_attr):
        return node_attr
    cmds.addAttr(node, ln=attr, *args, **kwargs)
    return node_attr


def set_attr(attr, value):
    if not cmds.objExists(attr):
        return
    typ = cmds.getAttr(attr, type=1)
    if typ in ["matrix", "string"]:
        cmds.setAttr(attr, value, type=typ)
    else:
        cmds.setAttr(attr, value)


def get_children(root):
    if not cmds.objExists(root):
        return []
    return cmds.listRelatives(root) or []


class FacePin(object):

    def __init__(self, name="M"):
        self.name = name
        self.pins = []
        self.pin_matrices = dict()
        self.clusters = dict()
        self.layers = dict()
        self.weights = dict()
        self.points = dict()
        self.drivers = dict()
        self.follows = dict()
        self.body = False

    @staticmethod
    def is_pin(pin_node):
        if cmds.objectType(pin_node) != "transform":
            return False
        if not pin_node.endswith("Pin"):
            return False
        if not cmds.objExists(pin_node + "." + "faceIndex"):
            return False
        if not cmds.objExists(pin_node + "." + "bindMatrix"):
            return False
        return True

    def load_pins(self):
        pins = dict()
        for pin_node in filter(self.is_pin, get_children(self.name+"Pins")):
            face_index = cmds.getAttr(pin_node + "." + "faceIndex")
            matrix = cmds.getAttr(pin_node + "." + "bindMatrix")
            name = pin_node[:-3]
            pins[face_index] = name
            self.pin_matrices[name] = matrix
        if not pins:
            return
        pin_count = max(pins.keys()) + 1
        self.pins = [self.name+"Unknown"] * pin_count
        for index, pin in pins.items():
            self.pins[index] = pin

    @staticmethod
    def is_cluster(cluster_node):
        if cmds.objectType(cluster_node) != "transform":
            return False
        if not cluster_node.endswith("Pre"):
            return False
        if not cmds.objExists(cluster_node[:-3]+"Cluster"):
            return False
        return True

    def load_clusters(self):
        for cluster_node in filter(self.is_cluster, get_children(self.name+"Clusters")):
            self.clusters[cluster_node[:-3]] = cmds.xform(cluster_node, q=1, ws=1, m=1)
        self.remove_cluster(self.name+"Static")

    @staticmethod
    def is_layer(layer_node):
        if cmds.objectType(layer_node) != "transform":
            return False
        if not layer_node.endswith("Layer"):
            return False
        clusters = get_skin_joints(layer_node)
        if not clusters:
            return False
        return True

    def load_weights(self):
        for layer_node in filter(self.is_layer, get_children(self.name+"Layers")):
            layer_name = layer_node[len(self.name):-len("Layer")]
            clusters = get_skin_joints(layer_node)
            joint_count = len(clusters)
            weights = get_weights(layer_node)
            weights = [weights[i:i+joint_count] for i in range(0, len(weights), joint_count)]
            weights = [weights[i] for i in range(0, len(weights), 4)]
            for cluster, ws in zip(clusters, zip(*weights)):
                if not cluster.endswith("Cluster"):
                    continue
                cluster_name = cluster[:-len("Cluster")]
                if cluster_name not in self.clusters:
                    continue
                self.set_layer(layer_name, cluster_name)
                for w, pin in zip(ws, self.pins):
                    self.set_weight(cluster_name, pin, w)

    def load_blend_shape(self):
        plane = self.plane_name()
        if not cmds.objExists(plane):
            return
        self.drivers.update(bs.get_target_drivers(plane))
        for target, id_points in bs.get_targets_id_points(plane).items():
            for i, pin in enumerate(self.pins):
                for j in range(4):
                    vtx_id = i * 4 + j
                    if vtx_id in id_points:
                        self.points.setdefault(target, dict()).setdefault(pin, dict())[j] = id_points[vtx_id]

    def load(self):
        self.load_pins()
        self.load_clusters()
        self.load_weights()
        self.load_blend_shape()

        if self.body:
            self.load_follow()
        return self

    def add_pin(self, name, matrix):
        if name not in self.pins:
            self.pins.append(name)
        self.pin_matrices[name] = matrix

    def build_pin(self, name, matrix):
        self.add_pin(name, matrix)
        pin_node = create_group(name + "Pin", self.name + "Pins")
        cmds.xform(name+"Pin", ws=1, m=matrix)
        set_attr(add_attr(pin_node, "bindMatrix", at="matrix"), matrix)

    def add_cluster(self, name, matrix):
        self.clusters[name] = matrix

    def set_weight(self, cluster, pin, weight):
        self.weights.setdefault(cluster, dict())[pin] = weight

    def set_follow(self, cluster, pin, weight):
        if cluster in self.pins:
            return
        self.follows.setdefault(cluster, dict())[pin] = weight

    def set_layer(self, layer, cluster):
        self.layers[cluster] = layer

    def build_root(self):
        root = create_group(self.name+"s")
        for suf in ["Pins", "Layers", "Clusters"]:
            group = create_group(self.name+suf, root)
            cmds.setAttr(group+".v", 0)
            cmds.setAttr(group+".inheritsTransform", False)

    def build_pins(self):
        plane = self.name + "Plane"
        for index, pin in enumerate(self.pins):
            pin_node = create_group(pin + "Pin", self.name + "Pins")
            set_attr(add_attr(pin_node, "bindMatrix", at="matrix"), self.pin_matrices[pin])
            set_attr(add_attr(pin_node, "faceIndex", at="long"), index)
            link_pin(plane, pin_node, index)

    def build_cluster(self, cluster):
        pre = create_group(cluster + "Pre", self.name+"Clusters")
        cmds.xform(pre, ws=1, m=self.clusters[cluster])
        joint = create_node("joint", cluster + "Cluster", pre)
        cmds.setAttr(joint+".v", 0)
        cmds.setAttr(joint+".radius", 0.05)

    def build_clusters(self):
        # Static簇，完全不动的簇，每个layer中，cluster未用到的权重，都会给Static
        self.add_cluster(self.name+"Static", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        list(map(self.build_cluster, self.clusters.keys()))

    def get_layer_names(self):
        return list(sorted(set(self.layers.values())))

    def build_layers(self):
        if cmds.objExists(self.name+"Plane_uvPin"):
            cmds.delete(self.name+"Plane_uvPin")
        matrices = [self.pin_matrices[pin] for pin in self.pins]
        layers = []
        for layer in self.get_layer_names():
            layer = create_group(self.name+layer+"Layer", self.name+"Layers")
            create_polygon_by_matrices(layer, matrices)
            layers.append(layer)
        plane = create_group(self.plane_name(), self.name+"s")
        cmds.setAttr(plane+".v", 0)
        create_polygon_by_matrices(plane, matrices)
        if not matrices:
            return
        bs.add_real_targets(layers, plane)

    def build_layer_skin(self, layer):
        clusters = sorted([cluster for cluster, _layer in self.layers.items()
                           if layer == _layer and cluster != "Static"])
        weights = [[self.weights.get(cluster, dict()).get(pin, 0.0) for cluster in clusters] for pin in self.pins]
        for ws in weights:
            # 1-所有簇权重之和=静态骨骼的权重
            ws.append(max(1.0-sum(ws), 0))
            sum_ws = sum(ws)
            # 归一化，所有权重之和等于1
            for i, w in enumerate(ws):
                ws[i] /= sum_ws
        # 每个pin对应三个点，pin权重复制三分为模型权重
        weights = sum(sum([[ws]*4 for ws in weights], []), [])
        clusters += [self.name+"Static"]
        joints = [name+"Cluster" for name in clusters]
        plane = self.name+layer+"Layer"
        if not self.pins:
            return
        create_skin(joints, plane, weights)

    def build_layer_skins(self):
        list(map(self.build_layer_skin, self.get_layer_names()))

    def build_blend_shape(self):
        plane = self.name + "Plane"
        targets_id_points = {}
        for target, pin_points in self.points.items():
            id_points = {}
            for i, pin in enumerate(self.pins):
                if pin not in pin_points:
                    continue
                for j, point in pin_points[pin].items():
                    j = int(j)
                    vtx_id = i*4+j
                    id_points[vtx_id] = point
            if not id_points:
                continue
            targets_id_points[target] = id_points
        bs.set_targets_id_points(plane, targets_id_points)
        _bs = bs.find_bs(plane)
        for target in targets_id_points.keys():
            set_attr(_bs+"."+target, 0)
        bs.set_target_drivers(plane, self.drivers)

    def build(self):
        if not self.pins:
            root = self.name + "s"
            if cmds.objExists(root):
                cmds.delete(root)
            return
        self.build_root()
        self.build_layers()
        self.build_clusters()
        self.build_layer_skins()
        self.build_blend_shape()
        if self.body:
            self.build_follow()
        self.build_pins()
        if self.body:
            self.build_driver()
        self.clear_useless()

    def remove_pin(self, pin):
        if pin in self.pins:
            self.pins.remove(pin)
        if pin in self.pin_matrices:
            self.pin_matrices.pop(pin)

    def remove_cluster(self, cluster):
        if cluster in self.clusters:
            self.clusters.pop(cluster)
        if cluster in self.weights:
            self.weights.pop(cluster)
        if cluster in self.layers:
            self.layers.pop(cluster)

    def clear_useless(self):
        def clear_useless_by_root_filter(root, filter_fun, names):
            for node in get_children(root):
                if not filter_fun(node):
                    cmds.delete(node)
                    continue
                if node not in names:
                    cmds.delete(node)
        pin_names = set([pin+"Pin" for pin in self.pins])
        clear_useless_by_root_filter(self.name + "Pins", self.is_pin, pin_names)
        layer_names = set([self.name+layer+"Layer" for layer in self.get_layer_names()])
        clear_useless_by_root_filter(self.name + "Layers", self.is_layer, layer_names)
        cluster_names = set([cluster+"Pre" for cluster in self.clusters])
        cluster_names.add(self.name+"StaticPre")
        clear_useless_by_root_filter(self.name + "Clusters", self.is_cluster, cluster_names)

    def build_target(self, find_joint):
        matrices = []
        for pin in self.pins:
            joint = find_joint(pin)
            if cmds.objExists(joint):
                matrices.append(cmds.xform(joint, q=1, ws=1, m=1))
            else:
                matrices.append(self.pin_matrices[pin])
        target = create_group(self.name + "Target", self.name + "s")
        create_polygon_by_matrices(target, matrices)
        cmds.setAttr(target+".v", 0)
        return target

    def update_weights(self, weights):
        for cluster, pin_weights in weights.items():
            if cluster not in self.clusters:
                continue
            for pin, value in pin_weights.items():
                if pin not in self.pins:
                    continue
                self.weights[cluster][pin] = value

    def update_points(self, points):
        for target, pin_points in points.items():
            for pin, id_points in pin_points.items():
                if pin not in self.pins:
                    continue
                id_points = {int(k): v for k, v in id_points.items()}
                self.points.setdefault(target, dict())[pin] = id_points

    def update_drivers(self, drivers):
        self.drivers.update(drivers)

    def build_driver(self, find_joint=str):
        matrices = [self.pin_matrices[pin] for pin in self.pins]
        driver = self.driver_name()
        create_group(driver, self.name+"s")
        create_polygon_by_matrices(driver, matrices)
        joints = [find_joint(pin) for pin in self.pins]
        weights = [[0.0]*len(joints) for _ in range(len(joints))]
        for i, ws in enumerate(weights):
            ws[i] = 1.0
        weights = sum(sum([[ws]*4 for ws in weights], []), [])
        create_skin(joints, driver, weights)
        cmds.setAttr(driver+".inheritsTransform", 0)
        cmds.setAttr(driver + ".v", 0)

    def build_follow(self):
        clusters = list(sorted(self.follows.keys()))
        weights = [[self.follows.get(cluster, dict()).get(pin, 0.0) for cluster in clusters] for pin in self.pins]
        for i, ws in enumerate(weights):
            # 1-所有簇权重之和=静态骨骼的权重
            sum_ws = sum(ws)
            if sum_ws < 1e-8:
                ws = [0.0]*len(ws)
                ws.append(1.0)
            else:
                ws = [w/sum_ws for w in ws]
                ws.append(0)
            weights[i] = ws
        # 每个pin对应四个个点，pin权重复制四分为模型权重
        weights = sum(sum([[ws]*4 for ws in weights], []), [])
        self.add_cluster(self.name+"Static", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
        self.build_cluster(self.name+"Static")
        clusters += [self.name+"StaticCluster"]
        plane = self.plane_name()
        create_skin(clusters, plane, weights)

    def load_follow(self):
        plane = self.plane_name()
        if not cmds.objExists(plane):
            return
        clusters = get_skin_joints(plane)
        if not clusters:
            return
        joint_count = len(clusters)
        weights = get_weights(plane)
        weights = [weights[i:i+joint_count] for i in range(0, len(weights), joint_count)]
        weights = [weights[i] for i in range(0, len(weights), 4)]
        for cluster, ws in zip(clusters, zip(*weights)):
            if cluster == self.name+"StaticCluster":
                continue
            for w, pin in zip(ws, self.pins):
                self.set_follow(cluster, pin, w)

    def plane_name(self):
        return self.name + "Plane"

    def driver_name(self):
        return self.name + "Driver"

    def get_all_data(self):
        self.load()
        keys = ["pins", "pin_matrices", "clusters", "layers", "weights", "points", "drivers", "follows"]
        return {key: getattr(self, key) for key in keys}

    def update_data(self, data):
        m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        for pin in data.get("pins", []):
            self.add_pin(pin, data.get("pin_matrices", {}).get(pin, m))
        for cluster, matrix in data.get("clusters", dict()).items():
            self.add_cluster(cluster, matrix)
        for cluster, layer in data.get("layers", dict()).items():
            self.set_layer(layer, cluster)
        for cluster, pin_weight in data.get("weights", dict()).items():
            for pin, weight in pin_weight.items():
                self.set_weight(cluster, pin, weight)
        for target, pin_point in data.get("points", dict()).items():
            for pin, id_points in pin_point.items():
                self.points.setdefault(target, dict()).setdefault(pin, id_points)
        self.drivers.update(data.get("drivers", dict()))
        for cluster, pin_weight in data.get("follows", dict()).items():
            for pin, weight in pin_weight.items():
                self.set_follow(cluster, pin, weight)
