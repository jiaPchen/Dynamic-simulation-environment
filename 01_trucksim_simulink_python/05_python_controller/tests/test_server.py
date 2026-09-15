# -*- coding: utf-8 -*-
"""本地闭环测试：模拟 Simulink TCP 客户端，验证握手、控制律与 CSV 记录。
运行：python tests/test_server.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASE = os.path.join(ROOT, "..", "02_测试用例", "step_steer_python.txt")


def recv_line(f):
    line = f.readline()
    assert line, "连接已断开"
    return json.loads(line)


def main():
    log_dir = tempfile.mkdtemp(prefix="p2_test_")
    port = 51234
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "tcp", "tcp_server.py"),
         "--case", CASE, "--port", str(port), "--log-dir", log_dir],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        env=env,
    )
    try:
        # 等待 LISTENING
        deadline = time.time() + 30
        while time.time() < deadline:
            line = proc.stdout.readline()
            print("SRV:", line.strip())
            if "LISTENING" in line:
                break
            if proc.poll() is not None:
                raise RuntimeError("服务提前退出")
        else:
            raise RuntimeError("等待 LISTENING 超时")

        s = socket.create_connection(("127.0.0.1", port), timeout=10)
        f_in = s.makefile("r", encoding="utf-8")
        f_out = s.makefile("w", encoding="utf-8")
        hello = {
            "type": "HELLO", "protocol": 1, "dt": 0.01,
            "inputs": ["Vx_kmh", "beta_deg", "w_degps"],
            "outputs": ["d1L", "d1R", "d2L", "d2R", "d3L", "d3R"],
        }
        f_out.write(json.dumps(hello) + "\n")
        f_out.flush()
        ready = recv_line(f_in)
        print("READY:", ready)
        assert ready["type"] == "READY"

        # t=0.5 (t<t0) 与 t=2.0 (t>=t0) 两个状态；step_id 应连续递增。
        for step_id, (t, beta) in enumerate([(0.5, 0.0), (2.0, 0.5)]):
            msg = {"type": "STATE", "step_id": step_id, "t": t,
                   "states": [30.0, beta, 5.0]}
            f_out.write(json.dumps(msg) + "\n")
            f_out.flush()
            ctrl = recv_line(f_in)
            print("CONTROL t=%.1f:" % t, ctrl["controls"], ctrl["diagnostics"])
            d1 = ctrl["controls"][0]
            assert abs(d1 - ctrl["controls"][1]) < 1e-9
            assert abs(ctrl["controls"][2] - ctrl["controls"][3]) < 1e-9
            assert abs(ctrl["controls"][4] - ctrl["controls"][5]) < 1e-9
            if t < 1.0:
                assert abs(d1) < 1e-9, "t<t0 时第一轴应为 0"
            else:
                assert abs(d1 - 3.0) < 1e-9, "第一轴应严格等于用例需求 3 度"

        f_out.write(json.dumps({"type": "RESET"}) + "\n")
        f_out.flush()
        f_out.write(json.dumps({"type": "STOP"}) + "\n")
        f_out.flush()
        s.close()

        proc.wait(timeout=10)
        out = proc.stdout.read()
        print("EXIT:", proc.returncode)
        print(out)
        csv_path = os.path.join(log_dir, "python_signals.csv")
        assert os.path.isfile(csv_path), "未生成 python_signals.csv"
        with open(csv_path, encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        print("CSV 行数(含表头):", len(lines))
        assert len(lines) == 3  # 表头 + 2 条记录
        print("测试通过 ✓")
    finally:
        if proc.poll() is None:
            proc.kill()


if __name__ == "__main__":
    main()
