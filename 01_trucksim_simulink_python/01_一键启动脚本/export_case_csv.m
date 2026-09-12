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
series = cell(nsig, 1);
used = false(nsig, 1);
masterTime = [];
for i = 1:nsig
    varName = signals{i, 1};
    if ~evalin('base', sprintf('exist(''%s'', ''var'')', varName))
        warning('export_case_csv:SkipVar', ...
            'Workspace variable "%s" not found; column "%s" skipped.', ...
            varName, signals{i, 2});
        continue;
    end
    v = evalin('base', varName);
    [ti, yi] = normalizeSeries(v);
    if isa(v, 'timeseries')
        % handled by normalizeSeries
    elseif strcmp(varName, 't')
        ti = yi;
    end
    if isempty(yi)
        warning('export_case_csv:EmptyVar', ...
            'Workspace variable "%s" 为空，列 "%s" 跳过。', varName, signals{i, 2});
        continue;
    end
    if strcmp(varName, 't')
        masterTime = double(yi(:));
        ti = masterTime;
    end
    if isempty(ti)
        ti = (0:numel(yi)-1)';
    end
    series{i} = struct('t', double(ti(:)), 'y', double(yi(:)));
    used(i) = true;
end
if isempty(masterTime)
    lens = cellfun(@(s) numel(s.y), series(used));
    usedSeries = series(used);
    [~, imax] = max(lens);
    masterTime = usedSeries{imax}.t;
end
masterTime = unique(masterTime(:), 'stable');

% ---- Build the table with traceability columns ----
T = table();
T.sample_index = (1:numel(masterTime))';
T.run_number   = repmat({runNo}, numel(masterTime), 1);
T.timestamp_local_iso8601 = repmat({datestr(now, 'yyyy-mm-ddTHH:MM:SS')}, numel(masterTime), 1);
for i = 1:nsig
    if ~used(i)
        continue;
    end
    colName = matlab.lang.makeValidName(signals{i, 2});
    if strcmp(signals{i, 1}, 't')
        T.(colName) = masterTime;
    else
        T.(colName) = resampleSeries(series{i}, masterTime);
    end
end
T.case_id   = repmat({getField(caseStruct, 'source_case_id', '')}, numel(masterTime), 1);
T.case_name = repmat({getField(caseStruct, 'case_name', '')}, numel(masterTime), 1);

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

% ----------------------------------------------------------------------
function [t, y] = normalizeSeries(v)
t = [];
if isa(v, 'timeseries')
    t = v.Time(:);
    data = v.Data;
elseif isstruct(v) && isfield(v, 'signals')
    data = v.signals.values;
    if isfield(v, 'time')
        t = v.time(:);
    end
else
    data = v;
end
data = squeeze(data);
if isempty(data)
    y = [];
    return;
end
if isvector(data)
    y = data(:);
elseif ~isempty(t) && size(data, 1) == numel(t)
    y = data(:, 1);
else
    y = data(:);
end
end

% ----------------------------------------------------------------------
function yq = resampleSeries(s, tq)
t = s.t(:);
y = s.y(:);
if numel(t) ~= numel(y)
    t = linspace(tq(1), tq(end), numel(y))';
end
[t, ia] = unique(t, 'stable');
y = y(ia);
if numel(y) == numel(tq) && max(abs(t - tq)) < 1e-12
    yq = y;
elseif numel(y) == 1
    yq = repmat(y, numel(tq), 1);
else
    yq = interp1(t, y, tq, 'linear', 'extrap');
end
end
