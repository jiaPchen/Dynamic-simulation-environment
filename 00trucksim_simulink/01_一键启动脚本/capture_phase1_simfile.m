function targetSimfile = capture_phase1_simfile(sourceSimfile)
% CAPTURE_PHASE1_SIMFILE 保存阶段一Run的专用Solver入口。
% 先在TruckSim中选中阶段一Run并“发送到Simulink”，再运行本函数。
% 仅复制simfile入口，不会修改TruckSim的Run或任何.par文件。

scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(scriptDir);
runtimeDir = fullfile(projectRoot, 'runtime');
pointerFile = fullfile(runtimeDir, 'trucksim_phase1.path');
if nargin < 1 || isempty(sourceSimfile)
    sourceSimfile = 'C:\Trucksim2019\TruckSim2019.0_Data\simfile.sim';
end

assert(exist(sourceSimfile, 'file') == 2, ...
    'capture_phase1_simfile:MissingSource', '发送到Simulink后生成的simfile不存在: %s', sourceSimfile);
sourceInput = resolve_input(sourceSimfile);
assert(exist(sourceInput, 'file') == 2, ...
    'capture_phase1_simfile:InvalidInput', '源simfile的INPUT无法定位参数文件: %s', sourceInput);

% 若同级阶段二已经保存入口，禁止两个阶段指向同一Run。
otherPointer = fullfile(fileparts(projectRoot), '01_trucksim_simulink_python', ...
    'runtime', 'trucksim_phase2.path');
if exist(otherPointer, 'file') == 2
    otherSimfile = strtrim(fileread(otherPointer));
    if exist(otherSimfile, 'file') == 2
        otherInput = resolve_input(otherSimfile);
        assert(~strcmpi(sourceInput, otherInput), ...
            'capture_phase1_simfile:SharedRun', ...
            '阶段一和阶段二不能指向同一Run_all.par。请在TruckSim选择阶段一专用Run后重新发送到Simulink。');
    else
        warning('capture_phase1_simfile:OtherStageNotConfigured', ...
            '阶段二入口仍是旧电脑路径或尚未配置：%s；本次仅跳过阶段二共享Run检查。', otherSimfile);
    end
end

if exist(runtimeDir, 'dir') ~= 7, mkdir(runtimeDir); end
% TruckSim S-Function只接受数据目录中的simfile，因此副本与源文件同目录保存。
targetSimfile = fullfile(fileparts(sourceSimfile), 'simfile_phase1.sim');
if exist(targetSimfile, 'file') == 2
    backup = [targetSimfile '.previous_' datestr(now, 'yyyymmdd_HHMMSS')];
    copyfile(targetSimfile, backup, 'f');
    fprintf('保留旧阶段一simfile: %s\n', backup);
end
copyfile(sourceSimfile, targetSimfile, 'f');

metaFile = fullfile(runtimeDir, 'trucksim_phase1.origin.txt');
fid = fopen(metaFile, 'w', 'n', 'UTF-8');
assert(fid >= 0, 'capture_phase1_simfile:MetaWrite', '无法写入: %s', metaFile);
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, 'source_simfile=%s\n', sourceSimfile);
fprintf(fid, 'input_par=%s\n', sourceInput);
fprintf(fid, 'captured_at=%s\n', datestr(now, 'yyyy-mm-dd HH:MM:SS'));
clear cleanup  % onCleanup 关闭文件，避免重复 fclose 的 MATLAB 警告
fid = fopen(pointerFile, 'w', 'n', 'UTF-8');
assert(fid >= 0, 'capture_phase1_simfile:PointerWrite', '无法写入: %s', pointerFile);
cleanupPointer = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, '%s\n', targetSimfile);
clear cleanupPointer
fprintf('阶段一专用simfile已保存: %s\n', targetSimfile);
fprintf('项目入口记录已保存: %s\n', pointerFile);
fprintf('其INPUT指向: %s\n', sourceInput);
end

function inputPath = resolve_input(simfile)
text = fileread(simfile);
macros = regexp(text, '(?m)^\s*SET_MACRO\s+(\S+)\s+(.+?)\s*$', 'tokens');
token = regexp(text, '(?m)^\s*INPUT\s+(.+?)\s*$', 'tokens', 'once');
assert(~isempty(token), 'capture_phase1_simfile:NoInput', 'simfile中没有INPUT行: %s', simfile);
expr = token{1};
for k = 1:numel(macros)
    expr = strrep(expr, macros{k}{1}, macros{k}{2});
end
expr = strrep(strtrim(expr), '/', filesep);
if ~is_absolute_path(expr)
    expr = fullfile(fileparts(simfile), expr);
end
inputPath = char(java.io.File(expr).getCanonicalPath());
end

function tf = is_absolute_path(pathValue)
tf = numel(pathValue) >= 3 && isletter(pathValue(1)) && pathValue(2) == ':' && ...
    (pathValue(3) == char(92) || pathValue(3) == '/');
end
