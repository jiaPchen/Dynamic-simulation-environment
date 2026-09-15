# -*- coding: utf-8 -*-
"""TruckSim 2019 COM 工况配置（阶段二）。

目标：仿真前由 Python 按 TXT 用例全量设置固定联仿 Run 的
初始/目标车速、附着系数、坡度和可选场景，回读确认后输出 CONFIG_READY。

映射依据：cpar(ORAC-BLFISMC1017 #phase2) 解包后的 temp.par 关键字——
  TSTOP                  仿真停止时间
  SPEED_TARGET_CONSTANT  速度控制器目标车速（km/h）
  MY_FRICTION            附着系数倍率（当前 1，道路基准 Mu=0.85）
  （road_grade 无独立关键字，平地；trucksim_scenario 对应道路数据集）

注意：优先使用 TruckSim/VehicleSim COM 自动化接口；若当前机器未注册 COM
ProgID，则回退为修改 simfile.sim 指向的 Run_all.par。Simulink S-Function 实际
读取该 par 文件，因此该回退能让 TXT 中的速度、仿真时长和附着系数进入本次仿真。
"""
import os
import re
import shutil
import time


RUN_NAME = "ORAC-BLFISMC1017 #phase2"
DEFAULT_KEYWORDS = {
    "stop_time_s": ["TSTOP"],
    "initial_speed_kmh": ["SPEED"],
    "target_speed_kmh": ["SPEED_TARGET_CONSTANT"],
    "road_friction_scale": ["MY_FRICTION"],
    "init_speed_enable": ["OPT_INIT_SPEED"],
}
PAR_KEYWORDS = {
    "stop_time_s": "TSTOP",
    "initial_speed_kmh": "SPEED",
    "target_speed_kmh": "SPEED_TARGET_CONSTANT",
    "road_friction": "MU_ROAD_CONSTANT",
    "road_friction_scale": "MY_FRICTION",
}


def _read(run, name):
    """尝试多种方式读取参数，返回 (ok, 值)。"""
    for getm in ("GetVariable", "GetParameter", "GetValue"):
        try:
            m = getattr(run, getm, None)
            if m is None:
                continue
            v = m(name)
            return True, float(v)
        except Exception:
            continue
    try:
        return True, float(getattr(run, name))
    except Exception:
        return False, None


def _write(run, name, value):
    """尝试多种方式写入参数，返回是否成功。"""
    for setm in ("SetVariable", "SetParameter", "SetValue"):
        try:
            m = getattr(run, setm, None)
            if m is None:
                continue
            m(name, value)
            return True
        except Exception:
            continue
    try:
        setattr(run, name, value)
        return True
    except Exception:
        return False


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _keywords(cfg, key):
    custom = cfg.get("trucksim", {}).get("com_keywords", {})
    if key in custom:
        return _as_list(custom[key])
    return DEFAULT_KEYWORDS.get(key, [])


def _write_checked(run, name, val):
    if not _write(run, name, val):
        print("[trucksim_com] 写入失败: %s=%g（请在目标机确认该控件名）" % (name, val))
        return False
    ok, got = _read(run, name)
    if not ok:
        print("[trucksim_com] 已写入但无法回读: %s（请在目标机确认回读接口）" % name)
        return False
    if abs(got - val) > max(1e-6, abs(val) * 1e-3):
        print("[trucksim_com] 回读校验失败: %s 期望 %g 实际 %s" % (name, val, got))
        return False
    return True


def _write_all(run, label, names, val, required=True):
    if not names:
        if required:
            print("[trucksim_com] 缺少 %s 的 COM 关键字映射，请在 vehicle_config.yaml:trucksim.com_keywords 中配置" % label)
            return False
        return True
    ok_all = True
    for name in names:
        ok_all = _write_checked(run, str(name), val) and ok_all
    return ok_all


def _apply_scenario(run, case, cfg):
    scenario = str(case.get("trucksim_scenario", "")).strip()
    if not scenario:
        return True
    scenario_map = cfg.get("trucksim", {}).get("scenario_map", {})
    if scenario not in scenario_map:
        print("[trucksim_com] 未配置 trucksim_scenario=%s 的映射；请在 vehicle_config.yaml:trucksim.scenario_map 中补充" % scenario)
        return False
    mapping = scenario_map.get(scenario) or {}
    ok_all = True
    for name, val in mapping.items():
        try:
            fval = float(val)
        except (TypeError, ValueError):
            print("[trucksim_com] 场景映射仅支持数值参数: %s=%r" % (name, val))
            ok_all = False
            continue
        ok_all = _write_checked(run, str(name), fval) and ok_all
    print("[trucksim_com] 场景映射完成: %s" % scenario)
    return ok_all


def _connect(cfg):
    """连接 TruckSim COM（按配置中的 ProgID 列表逐个尝试）。"""
    import win32com.client
    trucksim = cfg.get("trucksim", {})
    progids = trucksim.get("com_progids") or [trucksim.get("com_progid", "TruckSim.Application")]
    if isinstance(progids, str):
        progids = [progids]
    for progid in progids:
        try:
            ts = win32com.client.Dispatch(progid)
            print("[trucksim_com] 已连接 COM: %s" % progid)
            return ts
        except Exception as e:
            print("[trucksim_com] ProgID %s 连接失败: %s" % (progid, e))
    return None


def _read_text(path):
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
        return f.read()


def _write_text(path, text):
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(text)


def _resolve_simfile_input(simfile_path):
    if not os.path.isfile(simfile_path):
        raise FileNotFoundError("simfile.sim 不存在: %s" % simfile_path)
    base_dir = os.path.dirname(os.path.abspath(simfile_path))
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
        raise RuntimeError("simfile.sim 中未找到 INPUT 行: %s" % simfile_path)
    for key, value in macros.items():
        input_expr = input_expr.replace(key, value)
    input_expr = input_expr.replace("/", "\\")
    if not os.path.isabs(input_expr):
        input_expr = os.path.join(base_dir, input_expr)
    return os.path.normpath(input_expr)


def _patch_keyword_lines(text, keyword, value):
    pattern = re.compile(r"^(\s*\*?%s\s+)([-+0-9.eE]+)(\s*(?:[#!;].*)?)$" % re.escape(keyword),
                         re.MULTILINE)
    replacement = r"\g<1>%s\g<3>" % ("%.15g" % value)
    text2, count = pattern.subn(replacement, text)
    return text2, count


def _par_references(text, data_root):
    files = []
    seen = set()
    patterns = [
        re.compile(r"^\s*(?:ENTER_PARSFILE|PARSFILE)\s+(.+?\.par)\s*$",
                   re.MULTILINE | re.IGNORECASE),
        re.compile(r"^\s*DEFINE_EVENT\b.*?;\s*(.+?\.par)\s*(?:[#!;].*)?$",
                   re.MULTILINE | re.IGNORECASE),
    ]
    for pattern in patterns:
        for m in pattern.finditer(text):
            rel = m.group(1).strip().strip('"').replace("/", "\\")
            if os.path.isabs(rel):
                path = os.path.normpath(rel)
            else:
                path = os.path.normpath(os.path.join(data_root, rel))
            key = os.path.normcase(path)
            if key not in seen and os.path.isfile(path):
                seen.add(key)
                files.append(path)
    return files


def _linked_par_files(text, data_root):
    files = []
    seen = set()
    stack = _par_references(text, data_root)
    while stack:
        path = stack.pop(0)
        key = os.path.normcase(path)
        if key in seen:
            continue
        seen.add(key)
        files.append(path)
        try:
            child_text = _read_text(path)
        except OSError:
            continue
        for child in _par_references(child_text, data_root):
            child_key = os.path.normcase(child)
            if child_key not in seen:
                stack.append(child)
    return files


def _patch_one_par_file(path, updates, required_keywords=None):
    try:
        text = _read_text(path)
    except OSError as e:
        empty_counts = dict((k, 0) for k in updates)
        return empty_counts, list(required_keywords or ()), None, str(e)

    counts = {}
    for keyword, value in updates.items():
        text, count = _patch_keyword_lines(text, keyword, value)
        counts[keyword] = count
    if any(counts.values()):
        backup_path = path + ".phase2_backup"
        try:
            if not os.path.isfile(backup_path):
                shutil.copy2(path, backup_path)
            _write_text(path, text)
        except OSError as e:
            empty_counts = dict((k, 0) for k in updates)
            return empty_counts, list(required_keywords or ()), backup_path, str(e)
    else:
        backup_path = None

    required_keywords = required_keywords or ()
    missing = [k for k in required_keywords if counts.get(k, 0) == 0]
    return counts, missing, backup_path, None


def _source_updates_for(path, data_root, all_updates):
    rel = os.path.relpath(path, data_root).replace("/", "\\")
    rel_lower = rel.lower()
    if rel_lower.startswith("procedures\\"):
        keys = ("TSTOP", "SPEED", "SPEED_TARGET_CONSTANT")
    elif rel_lower.startswith("events\\"):
        keys = ("SPEED", "SPEED_TARGET_CONSTANT")
    elif rel_lower.startswith("roads\\friction\\"):
        keys = ("MU_ROAD_CONSTANT",)
    else:
        keys = ()
    return dict((k, all_updates[k]) for k in keys if k in all_updates)


def _source_patch_priority(path, data_root):
    rel = os.path.relpath(path, data_root).replace("/", "\\").lower()
    if rel.startswith("procedures\\"):
        return 0
    if rel.startswith("events\\"):
        return 1
    if rel.startswith("roads\\friction\\"):
        return 2
    return 9


def _patch_run_all_par(case, cfg):
    trucksim = cfg.get("trucksim", {})
    if not trucksim.get("allow_par_file_patch", True):
        print("[trucksim_par] COM 不可用，且 allow_par_file_patch=false")
        return False
    simfile_path = trucksim.get("simfile_path")
    if not simfile_path:
        print("[trucksim_par] 未配置 trucksim.simfile_path，无法定位 Run_all.par")
        return False
    try:
        par_path = _resolve_simfile_input(simfile_path)
    except Exception as e:
        print("[trucksim_par] 解析 simfile.sim 失败: %s" % e)
        return False
    if not os.path.isfile(par_path):
        print("[trucksim_par] Run_all.par 不存在: %s" % par_path)
        return False

    mu = float(case.get("road_friction", 0.85))
    base_mu = float(trucksim.get("road_base_mu", 0.85))
    target_speed = float(case.get("target_speed_kmh") or case.get("initial_speed_kmh") or 0.0)
    updates = {
        PAR_KEYWORDS["stop_time_s"]: float(case["stop_time_s"]),
        PAR_KEYWORDS["initial_speed_kmh"]: float(case.get("initial_speed_kmh") or 0.0),
        PAR_KEYWORDS["target_speed_kmh"]: target_speed,
        PAR_KEYWORDS["road_friction"]: mu,
        PAR_KEYWORDS["road_friction_scale"]: mu / base_mu,
    }

    data_root = os.path.dirname(os.path.abspath(simfile_path))
    par_text = _read_text(par_path)
    linked_files = sorted(_linked_par_files(par_text, data_root),
                          key=lambda p: (_source_patch_priority(p, data_root), p.lower()))
    patch_files = [par_path] + linked_files

    total_counts = dict((k, 0) for k in updates)
    touched = []
    warnings = []
    for i, path in enumerate(patch_files):
        file_updates = updates if i == 0 else _source_updates_for(path, data_root, updates)
        if not file_updates:
            continue
        counts, _missing, backup_path, error = _patch_one_par_file(path, file_updates)
        if error:
            warnings.append((path, error))
            continue
        if any(counts.values()):
            touched.append((path, backup_path, counts))
            for keyword, count in counts.items():
                total_counts[keyword] += count

    missing = [k for k, v in total_counts.items()
               if v == 0 and k in ("TSTOP", "SPEED", "SPEED_TARGET_CONSTANT")]
    if missing:
        print("[trucksim_par] 关键字段未找到，未写入: %s" % ", ".join(missing))
        return False
    if not touched:
        print("[trucksim_par] 未找到可修改字段")
        return False

    print("[trucksim_par] 已修改 %d 个 par 文件" % len(touched))
    for path, backup_path, counts in touched:
        print("[trucksim_par] 文件: %s" % path)
        print("[trucksim_par] 备份: %s" % backup_path)
        for keyword, count in counts.items():
            if count:
                print("[trucksim_par]   %s 更新 %d 处" % (keyword, count))
    for path, error in warnings:
        print("[trucksim_par] 警告: 跳过无法写入的文件: %s (%s)" % (path, error))
    return True


def configure_trucksim(case, cfg):
    try:
        ts = _connect(cfg)
    except Exception as e:
        print("[trucksim_com] 未安装/无法使用 pywin32: %s，改用 simfile/Run_all.par 配置" % e)
        return _patch_run_all_par(case, cfg)
    if ts is None:
        print("[trucksim_com] 未找到可用 COM ProgID，改用 simfile/Run_all.par 配置")
        return _patch_run_all_par(case, cfg)

    run_name = cfg.get("trucksim", {}).get("run_name", RUN_NAME)
    try:
        run = ts.GetRunByName(run_name)
    except Exception as e:
        print("[trucksim_com] 定位 Run 失败(%s): %s" % (run_name, e))
        return False

    # ---- TXT 字段 -> TruckSim 关键字映射表 ----
    mu = float(case.get("road_friction", 0.85))
    base_mu = float(cfg.get("trucksim", {}).get("road_base_mu", 0.85))
    v_init = float(case.get("initial_speed_kmh") or 0.0)
    v_target = float(case.get("target_speed_kmh") or case.get("initial_speed_kmh") or 0.0)

    ok_all = True
    ok_all = _write_all(run, "仿真时长", _keywords(cfg, "stop_time_s"),
                        float(case["stop_time_s"])) and ok_all
    ok_all = _write_all(run, "初始车速", _keywords(cfg, "initial_speed_kmh"),
                        v_init) and ok_all
    ok_all = _write_all(run, "目标车速", _keywords(cfg, "target_speed_kmh"),
                        v_target) and ok_all
    ok_all = _write_all(run, "附着系数倍率", _keywords(cfg, "road_friction_scale"),
                        mu / base_mu) and ok_all
    ok_all = _write_all(run, "初始速度开关", _keywords(cfg, "init_speed_enable"),
                        1.0, required=False) and ok_all
    ok_all = _apply_scenario(run, case, cfg) and ok_all

    grade = float(case.get("road_grade", 0.0))
    grade_keywords = _keywords(cfg, "road_grade")
    if abs(grade) > 1e-9:
        ok_all = _write_all(run, "道路坡度", grade_keywords, grade) and ok_all
    elif grade_keywords:
        ok_all = _write_all(run, "道路坡度", grade_keywords, 0.0, required=False) and ok_all

    if not ok_all:
        print("[trucksim_com] 映射未全部验证通过，CONFIG_FAIL")
        return False

    print("[trucksim_com] 工况配置完成（TXT 字段已按 vehicle_config.yaml 映射写入并回读确认）")
    time.sleep(0.1)
    return True
