function [runNo, ioDir] = run_single_python_case(caseFile, opt)
% RUN_SINGLE_PYTHON_CASE  阶段二：Python 闭环联仿单工况运行
%  流程：解析 TXT -> 启动 Python TCP 服务（可配置 TruckSim 工况）
%       -> 运行 Simulink（TCP 客户端 S-Function 闭环）
%       -> 导出 CSV -> 调用 Python 生成单工况报告
%  输入：
%    caseFile  TXT 测试用例绝对路径
%    opt       可选结构体：dataRoot/userName/pythonExe/port/
%              useTrucksimCom/mdlName/mdlPath/controllerRoot/reportRoot
%  输出：
%    runNo     本次运行编号

%% ---------- 0. 默认配置 ----------
if nargin < 2, opt = struct(); end

% 以本脚本所在目录自动定位阶段二根目录，复制到其他电脑后无需修改项目目录。
scriptDir = fileparts(mfilename('fullpath'));
phase2Root = fileparts(scriptDir);
mdlName  = getopt(opt, 'mdlName',  'three_axle_vehicle_2dof_3dof_Trucksim_python');
mdlPath  = getopt(opt, 'mdlPath',  fullfile(phase2Root, '00_simulink', [mdlName '.slx']));
dataRoot = getopt(opt, 'dataRoot', fullfile(phase2Root, '03_数据存储'));
userName = getopt(opt, 'userName', 'Python联仿');
reportRoot  = getopt(opt, 'reportRoot',  fullfile(phase2Root, '04_测试报告'));
controllerRoot = getopt(opt, 'controllerRoot', fullfile(phase2Root, '05_python_controller'));
pythonExe = getopt(opt, 'pythonExe', 'C:\Python\python\python3.10.4\python.exe');
port      = getopt(opt, 'port', 50007);
useTrucksimCom = getopt(opt, 'useTrucksimCom', true);
generateReport = getopt(opt, 'generateReport', true);   % 是否生成单工况报告（批量时置 false）

trucksimSolverDir = 'C:\Trucksim2019\TruckSim2019.0_Prog\Programs\solvers';
trucksimMlDir     = fullfile(trucksimSolverDir, 'Matlab84+');
% 阶段二专用simfile。首次使用或重新选择阶段二Run后，先运行
% capture_phase2_simfile；项目内记录文件指向TruckSim数据目录中的专用副本。
simfilePointer = fullfile(phase2Root, 'runtime', 'trucksim_phase2.path');
addpath(trucksimMlDir, trucksimSolverDir, '-begin');
if ~exist(simfilePointer, 'file')
    error('run_single_python_case:NoPhaseSimfilePointer', ['阶段二专用simfile记录不存在: %s\n' ...
        '请先在TruckSim选择阶段二Run并发送到Simulink，然后运行capture_phase2_simfile。'], ...
        simfilePointer);
end
trucksimSimFile = strtrim(fileread(simfilePointer));
if ~exist(trucksimSimFile, 'file')
    error('run_single_python_case:NoPhaseSimfile', '阶段二专用simfile不存在: %s', trucksimSimFile);
end

addpath(scriptDir);                        % parse_case.m / export_case_csv.m
addpath(fileparts(mdlPath));               % tcp_client_sfun.m 所在目录（模型目录）

%% ---------- 1. 解析测试用例 ----------
c = parse_case(caseFile);
fprintf('[阶段二] Case: %s | v0=%.1f km/h | steer=%s | t_end=%.1f s\n', ...
    c.case_name, str2double(c.initial_speed_kmh), c.steer_input_type, ...
    str2double(c.stop_time_s));

%% ---------- 2. 加载模型并设置 simfile ----------
if ~bdIsLoaded(mdlName)
    load_system(mdlPath);
end
sfunBlk = [mdlName '/TruckSim S-Function2'];
if getSimulinkBlockHandle(sfunBlk) >= 0
    set_param(sfunBlk, 'SIMFILE', trucksimSimFile);
else
    error('run_single_python_case:NoSfun', '找不到 TruckSim S-Function: %s', sfunBlk);
end
tcpBlk = [mdlName '/TCP Client'];
if getSimulinkBlockHandle(tcpBlk) < 0
    error('run_single_python_case:NoTcp', ...
        '模型缺少 TCP Client 块，请确认使用 %s 模型', mdlName);
end

%% ---------- 3. 启动 Python TCP 服务 ----------
logDir  = tempname;
mkdir(logDir);
logFile = fullfile(logDir, 'server_stdout.log');
pylog   = fullfile(logDir, 'python_signals.csv');
serverPy = fullfile(controllerRoot, 'tcp', 'tcp_server.py');
try

% 用例复制到临时目录并保留与 case_name 相同的文件名，避免编码问题且满足唯一性校验。
tempCaseDir = tempname;
mkdir(tempCaseDir);
tempCaseCleanup = onCleanup(@() cleanup_temp_case(tempCaseDir)); %#ok<NASGU>
asciiCase = fullfile(tempCaseDir, [c.case_name '.txt']);
copyfile(caseFile, asciiCase);

setenv('PYTHONIOENCODING', 'utf-8');
configTrucksim = normalize_trucksim_com_mode(useTrucksimCom);
cmd = sprintf('"%s" tcp_server.py --case "%s" --port %d --log-dir "%s" --config-trucksim %s > "%s" 2>&1', ...
    pythonExe, asciiCase, port, logDir, configTrucksim, logFile);
launcherFile = fullfile(logDir, 'launch_server.cmd');
fid = fopen(launcherFile, 'w');
if fid < 0
    error('run_single_python_case:LauncherWrite', '无法创建 Python 启动脚本: %s', launcherFile);
end
fprintf(fid, '@echo off\r\n%s\r\n', cmd);
fclose(fid);
serverProc = launch_server_process(launcherFile, fullfile(controllerRoot, 'tcp'));
serverCleanup = onCleanup(@() stop_server_process(serverProc)); %#ok<NASGU>

ready = false;
for k = 1:180
    pause(0.5);
    if exist(logFile, 'file')
        txt = fileread(logFile);
        if contains(txt, 'LISTENING')
            ready = true;
            break;
        end
        if contains(txt, 'CONFIG_FAIL') || contains(txt, 'SERVER_ERROR') || ...
           contains(txt, 'Traceback')
            error('run_single_python_case:PyStart', 'Python 服务启动失败:\n%s', txt);
        end
    end
    if serverProc.HasExited
        error('run_single_python_case:PyExited', ...
            'Python 服务在 LISTENING 前退出；检查归档的 python_stdout.log。');
    end
end
if ~ready
    error('run_single_python_case:PyTimeout', '等待 Python 服务 LISTENING 超时(90s)');
end
fprintf('[阶段二] Python 服务已就绪 (port=%d)\n', port);

%% ---------- 4. 运行仿真（TCP 闭环） ----------
assignin('base', 'tcp_port', port);        % 供 tcp_client_sfun 读取，避免端口不一致
fprintf('[阶段二] 运行仿真: %s ...\n', c.case_name);
try
    out = sim(mdlName, 'StopTime', c.stop_time_s);
catch ME
    fprintf('[阶段二] 仿真失败，错误如下（请复制发给维护者）：\n');
    fprintf('%s\n', ME.message);
    for k = 1:numel(ME.cause)
        fprintf('  原因: %s\n', ME.cause{k}.message);
    end
    rethrow(ME);
end
fprintf('[阶段二] 仿真结束\n');

% 检查 TruckSim 实际初始车速与用例设定是否一致（仅提示，以 simfile 为准）
try
    v0_actual = out.Vx_trucksim.Data(1);
    v0_case   = str2double(c.initial_speed_kmh);
    if abs(v0_actual - v0_case) > 0.5
        warning('run_single_python_case:SpeedMismatch', ...
            ['TruckSim 实际初始车速 %.2f km/h 与用例设定 %.2f km/h 不一致。' ...
             '请查看 Python 日志中的 CONFIG_READY / trucksim_par 更新记录。'], ...
            v0_actual, v0_case);
    end
catch
end

%% ---------- 5. 等待 Python 服务退出 ----------
stopped = false;
for k = 1:60
    pause(0.2);
    if exist(logFile, 'file') && contains(fileread(logFile), 'SERVER_STOPPED')
        stopped = true;
        break;
    end
end
serverText = '';
if exist(logFile, 'file')
    serverText = fileread(logFile);
end
requiredMarkers = {'LISTENING', 'HANDSHAKE_OK', 'STOP_OK', 'SERVER_STOPPED'};
missingMarkers = requiredMarkers(~cellfun(@(s) contains(serverText, s), requiredMarkers));
if ~stopped || ~isempty(missingMarkers) || contains(serverText, 'SERVER_ERROR') || ...
        contains(serverText, 'Traceback')
    error('run_single_python_case:ServerIntegrity', ...
        'Python 服务完整性检查失败，缺少标记[%s]。日志: %s', ...
        strjoin(missingMarkers, ', '), logFile);
end
if strcmp(configTrucksim, '1') && ~contains(serverText, 'CONFIG_READY')
    error('run_single_python_case:ConfigIntegrity', ...
        '严格配置模式下未出现 CONFIG_READY，拒绝归档结果。日志: %s', logFile);
end

%% ---------- 6. 导出 CSV ----------
signals = {
    't',                'sim_time_s';
    'Vx_trucksim',      'state_vehicle_speed_kmh';
    'beta_trucksim',    'state_beta_trucksim_deg';
    'w_trucksim',       'state_yaw_rate_trucksim_degps';
    'x_trucksim',       'state_x_m';
    'y_trucksim',       'state_y_m';
    'xt_trucksim',      'state_xt_m';
    'yt_trucksim',      'state_yt_m';
    'delta1_actual',    'cmd_delta1_deg';
    'delta2_actual',    'cmd_delta2_deg';
    'delta3_actual',    'cmd_delta3_deg';
};

% TruckSim 实际输入（TCP Client 输出的 6 路转角）稍后与目标时间轴对齐后
% 再拆成三轴，避免它与密集 TruckSim 状态信号的采样数不同。
deltaCmd6 = [];
try
    dc = out.delta_cmd6;
    if isa(dc, 'timeseries')
        deltaCmd6 = dc;
    end
catch
    warning('run_single_python_case:NoDeltaCmd', '未取到 delta_cmd6（TruckSim 实际输入），相关列跳过。');
end
% Python TCP 时间轴采用控制周期（当前 0.01 s），而 TruckSim 输出可能是
% 更密的基础步长（当前 0.001 s）。以 Python 时间为目标时间轴，并将每个
% TruckSim 状态重采样到该时间轴后再导出，保证所有 CSV 列逐行对应。
[tt, timeSource, rawToutEnd, tcpTimeEnd] = resolve_export_time(out, pylog, ...
    str2double(c.stop_time_s));
assignin('base', 't', tt(:));
if ~isempty(deltaCmd6)
    dcAligned = align_signal_to_time(deltaCmd6, tt, 'delta_cmd6');
    if size(dcAligned.Data, 2) < 5
        error('run_single_python_case:BadDeltaCmd', ...
            'delta_cmd6 少于 5 个通道，无法导出三轴转角。');
    end
    assignin('base', 'delta1_actual', timeseries(dcAligned.Data(:, 1), tt));
    assignin('base', 'delta2_actual', timeseries(dcAligned.Data(:, 3), tt));
    assignin('base', 'delta3_actual', timeseries(dcAligned.Data(:, 5), tt));
end
c.export_time_source = timeSource;
c.raw_out_tout_end_s = sprintf('%.12g', rawToutEnd);
c.tcp_sim_time_end_s = sprintf('%.12g', tcpTimeEnd);
c.run_status = 'COMPLETED';
c.tcp_integrity_status = strjoin(requiredMarkers, '|');
if contains(serverText, 'CONFIG_READY')
    c.trucksim_config_status = 'CONFIG_READY';
elseif contains(serverText, 'CONFIG_WARN')
    c.trucksim_config_status = 'CONFIG_WARN';
else
    c.trucksim_config_status = 'CONFIG_SKIP';
end
if contains(serverText, '[trucksim_par] 已修改')
    c.trucksim_config_method = 'PAR_FILE_FALLBACK';
elseif contains(serverText, '[trucksim_com] 已连接 COM')
    c.trucksim_config_method = 'COM';
elseif strcmp(c.trucksim_config_status, 'CONFIG_SKIP')
    c.trucksim_config_method = 'SKIPPED';
else
    c.trucksim_config_method = 'UNKNOWN';
end
c.case_file_path = caseFile;
c.model_file_path = mdlPath;
c.simfile_path = trucksimSimFile;
c.controller_entry_path = serverPy;
c.controller_source_path = fullfile(controllerRoot, 'controller', 'zero_sideslip_controller.py');
c.interface_version = 'p2-tcp-v1';
c.python_executable = pythonExe;
c.trucksim_version = 'TruckSim 2019.0';
% 仅存在于 base 工作区的变量（不从 out 读取，避免 SimulationOutput 缺字段警告覆盖为空值）
baseOnly = {'t', 'delta1_actual', 'delta2_actual', 'delta3_actual'};
for i = 1:size(signals, 1)
    v = signals{i, 1};
    if any(strcmp(v, baseOnly)), continue; end
    try
        assignin('base', v, align_signal_to_time(out.(v), tt, v));
    catch ME
        error('run_single_python_case:SignalAlignFailed', ...
            '无法将输出 "%s" 对齐到 Python 时间轴：%s', v, ME.message);
    end
end

[ioCsv, ~, runNo] = export_case_csv(dataRoot, userName, c, signals);
ioDir = fileparts(ioCsv);

% 把 Python 侧信号与日志并入运行目录
pylog = fullfile(logDir, 'python_signals.csv');
if exist(pylog, 'file')
    copyfile(pylog, fullfile(ioDir, [runNo '_python_signals.csv']));
end
copyfile(logFile, fullfile(ioDir, [runNo '_python_stdout.log']));
copyfile(caseFile, fullfile(ioDir, [runNo '_case.txt']));
fprintf('[阶段二] CSV 已保存: %s\n', ioDir);

%% ---------- 7. 生成单工况报告 ----------
if generateReport
    pyScript = fullfile(controllerRoot, 'report', 'make_report_python.py');
    oldDir = cd(fullfile(controllerRoot, 'report'));
    setenv('P2_RUN_DIR', ioDir);
    setenv('P2_REPORT_ROOT', reportRoot);
    cmd = sprintf('"%s" make_report_python.py', pythonExe);
    fprintf('[阶段二] 生成报告: %s ...\n', cmd);
    [st, msg] = system(cmd);
    cd(oldDir);
    if st ~= 0
        warning('run_single_python_case:ReportFailed', ...
            '报告生成失败(exit=%d):\n%s', st, msg);
    else
        fprintf('[阶段二] 报告已生成\n');
    end
end
catch ME
    % 失败工况也保留用例、Python 输出及错误堆栈，供批量状态表追溯。
    if exist('serverProc', 'var')
        stop_server_process(serverProc);
    end
    try
        diagnosticDir = save_failure_diagnostics(reportRoot, caseFile, ...
            logFile, pylog, ME);
    catch archiveError
        diagnosticDir = ['归档失败: ' archiveError.message '；临时日志: ' logDir];
    end
    wrapped = MException('run_single_python_case:CaseFailed', ...
        '工况 %s 失败（%s）：%s。诊断目录: %s', ...
        c.case_name, ME.identifier, ME.message, diagnosticDir);
    wrapped = addCause(wrapped, ME);
    throwAsCaller(wrapped);
end
end

% ----------------------------------------------------------------------
function diagnosticDir = save_failure_diagnostics(reportRoot, caseFile, logFile, pylog, ME)
failureRoot = fullfile(reportRoot, 'failed_cases');
if exist(failureRoot, 'dir') ~= 7, mkdir(failureRoot); end
diagnosticDir = tempname(failureRoot);
mkdir(diagnosticDir);
copyfile(caseFile, fullfile(diagnosticDir, 'case.txt'));
if exist(logFile, 'file') == 2
    copyfile(logFile, fullfile(diagnosticDir, 'python_stdout.log'));
end
if exist(pylog, 'file') == 2
    copyfile(pylog, fullfile(diagnosticDir, 'python_signals.csv'));
end
errorFile = fullfile(diagnosticDir, 'error.txt');
fid = fopen(errorFile, 'w', 'n', 'UTF-8');
if fid < 0
    error('run_single_python_case:DiagnosticWrite', ...
        '无法写入失败工况错误说明: %s', errorFile);
end
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, 'case_file=%s\n', caseFile);
fprintf(fid, 'error_identifier=%s\n', ME.identifier);
fprintf(fid, '%s\n', getReport(ME, 'extended', 'hyperlinks', 'off'));
end

function v = getopt(opt, name, dflt)
if isfield(opt, name) && ~isempty(opt.(name))
    v = opt.(name);
else
    v = dflt;
end
end

function mode = normalize_trucksim_com_mode(v)
if islogical(v)
    if v
        mode = '1';
    else
        mode = '0';
    end
elseif isnumeric(v)
    if v ~= 0
        mode = '1';
    else
        mode = '0';
    end
else
    mode = lower(strtrim(char(v)));
    if strcmp(mode, 'true')
        mode = '1';
    elseif strcmp(mode, 'false')
        mode = '0';
    elseif ~ismember(mode, {'0', '1', 'auto'})
        error('run_single_python_case:BadComMode', ...
            'useTrucksimCom 只能是 true、false 或 ''auto''。');
    end
end
end

function [t, source, rawToutEnd, tcpTimeEnd] = resolve_export_time(out, pyLog, stopTime)
% RESOLVE_EXPORT_TIME  Select the Python control timeline for CSV export.
% TruckSim state signals are resampled to this returned timeline by
% align_signal_to_time before export_case_csv is called.

try
    rawT = double(out.tout(:));
catch
    rawT = double(out.x_trucksim.Time(:));
end
if isempty(rawT) || any(~isfinite(rawT)) || any(diff(rawT) < -1e-9)
    error('run_single_python_case:InvalidRawTime', ...
        'SimulationOutput 的时间向量为空、非有限或非单调，无法导出 CSV。');
end

rawToutEnd = rawT(end);
tcpTimeEnd = NaN;

% 以实际导出的车辆状态的时间向量为准，而不是 solver 的 out.tout。
% 所有阶段二正式 CSV 都包含 Vx_trucksim，因此它是最可靠的对齐锚点。
try
    vx = out.Vx_trucksim;
    if isa(vx, 'timeseries')
        signalT = double(vx.Time(:));
    elseif isstruct(vx) && isfield(vx, 'time')
        signalT = double(vx.time(:));
    else
        error('Vx_trucksim 不含可读取的时间向量');
    end
catch ME
    error('run_single_python_case:NoSignalTime', ...
        '无法取得 Vx_trucksim 的时间轴，拒绝导出未对齐 CSV：%s', ME.message);
end

if isempty(signalT) || any(~isfinite(signalT)) || any(diff(signalT) < -1e-9)
    error('run_single_python_case:InvalidSignalTime', ...
        'Vx_trucksim 时间轴为空、非有限或非单调，拒绝导出 CSV。');
end

tol = max(0.02, 0.01 * max(stopTime, 1));
if abs(signalT(1)) > tol || abs(signalT(end) - stopTime) > tol
    error('run_single_python_case:SignalTimeCoverage', ...
        ['Vx_trucksim 时间轴未从 0 覆盖到停止时间（首=%.9g，末=%.9g，期望末=%.9g）；' ...
         '拒绝导出 CSV。'], signalT(1), signalT(end), stopTime);
end

t = signalT;
source = 'trucksim_signal_time';

if ~exist(pyLog, 'file')
    error('run_single_python_case:NoPythonTimeLog', ...
        '未找到 Python 时间日志，拒绝导出无法交叉验证时间轴的 CSV。');
end

try
    pyTable = readtable(pyLog);
    if ~ismember('sim_time_s', pyTable.Properties.VariableNames)
        error('缺少 sim_time_s 列');
    end
    tcpT = double(pyTable.sim_time_s(:));
catch ME
    error('run_single_python_case:PythonTimeReadFailed', ...
        '无法读取 Python 时间日志，拒绝导出 CSV：%s', ME.message);
end

if isempty(tcpT) || any(~isfinite(tcpT)) || any(diff(tcpT) < -1e-9)
    error('run_single_python_case:InvalidPythonTime', ...
        'Python 时间日志为空、非有限或非单调，拒绝导出 CSV。');
end
tcpTimeEnd = tcpT(end);

if ~isfinite(stopTime) || abs(tcpT(1)) > tol || abs(tcpT(end) - stopTime) > tol
    error('run_single_python_case:PythonTimeCoverage', ...
        ['Python 时间轴未从 0 覆盖到用例停止时间（首=%.9g，末=%.9g，期望末=%.9g）；' ...
         '拒绝导出 CSV。'], tcpT(1), tcpT(end), stopTime);
end

t = tcpT;
source = 'python_tcp_sim_time_s';
end

function aligned = align_signal_to_time(signal, targetT, signalName)
% ALIGN_SIGNAL_TO_TIME  Resample one TruckSim/Simulink output to targetT.
% targetT is the validated Python TCP timeline.  Linear interpolation is
% exact at common sample points and prevents the old shortest-column truncation.
if isa(signal, 'timeseries')
    sourceT = double(signal.Time(:));
    data = double(signal.Data);
elseif isstruct(signal) && isfield(signal, 'time') && isfield(signal, 'signals')
    sourceT = double(signal.time(:));
    data = double(signal.signals.values);
else
    error('输出不是带时间的 timeseries/StructureWithTime。');
end

if isvector(data)
    data = data(:);
end
if size(data, 1) ~= numel(sourceT)
    error('时间行数(%d)与数据行数(%d)不一致。', numel(sourceT), size(data, 1));
end
if isempty(sourceT) || any(~isfinite(sourceT)) || any(diff(sourceT) < -1e-9)
    error('源时间轴为空、非有限或非单调。');
end
if targetT(1) < sourceT(1) - 1e-9 || targetT(end) > sourceT(end) + 1e-9
    error(['目标时间轴[%.9g, %.9g]超出 "%s" 源时间轴[%.9g, %.9g]。'], ...
        targetT(1), targetT(end), signalName, sourceT(1), sourceT(end));
end

if numel(sourceT) == numel(targetT) && max(abs(sourceT - targetT)) <= 1e-9
    dataTarget = data;
else
    dataTarget = interp1(sourceT, data, targetT, 'linear');
end
if any(~isfinite(dataTarget(:)))
    error('重采样后出现非有限数据。');
end
aligned = timeseries(dataTarget, targetT);
end

function proc = launch_server_process(launcherFile, workingDir)
% 用可追踪的 cmd.exe 进程承载 Python；异常时可按进程树清理，避免端口残留。
psi = System.Diagnostics.ProcessStartInfo();
psi.FileName = 'cmd.exe';
psi.Arguments = sprintf('/d /s /c ""%s""', launcherFile);
psi.WorkingDirectory = workingDir;
psi.UseShellExecute = false;
psi.CreateNoWindow = true;
proc = System.Diagnostics.Process.Start(psi);
if isempty(proc)
    error('run_single_python_case:PyLaunch', '无法启动 Python 服务。');
end
end

function stop_server_process(proc)
% 正常运行时 Python 已收到 STOP；异常路径用 taskkill 清理整个子进程树。
try
    if ~proc.HasExited
        system(sprintf('taskkill /PID %d /T /F >NUL 2>&1', proc.Id));
    end
catch
end
end

function cleanup_temp_case(tempCaseDir)
if exist(tempCaseDir, 'dir')
    try
        rmdir(tempCaseDir, 's');
    catch
    end
end
end
