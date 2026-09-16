%% run_case_python.m - 阶段二一键启动（Python 闭环联仿，单工况）
%  使用前：打开 TruckSim 与 Simulink 模型（不运行），
%          修改下面的 caseFile 选择工况，然后直接运行本脚本。
clear; clc;
clear run_single_python_case parse_case export_case_csv;

caseFile = 'C:\Users\ccc\Desktop\动力学仿真环境阶段二\01_trucksim_simulink_python\02_测试用例\step_steer_python.txt';%step_steer_python  sine_steer_python

opt = struct();
opt.useTrucksimCom = true;  % 严格按 TXT 配置 TruckSim；COM 不可用时自动改 simfile 指向的 Run_all.par
runNo = run_single_python_case(caseFile, opt);
fprintf('完成，运行编号: %s\n', runNo);
