"""Import one observed main event into the season engine."""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .core import iso, number, require
from .major_archive import SOURCE, from_archive
from .pipeline import load
from .season import index


MAP_FIELDS = "event match map date stage venue team opponent player rounds kills deaths adr kast win series_rating event_rating".split()
MATCH_FIELDS = "match date stage maps source exception".split()
DEFAULT_INPUT = Path("data/2026/singapore")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path, fields):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require(set(fields) <= set(reader.fieldnames or []), f"{path.name} 缺少必填列")
        return list(reader)


def link(value, hltv=False):
    url = urlsplit(value or "")
    require(url.scheme == "https" and url.hostname and
            (not hltv or url.hostname in ("hltv.org", "www.hltv.org")), f"请核对来源链接 {value!r}")
    return value


def award_record(record, participants, complete):
    mvp = record.get("mvp")
    ordered, unordered = record["evps"], record.get("unranked_evps", [])
    require(isinstance(ordered, list) and isinstance(unordered, list), "EVP 必须为名单")
    winners = ([mvp] if mvp else []) + ordered + unordered
    require(set(winners) <= participants and len(winners) == len(set(winners)), "奖项选手重复或缺少实际出场记录")
    require(not (ordered or unordered) or mvp, "EVP 缺少 MVP 对照")
    require(not complete or (mvp and (ordered or unordered)), "正式榜需要完整 MVP 和 EVP")
    if winners:
        link(record["source"], True)
    evidence = record.get("peak_context", {})
    for pid, item in evidence.items():
        require(pid in ordered + unordered and item["signal"] in ("close", "clear") and item["note"],
                "争奖评语需对应官方 EVP")
        link(item["source"], True)
    result = {**record, "pending": not complete}
    require("first_evp_context" not in record, "请在 peak_context 按选手填写争奖评语")
    if ordered and ordered[0] in evidence:
        result["first_evp_context"] = evidence[ordered[0]]
    return result


def check_schedule(fixtures, spec, archive=False):
    matches = {}
    for row in fixtures:
        mid, day, stage = row["match"], row["date"], row["stage"]
        require(mid and mid not in matches and stage in spec["series_counts"], "赛程出现重复场次或未知阶段")
        iso(day, "比赛日期")
        require(spec["start"] <= day <= spec["end"], f"{mid} 超出主赛事日期范围")
        require(day <= spec["group_end"] if stage == "group" else day >= spec["playoffs"], f"{mid} 错误阶段")
        require(stage != "final" or day == spec["end"], "总决赛日期不符")
        if archive:
            require(row["source"] == SOURCE, "数据集来源不符")
        else:
            source = link(row["source"], True)
            match_id = re.match(r"/matches/(\d+)(?:/|$)",urlsplit(source).path)
            require(match_id and match_id.group(1) not in {m["hltv_match"] for m in matches.values()},
                    f"{mid} 需提供独立比赛结果页")
            row = {**row, "hltv_match":match_id.group(1)}
        maps = int(row["maps"])
        needed = 3 if stage == "final" else 2
        require(0 <= maps <= 2*needed-1 and (maps >= needed or row.get("exception")), f"{mid} 实际地图数与赛制不符")
        matches[mid] = {**row, "maps": maps}
    require(Counter(r["stage"] for r in fixtures) == spec["series_counts"], "赛程不全，请按主赛事结果页核对各阶段系列赛场数")
    return matches


def parse_maps(rows, matches, spec, rankings, aliases):
    by_map = defaultdict(list)
    for row in rows:
        mid, game = row["match"], row["map"]
        require(row["event"] == spec["event"] and mid in matches and game, "地图不在本届主赛事赛程")
        match = matches[mid]
        require(row["date"] == match["date"] and row["stage"] == match["stage"], f"{mid} 地图阶段或日期与赛程不同")
        require(row["venue"] in ("arena", "studio", "unknown"), f"{mid} 未知场馆标记")
        by_map[mid, game].append(row)
    map_counts = Counter(mid for mid, _ in by_map)
    missing = [f"{mid} {m.get('team1','')}/{m.get('team2','')}（实收 {map_counts[mid]}，应有 {m['maps']}）"
               for mid,m in matches.items() if map_counts[mid] != m["maps"]]
    require(not missing, "逐场实收图数不符，请核对或用 maps_patch.csv 补录："+"、".join(missing))
    observed, names, rosters, event_ratings, series_ratings = defaultdict(list), {}, defaultdict(set), {}, {}
    final_teams, sides, wins = set(), defaultdict(set), defaultdict(Counter)
    for (mid, game), group in sorted(by_map.items()):
        team_rows = defaultdict(list)
        for r in group:
            team_rows[r["team"]].append(r)
        require(len(team_rows) == 2 and all(t and len(v) == 5 for t,v in team_rows.items()), f"{mid}/{game} 缺少两个完整五人阵容")
        require(len({(r["rounds"], r["venue"]) for r in group}) == 1, f"{mid}/{game} 局数或场馆冲突")
        sides[mid].update(team_rows)
        players, map_wins = set(), []
        for team, records in team_rows.items():
            opponent = next(t for t in team_rows if t != team)
            require(all(r["opponent"] == opponent and r["win"] == records[0]["win"] for r in records), f"{mid}/{game} 对手或胜负冲突")
            won = int(records[0]["win"])
            require(won in (0,1), "胜负须为 0/1")
            map_wins.append(won)
            wins[mid][team] += won
            opp_ids = {aliases.get(r["player"].strip().casefold(), r["player"].strip().casefold()) for r in team_rows[opponent]}
            rank = next((n for n, lineup in rankings if len(lineup & opp_ids) >= 3), 99)
            for r in records:
                nick = r["player"].strip()
                pid = aliases.get(nick.casefold(), nick.casefold())
                require(pid and pid not in players, f"{mid}/{game} 选手身份重复或为空")
                players.add(pid)
                names[pid] = nick
                rosters[team].add(pid)
                rounds = int(r["rounds"])
                require(rounds >= 13 and 0 <= int(r["deaths"]) <= rounds and 0 <= int(r["kills"]) <= 5*rounds,
                        f"{mid}/{game} 计数错误")
                number(float(r["adr"]), 0, 1000, "ADR")
                number(float(r["kast"]), 0, 100, "KAST")
                for key, store, ident in (("series_rating", series_ratings, (mid,pid)), ("event_rating", event_ratings, pid)):
                    if r.get(key):
                        value = float(r[key])
                        number(value, 0, 10, key)
                        require(store.setdefault(ident,value) == value, f"{nick} 的 {key} 冲突")
                observed[pid].append((mid,index(r),r["stage"],r["venue"],rank,team,won))
            if records[0]["stage"] == "final":
                final_teams.add(team)
        require(sum(map_wins) == 1, f"{mid}/{game} 没有唯一胜方")
    for mid,teams in sides.items():
        needed = 3 if matches[mid]["stage"] == "final" else 2
        require(len(teams) == 2 and (matches[mid].get("exception") or
                sorted(wins[mid].values())[0] < needed == max(wins[mid].values())), f"{mid} 系列赛未决出胜负")
        if "score1" in matches[mid]:
            m = matches[mid]
            require(dict(wins[mid]) == {m["team1"]:m["score1"],m["team2"]:m["score2"]}, f"{mid} 逐图胜负与系列赛总比分不符")
    require(len(rosters) == spec["teams"] and len(final_teams) == 2, "正赛队伍数或决赛队伍数不符")
    stats = {}
    for pid, sequence in observed.items():
        single_stage = len({r[2] for r in sequence}) == 1
        stats[pid] = [(idx,stage,venue,rank,team,won,series_ratings.get((mid,pid)),
                       event_ratings.get(pid) if single_stage else None) for mid,idx,stage,venue,rank,team,won in sequence]
    strength = sum(1 if n<=5 else .5 for n,lineup in rankings if any(len(lineup & r)>=3 for r in rosters.values())) / 7.5
    return stats, names, final_teams, {"tier":"Major","field_strength":strength,"event_ratings":event_ratings}


def import_event(inputs, folder, spec, today=None, meta=None):
    if meta is None:
        meta = read_json(folder/"event.json")
    require(meta["event_id"] == spec["event_id"] and meta["event"] == spec["event"], "赛事 ID 或名称不符")
    cutoff = iso(meta["as_of"], "as_of")
    require(iso(spec["end"], "end") <= cutoff <= (today or date.today()) and cutoff.year == 2026, "需要赛后真实截止日")
    require(meta["awards_status"] in ("pending","complete"), "未知奖项状态")
    aliases = meta.get("aliases", {})
    require(all(isinstance(v,str) and v and v == v.strip().casefold() for v in aliases.values()), "别名必须指向小写选手 ID")
    archive = folder/"results.zip"
    digest = None
    patches = []
    if archive.exists():
        if (folder/"maps_patch.csv").exists():
            patches = read_csv(folder/"maps_patch.csv", [*MAP_FIELDS[:-2],"source"])
            for r in patches:
                link(r["source"],True)
        replaced = {(r["match"],r["map"]) for r in patches}
        fixtures,rows,digest = from_archive(archive,spec,meta.get("dataset_name",spec["event"]),replaced)
        rows.extend(patches)
        source = SOURCE
        matches = check_schedule(fixtures,spec,archive=True)
    else:
        source = link(meta["map_source"])
        fixtures = read_csv(folder/"matches.csv", MATCH_FIELDS)
        matches = check_schedule(fixtures,spec)
        rows = read_csv(folder/"maps.csv", MAP_FIELDS[:-2])
    # Use the published Major invitation standings for this event, frozen before play.
    require(spec["standings"] < spec["start"], "VRS 日期必须早于开赛")
    vrs = load("data/reference/vrs_top10_monthly.json")[spec["standings"]]
    rankings = [(n,{p.casefold() for p in lineup}) for n,_,lineup in vrs["teams"]]
    if (folder/"ratings.csv").exists():
        attach_ratings(rows, read_csv(folder/"ratings.csv", ["match","player","rating","source"]),aliases)
    stats,names,finals,entry = parse_maps(rows,matches,spec,rankings,aliases)
    complete = meta["awards_status"] == "complete"
    award = award_record(meta["awards"],set(stats),complete)
    if award["mvp"]:
        require(iso(spec["end"],"end") <= iso(award.get("published_on"),"awards.published_on") <= cutoff,
                "官方奖项发布日期超出榜单截止日")
    event = spec["event"]
    catalog,awards,all_stats,all_names,finalists = inputs
    require(event not in catalog, "重复导入同一赛事")
    catalog[event], awards[event], finalists[event] = entry, award, finals
    all_names.update({p:n for p,n in names.items() if p not in all_names})
    for pid, values in stats.items():
        all_stats[pid][event] = values
    files = ["event.json","ratings.csv","aggregate.json","published.json"] + (
        ["maps_patch.csv"] if archive.exists() else ["maps.csv","matches.csv"])
    hashes = {f:hashlib.sha256((folder/f).read_bytes()).hexdigest() for f in files if (folder/f).exists()}
    return {"cutoff":meta["as_of"], "state":"formal" if complete else "provisional", "file_sha256":hashes,
            "series":len(matches), "maps":len(rows)//10, "participants":len(stats), "vrs":vrs["source"],
            "map_source":source, "archive_sha256":digest, "schedule_source":spec["source"], "award_source":award["source"],
            "patch_sources":sorted({r["source"] for r in patches}),
            "matches":fixtures}


def attach_ratings(rows, ratings, aliases):
    index_rows = defaultdict(list)
    for r in rows:
        nick = r["player"].strip().casefold()
        pid = aliases.get(nick,nick)
        index_rows[r["match"],pid].append(r)
        index_rows["",pid].append(r)
    seen = set()
    for r in ratings:
        link(r["source"],True)
        key = (r["match"],r["player"].strip().casefold())
        require(key not in seen and key in index_rows, f"实测 Rating 重复或无对应出场记录 {key}")
        seen.add(key)
        score = float(r["rating"])
        number(score,0,10,"Rating")
        field = "series_rating" if r["match"] else "event_rating"
        for record in index_rows[key]:
            require(not record.get(field) or float(record[field])==score, "实测 Rating 冲突")
            record[field] = str(score)
