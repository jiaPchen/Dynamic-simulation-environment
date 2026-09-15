%% run_case_new.m  -  一键启动脚本（适配 new_three_axle_vehicle_2dof_3dof_Trucksim）
%  ============================================================
%  本文件为“逐行注释版”，仅供学习理解使用，运行请用 run_case_new.m。
%  注释版基于 2026-08-29 19:56 的 run_case_new.m 逐行添加说明。
%  ============================================================
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

clear; clc;                        % 清空 MATLAB 工作区变量并清空命令窗口（避免旧变量干扰）

%% ===================== 0. 用户配置 =====================
mdlName  = 'new_three_axle_vehicle_2dof_3dof_Trucksim';   % 此处输入自己需要运行的Simulink模型名称
mdlPath  = 'D:\动力学仿真环境\00_simulink\new_three_axle_vehicle_2dof_3dof_Trucksim.slx';  % 模型文件绝对路径
caseFile = 'D:\动力学仿真环境\02_测试用例\sine_steer_40kmh.txt';   % 此处输入本次要运行的测试用例文件路径
dataRoot = 'D:\动力学仿真环境\03_数据存储';               % 自己选择数据需要存储的根目录（先建立好对于文件夹位置）
userName = '正弦输入转角';                                % 数据存放的子文件夹名（按工况/人员区分）

% 启用 TruckSim COM 参数修改前，请先完成 trucksim_config.m 的
% TXT 字段 -> TruckSim 控制项映射（当前未验证，保持 false）。
useTrucksimCom = false;            % 是否通过 COM 修改 TruckSim 侧参数；暂未实现映射，保持 false

% Python 解释器（make_test_report_new.py 使用）
pythonExe = 'D:\05_python\python.exe';   % Python 可执行文件路径（报告脚本依赖 numpy/matplotlib/python-docx）
generateReport = true;   % 仿真结束后自动生成曲线图与 Word 测试报告（true=生成）

% TruckSim S-Function 运行环境与 simfile（必须绝对路径）
trucksimSolverDir = 'D:\04_trucksim\TruckSim2019.0_Prog\Programs\solvers';  % TruckSim 求解器目录（Solver64.exe 等）
trucksimMlDir     = fullfile(trucksimSolverDir, 'Matlab84+');               % MATLAB 接口目录（含 Solver_SF.slx 库）
trucksimSimFile   = 'D:\04_trucksim\TruckSim2019.0_Data\simfile.sim';       % TruckSim 数据文件（固定工况来源）
addpath(trucksimMlDir, trucksimSolverDir, '-begin');   % 把 TruckSim 目录加到 MATLAB 搜索路径最前面
if ~exist(trucksimSimFile, 'file')                     % 如果 simfile 文件不存在
    warning('run_case_new:NoSimFile', 'TruckSim simfile not found: %s', trucksimSimFile);  % 只告警不中断
end                                                    % 结束 if

%% ===================== 1. 解析测试用例 =====================
c = parse_case(caseFile);          % 调用 parse_case.m 解析 TXT，返回结构体 c（字段均为字符串）
fprintf('Case: %s | v0=%.2f km/h | steer=%s | t_end=%.2f s\n', ...   % 打印用例概要（工况名/初始车速/转向类型/时长）
    c.case_name, str2double(c.initial_speed_kmh), c.steer_input_type, ...  % 格式参数1：用例名、初始车速（转数值）、转向类型
    str2double(c.stop_time_s));    % 格式参数2：仿真时长（转数值），\n 表示换行

%% ===================== 2. 加载模型 =====================
if ~bdIsLoaded(mdlName)            % 如果模型还没有加载到内存
    load_system(mdlPath);          % 从磁盘加载 .slx 模型
end                                % 结束 if

% 防呆检查：模型必须包含 "Steering Input"（From Workspace）转向输入块。
% 若被误删，请先运行 repair_model_new 重建标准接线。
steerBlock = [mdlName '/Steering Input'];   % 拼接出转向输入块的完整路径：模型名/模块名
if getSimulinkBlockHandle(steerBlock) < 0   % 若该块不存在（句柄为负）
    error('run_case_new:NoSteerBlock', ...  % 抛出错误并停止运行
        ['模型缺少 "Steering Input"（From Workspace）块。请在 MATLAB 命令' ...  % 错误提示前半句
         '行运行 repair_model_new 修复模型接线后，再重新运行本脚本。']);         % 错误提示后半句（[...] 拼成完整字符串）
end                                % 结束 if

% TruckSim S-Function 的 simfile 改为绝对路径
sfunBlk = [mdlName '/TruckSim S-Function2'];  % 拼接 TruckSim S-Function 块完整路径
if getSimulinkBlockHandle(sfunBlk) >= 0       % 如果该块存在
    set_param(sfunBlk, 'SIMFILE', trucksimSimFile);  % 把块的 SIMFILE 参数设为绝对路径（避免相对路径解析失败）
    fprintf('TruckSim S-Function SIMFILE set: %s\n', trucksimSimFile);  % 打印设置结果
else                                  % 否则（块不存在）
    warning('run_case_new:NoSfun', 'TruckSim S-Function block not found: %s', sfunBlk);  % 告警提示找不到块
end                                   % 结束 if

%% ===================== 3. 按测试用例生成转向输入 =====================
% 模型内 "Steering Input"（From Workspace）读取 base 工作区的 steer_input
% timeseries，单位：度，仅作用于第一轴；第二/三轴由模型内 Constant 0 固定。
A    = str2double(c.steer_amplitude_deg);   % 转向幅值（度），从用例字符串转成数值
t0   = str2double(c.steer_start_time_s);    % 转向开始时刻（秒）
tEnd = str2double(c.stop_time_s);           % 仿真总时长（秒）
tSim = (0:0.001:tEnd)';                     % 时间轴：0~tEnd 秒，步长 0.001s，转成列向量

switch lower(c.steer_input_type)            % 按用例的转向类型（转小写）分分支
    case 'sine'                             % 正弦转向
        fHz = str2double(c.steer_frequency_hz);  % 转向频率（Hz）
        u = zeros(size(tSim));              % 初始化转向信号全 0（长度与 tSim 相同）
        idx = tSim >= t0;                   % 找到 t>=t0 的时间索引（t0 之前不转向）
        u(idx) = A * sin(2*pi*fHz*(tSim(idx) - t0));  % 正弦公式：A*sin(2πf(t-t0))，单位度
    case 'step'                             % 阶跃转向
        % 真正的阶跃：t < t0 时为 0，t >= t0 后保持 A 度
        u = zeros(size(tSim));              % 初始化转向信号全 0
        u(tSim >= t0) = A;                  % t>=t0 之后全部置为 A 度（阶跃跳变）
    otherwise                               % 其他未知类型
        error('run_case_new:UnknownSteer', 'Unsupported steer_input_type: %s', ...  % 抛错提示类型不支持
            c.steer_input_type);            % 错误信息里带上实际的类型值
end                                         % 结束 switch

steer_input = timeseries(u, tSim);          % 把数据和时刻封装成 timeseries 对象（Simulink From Workspace 支持）
steer_input.Name = 'steer_input';           % 给 timeseries 起名（与模型里 From Workspace 的变量名一致）
assignin('base', 'steer_input', steer_input);   % 写入 MATLAB base 工作区，仿真时模型才能读到
fprintf('Steering input built: type=%s, amplitude=%g deg, start=%.2f s\n', ...  % 打印转向输入生成信息
    c.steer_input_type, A, t0);             % 参数：类型、幅值、开始时刻

%% ===================== 4. TruckSim 参数设置（可选，未启用） =====================
if useTrucksimCom                          % 若启用 TruckSim COM（当前为 false，不进此分支）
    ok = trucksim_config(c);               % 调用 trucksim_config.m 配置 TruckSim（占位函数，未实现）
    if ~ok                                 % 如果配置失败（返回 false）
        error('run_case_new:TrucksimConfig', ...   % 抛错，不继续仿真
            'TruckSim configuration failed; simulation not started.');  % 错误提示
    end                                    % 结束 if
end                                        % 结束 if

%% ===================== 5. 运行仿真 =====================
fprintf('Running simulation: %s ...\n', c.case_name);   % 打印开始仿真的提示
out = sim(mdlName, 'StopTime', c.stop_time_s);          % 运行 Simulink 仿真，StopTime 覆盖为用例时长，结果存入 out
fprintf('Simulation finished.\n');                      % 打印仿真结束提示

% 检查 TruckSim 实际初始车速与用例设定是否一致（仅提示，以 simfile 为准）
try                                                % 尝试执行（可能因输出缺失报错，用 try 兜底）
    v0_actual = out.Vx_trucksim.Data(1);           % 取 TruckSim 车速 timeseries 的第一个采样点（初始车速，km/h）
    v0_case   = str2double(c.initial_speed_kmh);   % 用例设定的初始车速（km/h）
    if abs(v0_actual - v0_case) > 0.5              % 如果两者相差超过 0.5 km/h
        warning('run_case_new:SpeedMismatch', ...  % 告警提示车速不一致
            ['TruckSim 实际初始车速 %.2f km/h 与用例设定 %.2f km/h 不一致' ...  % 提示前半句（%.2f 为占位符）
             '（TruckSim 工况以 simfile 为准）。'], v0_actual, v0_case);  % 提示后半句 + 填充两个数值
    end                                            % 结束 if
catch                                              % 若上面任何一步出错
end                                                % 忽略错误继续执行（只是提示，不影响主流程）

%% ===================== 6. 导出 CSV =====================
% To Workspace 变量 -> CSV 列名（与 make_test_report_new.py 对应）
signals = {                          % 定义信号映射表：左列=模型 To Workspace 变量名，右列=CSV 列名
    't',                'sim_time_s';                 % 仿真时间
    'Vx_trucksim',      'state_vehicle_speed_kmh';    % 车速（km/h）
    'beta_trucksim',    'state_beta_trucksim_deg';    % 质心侧偏角（deg）
    'w_trucksim',       'state_yaw_rate_trucksim_degps';  % 横摆角速度（deg/s）
    'x_trucksim',       'state_x_m';                  % 纵向位置（m）
    'y_trucksim',       'state_y_m';                  % 横向位置（m）
    'xt_trucksim',      'state_xt_m';                 % 挂车纵向位置（m）
    'yt_trucksim',      'state_yt_m';                 % 挂车横向位置（m）
    'delta_input',      'state_steer_delta_deg';      % 第一轴转向输入（deg）
};

% 时间向量：优先取 sim() 的 tout，否则从任意 Timeseries 输出取时间
try                                                % 尝试执行
    tt = out.tout;                                 % 取 sim() 返回的时间向量（配置 SaveTime=on 时存在）
catch                                              % 若没有 tout
    tt = out.x_trucksim.Time;                      % 退而取 x_trucksim 这条 timeseries 自带的时间轴
end                                                % 结束 try
assignin('base', 't', tt(:));                      % 把时间向量写入 base 工作区变量 t（列向量）

for i = 1:size(signals, 1)                         % 遍历 signals 每一行（i 从 1 到行数）
    v = signals{i, 1};                             % 取第 i 行的 To Workspace 变量名
    if strcmp(v, 't'), continue; end               % 变量名是 t 就跳过（t 已在上面单独处理）
    try                                            % 尝试执行
        assignin('base', v, out.(v));              % 把 out 里的该信号写回 base 工作区（动态字段名）
    catch                                          % 如果 out 里没有这个字段
        warning('run_case_new:NoOutVar', 'sim() output has no field "%s".', v);  % 告警并跳过该列
    end                                            % 结束 try
end                                                % 结束 for

[ioCsv, infoCsv, runNo] = export_case_csv(dataRoot, userName, c, signals);  % 调用导出函数：生成 CSV 并返回文件路径和运行编号
fprintf('CSV saved:\n  %s\n  %s\n', ioCsv, infoCsv);   % 打印两个 CSV 文件的保存路径

%% ===================== 7. 生成报告 =====================
% 调用 make_test_report_new.py 绘制曲线并生成 Word 测试报告，
% 输出到 04_测试报告\<运行编号>\。运行编号写入临时标记文件，
% 由 make_test_report_new.py 自动读取。
if generateReport                             % 如果开启了自动生成报告
    scriptDir = fileparts(mfilename('fullpath'));   % 取本脚本所在目录（01_一键启动脚本）
    pyScript  = fullfile(scriptDir, 'make_test_report_new.py');  % 报告脚本的完整路径
    if exist(pyScript, 'file')                % 如果报告脚本存在
        if exist(pythonExe, 'file')           % 如果 Python 存在
            logFile    = fullfile(tempdir, 'make_test_report.log');  % 报告脚本日志文件（临时目录）
            markerFile = fullfile(tempdir, 'codex_last_run_no.txt'); % 运行编号标记文件（临时目录）
            fid = fopen(markerFile, 'w', 'n', 'UTF-8');   % 以 UTF-8 写模式打开标记文件，返回文件句柄
            if fid > 0                        % 如果打开成功
                fprintf(fid, '%s', runNo);    % 把本次运行编号写入标记文件
                fclose(fid);                  % 关闭文件
            else                              % 否则（打开失败）
                warning('run_case_new:MarkerWriteFailed', ...   % 告警：无法写标记文件
                    'Cannot write run marker file: %s', markerFile);   % 提示标记文件路径
            end                               % 结束 if
            oldDir = cd(scriptDir);   % 脚本目录作为工作目录，命令不含中文路径（切换到脚本目录并记住原目录）
            try                               % 尝试执行系统命令
                cmd = sprintf('%s make_test_report_new.py', pythonExe);   % 拼出命令行：python 路径 + 脚本名
                fprintf('Generating report via: %s ...\n', cmd);          % 打印将要执行的命令
                [st, msg] = system(cmd);      % 调用系统命令运行报告脚本；st=退出码，msg=输出内容
            catch ME                          % 若命令执行抛异常
                st  = -1;                     % 退出码记为 -1 表示失败
                msg = ME.message;             % 记录异常信息
            end                               % 结束 try
            cd(oldDir);                       % 切回原来的工作目录
            fid = fopen(logFile, 'w');        % 打开日志文件（写模式）
            if fid > 0                        % 如果打开成功
                fprintf(fid, '%s', msg);      % 把报告脚本输出写入日志
                fclose(fid);                  % 关闭日志文件
            end                               % 结束 if
            reportRoot = fullfile(fileparts(scriptDir), '04_测试报告');  % 报告根目录（脚本目录的上一级下）
            reportDir  = fullfile(reportRoot, runNo);   % 本次运行的报告目录：根目录\运行编号
            if st == 0 && exist(reportDir, 'dir')       % 如果退出码为 0 且报告目录已生成
                fprintf('Report generated: %s\n', reportDir);   % 打印报告目录
            else                                % 否则（生成失败）
                warning('run_case_new:ReportFailed', ...  % 告警：报告生成失败
                    ['Report generation failed (exit=%d). ' ...   % 提示前半句（带退出码）
                     'Log saved to %s:\n%s'], st, logFile, msg);  % 提示后半句：日志路径和内容
            end                                 % 结束 if
        else                                    % 否则（Python 不存在）
            warning('run_case_new:NoPython', ...  % 告警：找不到 Python
                'Python not found at %s; report step skipped.', pythonExe);   % 提示路径，跳过报告
        end                                     % 结束 if
    else                                        % 否则（报告脚本不存在）
        warning('run_case_new:NoReportScript', ...  % 告警：找不到报告脚本
            'Report script not found: %s', pyScript);   % 提示脚本路径
    end                                         % 结束 if
end                                             % 结束 if generateReport
