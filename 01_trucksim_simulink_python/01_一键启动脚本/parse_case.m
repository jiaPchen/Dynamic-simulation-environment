function c = parse_case(txtFile)
% PARSE_CASE  Parse a TXT test case in "key = value" format.
%  Supports '#' comments and blank lines, validates required fields and
%  numeric ranges, and checks file name vs. case_name consistency.
%
%  Returns a struct whose fields are character strings; convert numeric
%  fields at the call site (str2double).

c = struct();

if ~exist(txtFile, 'file')
    error('parse_case:FileNotFound', 'Test case not found: %s', txtFile);
end

fid = fopen(txtFile, 'r', 'n', 'UTF-8');
if fid < 0
    error('parse_case:OpenFailed', 'Cannot open test case: %s', txtFile);
end
raw = textscan(fid, '%s', 'Delimiter', '\n');
fclose(fid);

lines = raw{1};
for i = 1:numel(lines)
    line = strtrim(lines{i});
    if isempty(line) || startsWith(line, '#')
        continue;
    end
    kv = split(line, '=');
    if numel(kv) ~= 2
        warning('parse_case:SkipLine', 'Skipping unparseable line: %s', line);
        continue;
    end
    key = strtrim(kv{1});
    val = strtrim(kv{2});
    if ~isvarname(key)
        warning('parse_case:BadKey', 'Skipping invalid field name: %s', key);
        continue;
    end
    c.(key) = val;
end

% ---- Required fields and range checks ----
required = {'schema_version', 'case_name', 'stop_time_s', 'initial_speed_kmh', 'steer_input_type'};
missing = required(~ismember(required, fieldnames(c)));
if ~isempty(missing)
    error('parse_case:MissingField', 'Missing required field(s): %s', ...
        strjoin(missing, ', '));
end

checkNum(c, 'stop_time_s',        0, Inf);
checkNum(c, 'initial_speed_kmh',  0, 500);
checkNum(c, 'schema_version',     1, 99);
if isfield(c, 'steer_amplitude_deg'), checkNum(c, 'steer_amplitude_deg', -90, 90); end
if isfield(c, 'steer_frequency_hz'),  checkNum(c, 'steer_frequency_hz',  0, 100); end
if isfield(c, 'steer_start_time_s'),  checkNum(c, 'steer_start_time_s',  0, Inf); end
if isfield(c, 'road_friction'),       checkNum(c, 'road_friction',       0, 1.5); end
if isfield(c, 'road_grade'),          checkNum(c, 'road_grade',        -90, 90); end
if isfield(c, 'control_dt_s'),        checkNum(c, 'control_dt_s',    1e-4, 1); end
if isfield(c, 'kp_beta'),             checkNum(c, 'kp_beta',          -10, 10); end
if isfield(c, 'ki_beta'),             checkNum(c, 'ki_beta',          -10, 10); end
if isfield(c, 'max_steer_deg'),       checkNum(c, 'max_steer_deg',      0, 90); end

allowedSteer = {'step', 'sine'};
if ~ismember(lower(c.steer_input_type), allowedSteer)
    error('parse_case:BadSteerType', ...
        'steer_input_type="%s" 不支持，阶段二仅支持 step 或 sine。', c.steer_input_type);
end
c.steer_input_type = lower(c.steer_input_type);

% ---- File name vs. case_name consistency ----
[~, baseName] = fileparts(txtFile);
if ~strcmp(baseName, c.case_name)
    warning('parse_case:NameMismatch', ...
        'File name (%s) differs from case_name (%s).', baseName, c.case_name);
end

end

% ----------------------------------------------------------------------
function checkNum(c, fld, lo, hi)
v = str2double(c.(fld));
if isnan(v) || v < lo || v > hi
    error('parse_case:BadValue', ...
        'Field "%s" value "%s" out of range [%g, %g].', fld, c.(fld), lo, hi);
end
end
