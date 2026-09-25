function batchRoot = run_batch_cases(continueOnError)
% RUN_BATCH_CASES  阶段一批量运行全部 TXT，用例失败可继续并形成状态/指标汇总。
if nargin < 1, continueOnError = true; end

scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(scriptDir);
caseDir = fullfile(projectRoot, '02_测试用例');
reportRoot = fullfile(projectRoot, '04_测试报告');
batchNo = ['批量仿真_' char(datetime('now', ...
    'Format', 'yyyy年MM月dd日_HH时mm分ss秒_SSS毫秒'))];
batchRoot = fullfile(reportRoot, batchNo);
mkdir(batchRoot);

files = dir(fullfile(caseDir, '*.txt'));
if isempty(files), error('run_batch_cases:NoCases', '目录中没有 TXT 用例: %s', caseDir); end

statusRows = cell(0, 8);
metricRows = cell(0, 14);
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
            'run_batch_cases:StoppedAfterError', '前序用例失败且 continueOnError=false', now_iso8601()}; %#ok<AGROW>
        continue;
    end
    fprintf('========== 阶段一工况 %d/%d: %s ==========\n', i, numel(files), files(i).name);
    opt = struct('dataRoot', batchRoot, 'userName', 'cases', 'generateReport', false);
    try
        [runNo, ioDir] = run_case_new(casePath, opt);
        statusRows(end + 1, :) = {files(i).name, caseName, 'COMPLETED', runNo, ioDir, '', '', now_iso8601()}; %#ok<AGROW>
        metricsPath = fullfile(ioDir, [runNo '_metrics.csv']);
        m = read_metric_map(metricsPath);
        metricRows(end + 1, :) = {runNo, caseName, 'COMPLETED', ...
            metric(m, 'duration'), metric(m, 'sample_count'), metric(m, 'sample_period_median'), ...
            metric(m, 'v_start'), metric(m, 'v_end'), metric(m, 'v_min'), metric(m, 'v_max'), ...
            metric(m, 'max_abs_beta'), metric(m, 'max_abs_yaw_rate'), ...
            metric(m, 'max_abs_lateral_position'), metric(m, 'max_abs_steer')}; %#ok<AGROW>
    catch ME
        statusRows(end + 1, :) = {files(i).name, caseName, 'ERROR', '', '', ...
            ME.identifier, one_line(ME.message), now_iso8601()}; %#ok<AGROW>
        fprintf(2, '工况失败: %s\n', ME.message);
        if ~continueOnError, abortRemaining = true; end
    end
end

statusNames = {'case_file','case_name','status','run_number','run_dir', ...
    'error_identifier','error_message','timestamp_local_iso8601'};
writetable(cell2table(statusRows, 'VariableNames', statusNames), ...
    fullfile(batchRoot, '批量运行状态.csv'));
metricNames = {'run_number','case_name','status','duration_s','sample_count', ...
    'sample_period_s','v_start_kmh','v_end_kmh','v_min_kmh','v_max_kmh', ...
    'max_abs_beta_deg','max_abs_yaw_rate_degps','max_abs_lateral_position_m','max_abs_steer_deg'};
writetable(cell2table(metricRows, 'VariableNames', metricNames), ...
    fullfile(batchRoot, '批量指标汇总.csv'));

nOk = sum(strcmp(statusRows(:, 3), 'COMPLETED'));
nErr = sum(strcmp(statusRows(:, 3), 'ERROR'));
fprintf('阶段一批量结束：COMPLETED=%d, ERROR=%d，目录=%s\n', nOk, nErr, batchRoot);
end

function m = read_metric_map(path)
m = containers.Map('KeyType', 'char', 'ValueType', 'char');
if ~exist(path, 'file'), return; end
T = readtable(path, 'TextType', 'string');
for i = 1:height(T), m(char(T.metric(i))) = char(T.value(i)); end
end

function v = metric(m, key)
if isKey(m, key), v = str2double(m(key)); else, v = NaN; end
end

function s = one_line(s)
s = regexprep(s, '[\r\n]+', ' | ');
end

function s = now_iso8601()
d = datetime('now', 'TimeZone', 'local', 'Format', "yyyy-MM-dd'T'HH:mm:ssXXX");
s = char(d);
end
