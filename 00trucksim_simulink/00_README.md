# 阶段一TruckSim+Simulink开环仿真

`00trucksim_simulink`是可单独复制、单独配置和单独运行的阶段一项目。它不依赖其他项目文件夹中的代码、模型或配置文件。

项目读取TXT用例，生成第一轴开环转向输入，驱动TruckSimS-Function完成三轴车辆仿真，并自动输出CSV、曲线和Word报告。第二、第三轴转角在模型中固定为0度。

## 先读什么

1. `03_换机配置与AI交接说明.md`：换电脑时直接交给AI执行配置。
2. `02_阶段一仿真测试系统框架与运行指南.md`：日常运行与结果验收。
3. `01_阶段一仿真测试系统全景梳理.md`：文件职责和数据流。

## 独立运行所需内容

本文件夹已经包含阶段一需要的MATLAB脚本、本地TruckSim配置模块、Simulink模型、TXT用例和报告脚本。新电脑只需另外安装MATLAB、TruckSim和Python，并导入本目录的`ORAC-BLFISMC1017 #phase1.cpar`。

换机时只需调整`run_case_new.m`中的`pythonExe`和`trucksimSolverDir`，并检查项目根目录`requirements.txt`中的已验证Python依赖。每次导入或切换阶段一Run后，先在TruckSim中“发送到Simulink”，再运行`capture_phase1_simfile`：它会在TruckSim数据目录保存专用`simfile_phase1.sim`，并在项目内记录路径。项目内模型、用例、数据与报告目录均由脚本位置自动定位。
