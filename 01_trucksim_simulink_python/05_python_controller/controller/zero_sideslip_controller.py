# -*- coding: utf-8 -*-
"""零质心侧偏角多轴转角分配控制器（阶段二）。

控制律：
  第一轴转角需求由测试用例给出（阶跃或正弦）：
    step:  delta1(t) = 0                t < t0
                        A                t >= t0
    sine:  delta1(t) = 0                t < t0
                        A*sin(2*pi*f*(t-t0))   t >= t0

  其余轴按“稳态零质心侧偏角”前馈计算（线性三轴自行车模型，beta=0）：
    delta2 = (L2 / L1) * delta1
    delta3 = delta1 * [ S2*P - (m*Vx^2 + S1)*Q ] / [ C3*((m*Vx^2 + S1)*L3 - S2) ]
  其中：
    S1 = sum(Ci*Li)，S2 = sum(Ci*Li^2)
    P  = C1 + C2*(L2/L1)，Q = L1*C1 + L2*C2*(L2/L1)
    Ci 为各轴等效侧偏刚度（正值），Li 为各轴相对质心纵向位置（前正后负）。
  该前馈在 Vx->0 时退化为几何分配 delta_i=(Li/L1)*delta1。

  叠加质心侧偏角 PI 反馈（负反馈，作用于二、三轴，用于抑制模型误差/瞬态）：
    fb = -(kp*beta + ki*integral(beta))
    delta2 += (L2/L1)*fb；delta3 += fb
"""
import math


class ZeroSideslipController:
    def __init__(self, cfg, case):
        self.cfg = cfg
        self.case = case
        self.L = [float(x) for x in cfg["vehicle"]["axle_positions_m"]]
        self.C = [abs(float(x)) for x in cfg["vehicle"]["tire_cornering_N_per_rad"]]
        self.m = float(cfg["vehicle"]["m_kg"])
        self.L1, self.L2, self.L3 = self.L
        self.C1, self.C2, self.C3 = self.C

        self.R2 = self.L2 / self.L1
        self.S1 = sum(self.C[i] * self.L[i] for i in range(3))
        self.S2 = sum(self.C[i] * self.L[i] * self.L[i] for i in range(3))
        self.P = self.C1 + self.C2 * self.R2
        self.Q = self.L1 * self.C1 + self.L2 * self.C2 * self.R2

        self.kp = float(case.get("kp_beta", cfg["controller"].get("kp_beta", 0.0)))
        self.ki = float(case.get("ki_beta", cfg["controller"].get("ki_beta", 0.0)))
        self.max_steer = float(case.get("max_steer_deg", cfg["controller"].get("max_steer_deg", 20.0)))
        self.dt = float(case.get("control_dt_s", 0.01))

        self.step_id = 0
        self.beta_int = 0.0

    def reset(self):
        self.step_id = 0
        self.beta_int = 0.0

    def steer_demand1(self, t):
        case = self.case
        kind = case["steer_input_type"]
        A = float(case.get("steer_amplitude_deg", 0.0))
        t0 = float(case.get("steer_start_time_s", 0.0))
        if t < t0:
            return 0.0
        if kind == "step":
            return A
        if kind == "sine":
            f = float(case.get("steer_frequency_hz", 0.0))
            return A * math.sin(2.0 * math.pi * f * (t - t0))
        return 0.0

    def compute(self, t, Vx_kmh, beta_deg, w_degps):
        d1 = self.steer_demand1(t)
        vx = max(Vx_kmh / 3.6, 0.0)

        # 稳态零质心侧偏角前馈：delta2、delta3
        mvx2 = self.m * vx * vx
        den = self.C3 * ((mvx2 + self.S1) * self.L3 - self.S2)
        if abs(den) < 1e-9:
            d3 = (self.L3 / self.L1) * d1
        else:
            num = self.S2 * self.P - (mvx2 + self.S1) * self.Q
            d3 = d1 * num / den
        d2 = self.R2 * d1

        # beta 负反馈（作用于二、三轴）
        beta = float(beta_deg)
        self.beta_int += beta * self.dt
        fb = -(self.kp * beta + self.ki * self.beta_int)
        d2 += self.R2 * fb
        d3 += fb

        d1 = self._clamp(d1)
        d2 = self._clamp(d2)
        d3 = self._clamp(d3)

        ctrl = [d1, d1, d2, d2, d3, d3]
        diag = {
            "delta1_deg": d1,
            "delta2_deg": d2,
            "delta3_deg": d3,
            "beta_err_deg": beta,
            "fb_deg": fb,
            "beta_int_deg": self.beta_int,
        }
        self.step_id += 1
        return ctrl, diag

    def _clamp(self, x):
        return max(-self.max_steer, min(self.max_steer, x))


def load_controller(cfg, case):
    return ZeroSideslipController(cfg, case)
