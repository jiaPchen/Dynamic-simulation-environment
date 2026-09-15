function [ioCsv, infoCsv, runNo] = export_case_csv(dataRoot, userName, caseStruct, signals)  % 注释：定义 MATLAB 函数及其输入输出。
% EXPORT_CASE_CSV  Export simulation data per the project CSV conventions.  % 注释：原脚本说明文字，不参与执行。
%  % 注释：原脚本说明文字，不参与执行。
%  dataRoot   : data root folder, e.g. D:\动力学仿真环境\06_数据存储  % 注释：原脚本说明文字，不参与执行。 仿真数据输出根目录；需要保证本机有写入权限。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
%  userName   : person folder name  % 注释：原脚本说明文字，不参与执行。 数据输出子目录名称，用于区分不同测试批次或人员。
%  caseStruct : parsed test case (struct of strings)  % 注释：原脚本说明文字，不参与执行。
%  signals    : n x 2 cell {workspace variable name, CSV column name}  % 注释：原脚本说明文字，不参与执行。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
%  % 注释：原脚本说明文字，不参与执行。
%  Output layout:  dataRoot\userName\运行编号\运行编号_trucksim_io.csv  % 注释：原脚本说明文字，不参与执行。 仿真数据输出根目录；需要保证本机有写入权限。 数据输出子目录名称，用于区分不同测试批次或人员。
%                  dataRoot\userName\运行编号\运行编号_case_info.csv  % 注释：原脚本说明文字，不参与执行。 仿真数据输出根目录；需要保证本机有写入权限。 数据输出子目录名称，用于区分不同测试批次或人员。
%  Return values:  ioCsv/infoCsv 文件路径；runNo 运行编号（供报告脚本使用）。  % 注释：原脚本说明文字，不参与执行。
%  Run number format follows the project convention:  % 注释：原脚本说明文字，不参与执行。
%      2026年08月27日_10时30分00秒_第001次  % 注释：原脚本说明文字，不参与执行。
% 注释：空行，用来分隔代码段。
% ---- Run number ----  % 注释：原脚本说明文字，不参与执行。
st = clock;  % 注释：给变量赋值或计算参数，供后续流程使用。
userDir = fullfile(dataRoot, userName);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。 仿真数据输出根目录；需要保证本机有写入权限。 数据输出子目录名称，用于区分不同测试批次或人员。
if ~exist(userDir, 'dir')  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    mkdir(userDir);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
nRun = numel(dir(fullfile(userDir, '*_第*次'))) + 1;  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
runNo = sprintf('%04d年%02d月%02d日_%02d时%02d分%02d秒_第%03d次', ...  % 注释：给变量赋值或计算参数，供后续流程使用。
    st(1), st(2), st(3), st(4), st(5), fix(st(6)), nRun);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
outDir = fullfile(userDir, runNo);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
mkdir(outDir);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
% ---- Collect signals from the base workspace ----  % 注释：原脚本说明文字，不参与执行。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
nsig = size(signals, 1);  % 注释：给变量赋值或计算参数，供后续流程使用。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
cols = cell(nsig, 1);  % 注释：给变量赋值或计算参数，供后续流程使用。
used = false(nsig, 1);  % 注释：给变量赋值或计算参数，供后续流程使用。
nmin = Inf;  % 注释：给变量赋值或计算参数，供后续流程使用。
for i = 1:nsig  % 注释：循环开始，逐个处理数组、文件或变量。
    varName = signals{i, 1};  % 注释：给变量赋值或计算参数，供后续流程使用。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
    if ~evalin('base', sprintf('exist(''%s'', ''var'')', varName))  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        warning('export_case_csv:SkipVar', ...  % 注释：输出警告但不中断流程，用于提示潜在问题。
            'Workspace variable "%s" not found; column "%s" skipped.', ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
            varName, signals{i, 2});  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
        continue;  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    v = evalin('base', varName);  % 注释：给变量赋值或计算参数，供后续流程使用。
    if isa(v, 'timeseries')  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        v = v.Data(:);  % 注释：给变量赋值或计算参数，供后续流程使用。
    elseif isstruct(v) && isfield(v, 'signals')  % 注释：条件判断的另一个分支。
        v = v.signals.values(:);   % StructureWithTime save format  % 注释：给变量赋值或计算参数，供后续流程使用。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    if ismatrix(v)  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        v = v(:, 1);  % 注释：给变量赋值或计算参数，供后续流程使用。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    cols{i} = double(v(:));  % 注释：给变量赋值或计算参数，供后续流程使用。
    nmin = min(nmin, numel(cols{i}));  % 注释：给变量赋值或计算参数，供后续流程使用。
    used(i) = true;  % 注释：给变量赋值或计算参数，供后续流程使用。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
% ---- Build the table with traceability columns ----  % 注释：原脚本说明文字，不参与执行。
T = table();  % 注释：给变量赋值或计算参数，供后续流程使用。
T.sample_index = (1:nmin)';  % 注释：给变量赋值或计算参数，供后续流程使用。
T.run_number   = repmat({runNo}, nmin, 1);  % 注释：给变量赋值或计算参数，供后续流程使用。
T.timestamp_local_iso8601 = repmat({datestr(now, 'yyyy-mm-ddTHH:MM:SS')}, nmin, 1);  % 注释：给变量赋值或计算参数，供后续流程使用。
for i = 1:nsig  % 注释：循环开始，逐个处理数组、文件或变量。
    if ~used(i)  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        continue;  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    colName = matlab.lang.makeValidName(signals{i, 2});  % 注释：给变量赋值或计算参数，供后续流程使用。 定义要导出的工作区变量与 CSV 列名之间的对应关系。
    T.(colName) = cols{i}(1:nmin);  % 注释：给变量赋值或计算参数，供后续流程使用。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
T.case_id   = repmat({getField(caseStruct, 'source_case_id', '')}, nmin, 1);  % 注释：给变量赋值或计算参数，供后续流程使用。
T.case_name = repmat({getField(caseStruct, 'case_name', '')}, nmin, 1);  % 注释：给变量赋值或计算参数，供后续流程使用。
% 注释：空行，用来分隔代码段。
% ---- Save trucksim_io CSV ----  % 注释：原脚本说明文字，不参与执行。
ioCsv = fullfile(outDir, [runNo '_trucksim_io.csv']);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
writetable(T, ioCsv);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
% ---- Save case_info CSV ----  % 注释：原脚本说明文字，不参与执行。
fn = fieldnames(caseStruct);  % 注释：给变量赋值或计算参数，供后续流程使用。
info = cell(numel(fn) + 3, 2);  % 注释：给变量赋值或计算参数，供后续流程使用。
info(1, :) = {'run_number', runNo};  % 注释：给变量赋值或计算参数，供后续流程使用。
info(2, :) = {'timestamp_local_iso8601', datestr(now, 'yyyy-mm-ddTHH:MM:SS')};  % 注释：给变量赋值或计算参数，供后续流程使用。
info(3, :) = {'model_name', 'three_axle_vehicle_2dof_3dof_Trucksim'};  % 注释：给变量赋值或计算参数，供后续流程使用。
for i = 1:numel(fn)  % 注释：循环开始，逐个处理数组、文件或变量。
    info(i + 3, :) = {fn{i}, caseStruct.(fn{i})};  % 注释：给变量赋值或计算参数，供后续流程使用。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
infoCsv = fullfile(outDir, [runNo '_case_info.csv']);  % 注释：文件或路径处理；换电脑时要重点确认路径存在和有写权限。
writetable(cell2table(info, 'VariableNames', {'key', 'value'}), infoCsv);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
% ----------------------------------------------------------------------  % 注释：原脚本说明文字，不参与执行。
function v = getField(s, f, dflt)  % 注释：定义 MATLAB 函数及其输入输出。
if isfield(s, f)  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
    v = s.(f);  % 注释：给变量赋值或计算参数，供后续流程使用。
else  % 注释：条件判断的兜底分支。
    v = dflt;  % 注释：给变量赋值或计算参数，供后续流程使用。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
% 注释：空行，用来分隔代码段。
