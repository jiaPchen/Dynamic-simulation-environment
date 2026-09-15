%% run_case_new.m  -  一键启动脚本（适配 new_three_axle_vehicle_2dof_3dof_Trucksim）
%  说明：
%    * 模型只保留 TruckSim S-Function 输入/输出接口；
%    * 转向输入由本脚本按测试用例生成 timeseries(steer_input)（单位：度），
%      仅作用于第一轴（Mux2 第 1、2 通道），第二、第三轴转角由模型内
%      Constant 0 固定；
%    * 模型输出全部经 To Workspace 导出，本脚本将其写回 base workspace 并
%      生成 trucksim_io.csv / case_info.csv，再调用 make_test_report_new.py
%      生成曲线图与 Word 测试报告。
%  前置条件：
%    1. TruckSim 与 Simulink 模型已打开（未运行）；
%    2. 已运行 repair_model_new 确保模型接线为标准状态（Steering Input 等块存在）。
%  注意：
%    * TruckSim 侧初始车速等工况由固定 simfile 决定（trucksim_config.m 的
%      COM 映射未启用），与用例文件中的 initial_speed_kmh 可能不一致，
%      仿真结束后脚本会给出提示。

clear; clc;

%% ===================== 0. 用户配置 =====================
mdlName  = 'new_three_axle_vehicle_2dof_3dof_Trucksim';
mdlPath  = 'D:\动力学仿真环境\00_simulink\new_three_axle_vehicle_2dof_3dof_Trucksim.slx';
caseFile = 'D:\动力学仿真环境\02_测试用例\sine_steer_40kmh.txt';
dataRoot = 'D:\动力学仿真环境\03_数据存储';
userName = '正弦输入转角';

% 启用 TruckSim COM 参数修改前，请先完成 trucksim_config.m 的
% TXT 字段 -> TruckSim 控制项映射（当前未验证，保持 false）。
useTrucksimCom = false;

% Python 解释器（make_test_report_new.py 使用）
pythonExe = 'D:\05_python\python.exe';
generateReport = true;   % 仿真结束后自动生成曲线图与 Word 测试报告

% TruckSim S-Function 运行环境与 simfile（必须绝对路径）
trucksimSolverDir = 'D:\04_trucksim\TruckSim2019.0_Prog\Programs\solvers';
trucksimMlDir     = fullfile(trucksimSolverDir, 'Matlab84+');
trucksimSimFile   = 'D:\04_trucksim\TruckSim2019.0_Data\simfile.sim';
addpath(trucksimMlDir, trucksimSolverDir, '-begin');
if ~exist(trucksimSimFile, 'file')
    warning('run_case_new:NoSimFile', 'TruckSim simfile not found: %s', trucksimSimFile);
end

%% ===================== 1. 解析测试用例 =====================
c = parse_case(caseFile);
fprintf('Case: %s | v0=%.2f km/h | steer=%s | t_end=%.2f s\n', ...
    c.case_name, str2double(c.initial_speed_kmh), c.steer_input_type, ...
    str2double(c.stop_time_s));

%% ===================== 2. 加载模型 =====================
if ~bdIsLoaded(mdlName)
    load_system(mdlPath);
end

% 防呆检查：模型必须包含 "Steering Input"（From Workspace）转向输入块。
% 若被误删，请先运行 repair_model_new 重建标准接线。
steerBlock = [mdlName '/Steering Input'];
if getSimulinkBlockHandle(steerBlock) < 0
    error('run_case_new:NoSteerBlock', ...
        ['模型缺少 "Steering Input"（From Workspace）块。请在 MATLAB 命令' ...
         '行运行 repair_model_new 修复模型接线后，再重新运行本脚本。']);
end

% TruckSim S-Function 的 simfile 改为绝对路径
sfunBlk = [mdlName '/TruckSim S-Function2'];
if getSimulinkBlockHandle(sfunBlk) >= 0
    set_param(sfunBlk, 'SIMFILE', trucksimSimFile);
    fprintf('TruckSim S-Function SIMFILE set: %s\n', trucksimSimFile);
else
    warning('run_case_new:NoSfun', 'TruckSim S-Function block not found: %s', sfunBlk);
end

%% ===================== 3. 按测试用例生成转向输入 =====================
% 模型内 "Steering Input"（From Workspace）读取 base 工作区的 steer_input
% timeseries，单位：度，仅作用于第一轴；第二/三轴由模型内 Constant 0 固定。
A    = str2double(c.steer_amplitude_deg);
t0   = str2double(c.steer_start_time_s);
tEnd = str2double(c.stop_time_s);
tSim = (0:0.001:tEnd)';

switch lower(c.steer_input_type)
    case 'sine'
        fHz = str2double(c.steer_frequency_hz);
        u = zeros(size(tSim));
        idx = tSim >= t0;
        u(idx) = A * sin(2*pi*fHz*(tSim(idx) - t0));
    case 'step'
        % 真正的阶跃：t < t0 时为 0，t >= t0 后保持 A 度
        u = zeros(size(tSim));
        u(tSim >= t0) = A;
    otherwise
        error('run_case_new:UnknownSteer', 'Unsupported steer_input_type: %s', ...
            c.steer_input_type);
end

steer_input = timeseries(u, tSim);
steer_input.Name = 'steer_input';
assignin('base', 'steer_input', steer_input);
fprintf('Steering input built: type=%s, amplitude=%g deg, start=%.2f s\n', ...
    c.steer_input_type, A, t0);

%% ===================== 4. TruckSim 参数设置（可选，未启用） =====================
if useTrucksimCom
    ok = trucksim_config(c);
    if ~ok
        error('run_case_new:TrucksimConfig', ...
            'TruckSim configuration failed; simulation not started.');
    end
end

%% ===================== 5. 运行仿真 =====================
fprintf('Running simulation: %s ...\n', c.case_name);
out = sim(mdlName, 'StopTime', c.stop_time_s);
fprintf('Simulation finished.\n');

% 检查 TruckSim 实际初始车速与用例设定是否一致（仅提示，以 simfile 为准）
try
    v0_actual = out.Vx_trucksim.Data(1);
    v0_case   = str2double(c.initial_speed_kmh);
    if abs(v0_actual - v0_case) > 0.5
        warning('run_case_new:SpeedMismatch', ...
            ['TruckSim 实际初始车速 %.2f km/h 与用例设定 %.2f km/h 不一致' ...
             '（TruckSim 工况以 simfile 为准）。'], v0_actual, v0_case);
    end
catch
end

%% ===================== 6. 导出 CSV =====================
% To Workspace 变量 -> CSV 列名（与 make_test_report_new.py 对应）
signals = {
    't',                'sim_time_s';
    'Vx_trucksim',      'state_vehicle_speed_kmh';
    'beta_trucksim',    'state_beta_trucksim_deg';
    'w_trucksim',       'state_yaw_rate_trucksim_degps';
    'x_trucksim',       'state_x_m';
    'y_trucksim',       'state_y_m';
    'xt_trucksim',      'state_xt_m';
    'yt_trucksim',      'state_yt_m';
    'delta_input',      'state_steer_delta_deg';
};

% 时间向量：优先取 sim() 的 tout，否则从任意 Timeseries 输出取时间
try
    tt = out.tout;
catch
    tt = out.x_trucksim.Time;
end
assignin('base', 't', tt(:));

for i = 1:size(signals, 1)
    v = signals{i, 1};
    if strcmp(v, 't'), continue; end
    try
        assignin('base', v, out.(v));
    catch
        warning('run_case_new:NoOutVar', 'sim() output has no field "%s".', v);
    end
end

[ioCsv, infoCsv, runNo] = export_case_csv(dataRoot, userName, c, signals);
fprintf('CSV saved:\n  %s\n  %s\n', ioCsv, infoCsv);

%% ===================== 7. 生成报告 =====================
% 调用 make_test_report_new.py 绘制曲线并生成 Word 测试报告，
% 输出到 04_测试报告\<运行编号>\。运行编号写入临时标记文件，
% 由 make_test_report_new.py 自动读取。
if generateReport
    scriptDir = fileparts(mfilename('fullpath'));
    pyScript  = fullfile(scriptDir, 'make_test_report_new.py');
    if exist(pyScript, 'file')
        if exist(pythonExe, 'file')
            logFile    = fullfile(tempdir, 'make_test_report.log');
            markerFile = fullfile(tempdir, 'codex_last_run_no.txt');
            fid = fopen(markerFile, 'w', 'n', 'UTF-8');
            if fid > 0
                fprintf(fid, '%s', runNo);
                fclose(fid);
            else
                warning('run_case_new:MarkerWriteFailed', ...
                    'Cannot write run marker file: %s', markerFile);
            end
            oldDir = cd(scriptDir);   % 脚本目录作为工作目录，命令不含中文路径
            try
                cmd = sprintf('%s make_test_report_new.py', pythonExe);
                fprintf('Generating report via: %s ...\n', cmd);
                [st, msg] = system(cmd);
            catch ME
                st  = -1;
                msg = ME.message;
            end
            cd(oldDir);
            fid = fopen(logFile, 'w');
            if fid > 0
                fprintf(fid, '%s', msg);
                fclose(fid);
            end
            reportRoot = fullfile(fileparts(scriptDir), '04_测试报告');
            reportDir  = fullfile(reportRoot, runNo);
            if st == 0 && exist(reportDir, 'dir')
                fprintf('Report generated: %s\n', reportDir);
            else
                warning('run_case_new:ReportFailed', ...
                    ['Report generation failed (exit=%d). ' ...
                     'Log saved to %s:\n%s'], st, logFile, msg);
            end
        else
            warning('run_case_new:NoPython', ...
                'Python not found at %s; report step skipped.', pythonExe);
        end
    else
        warning('run_case_new:NoReportScript', ...
            'Report script not found: %s', pyScript);
    end
end
