import unittest
from copy import deepcopy

from analysis.compare_4_4 import keyed
from htpm.forecast_4_2 import calculate
from htpm.pipeline import load
from htpm.season import apply_year_end_peak_context


class YearEndPeakTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = keyed(calculate(model="4.4.1"))
        cls.new = keyed(calculate(model="4.4.2"))

    def test_scope_and_attribution(self):
        self.assertEqual(self.old.keys(), self.new.keys())
        changed_ranks = set()
        for pid, old in self.old.items():
            new = self.new[pid]
            self.assertEqual(old["eligible"], new["eligible"])
            self.assertEqual(old["awards"], new["awards"])
            if old["rank"] != new["rank"]:
                changed_ranks.add(pid)
            for part, points in old["contributions"].items():
                if pid != "flamez" or part not in ("P", "H"):
                    self.assertEqual(points, new["contributions"][part])
        self.assertEqual(changed_ranks, {"flamez", "ropz"})
        self.assertEqual([self.new[p]["rank"] for p in ("kscerato", "ropz", "flamez")], [4, 5, 6])
        self.assertGreater(self.new["ropz"]["score"], self.new["flamez"]["score"])

    def test_only_sourced_event_peaks_are_bounded(self):
        event = "BLAST Open Rotterdam 2026"
        names = {"ropz", "zywoo", "flamez"}
        ceiling = next(e["peak"] for e in self.old["ropz"]["events"] if e["event"] == event)
        seen = set()
        for pid, player in self.old.items():
            before = player["events"]
            after = self.new[pid]["events"]
            self.assertEqual(len(before), len(after))
            for old, new in zip(before, after):
                if old["event"] == event and pid in names:
                    self.assertEqual(new, dict(old, raw_peak=old["peak"], peak=min(old["peak"], ceiling)))
                    seen.add(pid)
                else:
                    self.assertEqual(old, new)
        self.assertEqual(seen, names)

    def test_lower_challenger_and_unlisted_evp_keep_peak(self):
        config = load("config/season_4_4_2.json")
        event, record = next(iter(config["year_end_peak_context"].items()))
        config.update(cutoff="2026-11-17", top_tier_peak_share=0.35)
        award = dict(mvp="ropz", evps=["zywoo", "flamez", "other"], source=record["source"])
        inputs = ({event: {"last_played": "2026-03-29"}}, {event: award})
        rows = [dict(id=pid, features={}, events=[dict(event=event, tier="Elite", peak=peak)])
                for pid, peak in (("ropz", 80), ("zywoo", 75), ("flamez", 85), ("other", 95))]
        original = deepcopy(rows)
        apply_year_end_peak_context(rows, inputs, config)
        self.assertEqual([p["events"][0]["peak"] for p in rows], [80, 75, 80, 95])
        self.assertEqual(rows[-1], original[-1])
        config["cutoff"] = "2026-03-31"
        with self.assertRaises(ValueError):
            apply_year_end_peak_context(original, inputs, config)
