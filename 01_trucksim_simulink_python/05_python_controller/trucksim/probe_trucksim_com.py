# -*- coding: utf-8 -*-
"""TruckSim COM 属性探查脚本：确认 TXT 字段 -> TruckSim 控件映射。
用法（在装有 TruckSim 的机器上、TruckSim 已打开时）：
  python probe_trucksim_com.py [--run "ORAC-BLFISMC1017 #phase2"]
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser(description="TruckSim COM 属性探查")
    ap.add_argument("--run", default="ORAC-BLFISMC1017 #phase2")
    args = ap.parse_args()

    try:
        import win32com.client
    except Exception as e:
        print("需要安装 pywin32: %s" % e)
        sys.exit(1)

    ts = None
    for progid in ("TruckSim.Application", "TruckSim2019.Application", "TS.Application"):
        try:
            ts = win32com.client.Dispatch(progid)
            print("已连接 COM: %s" % progid)
            break
        except Exception as e:
            print("ProgID %s 连接失败: %s" % (progid, e))
    if ts is None:
        print("无法连接任何 TruckSim COM ProgID。请确认 TruckSim 已打开且该版本注册了 COM 自动化接口。")
        sys.exit(2)

    run = ts.GetRunByName(args.run)
    print("Run:", args.run)
    members = [m for m in dir(run) if not m.startswith("_")]
    print("== Run 对象成员（共 %d 个）==" % len(members))
    print(", ".join(members))

    candidates = ["TSTOP", "TSTOP_WRITE", "TSTART", "SSTART", "SSTOP",
                  "SPEED_TARGET_CONSTANT", "SPEED_TARGET_ID", "OPT_SC",
                  "MY_FRICTION", "MY_FRIC_L"]
    print("== 候选属性读取尝试 ==")
    for name in candidates:
        got = None
        for getm in ("GetVariable", "GetParameter", "GetValue"):
            try:
                m = getattr(run, getm, None)
                if m is not None:
                    got = m(name)
                    print("  %-26s (via %s) = %r" % (name, getm, got))
                    break
            except Exception:
                continue
        if got is None:
            try:
                got = getattr(run, name)
                print("  %-26s (attr) = %r" % (name, got))
            except Exception:
                pass

    print("== 含 var/param/command/set/get/vs 的成员 ==")
    for m in members:
        if any(k in m.lower() for k in ("var", "param", "command", "set", "get", "vs")):
            print("  [%s]" % m)


if __name__ == "__main__":
    main()
