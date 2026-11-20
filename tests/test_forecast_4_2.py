import csv
import gzip
import io
import json
import tempfile
import unittest
from collections import defaultdict
from datetime import date
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from htpm.forecast_4_2 import additions, calculate, publish, settings
from htpm.major_import import MAP_FIELDS, MATCH_FIELDS, import_event
from htpm.pipeline import ROOT,load
from htpm.season import season_inputs


def csvfile(path, fields, rows):
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fields,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.spec, self.config, self.weights = settings()
        self.today = date(2026,12,16)

    def fixture(self):
        # Real archived Cologne playoffs, replayed in isolation. Test URL IDs
        # are local fixtures; they are never written to a production report.
        original = "IEM Cologne Major 2026"
        spec = {**self.spec,"start":"2026-06-18","group_end":"2026-06-17","playoffs":"2026-06-18",
                "end":"2026-06-21","series_counts":{"playoff":6,"final":1},"teams":8,"standings":"2026-06-01"}
        with gzip.open(ROOT/"data/2026/stage_maps.csv.gz","rt",encoding="utf8") as stream:
            rows = [dict(r,event=spec["event"]) for r in csv.DictReader(stream)
                    if r["event"]==original and r["stage"] in ("playoff","final")]
        matches = defaultdict(list)
        for row in rows:
            matches[row["match"]].append(row)
        fixtures = [dict(match=mid,maps=len({r["map"] for r in group}),date=group[0]["date"],stage=group[0]["stage"],
                         source=f"https://www.hltv.org/matches/{mid}/test-only",exception="") for mid,group in matches.items()]
        csvfile(self.folder/"matches.csv",MATCH_FIELDS,fixtures)
        csvfile(self.folder/"maps.csv",MAP_FIELDS,rows)
        meta = dict(event=spec["event"],event_id=spec["event_id"],awards_status="pending",
                    awards=dict(mvp=None,evps=[],source=""))
        meta.update(as_of="2026-12-16",map_source="https://www.hltv.org/events/8301/iem-cologne-major-2026")
        self.save(meta)
        return spec,meta,rows

    def save(self,meta):
        (self.folder/"event.json").write_text(json.dumps(meta),encoding="utf8")

    def test_snapshot_matches_frozen_ranks_and_scores(self):
        self.save({"as_of":None})
        result = calculate(self.folder,today=date(2026,11,20))
        old = load("output/forecast_4_1_1/scores.json")
        keys = lambda p:(p["id"],p["score"],p["rank"])
        self.assertEqual(list(map(keys,result["players"])), list(map(keys,old["players"])))
        self.assertEqual(result["state"],"snapshot")

    def test_formal_provisional_and_republication(self):
        spec,meta,rows = self.fixture()
        with patch("htpm.forecast_4_2.settings",return_value=(spec,self.config,self.weights)):
            result = calculate(self.folder,self.today)
            self.assertEqual(result["state"],"provisional")
            self.assertEqual(len(result["majors"]),2)
            self.assertTrue(all(p["contributions"]["H"]==p["contributions"]["R"]==0 for p in result["players"]))
            awards = next(a for a in load("data/reference/evp_orders_2026.json")["events"] if a["event"]=="IEM Cologne Major 2026")
            meta.update(awards_status="complete",awards={**awards,"published_on":"2026-06-25"})
            self.save(meta)
            final = calculate(self.folder,self.today)
            self.assertEqual(final["state"],"formal")
            p = next(p for p in final["players"] if p["id"]==awards["mvp"])
            self.assertEqual(sum(a["kind"]=="MVP" and a["event"] in final["majors"] for a in p["awards"]),2)
            dest = self.folder/"publish"
            path = publish(final,dest=dest)
            self.assertEqual(path,publish(calculate(self.folder,self.today),verify=True,dest=dest))
            report = path.read_text(encoding="utf8")
            self.assertIn("双 Major 正式预测",report)
            self.assertEqual(report.count("- 高于下一位"),30)
            self.assertIn("第 31–50 名",report)

    def test_invalid_observations(self):
        spec,meta,rows = self.fixture()
        for bad in (rows[:-1], rows[10:], rows+[rows[0]], [dict(rows[0],stage="group"),*rows[1:]]):
            csvfile(self.folder/"maps.csv",MAP_FIELDS,bad)
            with self.assertRaises(ValueError):
                import_event(season_inputs(2026),self.folder,spec,self.today)
        csvfile(self.folder/"maps.csv",MAP_FIELDS,rows)
        for updates in (dict(awards_status="complete"),dict(as_of="2026-12-17"),dict(event_id=8301)):
            self.save({**meta,**updates})
            with self.assertRaises(ValueError):
                import_event(season_inputs(2026),self.folder,spec,self.today)

    def test_stale_corrections_and_independent_refresh(self):
        (self.folder/"aggregate.json").write_text('{"metadata":{"snapshot_as_of":"2026-11-17"}}')
        (self.folder/"published.json").write_text('{"as_of":"2026-11-17"}')
        inputs=season_inputs(2026)
        audit={"cutoff":"2026-12-16"}
        old,published,notes=additions(inputs,self.folder,audit,self.spec,self.config)
        self.assertFalse(old or published)
        self.assertIn("日期",notes["H"])
        table = load("data/2026/published_stage_ratings.json")
        table.update(as_of=audit["cutoff"],events=list(inputs[0]),rating_version="3.0")
        (self.folder/"published.json").write_text(json.dumps(table),encoding="utf8")
        self.assertTrue(additions(inputs,self.folder,audit,self.spec,self.config)[1])

    def test_bulk_archive_matches_csv_and_patch_restores_a_missing_map(self):
        spec,meta,rows = self.fixture()
        api = lambda: import_event(season_inputs(2026),self.folder,spec,self.today)
        expected = api()["maps"]
        by_series = defaultdict(lambda:defaultdict(list))
        for r in rows:
            by_series[r["match"]][r["map"]].append(r)
        packed = []
        for mid,games in by_series.items():
            wins = defaultdict(int)
            for game,players in games.items():
                left,right = sorted({p["team"] for p in players})
                common = dict(match_id=mid,tournament=spec["event"],datetime=players[0]["date"],team1=left,team2=right)
                m = dict(common,game_id=game,is_total="False")
                for i,team in enumerate((left,right),1):
                    side = [r for r in players if r["team"]==team]
                    won = int(side[0]["win"])
                    wins[team] += won
                    rounds = int(side[0]["rounds"])
                    # Only the sum of rounds and the winning side are observed in the archive fixture.
                    m[f"score{i}_game"] = rounds if won else 0
                    for j,p in enumerate(side,1):
                        key = f"team{i}_player{j}"
                        m[key] = p["player"]
                        m.update({key+"_"+k:p[k] for k in ("kills","deaths","adr","kast")})
                packed.append(m)
            packed.append(dict(common,is_total="True",games_played=len(games),bestOf=5 if max(wins.values())==3 else 3,
                               score1_match=wins[left],score2_match=wins[right],team1_win=int(wins[left]>wins[right])))
        def save_zip(records):
            stream=io.StringIO()
            writer=csv.DictWriter(stream,sorted(set().union(*(r.keys() for r in records))))
            writer.writeheader()
            writer.writerows(records)
            with ZipFile(self.folder/"results.zip","w") as archive:
                archive.writestr("cs2_all_tiers_games.csv",stream.getvalue())
        save_zip(packed)
        self.assertEqual(api()["maps"],expected)
        missing = packed.pop(0)
        save_zip(packed)
        with self.assertRaisesRegex(ValueError, missing["match_id"]):
            api()
        restore = [dict(r,source="https://www.hltv.org/matches/123/test") for r in rows
                   if r["match"]==missing["match_id"] and r["map"]==missing["game_id"]]
        csvfile(self.folder/"maps_patch.csv",[*MAP_FIELDS,"source"],restore)
        self.assertEqual(api()["maps"],expected)

    def test_new_substitute_and_absent_player(self):
        spec,meta,rows = self.fixture()
        last = rows[-1]
        last["player"] = "TestSub"
        csvfile(self.folder/"maps.csv",MAP_FIELDS,rows)
        meta["awards"] = dict(mvp="testsub",evps=[],source="https://www.hltv.org/news/1/test",published_on=meta["as_of"])
        self.save(meta)
        with patch("htpm.forecast_4_2.settings",return_value=(spec,self.config,self.weights)):
            result=calculate(self.folder,self.today)
        p=next(p for p in result["players"] if p["id"]=="testsub")
        self.assertEqual(p["details"]["main"]["maps"],1)
        self.assertIsNone(p["snapshot_rank"])
        self.assertTrue(p["eligible"])
        self.assertTrue(any(p["eligible"] and all(e["event"]!=spec["event"] for e in p["events"]) for p in result["players"]))
