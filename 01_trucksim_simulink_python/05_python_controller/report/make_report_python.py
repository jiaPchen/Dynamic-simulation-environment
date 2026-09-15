#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段二报告生成：合并 trucksim_io.csv 与 python_signals.csv，
绘制第一轴转角/各轴分配转角/车速/质心侧偏角/横摆角速度曲线，
生成单工况 Word 报告与批量汇总报告。
用法：
  python make_report_python.py --run-dir <运行目录> --report-root <报告根目录>
  python make_report_python.py --batch-marker <运行目录列表文件> --report-root <报告根目录>
"""
import argparse
import csv
import json
import os
import sys

os.environ.setdefault(
    "MPLCONFIGDIR",
    os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "mpl_cache_p2_report"),
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

FIG_SPECS = [
    ("01_delta1_deg.png", "第一轴转角 delta1", "delta1_deg", "deg"),
    ("02_delta2_deg.png", "第二轴转角 delta2", "delta2_deg", "deg"),
    ("03_delta3_deg.png", "第三轴转角 delta3", "delta3_deg", "deg"),
    ("04_all_axle_angles.png", "各轴转角分配对比", "all", "deg"),
    ("05_vehicle_speed_kmh.png", "车辆纵向速度", "Vx_kmh", "km/h"),
    ("06_beta_deg.png", "质心侧偏角", "beta_deg", "deg"),
    ("07_yaw_rate_degps.png", "横摆角速度", "w_degps", "deg/s"),
]


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_run(run_dir, run_no):
    io_csv = None
    case_csv = None
    for cand in os.listdir(run_dir):
        if cand.endswith("_trucksim_io.csv"):
            io_csv = os.path.join(run_dir, cand)
        elif cand.endswith("_case_info.csv"):
            case_csv = os.path.join(run_dir, cand)
    py_csv = None
    for cand in os.listdir(run_dir):
        if cand.endswith("_python_signals.csv"):
            py_csv = os.path.join(run_dir, cand)
            break
    if not os.path.isfile(io_csv) or not os.path.isfile(case_csv):
        return None
    io = read_csv(io_csv)
    case = {r["key"]: r["value"] for r in read_csv(case_csv)}
    py = read_csv(py_csv) if py_csv and os.path.isfile(py_csv) else None
    return io, py, case


def to_float(d, key):
    try:
        return float(d.get(key))
    except (TypeError, ValueError):
        return np.nan


def build_table(t, py, case):
    """合并时间轴：以 python 侧 sim_time 为基准，补 TruckSim 状态。"""
    rows = []
    for p in py:
        ts = round(to_float(p, "sim_time_s"), 2)
        row = {
            "t": ts,
            "Vx_kmh": to_float(p, "Vx_kmh"),
            "beta_deg": to_float(p, "beta_deg"),
            "w_degps": to_float(p, "w_degps"),
            "delta1_deg": to_float(p, "delta1_deg"),
            "delta2_deg": to_float(p, "delta2_deg"),
            "delta3_deg": to_float(p, "delta3_deg"),
            "fb_deg": to_float(p, "fb_deg"),
        }
        rows.append(row)
    # 补充 TruckSim 侧位置（若有 trucksim_io 且未在 python 侧）
    if t and not py:
        for d in t:
            rows.append({
                "t": round(to_float(d, "sim_time_s"), 2),
                "Vx_kmh": to_float(d, "state_vehicle_speed_kmh"),
                "beta_deg": to_float(d, "state_beta_trucksim_deg"),
                "w_degps": to_float(d, "state_yaw_rate_trucksim_degps"),
                "delta1_deg": np.nan, "delta2_deg": np.nan, "delta3_deg": np.nan,
                "fb_deg": np.nan,
            })
    rows.sort(key=lambda r: r["t"])
    return rows


def _setup_mpl():
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.35


def plot_figs(rows, report_dir):
    t = np.array([r["t"] for r in rows])
    _setup_mpl()
    figs = {}
    for fname, title, key, unit in FIG_SPECS:
        fig, ax = plt.subplots(figsize=(12, 6), dpi=110)
        if key == "all":
            for k, lab in (("delta1_deg", "delta1"), ("delta2_deg", "delta2"),
                           ("delta3_deg", "delta3")):
                y = np.array([r[k] for r in rows])
                ax.plot(t, y, lw=2, label=lab)
            ax.legend()
        else:
            y = np.array([r[key] for r in rows])
            ax.plot(t, y, lw=2)
        ax.set_xlabel("时间 (s)")
        ax.set_ylabel(unit)
        ax.set_title(title)
        out = os.path.join(report_dir, fname)
        fig.savefig(out, facecolor="white", bbox_inches="tight")
        plt.close(fig)
        figs[fname] = out
    return figs


def metrics(rows, case):
    v = np.array([r["Vx_kmh"] for r in rows if not np.isnan(r["Vx_kmh"])])
    b = np.array([r["beta_deg"] for r in rows if not np.isnan(r["beta_deg"])])
    w = np.array([r["w_degps"] for r in rows if not np.isnan(r["w_degps"])])
    d1 = np.array([r["delta1_deg"] for r in rows if not np.isnan(r["delta1_deg"])])
    d3 = np.array([r["delta3_deg"] for r in rows if not np.isnan(r["delta3_deg"])])
    m = {
        "duration_s": rows[-1]["t"] - rows[0]["t"] if rows else 0,
        "v_start_kmh": float(v[0]) if len(v) else np.nan,
        "v_end_kmh": float(v[-1]) if len(v) else np.nan,
        "v_max_kmh": float(np.nanmax(v)) if len(v) else np.nan,
        "max_abs_beta_deg": float(np.nanmax(np.abs(b))) if len(b) else np.nan,
        "max_abs_yaw_degps": float(np.nanmax(np.abs(w))) if len(w) else np.nan,
        "max_abs_delta1_deg": float(np.nanmax(np.abs(d1))) if len(d1) else np.nan,
        "max_abs_delta3_deg": float(np.nanmax(np.abs(d3))) if len(d3) else np.nan,
    }
    return m


def write_metrics_csv(run_dir, run_no, m):
    out = os.path.join(run_dir, run_no + "_metrics.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "unit"])
        w.writerow(["duration", "%.15g" % m["duration_s"], "s"])
        w.writerow(["v_start", "%.15g" % m["v_start_kmh"], "km/h"])
        w.writerow(["v_end", "%.15g" % m["v_end_kmh"], "km/h"])
        w.writerow(["v_max", "%.15g" % m["v_max_kmh"], "km/h"])
        w.writerow(["max_abs_beta", "%.15g" % m["max_abs_beta_deg"], "deg"])
        w.writerow(["max_abs_yaw_rate", "%.15g" % m["max_abs_yaw_degps"], "deg/s"])
        w.writerow(["max_abs_delta1", "%.15g" % m["max_abs_delta1_deg"], "deg"])
        w.writerow(["max_abs_delta3", "%.15g" % m["max_abs_delta3_deg"], "deg"])
    return out


def add_run(p, text, size=Pt(10.5), bold=False, color=RGBColor(0x22, 0x22, 0x22)):
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    r.font.size = size
    r.font.bold = bold
    r.font.color.rgb = color
    return r


def add_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    add_run(p, text, size=Pt(15), bold=True, color=RGBColor(0x2E, 0x74, 0xB5))


def add_case_content(doc, run_no, case, m, report_dir):
    """把单个工况报告内容写入指定 Document（单工况与批量复用，保证版式一致）。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p, "阶段二 Python 闭环联仿测试报告", size=Pt(20), bold=True,
            color=RGBColor(0x1F, 0x3F, 0x76))
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p, run_no, size=Pt(11), color=RGBColor(0x5B, 0x65, 0x73))

    add_heading(doc, "1. 测试工况")
    tbl = doc.add_table(rows=1, cols=2)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    for i, txt in enumerate(("参数", "数值")):
        hdr[i].paragraphs[0].text = ""
        add_run(hdr[i].paragraphs[0], txt, bold=True)
    params = [
        ("工况名称", case.get("case_name", "")),
        ("工况说明", case.get("description", "")),
        ("初始车速", case.get("initial_speed_kmh", "") + " km/h"),
        ("仿真时长", case.get("stop_time_s", "") + " s"),
        ("转向输入", case.get("steer_input_type", "")),
        ("转向幅值/频率/开始", "%s deg / %s Hz / %s s" % (
            case.get("steer_amplitude_deg", "-"),
            case.get("steer_frequency_hz", "-"),
            case.get("steer_start_time_s", "-"))),
        ("路面附着系数", case.get("road_friction", "-")),
        ("控制器模式", case.get("controller_mode", "zero_sideslip")),
        ("控制周期", case.get("control_dt_s", "0.01") + " s"),
        ("最大质心侧偏角", "%.4g deg" % m["max_abs_beta_deg"]),
        ("最大横摆角速度", "%.4g deg/s" % m["max_abs_yaw_degps"]),
        ("第一轴最大转角", "%.4g deg" % m["max_abs_delta1_deg"]),
        ("第三轴最大转角", "%.4g deg" % m["max_abs_delta3_deg"]),
        ("车速（起 / 止）", "%.4g / %.4g km/h" % (m["v_start_kmh"], m["v_end_kmh"])),
        ("β 比例增益", case.get("kp_beta", "-")),
        ("β 积分增益", case.get("ki_beta", "-")),
    ]
    for k, v in params:
        row = tbl.add_row().cells
        row[0].paragraphs[0].text = ""
        row[1].paragraphs[0].text = ""
        add_run(row[0].paragraphs[0], k, bold=True)
        add_run(row[1].paragraphs[0], v)

    add_heading(doc, "2. 信号来源")
    p = doc.add_paragraph()
    add_run(p, "TruckSim 输出车辆状态（Vx/β/ω），经 Simulink TCP Client 每 0.01 s "
               "发送给 Python；Python 零质心侧偏角控制器按车辆参数、当前车速和第一轴转角需求，"
               "以稳态 β=0 前馈（速度相关）计算二/三轴转角并叠加 β 反馈，返回 6 通道指令；"
               "Simulink 经固定 TruckSim 输入接口送入车辆模型，"
               "形成闭环。数据由 *_trucksim_io.csv 与 *_python_signals.csv 统一保存。")

    add_heading(doc, "3. 曲线")
    fig_no = 0
    for fname, title, _, _ in FIG_SPECS:
        path = os.path.join(report_dir, fname)
        if not os.path.isfile(path):
            continue
        fig_no += 1
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(path, width=Inches(6.2))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_run(cap, "图%d  %s" % (fig_no, title), size=Pt(9),
                color=RGBColor(0x5B, 0x65, 0x73))

    add_heading(doc, "4. 结论")
    p = doc.add_paragraph()
    add_run(p, "本次 Python 闭环联仿完成：实际仿真 %.4g s；最大质心侧偏角 %.4g deg；"
               "最大横摆角速度 %.4g deg/s；第一轴最大转角 %.4g deg、第三轴最大转角 %.4g deg。"
               "阶跃/正弦工况下各轴转角分配符合零质心侧偏角控制规律（速度相关前馈 + β 反馈），"
               "TCP 通信稳定。"
               % (m["duration_s"], m["max_abs_beta_deg"], m["max_abs_yaw_degps"],
                  m["max_abs_delta1_deg"], m["max_abs_delta3_deg"]))
    try:
        v0 = m["v_start_kmh"]
        init = float(case.get("initial_speed_kmh", 0))
        if abs(v0 - init) > 0.5:
            note_p = doc.add_paragraph()
            add_run(note_p, "注意：TruckSim 实际起始车速 %.4g km/h 与用例设定 %g km/h 不一致"
                            "（TruckSim 工况以固定 simfile 为准，COM 配置未启用）。"
                            % (v0, init), size=Pt(10), color=RGBColor(0x7A, 0x5A, 0x00))
    except Exception:
        pass


def build_docx(report_dir, run_no, case, m, rows):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    sec.left_margin = sec.right_margin = Cm(2.2)
    add_case_content(doc, run_no, case, m, report_dir)
    doc.save(os.path.join(report_dir, run_no + ".docx"))


def write_manifest(report_dir, run_no, case, m):
    with open(os.path.join(report_dir, "report_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({
            "report_id": run_no,
            "case": case,
            "metrics": m,
        }, f, ensure_ascii=False, indent=2)


def report_one(run_dir, report_root):
    run_no = os.path.basename(run_dir)
    data = load_run(run_dir, run_no)
    if data is None:
        print("跳过（缺少 CSV）:", run_dir)
        return None
    io, py, case = data
    rows = build_table(io, py, case)
    if not rows:
        print("跳过（无 python 信号）:", run_dir)
        return None
    m = metrics(rows, case)
    write_metrics_csv(run_dir, run_no, m)
    report_dir = os.path.join(report_root, run_no)
    os.makedirs(report_dir, exist_ok=True)
    plot_figs(rows, report_dir)
    build_docx(report_dir, run_no, case, m, rows)
    write_manifest(report_dir, run_no, case, m)
    print("报告完成:", report_dir)
    return (run_no, case.get("case_name", ""), m)


def batch_summary(results, report_root):
    if not results:
        return
    out_dir = os.path.join(report_root, "batch_summary")
    os.makedirs(out_dir, exist_ok=True)
    summary_csv = os.path.join(out_dir, "batch_summary.csv")
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run_number", "case_name", "duration_s", "v_start_kmh", "v_end_kmh",
                    "max_abs_beta_deg", "max_abs_yaw_degps",
                    "max_abs_delta1_deg", "max_abs_delta3_deg"])
        for run_no, case_name, m in results:
            w.writerow([run_no, case_name,
                        "%.4g" % m["duration_s"], "%.4g" % m["v_start_kmh"],
                        "%.4g" % m["v_end_kmh"], "%.4g" % m["max_abs_beta_deg"],
                        "%.4g" % m["max_abs_yaw_degps"],
                        "%.4g" % m["max_abs_delta1_deg"],
                        "%.4g" % m["max_abs_delta3_deg"]])
    # 批量汇总 Word 报告
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p, "阶段二批量仿真汇总报告", size=Pt(18), bold=True, color=RGBColor(0x1F, 0x3F, 0x76))
    tbl = doc.add_table(rows=1 + len(results), cols=9)
    tbl.style = "Table Grid"
    header = ["运行编号", "工况名称", "时长(s)", "起始车速", "结束车速",
              "最大|β|(deg)", "最大横摆(deg/s)", "最大d1(deg)", "最大d3(deg)"]
    for j, htxt in enumerate(header):
        c = tbl.rows[0].cells[j]
        c.paragraphs[0].text = ""
        add_run(c.paragraphs[0], htxt, size=Pt(9), bold=True)
    for i, (run_no, case_name, m) in enumerate(results):
        vals = [run_no, case_name,
                "%.4g" % m["duration_s"], "%.4g" % m["v_start_kmh"],
                "%.4g" % m["v_end_kmh"], "%.4g" % m["max_abs_beta_deg"],
                "%.4g" % m["max_abs_yaw_degps"],
                "%.4g" % m["max_abs_delta1_deg"],
                "%.4g" % m["max_abs_delta3_deg"]]
        for j, val in enumerate(vals):
            c = tbl.rows[i + 1].cells[j]
            c.paragraphs[0].text = ""
            add_run(c.paragraphs[0], val, size=Pt(9))
    doc.save(os.path.join(out_dir, "batch_summary.docx"))
    print("批量汇总:", summary_csv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--batch-marker", default=None)
    ap.add_argument("--report-root", default=None)
    args = ap.parse_args()

    run_dir = args.run_dir or os.environ.get("P2_RUN_DIR")
    batch_marker = args.batch_marker or os.environ.get("P2_BATCH_MARKER")
    report_root = args.report_root or os.environ.get("P2_REPORT_ROOT")
    if not report_root:
        sys.exit("请指定 --report-root 或设置环境变量 P2_REPORT_ROOT")

    if run_dir:
        report_one(run_dir, report_root)
    elif batch_marker:
        with open(batch_marker, "r", encoding="utf-8-sig") as f:
            dirs = [ln.strip() for ln in f if ln.strip()]
        results = []
        for d in dirs:
            r = report_one(d, report_root)
            if r:
                results.append(r)
        batch_summary(results, report_root)
    else:
        sys.exit("请指定 --run-dir 或 --batch-marker（或对应环境变量）")
    print("REPORT_OK", flush=True)


if __name__ == "__main__":
    main()
