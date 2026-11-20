"""Replay the fixed HTPM-3.5 on 2025 HLTV aggregates. Run with python -m analysis.replay_aggregate_2025."""
import hashlib
import csv
import gzip
from collections import Counter, defaultdict
from itertools import combinations
from statistics import mean

from htpm.aggregate import score
from htpm.core import dump_json, fingerprint, require
from htpm.pipeline import ROOT, load
from htpm.core import HIGH


def check_snapshot(snap, catalog, config):
    """Verify early exclusions against the archive and HLTV's missing-map rosters."""
    players = snap["players"]
    require(set.union(*(set(pool) for pool in snap["pools"].values())) == set(players), "Pool mismatch")
    high = {e["official_event"]: e["event"] for e in catalog if e["tier"] in HIGH}
    archive_counts = defaultdict(Counter)
    archive_maps = defaultdict(set)
    with gzip.open(ROOT / "data/2025/stage_maps.csv.gz", "rt", encoding="utf8") as stream:
        for row in csv.DictReader(stream):
            event = row["event"]
            if event in high.values():
                pid = row["player"].casefold()
                archive_counts["snow" if pid == "snowzin" else pid][event] += 1
                archive_maps[event].add(row["map"])
    extra = Counter()
    audit = snap["eligibility_audit"]["events"]
    require(set(audit) == set(high), "Incomplete high-tier audit")
    for official, matches in audit.items():
        observed = len(archive_maps[high[official]])
        missing = matches["reported_maps"] - observed
        require(observed == matches["archived_maps"], "Archive total changed")
        require(missing == sum(m["missing_maps"] for m in matches["differences"]), "Unresolved map discrepancy")
        for match in matches["differences"]:
            require(match["match_sources"] and len(match["players"]) >= 10, "Missing lineups")
            extra.update({pid: match["missing_maps"] for pid in match["players"]})
    for pid, row in players.items():
        upper = sum(archive_counts[pid].values()) + extra[pid]
        if row["status"] == "screened":
            require(dict(archive_counts[pid]) == row["archived_elite_maps"]
                    and extra[pid] == row["possible_extra_maps"]
                    and upper == row["elite_maps_upper"] < config["eligibility"]["elite_maps"],
                    "Unverified eligibility exclusion: " + pid)
        else:
            require(row["status"] == "complete", "Missing data: " + pid)
            require(sum(e["maps"] for e in row["events"] if e["name"] in high) <= upper,
                    "Archive bound below observed maps: " + pid)
            if row["event_rows_reported"] is not None:
                require(len(row["events"]) == row["event_rows_reported"], "Missing event rows: " + pid)


def evaluate(players, truth):
    ranked = {p["id"]: p["rank"] for p in players if p["rank"] is not None}
    official = sorted(truth, key=truth.get)
    top = official[:20]
    order = sorted(ranked, key=lambda p:(ranked[p], p))
    differences = [abs(ranked[p]-truth[p]) for p in top if p in ranked]
    pairs = [(a,b) for a,b in combinations(official,2) if a in ranked and b in ranked]
    return {
        "eligible":len(ranked), "top20_hits":len(set(order[:20]) & set(top)),
        "top10_hits":len(set(order[:10]) & set(top[:10])),
        "exact_top20":sum(ranked.get(p)==truth[p] for p in top),
        "within_one_top20":sum(d<=1 for d in differences),
        "mae_top20_ranked":mean(differences) if differences else None,
        "mae_denominator":len(differences),
        "ordered_pairs_top30":sum(ranked[a]<ranked[b] for a,b in pairs),
        "tied_pairs":sum(ranked[a]==ranked[b] for a,b in pairs),
        "comparable_pairs":len(pairs), "all_pairs":len(list(combinations(official,2))),
        "missed":[p for p in top if p not in order[:20]],
        "false_positives":[p for p in order[:20] if p not in top],
        "actual30":{p:{"actual":truth[p],"predicted":ranked.get(p)} for p in official},
    }


def score_inputs(major_targets=None):
    snap=load("data/2025/aggregate_replay_3_5.json")
    catalog=load("data/reference/season_stage_catalog.json")["2025"]
    archive=load("data/2025/awards.json")
    tiers={e["official_event"]:e["tier"] for e in catalog}
    names={e["event"]:e["official_event"] for e in catalog}
    config=load("config/model.json")
    check_snapshot(snap, catalog, config)
    original_config=fingerprint(config)
    if major_targets:
        config["tier_samples"]["Major"].update(major_targets)
    # The saved discount explicitly names a 2026 event. No discount is documented for 2025.
    config.update(event_tiers=tiers,honor_factors={k:v for k,v in config["honor_factors"].items() if k in tiers})
    awards={}
    for event,record in archive.items():
        honors=[(record["mvp"],"MVP",None)]
        honors.extend((pid,"EVP",i) for i,pid in enumerate(record["evps"],1))
        honors.extend((pid,"EVP",None) for pid in record.get("unranked_evps",[]))
        for pid,kind,rank in honors:
            awards.setdefault(pid,[]).append(dict(event=names[event],player_id=pid,type=kind,evp_rank=rank,
                                                   source=record["source"],order_evidence=record["source"] if rank else None))
    meta={"mode":"observed_aggregate","rating_version":"3.0","year":2025,
          "cutoff":"2025-12-31","snapshot_as_of":"2025-12-31","query_start":"2025-01-01","query_end":"2025-12-31",
          "retrieved_on":snap["retrieved_on"],"replay_of_fixed_weights":True}
    data={"schema_version":"aggregate-1","metadata":meta,"players":[]}
    for pid,s in snap["players"].items():
        if s["status"]!="complete":
            continue
        p=dict(id=pid,name=s["name"],annual=s["annual"],opponents=s["opponents"],
               source=s["source"],opponent_source=s["source"],event_source=s["event_source"],
               retrieved_on=meta["retrieved_on"],awards=awards.get(pid,[]))
        p["events"]=[dict(e,tier=tiers.get(e["name"]),in_scope=e["name"] in tiers,source=s["event_source"])
                     for e in s["events"]]
        present={e["name"] for e in p["events"]}
        # London granted EVPs across its online group stage and its LAN finals.
        for a in p["awards"]:
            if a["event"]=="BLAST Open London 2025 Finals" and a["event"] not in present and "BLAST Open London 2025" in present:
                a["participation_event"]="BLAST Open London 2025"
        data["players"].append(p)
    return data,config,snap,original_config


def run(major_targets=None, write=True):
    data,config,snap,original_config = score_inputs(major_targets)
    result=score(data,config)["players"]
    # Calculate scores on held-out subsets without recomputing the rankings inside each fold.
    fold=lambda pid:int(hashlib.sha256(pid.encode()).hexdigest(),16)%5
    oof={}
    for i in range(5):
        test=[p for p in data["players"] if fold(p["id"])==i]
        for p in score({**data,"players":test},config)["players"]:
            oof[p["id"]]=(p["score"],p["eligible"])
    require(all(oof[p["id"]]==(p["score"],p["eligible"]) for p in result),"Fixed scores changed by fold")
    truth={**load("data/reference/official_top20_2025.json")["ranks"],**load("data/2025/boundary_ranks.json")["ranks"]}
    output={"model":"HTPM-3.5","config_sha256":original_config,"snapshot_sha256":fingerprint(snap),"scopes":{}}
    for key,members in snap["pools"].items():
        members=set(members)
        observed=[p for p in result if p["id"] in members]
        # 3.5 resolves equal scores by competition rank. Keep the same rule after restricting the pool.
        previous=None
        ranks=[]
        for i,p in enumerate(observed,1):
            rank=None
            if p["eligible"]:
                if previous is None or abs(previous-p["score"])>1e-9:
                    competition_rank=i
                rank=competition_rank
                previous=p["score"]
            ranks.append({"id":p["id"],"rank":rank,"score":p["score"],"counts":p["counts"],
                          "modules":p["modules"],"issues":p["issues"]})
        unavailable=sorted(pid for pid in members if snap["players"][pid]["status"]=="incomplete")
        screened=sorted(pid for pid in members if snap["players"][pid]["status"]=="screened")
        metrics = evaluate(ranks, truth)
        heldout = sorted((pid for pid in members if pid in oof and oof[pid][1]),
                         key=lambda pid: (-oof[pid][0], pid))
        require(heldout == [p["id"] for p in ranks if p["rank"] is not None], "Fold ranking mismatch")
        output["scopes"][key]={"candidates":len(members),"unavailable":unavailable,"screened":screened,
                               "metrics":metrics,"scores":ranks,"five_fold_order_verified":True}
    paired = output["scopes"]["shared_4_x"]["metrics"]["actual30"]
    pairs = [(a,b) for a,b in combinations(paired,2)
             if paired[a]["predicted"] is not None and paired[b]["predicted"] is not None]
    output["same_pairs"] = {"denominator":len(pairs),
                            "3.5":sum(paired[a]["predicted"] < paired[b]["predicted"] for a,b in pairs)}
    for version in ("4.1", "4.1.1"):
        other = (load("data/reference/benchmark_4_1_2025.json") if version == "4.1"
                 else load("output/forecast_4_1_1/scores.json")["replay"]["players"])
        output["same_pairs"][version] = sum(other[a]["predicted"] < other[b]["predicted"] for a,b in pairs)
    dest=ROOT/"output/replay_3_5_2025"
    if write:
        dump_json(dest/"scores.json",output)
    return output


if __name__=="__main__":
    for name,row in run()["scopes"].items():
        print(name,row["candidates"],row["metrics"],"incomplete",row["unavailable"])
