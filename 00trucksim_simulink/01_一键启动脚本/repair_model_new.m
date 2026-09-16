%% repair_model_new.m - 修复 new_three_axle_vehicle_2dof_3dof_Trucksim 的标准接线
%  作用：把模型恢复为“TruckSim 输入/输出接口”标准状态：
%    * 转向输入：From Workspace（Steering Input，变量 steer_input，单位 deg）
%      -> Mux2 第 1、2 通道（第一轴左右轮）；第二、第三轴由 Constant 0 固定；
%    * 输出：To Workspace 记录 delta_input（deg）与 Vx_trucksim（km/h），
%      原有 x/y/xt/yt/beta/w 的 To Workspace 保持不变；
%    * 删除历史遗留的 From13 / Manual Switch / Demux7 / 180-pi 增益 / delta Goto。
%  用法：在 MATLAB 命令行输入  repair_model_new  然后回车。
%  注意：本脚本会重建 “Steering Input” 等块，若你在模型里手动改过接线，
%        请先确认后再运行。

mdlName = 'new_three_axle_vehicle_2dof_3dof_Trucksim';
scriptDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(scriptDir);
mdlPath = fullfile(projectRoot, '00_simulink', ...
    'new_three_axle_vehicle_2dof_3dof_Trucksim.slx');

if ~bdIsLoaded(mdlName)
    load_system(mdlPath);
end

try
    % ---------- 1) 删除遗留的旧输入链（若存在） ----------
    oldBlks = {
        'From13', 'Manual Switch1', 'Demux7', ...
        'Gain9', 'Gain20', 'Gain21', 'Gain10', 'Gain11', 'Gain22', ...
        'Goto8', 'Goto79', 'Goto80', 'Goto81', 'Goto82', 'Goto83'
    };
    for i = 1:numel(oldBlks)
        b = [mdlName '/' oldBlks{i}];
        if getSimulinkBlockHandle(b) >= 0
            delete_block(b);
        end
    end

    % ---------- 2) 删除并重建标准输入/输出块（避免重复） ----------
    newBlks = {
        'Steering Input', 'To Workspace17', 'To Workspace18', ...
        'Constant1', 'Constant2', 'Constant3', 'Constant4'
    };
    for i = 1:numel(newBlks)
        b = [mdlName '/' newBlks{i}];
        if getSimulinkBlockHandle(b) >= 0
            delete_block(b);
        end
    end

    add_block('simulink/Sources/From Workspace', [mdlName '/Steering Input'], ...
        'Position', [500 985 660 1045]);
    set_param([mdlName '/Steering Input'], ...
        'VariableName', 'steer_input', 'SampleTime', '0');

    add_block('simulink/Sinks/To Workspace', [mdlName '/To Workspace17'], ...
        'Position', [720 990 810 1020]);
    set_param([mdlName '/To Workspace17'], ...
        'VariableName', 'delta_input', 'SaveFormat', 'Timeseries');

    add_block('simulink/Sinks/To Workspace', [mdlName '/To Workspace18'], ...
        'Position', [2825 625 2915 655]);
    set_param([mdlName '/To Workspace18'], ...
        'VariableName', 'Vx_trucksim', 'SaveFormat', 'Timeseries');

    add_block('simulink/Sources/Constant', [mdlName '/Constant1'], ...
        'Position', [1845 1040 1920 1070], 'Value', '0');
    add_block('simulink/Sources/Constant', [mdlName '/Constant2'], ...
        'Position', [1845 1095 1920 1125], 'Value', '0');
    add_block('simulink/Sources/Constant', [mdlName '/Constant3'], ...
        'Position', [1845 1150 1920 1180], 'Value', '0');
    add_block('simulink/Sources/Constant', [mdlName '/Constant4'], ...
        'Position', [1845 1205 1920 1235], 'Value', '0');

    % ---------- 3) 接线 ----------
    % 转向输入：仅第一轴（Mux2 第 1、2 通道），并记录 delta_input
    add_line(mdlName, 'Steering Input/1', 'Mux2/1', 'autorouting', 'on');
    add_line(mdlName, 'Steering Input/1', 'Mux2/2', 'autorouting', 'on');
    add_line(mdlName, 'Steering Input/1', 'To Workspace17/1', 'autorouting', 'on');
    % 第二、第三轴固定为 0 度
    add_line(mdlName, 'Constant1/1', 'Mux2/3', 'autorouting', 'on');
    add_line(mdlName, 'Constant2/1', 'Mux2/4', 'autorouting', 'on');
    add_line(mdlName, 'Constant3/1', 'Mux2/5', 'autorouting', 'on');
    add_line(mdlName, 'Constant4/1', 'Mux2/6', 'autorouting', 'on');
    % 车速（km/h，来自 TruckSim 输出第 4 路）记录到 To Workspace18
    add_line(mdlName, 'Demux6/4', 'To Workspace18/1', 'autorouting', 'on');

    % ---------- 4) 验证关键接线 ----------
    ph = get_param([mdlName '/Steering Input'], 'LineHandles');
    if ph.Outport(1) <= 0
        error('Steering Input 输出未连接，接线失败。');
    end

    % ---------- 5) 保存 ----------
    save_system(mdlName);
    fprintf('修复完成并已保存：模型已恢复为 TruckSim 接口标准接线。\n');
catch ME
    fprintf('修复未完成：%s\n', ME.message);
    fprintf('请把上面这行错误发给我；或关闭模型【不要保存】后告诉我，我直接替换模型文件。\n');
end
