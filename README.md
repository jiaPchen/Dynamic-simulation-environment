# 动力学仿真环境阶段二

对应《项目推进.docx》阶段二：Python 闭环联仿（零质心侧偏角多轴转角分配控制）。

换机配置、完整运行流程和故障定位请优先阅读：
`01_trucksim_simulink_python\阶段二联仿环境配置与运行说明_AI交接版.md`。

## 阶段二现状

- 00_trucksim_simulink：阶段一基线目录已补占位说明；当前文件夹内未发现阶段一原始模型/脚本资产，需从阶段一交付物或备份中补入后再作为基线归档。
- 01_trucksim_simulink_python：
  - `00_simulink/three_axle_vehicle_2dof_3dof_Trucksim_python.slx`：Python 联仿模型；
  - `00_simulink/tcp_client_sfun.m`：Simulink TCP 客户端；
  - `01_一键启动脚本/`：run_case_python.m（单工况）、run_batch_python.m（批量）、
    run_single_python_case.m（核心流程）；
  - `02_测试用例/`：step_steer_python.txt、sine_steer_python.txt 等阶段二用例；
  - `05_python_controller/`：零质心侧偏角控制器、TCP 服务、TruckSim COM 配置、
    报告生成、通讯方案对比表。

## 历史说明（2026-08-31）

旧说明曾提到 `00_trucksim_simulink` 已拷贝、`three_axle_vehicle_2dof_3dof_Trucksim_2.slx` 为原始模型；本次检查时这两项文件资产不在当前目录中，因此不再作为现状描述。

## 运行步骤（真实联仿）

1. 打开 TruckSim（ORAC-BLFISMC1017 对应 Run）与 Simulink 模型
   `three_axle_vehicle_2dof_3dof_Trucksim_python.slx`，不开始仿真；
2. 在 MATLAB 中 `cd D:\动力学仿真环境阶段二\01_trucksim_simulink_python\01_一键启动脚本`；
3. 运行 `run_case_python`（单工况）或 `run_batch_python`（批量）。默认严格按 TXT 配置 TruckSim：优先尝试 COM；若本机没有注册 COM ProgID，则按 `simfile.sim` 定位当前 `Run_all.par`，并递归同步关联的 Procedure/Event/Friction 源 `.par` 文件，包括 `DEFINE_EVENT` 嵌套事件，写入初始/目标车速、停止时间和附着系数。若配置仍失败会中止，避免继续沿用旧工况；无 TruckSim/COM 环境调试可设为 `false`；
4. 单工况结果：`03_数据存储\Python联仿\<运行编号>\` 下 CSV，
   `04_测试报告\<运行编号>\` 下曲线与 Word 报告；
   批量结果：`04_测试报告\批量仿真_时间戳\` 下集中保存全部工况数据、曲线、`批量指标汇总.csv`
   和唯一的 `阶段二批量仿真测试报告.docx`。
