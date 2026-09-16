#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_test_report_new.py - 新版测试报告一键生成脚本（适配 TruckSim-only 模型）
读取 run_case_new.m 导出的 trucksim_io.csv / case_info.csv，绘制时间历程曲线，
并按模板生成 Word 测试报告，输出到 04_测试报告\\<运行编号>\\。
注意：新模型不再包含 3DOF 参考模型，所有车辆状态信号均来自 TruckSim
S-Function 的 To Workspace 输出。
用法：
    python make_test_report_new.py [--run 运行编号或目录] [--data-root 数据根目录]
                                   [--user 用户文件夹] [--case-dir 测试用例目录]
                                   [--report-root 报告根目录]
不带 --run 时自动选择最近一次运行（第 NNN 次编号最大）。
依赖：matplotlib、numpy、python-docx。
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
import tempfile

os.environ.setdefault(
    "MPLCONFIGDIR",
    os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "mpl_cache_test_report"),
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor, Twips

# 以本脚本所在的阶段一目录为根目录，项目移动后仍可直接使用。
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_ROOT = os.path.join(ROOT, "03_数据存储")
DEFAULT_USER = "阶跃输入转角"
DEFAULT_CASE_DIR = os.path.join(ROOT, "02_测试用例")
DEFAULT_REPORT_ROOT = os.path.join(ROOT, "04_测试报告")

FONT_LATIN = "Calibri"
FONT_EAST = "宋体"
FONT_HEADING_EAST = "微软雅黑"
COLOR_HEADING = RGBColor(0x2E, 0x74, 0xB5)
COLOR_TITLE = RGBColor(0x0B, 0x25, 0x45)
COLOR_GRAY = RGBColor(0x5B, 0x65, 0x73)
COLOR_BODY = RGBColor(0x22, 0x22, 0x22)
COLOR_NOTE = RGBColor(0x7A, 0x5A, 0x00)

FILENAME_RE = re.compile(r".*_第(\d+)次")


# ----------------------------------------------------------------------------
# 数据读取与指标计算
# ----------------------------------------------------------------------------
def find_latest_run(data_root, user_name):
    user_dir = os.path.join(data_root, user_name)
    if not os.path.isdir(user_dir):
        return None, None
    runs = []
    for name in os.listdir(user_dir):
        m = FILENAME_RE.search(name)
        if m and os.path.isdir(os.path.join(user_dir, name)):
            runs.append((int(m.group(1)), name))
    if not runs:
        return None, None
    runs.sort()
    return os.path.join(user_dir, runs[-1][1]), runs[-1][1]


def iter_user_dirs(data_root):
    if not os.path.isdir(data_root):
        return
    for user in sorted(os.listdir(data_root)):
        user_dir = os.path.join(data_root, user)
        if os.path.isdir(user_dir):
            yield user, user_dir


def find_run_anywhere(data_root, run_arg):
    """在所有用户文件夹下按运行编号/目录名查找运行。"""
    for _, user_dir in iter_user_dirs(data_root):
        cand = os.path.join(user_dir, run_arg)
        if os.path.isdir(cand):
            return cand, run_arg
    if run_arg.isdigit():
        for _, user_dir in iter_user_dirs(data_root):
            matches = [n for n in os.listdir(user_dir)
                       if FILENAME_RE.search(n) and
                       FILENAME_RE.search(n).group(1) == run_arg.lstrip("0")]
            if len(matches) == 1:
                return os.path.join(user_dir, matches[0]), matches[0]
    return None, None


def find_latest_anywhere(data_root):
    """在所有用户文件夹下取最近一次运行。"""
    best = None
    for _, user_dir in iter_user_dirs(data_root):
        for name in os.listdir(user_dir):
            m = FILENAME_RE.search(name)
            if m and os.path.isdir(os.path.join(user_dir, name)):
                key = (m.group(1), name)
                if best is None or key[0] > best[0]:
                    best = (key[0], os.path.join(user_dir, name), name)
    if best is None:
        return None, None
    return best[1], best[2]


def resolve_run(data_root, user_name, run_arg):
    if not run_arg:
        return find_latest_run(data_root, user_name)
    if os.path.isdir(run_arg):
        run_dir = run_arg
        run_number = os.path.basename(run_dir)
        return run_dir, run_number
    user_dir = os.path.join(data_root, user_name)
    if os.path.isdir(os.path.join(user_dir, run_arg)):
        return os.path.join(user_dir, run_arg), run_arg
    if os.path.isdir(user_dir):
        cand = [n for n in os.listdir(user_dir)
                if FILENAME_RE.search(n) and FILENAME_RE.search(n).group(1) == run_arg.lstrip("0")]
        if len(cand) == 1:
            return os.path.join(user_dir, cand[0]), cand[0]
    return None, None


def load_case_info(case_info_csv):
    info = {}
    with open(case_info_csv, "r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                info[row[0].strip()] = row[1].strip()
    return info


def load_data(io_csv):
    with open(io_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = {name: [] for name in header}
        numeric = set()
        seen = False
        for row in reader:
            if not row:
                continue
            if not seen:
                for i, name in enumerate(header):
                    if i < len(row) and row[i] != "":
                        try:
                            float(row[i])
                            numeric.add(name)
                        except ValueError:
                            pass
                seen = True
            for i, name in enumerate(header):
                if name in numeric and i < len(row) and row[i] != "":
                    cols[name].append(float(row[i]))
    if "sim_time_s" not in cols:
        sys.exit("数据文件缺少必需列: sim_time_s")
    return {name: np.asarray(values, dtype=float) for name, values in cols.items()
            if name in numeric}


def compute_metrics(df):
    t = df["sim_time_s"]
    v = df["state_vehicle_speed_kmh"]
    x = df["state_x_m"]
    y = df["state_y_m"]
    beta_ts = (
        df["state_beta_trucksim_deg"]
        if "state_beta_trucksim_deg" in df
        else np.zeros_like(t)
    )
    w_ts = (
        df["state_yaw_rate_trucksim_degps"]
        if "state_yaw_rate_trucksim_degps" in df
        else np.zeros_like(t)
    )
    delta = (
        df["state_steer_delta_deg"]
        if "state_steer_delta_deg" in df
        else None
    )
    try:
        trapz = np.trapezoid
    except AttributeError:  # numpy < 2.0
        trapz = np.trapz
    distance = float(trapz(v / 3.6, t))
    metrics = {
        "t": t,
        "v_kmh": v,
        "x_m": x,
        "y_m": y,
        "beta_trucksim_deg": beta_ts,
        "yaw_trucksim_degps": w_ts,
        "duration_s": float(t[-1] - t[0]),
        "v_start_kmh": float(v[0]),
        "v_end_kmh": float(v[-1]),
        "v_min_kmh": float(v.min()),
        "v_max_kmh": float(v.max()),
        "distance_m": distance,
        "max_abs_y_m": float(np.max(np.abs(y))),
        "max_yaw_trucksim_degps": float(np.max(np.abs(w_ts))),
        "max_abs_beta_trucksim_deg": float(np.max(np.abs(beta_ts))),
        "delta_deg": delta,
    }
    return metrics


# ----------------------------------------------------------------------------
# 绘图
# ----------------------------------------------------------------------------
def _setup_mpl():
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 18
    plt.rcParams["axes.labelsize"] = 19
    plt.rcParams["axes.titlesize"] = 22
    plt.rcParams["legend.fontsize"] = 17
    plt.rcParams["legend.framealpha"] = 0.9
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.35


def _new_fig():
    fig, ax = plt.subplots(figsize=(20, 11.67), dpi=100)
    fig.subplots_adjust(left=0.07, right=0.975, top=0.94, bottom=0.085)
    return fig, ax


def plot_speed(m, out, target_kmh=None):
    fig, ax = _new_fig()
    ax.plot(m["t"], m["v_kmh"], lw=2.2, label="车辆实际速度（TruckSim）")
    if target_kmh is not None:
        ax.axhline(target_kmh, color="C3", ls="--", lw=2.0,
                   label="目标车速（用例设定 %g km/h）" % target_kmh)
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("车速 (km/h)")
    ax.set_title("车辆实际速度随时间变化")
    ax.legend()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def plot_beta(m, out):
    fig, ax = _new_fig()
    ax.plot(m["t"], m["beta_trucksim_deg"], lw=2.2, label="TruckSim")
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("质心侧偏角 (deg)")
    ax.set_title("质心侧偏角随时间变化（TruckSim）")
    ax.legend()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def plot_yaw(m, out):
    fig, ax = _new_fig()
    ax.plot(m["t"], m["yaw_trucksim_degps"], lw=2.2, label="TruckSim")
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("横摆角速度 (deg/s)")
    ax.set_title("横摆角速度随时间变化（TruckSim）")
    ax.legend()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def plot_trajectory(m, out):
    fig, ax = _new_fig()
    ax.plot(m["x_m"], m["y_m"], lw=2.2, color="C0", label="TruckSim 行驶轨迹")
    ax.set_xlabel("纵向位置 x (m)")
    ax.set_ylabel("横向位置 y (m)")
    ax.set_title("车辆行驶轨迹（X-Y 平面）")
    ax.set_aspect("equal", adjustable="box")
    ax.legend()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def plot_x_position(m, out):
    fig, ax = _new_fig()
    ax.plot(m["t"], m["x_m"], lw=2.2, color="C0")
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("纵向位置 x (m)")
    ax.set_title("车辆纵向位置随时间变化")
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def plot_y_position(m, out):
    fig, ax = _new_fig()
    ax.plot(m["t"], m["y_m"], lw=2.2, color="C1")
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("横向位置 y (m)")
    ax.set_title("车辆横向位置随时间变化")
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def plot_speed_vs_lateral(m, out):
    fig, ax = _new_fig()
    ax.plot(m["y_m"], m["v_kmh"], lw=2.2, color="C2")
    ax.set_xlabel("横向位移 y (m)")
    ax.set_ylabel("车速 (km/h)")
    ax.set_title("车速随横向位移变化")
    fig.savefig(out, facecolor="white")
    plt.close(fig)


def plot_steer_delta(m, out):
    fig, ax = _new_fig()
    ax.plot(m["t"], m["delta_deg"], lw=2.2, color="C4")
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("转向输入 delta (deg)")
    ax.set_title("转向输入信号随时间变化（第一轴）")
    fig.savefig(out, facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------------------
# Word 报告生成
# ----------------------------------------------------------------------------
def add_run(p, text, size=Pt(11), bold=False, color=COLOR_BODY,
            east=FONT_EAST, latin=FONT_LATIN):
    r = p.add_run(text)
    r.font.name = latin
    r._element.rPr.rFonts.set(qn("w:eastAsia"), east)
    r.font.size = size
    r.font.bold = bold
    r.font.color.rgb = color
    return r


def add_page_field(p, size=Pt(9), color=COLOR_GRAY):
    r = p.add_run()
    r.font.name = FONT_LATIN
    r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_EAST)
    r.font.size = size
    r.font.color.rgb = color
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    r._r.append(fld1)
    r._r.append(instr)
    r._r.append(fld2)


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = OxmlElement("w:tcMar")
    for tag, val in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        el = OxmlElement("w:" + tag)
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        tc_mar.append(el)
    tc_pr.append(tc_mar)


def add_heading(doc, text, page_break=False):
    if page_break:
        br_p = doc.add_paragraph()
        br_p.add_run().add_break(WD_BREAK.PAGE)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    add_run(p, text, size=Pt(16), bold=True, color=COLOR_HEADING, east=FONT_HEADING_EAST)
    return p


def build_docx(report_dir, run_number, params, signal_source, sections,
               conclusion_auto, conclusion_note):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.5)

    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(hp, "联合仿真测试报告", size=Pt(9), color=COLOR_GRAY)
    p_pr = hp._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "5B6573")
    p_bdr.append(bottom)
    p_pr.append(p_bdr)

    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(fp, "%s | 第" % run_number, size=Pt(9), color=COLOR_GRAY)
    add_page_field(fp)
    add_run(fp, " 页", size=Pt(9), color=COLOR_GRAY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p, "PYTHON / SIMULINK / TRUCKSIM", size=Pt(11), bold=True,
            color=RGBColor(0x2E, 0x74, 0xB5))
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    add_run(p, "Python / Simulink / TruckSim 联合仿真测试报告",
            size=Pt(23), bold=True, color=COLOR_TITLE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(12)
    add_run(p, run_number, size=Pt(12), color=COLOR_GRAY)

    # 1. 测试工况
    add_heading(doc, "1. 测试工况")
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = 1
    tbl.autofit = False
    tbl_pr = tbl._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    widths = [Twips(2700), Twips(6660)]
    for i, w in enumerate(widths):
        for cell in tbl.columns[i].cells:
            cell.width = w
    hdr = tbl.rows[0].cells
    for i, txt in enumerate(("参数", "数值")):
        cell = hdr[i]
        shade_cell(cell, "F2F4F7")
        cell_margins(cell)
        cp = cell.paragraphs[0]
        cp.paragraph_format.space_before = Pt(1)
        cp.paragraph_format.space_after = Pt(1)
        add_run(cp, txt, size=Pt(9.5), bold=True, color=COLOR_TITLE)
    for label, value in params:
        row = tbl.add_row().cells
        c0, c1 = row[0], row[1]
        shade_cell(c0, "F7F9FB")
        cell_margins(c0)
        cell_margins(c1)
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_before = Pt(1)
        p0.paragraph_format.space_after = Pt(1)
        add_run(p0, label, size=Pt(9), bold=True, color=COLOR_TITLE)
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(1)
        p1.paragraph_format.space_after = Pt(1)
        add_run(p1, value, size=Pt(9), color=COLOR_BODY)

    # 2. 数据来源与信号说明
    add_heading(doc, "2. 数据来源与信号说明", page_break=True)
    body = doc.add_paragraph()
    body.paragraph_format.space_after = Pt(6)
    add_run(body, signal_source)

    # 3..N 图表节
    fig_no = 0
    for i, s in enumerate(sections):
        title_no = 3 + i
        add_heading(doc, "%d. %s" % (title_no, s["title"]), page_break=True)
        if s["available"]:
            fig_no += 1
            img_p = doc.add_paragraph()
            img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            img_p.add_run().add_picture(
                os.path.join(report_dir, s["fileName"]), width=Inches(6.3))
            cap_p = doc.add_paragraph()
            cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap_p.paragraph_format.space_before = Pt(4)
            add_run(cap_p, "图%d  %s" % (fig_no, s["title"]),
                    size=Pt(9), color=COLOR_GRAY)
        else:
            note_p = doc.add_paragraph()
            add_run(note_p, "暂无数据：%s" % s["note"],
                    size=Pt(10.5), color=COLOR_NOTE)

    # 结论
    add_heading(doc, "%d. 结论" % (3 + len(sections)), page_break=True)
    conc = doc.add_paragraph()
    conc.paragraph_format.space_after = Pt(6)
    add_run(conc, conclusion_auto)
    note_p = doc.add_paragraph()
    add_run(note_p, "人工结论：%s" % conclusion_note, size=Pt(10.5), color=COLOR_NOTE)

    docx_path = os.path.join(report_dir, run_number + ".docx")
    try:
        doc.save(docx_path)
    except OSError:
        sys.exit("无法写入 Word 报告（文件可能正被 Word 打开）：%s\n"
                 "请关闭该文件后重新运行。" % docx_path)
    return docx_path


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def build_manifest(run_number, params, signal_source, sections,
                   conclusion_auto, conclusion_note):
    return {
        "report_id": run_number,
        "title": "Co-simulation Test Report",
        "parameters": [{"label": k, "value": v} for k, v in params],
        "signal_source": signal_source,
        "sections": sections,
        "conclusion_auto": conclusion_auto,
        "conclusion_note": conclusion_note,
    }


def main():
    ap = argparse.ArgumentParser(description="生成联合仿真测试报告")
    ap.add_argument("--run", default=None, help="运行编号或目录（默认最近一次）")
    ap.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    ap.add_argument("--user", default=DEFAULT_USER)
    ap.add_argument("--case-dir", default=DEFAULT_CASE_DIR)
    ap.add_argument("--report-root", default=DEFAULT_REPORT_ROOT)
    args = ap.parse_args()

    run_arg = args.run
    if run_arg is None:
        run_arg = os.environ.get("RUN_NO_REPORT")
    if run_arg is None:
        marker = os.path.join(tempfile.gettempdir(), "codex_last_run_no.txt")
        if os.path.isfile(marker):
            with open(marker, "r", encoding="utf-8-sig") as f:
                run_arg = f.read().strip()
    run_dir, run_number = resolve_run(args.data_root, args.user, run_arg)
    if run_dir is None and run_arg:
        run_dir, run_number = find_run_anywhere(args.data_root, run_arg)
    if run_dir is None and not run_arg:
        run_dir, run_number = find_latest_anywhere(args.data_root)
    if run_dir is None:
        sys.exit("无法定位运行数据（数据根目录: %s，运行编号: %s）"
                 % (args.data_root, run_arg or "最近一次"))
    io_csv = os.path.join(run_dir, "%s_trucksim_io.csv" % run_number)
    case_info_csv = os.path.join(run_dir, "%s_case_info.csv" % run_number)
    if not os.path.isfile(io_csv) or not os.path.isfile(case_info_csv):
        sys.exit("运行目录缺少 trucksim_io.csv 或 case_info.csv: %s" % run_dir)

    case = load_case_info(case_info_csv)
    df = load_data(io_csv)
    m = compute_metrics(df)

    report_dir = os.path.join(args.report_root, run_number)
    os.makedirs(report_dir, exist_ok=True)

    _setup_mpl()
    plot_speed(m, os.path.join(report_dir, "01_vehicle_speed.png"),
               target_kmh=_f(case, "target_speed_kmh", float))
    plot_beta(m, os.path.join(report_dir, "02_beta_compare.png"))
    plot_yaw(m, os.path.join(report_dir, "03_yaw_rate_compare.png"))
    plot_trajectory(m, os.path.join(report_dir, "04_trajectory.png"))
    plot_x_position(m, os.path.join(report_dir, "05_x_position.png"))
    plot_y_position(m, os.path.join(report_dir, "06_y_position.png"))
    plot_speed_vs_lateral(m, os.path.join(report_dir, "07_speed_vs_lateral.png"))
    delta_ok = m.get("delta_deg") is not None and m["delta_deg"].size > 0
    if delta_ok:
        plot_steer_delta(m, os.path.join(report_dir, "08_steer_delta.png"))

    copied_case = ""
    case_name = case.get("case_name", "")
    if case_name:
        for fname in os.listdir(args.case_dir):
            if fname.lower().endswith(".txt") and fname.startswith(case_name):
                copied_case = os.path.join(report_dir, fname)
                shutil.copy2(os.path.join(args.case_dir, fname), copied_case)
                break

    init_v = _f(case, "initial_speed_kmh", float)
    stop_time = _f(case, "stop_time_s", float)
    target_v = _f(case, "target_speed_kmh", float)
    params = [
        ("工况名称", case.get("case_name", "")),
        ("工况说明", case.get("description", "")),
        ("控制器模式", case.get("controller_mode", "无（模型验证）")),
        ("设定仿真时长", "%g s" % stop_time),
        ("实际仿真时长", "%.4g s" % m["duration_s"]),
        ("设定初始车速", "%g km/h" % init_v),
        ("车辆速度（初始 / 结束）", "%.6g / %.6g km/h" % (m["v_start_kmh"], m["v_end_kmh"])),
        ("车辆速度（最小 / 最大）", "%.6g / %.6g km/h" % (m["v_min_kmh"], m["v_max_kmh"])),
        ("目标车速（用例设定）", "%g km/h" % target_v),
        ("转向输入类型", case.get("steer_input_type", "")),
        ("转向幅值（第一轴）", "%s deg" % case.get("steer_amplitude_deg", "-")),
        ("转向频率", "%s Hz" % case["steer_frequency_hz"]
         if case.get("steer_frequency_hz") else "不适用（阶跃/其他输入）"),
        ("转向开始时间", "%s s" % case.get("steer_start_time_s", "-")),
        ("第二/第三轴转角", "0 deg（模型内固定）"),
        ("路面附着系数", case.get("road_friction", "-")),
        ("路面坡度", "%s" % case.get("road_grade", "-")),
        ("测试用例文件", os.path.join(args.case_dir, case_name + ".txt")),
        ("原始数据文件", io_csv),
        ("报告内测试用例副本", copied_case or "未找到对应测试用例文件"),
        ("累计行驶距离", "%.4g m（由车速信号梯形积分）" % m["distance_m"]),
        ("最大横向位移", "%.4g m" % m["max_abs_y_m"]),
        ("最大横摆角速度（TruckSim）", "%.4g deg/s" % m["max_yaw_trucksim_degps"]),
        ("最大质心侧偏角（TruckSim）", "%.4g deg" % m["max_abs_beta_trucksim_deg"]),
    ]

    signal_source = (
        "本模型仅保留 TruckSim S-Function 输入/输出接口，不含 3DOF 参考模型。"
        "所有车辆状态信号均由 TruckSim 输出，经模型内 To Workspace 块导出："
        "车速（Vx_trucksim，km/h）、质心侧偏角（beta_trucksim，deg）、"
        "横摆角速度（w_trucksim，deg/s）、车辆位置（x_trucksim / y_trucksim，m）"
        "与挂车位置（xt_trucksim / yt_trucksim，m）。"
        "转向输入 delta_input（deg）由 run_case_new.m 按测试用例生成 "
        "timeseries(steer_input) 后经模型内 From Workspace（Steering Input）输入，"
        "仅作用于第一轴，第二、第三轴转角固定为 0。"
        "仿真前由入口脚本按 TXT 配置 TruckSim；配置、时长、初始速度和实际转向"
        "均在 CSV 导出前验证。"
    )

    sections = [
        {"title": "车辆实际速度随时间变化", "available": True,
         "fileName": "01_vehicle_speed.png", "note": ""},
        {"title": "质心侧偏角随时间变化（TruckSim）", "available": True,
         "fileName": "02_beta_compare.png", "note": ""},
        {"title": "横摆角速度随时间变化（TruckSim）", "available": True,
         "fileName": "03_yaw_rate_compare.png", "note": ""},
        {"title": "车辆行驶轨迹（X-Y 平面）", "available": True,
         "fileName": "04_trajectory.png", "note": ""},
        {"title": "车辆纵向位置随时间变化", "available": True,
         "fileName": "05_x_position.png", "note": ""},
        {"title": "车辆横向位置随时间变化", "available": True,
         "fileName": "06_y_position.png", "note": ""},
        {"title": "车速随横向位移变化", "available": True,
         "fileName": "07_speed_vs_lateral.png", "note": ""},
        {"title": "转向输入信号（delta，第一轴）", "available": delta_ok,
         "fileName": "08_steer_delta.png" if delta_ok else "",
         "note": "" if delta_ok else
                 "数据文件（trucksim_io.csv）中暂无转向输入信号列。"
                 "请确认模型含 To Workspace(delta_input) 并重新运行。"},
    ]

    conclusion_auto = (
        "本次联合仿真已完成。实际仿真时长为 %.4g s（设定 %g s）；车辆初始/结束速度为 "
        "%.6g / %.6g km/h；车辆最小/最大速度为 %.6g / %.6g km/h；车辆累计行驶距离 "
        "%.4g m；最大横向位移 %.4g m；TruckSim 最大横摆角速度 %.4g deg/s，"
        "最大质心侧偏角 %.4g deg。"
        % (m["duration_s"], stop_time, m["v_start_kmh"], m["v_end_kmh"],
           m["v_min_kmh"], m["v_max_kmh"], m["distance_m"], m["max_abs_y_m"],
           m["max_yaw_trucksim_degps"], m["max_abs_beta_trucksim_deg"])
    )

    speed_mismatch = abs(m["v_start_kmh"] - init_v) > 0.5
    if case.get("conclusion_note"):
        conclusion_note = case["conclusion_note"]
    elif speed_mismatch:
        conclusion_note = (
            "异常：TruckSim 实际起始车速 %.6g km/h 与用例设定 %g km/h 不一致。"
            "此结果不应由当前严格入口产生，请检查历史数据或配置过程。"
            % (m["v_start_kmh"], init_v)
        )
    else:
        conclusion_note = (
            "本工况为模型验证用例（%s），TruckSim 响应符合预期，"
            "可作为后续控制器联合仿真的基线。"
            % case.get("source_case_id", "")
        )

    manifest = build_manifest(run_number, params, signal_source, sections,
                              conclusion_auto, conclusion_note)
    with open(os.path.join(report_dir, "report_manifest.json"), "w",
              encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    docx_path = build_docx(report_dir, run_number, params, signal_source, sections,
                           conclusion_auto, conclusion_note)

    print("测试报告生成完成")
    print("  报告目录: %s" % report_dir)
    print("  Word 报告: %s" % docx_path)
    print("  清单文件: %s" % os.path.join(report_dir, "report_manifest.json"))
    print("  曲线图数量: %d" % sum(1 for s in sections if s["available"]))
    print("REPORT_OK", flush=True)


def _f(d, key, cast, default=None):
    v = d.get(key)
    if v is None or v == "":
        return default
    try:
        return cast(v)
    except (TypeError, ValueError):
        return default


if __name__ == "__main__":
    main()
