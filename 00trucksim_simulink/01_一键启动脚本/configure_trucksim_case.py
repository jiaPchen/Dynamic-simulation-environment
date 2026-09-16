#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply one phase-one TXT case to the active TruckSim simfile."""
import argparse
import os
import sys


def read_case(path):
    case = {}
    with open(path, encoding="utf-8-sig") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            case[key.strip()] = value.strip()
    required = ("case_name", "stop_time_s", "initial_speed_kmh")
    missing = [key for key in required if not case.get(key)]
    if missing:
        raise ValueError("测试用例缺少字段: %s" % ", ".join(missing))
    case.setdefault("target_speed_kmh", case["initial_speed_kmh"])
    case.setdefault("road_friction", "0.85")
    return case


def main():
    parser = argparse.ArgumentParser(description="阶段一 TruckSim 工况配置")
    parser.add_argument("--case", required=True)
    parser.add_argument("--simfile", required=True)
    args = parser.parse_args()

    stage1_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(stage1_root)
    phase2_trucksim = os.path.join(
        project_root, "01_trucksim_simulink_python", "05_python_controller", "trucksim"
    )
    if not os.path.isfile(os.path.join(phase2_trucksim, "trucksim_com.py")):
        raise FileNotFoundError("缺少共享 TruckSim 配置模块: %s" % phase2_trucksim)
    sys.path.insert(0, phase2_trucksim)
    from trucksim_com import configure_trucksim

    case = read_case(args.case)
    config = {"trucksim": {
        "simfile_path": os.path.abspath(args.simfile),
        "allow_par_file_patch": True,
        "road_base_mu": 0.85,
    }}
    if not configure_trucksim(case, config):
        print("CONFIG_FAIL", flush=True)
        return 1
    print("CONFIG_READY %s" % case["case_name"], flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("CONFIG_FAIL %s" % exc, flush=True)
        raise SystemExit(1)
