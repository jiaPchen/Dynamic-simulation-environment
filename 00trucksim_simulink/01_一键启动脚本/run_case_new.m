function [runNo, ioDir] = run_case_new(caseFile, opt)
%% run_case_new  一键启动函数（无参数调用时运行默认工况）
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
%    * 仿真前会按 TXT 配置 TruckSim；COM 不可用时自动修改当前 simfile
%      所指向的参数文件。配置、时长、初始速度或实际转向不符时不会归档结果。

clc;
if nargin < 2, opt = struct(); end

%% ===================== 0. 用户配置 =====================
mdlName  = getopt(opt, 'mdlName', 'new_three_axle_vehicle_2dof_3dof_Trucksim');
% 项目内路径由本脚本位置推导，项目移动到其他目录后无需再改这里。
scriptDir   = fileparts(mfilename('fullpath'));
projectRoot = fileparts(scriptDir);
mdlPath  = getopt(opt, 'mdlPath', fullfile(projectRoot, '00_simulink', ...
    'new_three_axle_vehicle_2dof_3dof_Trucksim.slx'));
if nargin < 1 || isempty(caseFile)
    caseFile = fullfile(projectRoot, '02_测试用例', 'sine_steer_40kmh.txt');
end
dataRoot = getopt(opt, 'dataRoot', fullfile(projectRoot, '03_数据存储'));
userName = getopt(opt, 'userName', '');

% 严格按 TXT 配置 TruckSim：COM 不可用时自动修改 simfile 指向的
% Run_all.par 及其关联工况文件，并保留原文件备份。
useTrucksimCom = getopt(opt, 'useTrucksimCom', true);

% Python 解释器（make_test_report_new.py 使用）
pythonExe = getopt(opt, 'pythonExe', 'C:\Python\python\python3.10.4\python.exe');
generateReport = getopt(opt, 'generateReport', true);

% TruckSim S-Function 运行环境与阶段一专用 simfile（必须绝对路径）。
% 首次使用或重新选择阶段一Run后，先运行 capture_phase1_simfile。
trucksimSolverDir = 'C:\Trucksim2019\TruckSim2019.0_Prog\Programs\solvers';
trucksimMlDir     = fullfile(trucksimSolverDir, 'Matlab84+');
simfilePointer    = fullfile(projectRoot, 'runtime', 'trucksim_phase1.path');
addpath(trucksimMlDir, trucksimSolverDir, '-begin');
if ~exist(simfilePointer, 'file')
    error('run_case_new:NoSimFilePointer', ['阶段一专用simfile记录不存在: %s\n' ...
        '请先在TruckSim选择阶段一Run并发送到Simulink，然后运行capture_phase1_simfile。'], ...
        simfilePointer);
end
trucksimSimFile = strtrim(fileread(simfilePointer));
if ~exist(trucksimSimFile, 'file')
    error('run_case_new:NoSimFile', '阶段一专用simfile不存在: %s', trucksimSimFile);
end

%% ===================== 1. 解析测试用例 =====================
c = parse_case(caseFile);
switch lower(c.steer_input_type)
    case 'step'
        if isempty(userName), userName = '阶跃输入转角'; end
    case 'sine'
        if isempty(userName), userName = '正弦输入转角'; end
    otherwise
        if isempty(userName), userName = '其他输入转角'; end
end
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
    error('run_case_new:NoSfun', 'TruckSim S-Function block not found: %s', sfunBlk);
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

%% ===================== 4. TruckSim 参数设置 =====================
if useTrucksimCom
    [ok, configMethod] = trucksim_config(c, caseFile, pythonExe, trucksimSimFile);
    if ~ok
        error('run_case_new:TrucksimConfig', ...
            'TruckSim configuration failed; simulation not started.');
    end
else
    configMethod = 'SKIPPED';
end

%% ===================== 5. 运行仿真 =====================
fprintf('Running simulation: %s ...\n', c.case_name);
out = sim(mdlName, 'StopTime', c.stop_time_s);
fprintf('Simulation finished.\n');

% 严格验收：未跑满、初始速度不符或实际转向不符时，不归档 CSV/报告。
validate_simulation_output(out, tEnd, c, tSim, u);

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

% 内部仿真可保持更密步长；正式 CSV 统一按需求降采样到 0.01 s。
try
    rawT = double(out.tout(:));
catch
    rawT = double(out.x_trucksim.Time(:));
end
exportDt = 0.01;
tt = (0:exportDt:tEnd)';
if isempty(tt) || abs(tt(end) - tEnd) > 1e-9
    tt(end + 1, 1) = tEnd;
end
assignin('base', 't', tt);

for i = 1:size(signals, 1)
    v = signals{i, 1};
    if strcmp(v, 't'), continue; end
    try
        assignin('base', v, align_signal_to_time(out.(v), tt, rawT, v));
    catch ME
        error('run_case_new:SignalAlignFailed', ...
            '无法将输出 "%s" 对齐到 0.01 s 时间轴：%s', v, ME.message);
    end
end

c.run_status = 'COMPLETED';
c.trucksim_config_status = ternary(useTrucksimCom, 'CONFIG_READY', 'CONFIG_SKIP');
c.trucksim_config_method = configMethod;
c.case_file_path = caseFile;
c.model_file_path = mdlPath;
c.simfile_path = trucksimSimFile;
c.export_sample_period_s = sprintf('%.12g', exportDt);
c.python_executable = pythonExe;
c.trucksim_version = 'TruckSim 2019.0';
[ioCsv, infoCsv, runNo, metricsCsv] = export_case_csv(dataRoot, userName, c, signals);
ioDir = fileparts(ioCsv);
copyfile(caseFile, fullfile(ioDir, [runNo '_case.txt']));
fprintf('CSV saved:\n  %s\n  %s\n  %s\n', ioCsv, infoCsv, metricsCsv);

%% ===================== 7. 生成报告 =====================
% 调用 make_test_report_new.py 绘制曲线并生成 Word 测试报告，
% 输出到 04_测试报告\<运行编号>\。运行编号写入临时标记文件，
% 由 make_test_report_new.py 自动读取。
if generateReport
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
                error('run_case_new:MarkerWriteFailed', ...
                    'Cannot write run marker file: %s', markerFile);
            end
            oldDir = cd(scriptDir);   % 脚本目录作为工作目录，命令不含中文路径
            try
                cmd = sprintf('"%s" make_test_report_new.py', pythonExe);
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
            reportFile = fullfile(reportDir, [runNo '.docx']);
            if st == 0 && exist(reportFile, 'file')
                fprintf('Report generated: %s\n', reportDir);
            else
                error('run_case_new:ReportFailed', ...
                    ['Report generation failed (exit=%d). ' ...
                     'Log saved to %s:\n%s'], st, logFile, msg);
            end
        else
            error('run_case_new:NoPython', ...
                'Python not found at %s; report step skipped.', pythonExe);
        end
    else
        error('run_case_new:NoReportScript', ...
            'Report script not found: %s', pyScript);
    end
end

end

function v = getopt(opt, name, dflt)
if isfield(opt, name) && ~isempty(opt.(name)), v = opt.(name); else, v = dflt; end
end

function aligned = align_signal_to_time(signal, targetT, rawT, signalName)
if isa(signal, 'timeseries')
    sourceT = double(signal.Time(:));
    data = double(signal.Data);
elseif isstruct(signal) && isfield(signal, 'time') && isfield(signal, 'signals')
    sourceT = double(signal.time(:));
    data = double(signal.signals.values);
else
    data = double(signal);
    if isvector(data), data = data(:); end
    if size(data, 1) ~= numel(rawT)
        error('输出不带时间且行数与 out.tout 不一致。');
    end
    sourceT = rawT;
end
if isvector(data), data = data(:); end
if size(data, 1) ~= numel(sourceT)
    error('时间行数(%d)与数据行数(%d)不一致。', numel(sourceT), size(data, 1));
end
if isempty(sourceT) || any(~isfinite(sourceT)) || any(diff(sourceT) < -1e-9)
    error('源时间轴为空、非有限或非单调。');
end
if targetT(1) < sourceT(1) - 1e-9 || targetT(end) > sourceT(end) + 1e-9
    error('目标时间轴超出 "%s" 源时间范围。', signalName);
end
dataTarget = interp1(sourceT, data, targetT, 'linear');
if any(~isfinite(dataTarget(:))), error('重采样后出现非有限数据。'); end
aligned = timeseries(dataTarget, targetT);
end

function out = ternary(cond, a, b)
if cond, out = a; else, out = b; end
end
