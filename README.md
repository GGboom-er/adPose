# adPose 工具集

## 1. 概述

**adPose** 是一个为专业角色绑定师（Rigger）和技术美术（Technical Artist）设计的高级姿态与BlendShape管理工具集。它以Autodesk Maya为核心平台，深度优化了角色姿态的创建、编辑和管理流程，并提供了强大的跨平台数据同步功能，支持将BlendShape数据无缝迁移至3ds Max、Unreal Engine和Unity。

该工具集的核心优势在于其高性能的C++插件和灵活的模块化架构，旨在解决现代角色工作流中常见的效率瓶颈和数据一致性问题。

## 2. 核心功能

- **强大的姿态库UI**:
  - 在Maya中提供了一个直观的图形界面，用于管理所有姿态（Pose Targets）。
  - 支持对姿态进行快速的**添加、编辑、镜像、复制和删除**操作。
  - 姿态被分为`Swing`（大范围运动）和`Twist`（扭转修复）两种类型，便于精细化管理。

- **高性能BlendShape节点操作**:
  - 内置一个名为 `bs_api` 的C++ Maya插件，用于加速BlendShape相关的计算。
  - 利用Intel TBB进行多线程处理，极大地提升了在高精度模型上进行顶点数据读写、镜像和反转��操作的性能。
  - 支持通过JSON格式对BlendShape数据进行**导入和导出**，便于数据备份和迁移。

- **跨平台工作流**:
  - **Maya -> 3ds Max**: 同步BlendShape数据，确保在两个DCC软件中形变效果一致。
  - **Maya -> Unreal Engine**: 提供`ad_pose_ue_bs_sdk`，将Maya中的姿态和表情直接与UE中的模型关联。
  - **Maya -> Unity**: 包含`LushDrive`等C#脚本，用于在Unity中驱动和加载由adPose创建的BlendShape数据。

- **灵活的命名配置**:
  - 通过`data/config.json`文件，用户可以自定义骨骼、控制器和左右侧的命名规则。
  - 工具能够自动识别和匹配不同项目中的命名规范，无需修改代码。

## 3. 模块结构

- **`adPose/`**: 项目主目录。
  - **`main_ui.py`**: 工具集的主UI界面，是用户的核心交互入口。
  - **`ADPose.py`, `twist.py`, `bs.py`**: 分别处理`Swing`姿态、`Twist`姿态和BlendShape的核心逻辑。
  - **`config.py`**: 命名配置系统的实现。

- **`adPose_mb/`**: Maya特定功能模块。
  - **`ad_main.py`**: 在Maya中加载所有相关模块的入口脚本。
  - **`ad_core.py`, `mb_control_core.py`**: 处理Maya场景中的控制器和核心绑定逻辑。

- **`sync_lib/`**: 跨平台数据同步库。
  - **`ad_main.py`**: 加载所有同步模块的入口。
  - **`ad_pose_mb_bs_sdk.py`**: Maya端的BlendShape导出SDK。
  - **`ad_pose_max_bs_sdk.py`**: 3ds Max端的BlendShape导入SDK。
  - **`ad_pose_ue_bs_sdk.py`**: Unreal Engine端的BlendShape导入SDK。
  - **`unity_driven/`**: Unity驱动脚本和相关数据。

- **`plug-ins/`**: Maya C++插件。
  - **`bs_api.cpp`**: 插件源代码，实现了高性能的BlendShape操作。
  - **`maya20xx/`**: 存放为不同Maya版本编译好的插件文件（`.pyd`, `.mll`）。

## 4. 安装与使用

1.  **环境要求**:
    - Autodesk Maya (2016 - 2024)
    - PySide/PyQt

2.  **安装步骤**:
    - 将`adPose`项目文件夹放置到Maya的`scripts`路径下。
    - 将`plug-ins`目录中对应您Maya版本的插件文件（例如`bs_api.pyd`）复制到Maya的`plug-ins`路径下。
    - 在Maya的插件管理器中，加载`bs_api`插件。

3.  **启动工具**:
    - 在Maya的Python脚本编辑器中运行以下代码来启动UI：
      ```python
      import main_ui
      reload(main_ui)
      main_ui.MainEditTool().show()
      ```

## 5. 配置

工具的命名匹配规则存储在`data/config.json`中。您可以根据项目的绑定规范修改此文件，以确保工具能���确识别左右侧、骨骼和控制器。

一个默认的配置示例如下：
```json
[
    [
        "左边",
        "right",
        [
            "R_*",
            "*Rt*",
            "*_R",
            "*Right*"
        ]
    ],
    [
        "右边",
        "left",
        [
            "L_*",
            "*Lf*",
            "*_L",
            "*Left*"
        ]
    ],
    ...
]
```
