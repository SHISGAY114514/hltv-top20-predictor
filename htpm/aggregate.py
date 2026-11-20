"""Aggregate observations are never expanded into fabricated map records."""
import copy
import math
from .core import HIGH, fingerprint, iso, normalize, number, require
from .event_tiers import POLICY, OVERRIDES, ADDITIONAL_MAJORS, classify

MODULES = ("A", "E", "O", "T", "C", "N")


def scoring_tier(tier, c):
    """Keep factual event tiers intact; only pool the 2024 model's scoring layer."""
    return c.get("scoring_tier_aliases", {}).get(tier, tier)


def validate(data, c):
    require(data["schema_version"] == "aggregate-1", "需要 aggregate-1 数据")
    meta = data["metadata"]
    require(meta["mode"] == "observed_aggregate", "需要真实汇总快照")
    require(meta["rating_version"] == c.get("rating_version", "3.0"), "Rating版本与模型配置不一致")
    require(meta["rating_version"] in {"2.1", "3.0"}, "不支持该Rating版本")
    aliases = c.get("scoring_tier_aliases", {})
    require(not aliases or (c.get("model_basis_year") == 2024 and aliases == {"Major": "Super-elite"}),
            "只允许有明确2024依据的Major评分层合并")
    require(iso(meta["cutoff"], "cutoff") == iso(meta["snapshot_as_of"], "snapshot"),
            "汇总快照不能回填到其他截止日期")
    require(meta["query_start"] == str(meta["year"]) + "-01-01", "年度起点错误")
    require(meta["query_start"] <= meta["cutoff"] <= meta["query_end"], "筛选日期错误")
    replay = meta.get("replay_of_fixed_weights", False)
    collection_date = meta["snapshot_as_of"]
    if replay:
        require(meta["year"] == 2025 and c["version"] == "HTPM-3.5"
                and meta["cutoff"] == meta["query_end"] == "2025-12-31", "仅支持3.5的2025完整年度回放")
        collection_date = meta["retrieved_on"]
        require(iso(collection_date,"retrieved_on") >= iso(meta["query_end"],"query_end"), "年度回放取数早于赛季结束")
    require(set(c["weights"]) == set(MODULES), "模块不匹配")
    require(abs(sum(c["weights"].values()) - 1) < 1e-9, "权重之和必须为1")
    for w in c["weights"].values():
        number(w, 0, 1, "weight")
    for k in ("award_scale", "event_map_cap", "team_scale", "team_rating_span", "team_maps_target"):
        number(c[k], .001, 10000, k)
    r = c["rating"]
    number(r["low"], 0, 10, "rating low")
    number(r["high"], r["low"] + .001, 10, "rating high")
    number(r["prior"], r["low"], r["high"], "prior")
    number(r["prior_maps"], .001, 10000, "prior maps")
    require(set(c["opponent"]) == {"5", "10", "20", "30"}, "对手分组错误")
    require(abs(sum(c["opponent"].values()) - 1) < 1e-9, "对手权重不为1")
    for w in c["opponent"].values():
        number(w, 0, 1, "opponent weight")
    number(c["event_prior_count"], .001, 1000, "event prior")
    number(c["sample_volume_weight"], 0, 1, "volume weight")
    for values in [c["difficulty_weights"]]:
        require(abs(sum(values.values())-1) < 1e-9, "样本子权重合计须为1")
        for v in values.values():
            number(v, 0, 1, "sample weight")
    for values in (c["difficulty_targets"], c["opponent_prior_maps"]):
        for v in values.values():
            number(v, .001, 10000, "sample parameter")
    if meta["year"] == 2026:
        if c.get("tier_policy") == POLICY:
            medals = c.get("event_medals", {})
            require(set(medals) == set(c["event_tiers"]), "奖章目录不完整")
            require(set(OVERRIDES) <= set(medals), "缺少用户指定赛事")
            for name, medal in medals.items():
                require(medal in {"gold", "silver", "bronze"}, "未知奖章类别")
                require(medal != "gold" or name in OVERRIDES or name in ADDITIONAL_MAJORS, "新增金色奖章赛事需要明确分级")
                require(c["event_tiers"][name] == classify(name, medal), "违反用户固定赛事分级: " + name)
        forced = {"IEM Cologne Major 2026": "Major", "IEM Kraków 2026": "Super-elite",
                  "XSE Pro League Guangzhou 2026": "Medium", "CS Asia Championships 2026": "Medium",
                  "FISSURE Playground 3": "Medium"}
        require(all(c["event_tiers"].get(n) == t for n, t in forced.items()), "违反用户指定赛事分档")
        require(all(t != "Super-elite" or n == "IEM Kraków 2026" for n, t in c["event_tiers"].items()),
                "2026仅克拉科夫允许Super-elite")
    for tier in c["event_tiers"].values():
        require(scoring_tier(tier, c) in c["tiers"], "未知赛事级别")
    for event, factor in c.get("honor_factors", {}).items():
        require(event in c["event_tiers"], "荣誉修正赛事不在白名单")
        number(factor, 0, 1, "honor factor")
    number(c["evp_tail_step"], 0, 1, "EVP tail step")
    number(c["evp_tail_floor"], 0, 1, "EVP tail floor")
    require(set(c["tier_samples"]) == set(c["tiers"]), "分层参数不完整")
    require(abs(sum(t["weight"] for t in c["tier_samples"].values())-1) < 1e-9, "分层权重合计须为1")
    for tier, t in c["tier_samples"].items():
        number(t["weight"], 0, 1, "tier weight")
        for k in ("prior_maps", "prior_events", "target_maps", "target_events"):
            number(t[k], .001, 10000, k)
        available = sum(scoring_tier(v, c) == tier for v in c["event_tiers"].values())
        # A historical replay keeps the original season's coverage denominators, even if the past calendar was smaller.
        if not replay:
            require(t["target_events"] <= available, "赛事覆盖目标不可达")
    for k in ("tier_coverage_map_weight", "sample_tier_weight"):
        number(c[k], 0, 1, k)
    require(set(c["opponent_sample_targets"]) == set(c["opponent"]), "对手覆盖参数不完整")
    for v in c["opponent_sample_targets"].values():
        number(v, .001, 10000, "opponent target")
    ids, mvps, evp_orders = set(), set(), set()
    for p in data["players"]:
        require(p["id"] not in ids, "重复选手")
        require(p.get("retrieved_on") == collection_date, "选手统计采集日期与快照不一致")
        ids.add(p["id"])
        require(bool(p["source"]) and bool(p["opponent_source"]), "缺少统计来源")
        require(type(p["annual"]["maps"]) is int and p["annual"]["maps"] > 0, "年度样本错误")
        number(p["annual"]["rating"], 0, 10, "annual rating")
        names = set()
        for e in p["events"]:
            require(e["name"] not in names, p["id"] + ": 重复赛事行")
            names.add(e["name"])
            require(type(e["maps"]) is int and e["maps"] > 0, "赛事地图数错误")
            number(e["rating"], 0, 10, "event rating")
            require(bool(e["source"]), "赛事缺少来源")
            require(e["in_scope"] == (e["name"] in c["event_tiers"]), "赛事白名单不一致")
            if e["in_scope"]:
                require(e["tier"] == c["event_tiers"][e["name"]], "赛事分档不一致")
                require(e["placement"] != "-", "未完赛赛事不能计入已完赛模型")
        require(sum(e["maps"] for e in p["events"]) == p["annual"]["maps"], p["id"] + ": 逐赛事地图数未与年度对齐")
        prev = 0
        for k in ("5", "10", "20", "30", "50"):
            o = p["opponents"][k]
            require(type(o["maps"]) is int and prev <= o["maps"] <= p["annual"]["maps"], "累计对手样本不嵌套")
            require((o["rating"] is None) == (o["maps"] == 0), "零样本与缺失Rating不一致")
            if o["rating"] is not None:
                number(o["rating"], 0, 10, "opponent rating")
            prev = o["maps"]
        seen = set()
        for a in p["awards"]:
            require(a["event"] not in seen, "同选手同赛事重复奖项")
            seen.add(a["event"])
            participation = a.get("participation_event", a["event"]) if replay else a["event"]
            if participation != a["event"]:
                require((a["event"], participation, a["type"]) ==
                        ("BLAST Open London 2025 Finals", "BLAST Open London 2025", "EVP"),
                        "无对应的跨阶段赛事荣誉")
            require(participation in names and a["event"] in c["event_tiers"], p["id"] + ": 获奖赛事缺少参赛数据")
            require(a["type"] in {"MVP", "EVP"} and bool(a["source"]), "奖项类型/来源错误")
            require(a["player_id"] == p["id"], "奖项身份不匹配")
            rank = a.get("evp_rank")
            if rank is not None:
                require(a["type"] == "EVP" and type(rank) is int and rank >= 1 and bool(a.get("order_evidence")),
                        "EVP顺位需有明确官方证据")
                require((a["event"], rank) not in evp_orders, "EVP顺位重复")
                evp_orders.add((a["event"], rank))
            verified = c.get("verified_evp_orders", {}).get(a["event"])
            if verified and a["type"] == "EVP":
                require(p["id"] in verified["evps"], "EVP身份与核实目录不一致")
                require(rank == verified["evps"].index(p["id"])+1, "EVP顺位与核实目录不一致")
            if a["type"] == "MVP":
                require(a["event"] not in mvps, "赛事存在多个MVP")
                mvps.add(a["event"])
    return True


def shrink(rating, maps, c, prior_maps=None):
    prior, n0 = c["rating"]["prior"], c["rating"]["prior_maps"] if prior_maps is None else prior_maps
    adjusted = (maps * rating + n0 * prior) / (maps + n0) if maps else prior
    return {"raw_rating": rating, "maps": maps, "adjusted": adjusted, "score": normalize(adjusted, c),
            "shrinkage_weight": maps / (maps + n0)}


def event_estimate(events, c):
    if not events:
        return {**shrink(None, 0, c), "effective_maps": 0, "effective_events": 0,
                "map_reliability": 0, "event_reliability": 0}
    # Each cell represents an aggregate, not observed identical per-map ratings.
    sizes = [min(e["maps"], c["event_map_cap"]) for e in events]
    weights = [c["tiers"][scoring_tier(e["tier"], c)]["weight"] for e in events]
    mass = sum(n*w for n, w in zip(sizes, weights))
    rating = sum(e["rating"]*n*w for e, n, w in zip(events, sizes, weights)) / mass
    effective = mass**2 / sum(n*w*w for n, w in zip(sizes, weights))
    stat = shrink(rating, effective, c)
    effective_events = mass**2 / sum((n*w)**2 for n, w in zip(sizes, weights))
    event_reliability = effective_events / (effective_events+c["event_prior_count"])
    reliability = stat["shrinkage_weight"] * event_reliability
    adjusted = c["rating"]["prior"] + reliability*(rating-c["rating"]["prior"])
    return {**stat, "maps": sum(e["maps"] for e in events), "effective_maps": effective,
            "effective_events": effective_events, "map_reliability": stat["shrinkage_weight"],
            "event_reliability": event_reliability, "shrinkage_weight": reliability,
            "adjusted": adjusted, "score": normalize(adjusted, c)}


def award_entry(a, c):
    tier = scoring_tier(c["event_tiers"][a["event"]], c)
    rank = a.get("evp_rank")
    key = "EVP"+str(rank) if a["type"] == "EVP" and rank in (1, 2) else a["type"]
    base = c["tiers"][tier][key]
    # Unknown ranks retain legacy base points; missing awards are never fabricated.
    tail = max(c["evp_tail_floor"], 1-c["evp_tail_step"]*(rank-3)) if a["type"] == "EVP" and rank and rank >= 3 else 1
    factor = c.get("honor_factors", {}).get(a["event"], 1)
    return {**a, "tier": tier, "base_points": base, "rank_factor": tail,
            "honor_factor": factor, "points": base*tail*factor}


def stratified_event_estimate(events, c):
    strata = {}
    for tier, params in c["tier_samples"].items():
        rows = [e for e in events if scoring_tier(e["tier"], c) == tier]
        cfg = {**c, "rating": {**c["rating"], "prior_maps": params["prior_maps"]},
               "event_prior_count": params["prior_events"]}
        stat = event_estimate(rows, cfg)
        capped_maps = sum(min(e["maps"], c["event_map_cap"]) for e in rows)
        map_coverage = min(1, capped_maps/params["target_maps"])
        event_coverage = min(1, len(rows)/params["target_events"])
        mw = c["tier_coverage_map_weight"]
        strata[tier] = {**stat, "events": len(rows), "capped_maps": capped_maps,
                        "nominal_weight": c["weights"]["E"]*params["weight"],
                        "effective_weight": c["weights"]["E"]*params["weight"]*stat["shrinkage_weight"],
                        "map_coverage": map_coverage, "event_coverage": event_coverage,
                        "coverage": mw*map_coverage+(1-mw)*event_coverage}
    weighted = lambda key: sum(params["weight"]*strata[t][key] for t, params in c["tier_samples"].items())
    # Missing strata stay at the prior. No reallocation to abundant lower-tier data.
    return {"raw_rating": None, "maps": sum(s["maps"] for s in strata.values()),
            "effective_maps": sum(s["effective_maps"] for s in strata.values()),
            "effective_events": sum(s["effective_events"] for s in strata.values()),
            "adjusted": weighted("adjusted"), "score": weighted("score"),
            "shrinkage_weight": weighted("shrinkage_weight"), "tier_samples": strata}


def score(data, c):
    validate(data, c)
    results = []
    for p in data["players"]:
        events = [e for e in p["events"] if e["in_scope"]]
        counts = {"main_maps": sum(e["maps"] for e in events),
                  "elite_maps": sum(e["maps"] for e in events if e["tier"] in HIGH),
                  "main_events": len(events), "elite_events": sum(e["tier"] in HIGH for e in events),
                  "top5_maps": p["opponents"]["5"]["maps"], "top10_maps": p["opponents"]["10"]["maps"]}
        e_stat = stratified_event_estimate(events, c)
        opponents = {k: shrink(o["rating"], o["maps"], c, c["opponent_prior_maps"][k]) for k, o in p["opponents"].items()}
        previous = 0
        for k, o in opponents.items():
            o["prior_maps"] = c["opponent_prior_maps"][k]
            o["nominal_weight"] = c["weights"]["O"]*c["opponent"].get(k, 0)
            o["effective_weight"] = o["nominal_weight"]*o["shrinkage_weight"]
        exclusive = {}
        for k in ("5", "10", "20", "30"):
            exclusive[k] = opponents[k]["maps"]-previous
            previous = opponents[k]["maps"]
        ledger = [award_entry(a, c) for a in p["awards"]]
        points = sum(a["points"] for a in ledger)
        team = []
        for e in events:
            place = c["placement_points"].get(e["placement"], 0)
            personal = max(0, min(c["team_factor_cap"], (e["rating"]-c["team_rating_floor"])/c["team_rating_span"]))
            participation = min(1, e["maps"]/c["team_maps_target"])
            base_points = c["tiers"][scoring_tier(e["tier"], c)]["weight"] * place * personal * participation
            factor = c.get("honor_factors", {}).get(e["name"], 1)
            team.append({"event": e["name"], "placement": e["placement"], "individual_factor": personal,
                         "participation_factor": participation,
                         "base_points": base_points, "honor_factor": factor, "points": base_points*factor})
        cc = c["consistency"]
        positive = sum(e["rating"] >= cc["positive_threshold"] for e in events)
        noncollapse = sum(e["rating"] >= cc["noncollapse_threshold"] for e in events)
        n0, ne = cc["prior_events"], len(events)
        positive_rate = (positive + n0*cc["positive_prior"]) / (ne+n0)
        noncollapse_rate = (noncollapse + n0*cc["noncollapse_prior"]) / (ne+n0)
        shares = {"top10_share": counts["top10_maps"]/p["annual"]["maps"],
                  "top5_share": counts["top5_maps"]/p["annual"]["maps"],
                  "elite_share": counts["elite_maps"]/p["annual"]["maps"]}
        coverage = {}
        tier_coverage = sum(t["weight"]*e_stat["tier_samples"][tier]["coverage"] for tier, t in c["tier_samples"].items())
        opponent_coverage = sum(c["opponent"][k]*min(1, opponents[k]["maps"]/target)
                                for k, target in c["opponent_sample_targets"].items())
        volume = c["sample_tier_weight"]*tier_coverage + (1-c["sample_tier_weight"])*opponent_coverage
        coverage = {"tier_coverage": tier_coverage, "opponent_coverage": opponent_coverage,
                    "opponent_exclusive_maps": exclusive}
        difficulty = sum(c["difficulty_weights"][k]*min(1, shares[k]/v) for k, v in c["difficulty_targets"].items())
        modules = {
            "A": 100 * (1-math.exp(-points/c["award_scale"])), "E": e_stat["score"],
            "O": sum(c["opponent"][k]*opponents[k]["score"] for k in c["opponent"]),
            "T": 100 * (1-math.exp(-sum(t["points"] for t in team)/c["team_scale"])),
            "C": 100*(cc["positive_weight"]*positive_rate + (1-cc["positive_weight"])*noncollapse_rate),
            "N": 100*(c["sample_volume_weight"]*volume + (1-c["sample_volume_weight"])*difficulty),
        }
        issues = [k + "样本不足" for k, minimum in c["eligibility"].items() if counts[k] < minimum]
        contrib = {k: c["weights"][k]*modules[k] for k in MODULES}
        results.append({"id": p["id"], "name": p["name"], "score": sum(contrib.values()) if events else None,
                        "rank": None, "eligible": not issues, "status": "provisional_aggregate",
                        "issues": issues, "annual": p["annual"], "counts": counts, "modules": modules,
                        "contributions": contrib, "event_rating": e_stat, "opponents": opponents,
                        "award_points": points, "awards": ledger, "team_ledger": team,
                        "title_count": sum(e["placement"] == "1st" for e in events),
                        "runnerup_count": sum(e["placement"] == "2nd" for e in events),
                        "consistency": {"events": ne, "positive": positive, "noncollapse": noncollapse},
                        "sample_quality": {"volume": volume, "difficulty": difficulty, "shares": shares, **coverage},
                        "effective_data_weights": {"E": c["weights"]["E"]*e_stat["shrinkage_weight"],
                            "O": c["weights"]["O"]*sum(c["opponent"][k]*opponents[k]["shrinkage_weight"] for k in c["opponent"]),
                            "C": c["weights"]["C"]*ne/(ne+n0)},
                        "events": p["events"], "source": p["source"], "event_source": p["event_source"],
                        "key_matches": None})
    # Eligibility is a transparent model gate, not an assertion of official HLTV qualification.
    results.sort(key=lambda p: (not p["eligible"], -(p["score"] if p["score"] is not None else -1), p["id"]))
    eligible = [p for p in results if p["eligible"] and p["score"] is not None]
    previous, rank = None, None
    for i, p in enumerate(eligible, 1):
        if previous is None or abs(previous-p["score"]) > 1e-9:
            rank = i
        p["rank"], previous = rank, p["score"]
    return {"version": c["version"], "metadata": data["metadata"], "weights": c["weights"],
            "data_sha256": fingerprint(data), "config_sha256": fingerprint(c), "players": results,
            "ranking_label": "当前完整候选池的模型排序" if not data["metadata"].get("pending_statistics_count") else "已采集子集排序，仍有候选待补统计"}


def sensitivity(data, c):
    configs = {"base": copy.deepcopy(c)}
    for k in MODULES:
        for f in (.8, 1.2):
            v = copy.deepcopy(c)
            v["weights"][k] *= f
            total = sum(v["weights"].values())
            v["weights"] = {key: w/total for key, w in v["weights"].items()}
            configs["weight_%s_%s" % (k, f)] = v
    for key, options in (("award_scale", (48, 72)), ("event_map_cap", (8, 32))):
        for value in options:
            v = copy.deepcopy(c); v[key] = value
            configs[key+"_"+str(value)] = v
    for value in (10, 40):
        v = copy.deepcopy(c); v["rating"]["prior_maps"] = value
        v["opponent_prior_maps"] = {k: n*value/c["rating"]["prior_maps"] for k, n in c["opponent_prior_maps"].items()}
        for t in v["tier_samples"].values():
            t["prior_maps"] *= value/c["rating"]["prior_maps"]
        configs["prior_maps_"+str(value)] = v
    for value in (1, 4):
        v = copy.deepcopy(c); v["event_prior_count"] = value
        for t in v["tier_samples"].values():
            t["prior_events"] *= value/c["event_prior_count"]
        configs["event_prior_count_"+str(value)] = v
    for value in (0, 1):
        v = copy.deepcopy(c); v["sample_volume_weight"] = value
        configs["sample_volume_weight_"+str(value)] = v
    v = copy.deepcopy(c)
    v["weights"] = {k: 0 if k == "T" else w/(1-c["weights"]["T"]) for k, w in c["weights"].items()}
    configs["no_team_bonus"] = v
    event = "BLAST Bounty 2026 Season 1 Finals"
    for factor in (.4, .8, 1):
        v = copy.deepcopy(c); v["honor_factors"][event] = factor
        configs["bounty_honors_"+str(factor)] = v
    v = copy.deepcopy(c); v["evp_tail_step"] = 0
    configs["flat_evp_tail"] = v
    for delta in (-.05, .05):
        v = copy.deepcopy(c)
        v["tier_samples"]["Big"]["weight"] += delta
        v["tier_samples"]["Elite"]["weight"] -= delta
        configs["tier_allocation_"+str(delta)] = v
    results = {}
    for name, cfg in configs.items():
        d = copy.deepcopy(data)
        for p in d["players"]:
            for e in p["events"]:
                e["tier"] = cfg["event_tiers"].get(e["name"])
        results[name] = score(d, cfg)
    players = []
    for p in results["base"]["players"]:
        observations = {name: next(x for x in r["players"] if x["id"] == p["id"])["rank"] for name, r in results.items()}
        ranks = [r for r in observations.values() if r is not None]
        players.append({"id": p["id"], "base_rank": p["rank"], "min_rank": min(ranks) if ranks else None,
                        "max_rank": max(ranks) if ranks else None, "scenario_ranks": observations})
    return {"label": "参数敏感性范围，不是统计置信区间，不包含未来赛事和缺失EVP的不确定性",
            "scenario_count": len(configs), "players": players}
