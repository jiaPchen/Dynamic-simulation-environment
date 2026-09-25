function [ioCsv, infoCsv, runNo, metricsCsv] = export_case_csv(dataRoot, userName, caseStruct, signals)
% EXPORT_CASE_CSV  Export aligned phase-2 data, metrics and traceability metadata.

st = clock;
localNow = datetime('now', 'TimeZone', 'local', ...
    'Format', "yyyy-MM-dd'T'HH:mm:ssXXX");
utcNow = localNow;
utcNow.TimeZone = 'UTC';
utcNow.Format = "yyyy-MM-dd'T'HH:mm:ss'Z'";
localStamp = char(localNow);
utcStamp = char(utcNow);

userDir = fullfile(dataRoot, userName);
if ~exist(userDir, 'dir'), mkdir(userDir); end
nRun = next_run_number(userDir);
runNo = sprintf('%04d年%02d月%02d日_%02d时%02d分%02d秒_第%03d次', ...
    st(1), st(2), st(3), st(4), st(5), fix(st(6)), nRun);
outDir = fullfile(userDir, runNo);

nsig = size(signals, 1);
cols = cell(nsig, 1);
used = false(nsig, 1);
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
        v = v.Data;
    elseif isstruct(v) && isfield(v, 'signals')
        v = v.signals.values;
    end
    if isempty(v)
        warning('export_case_csv:EmptyVar', 'Workspace variable "%s" is empty.', varName);
        continue;
    end
    if ismatrix(v), v = v(:, 1); end
    cols{i} = double(v(:));
    used(i) = true;
end

timeIdx = find(strcmp(signals(:, 2), 'sim_time_s') & used, 1);
if isempty(timeIdx)
    error('export_case_csv:NoTimeColumn', '缺少 sim_time_s 时间列，拒绝导出 CSV。');
end
nref = numel(cols{timeIdx});
if nref < 1, error('export_case_csv:NoSignals', '没有可导出的有效数据。'); end
for i = find(used(:))'
    if numel(cols{i}) ~= nref
        error('export_case_csv:LengthMismatch', ...
            '信号 "%s" 行数(%d)与 sim_time_s 行数(%d)不一致。', ...
            signals{i, 2}, numel(cols{i}), nref);
    end
end

T = table();
T.sample_index = (1:nref)';
T.run_number = repmat({runNo}, nref, 1);
T.run_timestamp_local_iso8601 = repmat({localStamp}, nref, 1);
T.run_timestamp_utc_iso8601 = repmat({utcStamp}, nref, 1);
for i = 1:nsig
    if used(i)
        colName = matlab.lang.makeValidName(signals{i, 2});
        T.(colName) = cols{i};
    end
end
T.case_id = repmat({getField(caseStruct, 'source_case_id', '')}, nref, 1);
T.case_name = repmat({getField(caseStruct, 'case_name', '')}, nref, 1);
T.run_status = repmat({getField(caseStruct, 'run_status', 'COMPLETED')}, nref, 1);

mkdir(outDir);
ioCsv = fullfile(outDir, [runNo '_trucksim_io.csv']);
writetable(T, ioCsv);
metricsCsv = fullfile(outDir, [runNo '_metrics.csv']);
write_metrics_csv(T, metricsCsv);

caseStruct = add_traceability(caseStruct);
fn = fieldnames(caseStruct);
reservedKeys = {'run_number', 'run_timestamp_local_iso8601', ...
    'run_timestamp_utc_iso8601', 'run_status', 'acceptance_status', ...
    'model_name'};
fn = fn(~ismember(fn, reservedKeys));
info = cell(numel(fn) + 6, 2);
info(1, :) = {'run_number', runNo};
info(2, :) = {'run_timestamp_local_iso8601', localStamp};
info(3, :) = {'run_timestamp_utc_iso8601', utcStamp};
info(4, :) = {'run_status', getField(caseStruct, 'run_status', 'COMPLETED')};
info(5, :) = {'acceptance_status', 'NOT_EVALUATED'};
info(6, :) = {'model_name', 'three_axle_vehicle_2dof_3dof_Trucksim_python'};
for i = 1:numel(fn)
    info(i + 6, :) = {fn{i}, value_to_text(caseStruct.(fn{i}))};
end
infoCsv = fullfile(outDir, [runNo '_case_info.csv']);
writetable(cell2table(info, 'VariableNames', {'key', 'value'}), infoCsv);
end

function s = add_traceability(s)
scriptDir = fileparts(mfilename('fullpath'));
phaseRoot = fileparts(scriptDir);
repoRoot = fileparts(phaseRoot);
s.matlab_release = version('-release');
s.matlab_version = version;
sl = ver('simulink');
if isempty(sl), s.simulink_version = 'NOT_AVAILABLE'; else, s.simulink_version = sl(1).Version; end
s.python_version = python_version(getField(s, 'python_executable', ''));
s.platform = computer;
s.git_commit = git_value(repoRoot, 'rev-parse --verify HEAD', 'UNKNOWN');
[dirtyStatus, ~] = system(sprintf('git -C "%s" diff --quiet HEAD --', repoRoot));
s.git_tracked_worktree_dirty = ternary(dirtyStatus == 0, 'false', 'true');
s.case_file_sha256 = hash_if_present(getField(s, 'case_file_path', ''));
s.model_file_sha256 = hash_if_present(getField(s, 'model_file_path', ''));
s.simfile_sha256 = hash_if_present(getField(s, 'simfile_path', ''));
s.controller_entry_sha256 = hash_if_present(getField(s, 'controller_entry_path', ''));
s.controller_source_sha256 = hash_if_present(getField(s, 'controller_source_path', ''));
[s.trucksim_run_id, s.trucksim_external_step_s] = ...
    simfile_metadata(getField(s, 'simfile_path', ''));
end

function out = python_version(exe)
out = 'NOT_AVAILABLE';
if isempty(exe) || ~exist(exe, 'file'), return; end
[st, msg] = system(sprintf('"%s" --version', exe));
if st == 0, out = strtrim(msg); end
end

function out = git_value(repoRoot, args, dflt)
[st, msg] = system(sprintf('git -C "%s" %s', repoRoot, args));
if st == 0, out = strtrim(msg); else, out = dflt; end
end

function h = hash_if_present(path)
h = 'NOT_AVAILABLE';
if isempty(path) || ~exist(path, 'file'), return; end
fid = fopen(path, 'r');
if fid < 0, return; end
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
bytes = fread(fid, Inf, '*uint8');
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(bytes);
digest = typecast(md.digest(), 'uint8');
h = lower(reshape(dec2hex(digest, 2).', 1, []));
end

function [runId, step] = simfile_metadata(path)
runId = 'NOT_AVAILABLE';
step = 'NOT_AVAILABLE';
if isempty(path) || ~exist(path, 'file'), return; end
txt = fileread(path);
tok = regexp(txt, 'SET_MACRO\s+\$\(ROOT_FILE_NAME\)\$\s+(\S+)', 'tokens', 'once');
if ~isempty(tok), runId = tok{1}; end
tok = regexp(txt, 'EXT_MODEL_STEP\s+([0-9.eE+-]+)', 'tokens', 'once');
if ~isempty(tok), step = tok{1}; end
end

function write_metrics_csv(T, path)
pairs = {
    'duration', T.sim_time_s(end) - T.sim_time_s(1), 's';
    'sample_count', height(T), 'count';
    'sample_period_median', median(diff(T.sim_time_s)), 's';
    'v_start', column_stat(T, 'state_vehicle_speed_kmh', 'first'), 'km/h';
    'v_end', column_stat(T, 'state_vehicle_speed_kmh', 'last'), 'km/h';
    'v_max', column_stat(T, 'state_vehicle_speed_kmh', 'max'), 'km/h';
    'max_abs_beta', column_stat(T, 'state_beta_trucksim_deg', 'maxabs'), 'deg';
    'max_abs_yaw_rate', column_stat(T, 'state_yaw_rate_trucksim_degps', 'maxabs'), 'deg/s';
    'max_abs_delta1', column_stat(T, 'cmd_delta1_deg', 'maxabs'), 'deg';
    'max_abs_delta2', column_stat(T, 'cmd_delta2_deg', 'maxabs'), 'deg';
    'max_abs_delta3', column_stat(T, 'cmd_delta3_deg', 'maxabs'), 'deg';
    'acceptance_status', 'NOT_EVALUATED', '';
    };
writetable(cell2table(pairs, 'VariableNames', {'metric','value','unit'}), path);
end

function v = column_stat(T, name, op)
v = NaN;
if ~ismember(name, T.Properties.VariableNames), return; end
x = double(T.(name));
x = x(isfinite(x));
if isempty(x), return; end
switch op
    case 'first', v = x(1);
    case 'last', v = x(end);
    case 'max', v = max(x);
    case 'maxabs', v = max(abs(x));
end
end

function v = getField(s, f, dflt)
if isfield(s, f), v = s.(f); else, v = dflt; end
end

function out = value_to_text(v)
if ischar(v), out = v;
elseif isstring(v), out = char(v);
elseif isnumeric(v) || islogical(v), out = mat2str(v);
else, out = char(string(v));
end
end

function out = ternary(cond, a, b)
if cond, out = a; else, out = b; end
end

function n = next_run_number(userDir)
n = 1;
maxRun = 0;
runs = dir(fullfile(userDir, '*_第*次'));
for i = 1:numel(runs)
    if ~runs(i).isdir, continue; end
    token = regexp(runs(i).name, '_第(\d+)次$', 'tokens', 'once');
    if ~isempty(token), maxRun = max(maxRun, str2double(token{1})); end
end
n = maxRun + 1;
end
