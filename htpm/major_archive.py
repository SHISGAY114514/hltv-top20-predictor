"""Read the public series archive without modifying the frozen season datasets."""
import csv
import hashlib
import io
from collections import Counter
from zipfile import BadZipFile, ZipFile

from .core import require

SOURCE = "https://www.kaggle.com/datasets/ektarr/counter-strike-pro-matches"


def integer(value):
    n = float(value)
    require(n.is_integer(), "档案中的计数应为整数")
    return int(n)


def from_archive(path, spec, dataset_name, replaced=()):
    try:
        with ZipFile(path) as archive, archive.open("cs2_all_tiers_games.csv") as raw:
            rows = [r for r in csv.DictReader(io.TextIOWrapper(raw,encoding="utf-8-sig"))
                    if r["tournament"] == dataset_name]
    except BadZipFile as exc:
        raise ValueError("逐图数据文件不是有效的 ZIP 包") from exc
    totals = sorted((r for r in rows if r["is_total"]=="True" and spec["start"] <= r["datetime"][:10] <= spec["end"]),
                    key=lambda r:r["datetime"])
    fixtures, stages, lost = [], {}, set()
    for r in totals:
        mid,day,best = r["match_id"],r["datetime"][:10],int(r["bestOf"])
        if day >= spec["playoffs"] and best==1:
            continue  # Showmatch outside the competitive bracket.
        teams = {r["team1"],r["team2"]}
        stage = "group"
        if day >= spec["playoffs"]:
            if best == 5:
                stage = "final"
            elif teams <= lost:
                stage = "placement"
            else:
                stage = "playoff"
                lost.add(r["team2"] if int(r["team1_win"]) else r["team1"])
        require(mid not in stages and best == (5 if stage=="final" else 3), f"{mid} 系列赛冲突或赛制变更，请核对赛程")
        expected = integer(r["games_played"])
        require(expected == integer(r["score1_match"])+integer(r["score2_match"]), f"{mid} 系列赛总比分和地图数冲突")
        stages[mid] = stage
        fixtures.append(dict(match=mid,date=day,stage=stage,maps=expected,source=SOURCE,exception="",
                             team1=r["team1"],team2=r["team2"],score1=integer(r["score1_match"]),score2=integer(r["score2_match"])))
    require(Counter(stages.values()) == spec["series_counts"], "数据包未覆盖完整正赛，或赛事名称/赛程不匹配")
    days = {m["match"]:m["date"] for m in fixtures}
    maps = []
    for r in rows:
        mid = r["match_id"]
        if mid not in stages or r["is_total"] != "False" or (mid,r["game_id"]) in replaced:
            continue
        scores = [integer(r[f"score{i}_game"]) for i in (1,2)]
        require(scores[0]!=scores[1] and min(scores)>=0, "逐图比分无效")
        stage = stages[mid]
        for side in (1,2):
            for pos in range(1,6):
                key = f"team{side}_player{pos}"
                nick = r[key].split(" (")[0].split(",")[0].strip()
                maps.append(dict(event=spec["event"],match=mid,map=r["game_id"],date=days[mid],
                                 stage=stage,venue="unknown" if stage=="group" else "arena",team=r[f"team{side}"],
                                 opponent=r[f"team{3-side}"],player=nick,rounds=sum(scores),kills=integer(r[key+"_kills"]),
                                 deaths=integer(r[key+"_deaths"]),adr=r[key+"_adr"],kast=r[key+"_kast"],
                                 win=int(scores[side-1]>scores[2-side])))
    return fixtures,maps,hashlib.sha256(path.read_bytes()).hexdigest()
