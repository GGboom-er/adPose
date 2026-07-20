from maya import cmds


def create_node(typ, name, parent=None):
    if cmds.objExists(name):
        return name
    if parent is not None:
        return cmds.createNode(typ, n=name, p=parent, ss=True)
    else:
        return cmds.createNode(typ, n=name, ss=True)


def connect_attr(src, dst):
    if cmds.isConnected(src, dst):
        return
    cmds.connectAttr(src, dst, f=1)


def get_orig(polygon):
    orig_list = [shape for shape in cmds.listRelatives(polygon, s=1, f=1) or [] if cmds.getAttr(shape+'.io')]
    orig_list.sort(key=lambda x: len(list(set(cmds.listConnections(x, s=0, d=1, ) or []))))
    if orig_list:
        return orig_list[-1]
    else:
        return cmds.listRelatives(polygon, s=1)[0]


def create_uv_pin(plane):
    uv_pin = create_node("uvPin", plane + "_uvPin")
    mesh = cmds.listRelatives(plane, s=1)[0]
    orig = get_orig(plane)
    connect_attr(orig + ".outMesh", uv_pin + ".originalGeometry")
    connect_attr(mesh + ".worldMesh[0]", uv_pin + ".deformedGeometry")
    cmds.setAttr(uv_pin + ".normalAxis", 2)
    cmds.setAttr(uv_pin + ".tangentAxis", 3)
    return uv_pin


def get_uv(index):
    u_index = index // 100
    v_index = index % 100
    u = 0.01 * u_index + 0.005
    v = 0.01 * v_index + 0.005
    return u, v


def link_by_follicle(plane, follicle, u, v):
    shape = create_node("follicle", follicle+"Shape", follicle)
    cmds.setAttr(shape+".v", 0)
    cmds.setAttr(follicle+".parameterU", u)
    cmds.setAttr(follicle+".parameterV", v)
    connect_attr(plane+".outMesh", shape+".inputMesh")
    connect_attr(plane+".worldMatrix", shape+".inputWorldMatrix")
    connect_attr(shape + ".outTranslate", follicle + ".translate")
    connect_attr(shape + ".outRotate", follicle + ".rotate")
    return follicle


def link_by_uv_pin(plane, pin, index, u, v):
    uv_pin = create_uv_pin(plane)
    cmds.setAttr("{uv_pin}.coordinate[{index}].coordinateU".format(**locals()), u)
    cmds.setAttr("{uv_pin}.coordinate[{index}].coordinateV".format(**locals()), v)
    src = "{uv_pin}.outputMatrix[{index}]".format(**locals())
    cmds.setAttr(pin + ".r", 0, 0, 0)
    cmds.setAttr(pin + ".t", 0, 0, 0)
    connect_attr("{uv_pin}.outputMatrix[{index}]".format(**locals()), pin+".offsetParentMatrix")


def link_pin(plane, pin, index):
    u, v = get_uv(index)
    version = int(round(float(cmds.about(q=1, v=1))))
    if version >= 2020:
        link_by_uv_pin(plane, pin, index, u, v)
    else:
        link_by_follicle(plane, pin, u, v)
