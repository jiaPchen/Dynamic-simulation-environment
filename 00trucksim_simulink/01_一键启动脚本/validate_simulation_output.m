function validate_simulation_output(out, expectedStop, caseStruct, inputTime, inputValue)
% VALIDATE_SIMULATION_OUTPUT  Reject incomplete or wrongly configured runs.
% This check runs before CSV/report generation so invalid conditions are never
% archived as successful results.

tolTime = max(0.02, 0.001 * expectedStop);
try
    state = out.Vx_trucksim;
    actualStop = double(state.Time(end));
    v0Actual = double(state.Data(1));
catch ME
    error('run_case_new:MissingVehicleOutput', ...
        '无法读取 TruckSim 车速输出用于验收：%s', ME.message);
end
if abs(actualStop - expectedStop) > tolTime
    error('run_case_new:StopTimeMismatch', ...
        ['TruckSim 实际输出结束于 %.6g s，而 TXT 要求 %.6g s。' ...
         '本次结果不会导出；请检查 simfile/Run_all.par。'], ...
        actualStop, expectedStop);
end

v0Expected = str2double(caseStruct.initial_speed_kmh);
if abs(v0Actual - v0Expected) > 0.5
    error('run_case_new:SpeedMismatch', ...
        ['TruckSim 实际初始车速 %.3f km/h 与 TXT 要求 %.3f km/h 不一致。' ...
         '本次结果不会导出。'], v0Actual, v0Expected);
end

try
    actualInput = out.delta_input;
    actualTime = double(actualInput.Time(:));
    actualValue = double(actualInput.Data(:));
catch ME
    error('run_case_new:MissingSteerOutput', ...
        '无法读取 delta_input 验证实际转向：%s', ME.message);
end
expectedValue = interp1(inputTime, inputValue, actualTime, 'linear', 'extrap');
maxInputError = max(abs(actualValue - expectedValue));
if maxInputError > 1e-3
    error('run_case_new:SteerMismatch', ...
        ['TruckSim 实际第一轴转向与 TXT 生成输入不一致（最大误差 %.6g deg）。' ...
         '本次结果不会导出。'], maxInputError);
end
fprintf(['Output validation passed: t_end=%.3f s, v0=%.3f km/h, ' ...
    'max steer error=%.3g deg.\n'], actualStop, v0Actual, maxInputError);
end
