import csv
import gzip
import json
import unittest
from collections import Counter
from datetime import date
from unittest.mock import patch

from analysis.compare_4_4 import SCENARIOS, compare, keyed
from htpm.core import fingerprint
from htpm.event_policy import attach_vps
from htpm.forecast_4_2 import calculate, publish, settings
from htpm.frozen_4_4 import configure, input_hashes
from htpm.pipeline import ROOT, load
from htpm.season import features, season_inputs

DAY = date(2026, 11, 17)
KR = "IEM Kraków 2026"
HK = "BLAST Rivals 2026 Season 2"
# Independent of the release configuration. Include both sides of each live map.
EXCLUDED = {
    (KR, "6258176"): (2389665, "placement", {"125292", "125294"}),
    (HK, "7313139"): (2400204, "quarterfinal", {"156054", "156055"}),
    (HK, "7313138"): (2400205, "quarterfinal", {"156056", "156057", "156058"}),
}


class FrozenSeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load("config/season_4_4.json")
        cls.old = calculate(today=DAY, model="4.3")
        cls.new = calculate(today=DAY, model="4.4")

    def test_both_live_releases_match_archives(self):
        self.assertEqual(publish(self.old, verify=True).parent.name, "e06ce6dc913e2ffb")
        publish(self.new, verify=True)
        self.assertEqual(self.old["scope"], self.new["scope"])
        self.assertEqual(len(self.new["scope"]), 23)
        self.assertEqual(self.new["majors"], ["IEM Cologne Major 2026"])
        self.assertEqual(self.new["cutoff"], DAY.isoformat())
        self.assertEqual(fingerprint(input_hashes()), self.config["input_hash"])
        with patch("htpm.frozen_4_4.input_hashes", return_value={}):
            with self.assertRaisesRegex(ValueError, "input hash"):
                configure({}, self.config, None)

    def test_every_map_and_unaffected_match(self):
        rules = self.config["stage_exceptions"]
        self.assertEqual({(r["event"], r["match"]): (r["hltv_match"], r["phase"], set(r["maps"]))
                          for r in rules}, EXCLUDED)
        old = season_inputs(2026, detailed_rosters=True)[2]
        new = season_inputs(2026, True, rules, True)[2]
        offsets, changed = Counter(), Counter()
        with gzip.open(ROOT/"data/2026/stage_maps.csv.gz", "rt", encoding="utf8") as stream:
            for r in csv.DictReader(stream):
                event, pid = r["event"], r["player"].casefold()
                idx = offsets[pid, event]
                offsets[pid, event] += 1
                a, b = old[pid][event][idx], new[pid][event][idx]
                self.assertEqual((a[0], a[2], a[4:7]), (b[0], b[2], b[4:7]))
                self.assertEqual(a[1], r["stage"])
                self.assertEqual(b[3], int(r["opponent_rank"]) if r["opponent_rank"] else None)
                match = (event, r["match"])
                if match in EXCLUDED:
                    _, phase, maps = EXCLUDED[match]
                    self.assertIn(r["map"], maps)
                    self.assertEqual((a[1], b[1], b[2]), ("playoff", phase, "arena"))
                    changed[match, r["map"]] += 1
                else:
                    self.assertEqual(a[1], b[1])
        self.assertEqual(changed, {(match, m): 10 for match, (_, _, maps) in EXCLUDED.items() for m in maps})
        self.assertEqual(sum(offsets.values()), sum(len(rows) for e in new.values() for rows in e.values()))

    def test_all_downstream_slices(self):
        old = keyed(self.old)
        deltas = Counter()
        for b in self.new["players"]:
            a = old[b["id"]]
            for k in ("main", "arena", "final", "won", "top5", "top10"):
                self.assertEqual(a["details"][k], b["details"][k])
            for k in ("playoff", "elite_playoff", "big_playoff", "pressure_top10"):
                loss = a["details"][k]["maps"] - b["details"][k]["maps"]
                self.assertGreaterEqual(loss, 0)
                deltas[k] += loss
            for k in ("E", "C", "T", "R"):
                self.assertEqual(a["contributions"][k], b["contributions"][k])
            for tier, cells in b["tier_stages"].items():
                self.assertEqual(cells["all"], a["tier_stages"][tier]["all"])
                self.assertEqual(cells["all"]["maps"], sum(cells[k]["maps"] for k in
                                 ("group", "playoff", "placement", "quarterfinal_outside_filter")))
        self.assertEqual(deltas["playoff"], 70)
        self.assertEqual(deltas["elite_playoff"], 20)
        self.assertEqual(deltas["big_playoff"], 70)
        self.assertGreater(deltas["pressure_top10"], 0)
        for key in ("A", "K", "P", "N", "H"):
            self.assertTrue(any(old[b["id"]]["contributions"][key] != b["contributions"][key]
                                for b in self.new["players"]))

    def test_vrs_disjoint_scores_and_missingness(self):
        config = self.config
        for p in self.new["players"]:
            coverage = p["vrs_coverage"]
            self.assertEqual(coverage["total"], sum(coverage[k] for k in ("top5","six_to_ten","unmatched","known_outside")))
            self.assertEqual(coverage["known_outside"], 0)  # No explicit rank >10 in this top-ten archive.
            expected = 0
            for band, field in (("1-5", "top5"), ("6-10", "vrs_6_10")):
                d = p["details"][field]
                n, prior = d["maps"], config["opponent_bands"][band]["prior_maps"]
                value = (n * (d["index"] or 0) + prior * 50) / (n + prior)
                expected += config["opponent_bands"][band]["share"] * value
            self.assertAlmostEqual(p["features"]["O"], min(100, max(0, expected)))
        # A positively identified outside rank must survive as a distinct coverage class.
        inputs = season_inputs(2026, True, config["stage_exceptions"], True)
        rows = inputs[2]["ropz"][HK]
        changed = rows[0][:3] + (17,) + rows[0][4:]
        rows[0] = changed
        c = {**settings()[1], **load("config/season_4_3.json"), **config}
        players = {p["id"]: p for p in features(inputs, load("config/model.json"), c, 2026)}
        self.assertEqual(players["ropz"]["vrs_coverage"]["known_outside"], 1)
        self.assertGreater(players["ropz"]["vrs_coverage"]["unmatched"], 0)

    def test_vp_and_hong_kong_award_order(self):
        inputs = season_inputs(2026, detailed_rosters=True)
        record, = load("data/reference/official_vps_4_3.json")["2026"]
        a = inputs[1][record["event"]]
        for records in ([record, record], [dict(record, player=a["mvp"])],
                        [dict(record, player=a["evps"][0])], [dict(record, grade="honorable mention")]):
            with self.assertRaises(ValueError):
                attach_vps(inputs, records, DAY.isoformat())
        people = keyed(self.new)
        self.assertEqual(self.new["confirmed_vps"], 1)
        jame = people["jame"]
        vp, = [a for a in jame["awards"] if a["event"] == record["event"]]
        self.assertEqual(vp["kind"], "VP")
        self.assertEqual(next(e["event_credit"] for e in jame["events"] if e["event"] == record["event"]), 0)
        order = sorted((a["position"] or 0, p["id"]) for p in people.values() for a in p["awards"] if a["event"] == HK)
        self.assertEqual([pid for _, pid in order], ["kscerato","molodoy","donk","ropz","m0nesy"])
        with (ROOT/"output/comparison_4_4/award_rating.csv").open(encoding="utf-8-sig", newline="") as f:
            evidence = [r for r in csv.DictReader(f) if r["event"] == HK and r["id"] == "ropz"]
        self.assertEqual([(e["evp_order"], e["event_rating"], e["maps"], e["placement"]) for e in evidence],
                         [("3", "1.32", "7", "5-6th")])

    def test_published_comparison_covers_every_id_and_scenario(self):
        dest = ROOT/"output/comparison_4_4"
        manifest = json.loads((dest/"manifest.json").read_text(encoding="utf8"))
        live = {r["id"]: r for r in compare(self.old, self.new)}
        with (dest/"comparison.csv").open(encoding="utf-8-sig", newline="") as stream:
            written = list(csv.DictReader(stream))
        self.assertEqual(len(written), 177)
        self.assertEqual(set(live), {r["id"] for r in written})
        self.assertEqual(fingerprint(sorted(live)), manifest["cohort_hash"])
        self.assertEqual(manifest["natural_additions"] + manifest["natural_losses"], [])
        for row in written:
            item = live[row["id"]]
            for key, value in item.items():
                self.assertEqual(row[key], str(value))
            for tag in SCENARIOS:
                self.assertTrue(1 <= int(row[tag+"_rank"]) <= 177)
            self.assertAlmostEqual(sum(float(row[k+"_delta"]) for k in "AEOKPTCNHR"), float(row["score_delta"]))
            self.assertAlmostEqual(sum(float(row[k]) for k in ("stage_only_delta", "opponent_only_delta",
                                                                "joint_interaction")), float(row["score_delta"]))
            self.assertAlmostEqual(float(row["no_HR_score"]), item["new_score"] - item["H_new"] - item["R_new"])
        for tag in SCENARIOS:
            self.assertEqual(sorted(int(r[tag+"_rank"]) for r in written), list(range(1, 178)))
        self.assertEqual(set(json.loads((dest/"hltv_opponents.json").read_text(encoding="utf8"))), set(live))

    def test_undoing_both_score_changes_recovers_every_4_3_score(self):
        revision = {**self.config, "stage_exceptions": []}
        real_load = load
        def rollback(name):
            return revision if name == "config/season_4_4.json" else real_load(name)
        with patch("htpm.forecast_4_2.load", side_effect=rollback):
            result = calculate(today=DAY, model="4.4", scenario="nested_opponents")
        old = keyed(self.old)
        self.assertEqual(set(old), set(keyed(result)))
        for p in result["players"]:
            self.assertEqual(old[p["id"]]["contributions"], p["contributions"])
            self.assertEqual(old[p["id"]]["rank"], p["rank"])
