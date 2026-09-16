# 05_python_controller — 阶段二 Python 侧开发

## 目录结构

```
config/      车辆与控制器配置（vehicle_config.yaml，轴距/质量/侧偏刚度/反馈增益）
parse_case_py.py         TXT 测试用例解析（与 MATLAB parse_case.m 语义一致）
controller/  零质心侧偏角多轴转角分配控制器（zero_sideslip_controller.py）
tcp/         TCP 联仿服务（tcp_server.py，HELLO/READY/STATE/CONTROL）
trucksim/    TruckSim 工况配置（trucksim_com.py，优先 COM，失败则按 simfile 修改 Run_all.par）
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
2. 真实联仿：由 `01_一键启动脚本/run_case_python.m` 自动启动本服务并闭环运行，默认严格按 TXT 配置 TruckSim。优先尝试 COM；若本机没有注册 COM ProgID，则按 `vehicle_config.yaml` 中的 `trucksim.simfile_path` 定位当前 `Run_all.par`，并递归同步其关联的 Procedure/Event/Friction 源 `.par` 文件，包括 `DEFINE_EVENT` 嵌套事件，让初始速度、目标速度、停止时间和附着系数进入下一次仿真。
3. 批量联仿：由 `01_一键启动脚本/run_batch_python.m` 逐个运行 TXT。每次批量运行会生成一个统一批次目录 `04_测试报告/批量仿真_时间戳/`，其中 `cases/` 保存各工况 CSV/日志/用例副本，`figures/` 保存各工况曲线，只生成一份 `阶段二批量仿真测试报告.docx` 和一份 `批量指标汇总.csv`。

## 待验证项

- TruckSim COM 属性映射集中在 `config/vehicle_config.yaml` 的 `trucksim.com_keywords` 和 `trucksim.scenario_map`。COM 不可用时，`trucksim.simfile_path` 和 `allow_par_file_patch` 控制方法2的 `.par` 文件直写回退。
- `run_case_python.m` 中 `opt.useTrucksimCom = true` 表示配置失败即中止，适合正式验收；改为 `'auto'` 时配置失败会警告并继续用当前 simfile；改为 `false`/`0` 时完全跳过 TruckSim 工况配置，适合离线调试。
- `road_grade` 仍需在目标机确认 TruckSim 控件名后启用映射；非零坡度且无映射时会配置失败，避免静默按错误工况运行。
- 每次验收应比较 `trucksim_io.csv` 与 `python_signals.csv` 的 `sim_time_s`；两者均覆盖 TXT 的 `stop_time_s` 后，才可判定时间轴通过。
