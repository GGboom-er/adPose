# coding:utf-8
"""
bs_api 初始化模块
自动选择 C++ DLL 后端或 NumPy 纯 Python 后端
"""
try:
    from importlib import reload
except ImportError:
    pass

_USE_CPP = False

try:
    from . import c_bs_api
    reload(c_bs_api)
    from . import bs_api
    reload(bs_api)
    _USE_CPP = True
except (OSError, ImportError, Exception) as e:
    # DLL 加载失败（文件不存在、架构不匹配、依赖缺失等）
    # 降级到 NumPy 后端
    import warnings
    warnings.warn(
        "[adPose] C++ backend (bs_api.dll) failed to load: {}\n"
        "         Falling back to NumPy backend (slower but functional).".format(e)
    )
    from . import np_bs_api as c_bs_api
    # 创建兼容的 bs_api 模块
    from . import np_bs_api
    from . import _np_bs_api_compat
    reload(_np_bs_api_compat)
    from . import _np_bs_api_compat as bs_api
