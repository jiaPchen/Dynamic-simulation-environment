function test_capture_portability()
% 用临时 TruckSim 数据模拟换机：另一阶段旧路径可跳过，有效同 Run 必须拒绝。
testsDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(testsDir);
repoRoot = fileparts(projectRoot);
tempRoot = tempname;
mkdir(tempRoot);
cleanup = onCleanup(@() rmdir(tempRoot, 's')); %#ok<NASGU>

stage1ScriptDir = fullfile(tempRoot, '00trucksim_simulink', '01_一键启动脚本');
stage2ScriptDir = fullfile(tempRoot, '01_trucksim_simulink_python', '01_一键启动脚本');
mkdir(stage1ScriptDir);
mkdir(stage2ScriptDir);
copyfile(fullfile(projectRoot, '01_一键启动脚本', 'capture_phase1_simfile.m'), stage1ScriptDir);
copyfile(fullfile(repoRoot, '01_trucksim_simulink_python', '01_一键启动脚本', ...
    'capture_phase2_simfile.m'), stage2ScriptDir);
addpath(stage1ScriptDir, stage2ScriptDir, '-begin');
pathCleanup = onCleanup(@() rmpath(stage1ScriptDir, stage2ScriptDir)); %#ok<NASGU>

stage2Runtime = fullfile(tempRoot, '01_trucksim_simulink_python', 'runtime');
mkdir(stage2Runtime);
write_text(fullfile(stage2Runtime, 'trucksim_phase2.path'), ...
    ['Z:\old_computer\simfile_phase2.sim' newline]);

dataDir = fullfile(tempRoot, 'TruckSimData');
mkdir(dataDir);
runA = fullfile(dataDir, 'Results', 'RunA', 'Run_all.par');
runB = fullfile(dataDir, 'Results', 'RunB', 'Run_all.par');
mkdir(fileparts(runA));
mkdir(fileparts(runB));
write_text(runA, ['PARSFILE' newline 'END' newline]);
write_text(runB, ['PARSFILE' newline 'END' newline]);
source = fullfile(dataDir, 'simfile.sim');
write_text(source, sprintf('INPUT %s\n', runA));

stage1Saved = capture_phase1_simfile(source);
assert(exist(stage1Saved, 'file') == 2);
try
    capture_phase2_simfile(source);
    error('test_capture_portability:SharedRunAccepted', '不应允许两阶段共用Run。');
catch ME
    assert(strcmp(ME.identifier, 'capture_phase2_simfile:SharedRun'));
end

write_text(source, sprintf('INPUT %s\n', runB));
stage2Saved = capture_phase2_simfile(source);
assert(exist(stage2Saved, 'file') == 2);
clear pathCleanup  % 先撤销测试路径，再删除临时目录
fprintf('双阶段换机入口隔离测试通过。\n');
end

function write_text(path, content)
fid = fopen(path, 'w', 'n', 'UTF-8');
assert(fid >= 0, '无法创建测试文件: %s', path);
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, '%s', content);
end
