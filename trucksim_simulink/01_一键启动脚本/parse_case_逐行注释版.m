function c = parse_case(txtFile)  % 注释：定义 MATLAB 函数及其输入输出。
% PARSE_CASE  Parse a TXT test case in "key = value" format.  % 注释：原脚本说明文字，不参与执行。
%  Supports '#' comments and blank lines, validates required fields and  % 注释：原脚本说明文字，不参与执行。
%  numeric ranges, and checks file name vs. case_name consistency.  % 注释：原脚本说明文字，不参与执行。
%  % 注释：原脚本说明文字，不参与执行。
%  Returns a struct whose fields are character strings; convert numeric  % 注释：原脚本说明文字，不参与执行。
%  fields at the call site (str2double).  % 注释：原脚本说明文字，不参与执行。
% 注释：空行，用来分隔代码段。
c = struct();  % 注释：给变量赋值或计算参数，供后续流程使用。
% 注释：空行，用来分隔代码段。
if ~exist(txtFile, 'file')  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    error('parse_case:FileNotFound', 'Test case not found: %s', txtFile);  % 注释：抛出错误并中止运行，防止配置错误时继续仿真。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
fid = fopen(txtFile, 'r', 'n', 'UTF-8');  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
if fid < 0  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    error('parse_case:OpenFailed', 'Cannot open test case: %s', txtFile);  % 注释：抛出错误并中止运行，防止配置错误时继续仿真。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
raw = textscan(fid, '%s', 'Delimiter', '\n');  % 注释：给变量赋值或计算参数，供后续流程使用。
fclose(fid);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
% 注释：空行，用来分隔代码段。
lines = raw{1};  % 注释：给变量赋值或计算参数，供后续流程使用。
for i = 1:numel(lines)  % 注释：循环开始，逐个处理数组、文件或变量。
    line = strtrim(lines{i});  % 注释：给变量赋值或计算参数，供后续流程使用。
    if isempty(line) || startsWith(line, '#')  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        continue;  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    kv = split(line, '=');  % 注释：给变量赋值或计算参数，供后续流程使用。
    if numel(kv) ~= 2  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        warning('parse_case:SkipLine', 'Skipping unparseable line: %s', line);  % 注释：输出警告但不中断流程，用于提示潜在问题。
        continue;  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    key = strtrim(kv{1});  % 注释：给变量赋值或计算参数，供后续流程使用。
    val = strtrim(kv{2});  % 注释：给变量赋值或计算参数，供后续流程使用。
    if ~isvarname(key)  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        warning('parse_case:BadKey', 'Skipping invalid field name: %s', key);  % 注释：输出警告但不中断流程，用于提示潜在问题。
        continue;  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    c.(key) = val;  % 注释：给变量赋值或计算参数，供后续流程使用。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
% ---- Required fields and range checks ----  % 注释：原脚本说明文字，不参与执行。
required = {'case_name', 'stop_time_s', 'initial_speed_kmh', 'steer_input_type'};  % 注释：给变量赋值或计算参数，供后续流程使用。
missing = required(~ismember(required, fieldnames(c)));  % 注释：给变量赋值或计算参数，供后续流程使用。
if ~isempty(missing)  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    error('parse_case:MissingField', 'Missing required field(s): %s', ...  % 注释：抛出错误并中止运行，防止配置错误时继续仿真。
        strjoin(missing, ', '));  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
checkNum(c, 'stop_time_s',        0, Inf);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
checkNum(c, 'initial_speed_kmh',  0, 500);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
if isfield(c, 'steer_amplitude_deg'), checkNum(c, 'steer_amplitude_deg', -90, 90); end  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
if isfield(c, 'steer_frequency_hz'),  checkNum(c, 'steer_frequency_hz',  0, 100); end  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
if isfield(c, 'steer_start_time_s'),  checkNum(c, 'steer_start_time_s',  0, Inf); end  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
if isfield(c, 'road_friction'),       checkNum(c, 'road_friction',       0, 1.5); end  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
% 注释：空行，用来分隔代码段。
% ---- File name vs. case_name consistency ----  % 注释：原脚本说明文字，不参与执行。
[~, baseName] = fileparts(txtFile);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
if ~strcmp(baseName, c.case_name)  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    warning('parse_case:NameMismatch', ...  % 注释：输出警告但不中断流程，用于提示潜在问题。
        'File name (%s) differs from case_name (%s).', baseName, c.case_name);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
% ----------------------------------------------------------------------  % 注释：原脚本说明文字，不参与执行。
function checkNum(c, fld, lo, hi)  % 注释：定义 MATLAB 函数及其输入输出。
v = str2double(c.(fld));  % 注释：给变量赋值或计算参数，供后续流程使用。
if isnan(v) || v < lo || v > hi  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    error('parse_case:BadValue', ...  % 注释：抛出错误并中止运行，防止配置错误时继续仿真。
        'Field "%s" value "%s" out of range [%g, %g].', fld, c.(fld), lo, hi);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
