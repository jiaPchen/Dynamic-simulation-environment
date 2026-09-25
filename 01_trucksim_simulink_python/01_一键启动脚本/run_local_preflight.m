function info = run_local_preflight()
% RUN_LOCAL_PREFLIGHT  阶段二本机环境只读预检。
% 不启动仿真，不启动 Python 服务，不修改 simfile.sim 或 TruckSim .par 文件。

scriptDir = fileparts(mfilename('fullpath'));
phase2Root = fileparts(scriptDir);
pythonExe = 'C:\Python\python\python3.10.4\python.exe';
trucksimSolverDir = 'C:\Trucksim2019\TruckSim2019.0_Prog\Programs\solvers';
trucksimMlDir = fullfile(trucksimSolverDir, 'Matlab84+');
simfilePointer = fullfile(phase2Root, 'runtime', 'trucksim_phase2.path');
assert(exist(simfilePointer, 'file') == 2, 'run_local_preflight:Missing', ...
    '阶段二专用simfile记录不存在: %s；请先运行capture_phase2_simfile。', simfilePointer);
trucksimSimFile = strtrim(fileread(simfilePointer));
mdlName = 'three_axle_vehicle_2dof_3dof_Trucksim_python';
mdlPath = fullfile(phase2Root, '00_simulink', [mdlName '.slx']);

required = {
    '阶段二根目录', phase2Root, 'dir';
    'Python 解释器', pythonExe, 'file';
    'TruckSim solver 目录', trucksimSolverDir, 'dir';
    'TruckSim Matlab84+ 目录', trucksimMlDir, 'dir';
    'TruckSim simfile', trucksimSimFile, 'file';
    'Simulink 模型', mdlPath, 'file';
    'TCP 客户端 S-Function', fullfile(phase2Root, '00_simulink', 'tcp_client_sfun.m'), 'file';
};

fprintf('========== 阶段二本机环境预检 ==========\n');
fprintf('MATLAB: %s\n', version);
for i = 1:size(required, 1)
    label = required{i, 1};
    pathValue = required{i, 2};
    kind = required{i, 3};
    if strcmp(kind, 'dir')
        ok = exist(pathValue, 'dir') == 7;
    else
        ok = isfile(pathValue);
    end
    assert(ok, 'run_local_preflight:Missing', '%s 不存在: %s', label, pathValue);
    fprintf('[OK] %s: %s\n', label, pathValue);
end

[depStatus, depOutput] = system(sprintf( ...
    '"%s" -c "import yaml,numpy,matplotlib,docx"', pythonExe));
assert(depStatus == 0, 'run_local_preflight:PythonDeps', ...
    'Python 核心依赖缺失或解释器不可用: %s', strtrim(depOutput));
fprintf('[OK] Python 核心依赖: yaml/numpy/matplotlib/docx\n');

simfileText = fileread(trucksimSimFile);
imp = regexp(simfileText, '(?m)^\s*PORTS_IMP\s+(\d+)\s*,\s*(\d+)\s*$', 'tokens', 'once');
exp = regexp(simfileText, '(?m)^\s*PORTS_EXP\s+(\d+)\s*,\s*(\d+)\s*$', 'tokens', 'once');
assert(~isempty(imp) && ~isempty(exp) && ...
    str2double(imp{1}) == 1 && str2double(imp{2}) == 6 && ...
    str2double(exp{1}) == 1 && str2double(exp{2}) == 27, ...
    'run_local_preflight:PortContract', ...
    '阶段二 simfile 的固定接口应为 PORTS_IMP 1,6 / PORTS_EXP 1,27: %s', trucksimSimFile);
inputPar = resolve_input_from_simfile(trucksimSimFile, simfileText);
assert(exist(inputPar, 'file') == 2, 'run_local_preflight:MissingRunPar', ...
    '阶段二 simfile 的 INPUT 参数文件不存在: %s', inputPar);
fprintf('[OK] simfile 固定端口 6 输入/27 输出；INPUT: %s\n', inputPar);

addpath(trucksimSolverDir, trucksimMlDir, '-begin');
assert(exist('vs_sf', 'file') == 3, 'run_local_preflight:NoMex', ...
    '未找到可加载的 TruckSim MEX: vs_sf');
fprintf('[OK] TruckSim MEX: %s\n', which('vs_sf'));

load_system(mdlPath);
sfunBlk = [mdlName '/TruckSim S-Function2'];
tcpBlk = [mdlName '/TCP Client'];
assert(getSimulinkBlockHandle(sfunBlk) >= 0, ...
    'run_local_preflight:NoSfun', '模型缺少 TruckSim S-Function: %s', sfunBlk);
assert(getSimulinkBlockHandle(tcpBlk) >= 0, ...
    'run_local_preflight:NoTcp', '模型缺少 TCP Client: %s', tcpBlk);
fprintf('[OK] 模型已加载，TruckSim 与 TCP 块均存在。\n');
fprintf('预检通过：下一步可在确认 TruckSim 数据备份后运行 run_case_python。\n');

info = struct('phase2Root', phase2Root, 'pythonExe', pythonExe, ...
    'trucksimSolverDir', trucksimSolverDir, 'trucksimSimFile', trucksimSimFile, ...
    'trucksimInputPar', inputPar, 'modelPath', mdlPath);
end

function inputPath = resolve_input_from_simfile(simfile, simfileText)
macros = regexp(simfileText, '(?m)^\s*SET_MACRO\s+(\S+)\s+(.+?)\s*$', 'tokens');
token = regexp(simfileText, '(?m)^\s*INPUT\s+(.+?)\s*$', 'tokens', 'once');
assert(~isempty(token), 'run_local_preflight:NoInput', ...
    'simfile 中没有 INPUT 行: %s', simfile);
expr = token{1};
for k = 1:numel(macros)
    expr = strrep(expr, macros{k}{1}, macros{k}{2});
end
assert(~contains(expr, '$('), 'run_local_preflight:UnresolvedMacro', ...
    'simfile 的 INPUT 含未解析宏: %s', expr);
expr = strrep(strtrim(expr), '/', filesep);
if ~(numel(expr) >= 3 && isletter(expr(1)) && expr(2) == ':' && ...
        (expr(3) == char(92) || expr(3) == '/'))
    expr = fullfile(fileparts(simfile), expr);
end
inputPath = char(java.io.File(expr).getCanonicalPath());
end
