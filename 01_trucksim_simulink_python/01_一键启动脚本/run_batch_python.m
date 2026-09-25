function batchRoot = run_batch_python(continueOnError)
%% run_batch_python  阶段二批量联仿，逐工况记录状态并可在失败后继续
clc;
if nargin < 1, continueOnError = true; end

scriptDir = fileparts(mfilename('fullpath'));
phase2Root = fileparts(scriptDir);
caseDir = fullfile(phase2Root, '02_测试用例');
controllerRoot = fullfile(phase2Root, '05_python_controller');
reportRoot = fullfile(phase2Root, '04_测试报告');
pythonExe = 'C:\Python\python\python3.10.4\python.exe';

batchNo = ['批量仿真_' char(datetime('now', ...
    'Format', 'yyyy年MM月dd日_HH时mm分ss秒_SSS毫秒'))];
batchRoot = fullfile(reportRoot, batchNo);
mkdir(batchRoot);

files = dir(fullfile(caseDir, '*.txt'));
if isempty(files), error('run_batch_python:NoCases', '目录中没有 TXT 用例: %s', caseDir); end

runDirs = {};
statusRows = cell(0, 8);
abortRemaining = false;
for i = 1:numel(files)
    casePath = fullfile(caseDir, files(i).name);
    caseName = files(i).name;
    try
        c = parse_case(casePath);
        caseName = c.case_name;
    catch ME
        statusRows(end + 1, :) = {files(i).name, caseName, 'ERROR', '', '', ...
            ME.identifier, one_line(ME.message), now_iso8601()}; %#ok<AGROW>
        if ~continueOnError, abortRemaining = true; end
        continue;
    end
    if abortRemaining
        statusRows(end + 1, :) = {files(i).name, caseName, 'SKIPPED', '', '', ...
            'run_batch_python:StoppedAfterError', '前序用例失败且 continueOnError=false', now_iso8601()}; %#ok<AGROW>
        continue;
    end

    fprintf('========== 工况 %d/%d: %s ==========\n', i, numel(files), files(i).name);
    opt = struct('dataRoot', batchRoot, 'userName', 'cases', ...
        'reportRoot', batchRoot, 'generateReport', false);
    try
        [runNo, ioDir] = run_single_python_case(casePath, opt);
        runDirs{end + 1} = ioDir; %#ok<AGROW>
        statusRows(end + 1, :) = {files(i).name, caseName, 'COMPLETED', runNo, ioDir, '', '', now_iso8601()}; %#ok<AGROW>
    catch ME
        fprintf(2, '工况失败: %s\n', ME.message);
        statusRows(end + 1, :) = {files(i).name, caseName, 'ERROR', '', diagnostic_dir(ME.message), ...
            ME.identifier, one_line(ME.message), now_iso8601()}; %#ok<AGROW>
        if ~continueOnError, abortRemaining = true; end
    end
end

statusNames = {'case_file','case_name','status','run_number','run_dir', ...
    'error_identifier','error_message','timestamp_local_iso8601'};
writetable(cell2table(statusRows, 'VariableNames', statusNames), ...
    fullfile(batchRoot, '批量运行状态.csv'));

if isempty(runDirs)
    error('run_batch_python:AllCasesFailed', ...
        '没有成功工况；状态已保存到 %s', fullfile(batchRoot, '批量运行状态.csv'));
end

marker = fullfile(batchRoot, 'batch_run_dirs.txt');
fid = fopen(marker, 'w', 'n', 'UTF-8');
if fid < 0, error('run_batch_python:MarkerOpen', '无法创建批量运行目录清单: %s', marker); end
for i = 1:numel(runDirs), fprintf(fid, '%s\n', runDirs{i}); end
fclose(fid);

oldDir = cd(fullfile(controllerRoot, 'report'));
cleanupDir = onCleanup(@() cd(oldDir)); %#ok<NASGU>
cmd = sprintf('"%s" make_batch_summary.py --batch-marker "%s" --report-root "%s" --output-dir "%s"', ...
    pythonExe, marker, reportRoot, batchRoot);
[st, msg] = system(cmd);
if st ~= 0
    error('run_batch_python:BatchSummaryFailed', '批量汇总报告生成失败(exit=%d):\n%s', st, msg);
end

nOk = sum(strcmp(statusRows(:, 3), 'COMPLETED'));
nErr = sum(strcmp(statusRows(:, 3), 'ERROR'));
nSkipped = sum(strcmp(statusRows(:, 3), 'SKIPPED'));
fprintf('批量完成：COMPLETED=%d, ERROR=%d, SKIPPED=%d\n%s\n', ...
    nOk, nErr, nSkipped, batchRoot);

end

function s = one_line(s)
s = regexprep(s, '[\r\n]+', ' | ');
end

function path = diagnostic_dir(message)
path = '';
marker = '诊断目录: ';
idx = strfind(message, marker);
if ~isempty(idx)
    path = strtrim(message(idx(end) + numel(marker):end));
end
end

function s = now_iso8601()
d = datetime('now', 'TimeZone', 'local', 'Format', "yyyy-MM-dd'T'HH:mm:ssXXX");
s = char(d);
end
