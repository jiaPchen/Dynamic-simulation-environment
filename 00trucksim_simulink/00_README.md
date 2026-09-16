# 阶段一 TruckSim Simulink 一键测试项目

本文件夹是阶段一的三轴车辆 TruckSim + Simulink 联合仿真基线。它通过 MATLAB 脚本读取 TXT 用例、配置当前 TruckSim 工况、生成第一轴转向输入，运行 TruckSim S-Function，并自动导出 CSV、曲线和 Word 测试报告。

本项目采用单轴开环转向：第一轴按 TXT 用例生成转角，第二、第三轴转角固定为 0 度；Python 仅用于生成曲线和测试报告。

请优先阅读：

- `01_阶段一仿真测试系统全景梳理.md`：模块关系和数据流。
- `02_阶段一仿真测试系统框架与运行指南.md`：运行、验收、产物与排错。
- `03_换机配置与AI交接说明.md`：换电脑或交给 AI 配置时使用。

本机已配置：项目内模型、用例和数据目录均由入口脚本相对定位；Python 为 `C:\Python\python\python3.10.4\python.exe`；TruckSim solver 与 `simfile.sim` 位于 `C:\Trucksim2019`。入口默认严格按 TXT 配置 TruckSim，并在导出前验证实际时长、初始车速和第一轴转向；任一不符则不会归档为 CSV/报告。运行编号跨阶跃与正弦用例统一递增。
