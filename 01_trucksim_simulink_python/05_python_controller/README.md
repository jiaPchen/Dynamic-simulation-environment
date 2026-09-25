# 05_python_controller — 阶段二 Python 侧开发

## 目录结构

```
config/      车辆与控制器配置（vehicle_config.yaml，轴距/质量/侧偏刚度/反馈增益）
parse_case_py.py         TXT 测试用例解析（与 MATLAB parse_case.m 语义一致）
controller/  零质心侧偏角多轴转角分配控制器（zero_sideslip_controller.py）
tcp/         TCP 联仿服务（tcp_server.py，HELLO/READY/STATE/CONTROL）
trucksim/    TruckSim 工况配置（trucksim_com.py；本机默认使用阶段二专用 .par 回退，COM 为可选方式）
report/      报告生成（make_report_python.py：合并 CSV、绘图、Word、批量汇总）
doc/         通讯方案对比表等文档
tests/       本地闭环测试（test_server.py，模拟 Simulink 客户端）
```

## 零质心侧偏角分配控制律

第一轴转角需求来自测试用例（阶跃/正弦）；其余轴先按速度相关的稳态零质心侧偏角前馈计算，再叠加 beta PI 反馈：

```
delta2_ff = (L2 / L1) * delta1
delta3_ff = f(m, Vx, C1..C3, L1..L3) * delta1
fb = -(kp_beta * beta + ki_beta * integral(beta))
delta2 = delta2_ff + (L2 / L1) * fb
delta3 = delta3_ff + fb
```

其中 L_i 为各轴相对质心纵向位置（前正后负），C_i 为各轴等效侧偏刚度。本车 L1=1.058、L2=0.025、L3=-0.958 m。
输出 6 通道 [d1L,d1R,d2L,d2R,d3L,d3R]（deg）送入 TruckSim 固定输入接口。

## 运行方式

1. 本地测试（无需 MATLAB/TruckSim）：
   `python tests/test_server.py`
2. 真实联仿：由 `01_一键启动脚本/run_case_python.m` 自动启动本服务并闭环运行，默认严格按 TXT 配置 TruckSim。当前 `vehicle_config.yaml` 设置 `prefer_par_file_patch: true`，因此使用阶段二专用入口定位 `Run_all.par`，并递归同步关联的 Procedure/Event `.par` 文件；若目标机具备已验证的 COM 映射，可另行切换配置方式。附着系数仅写入 `MY_FRICTION=目标值/road_base_mu`，不会改写道路文件的 `MU_ROAD_CONSTANT`。
3. 批量联仿：由 `01_一键启动脚本/run_batch_python.m` 逐个运行 TXT。每次批量运行会生成一个统一批次目录 `04_测试报告/批量仿真_时间戳/`，其中 `cases/` 保存各工况 CSV/日志/用例副本，`figures/` 保存各工况曲线，只生成一份 `阶段二批量仿真测试报告.docx` 和一份 `批量指标汇总.csv`。

## 待验证项

- TruckSim COM 属性映射集中在`config/vehicle_config.yaml`的`trucksim.com_keywords`和`trucksim.scenario_map`。COM不可用时，项目内`runtime/trucksim_phase2.path`记录的专用simfile和`allow_par_file_patch`控制`.par`文件直写回退。
- `run_case_python.m` 中 `opt.useTrucksimCom = true` 表示配置失败即中止，适合正式验收；改为 `'auto'` 时配置失败会警告并继续用当前 simfile；改为 `false`/`0` 时完全跳过 TruckSim 工况配置，适合离线调试。
- `.par` 路径已支持 `road_grade` 百分数（写入 `ROAD_ZS_COEFFICIENT`）及 `straight_road` / `hill_20deg` 两种高程场景，并有离线回归测试；非零坡度和起伏场景尚需在真实 TruckSim 联仿中验证车辆响应。COM 路径的坡度控件映射仍未验证，不能把离线测试当作 COM 实测通过。
- 每次验收应比较 `trucksim_io.csv` 与 `python_signals.csv` 的 `sim_time_s`；两者均覆盖 TXT 的 `stop_time_s` 后，才可判定时间轴通过。
- 仿真或 Python 服务失败时，新建的 `04_测试报告/failed_cases/`（批量运行时位于该批次目录下）会保留用例、可取得的 Python 日志和错误堆栈；`批量运行状态.csv` 的 `run_dir` 指向诊断目录。
