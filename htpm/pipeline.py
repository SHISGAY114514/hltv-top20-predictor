"""One build entry: source evidence -> candidates -> evaluation -> current reports."""
import copy
import json
from pathlib import Path
from .aggregate import score, sensitivity
from .aggregate_report import write_reports
from .candidates import build_candidates
from .core import dump_json, fingerprint
from .event_tiers import POLICY, classify
from .evaluation import write_evaluation

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))


def prepare():
    raw = load("data/2026/aggregate_snapshot.json")
    archive = load("data/2026/award_snapshot.json")
    awards = archive["awards"]
    evidence = load("data/reference/evp_orders_2026.json")
    orders = {e["event"]: e for e in evidence["events"]}
    if len(orders) != len(evidence["events"]):
        raise ValueError("Duplicate EVP event")
    for name, entry in orders.items():
        archived = {(a["player_id"], a["type"]) for a in awards if a["event"] == name}
        expected = {(entry["mvp"], "MVP")} | {(pid, "EVP") for pid in entry["evps"]}
        if len(entry["evps"]) != len(set(entry["evps"])) or archived != expected:
            raise ValueError("EVP article/archive mismatch: " + name)
    for a in awards:
        if a["type"] == "EVP" and a["event"] in orders:
            entry = orders[a["event"]]
            a["evp_rank"] = entry["evps"].index(a["player_id"])+1
            a["order_evidence"] = entry["source"]
    catalog = load("data/reference/event_tiers_2026_user.json")
    medals = {e["event"]: e["medal"] for e in catalog["events"]}
    if len(medals) != len(catalog["events"]) or set(medals) != {a["event"] for a in awards}:
        raise ValueError("Medal and award event catalogs differ")
    tiers = {name: classify(name, medal) for name, medal in medals.items()}
    if any(e["tier"] != tiers[e["event"]] for e in catalog["events"]):
        raise ValueError("Event catalog violates user policy")
    config = load("config/model.json")
    config.update({"event_tiers": tiers, "event_medals": medals, "tier_policy": POLICY,
                   "verified_evp_orders": orders,
                   "pending_awards": [event+" EVP" for event in evidence.get("pending", [])]})
    watchlist = load("config/watchlist.json")["player_ids"]
    pool = build_candidates(awards, raw["players"], config, watchlist,
                            selection_date=raw["retrieved_on"],
                            award_date=archive["retrieved_on"], order_date=evidence["verified_on"])
    chosen = {p["id"] for p in pool["candidates"]}
    players = [p for p in raw["players"] if p["id"] in chosen]
    for p in players:
        p["awards"] = [a for a in awards if a["player_id"] == p["id"]]
        p["annual"]["source"] = p["source"]
        p["opponent_source"] = p["source"]
        for e in p["events"]:
            e.update({"source": p["event_source"], "tier": tiers.get(e["name"]), "in_scope": e["name"] in tiers,
                      "exclusion_reason": None if e["name"] in tiers else "不在已颁MVP主赛事白名单"})
        p["key_matches"] = None
        p["awards_complete"] = False
    data = {"schema_version": "aggregate-1", "players": players, "metadata": {
        "year": 2026, "cutoff": raw["retrieved_on"], "snapshot_as_of": raw["retrieved_on"],
        "mode": "observed_aggregate", "rating_version": "3.0", "tier_policy": POLICY,
        "query_start": "2026-01-01", "query_end": raw["query_end"],
        "candidate_count": len(pool["candidates"]), "award_candidate_count": pool["award_candidate_count"],
        "pending_statistics_count": pool["pending_statistics_count"], "candidate_pool_sha256": fingerprint(pool),
        "evp_order_verified_on": evidence["verified_on"], "evp_order_events": len(orders),
        "limitations": [
            "候选池包含全部已存档MVP/EVP获得者及原有观察选手；已评估%d人，待补完整统计%d人；缺失数据不等于零分或落选。" % (len(players), pool["pending_statistics_count"]),
            "当前为截至采集日的模型排序，不是HLTV官方排名或模拟剩余赛程的年终预测。",
            "表现快照采集于%s；年度URL的12-31上限不是未来赛果。" % raw["retrieved_on"],
            "%d项赛事EVP顺位已核实；%d项赛事EVP待补。" % (len(orders), len(evidence.get("pending", []))),
            "缺少全池同口径季后赛、决赛、Arena及赛事档次×对手档次交叉统计，不虚构K。",
            "O使用全年累计Top N统计，主赛事部分使用23项白名单；累计组不能相加为独立样本。",
            "赛事分级遵守用户规则；Bounty S1荣誉系数0.60。参数不是官方公式，尚未进行完整历史回测。"]}}
    return data, config, pool


def build_reference():
    data, config, pool = prepare()
    result = score(data, config)
    folder = ROOT/"output/current"
    ranges = sensitivity(data, config)
    write_reports(result, ranges, config, folder)
    write_evaluation(result, ranges, folder)
    dump_json(folder/"input.json", data)
    dump_json(folder/"candidates.json", pool)
    dump_json(folder/"collection_audit.json", {
        "retrieved_on": data["metadata"]["snapshot_as_of"],
        "query_start": data["metadata"]["query_start"], "query_end": data["metadata"]["query_end"],
        "players": [{"id": p["id"], "source": p["source"], "event_source": p["event_source"],
                     "retrieved_on": p["retrieved_on"], "annual_maps": p["annual"]["maps"],
                     "event_maps": sum(e["maps"] for e in p["events"]), "event_count": len(p["events"]),
                     "maps_reconciled": sum(e["maps"] for e in p["events"]) == p["annual"]["maps"]}
                    for p in data["players"]]})
    from .candidate_report import write_candidates, write_bounty
    write_candidates(pool, folder)
    scenarios = {}
    for factor in (.4, .6, .8, 1):
        cfg = copy.deepcopy(config)
        cfg["honor_factors"]["BLAST Bounty 2026 Season 1 Finals"] = factor
        scenarios[str(factor)] = [{"id": p["id"], "name": p["name"], "rank": p["rank"],
                                  "score": p["score"]} for p in score(data, cfg)["players"]]
    dump_json(folder/"bounty.json", scenarios)
    write_bounty(scenarios, folder)
    manifest = {"version": config["version"], "sources": {str(p.relative_to(ROOT)): fingerprint(load(p))
                 for p in [ROOT/"config/model.json", ROOT/"config/watchlist.json",
                           ROOT/"data/2026/aggregate_snapshot.json", ROOT/"data/2026/award_snapshot.json",
                           ROOT/"data/reference/evp_orders_2026.json", ROOT/"data/reference/event_tiers_2026_user.json",
                           ROOT/"data/reference/rivals_s2_2026_honors.json"]},
                "candidate_count": len(pool["candidates"]), "scored_count": len(result["players"]),
                "pending_count": pool["pending_statistics_count"]}
    dump_json(folder/"manifest.json", manifest)
    print("Built: %d award candidates + %d watch; %d scored, %d awaiting statistics" %
          (pool["award_candidate_count"], pool["watch_count"], len(result["players"]), pool["pending_statistics_count"]))
    print("%s forecast: %s" % (config["version"], folder/"evaluation.html"))
    return result


def build():
    from .season_forecast import run
    result = run(build_reference())
    print("%s full ranking: %s" % (result["version"], ROOT/"output/forecast_4_1_1/ranking.html"))
    return result
