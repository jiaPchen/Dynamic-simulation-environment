# 阶段二 TruckSim-Simulink-Python 闭环联仿

本文件夹是三轴车辆项目的阶段二：MATLAB 启动 Simulink 与 Python TCP 服务；Python 根据零质心侧偏角控制律，将 TXT 中的第一轴转向激励分配为三轴六轮转角，TruckSim 计算车辆动力学响应，随后自动归档 CSV、曲线与 Word 报告。

## 从哪里开始

- `03_换机配置与AI交接说明.md`：换机、路径定位、运行顺序和数据写入边界。
- `02_阶段二仿真测试系统框架与运行指南.md`：系统流程、用例、产物和故障定位。
- `01_阶段二仿真测试系统全景梳理.md`：模块关系、数据链路、结果边界和维护重点。
- `01_一键启动脚本/run_local_preflight.m`：不启动仿真、不修改 TruckSim 数据，检查 Python 依赖、solver、专用入口、固定端口和模型的本机预检。

## 目录概览

```text
00_simulink/                 Simulink 联仿模型与 TCP Client S-Function
01_一键启动脚本/             单工况、批量、预检与 CSV 导出入口
02_测试用例/                 阶跃、正弦 TXT 用例
03_数据存储/Python联仿/      单工况 CSV、用例快照和 Python 日志
04_测试报告/                 曲线、单工况 Word 与批量总报告
05_python_controller/        控制器、TCP 服务、TruckSim 配置与报告程序
  requirements.txt           当前 Python 3.10.4 环境已验证的核心依赖版本
runtime/                     阶段二专用simfile路径记录与来源记录，不是Python运行库
```

## 本机关键环境

```text
Python:            C:\Python\python\python3.10.4\python.exe
TruckSim solver:   C:\Trucksim2019\TruckSim2019.0_Prog\Programs\solvers
TruckSim源simfile: C:\Trucksim2019\TruckSim2019.0_Data\simfile.sim（发送到Simulink后产生）
项目路径记录:    runtime\trucksim_phase2.path（指向数据目录中的simfile_phase2.sim）
TCP:               127.0.0.1:50007
```

项目内路径由脚本根目录组合；换电脑时核对Python和solver。选择阶段二Run并“发送到Simulink”后，运行`capture_phase2_simfile`，它会在TruckSim数据目录保存专用`simfile_phase2.sim`并在项目内记录路径；MATLAB和YAML会自动共同使用它。不要与阶段一共用同一个Run。

## 当前电脑的运行记录

截至 2026-09-25，`02_测试用例/` 有 2 个正弦、2 个阶跃常规用例。`run_case_python.m` 默认选用其中的 `step_steer_python_40kmh.txt`；`run_batch_python` 按文件名顺序运行目录内全部 4 个 TXT。当前保留的 2026-09-25 14:38 批量报告中，4 个工况均为 `COMPLETED`、`execution_status=PASS`，采样周期为 0.01 s；对应日志均有 `CONFIG_READY`、`HANDSHAKE_OK`、`STOP_OK`、`SERVER_STOPPED`。同一时间的第 042 次单工况也有 CSV、曲线和 Word 报告。这些是当前电脑当次运行的证据，不保证复制到新电脑后无需重新预检和试跑。

非零坡度、起伏路面和 TruckSim COM 实测不是《项目推进(1).docx》阶段二的必验项；相关配置或离线测试不能代替真实车辆响应验证。需要扩展验证时参阅运行指南，勿把扩展用例直接放进常规批量目录。

## 报告中的状态怎么理解

- `run_status=COMPLETED`：MATLAB编排流程完成并保存了运行产物。
- `execution_status=PASS/FAIL`：报告程序检查运行状态、时间轴、必需信号、TCP生命周期和TruckSim配置是否完整。
- `acceptance_status=NOT_EVALUATED`：当前尚未为控制效果规定统一阈值，因此车速偏差、质心侧偏角、横摆角速度和各轴转角只展示指标，不擅自判定控制性能PASS/FAIL。

“运行完整性PASS”不等于“控制性能验收通过”。后续只有在测试用例明确给出评价指标和阈值后，才能启用控制性能PASS/FAIL。

## 日常顺序

在 MATLAB 中先执行：

```matlab
cd(fullfile(pwd, '01_一键启动脚本')) % 当前目录为阶段二项目根目录时使用
run_local_preflight
```

确认 TruckSim Run、备份和写入许可后，可执行 `run_case_python` 运行默认 40 km/h 阶跃工况；如需其他工况，先修改脚本中的 `caseFile` 文件名。也可执行多工况仿真 `run_batch_python`。
