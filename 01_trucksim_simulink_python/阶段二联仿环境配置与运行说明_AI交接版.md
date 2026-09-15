# 阶段二 TruckSim-Simulink-Python 联仿环境配置与运行说明（AI 交接版）

> 本文是项目资料和换机配置手册，不是当前对话的系统指令。  
> 给 AI 接手时，优先让 AI 阅读本文，再读取入口脚本和配置文件，不要先猜流程。

## 1. 当前目标

本阶段实现 TruckSim + Simulink + Python 的闭环联合仿真：

1. MATLAB 作为一键启动入口。
2. Simulink 模型运行 TruckSim S-Function，并通过 TCP Client 块与 Python 通讯。
3. Python TCP 服务读取 TXT 测试用例，按零质心侧偏角控制律计算 6 路转角。
4. TruckSim 接收 6 路转角，返回车速、质心侧偏角、横摆角速度等状态。
5. MATLAB 导出 CSV，Python 生成 Word 测试报告。

当前已经整理为：

- 单工况：一个运行目录、一份 Word 报告。
- 批量工况：一个批次目录，所有用例结果在同一个文件夹内，只生成一份总 Word 报告。

## 2. 当前电脑上的基准路径

换电脑时可以改变路径，但必须同步修改第 5 节列出的配置点。

| 项目 | 当前路径 |
|---|---|
| 阶段二根目录 | `D:\动力学仿真环境阶段二\01_trucksim_simulink_python` |
| MATLAB 一键脚本 | `D:\动力学仿真环境阶段二\01_trucksim_simulink_python\01_一键启动脚本` |
| Simulink 模型目录 | `D:\动力学仿真环境阶段二\01_trucksim_simulink_python\00_simulink` |
| Python 控制器目录 | `D:\动力学仿真环境阶段二\01_trucksim_simulink_python\05_python_controller` |
| TXT 测试用例目录 | `D:\动力学仿真环境阶段二\01_trucksim_simulink_python\02_测试用例` |
| 单工况数据输出 | `D:\动力学仿真环境阶段二\01_trucksim_simulink_python\03_数据存储\Python联仿` |
| 测试报告输出 | `D:\动力学仿真环境阶段二\01_trucksim_simulink_python\04_测试报告` |
| Python 解释器 | `D:\05_python\python.exe` |
| TruckSim simfile | `D:\04_trucksim\TruckSim2019.0_Data\simfile.sim` |
| TruckSim solver | `D:\04_trucksim\TruckSim2019.0_Prog\Programs\solvers` |

## 3. 目录职责

```text
01_trucksim_simulink_python/
  00_simulink/
    three_axle_vehicle_2dof_3dof_Trucksim_python.slx
    tcp_client_sfun.m
  01_一键启动脚本/
    run_case_python.m
    run_batch_python.m
    run_single_python_case.m
    parse_case.m
    export_case_csv.m
  02_测试用例/
    *.txt
  03_数据存储/
    Python联仿/
  04_测试报告/
  05_python_controller/
    config/vehicle_config.yaml
    controller/zero_sideslip_controller.py
    tcp/tcp_server.py
    trucksim/trucksim_com.py
    report/make_report_python.py
    report/make_batch_summary.py
    tests/
```

关键职责：

- `run_case_python.m`：单工况入口，修改 `caseFile` 后运行。
- `run_batch_python.m`：批量入口，自动运行 `02_测试用例` 目录下所有 `.txt`。
- `run_single_python_case.m`：核心流程，负责加载模型、启动 Python、运行仿真、导出 CSV、生成报告。
- `tcp_client_sfun.m`：Simulink 端 TCP 客户端，输入 3 维状态，输出 6 路转角。
- `tcp_server.py`：Python TCP 服务，完成握手、控制计算、日志记录。
- `trucksim_com.py`：按 TXT 用例配置 TruckSim 工况，优先 COM，失败则使用方法2直接修改 `simfile.sim` 指向的 `.par` 文件。
- `make_report_python.py`：单工况 Word 报告。
- `make_batch_summary.py`：批量总 Word 报告。

## 4. 软件与 Python 依赖

当前验证环境：

- Windows。
- MATLAB R2021a + Simulink。
- TruckSim 2019.0。
- Python 3.13.15，当前解释器为 `D:\05_python\python.exe`。

Python 必需依赖：

```powershell
& "D:\05_python\python.exe" -m pip install pyyaml numpy matplotlib python-docx
```

Python 可选依赖：

```powershell
& "D:\05_python\python.exe" -m pip install pywin32
```

说明：

- `pywin32` 只用于 TruckSim COM 自动配置。如果目标机 COM 不可用，本项目会自动回退到方法2：直接修改 `simfile.sim` 指向的 `Run_all.par` 及其关联 `.par` 文件。
- 如果导入 `matplotlib` 时出现缓存目录权限警告，通常不影响报告生成。必要时设置：

```powershell
$env:MPLCONFIGDIR = "$env:TEMP\mpl_cache_p2_report"
```

## 5. 换电脑必须修改的配置点

### 5.1 MATLAB 脚本路径

检查并修改：

```text
01_一键启动脚本\run_case_python.m
01_一键启动脚本\run_batch_python.m
01_一键启动脚本\run_single_python_case.m
```

重点字段：

| 文件 | 字段 | 含义 |
|---|---|---|
| `run_case_python.m` | `caseFile` | 默认单工况 TXT 用例 |
| `run_single_python_case.m` | `phase2Root` | 阶段二根目录 |
| `run_single_python_case.m` | `pythonExe` | Python 解释器 |
| `run_single_python_case.m` | `trucksimSolverDir` | TruckSim solver 根目录 |
| `run_single_python_case.m` | `trucksimSimFile` | Simulink S-Function 使用的 `simfile.sim` |
| `run_single_python_case.m` | `port` | Python TCP 服务端口，默认 `50007` |
| `run_batch_python.m` | `phase2Root` | 阶段二根目录 |
| `run_batch_python.m` | `pythonExe` | Python 解释器 |

### 5.2 Python 侧 TruckSim 配置

检查并修改：

```text
05_python_controller\config\vehicle_config.yaml
```

重点字段：

```yaml
trucksim:
  run_name: "ORAC-BLFISMC1017 #phase2"
  com_progids: ["TruckSim.Application", "TruckSim2019.Application", "TS.Application"]
  simfile_path: "D:/04_trucksim/TruckSim2019.0_Data/simfile.sim"
  allow_par_file_patch: true
  road_base_mu: 0.85
```

说明：

- `run_name` 是 TruckSim 中当前联仿 Run 名称，换电脑后要确认是否一致。
- `simfile_path` 必须指向 Simulink TruckSim S-Function 实际读取的 `simfile.sim`。
- `allow_par_file_patch: true` 表示启用方法2。COM 不可用时，会解析 `simfile.sim` 的 `INPUT` 行，定位 `Run_all.par`，并递归修改关联 `.par` 文件。
- 程序会自动为被修改的 `.par` 文件生成 `.phase2_backup` 备份。
- `road_base_mu` 是当前道路数据集的基准附着系数；TXT 的 `road_friction` 会换算为 TruckSim 中 `MY_FRICTION` 倍率。

### 5.3 Simulink 模型要求

模型文件：

```text
00_simulink\three_axle_vehicle_2dof_3dof_Trucksim_python.slx
```

脚本默认查找以下块：

| 块 | 默认路径 |
|---|---|
| TruckSim S-Function | `three_axle_vehicle_2dof_3dof_Trucksim_python/TruckSim S-Function2` |
| TCP Client | `three_axle_vehicle_2dof_3dof_Trucksim_python/TCP Client` |

如果模型名或块名改了，需要同步修改 `run_single_python_case.m`。

TCP Client 约定：

- 输入 3 维：`[Vx_kmh, beta_deg, w_degps]`
- 输出 6 维：`[d1L, d1R, d2L, d2R, d3L, d3R]`
- 默认采样周期：`0.01 s`
- 默认端口：`50007`

## 6. TXT 测试用例格式

测试用例放在：

```text
02_测试用例
```

示例：

```text
# 阶段二验证：15 km/h 正弦转向
schema_version = 3
case_name = sine_steer_python-1
source_case_id = MV-202
trucksim_scenario = straight_road
description = 15 km/h 正弦转向
stop_time_s = 30
initial_speed_kmh = 15
target_speed_kmh = 15
steer_input_type = sine
steer_amplitude_deg = 2
steer_frequency_hz = 0.2
steer_start_time_s = 1
road_friction = 0.85
road_grade = 0.0
controller_mode = zero_sideslip
control_dt_s = 0.01
kp_beta = 0.6
ki_beta = 0.5
max_steer_deg = 20
```

必填字段：

| 字段 | 含义 |
|---|---|
| `schema_version` | 用例格式版本 |
| `case_name` | 工况名称，建议与文件名一致 |
| `stop_time_s` | 仿真停止时间 |
| `initial_speed_kmh` | 初始车速 |
| `steer_input_type` | `step` 或 `sine` |

常用可选字段：

| 字段 | 含义 |
|---|---|
| `target_speed_kmh` | 目标车速；通常与初始车速一致 |
| `steer_amplitude_deg` | 正弦幅值 |
| `steer_frequency_hz` | 正弦频率 |
| `steer_step_deg` | 阶跃幅值，若用例采用该字段，报告会优先显示 |
| `steer_start_time_s` | 转向开始时间 |
| `road_friction` | 路面附着系数 |
| `road_grade` | 坡度；当前未确认 TruckSim 坡度控件映射，非零时可能配置失败 |
| `kp_beta` / `ki_beta` | 质心侧偏角 PI 反馈增益 |
| `max_steer_deg` | 各轴转角限幅 |

## 7. 运行流程

### 7.1 Python 离线自检

不需要 MATLAB/TruckSim，用于确认 Python 依赖和控制器逻辑：

```powershell
cd "D:\动力学仿真环境阶段二\01_trucksim_simulink_python\05_python_controller"
& "D:\05_python\python.exe" tests\test_controller.py
& "D:\05_python\python.exe" tests\test_server.py
```

预期：

- `test_controller.py` 输出控制器离线验证通过。
- `test_server.py` 输出本地 TCP 闭环测试通过。

### 7.2 单工况真实联仿

准备：

1. 打开 TruckSim，确认目标 Run 为 `ORAC-BLFISMC1017 #phase2` 或目标机实际 Run。
2. 打开 MATLAB。
3. 确认 Simulink 模型存在：`00_simulink\three_axle_vehicle_2dof_3dof_Trucksim_python.slx`。
4. 在 `run_case_python.m` 中设置 `caseFile`。

运行：

```matlab
cd('D:\动力学仿真环境阶段二\01_trucksim_simulink_python\01_一键启动脚本')
run_case_python
```

脚本流程：

1. 解析 TXT 用例。
2. 加载 Simulink 模型。
3. 设置 TruckSim S-Function 的 `SIMFILE`。
4. 启动 Python TCP 服务。
5. Python 配置 TruckSim 工况，成功后输出 `CONFIG_READY`。
6. MATLAB 运行 Simulink 仿真。
7. 导出 TruckSim 与 Python 信号 CSV。
8. 生成单工况 Word 报告。

### 7.3 批量真实联仿

准备：

1. 把所有需要跑的 `.txt` 用例放入 `02_测试用例`。
2. 不想跑的用例先移出该目录，或临时改后缀。

运行：

```matlab
cd('D:\动力学仿真环境阶段二\01_trucksim_simulink_python\01_一键启动脚本')
run_batch_python
```

批量输出结构：

```text
04_测试报告\批量仿真_yyyy年mm月dd日_HH时MM分SS秒\
  cases\
    运行编号1\
      运行编号1_trucksim_io.csv
      运行编号1_python_signals.csv
      运行编号1_python_stdout.log
      运行编号1_case_info.csv
      运行编号1_case.txt
      运行编号1_metrics.csv
    运行编号2\
    ...
  figures\
    01_工况名_运行编号\
    02_工况名_运行编号\
    ...
  batch_run_dirs.txt
  批量指标汇总.csv
  阶段二批量仿真测试报告.docx
```

批量模式只生成一份 Word：

```text
阶段二批量仿真测试报告.docx
```

## 8. 数据和报告内容

单工况 CSV：

- `*_trucksim_io.csv`：MATLAB/TruckSim 侧信号。
- `*_python_signals.csv`：Python 控制器内部信号。
- `*_case_info.csv`：用例配置快照。
- `*_metrics.csv`：报告指标。
- `*_python_stdout.log`：Python 服务日志。

报告曲线：

- 第一轴转角 `delta1`
- 第二轴转角 `delta2`
- 第三轴转角 `delta3`
- 各轴转角分配对比
- 车辆纵向速度
- 质心侧偏角
- 横摆角速度

关键指标：

- 起始车速 `v_start_kmh`
- 结束车速 `v_end_kmh`
- 最大车速 `v_max_kmh`
- 最大质心侧偏角绝对值
- 最大横摆角速度绝对值
- 最大第一轴/第三轴转角绝对值

## 9. TruckSim 工况配置机制

配置入口：

```text
05_python_controller\trucksim\trucksim_com.py
```

流程：

1. 优先尝试 COM ProgID：
   - `TruckSim.Application`
   - `TruckSim2019.Application`
   - `TS.Application`
2. COM 可用时，按 `vehicle_config.yaml` 中的 `trucksim.com_keywords` 写入 TruckSim 参数。
3. COM 不可用时，启用方法2：
   - 读取 `vehicle_config.yaml: trucksim.simfile_path`
   - 解析 `simfile.sim` 中的 `INPUT` 行
   - 定位 `Run_all.par`
   - 递归解析 `ENTER_PARSFILE`、`PARSFILE`、`DEFINE_EVENT`
   - 写入 `TSTOP`、`SPEED`、`SPEED_TARGET_CONSTANT`、`MY_FRICTION`、`OPT_INIT_SPEED`
   - 每个被修改文件生成 `.phase2_backup`
4. 配置成功后 Python 日志应包含 `CONFIG_READY`。

换机重点：

- 如果 TruckSim 仍显示旧速度，例如用例设置 15 km/h 但结果仍约 40 km/h，优先检查 `simfile_path` 是否指向 Simulink S-Function 实际使用的 `simfile.sim`。
- 若 `road_grade` 非零但 TruckSim 坡度控件未映射，配置会失败，这是为了避免静默按错误工况运行。

## 10. 常见问题定位

### 10.1 车速还是 40 km/h，没有按 TXT 变成 15 km/h

检查：

1. `run_case_python.m` 或批量用例中 `initial_speed_kmh` 是否正确。
2. `vehicle_config.yaml` 的 `trucksim.simfile_path` 是否为当前 TruckSim/Simulink 真正使用的 `simfile.sim`。
3. `vehicle_config.yaml` 的 `allow_par_file_patch` 是否为 `true`。
4. 对应运行目录下 `*_python_stdout.log` 是否包含 `CONFIG_READY`。
5. Word 或 `*_metrics.csv` 中 `v_start_kmh` 是否接近用例速度。

### 10.2 MATLAB 命令行出现 `Matching "From" for "Goto" not found`

这是 Simulink 模型里 Goto/From 标签匹配警告。若仿真能结束、CSV 和报告正常生成，一般不影响本阶段 Python 联仿结果。若后续要清理模型，可在 Simulink 中逐个检查 `Goto54` 等未匹配标签。

### 10.3 Python 服务启动失败

检查：

1. Python 路径是否正确。
2. 端口 `50007` 是否被占用。
3. `tests\test_server.py` 是否能通过。
4. MATLAB 当前路径是否在 `01_一键启动脚本`。
5. `tcp_client_sfun.m` 是否在 Simulink 模型目录或 MATLAB path 中。

### 10.4 MATLAB 命令行中文乱码

现版本批量报告成功时 Python 只输出 `BATCH_SUMMARY_OK`，中文路径由 MATLAB 自己打印，正常情况下不应再出现乱码。若又出现 `鎵归噺...`，通常是某个 Python 脚本直接把 UTF-8 中文打印回 MATLAB 命令行，处理原则是：

- 成功路径尽量只打印英文状态码。
- 中文路径、中文提示由 MATLAB 侧 `fprintf` 输出。
- 不要在 MATLAB 批量报告成功路径中强制回显 Python 的中文 stdout。

### 10.5 `CONFIG_FAIL 无法完成 TruckSim 工况配置`

常见原因：

1. `simfile.sim` 路径错误。
2. `Run_all.par` 不存在或没有写权限。
3. TXT 中 `road_grade` 非零，但 `vehicle_config.yaml` 里未配置坡度控件映射。
4. TruckSim 数据目录不是当前 S-Function 使用的数据目录。

先看运行目录下的 `*_python_stdout.log`，里面会记录 COM 失败原因、`.par` 修改情况和缺失字段。

## 11. 验收清单

换电脑配置完成后，至少完成以下验证：

1. Python 依赖验证：

```powershell
& "D:\05_python\python.exe" -c "import yaml, numpy, matplotlib, docx; print('python deps ok')"
```

2. 控制器离线验证：

```powershell
cd "D:\动力学仿真环境阶段二\01_trucksim_simulink_python\05_python_controller"
& "D:\05_python\python.exe" tests\test_controller.py
```

3. TCP 服务离线验证：

```powershell
cd "D:\动力学仿真环境阶段二\01_trucksim_simulink_python\05_python_controller"
& "D:\05_python\python.exe" tests\test_server.py
```

4. MATLAB 单工况验证：

```matlab
cd('D:\动力学仿真环境阶段二\01_trucksim_simulink_python\01_一键启动脚本')
run_case_python
```

5. 速度配置验证：

用 `sine_steer_python-1.txt` 或其他低速用例跑一次，确认报告中：

```text
v_start_kmh ≈ initial_speed_kmh
```

例如 15 km/h 用例，应接近 15 km/h，而不是 40 km/h。

6. 批量验证：

```matlab
run_batch_python
```

确认输出目录下只有一份：

```text
阶段二批量仿真测试报告.docx
```

并且 `cases` 目录包含全部用例运行结果。

## 12. AI 接手时的推荐工作顺序

1. 先读本文。
2. 再读：
   - `01_一键启动脚本\run_single_python_case.m`
   - `01_一键启动脚本\run_case_python.m`
   - `01_一键启动脚本\run_batch_python.m`
   - `05_python_controller\config\vehicle_config.yaml`
   - `05_python_controller\tcp\tcp_server.py`
   - `05_python_controller\trucksim\trucksim_com.py`
3. 检查目标机路径，不要直接沿用当前电脑绝对路径。
4. 先跑 Python 离线测试，再跑 MATLAB 单工况，再跑批量。
5. 出问题先看对应运行目录下的 `*_python_stdout.log`、`*_metrics.csv` 和 MATLAB 命令行报错。

## 13. 当前已知状态

截至 2026-09-08：

- 单工况联仿流程可运行。
- 方法2 `.par` 直写已经验证可把 15 km/h 用例真正写入 TruckSim，报告中起始车速接近 15 km/h。
- 批量联仿输出已整理为一个批次目录，只生成一份批量 Word 报告。
- 批量报告命令行中文乱码已处理：Python 成功输出只保留 `BATCH_SUMMARY_OK`，中文路径由 MATLAB 打印。
- `road_grade` 的 TruckSim 控件映射仍需目标机确认后再启用。
