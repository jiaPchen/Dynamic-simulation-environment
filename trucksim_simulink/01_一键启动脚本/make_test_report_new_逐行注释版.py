#!/usr/bin/env python3  # 注释：原脚本注释或文件头说明。
# -*- coding: utf-8 -*-  # 注释：原脚本注释或文件头说明。
"""  # 注释：Python 多行说明字符串的开始或结束。
make_test_report_new.py - 新版测试报告一键生成脚本（适配 TruckSim-only 模型）  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
读取 run_case_new.m 导出的 trucksim_io.csv / case_info.csv，绘制时间历程曲线，  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
并按模板生成 Word 测试报告，输出到 04_测试报告\\<运行编号>\\。  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
注意：新模型不再包含 3DOF 参考模型，所有车辆状态信号均来自 TruckSim  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
S-Function 的 To Workspace 输出。  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
用法：  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    python make_test_report_new.py [--run 运行编号或目录] [--data-root 数据根目录]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                                   [--user 用户文件夹] [--case-dir 测试用例目录]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                                   [--report-root 报告根目录]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
不带 --run 时自动选择最近一次运行（第 NNN 次编号最大）。  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
依赖：matplotlib、numpy、python-docx。  # 注释：执行 Python 语句，完成当前脚本流程的一小步。 Python 依赖相关代码；换电脑后需要安装对应库。
"""  # 注释：Python 多行说明字符串的开始或结束。
# 注释：空行，用来分隔代码段。
import argparse  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。
import csv  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。
import json  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。
import os  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。
import re  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。
import shutil  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。
import sys  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。
import tempfile  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。
# 注释：空行，用来分隔代码段。
os.environ.setdefault(  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    "MPLCONFIGDIR",  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "mpl_cache_test_report"),  # 注释：文件路径、目录创建或文件复制操作。
)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
import matplotlib  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。 Python 依赖相关代码；换电脑后需要安装对应库。
# 注释：空行，用来分隔代码段。
matplotlib.use("Agg")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。 Python 依赖相关代码；换电脑后需要安装对应库。
import matplotlib.pyplot as plt  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。 Python 依赖相关代码；换电脑后需要安装对应库。
import numpy as np  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。 Python 依赖相关代码；换电脑后需要安装对应库。
from docx import Document  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。 Python 依赖相关代码；换电脑后需要安装对应库。
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。 Python 依赖相关代码；换电脑后需要安装对应库。
from docx.oxml import OxmlElement  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。 Python 依赖相关代码；换电脑后需要安装对应库。
from docx.oxml.ns import qn  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。 Python 依赖相关代码；换电脑后需要安装对应库。
from docx.shared import Cm, Inches, Pt, RGBColor, Twips  # 注释：导入 Python 标准库或第三方库；缺库时需要在本机 pip install。 Python 依赖相关代码；换电脑后需要安装对应库。
# 注释：空行，用来分隔代码段。
ROOT = r"D:\动力学仿真环境"  # 注释：给变量赋值、创建对象或计算中间结果。 报告脚本默认项目根目录；换电脑后若使用旧流程，需要改成本机项目路径。 换机重点：这里写死了 Windows 绝对路径，要确认这台电脑是否存在同一路径。
DEFAULT_DATA_ROOT = os.path.join(ROOT, "03_数据存储")  # 注释：文件路径、目录创建或文件复制操作。 报告脚本默认项目根目录；换电脑后若使用旧流程，需要改成本机项目路径。 报告脚本默认数据目录，应和 MATLAB 导出的 dataRoot 对应。
DEFAULT_USER = "阶跃输入转角"  # 注释：给变量赋值、创建对象或计算中间结果。
DEFAULT_CASE_DIR = os.path.join(ROOT, "02_测试用例")  # 注释：文件路径、目录创建或文件复制操作。 报告脚本默认项目根目录；换电脑后若使用旧流程，需要改成本机项目路径。
DEFAULT_REPORT_ROOT = os.path.join(ROOT, "04_测试报告")  # 注释：文件路径、目录创建或文件复制操作。 报告脚本默认项目根目录；换电脑后若使用旧流程，需要改成本机项目路径。 报告脚本默认报告目录，生成图片和 Word 会写到这里。
# 注释：空行，用来分隔代码段。
FONT_LATIN = "Calibri"  # 注释：给变量赋值、创建对象或计算中间结果。
FONT_EAST = "宋体"  # 注释：给变量赋值、创建对象或计算中间结果。
FONT_HEADING_EAST = "微软雅黑"  # 注释：给变量赋值、创建对象或计算中间结果。
COLOR_HEADING = RGBColor(0x2E, 0x74, 0xB5)  # 注释：给变量赋值、创建对象或计算中间结果。
COLOR_TITLE = RGBColor(0x0B, 0x25, 0x45)  # 注释：给变量赋值、创建对象或计算中间结果。
COLOR_GRAY = RGBColor(0x5B, 0x65, 0x73)  # 注释：给变量赋值、创建对象或计算中间结果。
COLOR_BODY = RGBColor(0x22, 0x22, 0x22)  # 注释：给变量赋值、创建对象或计算中间结果。
COLOR_NOTE = RGBColor(0x7A, 0x5A, 0x00)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
FILENAME_RE = re.compile(r".*_第(\d+)次")  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
# ----------------------------------------------------------------------------  # 注释：原脚本注释或文件头说明。
# 数据读取与指标计算  # 注释：原脚本注释或文件头说明。
# ----------------------------------------------------------------------------  # 注释：原脚本注释或文件头说明。
def find_latest_run(data_root, user_name):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    user_dir = os.path.join(data_root, user_name)  # 注释：文件路径、目录创建或文件复制操作。
    if not os.path.isdir(user_dir):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        return None, None  # 注释：返回函数计算结果给调用方。
    runs = []  # 注释：给变量赋值、创建对象或计算中间结果。
    for name in os.listdir(user_dir):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        m = FILENAME_RE.search(name)  # 注释：给变量赋值、创建对象或计算中间结果。
        if m and os.path.isdir(os.path.join(user_dir, name)):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
            runs.append((int(m.group(1)), name))  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    if not runs:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        return None, None  # 注释：返回函数计算结果给调用方。
    runs.sort()  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    return os.path.join(user_dir, runs[-1][1]), runs[-1][1]  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def iter_user_dirs(data_root):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    if not os.path.isdir(data_root):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        return  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    for user in sorted(os.listdir(data_root)):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        user_dir = os.path.join(data_root, user)  # 注释：文件路径、目录创建或文件复制操作。
        if os.path.isdir(user_dir):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
            yield user, user_dir  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def find_run_anywhere(data_root, run_arg):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    """在所有用户文件夹下按运行编号/目录名查找运行。"""  # 注释：Python 多行说明字符串的开始或结束。
    for _, user_dir in iter_user_dirs(data_root):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        cand = os.path.join(user_dir, run_arg)  # 注释：文件路径、目录创建或文件复制操作。
        if os.path.isdir(cand):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
            return cand, run_arg  # 注释：返回函数计算结果给调用方。
    if run_arg.isdigit():  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        for _, user_dir in iter_user_dirs(data_root):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
            matches = [n for n in os.listdir(user_dir)  # 注释：给变量赋值、创建对象或计算中间结果。
                       if FILENAME_RE.search(n) and  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                       FILENAME_RE.search(n).group(1) == run_arg.lstrip("0")]  # 注释：给变量赋值、创建对象或计算中间结果。
            if len(matches) == 1:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                return os.path.join(user_dir, matches[0]), matches[0]  # 注释：返回函数计算结果给调用方。
    return None, None  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def find_latest_anywhere(data_root):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    """在所有用户文件夹下取最近一次运行。"""  # 注释：Python 多行说明字符串的开始或结束。
    best = None  # 注释：给变量赋值、创建对象或计算中间结果。
    for _, user_dir in iter_user_dirs(data_root):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        for name in os.listdir(user_dir):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
            m = FILENAME_RE.search(name)  # 注释：给变量赋值、创建对象或计算中间结果。
            if m and os.path.isdir(os.path.join(user_dir, name)):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                key = (m.group(1), name)  # 注释：给变量赋值、创建对象或计算中间结果。
                if best is None or key[0] > best[0]:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                    best = (key[0], os.path.join(user_dir, name), name)  # 注释：文件路径、目录创建或文件复制操作。
    if best is None:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        return None, None  # 注释：返回函数计算结果给调用方。
    return best[1], best[2]  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def resolve_run(data_root, user_name, run_arg):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    if not run_arg:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        return find_latest_run(data_root, user_name)  # 注释：返回函数计算结果给调用方。
    if os.path.isdir(run_arg):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        run_dir = run_arg  # 注释：给变量赋值、创建对象或计算中间结果。
        run_number = os.path.basename(run_dir)  # 注释：文件路径、目录创建或文件复制操作。
        return run_dir, run_number  # 注释：返回函数计算结果给调用方。
    user_dir = os.path.join(data_root, user_name)  # 注释：文件路径、目录创建或文件复制操作。
    if os.path.isdir(os.path.join(user_dir, run_arg)):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        return os.path.join(user_dir, run_arg), run_arg  # 注释：返回函数计算结果给调用方。
    if os.path.isdir(user_dir):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        cand = [n for n in os.listdir(user_dir)  # 注释：给变量赋值、创建对象或计算中间结果。
                if FILENAME_RE.search(n) and FILENAME_RE.search(n).group(1) == run_arg.lstrip("0")]  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        if len(cand) == 1:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
            return os.path.join(user_dir, cand[0]), cand[0]  # 注释：返回函数计算结果给调用方。
    return None, None  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def load_case_info(case_info_csv):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    info = {}  # 注释：给变量赋值、创建对象或计算中间结果。
    with open(case_info_csv, "r", encoding="utf-8-sig") as f:  # 注释：上下文管理语句，通常用于安全打开和关闭文件。
        for row in csv.reader(f):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
            if len(row) >= 2:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                info[row[0].strip()] = row[1].strip()  # 注释：给变量赋值、创建对象或计算中间结果。
    return info  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def load_data(io_csv):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    with open(io_csv, "r", encoding="utf-8-sig") as f:  # 注释：上下文管理语句，通常用于安全打开和关闭文件。
        reader = csv.reader(f)  # 注释：给变量赋值、创建对象或计算中间结果。
        header = next(reader)  # 注释：给变量赋值、创建对象或计算中间结果。
        cols = {name: [] for name in header}  # 注释：给变量赋值、创建对象或计算中间结果。
        numeric = set()  # 注释：给变量赋值、创建对象或计算中间结果。
        seen = False  # 注释：给变量赋值、创建对象或计算中间结果。
        for row in reader:  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
            if not row:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                continue  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
            if not seen:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                for i, name in enumerate(header):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
                    if i < len(row) and row[i] != "":  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                        try:  # 注释：异常保护开始，下面代码失败时会进入 except。
                            float(row[i])  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                            numeric.add(name)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                        except ValueError:  # 注释：异常处理分支，用于记录错误或采用备用逻辑。
                            pass  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                seen = True  # 注释：给变量赋值、创建对象或计算中间结果。
            for i, name in enumerate(header):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
                if name in numeric and i < len(row) and row[i] != "":  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                    cols[name].append(float(row[i]))  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    if "sim_time_s" not in cols:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        sys.exit("数据文件缺少必需列: sim_time_s")  # 注释：发生不可继续的问题时主动报错或退出。
    return {name: np.asarray(values, dtype=float) for name, values in cols.items()  # 注释：返回函数计算结果给调用方。
            if name in numeric}  # 注释：条件判断开始，根据当前变量状态选择执行路径。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def compute_metrics(df):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    t = df["sim_time_s"]  # 注释：给变量赋值、创建对象或计算中间结果。
    v = df["state_vehicle_speed_kmh"]  # 注释：给变量赋值、创建对象或计算中间结果。
    x = df["state_x_m"]  # 注释：给变量赋值、创建对象或计算中间结果。
    y = df["state_y_m"]  # 注释：给变量赋值、创建对象或计算中间结果。
    beta_ts = (  # 注释：给变量赋值、创建对象或计算中间结果。
        df["state_beta_trucksim_deg"]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        if "state_beta_trucksim_deg" in df  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        else np.zeros_like(t)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    )  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    w_ts = (  # 注释：给变量赋值、创建对象或计算中间结果。
        df["state_yaw_rate_trucksim_degps"]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        if "state_yaw_rate_trucksim_degps" in df  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        else np.zeros_like(t)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    )  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    delta = (  # 注释：给变量赋值、创建对象或计算中间结果。
        df["state_steer_delta_deg"]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        if "state_steer_delta_deg" in df  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        else None  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    )  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    try:  # 注释：异常保护开始，下面代码失败时会进入 except。
        trapz = np.trapezoid  # 注释：给变量赋值、创建对象或计算中间结果。
    except AttributeError:  # numpy < 2.0  # 注释：异常处理分支，用于记录错误或采用备用逻辑。
        trapz = np.trapz  # 注释：给变量赋值、创建对象或计算中间结果。
    distance = float(trapz(v / 3.6, t))  # 注释：给变量赋值、创建对象或计算中间结果。
    metrics = {  # 注释：给变量赋值、创建对象或计算中间结果。
        "t": t,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "v_kmh": v,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "x_m": x,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "y_m": y,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "beta_trucksim_deg": beta_ts,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "yaw_trucksim_degps": w_ts,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "duration_s": float(t[-1] - t[0]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "v_start_kmh": float(v[0]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "v_end_kmh": float(v[-1]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "v_min_kmh": float(v.min()),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "v_max_kmh": float(v.max()),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "distance_m": distance,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "max_abs_y_m": float(np.max(np.abs(y))),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "max_yaw_trucksim_degps": float(np.max(np.abs(w_ts))),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "max_abs_beta_trucksim_deg": float(np.max(np.abs(beta_ts))),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "delta_deg": delta,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    }  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    return metrics  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
# ----------------------------------------------------------------------------  # 注释：原脚本注释或文件头说明。
# 绘图  # 注释：原脚本注释或文件头说明。
# ----------------------------------------------------------------------------  # 注释：原脚本注释或文件头说明。
def _setup_mpl():  # 注释：定义 Python 函数，封装一段可复用逻辑。
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    plt.rcParams["axes.unicode_minus"] = False  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    plt.rcParams["font.size"] = 18  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    plt.rcParams["axes.labelsize"] = 19  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    plt.rcParams["axes.titlesize"] = 22  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    plt.rcParams["legend.fontsize"] = 17  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    plt.rcParams["legend.framealpha"] = 0.9  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    plt.rcParams["axes.grid"] = True  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    plt.rcParams["grid.alpha"] = 0.35  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def _new_fig():  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = plt.subplots(figsize=(20, 11.67), dpi=100)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.subplots_adjust(left=0.07, right=0.975, top=0.94, bottom=0.085)  # 注释：给变量赋值、创建对象或计算中间结果。
    return fig, ax  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def plot_speed(m, out, target_kmh=None):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = _new_fig()  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.plot(m["t"], m["v_kmh"], lw=2.2, label="车辆实际速度（TruckSim）")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    if target_kmh is not None:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        ax.axhline(target_kmh, color="C3", ls="--", lw=2.0,  # 注释：绘图相关代码，用于生成报告中的曲线图片。
                   label="目标车速（用例设定 %g km/h）" % target_kmh)  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.set_xlabel("时间 (s)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_ylabel("车速 (km/h)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_title("车辆实际速度随时间变化")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.legend()  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.savefig(out, facecolor="white")  # 注释：给变量赋值、创建对象或计算中间结果。
    plt.close(fig)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def plot_beta(m, out):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = _new_fig()  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.plot(m["t"], m["beta_trucksim_deg"], lw=2.2, label="TruckSim")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_xlabel("时间 (s)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_ylabel("质心侧偏角 (deg)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_title("质心侧偏角随时间变化（TruckSim）")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.legend()  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.savefig(out, facecolor="white")  # 注释：给变量赋值、创建对象或计算中间结果。
    plt.close(fig)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def plot_yaw(m, out):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = _new_fig()  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.plot(m["t"], m["yaw_trucksim_degps"], lw=2.2, label="TruckSim")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_xlabel("时间 (s)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_ylabel("横摆角速度 (deg/s)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_title("横摆角速度随时间变化（TruckSim）")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.legend()  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.savefig(out, facecolor="white")  # 注释：给变量赋值、创建对象或计算中间结果。
    plt.close(fig)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def plot_trajectory(m, out):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = _new_fig()  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.plot(m["x_m"], m["y_m"], lw=2.2, color="C0", label="TruckSim 行驶轨迹")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_xlabel("纵向位置 x (m)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_ylabel("横向位置 y (m)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_title("车辆行驶轨迹（X-Y 平面）")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_aspect("equal", adjustable="box")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.legend()  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.savefig(out, facecolor="white")  # 注释：给变量赋值、创建对象或计算中间结果。
    plt.close(fig)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def plot_x_position(m, out):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = _new_fig()  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.plot(m["t"], m["x_m"], lw=2.2, color="C0")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_xlabel("时间 (s)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_ylabel("纵向位置 x (m)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_title("车辆纵向位置随时间变化")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.savefig(out, facecolor="white")  # 注释：给变量赋值、创建对象或计算中间结果。
    plt.close(fig)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def plot_y_position(m, out):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = _new_fig()  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.plot(m["t"], m["y_m"], lw=2.2, color="C1")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_xlabel("时间 (s)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_ylabel("横向位置 y (m)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_title("车辆横向位置随时间变化")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.savefig(out, facecolor="white")  # 注释：给变量赋值、创建对象或计算中间结果。
    plt.close(fig)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def plot_speed_vs_lateral(m, out):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = _new_fig()  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.plot(m["y_m"], m["v_kmh"], lw=2.2, color="C2")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_xlabel("横向位移 y (m)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_ylabel("车速 (km/h)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_title("车速随横向位移变化")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.savefig(out, facecolor="white")  # 注释：给变量赋值、创建对象或计算中间结果。
    plt.close(fig)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def plot_steer_delta(m, out):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    fig, ax = _new_fig()  # 注释：给变量赋值、创建对象或计算中间结果。
    ax.plot(m["t"], m["delta_deg"], lw=2.2, color="C4")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_xlabel("时间 (s)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_ylabel("转向输入 delta (deg)")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    ax.set_title("转向输入信号随时间变化（第一轴）")  # 注释：绘图相关代码，用于生成报告中的曲线图片。
    fig.savefig(out, facecolor="white")  # 注释：给变量赋值、创建对象或计算中间结果。
    plt.close(fig)  # 注释：绘图相关代码，用于生成报告中的曲线图片。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
# ----------------------------------------------------------------------------  # 注释：原脚本注释或文件头说明。
# Word 报告生成  # 注释：原脚本注释或文件头说明。
# ----------------------------------------------------------------------------  # 注释：原脚本注释或文件头说明。
def add_run(p, text, size=Pt(11), bold=False, color=COLOR_BODY,  # 注释：定义 Python 函数，封装一段可复用逻辑。
            east=FONT_EAST, latin=FONT_LATIN):  # 注释：给变量赋值、创建对象或计算中间结果。
    r = p.add_run(text)  # 注释：给变量赋值、创建对象或计算中间结果。
    r.font.name = latin  # 注释：给变量赋值、创建对象或计算中间结果。
    r._element.rPr.rFonts.set(qn("w:eastAsia"), east)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    r.font.size = size  # 注释：给变量赋值、创建对象或计算中间结果。
    r.font.bold = bold  # 注释：给变量赋值、创建对象或计算中间结果。
    r.font.color.rgb = color  # 注释：给变量赋值、创建对象或计算中间结果。
    return r  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def add_page_field(p, size=Pt(9), color=COLOR_GRAY):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    r = p.add_run()  # 注释：给变量赋值、创建对象或计算中间结果。
    r.font.name = FONT_LATIN  # 注释：给变量赋值、创建对象或计算中间结果。
    r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_EAST)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    r.font.size = size  # 注释：给变量赋值、创建对象或计算中间结果。
    r.font.color.rgb = color  # 注释：给变量赋值、创建对象或计算中间结果。
    fld1 = OxmlElement("w:fldChar")  # 注释：给变量赋值、创建对象或计算中间结果。
    fld1.set(qn("w:fldCharType"), "begin")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    instr = OxmlElement("w:instrText")  # 注释：给变量赋值、创建对象或计算中间结果。
    instr.set(qn("xml:space"), "preserve")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    instr.text = " PAGE "  # 注释：给变量赋值、创建对象或计算中间结果。
    fld2 = OxmlElement("w:fldChar")  # 注释：给变量赋值、创建对象或计算中间结果。
    fld2.set(qn("w:fldCharType"), "end")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    r._r.append(fld1)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    r._r.append(instr)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    r._r.append(fld2)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def shade_cell(cell, fill):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    tc_pr = cell._tc.get_or_add_tcPr()  # 注释：给变量赋值、创建对象或计算中间结果。
    shd = OxmlElement("w:shd")  # 注释：给变量赋值、创建对象或计算中间结果。
    shd.set(qn("w:val"), "clear")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    shd.set(qn("w:fill"), fill)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    tc_pr.append(shd)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def cell_margins(cell, top=80, start=120, bottom=80, end=120):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    tc_pr = cell._tc.get_or_add_tcPr()  # 注释：给变量赋值、创建对象或计算中间结果。
    tc_mar = OxmlElement("w:tcMar")  # 注释：给变量赋值、创建对象或计算中间结果。
    for tag, val in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        el = OxmlElement("w:" + tag)  # 注释：给变量赋值、创建对象或计算中间结果。
        el.set(qn("w:w"), str(val))  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        el.set(qn("w:type"), "dxa")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        tc_mar.append(el)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    tc_pr.append(tc_mar)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def add_heading(doc, text, page_break=False):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    if page_break:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        br_p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
        br_p.add_run().add_break(WD_BREAK.PAGE)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
    p.paragraph_format.space_before = Pt(6)  # 注释：Word 报告生成相关代码。
    p.paragraph_format.space_after = Pt(6)  # 注释：Word 报告生成相关代码。
    add_run(p, text, size=Pt(16), bold=True, color=COLOR_HEADING, east=FONT_HEADING_EAST)  # 注释：给变量赋值、创建对象或计算中间结果。
    return p  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def build_docx(report_dir, run_number, params, signal_source, sections,  # 注释：定义 Python 函数，封装一段可复用逻辑。
               conclusion_auto, conclusion_note):  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    doc = Document()  # 注释：Word 报告生成相关代码。
    sec = doc.sections[0]  # 注释：Word 报告生成相关代码。
    sec.page_width = Cm(21.0)  # 注释：给变量赋值、创建对象或计算中间结果。
    sec.page_height = Cm(29.7)  # 注释：给变量赋值、创建对象或计算中间结果。
    sec.top_margin = Cm(2.5)  # 注释：给变量赋值、创建对象或计算中间结果。
    sec.bottom_margin = Cm(2.5)  # 注释：给变量赋值、创建对象或计算中间结果。
    sec.left_margin = Cm(2.5)  # 注释：给变量赋值、创建对象或计算中间结果。
    sec.right_margin = Cm(2.5)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    hp = sec.header.paragraphs[0]  # 注释：Word 报告生成相关代码。
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 注释：给变量赋值、创建对象或计算中间结果。
    add_run(hp, "联合仿真测试报告", size=Pt(9), color=COLOR_GRAY)  # 注释：给变量赋值、创建对象或计算中间结果。
    p_pr = hp._p.get_or_add_pPr()  # 注释：给变量赋值、创建对象或计算中间结果。
    p_bdr = OxmlElement("w:pBdr")  # 注释：给变量赋值、创建对象或计算中间结果。
    bottom = OxmlElement("w:bottom")  # 注释：给变量赋值、创建对象或计算中间结果。
    bottom.set(qn("w:val"), "single")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    bottom.set(qn("w:sz"), "6")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    bottom.set(qn("w:space"), "1")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    bottom.set(qn("w:color"), "5B6573")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    p_bdr.append(bottom)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    p_pr.append(p_bdr)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    fp = sec.footer.paragraphs[0]  # 注释：Word 报告生成相关代码。
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 注释：给变量赋值、创建对象或计算中间结果。
    add_run(fp, "%s | 第" % run_number, size=Pt(9), color=COLOR_GRAY)  # 注释：给变量赋值、创建对象或计算中间结果。
    add_page_field(fp)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    add_run(fp, " 页", size=Pt(9), color=COLOR_GRAY)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 注释：给变量赋值、创建对象或计算中间结果。
    add_run(p, "PYTHON / SIMULINK / TRUCKSIM", size=Pt(11), bold=True,  # 注释：给变量赋值、创建对象或计算中间结果。
            color=RGBColor(0x2E, 0x74, 0xB5))  # 注释：给变量赋值、创建对象或计算中间结果。
    p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 注释：给变量赋值、创建对象或计算中间结果。
    p.paragraph_format.space_before = Pt(4)  # 注释：Word 报告生成相关代码。
    p.paragraph_format.space_after = Pt(4)  # 注释：Word 报告生成相关代码。
    add_run(p, "Python / Simulink / TruckSim 联合仿真测试报告",  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
            size=Pt(23), bold=True, color=COLOR_TITLE)  # 注释：给变量赋值、创建对象或计算中间结果。
    p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 注释：给变量赋值、创建对象或计算中间结果。
    p.paragraph_format.space_after = Pt(12)  # 注释：Word 报告生成相关代码。
    add_run(p, run_number, size=Pt(12), color=COLOR_GRAY)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    # 1. 测试工况  # 注释：原脚本注释或文件头说明。
    add_heading(doc, "1. 测试工况")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    tbl = doc.add_table(rows=1, cols=2)  # 注释：Word 报告生成相关代码。
    tbl.alignment = 1  # 注释：给变量赋值、创建对象或计算中间结果。
    tbl.autofit = False  # 注释：给变量赋值、创建对象或计算中间结果。
    tbl_pr = tbl._tbl.tblPr  # 注释：给变量赋值、创建对象或计算中间结果。
    layout = OxmlElement("w:tblLayout")  # 注释：给变量赋值、创建对象或计算中间结果。
    layout.set(qn("w:type"), "fixed")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    tbl_pr.append(layout)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    widths = [Twips(2700), Twips(6660)]  # 注释：给变量赋值、创建对象或计算中间结果。
    for i, w in enumerate(widths):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        for cell in tbl.columns[i].cells:  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
            cell.width = w  # 注释：给变量赋值、创建对象或计算中间结果。
    hdr = tbl.rows[0].cells  # 注释：给变量赋值、创建对象或计算中间结果。
    for i, txt in enumerate(("参数", "数值")):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        cell = hdr[i]  # 注释：给变量赋值、创建对象或计算中间结果。
        shade_cell(cell, "F2F4F7")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        cell_margins(cell)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        cp = cell.paragraphs[0]  # 注释：Word 报告生成相关代码。
        cp.paragraph_format.space_before = Pt(1)  # 注释：Word 报告生成相关代码。
        cp.paragraph_format.space_after = Pt(1)  # 注释：Word 报告生成相关代码。
        add_run(cp, txt, size=Pt(9.5), bold=True, color=COLOR_TITLE)  # 注释：给变量赋值、创建对象或计算中间结果。
    for label, value in params:  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        row = tbl.add_row().cells  # 注释：给变量赋值、创建对象或计算中间结果。
        c0, c1 = row[0], row[1]  # 注释：给变量赋值、创建对象或计算中间结果。
        shade_cell(c0, "F7F9FB")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        cell_margins(c0)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        cell_margins(c1)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        p0 = c0.paragraphs[0]  # 注释：Word 报告生成相关代码。
        p0.paragraph_format.space_before = Pt(1)  # 注释：Word 报告生成相关代码。
        p0.paragraph_format.space_after = Pt(1)  # 注释：Word 报告生成相关代码。
        add_run(p0, label, size=Pt(9), bold=True, color=COLOR_TITLE)  # 注释：给变量赋值、创建对象或计算中间结果。
        p1 = c1.paragraphs[0]  # 注释：Word 报告生成相关代码。
        p1.paragraph_format.space_before = Pt(1)  # 注释：Word 报告生成相关代码。
        p1.paragraph_format.space_after = Pt(1)  # 注释：Word 报告生成相关代码。
        add_run(p1, value, size=Pt(9), color=COLOR_BODY)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    # 2. 数据来源与信号说明  # 注释：原脚本注释或文件头说明。
    add_heading(doc, "2. 数据来源与信号说明", page_break=True)  # 注释：给变量赋值、创建对象或计算中间结果。
    body = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
    body.paragraph_format.space_after = Pt(6)  # 注释：Word 报告生成相关代码。
    add_run(body, signal_source)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    # 3..N 图表节  # 注释：原脚本注释或文件头说明。
    fig_no = 0  # 注释：给变量赋值、创建对象或计算中间结果。
    for i, s in enumerate(sections):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
        title_no = 3 + i  # 注释：给变量赋值、创建对象或计算中间结果。
        add_heading(doc, "%d. %s" % (title_no, s["title"]), page_break=True)  # 注释：给变量赋值、创建对象或计算中间结果。
        if s["available"]:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
            fig_no += 1  # 注释：给变量赋值、创建对象或计算中间结果。
            img_p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
            img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 注释：给变量赋值、创建对象或计算中间结果。
            img_p.add_run().add_picture(  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                os.path.join(report_dir, s["fileName"]), width=Inches(6.3))  # 注释：文件路径、目录创建或文件复制操作。
            cap_p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
            cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER  # 注释：给变量赋值、创建对象或计算中间结果。
            cap_p.paragraph_format.space_before = Pt(4)  # 注释：Word 报告生成相关代码。
            add_run(cap_p, "图%d  %s" % (fig_no, s["title"]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                    size=Pt(9), color=COLOR_GRAY)  # 注释：给变量赋值、创建对象或计算中间结果。
        else:  # 注释：条件判断的兜底分支。
            note_p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
            add_run(note_p, "暂无数据：%s" % s["note"],  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                    size=Pt(10.5), color=COLOR_NOTE)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    # 结论  # 注释：原脚本注释或文件头说明。
    add_heading(doc, "%d. 结论" % (3 + len(sections)), page_break=True)  # 注释：给变量赋值、创建对象或计算中间结果。
    conc = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
    conc.paragraph_format.space_after = Pt(6)  # 注释：Word 报告生成相关代码。
    add_run(conc, conclusion_auto)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    note_p = doc.add_paragraph()  # 注释：Word 报告生成相关代码。
    add_run(note_p, "人工结论：%s" % conclusion_note, size=Pt(10.5), color=COLOR_NOTE)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    docx_path = os.path.join(report_dir, run_number + ".docx")  # 注释：文件路径、目录创建或文件复制操作。 Python 依赖相关代码；换电脑后需要安装对应库。
    try:  # 注释：异常保护开始，下面代码失败时会进入 except。
        doc.save(docx_path)  # 注释：Word 报告生成相关代码。 Python 依赖相关代码；换电脑后需要安装对应库。
    except OSError:  # 注释：异常处理分支，用于记录错误或采用备用逻辑。
        sys.exit("无法写入 Word 报告（文件可能正被 Word 打开）：%s\n"  # 注释：发生不可继续的问题时主动报错或退出。
                 "请关闭该文件后重新运行。" % docx_path)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。 Python 依赖相关代码；换电脑后需要安装对应库。
    return docx_path  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
# ----------------------------------------------------------------------------  # 注释：原脚本注释或文件头说明。
# 主流程  # 注释：原脚本注释或文件头说明。
# ----------------------------------------------------------------------------  # 注释：原脚本注释或文件头说明。
def build_manifest(run_number, params, signal_source, sections,  # 注释：定义 Python 函数，封装一段可复用逻辑。
                   conclusion_auto, conclusion_note):  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    return {  # 注释：返回函数计算结果给调用方。
        "report_id": run_number,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "title": "Co-simulation Test Report",  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "parameters": [{"label": k, "value": v} for k, v in params],  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "signal_source": signal_source,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "sections": sections,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "conclusion_auto": conclusion_auto,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "conclusion_note": conclusion_note,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    }  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def main():  # 注释：定义 Python 函数，封装一段可复用逻辑。
    ap = argparse.ArgumentParser(description="生成联合仿真测试报告")  # 注释：定义命令行参数，供 MATLAB 或用户调用脚本时传入。
    ap.add_argument("--run", default=None, help="运行编号或目录（默认最近一次）")  # 注释：定义命令行参数，供 MATLAB 或用户调用脚本时传入。
    ap.add_argument("--data-root", default=DEFAULT_DATA_ROOT)  # 注释：定义命令行参数，供 MATLAB 或用户调用脚本时传入。 报告脚本默认数据目录，应和 MATLAB 导出的 dataRoot 对应。
    ap.add_argument("--user", default=DEFAULT_USER)  # 注释：定义命令行参数，供 MATLAB 或用户调用脚本时传入。
    ap.add_argument("--case-dir", default=DEFAULT_CASE_DIR)  # 注释：定义命令行参数，供 MATLAB 或用户调用脚本时传入。
    ap.add_argument("--report-root", default=DEFAULT_REPORT_ROOT)  # 注释：定义命令行参数，供 MATLAB 或用户调用脚本时传入。 报告脚本默认报告目录，生成图片和 Word 会写到这里。
    args = ap.parse_args()  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    run_arg = args.run  # 注释：给变量赋值、创建对象或计算中间结果。
    if run_arg is None:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        run_arg = os.environ.get("RUN_NO_REPORT")  # 注释：给变量赋值、创建对象或计算中间结果。
    if run_arg is None:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        marker = os.path.join(tempfile.gettempdir(), "codex_last_run_no.txt")  # 注释：文件路径、目录创建或文件复制操作。
        if os.path.isfile(marker):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
            with open(marker, "r", encoding="utf-8-sig") as f:  # 注释：上下文管理语句，通常用于安全打开和关闭文件。
                run_arg = f.read().strip()  # 注释：给变量赋值、创建对象或计算中间结果。
    run_dir, run_number = resolve_run(args.data_root, args.user, run_arg)  # 注释：给变量赋值、创建对象或计算中间结果。
    if run_dir is None and run_arg:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        run_dir, run_number = find_run_anywhere(args.data_root, run_arg)  # 注释：给变量赋值、创建对象或计算中间结果。
    if run_dir is None and not run_arg:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        run_dir, run_number = find_latest_anywhere(args.data_root)  # 注释：给变量赋值、创建对象或计算中间结果。
    if run_dir is None:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        sys.exit("无法定位运行数据（数据根目录: %s，运行编号: %s）"  # 注释：发生不可继续的问题时主动报错或退出。
                 % (args.data_root, run_arg or "最近一次"))  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    io_csv = os.path.join(run_dir, "%s_trucksim_io.csv" % run_number)  # 注释：文件路径、目录创建或文件复制操作。
    case_info_csv = os.path.join(run_dir, "%s_case_info.csv" % run_number)  # 注释：文件路径、目录创建或文件复制操作。
    if not os.path.isfile(io_csv) or not os.path.isfile(case_info_csv):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        sys.exit("运行目录缺少 trucksim_io.csv 或 case_info.csv: %s" % run_dir)  # 注释：发生不可继续的问题时主动报错或退出。
# 注释：空行，用来分隔代码段。
    case = load_case_info(case_info_csv)  # 注释：给变量赋值、创建对象或计算中间结果。
    df = load_data(io_csv)  # 注释：给变量赋值、创建对象或计算中间结果。
    m = compute_metrics(df)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    report_dir = os.path.join(args.report_root, run_number)  # 注释：文件路径、目录创建或文件复制操作。
    os.makedirs(report_dir, exist_ok=True)  # 注释：文件路径、目录创建或文件复制操作。
# 注释：空行，用来分隔代码段。
    _setup_mpl()  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    plot_speed(m, os.path.join(report_dir, "01_vehicle_speed.png"),  # 注释：文件路径、目录创建或文件复制操作。
               target_kmh=_f(case, "target_speed_kmh", float))  # 注释：给变量赋值、创建对象或计算中间结果。
    plot_beta(m, os.path.join(report_dir, "02_beta_compare.png"))  # 注释：文件路径、目录创建或文件复制操作。
    plot_yaw(m, os.path.join(report_dir, "03_yaw_rate_compare.png"))  # 注释：文件路径、目录创建或文件复制操作。
    plot_trajectory(m, os.path.join(report_dir, "04_trajectory.png"))  # 注释：文件路径、目录创建或文件复制操作。
    plot_x_position(m, os.path.join(report_dir, "05_x_position.png"))  # 注释：文件路径、目录创建或文件复制操作。
    plot_y_position(m, os.path.join(report_dir, "06_y_position.png"))  # 注释：文件路径、目录创建或文件复制操作。
    plot_speed_vs_lateral(m, os.path.join(report_dir, "07_speed_vs_lateral.png"))  # 注释：文件路径、目录创建或文件复制操作。
    delta_ok = m.get("delta_deg") is not None and m["delta_deg"].size > 0  # 注释：给变量赋值、创建对象或计算中间结果。
    if delta_ok:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        plot_steer_delta(m, os.path.join(report_dir, "08_steer_delta.png"))  # 注释：文件路径、目录创建或文件复制操作。
# 注释：空行，用来分隔代码段。
    copied_case = ""  # 注释：给变量赋值、创建对象或计算中间结果。
    case_name = case.get("case_name", "")  # 注释：给变量赋值、创建对象或计算中间结果。
    if case_name:  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        for fname in os.listdir(args.case_dir):  # 注释：循环开始，逐个处理列表、字典、文件行或绘图项。
            if fname.lower().endswith(".txt") and fname.startswith(case_name):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
                copied_case = os.path.join(report_dir, fname)  # 注释：文件路径、目录创建或文件复制操作。
                shutil.copy2(os.path.join(args.case_dir, fname), copied_case)  # 注释：文件路径、目录创建或文件复制操作。
                break  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    init_v = _f(case, "initial_speed_kmh", float)  # 注释：给变量赋值、创建对象或计算中间结果。
    stop_time = _f(case, "stop_time_s", float)  # 注释：给变量赋值、创建对象或计算中间结果。
    target_v = _f(case, "target_speed_kmh", float)  # 注释：给变量赋值、创建对象或计算中间结果。
    params = [  # 注释：给变量赋值、创建对象或计算中间结果。
        ("工况名称", case.get("case_name", "")),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("工况说明", case.get("description", "")),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("控制器模式", case.get("controller_mode", "无（模型验证）")),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("设定仿真时长", "%g s" % stop_time),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("实际仿真时长", "%.4g s" % m["duration_s"]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("设定初始车速", "%g km/h" % init_v),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("车辆速度（初始 / 结束）", "%.6g / %.6g km/h" % (m["v_start_kmh"], m["v_end_kmh"])),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("车辆速度（最小 / 最大）", "%.6g / %.6g km/h" % (m["v_min_kmh"], m["v_max_kmh"])),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("目标车速（用例设定）", "%g km/h" % target_v),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("转向输入类型", case.get("steer_input_type", "")),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("转向幅值（第一轴）", "%s deg" % case.get("steer_amplitude_deg", "-")),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("转向频率", "%s Hz" % case["steer_frequency_hz"]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         if case.get("steer_frequency_hz") else "不适用（阶跃/其他输入）"),  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        ("转向开始时间", "%s s" % case.get("steer_start_time_s", "-")),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("第二/第三轴转角", "0 deg（模型内固定）"),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("路面附着系数", case.get("road_friction", "-")),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("路面坡度", "%s" % case.get("road_grade", "-")),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("测试用例文件", os.path.join(args.case_dir, case_name + ".txt")),  # 注释：文件路径、目录创建或文件复制操作。
        ("原始数据文件", io_csv),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("报告内测试用例副本", copied_case or "未找到对应测试用例文件"),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("累计行驶距离", "%.4g m（由车速信号梯形积分）" % m["distance_m"]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("最大横向位移", "%.4g m" % m["max_abs_y_m"]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("最大横摆角速度（TruckSim）", "%.4g deg/s" % m["max_yaw_trucksim_degps"]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        ("最大质心侧偏角（TruckSim）", "%.4g deg" % m["max_abs_beta_trucksim_deg"]),  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    ]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    signal_source = (  # 注释：给变量赋值、创建对象或计算中间结果。
        "本模型仅保留 TruckSim S-Function 输入/输出接口，不含 3DOF 参考模型。"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "所有车辆状态信号均由 TruckSim 输出，经模型内 To Workspace 块导出："  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "车速（Vx_trucksim，km/h）、质心侧偏角（beta_trucksim，deg）、"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "横摆角速度（w_trucksim，deg/s）、车辆位置（x_trucksim / y_trucksim，m）"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "与挂车位置（xt_trucksim / yt_trucksim，m）。"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "转向输入 delta_input（deg）由 run_case_new.m 按测试用例生成 "  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "timeseries(steer_input) 后经模型内 From Workspace（Steering Input）输入，"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "仅作用于第一轴，第二、第三轴转角固定为 0。"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "注意：TruckSim 侧初始工况以固定 simfile 为准（trucksim_config.m 的 "  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "COM 映射未启用），与用例 initial_speed_kmh 可能不一致。"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    )  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    sections = [  # 注释：给变量赋值、创建对象或计算中间结果。
        {"title": "车辆实际速度随时间变化", "available": True,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "fileName": "01_vehicle_speed.png", "note": ""},  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        {"title": "质心侧偏角随时间变化（TruckSim）", "available": True,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "fileName": "02_beta_compare.png", "note": ""},  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        {"title": "横摆角速度随时间变化（TruckSim）", "available": True,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "fileName": "03_yaw_rate_compare.png", "note": ""},  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        {"title": "车辆行驶轨迹（X-Y 平面）", "available": True,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "fileName": "04_trajectory.png", "note": ""},  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        {"title": "车辆纵向位置随时间变化", "available": True,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "fileName": "05_x_position.png", "note": ""},  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        {"title": "车辆横向位置随时间变化", "available": True,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "fileName": "06_y_position.png", "note": ""},  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        {"title": "车速随横向位移变化", "available": True,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "fileName": "07_speed_vs_lateral.png", "note": ""},  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        {"title": "转向输入信号（delta，第一轴）", "available": delta_ok,  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "fileName": "08_steer_delta.png" if delta_ok else "",  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
         "note": "数据文件（trucksim_io.csv）中暂无转向输入信号列。"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
                 "请确认模型含 To Workspace(delta_input) 并重新运行。"},  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    ]  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    conclusion_auto = (  # 注释：给变量赋值、创建对象或计算中间结果。
        "本次联合仿真已完成。实际仿真时长为 %.4g s（设定 %g s）；车辆初始/结束速度为 "  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "%.6g / %.6g km/h；车辆最小/最大速度为 %.6g / %.6g km/h；车辆累计行驶距离 "  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "%.4g m；最大横向位移 %.4g m；TruckSim 最大横摆角速度 %.4g deg/s，"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        "最大质心侧偏角 %.4g deg。"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        % (m["duration_s"], stop_time, m["v_start_kmh"], m["v_end_kmh"],  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
           m["v_min_kmh"], m["v_max_kmh"], m["distance_m"], m["max_abs_y_m"],  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
           m["max_yaw_trucksim_degps"], m["max_abs_beta_trucksim_deg"])  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    )  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    speed_mismatch = abs(m["v_start_kmh"] - init_v) > 0.5  # 注释：给变量赋值、创建对象或计算中间结果。
    if case.get("conclusion_note"):  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        conclusion_note = case["conclusion_note"]  # 注释：给变量赋值、创建对象或计算中间结果。
    elif speed_mismatch:  # 注释：条件判断的另一个分支。
        conclusion_note = (  # 注释：给变量赋值、创建对象或计算中间结果。
            "注意：TruckSim 实际起始车速 %.6g km/h 与用例设定 %g km/h 不一致"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
            "（TruckSim 工况以固定 simfile 为准）；如需按用例初始车速运行，"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
            "请完成 trucksim_config.m 的 COM 映射后启用 useTrucksimCom。"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。 是否启用 TruckSim COM 配置；旧流程当前映射未验证，通常保持 false。
            % (m["v_start_kmh"], init_v)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        )  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    else:  # 注释：条件判断的兜底分支。
        conclusion_note = (  # 注释：给变量赋值、创建对象或计算中间结果。
            "本工况为模型验证用例（%s），TruckSim 响应符合预期，"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
            "可作为后续控制器联合仿真的基线。"  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
            % case.get("source_case_id", "")  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
        )  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    manifest = build_manifest(run_number, params, signal_source, sections,  # 注释：给变量赋值、创建对象或计算中间结果。
                              conclusion_auto, conclusion_note)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
    with open(os.path.join(report_dir, "report_manifest.json"), "w",  # 注释：上下文管理语句，通常用于安全打开和关闭文件。
              encoding="utf-8") as f:  # 注释：给变量赋值、创建对象或计算中间结果。
        json.dump(manifest, f, ensure_ascii=False, indent=2)  # 注释：给变量赋值、创建对象或计算中间结果。
# 注释：空行，用来分隔代码段。
    docx_path = build_docx(report_dir, run_number, params, signal_source, sections,  # 注释：给变量赋值、创建对象或计算中间结果。 Python 依赖相关代码；换电脑后需要安装对应库。
                           conclusion_auto, conclusion_note)  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
# 注释：空行，用来分隔代码段。
    print("测试报告生成完成")  # 注释：打印运行状态，便于 MATLAB 或命令行查看执行结果。
    print("  报告目录: %s" % report_dir)  # 注释：打印运行状态，便于 MATLAB 或命令行查看执行结果。
    print("  Word 报告: %s" % docx_path)  # 注释：打印运行状态，便于 MATLAB 或命令行查看执行结果。
    print("  清单文件: %s" % os.path.join(report_dir, "report_manifest.json"))  # 注释：文件路径、目录创建或文件复制操作。
    print("  曲线图数量: %d" % sum(1 for s in sections if s["available"]))  # 注释：打印运行状态，便于 MATLAB 或命令行查看执行结果。
    print("REPORT_OK", flush=True)  # 注释：打印运行状态，便于 MATLAB 或命令行查看执行结果。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
def _f(d, key, cast, default=None):  # 注释：定义 Python 函数，封装一段可复用逻辑。
    v = d.get(key)  # 注释：给变量赋值、创建对象或计算中间结果。
    if v is None or v == "":  # 注释：条件判断开始，根据当前变量状态选择执行路径。
        return default  # 注释：返回函数计算结果给调用方。
    try:  # 注释：异常保护开始，下面代码失败时会进入 except。
        return cast(v)  # 注释：返回函数计算结果给调用方。
    except (TypeError, ValueError):  # 注释：异常处理分支，用于记录错误或采用备用逻辑。
        return default  # 注释：返回函数计算结果给调用方。
# 注释：空行，用来分隔代码段。
# 注释：空行，用来分隔代码段。
if __name__ == "__main__":  # 注释：条件判断开始，根据当前变量状态选择执行路径。
    main()  # 注释：执行 Python 语句，完成当前脚本流程的一小步。
