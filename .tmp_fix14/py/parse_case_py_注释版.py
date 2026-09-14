# -*- coding: utf-8 -*-
"""阶段二 TXT 测试用例解析（Python 版）。（本文件为逐行注释版，运行请用 parse_case_py.py）
与 01_一键启动脚本/parse_case.m 保持相同语义：
- 支持 # 注释与空行；
- key = value 格式；
- 必填字段与数值范围校验；
- 文件名与 case_name 一致性提示。
"""
import os                                   # 导入 os 模块（用于文件路径判断）


REQUIRED = {                                # 必填字段定义：字段名 -> (类型, 下限, 上限) 或 None
    "schema_version": (int, 1, 99),         # 用例格式版本
    "case_name": None,                      # 工况名称（字符串，不校验数值）
    "stop_time_s": (float, 0.0, 1e6),       # 仿真时长
    "initial_speed_kmh": (float, 0.0, 500.0),  # 初始车速
    "steer_input_type": None,               # 转向输入类型（字符串）
}

OPTIONAL = {                                # 可选字段定义（有则校验）
    "source_case_id": str,                  # 来源标准工况编号
    "trucksim_scenario": str,               # TruckSim 场景名
    "description": str,                     # 工况说明
    "target_speed_kmh": (float, 0.0, 500.0),   # 目标车速
    "steer_amplitude_deg": (float, -90.0, 90.0),  # 转向幅值
    "steer_frequency_hz": (float, 0.0, 100.0),   # 正弦频率
    "steer_start_time_s": (float, 0.0, 1e6),     # 转向开始时间
    "road_friction": (float, 0.0, 1.5),     # 路面附着系数
    "road_grade": (float, -90.0, 90.0),     # 道路坡度
    "controller_mode": str,                 # 控制器模式
    "control_dt_s": (float, 1e-4, 1.0),     # 控制周期
    "kp_beta": (float, -10.0, 10.0),        # β 比例增益
    "ki_beta": (float, -10.0, 10.0),        # β 积分增益
    "max_steer_deg": (float, 0.0, 90.0),    # 转角限幅
}


def parse_case(txt_file, check_name=True):  # 主解析函数：输入用例路径，返回字典；check_name 控制是否校验文件名
    if not os.path.isfile(txt_file):        # 如果文件不存在
        raise FileNotFoundError("用例文件不存在: %s" % txt_file)  # 抛异常
    c = {}                                  # 结果字典
    with open(txt_file, "r", encoding="utf-8-sig") as f:  # 打开文件（utf-8-sig 自动去 BOM）
        for raw in f:                       # 逐行读取
            line = raw.strip()              # 去掉首尾空白
            if not line or line.startswith("#"):  # 空行或注释行
                continue                    # 跳过
            if "=" not in line:             # 没有等号的行
                continue                    # 跳过
            key, _, val = line.partition("=")  # 按第一个等号切分
            key = key.strip()               # key 去空白
            val = val.strip()               # value 去空白
            if not key.replace("_", "").isalnum():  # 非法 key（含非字母数字下划线）
                continue                    # 跳过
            c[key] = val                    # 存入字典（值保持字符串）

    missing = [k for k in REQUIRED if k not in c]  # 找出缺失的必填字段
    if missing:                             # 如果有缺失
        raise ValueError("缺少必填字段: %s" % ", ".join(missing))  # 抛异常

    for key, spec in REQUIRED.items():      # 校验必填字段
        if spec is not None and key in c:   # 若定义了数值范围且字段存在
            _check(key, c[key], spec)       # 调用校验函数
    for key, spec in OPTIONAL.items():      # 校验可选字段
        if key in c:                        # 若字段存在
            _check(key, c[key], spec)       # 调用校验函数

    if check_name:                          # 仅当需要校验时
        base = os.path.splitext(os.path.basename(txt_file))[0]  # 文件名主体（去扩展名）
        if c["case_name"] != base:          # 若文件名与 case_name 不一致
            print("[警告] 文件名(%s)与 case_name(%s)不一致" % (base, c["case_name"]))  # 提示

    c["steer_input_type"] = c["steer_input_type"].lower()  # 转向类型转小写统一
    return c                                # 返回解析结果


def _check(key, val, spec):                 # 子函数：数值范围校验
    if not isinstance(spec, tuple):         # 若 spec 不是 (类型,下限,上限) 元组
        return  # 字符串字段，不做数值范围校验  # 直接返回
    cast, lo, hi = spec                     # 解包：类型、下限、上限
    try:                                    # 尝试转换
        v = cast(val)                       # 把字符串转成指定类型
    except (TypeError, ValueError):         # 转换失败
        raise ValueError("字段 %s 的值 %r 不是有效数值" % (key, val))  # 抛异常
    if v < lo or v > hi:                    # 若超出范围
        raise ValueError("字段 %s 的值 %r 超出范围 [%s, %s]" % (key, val, lo, hi))  # 抛异常


if __name__ == "__main__":                  # 直接运行时执行（方便单独测试）
    import sys                              # 导入 sys
    print(parse_case(sys.argv[1]))          # 打印解析第一个命令行参数对应的用例
