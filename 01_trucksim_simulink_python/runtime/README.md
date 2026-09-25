# 阶段二专用TruckSim入口

不要把共享TruckSim数据目录中的`simfile.sim`直接作为阶段二运行入口。

在TruckSim中选择阶段二Run并发送到Simulink后，在MATLAB的`01_一键启动脚本`目录运行：

```matlab
capture_phase2_simfile
```

脚本会在TruckSim数据目录中生成`simfile_phase2.sim`，并在本目录写入其路径记录`trucksim_phase2.path`。同级阶段一入口存在且两者指向同一`Run_all.par`时会拒绝保存。
