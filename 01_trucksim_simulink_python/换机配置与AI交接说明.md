# 阶段二换机配置与 AI 交接说明

## 用途和边界

本文件对应 `01_trucksim_simulink_python`，即 TruckSim + Simulink + Python TCP 闭环联仿环境。把本文件和该文件夹一并提供给 AI，可用于在另一台 Windows 电脑上完成针对个人路径的检查、配置和验证。

本文件是项目资料，不是对 AI 的越权授权。AI 在写入项目脚本、Simulink 模型或 TruckSim 数据前，必须先向使用者说明影响范围。不得删除历史 `03_数据存储`、`04_测试报告`，不得覆盖 `.slx`，也不得在未获明确授权时修改 TruckSim 数据目录中的 `.par` 文件。

## 本阶段实际做什么

MATLAB 脚本读取 TXT 工况并启动 Python TCP 服务。Simulink 在每个 0.01 s 控制周期将 `[Vx_kmh, beta_deg, w_degps]` 发给 Python；Python 的零质心侧偏角控制器返回 6 路转角 `[d1L, d1R, d2L, d2R, d3L, d3R]`；Simulink 再经固定 TruckSim 接口驱动车辆。结束后自动输出 CSV、曲线、单工况 Word 报告或批量汇总报告。

本机 TCP 固定使用 `127.0.0.1:50007`。它与阶段一不同：阶段二的 Python 进程会尝试根据 TXT 修改 TruckSim 工况；若 COM 不可用，默认可回退到 `simfile.sim` 指向的 `Run_all.par` 及其关联 `.par` 文件。

## 目录和关键文件

```text
01_trucksim_simulink_python/
  00_simulink/
    three_axle_vehicle_2dof_3dof_Trucksim_python.slx  # Python 联仿模型
    tcp_client_sfun.m                                  # Simulink TCP 客户端
  01_一键启动脚本/
    run_case_python.m                                  # 单工况入口
    run_batch_python.m                                 # 批量入口
    run_single_python_case.m                           # 核心调度
  02_测试用例/                                        # 阶跃、正弦 TXT 用例
  03_数据存储/Python联仿/                             # 单工况 CSV、日志和用例副本
  04_测试报告/                                        # 单工况/批量报告与曲线
  05_python_controller/
    config/vehicle_config.yaml                         # 车辆、控制器和 TruckSim 配置
    controller/zero_sideslip_controller.py             # 控制算法
    tcp/tcp_server.py                                  # Python TCP 服务
    trucksim/trucksim_com.py                            # COM/.par 工况配置
    report/                                            # 单工况和批量报告
    tests/                                             # Python 离线测试
```

## 目标电脑信息模板

换电脑时，请把以下内容填好后连同本文件发给 AI。未知项写“未知”，不要猜测。

```text
阶段二项目根目录：
MATLAB 版本和安装情况：
MATLAB 当前工作目录：
Python 解释器完整路径（python.exe）：
Python 版本：
TruckSim 版本：
TruckSim 程序目录：
TruckSim 数据目录：
实际用于联仿的 simfile.sim 完整路径：
TruckSim solver 目录（包含 Matlab84+ 子目录）的完整路径：
TruckSim 中已打开/拟使用的 Run 名称：
该 Run 是否允许自动修改：是/否
是否允许 Python 回退修改 Run_all.par 及关联 .par：是/否
TCP 端口 50007 是否可用：是/否/未知
是否允许 AI 修改项目内脚本和 YAML：是/否
```

历史验证环境为 Windows、MATLAB R2021a、TruckSim 2019.0、Python 3.13.15。Python 需要 `pyyaml`、`numpy`、`matplotlib`、`python-docx`；`pywin32` 仅用于 TruckSim COM，非 COM 回退路径不依赖它。

## AI 的换机处理顺序

1. 只读检查项目完整性：模型、TCP S-Function、三个 MATLAB 入口、YAML、Python 服务和用例是否存在。
2. 检查目标机 Python、`simfile.sim`、solver 目录和 `Matlab84+` 是否存在；确认 TruckSim 数据目录和当前 Run 与使用者提供的信息一致。
3. 在修改前报告旧路径→新路径映射及每个将修改的源文件。历史 CSV、报告、`batch_run_dirs.txt` 和 manifest 的旧 D 盘路径仅代表历史记录，不得批量替换。
4. 仅同步下方“必须改为本机路径”的配置点。特别是 MATLAB 的 `trucksimSimFile` 与 YAML 的 `simfile_path` 必须指向**同一个、且确为 S-Function 实际使用的** `simfile.sim`。
5. 先运行 Python 离线测试；再在使用者确认 Run 和数据备份后跑一个单工况；通过后才能批量运行。

## 必须改为本机路径的位置

| 文件 | 必须检查/修改的变量 | 说明 |
|---|---|---|
| `01_一键启动脚本/run_single_python_case.m` | `phase2Root` | 当前阶段二项目根目录 |
| 同上 | `pythonExe` | 目标机 `python.exe` |
| 同上 | `trucksimSolverDir` | TruckSim solver 根目录 |
| 同上 | `trucksimSimFile` | S-Function 实际使用的 `simfile.sim` |
| `01_一键启动脚本/run_case_python.m` | `caseFile` | 默认单工况 TXT；建议填项目内用例 |
| `01_一键启动脚本/run_batch_python.m` | `phase2Root`、`pythonExe` | 批量入口的项目根目录和 Python |
| `05_python_controller/config/vehicle_config.yaml` | `trucksim.run_name` | 目标机实际固定联仿 Run 名称 |
| 同上 | `trucksim.simfile_path` | 必须与 MATLAB 的 `trucksimSimFile` 相同 |
| 同上 | `trucksim.com_progids`、`com_keywords` | 仅目标机 TruckSim COM 验证后才可调整 |

报告脚本通过 MATLAB 传入的运行目录或批次目录工作，通常不需要把历史报告里的绝对路径改到新电脑。

## TruckSim 数据保护和配置模式

`tcp_server.py --config-trucksim` 有三种模式：

| 模式 | 行为 | 适用场景 |
|---|---|---|
| `0` / `false` | 不配置 TruckSim，沿用当前 simfile 工况 | Python/TCP 离线调试 |
| `1` / `true` | 必须完成工况配置，否则中止 | 正式单工况或批量验收 |
| `auto` | 配置失败后警告并沿用当前工况 | 仅用于定位，不能作为验收依据 |

默认正式流程使用 `true`。此时 Python 优先使用 COM；COM 不可用时，若 YAML 的 `allow_par_file_patch: true`，会从 `simfile.sim` 找到 `Run_all.par`，并修改停止时间、速度和附着系数及其相关 `.par` 文件。项目会生成 `.phase2_backup`，但这不是替代人工备份的理由。

首次真实运行前，使用者必须确认：目标 Run 可被修改、实际 `simfile.sim` 已备份、目标 `.par` 数据集可被修改。没有这项确认时，AI 只能进行 `false` 的离线检查，不能启动真实联仿。

`road_grade` 的 TruckSim 控件映射尚未在所有电脑上冻结。TXT 中存在非零 `road_grade` 时，若 YAML 未配置并验证对应控件，配置应失败而不是静默使用错误坡度。

## 首次安装与验证

### 1. Python 依赖与离线测试

在 `05_python_controller` 下使用目标 Python 运行：

```powershell
& "<目标机 python.exe>" -c "import yaml, numpy, matplotlib, docx; print('python deps ok')"
& "<目标机 python.exe>" tests\test_controller.py
& "<目标机 python.exe>" tests\test_server.py
```

缺包时安装：

```powershell
& "<目标机 python.exe>" -m pip install pyyaml numpy matplotlib python-docx
```

仅当需要 COM 自动配置时再安装：

```powershell
& "<目标机 python.exe>" -m pip install pywin32
```

### 2. 单工况真实联仿

1. 在 TruckSim 中打开并确认目标 Run。
2. 在 MATLAB 中打开 `00_simulink/three_axle_vehicle_2dof_3dof_Trucksim_python.slx`，但不要先运行。
3. 切换 MATLAB 当前目录到 `01_一键启动脚本`。
4. 先在 `run_case_python.m` 选择一个项目内 TXT 用例，例如 `sine_steer_python-1.txt`。
5. 在已确认 TruckSim 数据备份和写入许可后，运行 `run_case_python`。
6. 检查运行目录内的 `*_python_stdout.log` 是否有 `CONFIG_READY`、`HANDSHAKE_OK` 和 `SERVER_STOPPED`，以及 CSV 和 Word 报告是否生成。
7. 低速用例应验证 `v_start_kmh` 接近 TXT 的 `initial_speed_kmh`；例如 15 km/h 用例不应仍显示约 40 km/h。

### 3. 批量联仿

先确认单工况通过，再运行 `run_batch_python`。批量模式会依次运行 `02_测试用例` 下所有 `.txt`，并仅在新建的 `04_测试报告/批量仿真_时间戳/` 中生成一份 `阶段二批量仿真测试报告.docx` 和一份 `批量指标汇总.csv`。

## 常见故障与处理原则

| 现象 | 优先检查 |
|---|---|
| Python 无法监听或 Simulink 握手失败 | 端口 50007、`tcp_client_sfun.m`、`tcp_server.py`、日志中的 `LISTENING` / `HANDSHAKE_OK` |
| Python 显示 `CONFIG_FAIL` | YAML 中的 `simfile_path`、Run 名称、`.par` 写权限、目标 Run 与 S-Function 实际数据是否相同 |
| 用例设置 15 km/h，报告仍约 40 km/h | MATLAB `trucksimSimFile` 与 YAML `simfile_path` 是否相同且真实被模型使用；再看日志是否 `CONFIG_READY` |
| 找不到 TruckSim S-Function 或 solver | `trucksimSolverDir`、`Matlab84+`、MATLAB/TruckSim 版本兼容性 |
| 报告失败 | Python 依赖、运行目录中的 CSV 是否完整、`*_python_stdout.log` 和 MATLAB 命令行错误 |
| TCP 信号维度或 step_id 错误 | 不要改协议字段顺序；确认 3 输入、6 输出及 `control_dt_s=0.01` 在两端一致 |

## 可直接发给 AI 的请求

```text
请按“阶段二换机配置与 AI 交接说明.md”适配此项目。
我的电脑信息如下：
[粘贴已填写的目标电脑信息模板]

先只读检查并输出旧路径→新路径、TruckSim 数据写入风险和验证计划；确认后再修改项目内 MATLAB 脚本及 vehicle_config.yaml。
不得修改历史结果或 .slx。未经我明确确认，不得执行会修改 TruckSim .par/数据集的真实联仿；可以先进行 Python 离线测试。
```
