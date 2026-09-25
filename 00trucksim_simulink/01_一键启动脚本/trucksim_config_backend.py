#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段一本地TruckSim工况配置。

本模块仅供00trucksim_simulink使用。优先通过TruckSim COM配置当前Run；
COM不可用时，从simfile.sim的INPUT项定位参数文件并更新关联.par文件。
"""
import os
import re
import shutil
import time


RUN_NAME = "ORAC-BLFISMC1017 #phase1"
COM_PROGIDS = ("TruckSim.Application", "TruckSim2019.Application", "TS.Application")


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as handle:
        return handle.read()


def _write_text(path, text):
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as handle:
        handle.write(text)


def _read(run, name):
    for method_name in ("GetVariable", "GetParameter", "GetValue"):
        try:
            method = getattr(run, method_name, None)
            if method is not None:
                return True, float(method(name))
        except Exception:
            pass
    try:
        return True, float(getattr(run, name))
    except Exception:
        return False, None


def _write(run, name, value):
    for method_name in ("SetVariable", "SetParameter", "SetValue"):
        try:
            method = getattr(run, method_name, None)
            if method is not None:
                method(name, value)
                return True
        except Exception:
            pass
    try:
        setattr(run, name, value)
        return True
    except Exception:
        return False


def _write_checked(run, name, value):
    if not _write(run, name, value):
        print("[phase1_com] 写入失败: %s=%g" % (name, value))
        return False
    ok, actual = _read(run, name)
    if not ok or abs(actual - value) > max(1e-6, abs(value) * 1e-3):
        print("[phase1_com] 回读校验失败: %s 期望=%g 实际=%s" % (name, value, actual))
        return False
    return True


def _connect_com():
    import win32com.client
    for progid in COM_PROGIDS:
        try:
            trucksim = win32com.client.Dispatch(progid)
            print("[phase1_com] 已连接COM: %s" % progid)
            return trucksim
        except Exception as exc:
            print("[phase1_com] ProgID %s连接失败: %s" % (progid, exc))
    return None


def _resolve_simfile_input(simfile_path):
    if not os.path.isfile(simfile_path):
        raise FileNotFoundError("simfile.sim不存在: %s" % simfile_path)
    macros = {}
    input_expr = None
    for raw in _read_text(simfile_path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("SET_MACRO "):
            parts = line.split(None, 2)
            if len(parts) == 3:
                macros[parts[1]] = parts[2]
        elif line.startswith("INPUT ") and not line.startswith("INPUTARCHIVE "):
            input_expr = line.split(None, 1)[1].strip()
            break
    if not input_expr:
        raise RuntimeError("simfile.sim中未找到INPUT行: %s" % simfile_path)
    for key, value in macros.items():
        input_expr = input_expr.replace(key, value)
    input_expr = input_expr.replace("/", "\\")
    if not os.path.isabs(input_expr):
        input_expr = os.path.join(os.path.dirname(os.path.abspath(simfile_path)), input_expr)
    return os.path.normpath(input_expr)


def _patch_keyword(text, keyword, value):
    pattern = re.compile(
        r"^(\s*\*?%s\s+)([-+0-9.eE]+)(\s*(?:[#!;].*)?)$" % re.escape(keyword),
        re.MULTILINE,
    )
    return pattern.subn(r"\g<1>%s\g<3>" % ("%.15g" % value), text)


def _par_references(text, data_root):
    patterns = (
        re.compile(r"^\s*(?:ENTER_PARSFILE|PARSFILE)\s+(.+?\.par)\s*$", re.MULTILINE | re.IGNORECASE),
        re.compile(r"^\s*DEFINE_EVENT\b.*?;\s*(.+?\.par)\s*(?:[#!;].*)?$", re.MULTILINE | re.IGNORECASE),
    )
    result, seen = [], set()
    for pattern in patterns:
        for match in pattern.finditer(text):
            candidate = match.group(1).strip().strip('"').replace("/", "\\")
            path = os.path.normpath(candidate if os.path.isabs(candidate) else os.path.join(data_root, candidate))
            key = os.path.normcase(path)
            if key not in seen and os.path.isfile(path):
                seen.add(key)
                result.append(path)
    return result


def _linked_par_files(root_par, data_root):
    result, seen, queue = [], set(), [root_par]
    while queue:
        path = queue.pop(0)
        key = os.path.normcase(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
        try:
            queue.extend(child for child in _par_references(_read_text(path), data_root)
                         if os.path.normcase(child) not in seen)
        except OSError:
            pass
    return result


def _updates_for(path, data_root, updates):
    rel = os.path.relpath(path, data_root).replace("/", "\\").lower()
    if rel.startswith("procedures\\"):
        keys = ("TSTOP", "SPEED", "SPEED_TARGET_CONSTANT")
    elif rel.startswith("events\\"):
        keys = ("SPEED", "SPEED_TARGET_CONSTANT")
    else:
        keys = ()
    return {key: updates[key] for key in keys if key in updates}


def _patch_one(path, updates):
    try:
        text = _read_text(path)
    except OSError as exc:
        return {}, None, str(exc)
    counts = {}
    for keyword, value in updates.items():
        text, counts[keyword] = _patch_keyword(text, keyword, value)
    if not any(counts.values()):
        return counts, None, None
    backup = path + ".phase1_backup"
    try:
        if not os.path.isfile(backup):
            shutil.copy2(path, backup)
        _write_text(path, text)
        return counts, backup, None
    except OSError as exc:
        return {}, backup, str(exc)


def _patch_par_files(case, cfg):
    trucksim = cfg.get("trucksim", {})
    if not trucksim.get("allow_par_file_patch", True):
        print("[phase1_par] COM不可用，且未允许.par回退配置")
        return False
    simfile = trucksim.get("simfile_path")
    try:
        root_par = _resolve_simfile_input(simfile)
    except Exception as exc:
        print("[phase1_par] 解析simfile.sim失败: %s" % exc)
        return False
    if not os.path.isfile(root_par):
        print("[phase1_par] INPUT参数文件不存在: %s" % root_par)
        return False

    # road_friction 是目标绝对附着系数。当前道路文件保留其基准
    # MU_ROAD_CONSTANT；只写 MY_FRICTION 倍率，避免二次缩放。
    mu = float(case.get("road_friction", 0.85))
    base_mu = float(trucksim.get("road_base_mu", 0.85))
    if base_mu <= 0:
        print("[phase1_par] road_base_mu 必须大于 0")
        return False
    target_speed = float(case.get("target_speed_kmh") or case["initial_speed_kmh"])
    updates = {
        "TSTOP": float(case["stop_time_s"]),
        "SPEED": float(case["initial_speed_kmh"]),
        "SPEED_TARGET_CONSTANT": target_speed,
        "MY_FRICTION": mu / base_mu,
    }
    data_root = os.path.dirname(os.path.abspath(simfile))
    total, touched = {key: 0 for key in updates}, []
    for index, path in enumerate(_linked_par_files(root_par, data_root)):
        selected = updates if index == 0 else _updates_for(path, data_root, updates)
        if not selected:
            continue
        counts, backup, error = _patch_one(path, selected)
        if error:
            print("[phase1_par] 无法写入%s: %s" % (path, error))
            continue
        if any(counts.values()):
            touched.append((path, backup))
            for key, count in counts.items():
                total[key] += count
    required = ("TSTOP", "SPEED", "SPEED_TARGET_CONSTANT")
    missing = [key for key in required if total[key] == 0]
    if missing or not touched:
        print("[phase1_par] 关键字段未写入: %s" % ", ".join(missing or ["无可写入字段"]))
        return False
    for path, backup in touched:
        print("[phase1_par] 已更新: %s（备份: %s）" % (path, backup))
    return True


def _configure_by_com(case, cfg):
    trucksim = _connect_com()
    if trucksim is None:
        return None
    run_name = cfg.get("trucksim", {}).get("run_name", RUN_NAME)
    try:
        run = trucksim.GetRunByName(run_name)
    except Exception as exc:
        print("[phase1_com] 定位Run失败(%s): %s" % (run_name, exc))
        return False
    mu = float(case.get("road_friction", 0.85))
    base_mu = float(cfg.get("trucksim", {}).get("road_base_mu", 0.85))
    if base_mu <= 0:
        print("[phase1_com] road_base_mu 必须大于 0")
        return False
    target_speed = float(case.get("target_speed_kmh") or case["initial_speed_kmh"])
    pairs = (
        ("TSTOP", float(case["stop_time_s"])),
        ("SPEED", float(case["initial_speed_kmh"])),
        ("SPEED_TARGET_CONSTANT", target_speed),
        ("MY_FRICTION", mu / base_mu),
        ("OPT_INIT_SPEED", 1.0),
    )
    return all(_write_checked(run, name, value) for name, value in pairs)


def configure_trucksim(case, cfg):
    """按TXT用例配置阶段一TruckSimRun，返回是否成功。"""
    try:
        result = _configure_by_com(case, cfg)
    except Exception as exc:
        print("[phase1_com] COM不可用: %s，改用.par回退配置" % exc)
        result = None
    if result is None:
        return _patch_par_files(case, cfg)
    if result:
        print("[phase1_com] 工况配置完成并已回读确认")
        time.sleep(0.1)
    return result
