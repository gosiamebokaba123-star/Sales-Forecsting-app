import ast
import math
import unittest
from pathlib import Path

import pandas as pd


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def load_target_function():
    app_tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    target_function = next(
        node for node in app_tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "calculate_sales_target"
    )
    function_module = ast.Module(body=[target_function], type_ignores=[])
    namespace = {"math": math, "pd": pd}
    exec(
        compile(function_module, str(APP_PATH), "exec"),
        namespace,
    )
    return namespace["calculate_sales_target"]


class SalesActionPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calculate_target = staticmethod(load_target_function())

    def test_calculates_ten_percent_target_per_recorded_date(self):
        data = pd.DataFrame({"sales": [100.0, 200.0, 300.0]})

        result = self.calculate_target(data, 10)

        self.assertAlmostEqual(result["historical_average"], 200.0)
        self.assertAlmostEqual(result["target_average"], 220.0)
        self.assertAlmostEqual(result["additional_per_date"], 20.0)

    def test_zero_sales_baseline_has_zero_target_and_gap(self):
        data = pd.DataFrame({"sales": [0.0, 0.0]})

        result = self.calculate_target(data, 10)

        self.assertEqual(result["historical_average"], 0.0)
        self.assertEqual(result["target_average"], 0.0)
        self.assertEqual(result["additional_per_date"], 0.0)

    def test_rejects_negative_nonfinite_and_non_numeric_percentages(self):
        data = pd.DataFrame({"sales": [100.0]})

        for invalid_percentage in (-1, float("nan"), float("inf"), "ten"):
            with self.subTest(improvement_pct=invalid_percentage):
                with self.assertRaises(ValueError):
                    self.calculate_target(data, invalid_percentage)

    def test_rejects_empty_or_invalid_sales_data(self):
        invalid_data = [
            pd.DataFrame({"sales": []}),
            pd.DataFrame({"amount": [10.0]}),
            pd.DataFrame({"sales": [float("nan")]}),
            pd.DataFrame({"sales": [float("inf")]}),
            pd.DataFrame({"sales": [-1.0]}),
        ]

        for data in invalid_data:
            with self.subTest(data=data.to_dict()):
                with self.assertRaises(ValueError):
                    self.calculate_target(data, 10)


if __name__ == "__main__":
    unittest.main()
