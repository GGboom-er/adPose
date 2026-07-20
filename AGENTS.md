# adPose · AI 协作入口

@Y:/GGbommer/scripts/Notes/AGENTS.md

## 项目边界

- 用途：Maya 角色姿态修型、BlendShape 编辑与骨骼局部角度驱动。
- 当前目标环境：Maya 2025、Python 3、PySide6。
- 项目真相源：本仓 `README.md`、源码和 `tests/maya_smoke.py`。
- 大脑项目卡：`Y:/GGbommer/scripts/Notes/ai/projects/adpose.md`。
- 大脑工具卡：`Y:/GGbommer/scripts/Notes/Tools/adPose/adPose.md`。

## 开工规则

1. 先读 README 的“已验证范围”和“未承诺范围”。
2. Maya 场景操作必须通过 CGI Pipeline MCP 的前台会话执行，不直接裸连 commandPort。
3. 生产驱动读取骨骼；控制器矩阵只用于保存和回放姿态。
4. 修改后至少运行 `py_compile`、当前场景 smoke 和对应用户入口。
5. 不保存用户生产场景；需要保存时单独取得路径和版本授权。
