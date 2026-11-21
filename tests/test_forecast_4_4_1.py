import csv
import unittest

from analysis.compare_4_4 import keyed
from htpm.forecast_4_2 import calculate, publish
from htpm.pipeline import ROOT, load


class EvidenceRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = calculate(model="4.4")
        cls.new = calculate(model="4.4.1")
        cls.people = keyed(cls.new)

    def test_frozen_output_and_fixed_cohort(self):
        self.assertEqual(publish(self.old, verify=True).parent.name, self.new["baseline_snapshot"])
        self.assertEqual(self.new["scope"], self.old["scope"])
        self.assertEqual(self.new["input_hash"], self.old["input_hash"])
        self.assertEqual(self.new["cutoff"], "2026-11-17")
        publish(self.new, verify=True)
        old = keyed(self.old)
        eligible = {pid for pid, p in old.items() if p["eligible"]}
        self.assertEqual(eligible, {pid for pid, p in self.people.items() if p["eligible"]})
        with (ROOT/"output/comparison_4_4_1/comparison.csv").open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 177)
        self.assertEqual({r["id"] for r in rows}, eligible)
        for r in rows:
            p = self.people[r["id"]]
            self.assertEqual(int(r["new_rank"]), p["rank"])
            self.assertEqual(p["snapshot_rank"], int(r["old_rank"]))
            self.assertAlmostEqual(p["score"], float(r["new_score"]))
            self.assertAlmostEqual(sum(float(r[k+"_delta"]) for k in p["contributions"]), float(r["delta"]))

    def test_community_table_is_inspectable_and_reversible(self):
        restored = keyed(calculate(model="4.4.1", scenario="restore_R"))
        for pid, p in self.people.items():
            a = restored[pid]
            self.assertEqual(p["contributions"]["R"], 0)
            self.assertEqual(p["published"], a["published"])
            self.assertAlmostEqual(a["score"]-p["score"], a["contributions"]["R"])
        self.assertEqual(sum(p["published"] is not None for p in self.people.values() if p["eligible"]), 39)
        self.assertTrue(any(p["contributions"]["R"] for p in restored.values()))

    def test_partial_ratings_never_create_stage_or_opponent_maps(self):
        matched = keyed(calculate(model="4.4.1", scenario="matched_only"))
        catalog = {e["event"]: e for e in load("data/reference/season_stage_catalog.json")["2026"]}
        for p in self.people.values():
            a = matched[p["id"]]
            self.assertEqual(p["tier_stages"], a["tier_stages"])
            self.assertEqual(p["details"], a["details"])
            for k in ("O","K","C","N"):
                self.assertEqual(p["features"][k], a["features"][k])
            for e in p["events"]:
                x = e.get("whole_event_observation")
                if x:
                    self.assertEqual(x["archived_maps"], e["maps"])
                    self.assertLess(e["maps"], x["maps"])
                    self.assertIsNone(catalog[e["event"]]["start"])
                    self.assertIsNone(e["event_rating"])  # The map-aligned Rating remains unavailable.
        for pid, event, expected in (
            ("kscerato", "Thunderpick World Championship 2026", (11,12,1.34)),
            ("flamez", "BLAST Open Rotterdam 2026", (10,11,1.46)),
        ):
            e = next(e for e in self.people[pid]["events"] if e["event"] == event)
            x = e["whole_event_observation"]
            self.assertEqual((e["maps"],x["maps"],x["rating"]), expected)

    def test_published_awards_keep_order_and_updated_evidence(self):
        for record in load("config/season_4_4_1.json")["first_evp_evidence"]:
            a = next(a for a in self.people[record["player"]]["awards"] if a["event"] == record["event"])
            self.assertEqual((a["kind"], a["position"]), ("EVP",1))
            self.assertEqual(a["first_evp_context"], record)
            if record["signal"] == "clear":
                self.assertEqual(a["proximity_points"], 0)
        for name, current in self.new["event_weights"].items():
            old = self.old["event_weights"][name]
            self.assertEqual(current["event_factor"], old["event_factor"])
            self.assertEqual(current["tier"], old["tier"])
        def honors(player):
            return [(a["event"], a["kind"], a.get("position")) for a in player["awards"]]
        for pid, p in keyed(self.old).items():
            self.assertEqual(honors(p), honors(self.people[pid]))
