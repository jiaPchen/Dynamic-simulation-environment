# -*- coding: utf-8 -*-
"""Python TCP 联仿服务（阶段二）。（本文件为逐行注释版，运行请用 tcp_server.py）

职责：
  1. 读取 TXT 测试用例（可选：通过 TruckSim COM 配置工况）；
  2. 启动零质心侧偏角控制器；
  3. 监听 127.0.0.1:<port>，与 Simulink 完成 HELLO/READY 握手；
  4. 按控制周期接收 STATE，计算 CONTROL 返回，并记录 python_signals.csv；
  5. 收到 RESET 清零状态；收到 STOP 或连接断开后退出。

协议（JSON 行，UTF-8，以换行结尾）：
  HELLO   Simulink -> Python  {"type":"HELLO","protocol":1,"dt":0.01,
                               "inputs":[...],"outputs":[...]}
  READY   Python -> Simulink  {"type":"READY","protocol":1,
                               "input_dim":3,"output_dim":6,"controller":"zero_sideslip"}
  STATE   Simulink -> Python  {"type":"STATE","step_id":N,"t":t,
                               "states":[Vx_kmh,beta_deg,w_degps]}
  CONTROL Python -> Simulink  {"type":"CONTROL","step_id":N,"t":t,
                               "controls":[6], "diagnostics":{...}}
  RESET / STOP                控制流消息

用法：
  python tcp_server.py --case <TXT> [--port 50007] [--log-dir <dir>]
                       [--config-trucksim 0|1] [--vehicle-config <yaml>]
"""
import argparse                             # 命令行参数解析
import csv                                  # CSV 写入
import json                                 # JSON 编解码
import os                                   # 路径处理
import socket                               # TCP socket
import sys                                  # 系统相关（退出）
import time                                 # 时间（未直接使用，保留）

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 把 05_python_controller 加入模块搜索路径

from controller.zero_sideslip_controller import load_controller  # noqa: E402  # 导入控制器工厂
from parse_case_py import parse_case  # noqa: E402  # 导入用例解析
from trucksim.trucksim_com import configure_trucksim  # noqa: E402  # 导入 TruckSim COM 配置

HOST = "127.0.0.1"                          # 本机回环地址
PROTOCOL = 1                                # 协议版本号
LOG_COLS = [                                # python_signals.csv 表头
    "step_id", "sim_time_s", "Vx_kmh", "beta_deg", "w_degps",
    "delta1_deg", "delta2_deg", "delta3_deg", "fb_deg", "beta_int_deg", "status",
]


def load_yaml(path):                        # 读取 yaml 配置
    import yaml                             # 导入 yaml
    with open(path, "r", encoding="utf-8") as f:  # 打开配置文件
        return yaml.safe_load(f)            # 解析并返回字典


def log_row(writer, ctrl, diag, states, t, step, status):  # 写一行 CSV 记录
    writer.writerow([                       # 按列顺序写入
        step, "%.6f" % t, "%.6f" % states[0], "%.6f" % states[1], "%.6f" % states[2],  # 步号/时间/三个状态
        "%.6f" % diag["delta1_deg"], "%.6f" % diag["delta2_deg"], "%.6f" % diag["delta3_deg"],  # 三轴转角
        "%.6f" % diag["fb_deg"], "%.6f" % diag["beta_int_deg"], status,  # 反馈量/积分/状态
    ])


def main():                                 # 主函数
    ap = argparse.ArgumentParser(description="Python TCP 联仿服务")  # 参数解析器
    ap.add_argument("--case", required=True, help="TXT 测试用例路径")  # 用例参数（必填）
    ap.add_argument("--port", type=int, default=50007)  # 端口参数
    ap.add_argument("--log-dir", default=os.path.join(os.environ.get("TEMP", "."), "p2_logs"))  # 日志目录
    ap.add_argument("--config-trucksim", type=int, default=0, help="是否通过 COM 配置 TruckSim（0/1）")  # COM 开关
    ap.add_argument("--vehicle-config", default=None)  # 车辆配置路径
    args = ap.parse_args()                  # 解析命令行

    case = parse_case(args.case, check_name=False)  # 解析测试用例（跳过文件名一致性：MATLAB 侧已校验并复制为临时文件）
    print("CASE_OK %s | v0=%.1f km/h | steer=%s | t_end=%.1f s"  # 打印用例概要
          % (case["case_name"], float(case["initial_speed_kmh"]),
             case["steer_input_type"], float(case["stop_time_s"])), flush=True)  # 立即输出

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 05_python_controller 目录
    cfg_path = args.vehicle_config or os.path.join(base, "config", "vehicle_config.yaml")  # 配置路径
    cfg = load_yaml(cfg_path)               # 读取车辆/控制器配置
    dt = float(case.get("control_dt_s", 0.01))  # 控制周期（默认 0.01s）
    cfg["dt"] = dt                          # 把周期放进配置供控制器使用

    if args.config_trucksim:                # 如果启用 TruckSim COM
        ok = configure_trucksim(case, cfg)  # 调用 COM 配置
        if not ok:                          # 如果失败
            print("CONFIG_FAIL 无法完成 TruckSim 工况配置", flush=True)  # 打印失败
            sys.exit(1)                     # 退出码 1
        print("CONFIG_READY", flush=True)   # 打印配置就绪
    else:                                   # 未启用
        print("CONFIG_SKIP（未启用 TruckSim COM，以当前 simfile 工况为准）", flush=True)  # 提示跳过

    ctrlr = load_controller(cfg, case)      # 创建控制器
    os.makedirs(args.log_dir, exist_ok=True)  # 创建日志目录（已存在则忽略）
    log_path = os.path.join(args.log_dir, "python_signals.csv")  # 信号文件路径
    logf = open(log_path, "w", newline="", encoding="utf-8")  # 打开 CSV（UTF-8）
    writer = csv.writer(logf)               # CSV 写入器
    writer.writerow(LOG_COLS)               # 写表头

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建 TCP socket
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 端口复用（防 TIME_WAIT 占用）
    srv.bind((HOST, args.port))             # 绑定地址和端口
    srv.listen(1)                           # 开始监听（允许 1 个排队连接）
    srv.settimeout(120)                     # 等待连接超时 120s
    print("LISTENING %s:%d" % (HOST, args.port), flush=True)  # 打印监听状态

    conn = None                             # 连接对象
    f_in = None                             # 输入流
    f_out = None                            # 输出流
    try:                                    # 主流程 try
        # ---- 握手（容忍无效连接，例如被探活 ping 打断，继续等真正客户端）----
        while True:                         # 循环等待有效客户端
            try:                            # 握手 try
                conn, addr = srv.accept()   # 接受连接
                print("CLIENT_CONNECTED %s" % str(addr), flush=True)  # 打印客户端地址
                conn.settimeout(10.0)       # 单次收发超时 10s
                f_in = conn.makefile("r", encoding="utf-8")  # 输入流
                f_out = conn.makefile("w", encoding="utf-8")  # 输出流
                hello = json.loads(f_in.readline())  # 读 HELLO 并解析
                if hello.get("type") != "HELLO":  # 如果不是 HELLO
                    raise RuntimeError("握手失败：期望 HELLO")  # 抛异常
                ready = {                   # 构造 READY 消息
                    "type": "READY", "protocol": PROTOCOL,
                    "input_dim": 3, "output_dim": 6,
                    "controller": "zero_sideslip",
                    "dt": dt,
                }
                f_out.write(json.dumps(ready, ensure_ascii=False) + "\n")  # 发送 READY
                f_out.flush()               # 立即刷新
                print("HANDSHAKE_OK", flush=True)  # 打印握手成功
                break                       # 退出握手循环
            except (json.JSONDecodeError, RuntimeError, socket.timeout, OSError) as e:  # 无效连接/超时
                print("REJECT_CONN %s" % e, flush=True)  # 打印拒绝原因
                if conn is not None:        # 如果有连接
                    try:                    # 尝试
                        conn.close()        # 关闭连接
                    except Exception:       # 关闭失败也忽略
                        pass                # 忽略
                conn = None                 # 置空
                continue                    # 继续等待下一个客户端

        # ---- 周期通讯 ----
        running = True                      # 运行标志
        while running:                      # 周期循环
            line = f_in.readline()          # 读一行消息
            if not line:                    # 连接关闭（EOF）
                print("CLIENT_CLOSED", flush=True)  # 打印客户端关闭
                break                       # 退出循环
            msg = json.loads(line)          # 解析消息
            mtype = msg.get("type")         # 取消息类型
            if mtype == "RESET":            # RESET 消息
                ctrlr.reset()               # 重置控制器状态
                print("RESET_OK", flush=True)  # 打印
                continue                    # 继续下一轮
            if mtype == "STOP":             # STOP 消息
                print("STOP_OK", flush=True)  # 打印
                running = False             # 停止运行
                break                       # 退出循环
            if mtype != "STATE":            # 其他未知类型
                print("UNKNOWN_MSG %s" % mtype, flush=True)  # 打印未知类型
                continue                    # 继续
            t = float(msg["t"])             # 仿真时间
            states = [float(x) for x in msg["states"]]  # 状态数组
            controls, diag = ctrlr.compute(t, states[0], states[1], states[2])  # 控制器计算
            resp = {                        # 构造 CONTROL 响应
                "type": "CONTROL", "step_id": int(msg["step_id"]), "t": t,
                "controls": controls, "diagnostics": diag,
            }
            f_out.write(json.dumps(resp, ensure_ascii=False) + "\n")  # 发送 CONTROL
            f_out.flush()                   # 刷新
            log_row(writer, controls, diag, states, t, ctrlr.step_id, "OK")  # 记录一行
            logf.flush()   # 每条记录立即落盘，避免 MATLAB 拷贝到半截文件  # 立即落盘
    except socket.timeout:                  # 监听超时
        print("ACCEPT_TIMEOUT", flush=True)  # 打印
        sys.exit(2)                         # 退出码 2
    except Exception as e:                  # 其他异常
        print("SERVER_ERROR %s" % e, flush=True)  # 打印错误
        raise                               # 重新抛出（保留堆栈）
    finally:                                # 收尾
        if conn is not None:                # 若连接存在
            try:                            # 尝试
                conn.close()                # 关闭连接
            except Exception:               # 失败忽略
                pass                        # 忽略
        srv.close()                         # 关闭服务 socket
        logf.flush()                        # 刷新日志
        logf.close()                        # 关闭日志文件
    print("SERVER_STOPPED", flush=True)     # 打印正常退出


if __name__ == "__main__":                  # 直接运行时执行
    main()                                  # 调用主函数
