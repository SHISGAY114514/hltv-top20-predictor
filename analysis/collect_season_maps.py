"""Extract the two seasons' observed map scoreboards from the pinned public ZIP."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from htpm.pipeline import ROOT, load
from htpm.core import dump_json, require

SOURCE = "https://www.kaggle.com/datasets/ektarr/counter-strike-pro-matches"
FIELDS = "event match map date stage venue team opponent opponent_rank player rounds kills deaths adr kast win".split()


def name_key(name):
    return name.split(" (")[0].split(",")[0].strip().casefold()


def opponent_rank(roster, ranking):
    for rank, team, players in ranking["teams"]:
        if len(roster.intersection(name_key(p) for p in players)) >= 3:
            return rank
    return ""


def collect(archive):
    catalog = load("data/reference/season_stage_catalog.json")
    rankings = load("data/reference/vrs_top10_monthly.json")
    with zipfile.ZipFile(archive) as z, z.open("cs2_all_tiers_games.csv") as f:
        groups = defaultdict(list)
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
            groups[row["tournament"]].append(row)
    audit = {"source": SOURCE, "archive_sha256": hashlib.sha256(Path(archive).read_bytes()).hexdigest(), "events": []}
    for year, events in catalog.items():
        output = []
        for e in events:
            rows = [r for r in groups[e["dataset_name"]] if r["datetime"][:4] == year
                    and r["datetime"] >= (e["start"] or year)]
            series = [r for r in rows if r["is_total"] == "True"]
            final = max(series, key=lambda r: r["datetime"])
            hong_kong = year == "2026" and e["event"] == "BLAST Rivals 2026 Season 2"
            finalists = {"Team Spirit", "FURIA Esports"} if hong_kong else {final["team1"], final["team2"]}
            bronze = set()
            if not hong_kong:
                # A playoff series after both sides lost to the eventual finalists is a placement match.
                lost = set()
                for r in sorted(series, key=lambda r: r["datetime"]):
                    if r["datetime"] < e["playoffs"] or float(r["bestOf"] or 0) <= 1:
                        continue
                    teams = {r["team1"], r["team2"]}
                    if teams <= lost:
                        bronze.add(r["match_id"])
                    winner = r["team1"] if r["team1_win"] == "1" else r["team2"]
                    if winner in finalists:
                        lost.update(teams - {winner} - finalists)
            seen = set()
            skipped = Counter()
            def emit(mid, game, date, stage, teams, players, rounds, winning_side):
                snapshot = rankings[max(k for k in rankings if k < date)]
                ranks = [opponent_rank({name_key(p[0]) for p in side}, snapshot) for side in players]
                venue = "unknown"
                if e["venue"] == "studio" or (e["venue"] == "split" and stage == "group"):
                    venue = "studio"
                elif e["venue"] in ("arena", "split") and stage != "group":
                    venue = "arena"
                for side, roster in enumerate(players):
                    for nick, kills, deaths, adr, kast in roster:
                        output.append([e["event"], mid, game, date, stage, venue, teams[side], teams[1-side],
                                       ranks[1-side], nick, rounds, kills, deaths, adr, kast, int(side==winning_side)])
            for r in rows:
                if r["is_total"] != "False":
                    continue
                mid, game = r["match_id"], r["game_id"]
                if (mid, game) in seen:
                    raise ValueError("Duplicate map: " + str((mid, game)))
                seen.add((mid, game))
                stage = "group"
                if r["datetime"] >= e["playoffs"]:
                    if float(r["bestOf"] or 0) <= 1:
                        skipped["exhibition"] += 1
                        continue
                    stage = "placement" if mid in bronze else "playoff"
                if not hong_kong and mid == final["match_id"]:
                    stage = "final"
                players = [[], []]
                try:
                    rounds = int(float(r["score1_game"]) + float(r["score2_game"]))
                    if rounds < 13:
                        raise ValueError("incomplete map")
                    for i in (0, 1):
                        for j in range(1,6):
                            key = "team%d_player%d" % (i+1,j)
                            nick = r[key].split(" (")[0].split(",")[0].strip()
                            kills, deaths, adr, kast = (float(r[key+"_"+field]) for field in ("kills","deaths","adr","kast"))
                            if not nick or min(kills,deaths,adr,kast) < 0 or kast > 100 or deaths > rounds:
                                raise ValueError("invalid scoreboard")
                            players[i].append([nick,int(kills),int(deaths),adr,kast])
                    if len({name_key(p[0]) for side in players for p in side}) != 10:
                        raise ValueError("incomplete rosters")
                except (ValueError, TypeError):
                    skipped["incomplete_scoreboard"] += 1
                    continue
                winner = 0 if float(r["score1_game"]) > float(r["score2_game"]) else 1
                emit(mid, game, r["datetime"][:10], stage, [r["team1"],r["team2"]], players, rounds,winner)
            if hong_kong:
                extra = load("data/2026/hong_kong_final_maps.json")
                for m in extra["maps"]:
                    emit("hltv-2400208", m["map"], "2026-11-15", "final", extra["team_order"], m["teams"], m["rounds"],1)
            own = [r for r in output if r[0] == e["event"]]
            audit["events"].append({"year":year, "event":e["event"], "finalists":sorted(finalists),
                                    "included_maps":len(own)//10, "source_series":len(series),
                                    "excluded_maps":dict(skipped),"placement_series":sorted(bronze)})
        dest = ROOT/"data"/year/"stage_maps.csv.gz"
        dest.parent.mkdir(exist_ok=True, parents=True)
        stream = io.StringIO(newline="")
        writer = csv.writer(stream,lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows(sorted(output, key=lambda r:(r[3],r[0],r[1],r[2],r[9])))
        dest.write_bytes(gzip.compress(stream.getvalue().encode("utf-8"),mtime=0))
    dump_json(ROOT/"data/reference/stage_collection_audit.json",audit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive",type=Path)
    collect(parser.parse_args().archive)
