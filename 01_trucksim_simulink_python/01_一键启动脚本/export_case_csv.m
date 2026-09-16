function [ioCsv, infoCsv, runNo] = export_case_csv(dataRoot, userName, caseStruct, signals)
% EXPORT_CASE_CSV  Export simulation data per the project CSV conventions.
%
%  dataRoot   : data root folder, e.g. D:\动力学仿真环境\06_数据存储
%  userName   : person folder name
%  caseStruct : parsed test case (struct of strings)
%  signals    : n x 2 cell {workspace variable name, CSV column name}
%
%  Output layout:  dataRoot\userName\运行编号\运行编号_trucksim_io.csv
%                  dataRoot\userName\运行编号\运行编号_case_info.csv
%  Return values:  ioCsv/infoCsv 文件路径；runNo 运行编号（供报告脚本使用）。
%  Run number format follows the project convention:
%      2026年08月27日_10时30分00秒_第001次

% ---- Run number ----
st = clock;
userDir = fullfile(dataRoot, userName);
if ~exist(userDir, 'dir')
    mkdir(userDir);
end
nRun = numel(dir(fullfile(userDir, '*_第*次'))) + 1;
runNo = sprintf('%04d年%02d月%02d日_%02d时%02d分%02d秒_第%03d次', ...
    st(1), st(2), st(3), st(4), st(5), fix(st(6)), nRun);

outDir = fullfile(userDir, runNo);
mkdir(outDir);

% ---- Collect signals from the base workspace ----
nsig = size(signals, 1);
cols = cell(nsig, 1);
used = false(nsig, 1);
nmin = Inf;
for i = 1:nsig
    varName = signals{i, 1};
    if ~evalin('base', sprintf('exist(''%s'', ''var'')', varName))
        warning('export_case_csv:SkipVar', ...
            'Workspace variable "%s" not found; column "%s" skipped.', ...
            varName, signals{i, 2});
        continue;
    end
    v = evalin('base', varName);
    if isa(v, 'timeseries')
        v = v.Data(:);
    elseif isstruct(v) && isfield(v, 'signals')
        v = v.signals.values(:);   % StructureWithTime save format
    end
    if isempty(v)
        warning('export_case_csv:EmptyVar', ...
            'Workspace variable "%s" 为空，列 "%s" 跳过。', varName, signals{i, 2});
        continue;
    end
    if ismatrix(v)
        v = v(:, 1);
    end
    cols{i} = double(v(:));
    nmin = min(nmin, numel(cols{i}));
    used(i) = true;
end

% 时间列是所有导出信号的物理时间基准。过去这里用最短列静默截断，
% 会把 20 s 仿真错误写成 2 s。阶段二要求所有实际导出列逐行对齐；
% 不一致时应由上游修复时间轴，而不是生成看似完整的 CSV。
timeIdx = find(strcmp(signals(:, 2), 'sim_time_s') & used, 1);
if isempty(timeIdx)
    error('export_case_csv:NoTimeColumn', '缺少 sim_time_s 时间列，拒绝导出 CSV。');
end
nref = numel(cols{timeIdx});
for i = find(used(:))'
    if numel(cols{i}) ~= nref
        error('export_case_csv:LengthMismatch', ...
            ['信号 "%s" 的行数(%d)与 sim_time_s 的行数(%d)不一致；' ...
             '拒绝导出 CSV。'], signals{i, 2}, numel(cols{i}), nref);
    end
end
nmin = nref;

% ---- Build the table with traceability columns ----
T = table();
T.sample_index = (1:nmin)';
T.run_number   = repmat({runNo}, nmin, 1);
T.timestamp_local_iso8601 = repmat({datestr(now, 'yyyy-mm-ddTHH:MM:SS')}, nmin, 1);
for i = 1:nsig
    if ~used(i)
        continue;
    end
    colName = matlab.lang.makeValidName(signals{i, 2});
    T.(colName) = cols{i}(1:nmin);
end
T.case_id   = repmat({getField(caseStruct, 'source_case_id', '')}, nmin, 1);
T.case_name = repmat({getField(caseStruct, 'case_name', '')}, nmin, 1);

% ---- Save trucksim_io CSV ----
ioCsv = fullfile(outDir, [runNo '_trucksim_io.csv']);
writetable(T, ioCsv);

% ---- Save case_info CSV ----
fn = fieldnames(caseStruct);
info = cell(numel(fn) + 3, 2);
info(1, :) = {'run_number', runNo};
info(2, :) = {'timestamp_local_iso8601', datestr(now, 'yyyy-mm-ddTHH:MM:SS')};
info(3, :) = {'model_name', 'three_axle_vehicle_2dof_3dof_Trucksim_python'};
for i = 1:numel(fn)
    info(i + 3, :) = {fn{i}, caseStruct.(fn{i})};
end
infoCsv = fullfile(outDir, [runNo '_case_info.csv']);
writetable(cell2table(info, 'VariableNames', {'key', 'value'}), infoCsv);

end

% ----------------------------------------------------------------------
function v = getField(s, f, dflt)
if isfield(s, f)
    v = s.(f);
else
    v = dflt;
end
end
