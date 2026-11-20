import unittest

from htpm.pipeline import load
from htpm.season import features, season_inputs
from htpm.season_forecast import major_replay, published_adjustment, run


class SeasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=season_inputs(2026)
        cls.base=load("config/model.json")
        cls.config=load("config/season_model.json")
        cls.report=run(load("output/current/scores.json"),write=False)
        cls.people={p["id"]:p for p in cls.report["players"]}

    def test_offline_replay_and_scores_reconcile(self):
        self.assertEqual(self.report,load("output/forecast_4_1_1/scores.json"))
        for p in self.people.values():
            self.assertAlmostEqual(p["score"],sum(p["contributions"].values()))
            self.assertLessEqual(abs(p["contributions"]["H"]),self.config["legacy_adjustment_cap"])
            self.assertLessEqual(abs(p["contributions"]["R"]),self.config["published_stage_cap"])

    def test_historical_boundary_contains_real_negatives(self):
        hist=self.report["replay"]
        self.assertEqual({p["actual"] for p in hist["players"].values()},set(range(1,31)))
        self.assertGreater(hist["eligible"],30)
        self.assertEqual(sum(f["target_count"] for f in hist["folds"]),30)
        self.assertEqual(hist["metrics"]["pairs"],435)
        self.assertEqual(len(hist["metrics"]["missed"]),len(hist["metrics"]["false_positives"]))

    def test_venue_and_missing_observations(self):
        self.assertEqual(published_adjustment(None,1.25),0)
        for p in self.people.values():
            d=p["details"]
            self.assertLessEqual(d["studio"]["maps"]+d["arena"]["maps"],d["main"]["maps"])
            self.assertLessEqual(d["pressure_top10"]["maps"],d["playoff"]["maps"])
            self.assertLessEqual(d["final"]["maps"],d["playoff"]["maps"])
            for s in d.values():
                self.assertEqual(s["maps"]==0,s["index"] is None)

    def test_first_evp_proximity_preserves_factual_awards(self):
        neutral={p["id"]:p for p in features(self.inputs,self.base,self.config,2026,near=False)}
        for pid,p in self.people.items():
            for award,flat in zip(p["awards"],neutral[pid]["awards"]):
                self.assertEqual(award["position"],flat["position"])
                self.assertAlmostEqual(award["points"]-flat["points"],award["proximity_points"])
                if award["position"]!=1 and pid not in self.inputs[1][award["event"]].get("peak_context",{}):
                    self.assertEqual(award["proximity_points"],0)
        self.assertTrue(any(a["proximity_points"]>0 for p in self.people.values() for a in p["awards"]))
        for event, pid, signal in (("BLAST Open Porto 2026","sh1ro","close"),
                                   ("BLAST Rivals 2026 Season 2","molodoy","clear")):
            award=next(a for a in self.people[pid]["awards"] if a["event"]==event)
            self.assertEqual(award["first_evp_context"]["signal"],signal)
            self.assertEqual(award["proximity_points"]>0,signal=="close")

    def test_counterfactual_is_one_event_with_one_mvp(self):
        template="IEM Cologne Major 2026"
        cat,awards,stats,_,_=major_replay(self.inputs,template)
        extra=(set(cat)-set(self.inputs[0])).pop()
        self.assertEqual(cat[extra]["tier"],"Major")
        self.assertEqual(awards[extra],awards[template])
        self.assertNotIn(extra,self.inputs[0])
        for pid,events in self.inputs[2].items():
            self.assertEqual(extra in stats[pid],template in events)
        self.assertTrue(all(len(ids)==len(set(ids))==30 for ids in self.report["major_scenarios"].values()))

    def test_stages_partition_maps_and_mark_unmeasured_ratings(self):
        for p in self.people.values():
            matrix=p["tier_stages"]
            self.assertEqual(sum(t["all"]["maps"] for t in matrix.values()),p["details"]["main"]["maps"])
            for t in matrix.values():
                self.assertEqual(t["all"]["maps"],sum(t[k]["maps"] for k in ("group","playoff","placement")))
                self.assertLessEqual(t["final"]["maps"],t["playoff"]["maps"])
                for cell in t.values():
                    self.assertLessEqual(cell["whole_stage_maps"],cell["rating_maps"])
                    self.assertLessEqual(cell["rating_maps"],cell["maps"])
                    self.assertEqual(cell["observed_rating"] is None,cell["rating_maps"]==0)
        self.assertEqual(self.report["version"],"HTPM-4.1.1")

    def test_peak_context_covers_non_first_evp_and_unawarded_events(self):
        e=next(e for e in self.people["flamez"]["events"] if e["event"]=="BLAST Open Rotterdam 2026")
        self.assertEqual(e["proximity_basis"],"官方评语·接近")
        self.assertGreater(next(a["proximity_points"] for a in self.people["flamez"]["awards"] if a["event"]==e["event"]),0)
        self.assertEqual(self.people["npl"]["awards"],[])
        self.assertTrue(any(e["mvp_gap"] is not None for e in self.people["npl"]["events"]))
        self.assertTrue(any(e["peak_class"]=="数据高峰" for p in self.people.values()
                            for e in p["events"] if e["event"] not in {a["event"] for a in p["awards"]}))

    def test_event_credit_keeps_awards_separate_and_respects_caps(self):
        c=self.config
        share=self.report["replay"]["event_credit_share"]
        for p in self.people.values():
            awards={a["event"] for a in p["awards"]}
            for e in p["events"]:
                if e["event"] in awards or e["maps"]<c["peak_min_maps"]:
                    self.assertEqual(e["event_credit"],0)
                if e["exceptional_bonus"]>0:
                    self.assertEqual(e["peak_class"],"官方争奖高峰")
            net=sum(e["event_credit"] for e in p["events"])
            cap=c["event_credit_cap"]
            self.assertAlmostEqual(p["event_credit"],share*min(cap,max(-cap,net)))
            self.assertAlmostEqual(p["resume_points"],max(0,sum(a["points"] for a in p["awards"])+p["event_credit"]))
        for event in self.inputs[1].values():
            context=event.get("first_evp_context") or {}
            if context.get("signal")=="close":
                award=next(a for a in self.people[event["mvp"]]["awards"] if a["event"]==event["event"])
                self.assertEqual(award["dominance_points"],0.)

    def test_full_event_ratings_do_not_leak_into_unobserved_stages(self):
        catalog,_,stats,_,_=self.inputs
        for p in self.people.values():
            for tier, cells in p["tier_stages"].items():
                expected={"all":0,"group":0,"playoff":0,"final":0,"placement":0}
                for e,rows in stats[p["id"]].items():
                    if catalog[e]["tier"]!=tier or p["id"] not in catalog[e].get("event_ratings",{}):
                        continue
                    stages={r[1] for r in rows}
                    expected["all"]+=len(rows)
                    if stages<={"playoff","final"}:
                        expected["playoff"]+=len(rows)
                    for stage in ("group","final","placement"):
                        if stages=={stage}:
                            expected[stage]+=len(rows)
                self.assertEqual({s:c["whole_stage_maps"] for s,c in cells.items()},expected)

    def test_boundary_and_new_candidates_are_scored_from_evidence(self):
        for pid in ("npl","sunpayus","jame"):
            self.assertTrue(self.people[pid]["eligible"])
        for p in self.people.values():
            if p["rank"] is not None:
                ranks=[s[p["id"]] for s in self.report["scenarios"].values()]
                self.assertEqual(p["range"],[min(ranks),max(ranks)])
            if p["published"] is None:
                self.assertEqual(p["contributions"]["R"],0)
