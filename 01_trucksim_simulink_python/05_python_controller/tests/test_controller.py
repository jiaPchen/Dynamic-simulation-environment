# -*- coding: utf-8 -*-
"""零质心侧偏角控制器离线验证：
1) 低速极限退化为几何分配 delta_i=(Li/L1)*delta1；
2) 线性三轴模型 40km/h 阶跃/正弦闭环仿真，质心侧偏角应接近 0。
运行：python tests/test_controller.py
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)          # 05_python_controller
sys.path.insert(0, ROOT)

from controller.zero_sideslip_controller import ZeroSideslipController  # noqa: E402


def load_cfg():
    import yaml
    with open(os.path.join(ROOT, "config", "vehicle_config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


CFG = load_cfg()


def make_case(kind):
    return {
        "case_name": "test_" + kind,
        "steer_input_type": kind,
        "steer_amplitude_deg": "2" if kind == "sine" else "3",
        "steer_frequency_hz": "0.2" if kind == "sine" else "0",
        "steer_start_time_s": "1",
        "stop_time_s": "12" if kind == "sine" else "10",
        "initial_speed_kmh": "40",
        "kp_beta": "0.6",
        "ki_beta": "0.5",
        "max_steer_deg": "20",
        "control_dt_s": "0.01",
    }


def simulate(case, Vx_kmh, T_end):
    ctrl = ZeroSideslipController(CFG, case)
    L = [float(x) for x in CFG["vehicle"]["axle_positions_m"]]
    C = [abs(float(x)) for x in CFG["vehicle"]["tire_cornering_N_per_rad"]]
    m = float(CFG["vehicle"]["m_kg"])
    Iz = float(CFG["vehicle"]["iz_kgm2"])
    Vx = Vx_kmh / 3.6
    dt = 0.01
    beta = 0.0
    w = 0.0
    max_beta = 0.0
    t = 0.0
    while t <= T_end + 1e-9:
        controls, _ = ctrl.compute(t, Vx_kmh, beta * 180 / math.pi, w * 180 / math.pi)
        dd = [controls[0], controls[2], controls[4]]
        dd = [x * math.pi / 180.0 for x in dd]
        Fy = -sum(C[i] * (beta + L[i] * w / Vx - dd[i]) for i in range(3))
        Mz = -sum(L[i] * C[i] * (beta + L[i] * w / Vx - dd[i]) for i in range(3))
        beta += (Fy / (m * Vx) - w) * dt
        w += (Mz / Iz) * dt
        max_beta = max(max_beta, abs(beta * 180 / math.pi))
        t += dt
    return max_beta, beta * 180 / math.pi


def main():
    ctrl = ZeroSideslipController(CFG, make_case("step"))
    _, diag = ctrl.compute(2.0, 0.1, 0.0, 0.0)
    r2 = diag["delta2_deg"] / 3.0
    r3 = diag["delta3_deg"] / 3.0
    print("低速(0.1km/h) d2/d1=%.4f 期望 %.4f" % (r2, 0.025 / 1.058))
    print("低速(0.1km/h) d3/d1=%.4f 期望 %.4f" % (r3, -0.958 / 1.058))
    assert abs(r3 - (-0.958 / 1.058)) < 0.02

    b_step, b_step_ss = simulate(make_case("step"), 40.0, 10.0)
    print("阶跃 40km/h 闭环 max|beta|=%.4f deg, 稳态=%.4f deg" % (b_step, b_step_ss))
    assert b_step < 0.60
    assert abs(b_step_ss) < 0.05

    b_sine, _ = simulate(make_case("sine"), 40.0, 12.0)
    print("正弦 40km/h 闭环 max|beta|=%.4f deg" % b_sine)
    assert b_sine < 0.35

    print("控制器离线验证全部通过 ✓")


if __name__ == "__main__":
    main()
