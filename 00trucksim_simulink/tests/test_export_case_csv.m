function test_export_case_csv()
% 离线验证：0.001 s 原始信号导出后为统一的 0.01 s 时间轴。
testDir = tempname;
mkdir(testDir);
cleanup = onCleanup(@() rmdir(testDir, 's')); %#ok<NASGU>
scriptDir = fullfile(fileparts(fileparts(mfilename('fullpath'))), '01_一键启动脚本');
addpath(scriptDir);

t_test = (0:0.001:0.02)';
v_test = 20 + t_test;
steer_test = double(t_test >= 0.01) * 3;
assignin('base', 't_test', t_test);
assignin('base', 'v_test', v_test);
assignin('base', 'steer_test', steer_test);
signals = {
    't_test', 'sim_time_s';
    'v_test', 'state_vehicle_speed_kmh';
    'steer_test', 'state_steer_delta_deg';
};
caseStruct = struct('case_name', 'offline_export_test', ...
    'source_case_id', 'TEST-EXPORT', 'stop_time_s', '0.02');
[ioCsv, infoCsv, ~, metricsCsv] = export_case_csv(testDir, 'test', caseStruct, signals);
io = readtable(ioCsv);
assert(height(io) == 3);
assert(max(abs(io.sim_time_s - [0; 0.01; 0.02])) < 1e-10);
assert(isequal(io.sample_index, [1; 2; 3]));
assert(max(abs(io.state_vehicle_speed_kmh - [20; 20.01; 20.02])) < 1e-10);
assert(isequal(io.state_steer_delta_deg, [0; 3; 3]));
info = readtable(infoCsv, 'TextType', 'string');
assert(strcmp(info.value(info.key == "raw_sample_count"), "21"));
assert(strcmp(info.value(info.key == "export_sample_count"), "3"));
assert(contains(fileread(metricsCsv), 'sample_count'));
fprintf('阶段一 0.01 s CSV 导出测试通过。\n');
end
