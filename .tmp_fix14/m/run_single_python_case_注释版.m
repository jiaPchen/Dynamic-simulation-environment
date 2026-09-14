function [runNo, ioDir] = run_single_python_case(caseFile, opt)
% RUN_SINGLE_PYTHON_CASE  阶段二：Python 闭环联仿单工况运行（本文件为逐行注释版）
%  流程：解析 TXT -> 启动 Python TCP 服务（可选 COM 配置 TruckSim）
%       -> 运行 Simulink（TCP 客户端 S-Function 闭环）
%       -> 导出 CSV -> 调用 Python 生成单工况报告
%  输入：
%    caseFile  TXT 测试用例绝对路径
%    opt       可选结构体：dataRoot/userName/pythonExe/port/
%              useTrucksimCom/mdlName/mdlPath/controllerRoot/reportRoot
%  输出：
%    runNo     本次运行编号

%% ---------- 0. 默认配置 ----------
if nargin < 2, opt = struct(); end          % 若未传 opt，则用空结构体（全部取默认值）

phase2Root = 'D:\动力学仿真环境阶段二\01_trucksim_simulink_python';  % 阶段二 Python 链路根目录
mdlName  = getopt(opt, 'mdlName',  'three_axle_vehicle_2dof_3dof_Trucksim_python');  % 模型名（默认 Python 联仿模型）
mdlPath  = getopt(opt, 'mdlPath',  fullfile(phase2Root, '00_simulink', [mdlName '.slx']));  % 模型文件绝对路径
dataRoot = getopt(opt, 'dataRoot', fullfile(phase2Root, '03_数据存储'));  % 数据存储根目录
userName = getopt(opt, 'userName', 'Python联仿');  % 使用者子目录名
reportRoot  = getopt(opt, 'reportRoot',  fullfile(phase2Root, '04_测试报告'));  % 报告根目录
caseDir     = getopt(opt, 'caseDir',     fullfile(phase2Root, '02_测试用例'));  % 用例目录
controllerRoot = getopt(opt, 'controllerRoot', fullfile(phase2Root, '05_python_controller'));  % Python 控制器根目录
pythonExe = getopt(opt, 'pythonExe', 'D:\05_python\python.exe');  % Python 解释器
port      = getopt(opt, 'port', 50007);     % TCP 端口（与 tcp_server.py / S-Function 一致）
useTrucksimCom = getopt(opt, 'useTrucksimCom', false);  % 是否启用 TruckSim COM 配置（默认否）
generateReport = getopt(opt, 'generateReport', true);   % 是否生成单工况报告（批量时置 false）

trucksimSolverDir = 'D:\04_trucksim\TruckSim2019.0_Prog\Programs\solvers';  % TruckSim 求解器目录
trucksimMlDir     = fullfile(trucksimSolverDir, 'Matlab84+');               % MATLAB 接口目录
trucksimSimFile   = 'D:\04_trucksim\TruckSim2019.0_Data\simfile.sim';       % simfile 绝对路径
addpath(trucksimMlDir, trucksimSolverDir, '-begin');  % 把 TruckSim 路径加到搜索路径最前

scriptDir = fileparts(mfilename('fullpath'));  % 本脚本所在目录
addpath(scriptDir);                        % parse_case.m / export_case_csv.m
addpath(fileparts(mdlPath));               % tcp_client_sfun.m 所在目录（模型目录）

%% ---------- 1. 解析测试用例 ----------
c = parse_case(caseFile);                  % 调用 parse_case.m 解析 TXT，返回结构体 c（字段为字符串）
fprintf('[阶段二] Case: %s | v0=%.1f km/h | steer=%s | t_end=%.1f s\n', ...  % 打印用例概要
    c.case_name, str2double(c.initial_speed_kmh), c.steer_input_type, ...   % 参数：用例名/初始车速/转向类型
    str2double(c.stop_time_s));            % 参数：仿真时长

%% ---------- 2. 加载模型并设置 simfile ----------
if ~bdIsLoaded(mdlName)                    % 如果模型尚未加载
    load_system(mdlPath);                  % 从磁盘加载模型
end                                        % 结束 if
sfunBlk = [mdlName '/TruckSim S-Function2'];  % TruckSim S-Function 块路径
if getSimulinkBlockHandle(sfunBlk) >= 0    % 如果块存在
    set_param(sfunBlk, 'SIMFILE', trucksimSimFile);  % 把 SIMFILE 设为绝对路径
else                                       % 否则
    error('run_single_python_case:NoSfun', '找不到 TruckSim S-Function: %s', sfunBlk);  % 报错
end                                        % 结束 if
tcpBlk = [mdlName '/TCP Client'];          % TCP Client 块路径
if getSimulinkBlockHandle(tcpBlk) < 0      % 如果块不存在
    error('run_single_python_case:NoTcp', ...  % 报错提示用错模型
        '模型缺少 TCP Client 块，请确认使用 %s 模型', mdlName);  % 错误信息
end                                        % 结束 if

%% ---------- 3. 启动 Python TCP 服务 ----------
logDir  = fullfile(tempdir, ['p2_log_' datestr(now, 'yyyymmdd_HHMMSS')]);  % 本次服务日志目录（临时目录）
mkdir(logDir);                             % 创建日志目录
logFile = fullfile(logDir, 'server_stdout.log');  % 服务标准输出日志文件
serverPy = fullfile(controllerRoot, 'tcp', 'tcp_server.py');  % 服务脚本路径

% 用例复制到 ASCII 临时路径，避免 system() 命令里的中文路径被 cmd 乱码
asciiCase = fullfile(tempdir, 'p2_case_current.txt');  % ASCII 临时用例路径
copyfile(caseFile, asciiCase);             % 复制用例到临时路径

oldDir = cd(fullfile(controllerRoot, 'tcp'));  % 切到服务脚本目录（命令里不含中文路径）
cmd = sprintf('start /b "" "%s" tcp_server.py --case "%s" --port %d --log-dir "%s" --config-trucksim %d > "%s" 2>&1', ...
    pythonExe, asciiCase, port, logDir, double(useTrucksimCom), logFile);  % 拼出启动命令（后台启动并重定向日志）
[st, ~] = system(cmd);                     % 执行命令（start /b 立即返回）
cd(oldDir);                                % 切回原目录
if st ~= 0                                 % 如果启动失败
    error('run_single_python_case:PyLaunch', '无法启动 Python 服务: %s', cmd);  % 报错
end                                        % 结束 if

ready = false;                             % 就绪标志
for k = 1:180                              % 最多轮询 180 次
    pause(0.5);                            % 每 0.5s 检查一次
    if exist(logFile, 'file')              % 如果日志文件已生成
        txt = fileread(logFile);           % 读取日志内容
        if contains(txt, 'LISTENING')      % 如果服务已开始监听
            ready = true;                  % 置就绪
            break;                         % 跳出循环
        end                                % 结束 if
        if contains(txt, 'CONFIG_FAIL')    % 若是 COM 配置失败
            error('run_single_python_case:ComConfigFailed', ...  % 报针对性错误
                ['TruckSim COM 配置失败，Python 服务已退出。常见原因：TruckSim 未打开、' ...
                 '该版本未注册 COM 自动化接口，或控件名映射未验证。' ...
                 '请保持 useTrucksimCom=false 以固定 simfile 工况运行，' ...
                 '或先运行 probe_trucksim_com.py 验证映射。\n日志：\n%s'], txt);  % 附日志
        elseif contains(txt, 'SERVER_ERROR') || contains(txt, 'Traceback')  % 其他启动失败
            error('run_single_python_case:PyStart', 'Python 服务启动失败:\n%s', txt);  % 报错并附日志
        end                                % 结束 if
    end                                    % 结束 if
end                                        % 结束 for
if ~ready                                  % 如果超时仍未就绪
    error('run_single_python_case:PyTimeout', '等待 Python 服务 LISTENING 超时(90s)');  % 报错
end                                        % 结束 if
fprintf('[阶段二] Python 服务已就绪 (port=%d)\n', port);  % 打印就绪信息

%% ---------- 4. 运行仿真（TCP 闭环） ----------
assignin('base', 'tcp_port', port);        % 供 tcp_client_sfun 读取，避免端口不一致
fprintf('[阶段二] 运行仿真: %s ...\n', c.case_name);  % 打印开始仿真
try                                        % 尝试执行仿真
    out = sim(mdlName, 'StopTime', c.stop_time_s);  % 运行 Simulink 仿真，结果存 out
catch ME                                   % 如果仿真报错
    fprintf('[阶段二] 仿真失败，错误如下（请复制发给维护者）：\n');  % 提示
    fprintf('%s\n', ME.message);           % 打印主错误信息
    for k = 1:numel(ME.cause)              % 遍历错误原因链
        fprintf('  原因: %s\n', ME.cause{k}.message);  % 打印每层原因
    end                                    % 结束 for
    rethrow(ME);                           % 重新抛出错误（保留原始堆栈）
end                                        % 结束 try
fprintf('[阶段二] 仿真结束\n');            % 打印仿真结束

%% ---------- 5. 等待 Python 服务退出 ----------
for k = 1:60                               % 最多等 12s
    pause(0.2);                            % 每 0.2s 检查
    if exist(logFile, 'file') && contains(fileread(logFile), 'SERVER_STOPPED')  % 若服务已正常退出
        break;                             % 跳出
    end                                    % 结束 if
end                                        % 结束 for

%% ---------- 6. 导出 CSV ----------
signals = {                                % 信号映射表：To Workspace 变量名 -> CSV 列名
    't',                'sim_time_s';      % 时间
    'Vx_trucksim',      'state_vehicle_speed_kmh';  % 车速
    'beta_trucksim',    'state_beta_trucksim_deg';  % 质心侧偏角
    'w_trucksim',       'state_yaw_rate_trucksim_degps';  % 横摆角速度
    'x_trucksim',       'state_x_m';       % 纵向位置
    'y_trucksim',       'state_y_m';       % 横向位置
    'xt_trucksim',      'state_xt_m';      % 挂车纵向位置
    'yt_trucksim',      'state_yt_m';      % 挂车横向位置
};
try                                        % 尝试
    tt = out.tout;                         % 取 sim() 返回的时间向量
catch                                      % 如果没有 tout
    tt = out.x_trucksim.Time;              % 退而用某条 timeseries 的时间轴
end                                        % 结束 try
assignin('base', 't', tt(:));              % 把时间写入 base 工作区变量 t
% 仅存在于 base 工作区的变量（不从 out 读取，避免 SimulationOutput 缺字段警告覆盖为空值）
baseOnly = {'t', 'delta1_actual', 'delta2_actual', 'delta3_actual'};  % base 专用变量名
for i = 1:size(signals, 1)                 % 遍历信号表
    v = signals{i, 1};                     % 取变量名
    if any(strcmp(v, baseOnly)), continue; end  % base 专用变量跳过（不从 out 读）
    try                                    % 尝试
        assignin('base', v, out.(v));      % 把 out 里该信号写回 base 工作区
    catch                                  % 如果缺少该字段
        warning('run_single_python_case:NoOutVar', '缺少输出: %s', v);  % 告警跳过
    end                                    % 结束 try
end                                        % 结束 for

[ioCsv, ~, runNo] = export_case_csv(dataRoot, userName, c, signals);  % 调用导出函数：生成 CSV 并返回路径/编号
ioDir = fileparts(ioCsv);                  % 取运行数据目录

% 把 Python 侧信号与日志并入运行目录
pylog = fullfile(logDir, 'python_signals.csv');  % Python 侧信号文件路径
if exist(pylog, 'file')                    % 如果存在
    copyfile(pylog, fullfile(ioDir, [runNo '_python_signals.csv']));  % 复制进运行目录
end                                        % 结束 if
copyfile(logFile, fullfile(ioDir, [runNo '_python_stdout.log']));  % 复制服务日志
copyfile(caseFile, fullfile(ioDir, [runNo '_case.txt']));  % 复制用例副本（可追溯）
fprintf('[阶段二] CSV 已保存: %s\n', ioDir);  % 打印保存位置

%% ---------- 7. 生成单工况报告 ----------
if generateReport                          % 若开启单工况报告（批量时关闭）
    pyScript = fullfile(controllerRoot, 'report', 'make_report_python.py');  % 报告脚本路径
    oldDir = cd(fullfile(controllerRoot, 'report'));  % 切到报告脚本目录
    setenv('P2_RUN_DIR', ioDir);           % 运行目录通过环境变量传入 Python
    setenv('P2_REPORT_ROOT', reportRoot);  % 报告根目录通过环境变量传入
    cmd = sprintf('"%s" make_report_python.py', pythonExe);  % 命令行（无中文参数，避免乱码）
    fprintf('[阶段二] 生成报告: %s ...\n', cmd);  % 打印命令
    [st, msg] = system(cmd);               % 执行报告脚本
    cd(oldDir);                            % 切回原目录
    if st ~= 0                             % 如果失败
        warning('run_single_python_case:ReportFailed', ...  % 告警
            '报告生成失败(exit=%d):\n%s', st, msg);  % 显示退出码和输出
    else                                   % 否则
        fprintf('[阶段二] 报告已生成\n');  % 打印成功
    end                                    % 结束 if
end                                        % 结束 if generateReport
end                                        % 函数结束

% ----------------------------------------------------------------------
function v = getopt(opt, name, dflt)       % 工具函数：从 opt 取配置项，取不到用默认值
if isfield(opt, name) && ~isempty(opt.(name))  % 如果存在且非空
    v = opt.(name);                        % 用传入值
else                                       % 否则
    v = dflt;                              % 用默认值
end                                        % 结束 if
end                                        % 函数结束
