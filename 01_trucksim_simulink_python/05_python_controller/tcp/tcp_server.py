# -*- coding: utf-8 -*-
"""Python TCP 联仿服务（阶段二）。

职责：
  1. 读取 TXT 测试用例（可选：配置 TruckSim 工况）；
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
                       [--config-trucksim 0|1|auto] [--vehicle-config <yaml>]
"""
import argparse
import csv
import json
import math
import os
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controller.zero_sideslip_controller import load_controller  # noqa: E402
from parse_case_py import parse_case  # noqa: E402
from trucksim.trucksim_com import configure_trucksim  # noqa: E402

HOST = "127.0.0.1"
PROTOCOL = 1
EXPECTED_INPUTS = ["Vx_kmh", "beta_deg", "w_degps"]
EXPECTED_OUTPUTS = ["d1L", "d1R", "d2L", "d2R", "d3L", "d3R"]
LOG_COLS = [
    "step_id", "sim_time_s", "Vx_kmh", "beta_deg", "w_degps",
    "delta1_deg", "delta2_deg", "delta3_deg", "fb_deg", "beta_int_deg", "status",
]


def load_yaml(path):
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_env_overrides(cfg):
    trucksim = cfg.setdefault("trucksim", {})
    simfile = os.environ.get("P2_TRUCKSIM_SIMFILE")
    if simfile:
        trucksim["simfile_path"] = simfile
        print("CONFIG_SIMFILE %s" % simfile, flush=True)
    speed_controller = trucksim.setdefault("speed_controller", {})
    env_map = {
        "P2_TRUCKSIM_SPEED_KP": "kp",
        "P2_TRUCKSIM_SPEED_KI": "ki",
        "P2_TRUCKSIM_SPEED_KP3": "kp3",
        "P2_TRUCKSIM_SPEED_I_DEADBAND": "integral_deadband_m",
    }
    for env_name, cfg_key in env_map.items():
        value = os.environ.get(env_name)
        if value is not None and value != "":
            speed_controller[cfg_key] = float(value)


def log_row(writer, diag, states, t, step, status):
    writer.writerow([
        step, "%.6f" % t, "%.6f" % states[0], "%.6f" % states[1], "%.6f" % states[2],
        "%.6f" % diag["delta1_deg"], "%.6f" % diag["delta2_deg"], "%.6f" % diag["delta3_deg"],
        "%.6f" % diag["fb_deg"], "%.6f" % diag["beta_int_deg"], status,
    ])


def _require(cond, message):
    if not cond:
        raise RuntimeError(message)


def validate_hello(hello):
    _require(hello.get("type") == "HELLO", "握手失败：期望 HELLO")
    _require(int(hello.get("protocol", -1)) == PROTOCOL,
             "协议版本不一致：Python=%d, Simulink=%s" % (PROTOCOL, hello.get("protocol")))
    _require(list(hello.get("inputs", [])) == EXPECTED_INPUTS,
             "输入信号列表不一致：%s" % hello.get("inputs"))
    _require(list(hello.get("outputs", [])) == EXPECTED_OUTPUTS,
             "输出信号列表不一致：%s" % hello.get("outputs"))


def validate_state(msg, expected_step):
    _require("step_id" in msg, "STATE 缺少 step_id")
    step = int(msg["step_id"])
    if expected_step is not None:
        _require(step == expected_step,
                 "step_id 不连续：期望 %d 实际 %d" % (expected_step, step))
    states = [float(x) for x in msg.get("states", [])]
    _require(len(states) == len(EXPECTED_INPUTS),
             "STATE 维度错误：期望 %d 实际 %d" % (len(EXPECTED_INPUTS), len(states)))
    _require(all(math.isfinite(x) for x in states), "STATE 包含非有限数值")
    t = float(msg["t"])
    _require(math.isfinite(t), "STATE 时间为非有限数值")
    return step, t, states


def main():
    ap = argparse.ArgumentParser(description="Python TCP 联仿服务")
    ap.add_argument("--case", required=True, help="TXT 测试用例路径")
    ap.add_argument("--port", type=int, default=50007)
    ap.add_argument("--log-dir", default=os.path.join(os.environ.get("TEMP", "."), "p2_logs"))
    ap.add_argument("--config-trucksim", default="0",
                    choices=("0", "1", "auto"),
                    help="是否配置 TruckSim 工况：0=不配置，1=失败即中止，auto=失败警告后继续")
    ap.add_argument("--vehicle-config", default=None)
    args = ap.parse_args()

    case = parse_case(args.case)
    print("CASE_OK %s | v0=%.1f km/h | steer=%s | t_end=%.1f s"
          % (case["case_name"], float(case["initial_speed_kmh"]),
             case["steer_input_type"], float(case["stop_time_s"])), flush=True)

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = args.vehicle_config or os.path.join(base, "config", "vehicle_config.yaml")
    cfg = load_yaml(cfg_path)
    apply_env_overrides(cfg)
    dt = float(case.get("control_dt_s", 0.01))
    cfg["dt"] = dt

    if args.config_trucksim in ("1", "auto"):
        ok = configure_trucksim(case, cfg)
        if not ok:
            if args.config_trucksim == "auto":
                print("CONFIG_WARN 无法完成 TruckSim 工况配置；继续使用当前 simfile 工况", flush=True)
            else:
                print("CONFIG_FAIL 无法完成 TruckSim 工况配置", flush=True)
                sys.exit(1)
        else:
            print("CONFIG_READY", flush=True)
    else:
        print("CONFIG_SKIP（未启用 TruckSim 工况配置，以当前 simfile 工况为准）", flush=True)

    ctrlr = load_controller(cfg, case)
    os.makedirs(args.log_dir, exist_ok=True)
    log_path = os.path.join(args.log_dir, "python_signals.csv")
    logf = open(log_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(logf)
    writer.writerow(LOG_COLS)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, args.port))
    srv.listen(1)
    srv.settimeout(120)
    print("LISTENING %s:%d" % (HOST, args.port), flush=True)

    conn = None
    f_in = None
    f_out = None
    try:
        # ---- 握手（容忍无效连接，例如被探活 ping 打断，继续等真正客户端）----
        while True:
            try:
                conn, addr = srv.accept()
                print("CLIENT_CONNECTED %s" % str(addr), flush=True)
                conn.settimeout(10.0)
                f_in = conn.makefile("r", encoding="utf-8")
                f_out = conn.makefile("w", encoding="utf-8")
                hello = json.loads(f_in.readline())
                validate_hello(hello)
                ready = {
                    "type": "READY", "protocol": PROTOCOL,
                    "input_dim": len(EXPECTED_INPUTS), "output_dim": len(EXPECTED_OUTPUTS),
                    "controller": "zero_sideslip",
                    "dt": dt,
                }
                f_out.write(json.dumps(ready, ensure_ascii=False) + "\n")
                f_out.flush()
                print("HANDSHAKE_OK", flush=True)
                break
            except (json.JSONDecodeError, RuntimeError, ValueError, TypeError,
                    socket.timeout, OSError) as e:
                print("REJECT_CONN %s" % e, flush=True)
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                conn = None
                continue

        # ---- 周期通讯 ----
        running = True
        expected_step = None
        while running:
            line = f_in.readline()
            if not line:
                print("CLIENT_CLOSED", flush=True)
                break
            msg = json.loads(line)
            mtype = msg.get("type")
            if mtype == "RESET":
                ctrlr.reset()
                expected_step = None
                print("RESET_OK", flush=True)
                continue
            if mtype == "STOP":
                print("STOP_OK", flush=True)
                running = False
                break
            if mtype != "STATE":
                print("UNKNOWN_MSG %s" % mtype, flush=True)
                continue
            step, t, states = validate_state(msg, expected_step)
            controls, diag = ctrlr.compute(t, states[0], states[1], states[2])
            _require(len(controls) == len(EXPECTED_OUTPUTS),
                     "CONTROL 维度错误：期望 %d 实际 %d" % (len(EXPECTED_OUTPUTS), len(controls)))
            _require(all(math.isfinite(float(x)) for x in controls),
                     "CONTROL 包含非有限数值")
            resp = {
                "type": "CONTROL", "step_id": step, "t": t,
                "controls": controls, "diagnostics": diag,
            }
            f_out.write(json.dumps(resp, ensure_ascii=False) + "\n")
            f_out.flush()
            log_row(writer, diag, states, t, step, "OK")
            logf.flush()   # 每条记录立即落盘，避免 MATLAB 拷贝到半截文件
            expected_step = step + 1
    except socket.timeout:
        print("ACCEPT_TIMEOUT", flush=True)
        sys.exit(2)
    except Exception as e:
        print("SERVER_ERROR %s" % e, flush=True)
        raise
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        srv.close()
        logf.flush()
        logf.close()
    print("SERVER_STOPPED", flush=True)


if __name__ == "__main__":
    main()
