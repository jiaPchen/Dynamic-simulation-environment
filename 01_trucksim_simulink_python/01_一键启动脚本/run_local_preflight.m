function info = run_local_preflight()
% RUN_LOCAL_PREFLIGHT  阶段二本机环境只读预检。
% 不启动仿真，不启动 Python 服务，不修改 simfile.sim 或 TruckSim .par 文件。

scriptDir = fileparts(mfilename('fullpath'));
phase2Root = fileparts(scriptDir);
pythonExe = 'C:\Python\python\python3.10.4\python.exe';
trucksimSolverDir = 'C:\Trucksim2019\TruckSim2019.0_Prog\Programs\solvers';
trucksimMlDir = fullfile(trucksimSolverDir, 'Matlab84+');
trucksimSimFile = 'C:\Trucksim2019\TruckSim2019.0_Data\simfile.sim';
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
        ok = exist(pathValue, 'file') == 2;
    end
    assert(ok, 'run_local_preflight:Missing', '%s 不存在: %s', label, pathValue);
    fprintf('[OK] %s: %s\n', label, pathValue);
end

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
    'modelPath', mdlPath);
end
