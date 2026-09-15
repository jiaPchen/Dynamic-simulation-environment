%% run_case_new.m  -  一键启动脚本（适配 new_three_axle_vehicle_2dof_3dof_Trucksim）  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
%  说明：  % 注释：原脚本说明文字，不参与执行。
%    * 模型只保留 TruckSim S-Function 输入/输出接口；  % 注释：原脚本说明文字，不参与执行。
%    * 转向输入由本脚本按测试用例生成 timeseries(steer_input)（单位：度），  % 注释：原脚本说明文字，不参与执行。
%      仅作用于第一轴（Mux2 第 1、2 通道），第二、第三轴转角由模型内  % 注释：原脚本说明文字，不参与执行。
%      Constant 0 固定；  % 注释：原脚本说明文字，不参与执行。
%    * 模型输出全部经 To Workspace 导出，本脚本将其写回 base workspace 并  % 注释：原脚本说明文字，不参与执行。
%      生成 trucksim_io.csv / case_info.csv，再调用 make_test_report_new.py  % 注释：原脚本说明文字，不参与执行。
%      生成曲线图与 Word 测试报告。  % 注释：原脚本说明文字，不参与执行。
%  前置条件：  % 注释：原脚本说明文字，不参与执行。
%    1. TruckSim 与 Simulink 模型已打开（未运行）；  % 注释：原脚本说明文字，不参与执行。
%    2. 已运行 repair_model_new 确保模型接线为标准状态（Steering Input 等块存在）。  % 注释：原脚本说明文字，不参与执行。
%  注意：  % 注释：原脚本说明文字，不参与执行。
%    * TruckSim 侧初始车速等工况由固定 simfile 决定（trucksim_config.m 的  % 注释：原脚本说明文字，不参与执行。
%      COM 映射未启用），与用例文件中的 initial_speed_kmh 可能不一致，  % 注释：原脚本说明文字，不参与执行。
%      仿真结束后脚本会给出提示。  % 注释：原脚本说明文字，不参与执行。
% 注释：空行，用来分隔代码段。
clear; clc;  % 注释：清理工作区或命令窗口，避免旧变量影响本次运行。
% 注释：空行，用来分隔代码段。
%% ===================== 0. 用户配置 =====================  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
mdlName  = 'new_three_axle_vehicle_2dof_3dof_Trucksim';  % 注释：给变量赋值或计算参数，供后续流程使用。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
mdlPath  = 'D:\动力学仿真环境\00_simulink\new_three_axle_vehicle_2dof_3dof_Trucksim.slx';  % 注释：给变量赋值或计算参数，供后续流程使用。 模型文件路径；换电脑后若模型位置变化，需要改成本机实际 .slx 路径。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
caseFile = 'D:\动力学仿真环境\02_测试用例\sine_steer_40kmh.txt';  % 注释：给变量赋值或计算参数，供后续流程使用。 测试用例文件路径；换工况或换电脑后要指向实际存在的 TXT 文件。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
dataRoot = 'D:\动力学仿真环境\03_数据存储';  % 注释：给变量赋值或计算参数，供后续流程使用。 仿真数据输出根目录；需要保证本机有写入权限。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
userName = '正弦输入转角';  % 注释：给变量赋值或计算参数，供后续流程使用。 数据输出子目录名称，用于区分不同测试批次或人员。
% 注释：空行，用来分隔代码段。
% 启用 TruckSim COM 参数修改前，请先完成 trucksim_config.m 的  % 注释：原脚本说明文字，不参与执行。
% TXT 字段 -> TruckSim 控制项映射（当前未验证，保持 false）。  % 注释：原脚本说明文字，不参与执行。
useTrucksimCom = false;  % 注释：给变量赋值或计算参数，供后续流程使用。 是否启用 TruckSim COM 配置；旧流程当前映射未验证，通常保持 false。
% 注释：空行，用来分隔代码段。
% Python 解释器（make_test_report_new.py 使用）  % 注释：原脚本说明文字，不参与执行。
pythonExe = 'D:\05_python\python.exe';  % 注释：给变量赋值或计算参数，供后续流程使用。 Python 解释器路径；换电脑后要改成装好依赖的 python.exe。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
generateReport = true;   % 仿真结束后自动生成曲线图与 Word 测试报告  % 注释：给变量赋值或计算参数，供后续流程使用。 是否在仿真结束后自动生成图和 Word 报告。
% 注释：空行，用来分隔代码段。
% TruckSim S-Function 运行环境与 simfile（必须绝对路径）  % 注释：原脚本说明文字，不参与执行。
trucksimSolverDir = 'D:\04_trucksim\TruckSim2019.0_Prog\Programs\solvers';  % 注释：给变量赋值或计算参数，供后续流程使用。 TruckSim solver 目录；MATLAB 需要把它加入路径才能使用 TruckSim S-Function。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
trucksimMlDir     = fullfile(trucksimSolverDir, 'Matlab84+');  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。 TruckSim solver 目录；MATLAB 需要把它加入路径才能使用 TruckSim S-Function。 TruckSim 的 MATLAB 适配目录，通常在 solver 目录下。
trucksimSimFile   = 'D:\04_trucksim\TruckSim2019.0_Data\simfile.sim';  % 注释：给变量赋值或计算参数，供后续流程使用。 TruckSim simfile.sim 路径；必须和 Simulink S-Function 实际读取的文件一致。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
addpath(trucksimMlDir, trucksimSolverDir, '-begin');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 TruckSim solver 目录；MATLAB 需要把它加入路径才能使用 TruckSim S-Function。 TruckSim 的 MATLAB 适配目录，通常在 solver 目录下。 把目录加入 MATLAB 搜索路径，避免函数、模型或 TruckSim 库找不到。
if ~exist(trucksimSimFile, 'file')  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。 TruckSim simfile.sim 路径；必须和 Simulink S-Function 实际读取的文件一致。
    warning('run_case_new:NoSimFile', 'TruckSim simfile not found: %s', trucksimSimFile);  % 注释：输出警告但不中断流程，用于提示潜在问题。 TruckSim simfile.sim 路径；必须和 Simulink S-Function 实际读取的文件一致。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
%% ===================== 1. 解析测试用例 =====================  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
c = parse_case(caseFile);  % 注释：给变量赋值或计算参数，供后续流程使用。 测试用例文件路径；换工况或换电脑后要指向实际存在的 TXT 文件。
fprintf('Case: %s | v0=%.2f km/h | steer=%s | t_end=%.2f s\n', ...  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
    c.case_name, str2double(c.initial_speed_kmh), c.steer_input_type, ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    str2double(c.stop_time_s));  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
%% ===================== 2. 加载模型 =====================  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
if ~bdIsLoaded(mdlName)  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    load_system(mdlPath);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型文件路径；换电脑后若模型位置变化，需要改成本机实际 .slx 路径。 加载 Simulink 模型文件；路径错误会在这里失败。 调用外部命令，主要用于运行 Python 报告脚本。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
% 防呆检查：模型必须包含 "Steering Input"（From Workspace）转向输入块。  % 注释：原脚本说明文字，不参与执行。
% 若被误删，请先运行 repair_model_new 重建标准接线。  % 注释：原脚本说明文字，不参与执行。
steerBlock = [mdlName '/Steering Input'];  % 注释：给变量赋值或计算参数，供后续流程使用。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
if getSimulinkBlockHandle(steerBlock) < 0  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    error('run_case_new:NoSteerBlock', ...  % 注释：抛出错误并中止运行，防止配置错误时继续仿真。
        ['模型缺少 "Steering Input"（From Workspace）块。请在 MATLAB 命令' ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
         '行运行 repair_model_new 修复模型接线后，再重新运行本脚本。']);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
% TruckSim S-Function 的 simfile 改为绝对路径  % 注释：原脚本说明文字，不参与执行。
sfunBlk = [mdlName '/TruckSim S-Function2'];  % 注释：给变量赋值或计算参数，供后续流程使用。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
if getSimulinkBlockHandle(sfunBlk) >= 0  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    set_param(sfunBlk, 'SIMFILE', trucksimSimFile);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 TruckSim simfile.sim 路径；必须和 Simulink S-Function 实际读取的文件一致。 设置 Simulink 块参数，模型块名或参数名变化时这里要同步修改。
    fprintf('TruckSim S-Function SIMFILE set: %s\n', trucksimSimFile);  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
else  % 注释：条件判断的兜底分支。
    warning('run_case_new:NoSfun', 'TruckSim S-Function block not found: %s', sfunBlk);  % 注释：输出警告但不中断流程，用于提示潜在问题。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
%% ===================== 3. 按测试用例生成转向输入 =====================  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
% 模型内 "Steering Input"（From Workspace）读取 base 工作区的 steer_input  % 注释：原脚本说明文字，不参与执行。
% timeseries，单位：度，仅作用于第一轴；第二/三轴由模型内 Constant 0 固定。  % 注释：原脚本说明文字，不参与执行。
A    = str2double(c.steer_amplitude_deg);  % 注释：给变量赋值或计算参数，供后续流程使用。
t0   = str2double(c.steer_start_time_s);  % 注释：给变量赋值或计算参数，供后续流程使用。
tEnd = str2double(c.stop_time_s);  % 注释：给变量赋值或计算参数，供后续流程使用。
tSim = (0:0.001:tEnd)';  % 注释：给变量赋值或计算参数，供后续流程使用。
% 注释：空行，用来分隔代码段。
switch lower(c.steer_input_type)  % 注释：多分支选择开始，根据变量取值进入不同 case。
    case 'sine'  % 注释：switch 的一个具体分支。
        fHz = str2double(c.steer_frequency_hz);  % 注释：给变量赋值或计算参数，供后续流程使用。
        u = zeros(size(tSim));  % 注释：给变量赋值或计算参数，供后续流程使用。
        idx = tSim >= t0;  % 注释：给变量赋值或计算参数，供后续流程使用。
        u(idx) = A * sin(2*pi*fHz*(tSim(idx) - t0));  % 注释：给变量赋值或计算参数，供后续流程使用。
    case 'step'  % 注释：switch 的一个具体分支。
        % 真正的阶跃：t < t0 时为 0，t >= t0 后保持 A 度  % 注释：原脚本说明文字，不参与执行。
        u = zeros(size(tSim));  % 注释：给变量赋值或计算参数，供后续流程使用。
        u(tSim >= t0) = A;  % 注释：给变量赋值或计算参数，供后续流程使用。
    otherwise  % 注释：switch 的兜底分支，用于处理不支持的输入。
        error('run_case_new:UnknownSteer', 'Unsupported steer_input_type: %s', ...  % 注释：抛出错误并中止运行，防止配置错误时继续仿真。
            c.steer_input_type);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
steer_input = timeseries(u, tSim);  % 注释：给变量赋值或计算参数，供后续流程使用。
steer_input.Name = 'steer_input';  % 注释：给变量赋值或计算参数，供后续流程使用。
assignin('base', 'steer_input', steer_input);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
fprintf('Steering input built: type=%s, amplitude=%g deg, start=%.2f s\n', ...  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
    c.steer_input_type, A, t0);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
%% ===================== 4. TruckSim 参数设置（可选，未启用） =====================  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
if useTrucksimCom  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。 是否启用 TruckSim COM 配置；旧流程当前映射未验证，通常保持 false。
    ok = trucksim_config(c);  % 注释：给变量赋值或计算参数，供后续流程使用。
    if ~ok  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        error('run_case_new:TrucksimConfig', ...  % 注释：抛出错误并中止运行，防止配置错误时继续仿真。
            'TruckSim configuration failed; simulation not started.');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
%% ===================== 5. 运行仿真 =====================  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
fprintf('Running simulation: %s ...\n', c.case_name);  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
out = sim(mdlName, 'StopTime', c.stop_time_s);  % 注释：给变量赋值或计算参数，供后续流程使用。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。 启动 Simulink 仿真，并使用测试用例里的停止时间。
fprintf('Simulation finished.\n');  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
% 注释：空行，用来分隔代码段。
% 检查 TruckSim 实际初始车速与用例设定是否一致（仅提示，以 simfile 为准）  % 注释：原脚本说明文字，不参与执行。
try  % 注释：异常保护开始，下面代码失败时会进入 catch。
    v0_actual = out.Vx_trucksim.Data(1);  % 注释：给变量赋值或计算参数，供后续流程使用。
    v0_case   = str2double(c.initial_speed_kmh);  % 注释：给变量赋值或计算参数，供后续流程使用。
    if abs(v0_actual - v0_case) > 0.5  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        warning('run_case_new:SpeedMismatch', ...  % 注释：输出警告但不中断流程，用于提示潜在问题。
            ['TruckSim 实际初始车速 %.2f km/h 与用例设定 %.2f km/h 不一致' ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
             '（TruckSim 工况以 simfile 为准）。'], v0_actual, v0_case);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
catch  % 注释：异常处理分支，用于提示或跳过失败步骤。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
%% ===================== 6. 导出 CSV =====================  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
% To Workspace 变量 -> CSV 列名（与 make_test_report_new.py 对应）  % 注释：原脚本说明文字，不参与执行。
signals = {  % 注释：给变量赋值或计算参数，供后续流程使用。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
    't',                'sim_time_s';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    'Vx_trucksim',      'state_vehicle_speed_kmh';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    'beta_trucksim',    'state_beta_trucksim_deg';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    'w_trucksim',       'state_yaw_rate_trucksim_degps';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    'x_trucksim',       'state_x_m';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    'y_trucksim',       'state_y_m';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    'xt_trucksim',      'state_xt_m';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    'yt_trucksim',      'state_yt_m';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    'delta_input',      'state_steer_delta_deg';  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
};  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
% 时间向量：优先取 sim() 的 tout，否则从任意 Timeseries 输出取时间  % 注释：原脚本说明文字，不参与执行。 启动 Simulink 仿真，并使用测试用例里的停止时间。
try  % 注释：异常保护开始，下面代码失败时会进入 catch。
    tt = out.tout;  % 注释：给变量赋值或计算参数，供后续流程使用。
catch  % 注释：异常处理分支，用于提示或跳过失败步骤。
    tt = out.x_trucksim.Time;  % 注释：给变量赋值或计算参数，供后续流程使用。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
assignin('base', 't', tt(:));  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
for i = 1:size(signals, 1)  % 注释：循环开始，逐个处理数组、文件或变量。
    v = signals{i, 1};  % 注释：给变量赋值或计算参数，供后续流程使用。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
    if strcmp(v, 't'), continue; end  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    try  % 注释：异常保护开始，下面代码失败时会进入 catch。
        assignin('base', v, out.(v));  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    catch  % 注释：异常处理分支，用于提示或跳过失败步骤。
        warning('run_case_new:NoOutVar', 'sim() output has no field "%s".', v);  % 注释：输出警告但不中断流程，用于提示潜在问题。 启动 Simulink 仿真，并使用测试用例里的停止时间。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
[ioCsv, infoCsv, runNo] = export_case_csv(dataRoot, userName, c, signals);  % 注释：给变量赋值或计算参数，供后续流程使用。 仿真数据输出根目录；需要保证本机有写入权限。 数据输出子目录名称，用于区分不同测试批次或人员。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
fprintf('CSV saved:\n  %s\n  %s\n', ioCsv, infoCsv);  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
% 注释：空行，用来分隔代码段。
%% ===================== 7. 生成报告 =====================  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
% 调用 make_test_report_new.py 绘制曲线并生成 Word 测试报告，  % 注释：原脚本说明文字，不参与执行。
% 输出到 04_测试报告\<运行编号>\。运行编号写入临时标记文件，  % 注释：原脚本说明文字，不参与执行。
% 由 make_test_report_new.py 自动读取。  % 注释：原脚本说明文字，不参与执行。
if generateReport  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。 是否在仿真结束后自动生成图和 Word 报告。
    scriptDir = fileparts(mfilename('fullpath'));  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
    pyScript  = fullfile(scriptDir, 'make_test_report_new.py');  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
    if exist(pyScript, 'file')  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        if exist(pythonExe, 'file')  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。 Python 解释器路径；换电脑后要改成装好依赖的 python.exe。
            logFile    = fullfile(tempdir, 'make_test_report.log');  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
            markerFile = fullfile(tempdir, 'codex_last_run_no.txt');  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
            fid = fopen(markerFile, 'w', 'n', 'UTF-8');  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
            if fid > 0  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
                fprintf(fid, '%s', runNo);  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
                fclose(fid);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
            else  % 注释：条件判断的兜底分支。
                warning('run_case_new:MarkerWriteFailed', ...  % 注释：输出警告但不中断流程，用于提示潜在问题。
                    'Cannot write run marker file: %s', markerFile);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
            end  % 注释：结束当前函数、条件、循环或 switch 代码块。
            oldDir = cd(scriptDir);   % 脚本目录作为工作目录，命令不含中文路径  % 注释：给变量赋值或计算参数，供后续流程使用。
            try  % 注释：异常保护开始，下面代码失败时会进入 catch。
                cmd = sprintf('%s make_test_report_new.py', pythonExe);  % 注释：给变量赋值或计算参数，供后续流程使用。 Python 解释器路径；换电脑后要改成装好依赖的 python.exe。
                fprintf('Generating report via: %s ...\n', cmd);  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
                [st, msg] = system(cmd);  % 注释：给变量赋值或计算参数，供后续流程使用。 调用外部命令，主要用于运行 Python 报告脚本。
            catch ME  % 注释：异常处理分支，用于提示或跳过失败步骤。
                st  = -1;  % 注释：给变量赋值或计算参数，供后续流程使用。
                msg = ME.message;  % 注释：给变量赋值或计算参数，供后续流程使用。
            end  % 注释：结束当前函数、条件、循环或 switch 代码块。
            cd(oldDir);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
            fid = fopen(logFile, 'w');  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
            if fid > 0  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
                fprintf(fid, '%s', msg);  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
                fclose(fid);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
            end  % 注释：结束当前函数、条件、循环或 switch 代码块。
            reportRoot = fullfile(fileparts(scriptDir), '04_测试报告');  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
            reportDir  = fullfile(reportRoot, runNo);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
            if st == 0 && exist(reportDir, 'dir')  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
                fprintf('Report generated: %s\n', reportDir);  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
            else  % 注释：条件判断的兜底分支。
                warning('run_case_new:ReportFailed', ...  % 注释：输出警告但不中断流程，用于提示潜在问题。
                    ['Report generation failed (exit=%d). ' ...  % 注释：给变量赋值或计算参数，供后续流程使用。
                     'Log saved to %s:\n%s'], st, logFile, msg);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
            end  % 注释：结束当前函数、条件、循环或 switch 代码块。
        else  % 注释：条件判断的兜底分支。
            warning('run_case_new:NoPython', ...  % 注释：输出警告但不中断流程，用于提示潜在问题。
                'Python not found at %s; report step skipped.', pythonExe);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 Python 解释器路径；换电脑后要改成装好依赖的 python.exe。
        end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    else  % 注释：条件判断的兜底分支。
        warning('run_case_new:NoReportScript', ...  % 注释：输出警告但不中断流程，用于提示潜在问题。
            'Report script not found: %s', pyScript);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
