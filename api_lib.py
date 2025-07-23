import pymel.core as pm
import os
import sys

use_default = False

version = int(round(float(pm.about(q=1, v=1))))
pyd_path = os.path.abspath(__file__+"/../plug-ins/maya%i" % version).replace("\\", "/")
py_path = os.path.abspath(__file__+"/../plug-ins/maya%s" % "default").replace("\\", "/")
if version == 2022:
    if sys.version[0] == "2":
        pyd_path = os.path.abspath(__file__ + "/../cores/maya%i_2" % version).replace("\\", "/")
if os.path.exists(pyd_path):
    path = pyd_path
else:
    path = py_path

if use_default:
    if path in sys.path:
        sys.path.remove(path)
    path = py_path

if path not in sys.path:
    sys.path.insert(0, path)


import bs_api


