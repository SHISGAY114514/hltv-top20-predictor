import json
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from htpm.aggregate import score
from htpm.event_policy import apply_stage_context, attach_vps, event_policy
from htpm.forecast_4_2 import calculate, individual_reference, publish, settings
from htpm.pipeline import load, prepare
from htpm.season import season_inputs


class IndividualSeasonTests(unittest.TestCase):
    def test_current_scores_and_venue(self):
        with TemporaryDirectory() as folder:
            Path(folder, "event.json").write_text('{"as_of":null}', encoding="utf8")
            result = calculate(folder, date(2026,11,17), model="4.3")
        policies = result["event_weights"]
        self.assertEqual(len(policies), 23)
        self.assertEqual(set(policies), set(result["scope"]))
        self.assertGreater(policies["Esports World Cup 2026"]["stage_factors"]["final"],
                           policies["Esports World Cup 2026"]["stage_factors"]["playoff"])
        group = policies["FISSURE Playground 3"]["stage_factors"]
        self.assertGreater(group["group_arena"], group["group_lan"])
        self.assertEqual(policies["XSE Pro League Guangzhou 2026"]["roster"]["teams"],16)
        for p in result["players"]:
            self.assertEqual(p["features"]["T"], 0)
            self.assertEqual(p["contributions"]["T"], 0)
            self.assertAlmostEqual(sum(p["contributions"].values()), p["score"])
        jame = next(p for p in result["players"] if p["id"] == "jame")
        vp = next(a for a in jame["awards"] if a["kind"] == "VP")
        policy = policies[vp["event"]]
        basic = load("config/model.json")["tiers"][policy["tier"]]["EVP"]
        self.assertAlmostEqual(vp["points"], basic * .40 * policy["honor_multiplier"])
        event = next(e for e in jame["events"] if e["event"] == vp["event"])
        self.assertEqual(event["event_credit"], 0)
        self.assertAlmostEqual(jame["resume_points"], sum(a["points"] for a in jame["awards"]) + jame["event_credit"])

    def test_historical_event_order_and_cutoff(self):
        _, config, _ = settings()
        config.update(load("config/season_4_3.json"))
        inputs = season_inputs(2025, detailed_rosters=True)
        policy = event_policy(inputs, 2025, config)
        for order in load("data/reference/award_order_2025.json")["within_tier"].values():
            factors = [policy[name]["event_factor"] for name in order]
            self.assertEqual(factors, sorted(factors, reverse=True))
        self.assertEqual(policy["BLAST Open S2"]["roster"]["teams"], 6)
        apply_stage_context(inputs, policy)
        stages = {r[1] for events in inputs[2].values() for r in events.get("Esports World Cup", [])}
        self.assertTrue(stages)
        self.assertNotIn("group", stages)
        records = load("data/reference/official_vps_4_3.json")["2025"]
        self.assertEqual(attach_vps(inputs, records, "2025-12-23"), 0)
        self.assertEqual(attach_vps(inputs, records, "2025-12-31"), 3)

    def test_team_placements_cannot_change_reference_score_or_rank(self):
        data, params, _ = prepare()
        params = individual_reference(params)
        def results(p):
            return [(r["id"], r["score"], r["rank"]) for r in score(data, p)["players"]]
        self.assertEqual(results(params), results({**params, "placement_points": dict.fromkeys(params["placement_points"], 0)}))

    def test_vp_evidence_as_of_and_duplicates(self):
        inputs = season_inputs(2026, detailed_rosters=True)
        record = load("data/reference/official_vps_4_3.json")["2026"][0]
        event = record["event"]
        self.assertEqual(attach_vps(inputs, [record], "2026-01-26"), 0)
        self.assertEqual(attach_vps(inputs, [record], record["published_on"]), 1)
        for invalid in ([record, record], [dict(record, player=inputs[1][event]["mvp"])],
                        [dict(record, grade="honorable mention")], [dict(record, published_on="2026-01-01")],
                        [dict(record, source="https://other.example/news/1")]):
            with self.assertRaises(ValueError):
                attach_vps(inputs, invalid, "2026-11-17")

    def test_two_major_release(self):
        from test_forecast_4_2 import ReleaseTests
        fixture = ReleaseTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        spec, meta, rows = fixture.fixture()
        awards = next(a for a in load("data/reference/evp_orders_2026.json")["events"] if a["event"] == "IEM Cologne Major 2026")
        pid = next(r["player"].casefold() for r in rows if r["player"].casefold() not in {awards["mvp"], *awards["evps"]})
        # A synthetic local source record tests the interface, never the published ledger.
        vp = dict(event=spec["event"], player=pid, grade="VP", evidence="local test",
                  source="https://www.hltv.org/news/1/test", published_on="2026-06-25")
        (fixture.folder/"vps.json").write_text(json.dumps([vp]), encoding="utf8")
        with patch("htpm.forecast_4_2.settings", return_value=(spec, deepcopy(fixture.config), fixture.weights)):
            provisional = calculate(fixture.folder, fixture.today, model="4.3")
            self.assertEqual(provisional["state"], "provisional")
            meta.update(awards_status="complete", awards={**awards, "published_on":"2026-06-25"})
            fixture.save(meta)
            final = calculate(fixture.folder, fixture.today, model="4.3")
            self.assertEqual(final["state"], "formal")
            self.assertEqual(len(final["majors"]), 2)
            self.assertIn(spec["event"], final["event_weights"])
            player = next(p for p in final["players"] if p["id"] == pid)
            self.assertTrue(any(a["kind"] == "VP" and a["event"] == spec["event"] for a in player["awards"]))
            for p in final["players"]:
                self.assertEqual(p["contributions"]["T"], 0)
            dest = fixture.folder/"report"
            self.assertEqual(publish(final, dest=dest), publish(final, verify=True, dest=dest))
