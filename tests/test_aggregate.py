import copy
import json
import math
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from htpm.aggregate import award_entry, event_estimate, stratified_event_estimate, score, sensitivity, shrink, validate
from htpm.aggregate_report import write_reports
from htpm.core import DataError
from htpm.event_tiers import classify

ROOT = Path(__file__).resolve().parents[1]


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "output/current/input.json").read_text(encoding="utf-8"))
        self.config = json.loads((ROOT / "output/current/config.json").read_text(encoding="utf-8"))

    def test_all_players_maps_reconcile_and_sources_exist(self):
        self.assertTrue(validate(self.data, self.config))
        self.assertEqual(len(self.data["players"]), 58)
        self.assertEqual(len(self.config["event_tiers"]), 23)

    def test_manual_shrink_and_empty_sample(self):
        self.assertAlmostEqual(shrink(1.2, 60, self.config)["adjusted"], 1.1625)
        empty = shrink(None, 0, self.config)
        self.assertIsNone(empty["raw_rating"])
        self.assertEqual(empty["adjusted"], 1.05)
        self.assertEqual(empty["shrinkage_weight"], 0)

    def test_weighted_aggregate_and_sample_size_by_hand(self):
        rows = [{"rating": 1.2, "maps": 10, "tier": "Major"}, {"rating": 1.0, "maps": 10, "tier": "Big"}]
        result = event_estimate(rows, self.config)
        expected_raw = (18*1.2+11*1.0)/29
        n_eff = 29**2/(10*1.8**2+10*1.1**2)
        self.assertAlmostEqual(result["raw_rating"], expected_raw)
        self.assertAlmostEqual(result["effective_maps"], n_eff)
        event_eff = 29**2/(18**2+11**2)
        reliability = n_eff/(n_eff+20)*event_eff/(event_eff+2)
        self.assertAlmostEqual(result["adjusted"], 1.05+reliability*(expected_raw-1.05))

    def test_event_cap_does_not_duplicate_maps(self):
        a = event_estimate([{"rating": 1.2, "maps": 100, "tier": "Major"}], self.config)
        self.assertEqual(a["maps"], 100)
        self.assertAlmostEqual(a["effective_maps"], 16)

    def test_missing_events_or_non_nested_counts_rejected(self):
        self.data["players"][0]["events"].pop()
        with self.assertRaises(DataError):
            validate(self.data, self.config)
        self.setUp()
        self.data["players"][0]["opponents"]["5"]["maps"] = 170
        with self.assertRaises(DataError):
            validate(self.data, self.config)

    def test_unknown_is_not_zero(self):
        self.data["players"][0]["opponents"]["5"]["rating"] = None
        with self.assertRaises(DataError):
            validate(self.data, self.config)

    def test_mvp_duplicate_and_rating_nan_rejected(self):
        self.data["players"][0]["awards"].append(copy.deepcopy(self.data["players"][0]["awards"][0]))
        with self.assertRaises(DataError):
            validate(self.data, self.config)
        self.setUp()
        self.data["players"][0]["annual"]["rating"] = math.nan
        with self.assertRaises(DataError):
            validate(self.data, self.config)

    def test_snapshot_cannot_be_used_as_past_observation(self):
        self.data["metadata"]["cutoff"] = "2026-06-01"
        with self.assertRaises(DataError):
            validate(self.data, self.config)

    def test_forced_tiers_and_weights(self):
        self.config["event_tiers"]["CS Asia Championships 2026"] = "Elite"
        with self.assertRaises(DataError):
            validate(self.data, self.config)
        self.setUp()
        self.config["weights"]["A"] = .4
        with self.assertRaises(DataError):
            validate(self.data, self.config)

    def test_medal_policy_distinguishes_similar_event_names(self):
        self.assertEqual(classify("BLAST Bounty 2026 Season 1 Finals", "silver"), "Big")
        self.assertEqual(classify("BLAST Bounty 2026 Season 2 Finals", "bronze"), "Medium")
        self.assertEqual(classify("PGL Bucharest 2026", "bronze"), "Medium")
        self.assertEqual(classify("PGL Masters Bucharest 2026", "silver"), "Big")
        self.assertEqual(classify("ESL Pro League Season 24", "silver"), "Elite")
        with self.assertRaises(ValueError):
            classify("Unverified event", "unknown")
        for name in ("IEM Rio 2026", "BLAST Bounty 2026 Season 2 Finals"):
            cfg = copy.deepcopy(self.config)
            cfg["event_tiers"][name] = "Elite"
            with self.assertRaises(DataError):
                validate(self.data, cfg)

    def test_fixed_tiers_are_preserved_by_sensitivity(self):
        result = sensitivity(self.data, self.config)
        self.assertEqual(result["scenario_count"], 30)
        self.assertFalse(any(name.startswith("uncertain_tiers")
                             for p in result["players"] for name in p["scenario_ranks"]))

    def test_missing_main_sample_cannot_rank(self):
        results = {p["id"]: p for p in score(self.data, self.config)["players"]}
        self.assertIsNone(results["vexite"]["rank"])
        self.assertIsNone(results["vexite"]["score"])
        self.assertIsNone(results["insani"]["rank"])
        self.assertIsNotNone(results["insani"]["score"])

    def test_individual_scores_do_not_depend_on_candidate_pool(self):
        before = score(self.data, self.config)["players"]
        original = next(p for p in before if p["id"] == "zywoo")
        self.data["players"] = [p for p in self.data["players"] if p["id"] == "zywoo"]
        after = score(self.data, self.config)["players"][0]
        self.assertEqual(original["score"], after["score"])

    def test_team_contribution_rewards_actual_performance_and_is_bounded(self):
        results = {p["id"]: p for p in score(self.data, self.config)["players"]}
        self.assertEqual(results["zywoo"]["title_count"], results["ropz"]["title_count"])
        self.assertNotEqual(results["zywoo"]["contributions"]["T"], results["ropz"]["contributions"]["T"])
        for p in results.values():
            self.assertTrue(0 <= p["contributions"]["T"] <= 5)
            if p["score"] is not None:
                self.assertAlmostEqual(p["score"], sum(p["contributions"].values()))

    def test_excluded_qualifier_does_not_create_team_honor(self):
        before = score(self.data, self.config)["players"]
        for p in self.data["players"]:
            for e in p["events"]:
                if not e["in_scope"]:
                    e["placement"] = "1st"
                    e["rating"] = 3
        after = score(self.data, self.config)["players"]
        self.assertEqual([p["score"] for p in before], [p["score"] for p in after])

    def test_sensitivity_does_not_mutate_inputs_and_report_links_resolve(self):
        before = copy.deepcopy((self.data, self.config))
        result = score(self.data, self.config)
        s = sensitivity(self.data, self.config)
        self.assertEqual((self.data, self.config), before)
        self.assertEqual(s["scenario_count"], 30)
        class Inspect(HTMLParser):
            ids, hrefs = [], []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if "id" in attrs:
                    self.ids.append(attrs["id"])
                if attrs.get("href", "").startswith("#"):
                    self.hrefs.append(attrs["href"][1:])
        with tempfile.TemporaryDirectory() as directory:
            write_reports(result, s, self.config, directory)
            text = (Path(directory)/"report.html").read_text(encoding="utf-8")
            parser = Inspect(); parser.feed(text)
            self.assertEqual(len(parser.ids), len(set(parser.ids)))
            self.assertTrue(set(parser.hrefs) <= set(parser.ids))
            self.assertNotIn("__NOTICE__", text)
            self.assertNotIn("NaN", text)
            self.assertEqual(len(parser.hrefs), len(result["players"]))

    def test_small_top5_peak_has_less_influence_than_large_sample(self):
        small = shrink(1.30, 6, self.config, 30)
        large = shrink(1.30, 60, self.config, 30)
        self.assertAlmostEqual(small["adjusted"], 1.0916666666666666)
        self.assertAlmostEqual(large["adjusted"], 1.2166666666666666)
        self.assertLess(small["shrinkage_weight"], large["shrinkage_weight"])

    def test_same_map_volume_across_events_more_reliable_than_one_peak(self):
        one = event_estimate([{"rating": 1.3, "maps": 32, "tier": "Elite"}], self.config)
        four = event_estimate([{"rating": 1.3, "maps": 8, "tier": "Elite"} for _ in range(4)], self.config)
        self.assertLess(one["shrinkage_weight"], four["shrinkage_weight"])
        self.assertLess(one["effective_events"], four["effective_events"])

    def test_low_tier_map_farming_cannot_increase_sample_quality_or_awards(self):
        before = {p["id"]: p for p in score(self.data, self.config)["players"]}
        p = self.data["players"][0]
        pid = p["id"]
        p["events"].append({"name": "Excluded test league", "maps": 200, "rating": 1.6,
                            "placement": "1st", "in_scope": False, "tier": None, "source": "https://example.test"})
        p["annual"]["maps"] += 200
        after = {p["id"]: p for p in score(self.data, self.config)["players"]}
        self.assertLess(after[pid]["modules"]["N"], before[pid]["modules"]["N"])
        self.assertEqual(after[pid]["modules"]["A"], before[pid]["modules"]["A"])
        self.assertEqual(after[pid]["modules"]["E"], before[pid]["modules"]["E"])

    def test_official_evp_order_used_and_cannot_be_unsubstantiated(self):
        result = {p["id"]: p for p in score(self.data, self.config)["players"]}
        major = lambda pid: next(a for a in result[pid]["awards"] if a["event"] == "IEM Cologne Major 2026")
        self.assertEqual(major("kyousuke")["points"], 14)
        self.assertEqual(major("niko")["points"], 12)
        a = next(a for p in self.data["players"] for a in p["awards"] if a.get("evp_rank"))
        a.pop("order_evidence")
        with self.assertRaises(DataError):
            validate(self.data, self.config)

    def test_bounty_discount_applies_only_to_honors_once(self):
        event = "BLAST Bounty 2026 Season 1 Finals"
        reduced = {p["id"]: p for p in score(self.data, self.config)["players"]}
        self.config["honor_factors"][event] = 1
        full = {p["id"]: p for p in score(self.data, self.config)["players"]}
        mvp = next(a for a in reduced["niko"]["awards"] if a["event"] == event)
        self.assertAlmostEqual(mvp["points"], 6.6)
        self.config["honor_factors"][event] = .6
        evp = award_entry({"event": event, "type": "EVP", "evp_rank": 1}, self.config)
        self.assertAlmostEqual(evp["points"], 4.8)
        for pid, p in reduced.items():
            for module in ("E", "O", "C", "N"):
                self.assertEqual(p["modules"][module], full[pid]["modules"][module])
            self.assertEqual(p["counts"], full[pid]["counts"])
            for t in p["team_ledger"]:
                original = next(x for x in full[pid]["team_ledger"] if x["event"] == t["event"])
                self.assertAlmostEqual(t["points"], original["points"]*(.6 if t["event"] == event else 1))

    def test_missing_elite_stratum_cannot_borrow_big_maps(self):
        events = [{"rating": 1.3, "maps": 16, "tier": "Big"} for _ in range(12)]
        stat = stratified_event_estimate(events, self.config)
        for tier in ("Major", "Super-elite", "Elite"):
            t = stat["tier_samples"][tier]
            self.assertEqual(t["adjusted"], 1.05)
            self.assertEqual(t["effective_weight"], 0)
            self.assertEqual(t["coverage"], 0)
        self.assertLessEqual(stat["shrinkage_weight"], .30)

    def test_stratum_manual_reliability_and_larger_sample(self):
        rows = [{"rating": 1.3, "maps": 12, "tier": "Major"}]
        a = stratified_event_estimate(rows, self.config)["tier_samples"]["Major"]
        self.assertAlmostEqual(a["shrinkage_weight"], .5*(1/1.5))
        self.assertAlmostEqual(a["adjusted"], 1.05+(1.3-1.05)/3)
        self.assertEqual(a["coverage"], 1)
        rows[0]["maps"] = 3
        b = stratified_event_estimate(rows, self.config)["tier_samples"]["Major"]
        self.assertLess(b["shrinkage_weight"], a["shrinkage_weight"])

    def test_evp_tail_and_non_candidate_first_place(self):
        p = next(p for p in self.data["players"] if p["id"] == "m0nesy")
        a = next(a for a in p["awards"] if a["event"] == "Esports World Cup 2026")
        self.assertEqual(a["evp_rank"], 2)
        self.assertEqual(award_entry(a, self.config)["points"], 8)
        points = [award_entry({"event": a["event"], "type": "EVP", "evp_rank": i}, self.config)["points"] for i in range(1, 15)]
        self.assertEqual(points, sorted(points, reverse=True))
        self.assertAlmostEqual(points[-1], 6*.75)
        a["evp_rank"] = 999
        with self.assertRaises(DataError):
            validate(self.data, self.config)

    def test_nested_groups_are_not_summed_as_independent_samples(self):
        for p in score(self.data, self.config)["players"]:
            self.assertEqual(sum(p["sample_quality"]["opponent_exclusive_maps"].values()), p["opponents"]["30"]["maps"])
            self.assertAlmostEqual(sum(o["effective_weight"] for o in p["opponents"].values()), p["effective_data_weights"]["O"])

    def test_invalid_honor_factor_and_impossible_target_rejected(self):
        self.config["honor_factors"]["BLAST Bounty 2026 Season 1 Finals"] = -.1
        with self.assertRaises(DataError):
            validate(self.data, self.config)
        self.setUp()
        self.config["tier_samples"]["Elite"]["target_events"] = 10
        with self.assertRaises(DataError):
            validate(self.data, self.config)


if __name__ == "__main__":
    unittest.main()
