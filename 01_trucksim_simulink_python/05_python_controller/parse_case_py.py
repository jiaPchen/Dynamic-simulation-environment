# -*- coding: utf-8 -*-
"""阶段二 TXT 测试用例解析（Python 版）。
与 01_一键启动脚本/parse_case.m 保持相同语义：
- 支持 # 注释与空行；
- key = value 格式；
- 必填字段与数值范围校验；
- 文件名与 case_name 一致性提示。
"""
import os


REQUIRED = {
    "schema_version": (int, 1, 99),
    "case_name": None,
    "stop_time_s": (float, 0.0, 1e6),
    "initial_speed_kmh": (float, 0.0, 500.0),
    "steer_input_type": None,
}

OPTIONAL = {
    "source_case_id": str,
    "trucksim_scenario": str,
    "description": str,
    "target_speed_kmh": (float, 0.0, 500.0),
    "steer_amplitude_deg": (float, -90.0, 90.0),
    "steer_frequency_hz": (float, 0.0, 100.0),
    "steer_start_time_s": (float, 0.0, 1e6),
    "road_friction": (float, 0.0, 1.5),
    "road_grade": (float, -90.0, 90.0),
    "controller_mode": str,
    "control_dt_s": (float, 1e-4, 1.0),
    "kp_beta": (float, -10.0, 10.0),
    "ki_beta": (float, -10.0, 10.0),
    "max_steer_deg": (float, 0.0, 90.0),
}


def parse_case(txt_file):
    if not os.path.isfile(txt_file):
        raise FileNotFoundError("用例文件不存在: %s" % txt_file)
    c = {}
    with open(txt_file, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if not key.replace("_", "").isalnum():
                continue
            c[key] = val

    missing = [k for k in REQUIRED if k not in c]
    if missing:
        raise ValueError("缺少必填字段: %s" % ", ".join(missing))

    for key, spec in REQUIRED.items():
        if spec is not None and key in c:
            _check(key, c[key], spec)
    for key, spec in OPTIONAL.items():
        if key in c:
            _check(key, c[key], spec)

    base = os.path.splitext(os.path.basename(txt_file))[0]
    if c["case_name"] != base:
        print("[警告] 文件名(%s)与 case_name(%s)不一致" % (base, c["case_name"]))

    c["steer_input_type"] = c["steer_input_type"].lower()
    if c["steer_input_type"] not in ("step", "sine"):
        raise ValueError("steer_input_type=%r 不支持，阶段二仅支持 step 或 sine" % c["steer_input_type"])
    return c


def _check(key, val, spec):
    if not isinstance(spec, tuple):
        return  # 字符串字段，不做数值范围校验
    cast, lo, hi = spec
    try:
        v = cast(val)
    except (TypeError, ValueError):
        raise ValueError("字段 %s 的值 %r 不是有效数值" % (key, val))
    if v < lo or v > hi:
        raise ValueError("字段 %s 的值 %r 超出范围 [%s, %s]" % (key, val, lo, hi))


if __name__ == "__main__":
    import sys
    print(parse_case(sys.argv[1]))
