import copy
import json
import unittest
from pathlib import Path

from htpm.aggregate import score, sensitivity, validate
from htpm.core import DataError
from htpm.evaluation import explain
from htpm.pipeline import prepare

ROOT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.config, cls.pool = prepare()
        cls.result = score(cls.data, cls.config)
        cls.explanations = explain(cls.result, sensitivity(cls.data, cls.config))

    def test_entire_pool_evaluated_and_twenty_selected(self):
        self.assertEqual({p["id"] for p in self.explanations}, {p["id"] for p in self.pool["candidates"]})
        self.assertEqual(sum(p["selected"] for p in self.explanations), 20)
        for p in self.explanations:
            self.assertGreaterEqual(len(p["paragraphs"]), 6)
            if not p["eligible"]:
                self.assertIsNone(p["rank"])
                self.assertFalse(p["selected"])
                self.assertFalse(p["comparisons"])

    def test_adjacent_contributions_explain_exact_score_gaps(self):
        people = {p["id"]: p for p in self.result["players"]}
        for p in self.explanations:
            for comparison in p["comparisons"]:
                other = people[comparison["other_id"]]
                self.assertEqual(abs(p["rank"]-other["rank"]), 1)
                self.assertAlmostEqual(sum(comparison["module_deltas"].values()), comparison["score_delta"])
                self.assertAlmostEqual(p["score"]-other["score"], comparison["score_delta"])

    def test_stale_player_cannot_silently_enter_new_snapshot(self):
        data = copy.deepcopy(self.data)
        data["players"][0]["retrieved_on"] = "2026-11-15"
        with self.assertRaises(DataError):
            validate(data, self.config)

    def test_generated_results_reproduce_from_current_sources(self):
        saved = json.loads((ROOT/"output/current/scores.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, self.result)
        explained = json.loads((ROOT/"output/current/evaluation.json").read_text(encoding="utf-8"))
        self.assertEqual(explained["players"], self.explanations)
        for name in ("report.html", "evaluation.html"):
            text = (ROOT/"output/current"/name).read_text(encoding="utf-8")
            self.assertIn("2026-11-17", text)
            self.assertNotIn("截至2026-11-15", text)
            self.assertNotIn("已采集子集评分", text)


if __name__ == "__main__":
    unittest.main()
