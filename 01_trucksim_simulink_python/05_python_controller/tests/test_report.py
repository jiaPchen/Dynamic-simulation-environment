# -*- coding: utf-8 -*-
"""阶段二报告结论与指标文件的离线回归测试。"""
import csv
import os
import sys
import tempfile

from docx import Document

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "report"))

from make_report_python import add_case_content, metrics, write_metrics_csv  # noqa: E402


def main():
    case = {
        "case_name": "synthetic", "run_status": "COMPLETED",
        "initial_speed_kmh": "40", "stop_time_s": "20",
        "steer_input_type": "step", "control_dt_s": "0.01",
        "tcp_integrity_status": "LISTENING|HANDSHAKE_OK|STOP_OK|SERVER_STOPPED",
        "trucksim_config_status": "CONFIG_READY",
    }
    rows = []
    for idx in range(2001):
        rows.append({"t": idx * 0.01, "Vx_kmh": 40.0, "beta_deg": 0.0,
                     "w_degps": 0.0, "delta1_deg": 3.0 if idx >= 100 else 0.0,
                     "delta2_deg": 0.1 if idx >= 100 else 0.0,
                     "delta3_deg": 0.5 if idx >= 100 else 0.0, "fb_deg": 0.0})
    metric_values = metrics(rows, case)
    with tempfile.TemporaryDirectory(prefix="p2_report_test_") as tmp:
        doc = Document()
        add_case_content(doc, "synthetic_run", case, metric_values, tmp)
        doc.save(os.path.join(tmp, "report.docx"))
        csv_path = os.path.join(tmp, "synthetic_run_metrics.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["metric", "value", "unit"])
            writer.writerow(["custom_trace", "preserve_me", ""])
        csv_path = write_metrics_csv(tmp, "synthetic_run", metric_values)
        with open(csv_path, encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        assert ["acceptance_status", "NOT_EVALUATED", ""] in rows
        assert ["execution_status", "PASS", ""] in rows
        assert ["sample_count", "2001", "count"] in rows
        assert ["max_abs_delta2", "0.1", "deg"] in rows
        assert ["custom_trace", "preserve_me", ""] in rows
        assert os.path.isfile(os.path.join(tmp, "report.docx"))
    print("报告结论与指标回归测试通过 [OK]")


if __name__ == "__main__":
    main()
