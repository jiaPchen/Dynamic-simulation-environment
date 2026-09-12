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

scriptDir = fileparts(mfilename('fullpath'));
addpath(scriptDir);                        % parse_case.m / export_case_csv.m
phase2Root = getopt(opt, 'phase2Root', fileparts(scriptDir));
localEnv = p2_detect_local_env(phase2Root);
mdlName  = getopt(opt, 'mdlName',  'three_axle_vehicle_2dof_3dof_Trucksim_python');
mdlPath  = getopt(opt, 'mdlPath',  fullfile(phase2Root, '00_simulink', [mdlName '.slx']));
dataRoot = getopt(opt, 'dataRoot', fullfile(phase2Root, '03_数据存储'));
userName = getopt(opt, 'userName', 'Python联仿');
reportRoot  = getopt(opt, 'reportRoot',  fullfile(phase2Root, '04_测试报告'));
caseDir     = getopt(opt, 'caseDir',     fullfile(phase2Root, '02_测试用例'));
controllerRoot = getopt(opt, 'controllerRoot', fullfile(phase2Root, '05_python_controller'));
pythonExe = getopt(opt, 'pythonExe', localEnv.pythonExe);
port      = getopt(opt, 'port', 50007);
useTrucksimCom = getopt(opt, 'useTrucksimCom', true);
generateReport = getopt(opt, 'generateReport', true);   % 是否生成单工况报告（批量时置 false）

trucksimSolverDir = getopt(opt, 'trucksimSolverDir', localEnv.trucksimSolverDir);
trucksimMlDir     = fullfile(trucksimSolverDir, 'Matlab84+');
trucksimSimFile   = getopt(opt, 'trucksimSimFile', localEnv.trucksimSimFile);
if isempty(trucksimSolverDir) || exist(trucksimSolverDir, 'dir') ~= 7
    error('run_single_python_case:NoTrucksimSolver', ...
        ['找不到 TruckSim solver 目录。请设置环境变量 P2_TRUCKSIM_SOLVER_DIR，' ...
         '或在 opt.trucksimSolverDir 中传入本机路径。']);
end
if isempty(trucksimSimFile) || exist(trucksimSimFile, 'file') ~= 2
    error('run_single_python_case:NoTrucksimSimFile', ...
        ['找不到 TruckSim simfile.sim。请设置环境变量 P2_TRUCKSIM_SIMFILE，' ...
         '或在 opt.trucksimSimFile 中传入本机路径。']);
end
if exist(trucksimMlDir, 'dir') == 7
    addpath(trucksimMlDir, trucksimSolverDir, '-begin');
else
    addpath(trucksimSolverDir, '-begin');
end

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
logDir  = fullfile(tempdir, ['p2_log_' datestr(now, 'yyyymmdd_HHMMSS')]);
mkdir(logDir);
logFile = fullfile(logDir, 'server_stdout.log');
serverPy = fullfile(controllerRoot, 'tcp', 'tcp_server.py');

% 用例复制到 ASCII 临时路径，避免 system() 命令里的中文路径被 cmd 乱码
asciiCase = fullfile(tempdir, 'p2_case_current.txt');
copyfile(caseFile, asciiCase);

oldDir = cd(fullfile(controllerRoot, 'tcp'));
setenv('PYTHONIOENCODING', 'utf-8');
setenv('P2_TRUCKSIM_SIMFILE', trucksimSimFile);
configTrucksim = normalize_trucksim_com_mode(useTrucksimCom);
cmd = sprintf('start /b "" "%s" tcp_server.py --case "%s" --port %d --log-dir "%s" --config-trucksim %s > "%s" 2>&1', ...
    pythonExe, asciiCase, port, logDir, configTrucksim, logFile);
[st, ~] = system(cmd);
cd(oldDir);
if st ~= 0
    error('run_single_python_case:PyLaunch', '无法启动 Python 服务: %s', cmd);
end

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
for k = 1:60
    pause(0.2);
    if exist(logFile, 'file') && contains(fileread(logFile), 'SERVER_STOPPED')
        break;
    end
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

% TruckSim 实际输入（TCP Client 输出的 6 路转角）拆成三轴后加入导出
try
    dc = out.delta_cmd6;
    if isa(dc, 'timeseries')
        dt6 = dc.Time;
        assignin('base', 'delta1_actual', timeseries(dc.Data(:, 1), dt6));
        assignin('base', 'delta2_actual', timeseries(dc.Data(:, 3), dt6));
        assignin('base', 'delta3_actual', timeseries(dc.Data(:, 5), dt6));
    end
catch
    warning('run_single_python_case:NoDeltaCmd', '未取到 delta_cmd6（TruckSim 实际输入），相关列跳过。');
end
try
    tt = out.tout;
catch
    tt = out.x_trucksim.Time;
end
assignin('base', 't', tt(:));
% 仅存在于 base 工作区的变量（不从 out 读取，避免 SimulationOutput 缺字段警告覆盖为空值）
baseOnly = {'t', 'delta1_actual', 'delta2_actual', 'delta3_actual'};
for i = 1:size(signals, 1)
    v = signals{i, 1};
    if any(strcmp(v, baseOnly)), continue; end
    try
        assignin('base', v, out.(v));
    catch
        warning('run_single_python_case:NoOutVar', '缺少输出: %s', v);
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
end

% ----------------------------------------------------------------------
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
