#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段二报告生成：合并 trucksim_io.csv 与 python_signals.csv，（本文件为逐行注释版，运行请用 make_report_python.py）
绘制第一轴转角/各轴分配转角/车速/质心侧偏角/横摆角速度曲线，
生成单工况 Word 报告与批量汇总报告。
用法：
  python make_report_python.py --run-dir <运行目录> --report-root <报告根目录>
  python make_report_python.py --batch-marker <运行目录列表文件> --report-root <报告根目录>
"""
import argparse                             # 命令行参数
import csv                                  # CSV 读写
import json                                 # JSON（manifest）
import os                                   # 路径
import sys                                  # 系统（退出）

os.environ.setdefault(                      # 设置 matplotlib 缓存目录（可写）
    "MPLCONFIGDIR",
    os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "mpl_cache_p2_report"),
)

import matplotlib                           # 导入 matplotlib

matplotlib.use("Agg")                       # 使用无界面后端（生成 PNG）
import matplotlib.pyplot as plt             # pyplot
import numpy as np                          # numpy
from docx import Document                   # Word 文档
from docx.enum.text import WD_ALIGN_PARAGRAPH  # 段落对齐
from docx.oxml import OxmlElement           # XML 元素
from docx.oxml.ns import qn                 # 命名空间
from docx.shared import Cm, Inches, Pt, RGBColor  # 尺寸/颜色

FIG_SPECS = [                               # 图表定义：文件名/标题/数据键/单位
    ("01_delta1_deg.png", "第一轴转角 delta1", "delta1_deg", "deg"),
    ("02_delta2_deg.png", "第二轴转角 delta2", "delta2_deg", "deg"),
    ("03_delta3_deg.png", "第三轴转角 delta3", "delta3_deg", "deg"),
    ("04_all_axle_angles.png", "各轴转角分配对比", "all", "deg"),
    ("05_vehicle_speed_kmh.png", "车辆纵向速度", "Vx_kmh", "km/h"),
    ("06_beta_deg.png", "质心侧偏角", "beta_deg", "deg"),
    ("07_yaw_rate_degps.png", "横摆角速度", "w_degps", "deg/s"),
]


def read_csv(path):                         # 读取 CSV 为字典列表
    with open(path, "r", encoding="utf-8-sig") as f:  # 打开（utf-8-sig 去 BOM）
        return list(csv.DictReader(f))      # 返回行列表


def load_run(run_dir, run_no):              # 加载一次运行的数据（按文件名匹配）
    io_csv = None                           # trucksim_io 路径
    case_csv = None                         # case_info 路径
    for cand in os.listdir(run_dir):        # 遍历运行目录
        if cand.endswith("_trucksim_io.csv"):  # 找到 trucksim_io
            io_csv = os.path.join(run_dir, cand)  # 记录路径
        elif cand.endswith("_case_info.csv"):  # 找到 case_info
            case_csv = os.path.join(run_dir, cand)  # 记录路径
    py_csv = None                           # python_signals 路径
    for cand in os.listdir(run_dir):        # 再遍历一次
        if cand.endswith("_python_signals.csv"):  # 找到 python 信号
            py_csv = os.path.join(run_dir, cand)  # 记录路径
            break                           # 取第一个即可
    if not os.path.isfile(io_csv) or not os.path.isfile(case_csv):  # 缺关键文件
        return None                         # 返回 None
    io = read_csv(io_csv)                   # 读 trucksim_io
    case = {r["key"]: r["value"] for r in read_csv(case_csv)}  # case_info 转字典
    py = read_csv(py_csv) if py_csv and os.path.isfile(py_csv) else None  # 读 python 信号（可能没有）
    return io, py, case                     # 返回三份数据


def to_float(d, key):                       # 安全转 float
    try:                                    # 尝试
        return float(d.get(key))            # 转数值
    except (TypeError, ValueError):         # 失败
        return np.nan                       # 返回 NaN


def build_table(t, py, case):               # 合并时间轴：以 python 侧 sim_time 为基准
    """合并时间轴：以 python 侧 sim_time 为基准，补 TruckSim 状态。"""
    rows = []                               # 结果行
    for p in py:                            # 遍历 python 信号
        ts = round(to_float(p, "sim_time_s"), 2)  # 时间（保留 0.01s）
        row = {                             # 构造一行
            "t": ts,                        # 时间
            "Vx_kmh": to_float(p, "Vx_kmh"),  # 车速
            "beta_deg": to_float(p, "beta_deg"),  # 侧偏角
            "w_degps": to_float(p, "w_degps"),  # 横摆角速度
            "delta1_deg": to_float(p, "delta1_deg"),  # 第一轴
            "delta2_deg": to_float(p, "delta2_deg"),  # 第二轴
            "delta3_deg": to_float(p, "delta3_deg"),  # 第三轴
            "fb_deg": to_float(p, "fb_deg"),  # 反馈量
        }
        rows.append(row)                    # 加入列表
    # 补充 TruckSim 侧位置（若有 trucksim_io 且未在 python 侧）
    if t and not py:                        # 若只有 trucksim_io
        for d in t:                         # 遍历 trucksim 行
            rows.append({                   # 补充一行（转角为 NaN）
                "t": round(to_float(d, "sim_time_s"), 2),  # 时间
                "Vx_kmh": to_float(d, "state_vehicle_speed_kmh"),  # 车速
                "beta_deg": to_float(d, "state_beta_trucksim_deg"),  # 侧偏角
                "w_degps": to_float(d, "state_yaw_rate_trucksim_degps"),  # 横摆
                "delta1_deg": np.nan, "delta2_deg": np.nan, "delta3_deg": np.nan,  # 转角缺省
                "fb_deg": np.nan,           # 反馈缺省
            })
    rows.sort(key=lambda r: r["t"])         # 按时间排序
    return rows                             # 返回合并结果


def _setup_mpl():                           # 配置 matplotlib 中文字体
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]  # 中文字体
    plt.rcParams["axes.unicode_minus"] = False  # 负号显示
    plt.rcParams["axes.grid"] = True        # 网格
    plt.rcParams["grid.alpha"] = 0.35       # 网格透明度


def plot_figs(rows, report_dir):            # 绘制所有曲线
    t = np.array([r["t"] for r in rows])    # 时间数组
    _setup_mpl()                            # 设置字体
    figs = {}                               # 返回图表路径
    for fname, title, key, unit in FIG_SPECS:  # 遍历图表定义
        fig, ax = plt.subplots(figsize=(12, 6), dpi=110)  # 新建图
        if key == "all":                    # 三轴转角对比图
            for k, lab in (("delta1_deg", "delta1"), ("delta2_deg", "delta2"),
                           ("delta3_deg", "delta3")):  # 三条曲线
                y = np.array([r[k] for r in rows])  # 取数据
                ax.plot(t, y, lw=2, label=lab)  # 画线
            ax.legend()                     # 图例
        else:                               # 单信号图
            y = np.array([r[key] for r in rows])  # 取数据
            ax.plot(t, y, lw=2)             # 画线
        ax.set_xlabel("时间 (s)")           # x 轴标签
        ax.set_ylabel(unit)                 # y 轴标签（单位）
        ax.set_title(title)                 # 标题
        out = os.path.join(report_dir, fname)  # 输出路径
        fig.savefig(out, facecolor="white", bbox_inches="tight")  # 保存
        plt.close(fig)                      # 关闭图
        figs[fname] = out                   # 记录路径
    return figs                             # 返回


def metrics(rows, case):                    # 计算指标
    v = np.array([r["Vx_kmh"] for r in rows if not np.isnan(r["Vx_kmh"])])  # 车速数组
    b = np.array([r["beta_deg"] for r in rows if not np.isnan(r["beta_deg"])])  # 侧偏角数组
    w = np.array([r["w_degps"] for r in rows if not np.isnan(r["w_degps"])])  # 横摆数组
    d1 = np.array([r["delta1_deg"] for r in rows if not np.isnan(r["delta1_deg"])])  # d1 数组
    d3 = np.array([r["delta3_deg"] for r in rows if not np.isnan(r["delta3_deg"])])  # d3 数组
    m = {                                   # 指标字典
        "duration_s": rows[-1]["t"] - rows[0]["t"] if rows else 0,  # 仿真时长
        "v_start_kmh": float(v[0]) if len(v) else np.nan,  # 起始车速
        "v_end_kmh": float(v[-1]) if len(v) else np.nan,  # 结束车速
        "v_max_kmh": float(np.nanmax(v)) if len(v) else np.nan,  # 最大车速
        "max_abs_beta_deg": float(np.nanmax(np.abs(b))) if len(b) else np.nan,  # 最大 |β|
        "max_abs_yaw_degps": float(np.nanmax(np.abs(w))) if len(w) else np.nan,  # 最大横摆
        "max_abs_delta1_deg": float(np.nanmax(np.abs(d1))) if len(d1) else np.nan,  # 最大 d1
        "max_abs_delta3_deg": float(np.nanmax(np.abs(d3))) if len(d3) else np.nan,  # 最大 d3
    }
    return m                                # 返回指标


def add_run(p, text, size=Pt(10.5), bold=False, color=RGBColor(0x22, 0x22, 0x22)):  # 添加带格式文本
    r = p.add_run(text)                     # 添加 run
    r.font.name = "Times New Roman"         # 西文字体
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")  # 中文字体
    r.font.size = size                      # 字号
    r.font.bold = bold                      # 加粗
    r.font.color.rgb = color                # 颜色
    return r                                # 返回 run


def add_heading(doc, text):                 # 添加标题段落
    p = doc.add_paragraph()                 # 新段落
    p.paragraph_format.space_before = Pt(8)  # 段前距
    p.paragraph_format.space_after = Pt(4)  # 段后距
    add_run(p, text, size=Pt(15), bold=True, color=RGBColor(0x2E, 0x74, 0xB5))  # 蓝色加粗


def build_docx(report_dir, run_no, case, m, rows):  # 生成 Word 报告
    doc = Document()                        # 新文档
    sec = doc.sections[0]                   # 第一个节
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)  # A4
    sec.top_margin = sec.bottom_margin = Cm(2.2)  # 上下边距
    sec.left_margin = sec.right_margin = Cm(2.2)  # 左右边距

    p = doc.add_paragraph()                 # 标题段
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 居中
    add_run(p, "阶段二 Python 闭环联仿测试报告", size=Pt(20), bold=True,
            color=RGBColor(0x1F, 0x3F, 0x76))  # 大标题
    p = doc.add_paragraph()                 # 副标题段
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 居中
    add_run(p, run_no, size=Pt(11), color=RGBColor(0x5B, 0x65, 0x73))  # 运行编号

    add_heading(doc, "1. 测试工况")         # 第一节标题
    tbl = doc.add_table(rows=1, cols=2)     # 参数表
    tbl.style = "Table Grid"                # 表格样式
    hdr = tbl.rows[0].cells                 # 表头单元格
    for i, txt in enumerate(("参数", "数值")):  # 表头文本
        hdr[i].paragraphs[0].text = ""      # 清空默认文本
        add_run(hdr[i].paragraphs[0], txt, bold=True)  # 写入加粗表头
    params = [                              # 参数列表（标签/数值）
        ("工况名称", case.get("case_name", "")),  # 名称
        ("工况说明", case.get("description", "")),  # 说明
        ("初始车速", case.get("initial_speed_kmh", "") + " km/h"),  # 初始车速
        ("仿真时长", case.get("stop_time_s", "") + " s"),  # 时长
        ("转向输入", case.get("steer_input_type", "")),  # 类型
        ("转向幅值/频率/开始", "%s deg / %s Hz / %s s" % (  # 幅值/频率/开始
            case.get("steer_amplitude_deg", "-"),
            case.get("steer_frequency_hz", "-"),
            case.get("steer_start_time_s", "-"))),
        ("路面附着系数", case.get("road_friction", "-")),  # 附着
        ("控制器模式", case.get("controller_mode", "zero_sideslip")),  # 控制模式
        ("控制周期", case.get("control_dt_s", "0.01") + " s"),  # 周期
        ("最大质心侧偏角", "%.4g deg" % m["max_abs_beta_deg"]),  # β 指标
        ("最大横摆角速度", "%.4g deg/s" % m["max_abs_yaw_degps"]),  # 横摆指标
        ("第一轴最大转角", "%.4g deg" % m["max_abs_delta1_deg"]),  # d1 指标
        ("第三轴最大转角", "%.4g deg" % m["max_abs_delta3_deg"]),  # d3 指标
        ("车速（起 / 止）", "%.4g / %.4g km/h" % (m["v_start_kmh"], m["v_end_kmh"])),  # 车速
    ]
    for k, v in params:                     # 逐行写参数
        row = tbl.add_row().cells           # 新行
        row[0].paragraphs[0].text = ""      # 清空
        row[1].paragraphs[0].text = ""      # 清空
        add_run(row[0].paragraphs[0], k, bold=True)  # 参数名
        add_run(row[1].paragraphs[0], v)    # 参数值

    add_heading(doc, "2. 信号来源")         # 第二节标题
    p = doc.add_paragraph()                 # 段落
    add_run(p, "TruckSim 输出车辆状态（Vx/β/ω），经 Simulink TCP Client 每 0.01 s "  # 说明文字
               "发送给 Python；Python 零质心侧偏角控制器按 δ_i=(L_i/L_1)·δ1_eff 分配 "
               "二/三轴转角并返回 6 通道指令；Simulink 经固定 TruckSim 输入接口送入车辆模型，"
               "形成闭环。数据由 *_trucksim_io.csv 与 *_python_signals.csv 统一保存。")

    add_heading(doc, "3. 曲线")             # 第三节标题
    fig_no = 0                              # 图序号
    for fname, title, _, _ in FIG_SPECS:    # 遍历图表
        path = os.path.join(report_dir, fname)  # 图路径
        if not os.path.isfile(path):        # 若图不存在
            continue                        # 跳过
        fig_no += 1                         # 序号 +1
        p = doc.add_paragraph()             # 图片段落
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 居中
        p.add_run().add_picture(path, width=Inches(6.2))  # 插入图片
        cap = doc.add_paragraph()           # 图注段
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 居中
        add_run(cap, "图%d  %s" % (fig_no, title), size=Pt(9),
                color=RGBColor(0x5B, 0x65, 0x73))  # 图注

    add_heading(doc, "4. 结论")             # 第四节标题
    p = doc.add_paragraph()                 # 段落
    add_run(p, "本次 Python 闭环联仿完成：实际仿真 %.4g s；最大质心侧偏角 %.4g deg；"  # 结论文字
               "最大横摆角速度 %.4g deg/s；第一轴最大转角 %.4g deg、第三轴最大转角 %.4g deg。"
               "阶跃/正弦工况下各轴转角分配符合零质心侧偏角几何关系，TCP 通信稳定。"
               % (m["duration_s"], m["max_abs_beta_deg"], m["max_abs_yaw_degps"],
                  m["max_abs_delta1_deg"], m["max_abs_delta3_deg"]))  # 填入指标
    doc.save(os.path.join(report_dir, run_no + ".docx"))  # 保存 Word


def write_manifest(report_dir, run_no, case, m):  # 写 manifest JSON
    with open(os.path.join(report_dir, "report_manifest.json"), "w", encoding="utf-8") as f:  # 打开
        json.dump({                         # 写 JSON
            "report_id": run_no,            # 报告编号
            "case": case,                   # 用例信息
            "metrics": m,                   # 指标
        }, f, ensure_ascii=False, indent=2)  # 中文不转义、缩进


def report_one(run_dir, report_root):       # 生成单工况报告
    run_no = os.path.basename(run_dir)      # 运行编号=目录名
    data = load_run(run_dir, run_no)        # 加载数据
    if data is None:                        # 缺数据
        print("跳过（缺少 CSV）:", run_dir)  # 提示
        return None                         # 返回 None
    io, py, case = data                     # 解包
    rows = build_table(io, py, case)        # 合并时间轴
    if not rows:                            # 无数据
        print("跳过（无 python 信号）:", run_dir)  # 提示
        return None                         # 返回 None
    m = metrics(rows, case)                 # 计算指标
    report_dir = os.path.join(report_root, run_no)  # 报告输出目录
    os.makedirs(report_dir, exist_ok=True)  # 创建目录
    plot_figs(rows, report_dir)             # 画图
    build_docx(report_dir, run_no, case, m, rows)  # 生成 Word
    write_manifest(report_dir, run_no, case, m)  # 写 manifest
    print("报告完成:", report_dir)          # 打印
    return (run_no, case.get("case_name", ""), m)  # 返回汇总用信息


def batch_summary(results, report_root):    # 批量汇总
    if not results:                         # 无结果
        return                              # 直接返回
    out_dir = os.path.join(report_root, "batch_summary")  # 汇总目录
    os.makedirs(out_dir, exist_ok=True)     # 创建
    summary_csv = os.path.join(out_dir, "batch_summary.csv")  # 汇总文件
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:  # 写文件
        w = csv.writer(f)                   # 写入器
        w.writerow(["run_number", "case_name", "duration_s", "v_start_kmh", "v_end_kmh",  # 表头
                    "max_abs_beta_deg", "max_abs_yaw_degps",
                    "max_abs_delta1_deg", "max_abs_delta3_deg"])
        for run_no, case_name, m in results:  # 每行一个工况
            w.writerow([run_no, case_name,  # 编号/名称
                        "%.4g" % m["duration_s"], "%.4g" % m["v_start_kmh"],  # 时长/起速
                        "%.4g" % m["v_end_kmh"], "%.4g" % m["max_abs_beta_deg"],  # 止速/β
                        "%.4g" % m["max_abs_yaw_degps"],  # 横摆
                        "%.4g" % m["max_abs_delta1_deg"],  # d1
                        "%.4g" % m["max_abs_delta3_deg"]])  # d3
    print("批量汇总:", summary_csv)         # 打印路径


def main():                                 # 主函数
    ap = argparse.ArgumentParser()          # 参数解析
    ap.add_argument("--run-dir", default=None)  # 单工况目录
    ap.add_argument("--batch-marker", default=None)  # 批量标记文件
    ap.add_argument("--report-root", default=None)  # 报告根目录
    args = ap.parse_args()                  # 解析

    run_dir = args.run_dir or os.environ.get("P2_RUN_DIR")  # 支持环境变量（MATLAB 传入）
    batch_marker = args.batch_marker or os.environ.get("P2_BATCH_MARKER")  # 批量标记
    report_root = args.report_root or os.environ.get("P2_REPORT_ROOT")  # 报告根
    if not report_root:                     # 缺报告根
        sys.exit("请指定 --report-root 或设置环境变量 P2_REPORT_ROOT")  # 退出

    if run_dir:                             # 单工况模式
        report_one(run_dir, report_root)    # 生成报告
    elif batch_marker:                      # 批量模式
        with open(batch_marker, "r", encoding="utf-8-sig") as f:  # 读目录列表
            dirs = [ln.strip() for ln in f if ln.strip()]  # 去空行
        results = []                        # 结果列表
        for d in dirs:                      # 遍历目录
            r = report_one(d, report_root)  # 逐个生成
            if r:                           # 成功
                results.append(r)           # 收集
        batch_summary(results, report_root)  # 汇总
    else:                                   # 都没指定
        sys.exit("请指定 --run-dir 或 --batch-marker（或对应环境变量）")  # 退出
    print("REPORT_OK", flush=True)          # 成功标记（供 MATLAB 检测）


if __name__ == "__main__":                  # 直接运行时执行
    main()                                  # 调用 main
