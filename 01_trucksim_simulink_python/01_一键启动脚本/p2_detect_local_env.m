function env = p2_detect_local_env(phase2Root)
% P2_DETECT_LOCAL_ENV  Detect local executable/data paths for migrated PCs.
%
% Optional environment overrides:
%   P2_PYTHON_EXE          Python executable
%   P2_TRUCKSIM_SIMFILE    TruckSim simfile.sim used by the S-Function
%   P2_TRUCKSIM_SOLVER_DIR TruckSim solver directory

if nargin < 1 || isempty(phase2Root)
    phase2Root = fileparts(fileparts(mfilename('fullpath')));
end

env = struct();
env.phase2Root = phase2Root;
env.pythonExe = detect_python_exe(phase2Root);
env.trucksimSimFile = detect_existing_file('P2_TRUCKSIM_SIMFILE', {
    'C:\Trucksim2019\TruckSim2019.0_Data\simfile.sim'
    'C:\04_trucksim\TruckSim2019.0_Data\simfile.sim'
    'D:\04_trucksim\TruckSim2019.0_Data\simfile.sim'
});
env.trucksimSolverDir = detect_existing_dir('P2_TRUCKSIM_SOLVER_DIR', {
    'C:\Trucksim2019\TruckSim2019.0_Prog\Programs\solvers'
    'C:\04_trucksim\TruckSim2019.0_Prog\Programs\solvers'
    'D:\04_trucksim\TruckSim2019.0_Prog\Programs\solvers'
});
end

% ----------------------------------------------------------------------
function path = detect_python_exe(phase2Root)
path = detect_existing_file('P2_PYTHON_EXE', {
    fullfile(phase2Root, '05_python_controller', '.venv', 'Scripts', 'python.exe')
    'C:\Python\python\python3.10.4\python.exe'
    'D:\05_python\python.exe'
});
if ~isempty(path)
    return;
end

[st, out] = system('where python');
if st == 0
    lines = regexp(strtrim(out), '\r?\n', 'split');
    for i = 1:numel(lines)
        candidate = strtrim(lines{i});
        if exist(candidate, 'file') == 2
            path = candidate;
            return;
        end
    end
end

path = 'python';
end

% ----------------------------------------------------------------------
function path = detect_existing_file(envName, candidates)
override = strtrim(getenv(envName));
if ~isempty(override)
    if exist(override, 'file') == 2
        path = override;
        return;
    end
    warning('p2_detect_local_env:BadFileOverride', ...
        '%s 指向的文件不存在: %s', envName, override);
end

path = '';
for i = 1:numel(candidates)
    candidate = candidates{i};
    if exist(candidate, 'file') == 2
        path = candidate;
        return;
    end
end
end

% ----------------------------------------------------------------------
function path = detect_existing_dir(envName, candidates)
override = strtrim(getenv(envName));
if ~isempty(override)
    if exist(override, 'dir') == 7
        path = override;
        return;
    end
    warning('p2_detect_local_env:BadDirOverride', ...
        '%s 指向的目录不存在: %s', envName, override);
end

path = '';
for i = 1:numel(candidates)
    candidate = candidates{i};
    if exist(candidate, 'dir') == 7
        path = candidate;
        return;
    end
end
end
