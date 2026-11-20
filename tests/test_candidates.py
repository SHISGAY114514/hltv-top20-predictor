import copy
import json
import unittest
from pathlib import Path
from html.parser import HTMLParser
from htpm.pipeline import prepare
from htpm.candidates import build_candidates
from htpm.core import fingerprint

ROOT = Path(__file__).resolve().parents[1]


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.data, self.config, self.pool = prepare()
        self.players = {p["id"]: p for p in self.pool["candidates"]}

    def test_every_award_recipient_is_included_without_statistics_gate(self):
        awards = json.loads((ROOT/"data/2026/award_snapshot.json").read_text(encoding="utf-8"))["awards"]
        self.assertEqual({a["player_id"] for a in awards}, {p["id"] for p in self.players.values() if p["membership"] == "award_candidate"})
        self.assertEqual(len(self.players), 58)
        self.assertEqual(self.pool["award_candidate_count"], 55)
        self.assertEqual(sum(p["mvp_count"] for p in self.players.values()), 23)
        self.assertEqual(sum(p["evp_count"] for p in self.players.values()), 124)
        self.assertEqual(self.pool["pending_statistics_count"], 0)

    def test_new_players_have_current_statistics_and_registry_is_not_a_ranking(self):
        for pid in ("try", "xfl0ud", "tenzy", "rez", "nertz", "nota"):
            p = self.players[pid]
            self.assertEqual(p["statistics_status"], "available")
            self.assertIsNone(p["total_score"])
            self.assertIsNone(p["rank"])
            self.assertEqual(p["statistics_as_of"], "2026-11-17")
        self.assertEqual(self.players["try"]["awards"][0]["evp_rank"], 1)
        self.assertEqual(self.players["try"]["award_points"], 10)
        self.assertEqual(self.players["try"]["group"], "priority")
        self.assertAlmostEqual(self.players["nota"]["award_points"], 4.8)

    def test_missing_statistics_never_remove_award_candidate_or_impute_score(self):
        awards = [a for p in self.players.values() for a in p["awards"]]
        stats = [p for p in self.data["players"] if p["id"] != "try"]
        pool = build_candidates(awards, stats, self.config, ["jamyoung", "senzu", "vexite"])
        p = next(p for p in pool["candidates"] if p["id"] == "try")
        self.assertEqual(pool["pending_statistics_count"], 1)
        self.assertEqual(p["statistics_status"], "pending_collection")
        for key in ("rank", "total_score", "statistics_as_of"):
            self.assertIsNone(p[key])

    def test_watchlist_is_separate_and_candidate_registry_is_bound_to_input(self):
        self.assertEqual({p["id"] for p in self.players.values() if p["membership"] == "watchlist"}, {"jamyoung", "senzu", "vexite"})
        self.assertEqual(fingerprint(self.pool), self.data["metadata"]["candidate_pool_sha256"])
        self.assertTrue({p["id"] for p in self.data["players"]} <= set(self.players))

    def test_duplicate_awards_rejected(self):
        awards = [a for p in self.players.values() for a in p["awards"]]
        awards.append(copy.deepcopy(awards[0]))
        with self.assertRaises(ValueError):
            build_candidates(awards, self.data["players"], self.config, [])

    def test_current_artifact_local_links_and_placeholders(self):
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.hrefs = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and attrs.get("href"):
                    self.hrefs.append(attrs["href"])
        for name in ("report.html", "candidates.html", "bounty.html", "evaluation.html"):
            path = ROOT/"output/current"/name
            text = path.read_text(encoding="utf-8")
            parser = Links(); parser.feed(text)
            self.assertNotIn("__NOTICE__", text)
            self.assertNotIn("__COVERAGE__", text)
            self.assertNotIn("comparison.html", text)
            for href in parser.hrefs:
                if not href.startswith(("http", "#")):
                    self.assertTrue((path.parent/href.split("#")[0]).is_file(), href)


if __name__ == "__main__":
    unittest.main()
