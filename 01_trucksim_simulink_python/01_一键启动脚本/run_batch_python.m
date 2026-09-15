%% run_batch_python.m - 阶段二批量联仿（目录下所有 TXT 依次运行）
%  逐工况运行 run_single_python_case，所有结果收拢到一个批次目录，只生成一份总报告。
clear; clc;
clear run_single_python_case parse_case export_case_csv;

phase2Root = 'D:\动力学仿真环境阶段二\01_trucksim_simulink_python';
caseDir = fullfile(phase2Root, '02_测试用例');
controllerRoot = fullfile(phase2Root, '05_python_controller');
reportRoot = fullfile(phase2Root, '04_测试报告');
pythonExe = 'D:\05_python\python.exe';
batchNo = ['批量仿真_' datestr(now, 'yyyy年mm月dd日_HH时MM分SS秒')];
batchRoot = fullfile(reportRoot, batchNo);
caseDataRoot = fullfile(batchRoot, 'cases');
mkdir(caseDataRoot);

files = dir(fullfile(caseDir, '*.txt'));
if isempty(files)
    error('run_batch_python:NoCases', '目录中没有 TXT 用例: %s', caseDir);
end

runDirs = {};
for i = 1:numel(files)
    fprintf('========== 工况 %d/%d: %s ==========\n', i, numel(files), files(i).name);
    opt = struct();
    opt.dataRoot = batchRoot;
    opt.userName = 'cases';
    opt.reportRoot = batchRoot;
    opt.generateReport = false;  % 批量模式只生成最终一份 Word
    [runNo, ioDir] = run_single_python_case(fullfile(caseDir, files(i).name), opt);
    runDirs{end+1} = ioDir; %#ok<AGROW>
end

fprintf('========== 批量完成，共 %d 个工况 ==========\n', numel(runDirs));
fprintf('批次目录: %s\n', batchRoot);
for i = 1:numel(runDirs)
    fprintf('  %s\n', runDirs{i});
end

%% ---------- 生成批量汇总报告 ----------
marker = fullfile(batchRoot, 'batch_run_dirs.txt');
fid = fopen(marker, 'w', 'n', 'UTF-8');
if fid < 0
    error('run_batch_python:MarkerOpen', '无法创建批量运行目录清单: %s', marker);
end
for i = 1:numel(runDirs)
    fprintf(fid, '%s\n', runDirs{i});
end
fclose(fid);

oldDir = cd(fullfile(controllerRoot, 'report'));
cmd = sprintf('"%s" make_batch_summary.py --batch-marker "%s" --report-root "%s" --output-dir "%s"', ...
    pythonExe, marker, reportRoot, batchRoot);
fprintf('========== 生成批量汇总报告 ==========\n%s\n', cmd);
[st, msg] = system(cmd);
cd(oldDir);
if st ~= 0
    error('run_batch_python:BatchSummaryFailed', ...
        '批量汇总报告生成失败(exit=%d):\n%s', st, msg);
end
if ~contains(msg, 'BATCH_SUMMARY_OK')
    fprintf('%s\n', msg);
end
fprintf('========== 批量报告完成 ==========\n%s\n', batchRoot);
fprintf('Word: %s\n', fullfile(batchRoot, '阶段二批量仿真测试报告.docx'));
fprintf('CSV : %s\n', fullfile(batchRoot, '批量指标汇总.csv'));
