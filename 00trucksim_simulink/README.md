# 阶段一 TruckSim Simulink 一键测试项目

本文件夹是阶段一的三轴车辆 TruckSim + Simulink 联合仿真基线。它通过 MATLAB 脚本生成第一轴转向输入，运行 TruckSim S-Function，并自动导出 CSV、曲线和 Word 测试报告。

它与同级 `01_trucksim_simulink_python/` 的阶段二不同：阶段一没有 Python TCP 闭环控制，第二、第三轴转角固定为 0 度；Python 只负责报告生成。

请优先阅读：

- `阶段一仿真测试系统框架与运行指南.md`：运行、换机、产物与排错。
- `阶段一仿真测试系统全景梳理.md`：模块关系、数据流、现状与边界。
- `换机配置与AI交接说明.md`：把项目交给另一台电脑或 AI 时的环境信息与改动范围。

当前 `run_case_new.m` 仍保留原电脑的 `D:\动力学仿真环境`、`D:\04_trucksim` 和 `D:\05_python` 路径；在本电脑首次运行前必须按交接说明更新路径，并保持 `useTrucksimCom = false`。

