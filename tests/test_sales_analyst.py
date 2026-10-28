import ast
import re
import unittest
from pathlib import Path

import pandas as pd


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def load_answer_function():
    app_tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    answer_function = next(
        node for node in app_tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "answer_sales_question"
    )
    function_module = ast.Module(body=[answer_function], type_ignores=[])
    namespace = {"pd": pd, "re": re}
    exec(
        compile(function_module, str(APP_PATH), "exec"),
        namespace,
    )
    return namespace["answer_sales_question"]


class SalesAnalystRecommendationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.answer = staticmethod(load_answer_function())
        cls.data = pd.DataFrame({
            "date": pd.to_datetime([
                "2026-01-05",
                "2026-01-06",
                "2026-01-12",
                "2026-01-13",
            ]),
            "sales": [100.0, 40.0, 120.0, 60.0],
        })

    def test_recommendation_returns_three_testable_suggestions(self):
        response = self.answer(
            "How can I improve sales by product?",
            self.data,
        )

        self.assertIn("**What the data shows**", response)
        self.assertIn("**Suggestions to test**", response)
        self.assertIn("**1.", response)
        self.assertIn("**2.", response)
        self.assertIn("**3.", response)
        self.assertIn("baseline", response.lower())
        self.assertIn("profit", response.lower())
        self.assertIn("hypotheses", response.lower())
        self.assertIn("does not identify products or customers", response)

    def test_recommendation_uses_uploaded_weekday_facts_without_inventing(self):
        response = self.answer("Give me advice to boost sales", self.data)

        self.assertIn("Monday had the highest average recorded sales", response)
        self.assertIn("R 110.00", response)
        self.assertIn("Tuesday had the lowest average recorded sales", response)
        self.assertIn("R 50.00", response)
        self.assertNotIn("product X", response.lower())

    def test_unsupported_product_sales_breakdown_is_refused(self):
        response = self.answer(
            "What were my sales by product?",
            self.data,
        )

        self.assertIn("can't answer that breakdown reliably", response)
        self.assertNotIn("**Suggestions to test**", response)


if __name__ == "__main__":
    unittest.main()
