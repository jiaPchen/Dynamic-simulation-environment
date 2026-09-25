# -*- coding: utf-8 -*-
"""阶段二道路坡度/场景配置的离线回归测试。"""
import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from trucksim.trucksim_com import _patch_run_all_par, _read_text, ROAD_BEGIN  # noqa: E402


RUN_ALL = """PARSFILE
TSTOP 10
SPEED 20
SPEED_TARGET_CONSTANT 20
MY_FRICTION 1
ENTER_PARSFILE Roads\\3D_Road\\Road_example.par
SET_IROAD_FOR_ID 0
CURRENT_ROAD_ID = ROAD_ID
ENTER_PARSFILE Roads\\BuilderSegment\\RoadSeg_example.par
SEGMENT_LENGTH 100
EXIT_PARSFILE Roads\\BuilderSegment\\RoadSeg_example.par
ROAD_PATH_ID = PATH_ID
set_description road_path_id PATH_ID for: Straight Path East
ENTER_PARSFILE Roads\\Friction\\RdMu_example.par
MU_ROAD_CONSTANT 0.85
EXIT_PARSFILE Roads\\Friction\\RdMu_example.par
EXIT_PARSFILE Roads\\3D_Road\\Road_example.par
END
"""


class RoadConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        data_dir = self.tmp.name
        result_dir = os.path.join(data_dir, "Results", "Run_stage2")
        os.makedirs(result_dir)
        self.par_path = os.path.join(result_dir, "Run_all.par")
        self.sim_path = os.path.join(data_dir, "simfile_phase2.sim")
        with open(self.par_path, "w", encoding="utf-8") as f:
            f.write(RUN_ALL)
        with open(self.sim_path, "w", encoding="utf-8") as f:
            f.write("INPUT Results\\Run_stage2\\Run_all.par\n")
        self.cfg = {"trucksim": {
            "simfile_path": self.sim_path,
            "allow_par_file_patch": True,
            "road_base_mu": 0.85,
            "scenario_map": {
                "straight_road": {"road_elevation": "uniform_grade"},
                "hill_20deg": {"road_elevation": "hill_20deg"},
            },
        }}
        self.case = {"stop_time_s": "12", "initial_speed_kmh": "30",
                     "target_speed_kmh": "30", "road_friction": "0.7",
                     "road_grade": "5", "trucksim_scenario": "straight_road"}

    def test_uniform_grade_then_flat_resets_previous_case(self):
        self.assertTrue(_patch_run_all_par(self.case, self.cfg))
        text = _read_text(self.par_path)
        self.assertIn("ROAD_ZS_COEFFICIENT 0.05", text)
        self.assertIn("MY_FRICTION 0.823529411764706", text)
        self.assertEqual(text.count(ROAD_BEGIN), 1)
        self.case["road_grade"] = "0"
        self.assertTrue(_patch_run_all_par(self.case, self.cfg))
        text = _read_text(self.par_path)
        self.assertIn("ROAD_ZS_COEFFICIENT 0", text)
        self.assertNotIn("ROAD_ZS_COEFFICIENT 0.05", text)
        self.assertEqual(text.count(ROAD_BEGIN), 1)

    def test_hill_scenario_and_conflicting_grade(self):
        self.case["trucksim_scenario"] = "hill_20deg"
        self.case["road_grade"] = "0"
        self.assertTrue(_patch_run_all_par(self.case, self.cfg))
        text = _read_text(self.par_path)
        self.assertIn("ROAD_ZS_TABLE SPLINE", text)
        self.assertIn("104, 35.154", text)
        self.case["road_grade"] = "5"
        self.assertFalse(_patch_run_all_par(self.case, self.cfg))
        self.assertEqual(_read_text(self.par_path), text)

    def test_unknown_scenario_fails_without_writing(self):
        self.case["trucksim_scenario"] = "unconfigured_road"
        self.assertFalse(_patch_run_all_par(self.case, self.cfg))
        self.assertEqual(_read_text(self.par_path), RUN_ALL)

    def test_missing_solver_keyword_fails_without_writing(self):
        incomplete = RUN_ALL.replace("MY_FRICTION 1\n", "")
        with open(self.par_path, "w", encoding="utf-8") as f:
            f.write(incomplete)
        self.assertFalse(_patch_run_all_par(self.case, self.cfg))
        self.assertEqual(_read_text(self.par_path), incomplete)

    def test_independent_initial_speed_is_not_silently_claimed(self):
        self.case["target_speed_kmh"] = "0"
        self.assertFalse(_patch_run_all_par(self.case, self.cfg))
        self.assertEqual(_read_text(self.par_path), RUN_ALL)

    def test_real_run_shape_with_speed_only_in_procedure(self):
        procedure_dir = os.path.join(self.tmp.name, "Procedures")
        os.makedirs(procedure_dir)
        procedure_path = os.path.join(procedure_dir, "Proc_example.par")
        with open(procedure_path, "w", encoding="utf-8") as f:
            f.write("PARSFILE\n*SPEED 20\nTSTOP 10\nSPEED_TARGET_CONSTANT 20\nEND\n")
        expanded = RUN_ALL.replace("SPEED 20\n", "").replace(
            "ENTER_PARSFILE Roads\\3D_Road\\Road_example.par",
            "ENTER_PARSFILE Procedures\\Proc_example.par\n"
            "TSTOP 10\nSPEED_TARGET_CONSTANT 20\n"
            "EXIT_PARSFILE Procedures\\Proc_example.par\n"
            "ENTER_PARSFILE Roads\\3D_Road\\Road_example.par")
        with open(self.par_path, "w", encoding="utf-8") as f:
            f.write(expanded)
        self.assertTrue(_patch_run_all_par(self.case, self.cfg))
        self.assertIn("ROAD_ZS_COEFFICIENT 0.05", _read_text(self.par_path))
        self.assertIn("*SPEED 30", _read_text(procedure_path))


if __name__ == "__main__":
    unittest.main()
