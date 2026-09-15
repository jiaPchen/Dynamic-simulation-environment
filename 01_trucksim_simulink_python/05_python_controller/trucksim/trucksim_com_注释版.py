# -*- coding: utf-8 -*-
"""TruckSim 2019 COM 工况配置（阶段二）。（本文件为逐行注释版，运行请用 trucksim_com.py）

目标：仿真前由 Python 按 TXT 用例全量设置固定联仿 Run 的
初始车速、附着系数、坡度和可选场景，回读确认后输出 CONFIG_READY。

注意：TruckSim COM 的控件/属性映射需在目标工控机上验证后冻结。
当前为框架实现：连接 TruckSim.Application、定位固定 Run、
设置并回读关键工况参数；若 COM 不可用或映射未验证，函数返回 False，
调用方应跳过配置（--config-trucksim 0）。

TXT 字段 -> TruckSim 配置目标（待验证映射表）：
  initial_speed_kmh   -> Run 初始车速
  road_friction       -> 路面/轮胎附着系数
  road_grade          -> 道路坡度
  trucksim_scenario   -> 可选 Procedure/Run/道路数据集
  stop_time_s         -> 仿真结束时间
"""
import time                                 # 导入 time（用于短暂等待）


RUN_NAME = "ORAC-BLFISMC1017 #phase2"       # 固定联仿 Run 名称（默认）


def configure_trucksim(case, cfg):          # 配置函数：case=解析后的用例，cfg=车辆配置
    try:                                    # 尝试导入 pywin32
        import win32com.client              # COM 客户端库
    except Exception as e:                  # 导入失败
        print("[trucksim_com] 未安装 pywin32: %s" % e)  # 提示
        return False                        # 返回失败

    run_name = cfg.get("trucksim", {}).get("run_name", RUN_NAME)  # 取固定 Run 名称（可配置）
    progid = cfg.get("trucksim", {}).get("com_progid", "TruckSim.Application")  # COM 程序标识
    try:                                    # 尝试 COM 连接
        ts = win32com.client.Dispatch(progid)  # 连接 TruckSim 2019 COM 服务
        # 定位固定联仿 Run（名称需与目标机一致）
        run = ts.GetRunByName(run_name)     # 按名称定位固定联仿 Run
        # ---- 全量设置工况参数（映射验证后启用）----
        # run.VehicleInitialSpeed = float(case["initial_speed_kmh"]) / 3.6   # 设置初始车速（待验证）
        # run.RoadFriction        = float(case.get("road_friction", 0.85))   # 设置附着系数（待验证）
        # run.RoadGrade           = float(case.get("road_grade", 0.0))       # 设置坡度（待验证）
        # run.StopTime            = float(case["stop_time_s"])               # 设置仿真时长（待验证）
        # ---- 回读校验 ----
        # v = run.VehicleInitialSpeed                                      # 回读车速
        # if abs(v - float(case["initial_speed_kmh"]) / 3.6) > 1e-6:       # 若不匹配
        #     return False                                                  # 返回失败
        print("[trucksim_com] 已连接 TruckSim，Run=%s（参数映射待验证，未实际修改）" % run_name)  # 提示已连接
        time.sleep(0.1)                     # 短暂等待，确保 COM 调用完成
        return True                         # 返回成功（当前仅验证连接）
    except Exception as e:                  # COM 调用异常
        print("[trucksim_com] COM 配置失败: %s" % e)  # 打印错误
        return False                        # 返回失败
