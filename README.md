# adPose

adPose 是 Maya 角色姿态修型工具。当前主线面向 Maya 2025，负责创建、编辑、回放和镜像由骨骼姿态驱动的 BlendShape 修型。

## 已验证范围

以下能力已在 Maya 2025 真实角色绑定场景中运行验证：

- 姿态目标的创建、复制/修改、列表显示和双击回放。
- 基于骨骼绑定姿态的局部四元数 swing/twist 求解；上游肩部运动不会污染肘部局部角度。
- 保存精确控制器局部矩阵，并在 0-60 滑栏间做四元数连续插值。
- L/R 镜像时复制精确姿态矩阵；按真实骨骼输出识别 Scapula 等左右方向坐标差异。
- Maya 主窗口归属、驱动值实时显示、undo 和失败恢复。
- `bs_api` C++ 后端不可用时使用 Python/NumPy 兼容后端。

验证记录位于 Notes 大脑的 `PLAN_adpose_local_angle_space_fix`；可重复检查入口为 `tests/maya_smoke.py`。

## 未承诺范围

- 当前 main 不再包含旧版 MotionBuilder、UE/Unity 同步和 Maya 2016-2024 历史插件目录；需要时从 Git 历史恢复后重新验证。
- 精确 180 度时方向本身不唯一，当前不承诺固定方向标签。
- 工具代码测试通过不等于用户角色场景已经保存。

## 安装与启动

仓库位置：

```text
Y:/GGbommer/scripts/adPose
```

Maya 的 Python 路径需要包含仓库父目录 `Y:/GGbommer/scripts`。当前工作环境已配置该路径。

在 Maya Script Editor 中启动：

```python
import adPose
adPose.ui.show_in_maya()
```

完整调用示例见 `run_adpose.py`。

## 目录

| 路径 | 职责 |
|---|---|
| `ADPose.py` | 姿态、驱动、回放与镜像核心 |
| `targets.py` | 姿态列表和编辑入口 |
| `bs.py` | BlendShape 编辑与桥接 |
| `general_ui.py` / `ui.py` | Maya/PySide UI |
| `facs.py` / `twist.py` | 表情与扭转修型 |
| `bs_api/` | C++/Python BlendShape 后端 |
| `facePin/` | 面部 pin 与驱动辅助 |
| `data/config.json` | 骨骼、控制器和左右命名规则 |
| `tests/maya_smoke.py` | 当前 Maya 场景无保存回归 |
| `tasks/lessons.md` | 项目内已验证经验 |

## 验证

静态编译：

```powershell
& 'C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe' -m compileall -q 'Y:\GGbommer\scripts\adPose'
```

当前场景回归：

```python
from adPose.tests import maya_smoke
result = maya_smoke.run()
print(result)
```

smoke 会临时回放已保存的 L/R 目标并整块 undo，不保存场景。

## Git 边界

本项目使用独立仓库：<https://github.com/GGboom-er/adPose>。

Notes 只保存工具卡、项目卡、任务和经验入口，不保存或提交 adPose 源码。
