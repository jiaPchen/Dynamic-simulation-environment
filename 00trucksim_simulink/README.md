# 阶段一 TruckSim Simulink 一键测试项目

本文件夹是阶段一的三轴车辆 TruckSim + Simulink 联合仿真基线。它通过 MATLAB 脚本读取 TXT 用例、配置当前 TruckSim 工况、生成第一轴转向输入，运行 TruckSim S-Function，并自动导出 CSV、曲线和 Word 测试报告。

它与同级 `01_trucksim_simulink_python/` 的阶段二不同：阶段一没有 Python TCP 闭环控制，第二、第三轴转角固定为 0 度；Python 只负责报告生成。

请优先阅读：

- `阶段一仿真测试系统框架与运行指南.md`：运行、验收、产物与排错。
- `阶段一仿真测试系统全景梳理.md`：模块关系、数据流、已验证结果与边界。
- `换机配置与AI交接说明.md`：把项目交给另一台电脑或 AI 时的环境信息、共享外部状态和改动范围。
- `联合仿真一键测试项目说明.docx`：面向使用者的项目总说明，已同步当前流程和最近验证情况。

本机已配置：项目内模型、用例和数据目录均由入口脚本相对定位；Python 为 `C:\Python\python\python3.10.4\python.exe`；TruckSim solver 与 `simfile.sim` 位于 `C:\Trucksim2019`。入口默认严格按 TXT 配置 TruckSim，并在导出前验证实际时长、初始车速和第一轴转向；任一不符则不会归档为 CSV/报告。运行编号已改为跨“阶跃输入转角”和“正弦输入转角”统一递增，当前最大编号为第017次，下次将为第018次。
