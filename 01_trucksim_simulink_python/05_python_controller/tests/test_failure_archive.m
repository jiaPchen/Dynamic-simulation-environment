function test_failure_archive()
% 离线验证：Python 启动失败时不等待完整超时，并保存可追溯诊断文件。
testsDir = fileparts(mfilename('fullpath'));
phaseRoot = fileparts(fileparts(testsDir));
scriptDir = fullfile(phaseRoot, '01_一键启动脚本');
addpath(scriptDir);
tempRoot = tempname;
mkdir(tempRoot);
cleanup = onCleanup(@() rmdir(tempRoot, 's')); %#ok<NASGU>
reportRoot = fullfile(tempRoot, 'reports');
dataRoot = fullfile(tempRoot, 'data');
caseFile = fullfile(phaseRoot, '02_测试用例', 'step_steer_python_20kmh.txt');
opt = struct('pythonExe', fullfile(tempRoot, 'missing_python.exe'), ...
    'reportRoot', reportRoot, 'dataRoot', dataRoot, 'generateReport', false);
try
    run_single_python_case(caseFile, opt);
    error('test_failure_archive:UnexpectedSuccess', '不存在的 Python 不应启动成功。');
catch ME
    assert(strcmp(ME.identifier, 'run_single_python_case:CaseFailed'), ...
        '错误应携带诊断目录，实际为 %s: %s', ME.identifier, ME.message);
    assert(contains(ME.message, '诊断目录:'));
end
failureRoot = fullfile(reportRoot, 'failed_cases');
folders = dir(failureRoot);
folders = folders([folders.isdir] & ~ismember({folders.name}, {'.', '..'}));
assert(numel(folders) == 1, '应只产生一个失败诊断目录。');
diagnosticDir = fullfile(failureRoot, folders(1).name);
assert(exist(fullfile(diagnosticDir, 'case.txt'), 'file') == 2);
assert(exist(fullfile(diagnosticDir, 'error.txt'), 'file') == 2);
assert(exist(fullfile(diagnosticDir, 'python_stdout.log'), 'file') == 2);
fprintf('阶段二失败日志归档测试通过。\n');
end
