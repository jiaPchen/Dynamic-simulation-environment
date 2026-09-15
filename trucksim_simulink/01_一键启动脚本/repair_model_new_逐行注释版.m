%% repair_model_new.m - 修复 new_three_axle_vehicle_2dof_3dof_Trucksim 的标准接线  % 注释：MATLAB 分节标题，说明下面是一段主要流程。
%  作用：把模型恢复为“TruckSim 输入/输出接口”标准状态：  % 注释：原脚本说明文字，不参与执行。
%    * 转向输入：From Workspace（Steering Input，变量 steer_input，单位 deg）  % 注释：原脚本说明文字，不参与执行。
%      -> Mux2 第 1、2 通道（第一轴左右轮）；第二、第三轴由 Constant 0 固定；  % 注释：原脚本说明文字，不参与执行。
%    * 输出：To Workspace 记录 delta_input（deg）与 Vx_trucksim（km/h），  % 注释：原脚本说明文字，不参与执行。
%      原有 x/y/xt/yt/beta/w 的 To Workspace 保持不变；  % 注释：原脚本说明文字，不参与执行。
%    * 删除历史遗留的 From13 / Manual Switch / Demux7 / 180-pi 增益 / delta Goto。  % 注释：原脚本说明文字，不参与执行。
%  用法：在 MATLAB 命令行输入  repair_model_new  然后回车。  % 注释：原脚本说明文字，不参与执行。
%  注意：本脚本会重建 “Steering Input” 等块，若你在模型里手动改过接线，  % 注释：原脚本说明文字，不参与执行。
%        请先确认后再运行。  % 注释：原脚本说明文字，不参与执行。
% 注释：空行，用来分隔代码段。
mdlName = 'new_three_axle_vehicle_2dof_3dof_Trucksim';  % 注释：给变量赋值或计算参数，供后续流程使用。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
mdlPath = 'D:\动力学仿真环境\00_simulink\new_three_axle_vehicle_2dof_3dof_Trucksim.slx';  % 注释：给变量赋值或计算参数，供后续流程使用。 模型文件路径；换电脑后若模型位置变化，需要改成本机实际 .slx 路径。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
% 注释：空行，用来分隔代码段。
if ~bdIsLoaded(mdlName)  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    load_system(mdlPath);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型文件路径；换电脑后若模型位置变化，需要改成本机实际 .slx 路径。 加载 Simulink 模型文件；路径错误会在这里失败。 调用外部命令，主要用于运行 Python 报告脚本。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
try  % 注释：异常保护开始，下面代码失败时会进入 catch。
    % ---------- 1) 删除遗留的旧输入链（若存在） ----------  % 注释：原脚本说明文字，不参与执行。
    oldBlks = {  % 注释：给变量赋值或计算参数，供后续流程使用。
        'From13', 'Manual Switch1', 'Demux7', ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
        'Gain9', 'Gain20', 'Gain21', 'Gain10', 'Gain11', 'Gain22', ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
        'Goto8', 'Goto79', 'Goto80', 'Goto81', 'Goto82', 'Goto83'  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    };  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    for i = 1:numel(oldBlks)  % 注释：循环开始，逐个处理数组、文件或变量。
        b = [mdlName '/' oldBlks{i}];  % 注释：给变量赋值或计算参数，供后续流程使用。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        if getSimulinkBlockHandle(b) >= 0  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
            delete_block(b);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
        end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
    % ---------- 2) 删除并重建标准输入/输出块（避免重复） ----------  % 注释：原脚本说明文字，不参与执行。
    newBlks = {  % 注释：给变量赋值或计算参数，供后续流程使用。
        'Steering Input', 'To Workspace17', 'To Workspace18', ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
        'Constant1', 'Constant2', 'Constant3', 'Constant4'  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    };  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    for i = 1:numel(newBlks)  % 注释：循环开始，逐个处理数组、文件或变量。
        b = [mdlName '/' newBlks{i}];  % 注释：给变量赋值或计算参数，供后续流程使用。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        if getSimulinkBlockHandle(b) >= 0  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
            delete_block(b);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
        end  % 注释：结束当前函数、条件、循环或 switch 代码块。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
    add_block('simulink/Sources/From Workspace', [mdlName '/Steering Input'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        'Position', [500 985 660 1045]);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    set_param([mdlName '/Steering Input'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。 设置 Simulink 块参数，模型块名或参数名变化时这里要同步修改。
        'VariableName', 'steer_input', 'SampleTime', '0');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
    add_block('simulink/Sinks/To Workspace', [mdlName '/To Workspace17'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        'Position', [720 990 810 1020]);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    set_param([mdlName '/To Workspace17'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。 设置 Simulink 块参数，模型块名或参数名变化时这里要同步修改。
        'VariableName', 'delta_input', 'SaveFormat', 'Timeseries');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
    add_block('simulink/Sinks/To Workspace', [mdlName '/To Workspace18'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        'Position', [2825 625 2915 655]);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    set_param([mdlName '/To Workspace18'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。 设置 Simulink 块参数，模型块名或参数名变化时这里要同步修改。
        'VariableName', 'Vx_trucksim', 'SaveFormat', 'Timeseries');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
    add_block('simulink/Sources/Constant', [mdlName '/Constant1'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        'Position', [1845 1040 1920 1070], 'Value', '0');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    add_block('simulink/Sources/Constant', [mdlName '/Constant2'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        'Position', [1845 1095 1920 1125], 'Value', '0');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    add_block('simulink/Sources/Constant', [mdlName '/Constant3'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        'Position', [1845 1150 1920 1180], 'Value', '0');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
    add_block('simulink/Sources/Constant', [mdlName '/Constant4'], ...  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
        'Position', [1845 1205 1920 1235], 'Value', '0');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。
% 注释：空行，用来分隔代码段。
    % ---------- 3) 接线 ----------  % 注释：原脚本说明文字，不参与执行。
    % 转向输入：仅第一轴（Mux2 第 1、2 通道），并记录 delta_input  % 注释：原脚本说明文字，不参与执行。
    add_line(mdlName, 'Steering Input/1', 'Mux2/1', 'autorouting', 'on');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    add_line(mdlName, 'Steering Input/1', 'Mux2/2', 'autorouting', 'on');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    add_line(mdlName, 'Steering Input/1', 'To Workspace17/1', 'autorouting', 'on');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    % 第二、第三轴固定为 0 度  % 注释：原脚本说明文字，不参与执行。
    add_line(mdlName, 'Constant1/1', 'Mux2/3', 'autorouting', 'on');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    add_line(mdlName, 'Constant2/1', 'Mux2/4', 'autorouting', 'on');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    add_line(mdlName, 'Constant3/1', 'Mux2/5', 'autorouting', 'on');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    add_line(mdlName, 'Constant4/1', 'Mux2/6', 'autorouting', 'on');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    % 车速（km/h，来自 TruckSim 输出第 4 路）记录到 To Workspace18  % 注释：原脚本说明文字，不参与执行。
    add_line(mdlName, 'Demux6/4', 'To Workspace18/1', 'autorouting', 'on');  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
% 注释：空行，用来分隔代码段。
    % ---------- 4) 验证关键接线 ----------  % 注释：原脚本说明文字，不参与执行。
    ph = get_param([mdlName '/Steering Input'], 'LineHandles');  % 注释：给变量赋值或计算参数，供后续流程使用。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。
    if ph.Outport(1) <= 0  % 注释：条件判断开始，根据当前状态决定是否执行内部语句。
        error('Steering Input 输出未连接，接线失败。');  % 注释：抛出错误并中止运行，防止配置错误时继续仿真。
    end  % 注释：结束当前函数、条件、循环或 switch 代码块。
% 注释：空行，用来分隔代码段。
    % ---------- 5) 保存 ----------  % 注释：原脚本说明文字，不参与执行。
    save_system(mdlName);  % 注释：执行 MATLAB 语句，完成当前流程的一小步。 模型名称，必须和 Simulink 模型文件及内部顶层模型名一致。 调用外部命令，主要用于运行 Python 报告脚本。
    fprintf('修复完成并已保存：模型已恢复为 TruckSim 接口标准接线。\n');  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
catch ME  % 注释：异常处理分支，用于提示或跳过失败步骤。
    fprintf('修复未完成：%s\n', ME.message);  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
    fprintf('请把上面这行错误发给我；或关闭模型【不要保存】后告诉我，我直接替换模型文件。\n');  % 注释：向 MATLAB 命令行打印运行状态或结果路径。
end  % 注释：结束当前函数、条件、循环或 switch 代码块。
