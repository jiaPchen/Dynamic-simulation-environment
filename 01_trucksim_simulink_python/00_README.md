# 阶段二 TruckSim-Simulink-Python 闭环联仿

本文件夹是三轴车辆项目的阶段二：MATLAB 启动 Simulink 与 Python TCP 服务；Python 根据零质心侧偏角控制律，将 TXT 中的第一轴转向激励分配为三轴六轮转角，TruckSim 计算车辆动力学响应，随后自动归档 CSV、曲线与 Word 报告。

## 从哪里开始

- `阶段二联仿环境配置与运行说明_AI交接版.md`：换机、路径、运行顺序和风险的主交接文档。
- `换机配置与AI交接说明.md`：提供给 AI 的电脑信息模板与权限边界。
- `阶段二仿真测试系统框架与运行指南.md`：系统流程、用例、产物和故障定位。
- `阶段二仿真测试系统全景梳理.md`：模块关系、历史结果边界和维护重点。
- `01_一键启动脚本/run_local_preflight.m`：不启动仿真、不修改 TruckSim 数据的本机预检。

## 目录概览

```text
00_simulink/                 Simulink 联仿模型与 TCP Client S-Function
01_一键启动脚本/             单工况、批量、预检与 CSV 导出入口
02_测试用例/                 阶跃、正弦 TXT 用例
03_数据存储/Python联仿/      单工况 CSV、用例快照和 Python 日志
04_测试报告/                 曲线、单工况 Word 与批量总报告
05_python_controller/        控制器、TCP 服务、TruckSim 配置与报告程序
```

## 本机关键环境

```text
Python:            C:\Python\python\python3.10.4\python.exe
TruckSim solver:   C:\Trucksim2019\TruckSim2019.0_Prog\Programs\solvers
TruckSim simfile:  C:\Trucksim2019\TruckSim2019.0_Data\simfile.sim
TCP:               127.0.0.1:50007
```

项目内路径由脚本根目录组合；换电脑时仍须核对 Python、solver 和实际被 S-Function 使用的 `simfile.sim`，并让 MATLAB 的 `trucksimSimFile` 与 YAML 的 `trucksim.simfile_path` 保持一致。

## 日常顺序

在 MATLAB 中先执行：

```matlab
cd('C:\Users\ccc\Desktop\动力学仿真环境阶段二\01_trucksim_simulink_python\01_一键启动脚本')
run_local_preflight
```

确认 TruckSim Run、备份和写入许可后，再执行 `run_case_python`。单工况完整通过后才可执行 `run_batch_python`。项目会修改当前 TruckSim `.par` 数据，因此不得与另一套使用同一 Run 或同一 `simfile.sim` 的仿真实例并行运行。
