"""Conditional Major projections, isolated from observed inputs and current ranking.

Run: python -m analysis.major_projection
Opponent aggregate updates are map-weighted approximations, NOT future HLTV stats.
"""
import json
import math
from pathlib import Path

from htpm.aggregate import shrink, stratified_event_estimate
from htpm.core import dump_json
from htpm.pipeline import prepare
from htpm.aggregate import score

ROOT = Path(__file__).resolve().parents[1]


def project(player, config, rating, placement, award, maps, opponent_maps):
    """Apply an explicitly hypothetical new Major to one observed score record."""
    assert maps > 0 and all(0 <= n <= maps for n in opponent_maps.values())
    assert list(opponent_maps.values()) == sorted(opponent_maps.values())
    points = {None: 0, "MVP": 20, "EVP1": 14, "EVP2": 12, "EVP3": 10}[award]
    contributions = dict(player["contributions"])
    contributions["A"] = config["weights"]["A"]*100*(1-math.exp(-(player["award_points"]+points)/config["award_scale"]))
    events = [e for e in player["events"] if e["in_scope"]]
    hypothetical = {"name": "HYPOTHETICAL second Major", "maps": maps, "rating": rating, "tier": "Major"}
    est = stratified_event_estimate(events+[hypothetical], config)
    contributions["E"] = config["weights"]["E"]*est["score"]
    opponents = {}
    for k in config["opponent"]:
        old, n = player["opponents"][k], opponent_maps[k]
        total = old["maps"]+n
        # Same assumed rating in every nested opponent group, no inferred real cross-table.
        avg = (old["raw_rating"]*old["maps"]+rating*n)/total
        opponents[k] = shrink(avg, total, config, config["opponent_prior_maps"][k])
    contributions["O"] = config["weights"]["O"]*sum(config["opponent"][k]*o["score"] for k, o in opponents.items())
    personal = max(0, min(config["team_factor_cap"], (rating-config["team_rating_floor"])/config["team_rating_span"]))
    team_added = config["tiers"]["Major"]["weight"]*config["placement_points"].get(placement, 0)*personal*min(1, maps/config["team_maps_target"])
    team_total = sum(t["points"] for t in player["team_ledger"])+team_added
    contributions["T"] = config["weights"]["T"]*100*(1-math.exp(-team_total/config["team_scale"]))
    cc = config["consistency"]
    n0, ne = cc["prior_events"], len(events)+1
    positive = player["consistency"]["positive"]+int(rating >= cc["positive_threshold"])
    noncollapse = player["consistency"]["noncollapse"]+int(rating >= cc["noncollapse_threshold"])
    consistency = cc["positive_weight"]*(positive+n0*cc["positive_prior"])/(ne+n0)+(1-cc["positive_weight"])*(noncollapse+n0*cc["noncollapse_prior"])/(ne+n0)
    contributions["C"] = config["weights"]["C"]*100*consistency
    tier_coverage = sum(t["weight"]*est["tier_samples"][tier]["coverage"] for tier, t in config["tier_samples"].items())
    opponent_coverage = sum(config["opponent"][k]*min(1, opponents[k]["maps"]/target) for k, target in config["opponent_sample_targets"].items())
    volume = config["sample_tier_weight"]*tier_coverage+(1-config["sample_tier_weight"])*opponent_coverage
    annual_maps = player["annual"]["maps"]+maps
    shares = {"top10_share": opponents["10"]["maps"]/annual_maps,
              "top5_share": opponents["5"]["maps"]/annual_maps,
              "elite_share": (player["counts"]["elite_maps"]+maps)/annual_maps}
    difficulty = sum(config["difficulty_weights"][k]*min(1, shares[k]/target) for k, target in config["difficulty_targets"].items())
    contributions["N"] = config["weights"]["N"]*100*(config["sample_volume_weight"]*volume+(1-config["sample_volume_weight"])*difficulty)
    return {"name": player["name"], "rating": rating, "placement": placement, "award": award,
            "maps": maps, "opponent_maps": opponent_maps, "score": sum(contributions.values()),
            "contributions": contributions, "delta": sum(contributions.values())-player["score"]}


def run():
    data, config, _ = prepare()
    people = {p["id"]: p for p in score(data, config)["players"] if p["id"] in {"zywoo", "donk", "m0nesy"}}
    profiles = {
        "champion": ("1st", "MVP", 16, {"5": 8, "10": 12, "20": 16, "30": 16}),
        "finalist": ("2nd", "EVP1", 16, {"5": 8, "10": 12, "20": 16, "30": 16}),
        "semi": ("3-4th", "EVP2", 12, {"5": 6, "10": 8, "20": 12, "30": 12}),
        "quarter": ("5-8th", "EVP3", 10, {"5": 4, "10": 6, "20": 10, "30": 10}),
        "early": ("15-16th", None, 6, {"5": 0, "10": 2, "20": 6, "30": 6}),
    }
    def calc(pid, profile, rating):
        place, award, maps, opp = profiles[profile]
        return project(people[pid], config, rating, place, award, maps, opp)
    cases = [
        ("donk常规MVP，ZywOo早退", [("donk", "champion", 1.40), ("zywoo", "early", .90)]),
        ("donk极强MVP，ZywOo早退", [("donk", "champion", 1.60), ("zywoo", "early", .90)]),
        ("donk极强MVP，ZywOo八强EVP3", [("donk", "champion", 1.60), ("zywoo", "quarter", 1.15)]),
        ("m0NESY常规MVP，donk早退", [("m0nesy", "champion", 1.30), ("donk", "early", .90)]),
        ("m0NESY强势MVP，donk早退", [("m0nesy", "champion", 1.40), ("donk", "early", .90)]),
        ("m0NESY强势MVP，donk八强EVP3", [("m0nesy", "champion", 1.50), ("donk", "quarter", 1.15)]),
        ("m0NESY强势MVP，donk四强EVP2", [("m0nesy", "champion", 1.50), ("donk", "semi", 1.25)]),
        ("m0NESY极强MVP，donk亚军EVP1", [("m0nesy", "champion", 1.60), ("donk", "finalist", 1.30)]),
        ("m0NESY极强MVP，ZywOo早退", [("m0nesy", "champion", 1.60), ("zywoo", "early", .90)]),
        ("m0NESY亚军第一EVP，donk早退", [("m0nesy", "finalist", 1.40), ("donk", "early", .90)]),
        ("m0NESY高表现亚军第一EVP，donk早退", [("m0nesy", "finalist", 1.50), ("donk", "early", .90)]),
    ]
    rows = []
    for label, specifications in cases:
        projected = [calc(*spec) for spec in specifications]
        rows.append({"scenario": label, "players": projected, "gap": projected[0]["score"]-projected[1]["score"]})
    # A different, still plausible map/opposition schedule demonstrates non-universal thresholds.
    alternative = []
    for r in (1.60, 1.70):
        chaser = project(people["donk"], config, r, "1st", "MVP", 20, {"5": 12, "10": 16, "20": 20, "30": 20})
        leader = project(people["zywoo"], config, .90, "12-14th", None, 8, {"5": 4, "10": 6, "20": 8, "30": 8})
        alternative.append({"scenario": "更长强队赛程：donk冠军MVP %.2f，ZywOo早退 .90" % r,
                            "players": [chaser, leader], "gap": chaser["score"]-leader["score"]})
    thresholds = []
    for chaser, leader in [("donk", "zywoo"), ("m0nesy", "donk"), ("m0nesy", "zywoo")]:
        for profile, r in [("early", .90), ("quarter", 1.15), ("semi", 1.25), ("finalist", 1.30)]:
            target = calc(leader, profile, r)["score"]
            lo, hi = .8, 2.5
            reached = calc(chaser, "champion", hi)["score"] >= target
            if reached:
                for _ in range(60):
                    mid = (lo+hi)/2
                    if calc(chaser, "champion", mid)["score"] < target:
                        lo = mid
                    else:
                        hi = mid
            thresholds.append({"chaser": chaser, "leader": leader, "leader_profile": profile,
                               "leader_rating": r, "champion_uniform_rating_break_even": hi if reached else None,
                               "search_max_rating": 2.5, "reached_in_search_range": reached})
    award_only = {pid: {label: config["weights"]["A"]*100*math.exp(-p["award_points"]/config["award_scale"])*(1-math.exp(-points/config["award_scale"]))
                        for label, points in [("MVP", 20), ("EVP1", 14), ("EVP2", 12)]} for pid, p in people.items()}
    output = {"kind": "hypothetical_major_projection", "base_date": data["metadata"]["snapshot_as_of"],
              "assumptions": ["仅新增一届Major，其余比赛及待公布奖项不变；不是概率预测。",
                              "沿用现行参数，包括Major层20%占比及现有覆盖目标。",
                              "按情景指定参赛图数与嵌套Top N图数；假设新赛事各对手组Rating等于赛事Rating。",
                              "累计Rating以图数加权近似，非HLTV数据库精确重算；临界值不能当成真实保底线。",
                              "奖项、名次均为条件假设，不从Rating自动推定MVP/EVP。",
                              "本结果仅比较指定两人，不能据此排除其他选手反超。"],
              "baseline": {pid: p["score"] for pid, p in people.items()}, "award_only_gain": award_only,
              "scenarios": rows, "alternative_sample_scenarios": alternative, "conditional_break_even": thresholds}
    folder = ROOT/"output/scenarios"
    dump_json(folder/"major_projection.json", output)
    text = ["# 下一届Major条件情景分析", "", "基于2026-11-17快照；与真实评分数据隔离。", ""]
    text += ["- "+a for a in output["assumptions"]]
    text += ["", "| 情景 | 假设Rating（追赶者/领先者） | 追赶者得分 | 领先者得分 | 差值 |", "|---|---:|---:|---:|---:|"]
    text += ["| %s | %.2f / %.2f | %.2f | %.2f | %+.2f |" % (r["scenario"], r["players"][0]["rating"], r["players"][1]["rating"], r["players"][0]["score"], r["players"][1]["score"], r["gap"]) for r in rows]
    text += ["", "基础冠军/亚军情景为16图，其中Top5/10/20/30累计8/12/16/16图；早退情景6图，累计0/2/6/6图。四强12图，累计6/8/12/12图；八强10图，累计4/6/10/10图。累计组不能相加。", "",
             "替代样本：donk冠军20图，其中累计12/16/20/20图；ZywOo早退8图，累计4/6/8/8图。", ""]
    text += ["- %s：%.2f 对 %.2f，分差%+.2f。" % (r["scenario"], r["players"][0]["score"], r["players"][1]["score"], r["gap"]) for r in alternative]
    (folder/"major_projection.md").write_text("\n".join(text)+"\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
