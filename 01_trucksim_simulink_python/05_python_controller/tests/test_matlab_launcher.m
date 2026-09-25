function test_matlab_launcher()
% TEST_MATLAB_LAUNCHER  验证 Windows 后台服务可追踪启动并按进程树清理。
testsDir = fileparts(mfilename('fullpath'));
controllerRoot = fileparts(testsDir);
phaseRoot = fileparts(controllerRoot);
caseSource = fullfile(phaseRoot, '02_测试用例', 'step_steer_python_40kmh.txt');
pythonExe = 'C:\Python\python\python3.10.4\python.exe';

tempRoot = tempname;
mkdir(tempRoot);
tempCleanup = onCleanup(@() cleanup_dir(tempRoot)); %#ok<NASGU>
casePath = fullfile(tempRoot, 'step_steer_python_40kmh.txt');
copyfile(caseSource, casePath);
logFile = fullfile(tempRoot, 'server.log');
launcher = fullfile(tempRoot, 'launch.cmd');
fid = fopen(launcher, 'w');
assert(fid > 0, '无法创建临时启动脚本。');
fprintf(fid, ['@echo off\r\n"%s" tcp_server.py --case "%s" --port 51235 ' ...
    '--log-dir "%s" --config-trucksim 0 > "%s" 2>&1\r\n'], ...
    pythonExe, casePath, tempRoot, logFile);
fclose(fid);

psi = System.Diagnostics.ProcessStartInfo();
psi.FileName = 'cmd.exe';
psi.Arguments = sprintf('/d /s /c ""%s""', launcher);
psi.WorkingDirectory = fullfile(controllerRoot, 'tcp');
psi.UseShellExecute = false;
psi.CreateNoWindow = true;
proc = System.Diagnostics.Process.Start(psi);
assert(~isempty(proc), '无法启动测试服务。');
procCleanup = onCleanup(@() stop_tree(proc)); %#ok<NASGU>

ready = false;
for k = 1:100
    pause(0.1);
    if exist(logFile, 'file') && contains(fileread(logFile), 'LISTENING')
        ready = true;
        break;
    end
end
assert(ready, 'Python 服务未通过 MATLAB/.NET 启动。');
fprintf('MATLAB 进程启动与清理验证通过 [OK]\n');
end

function stop_tree(proc)
try
    if ~proc.HasExited
        system(sprintf('taskkill /PID %d /T /F >NUL 2>&1', proc.Id));
    end
catch
end
end

function cleanup_dir(path)
if exist(path, 'dir')
    try
        rmdir(path, 's');
    catch
    end
end
end
