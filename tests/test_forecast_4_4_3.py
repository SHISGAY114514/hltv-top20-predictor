import csv
import gzip
import unittest
from collections import Counter

from analysis.compare_4_4 import keyed
from htpm.forecast_4_2 import calculate, publish
from htpm.pipeline import ROOT
from htpm.season import season_inputs


EVENT = "BLAST Rivals 2026 Season 1"
MATCH = "7300742"
MAPS = {"153567", "153575"}
PLAYERS = {"hooxi", "hypex", "jabbi", "pr", "rez", "ryu", "snax", "staehr", "tauson", "phzy"}


class FortWorthQuarterfinalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = calculate(model="4.4.2")
        cls.new = calculate(model="4.4.3")

    def test_only_these_twenty_player_map_records_change_phase(self):
        old_rules, new_rules = self.old["stage_exceptions"], self.new["stage_exceptions"]
        self.assertEqual(new_rules[:-1], old_rules)
        rule = new_rules[-1]
        self.assertEqual((rule["event"], rule["match"], rule["hltv_match"], set(rule["maps"])),
                         (EVENT, MATCH, 2393347, MAPS))
        old, new = (season_inputs(2026, True, rules, True, True)[2] for rules in (old_rules, new_rules))
        offset, changed = Counter(), set()
        with gzip.open(ROOT/"data/2026/stage_maps.csv.gz", "rt", encoding="utf8") as f:
            for row in csv.DictReader(f):
                pid, event = row["player"].casefold(), row["event"]
                i = offset[pid, event]
                offset[pid, event] += 1
                a, b = old[pid][event][i], new[pid][event][i]
                if (event, row["match"]) == (EVENT, MATCH):
                    self.assertEqual((a[1], a[2]), ("playoff", "arena"))
                    self.assertEqual(b, a[:1] + ("quarterfinal",) + a[2:])
                    changed.add((pid, row["map"]))
                else:
                    self.assertEqual(a, b)
        self.assertEqual(changed, {(p, m) for p in PLAYERS for m in MAPS})

    def test_corrected_stage_reaches_year_end_scoring(self):
        before, after = keyed(self.old), keyed(self.new)
        self.assertEqual(before.keys(), after.keys())
        self.assertEqual(self.old["event_weights"], self.new["event_weights"])
        for pid, a in before.items():
            b = after[pid]
            for key in ("main", "arena", "final", "won", "top5", "top10"):
                self.assertEqual(a["details"][key], b["details"][key])
            for key in ("playoff", "big_playoff"):
                self.assertEqual(a["details"][key]["maps"] - b["details"][key]["maps"],
                                 2 if pid in PLAYERS else 0)
            self.assertEqual(a["eligible"], b["eligible"])
            if pid not in PLAYERS:
                self.assertEqual(a["contributions"], b["contributions"])
            else:
                a_cells, b_cells = (p["tier_stages"]["Big"] for p in (a, b))
                key = "quarterfinal_outside_filter"
                self.assertEqual(b_cells[key]["maps"] - a_cells[key]["maps"], 2)
                self.assertEqual(a_cells["group"], b_cells["group"])
                self.assertEqual(a_cells["all"], b_cells["all"])
        self.assertEqual(sum(p["eligible"] for p in after.values()), 177)
        self.assertEqual(publish(self.old, verify=True).parent.name, self.new["baseline_snapshot"])
        publish(self.new, verify=True)
