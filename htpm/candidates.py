"""Award-led candidate discovery; missing statistics never imply rejection."""
import math
from collections import defaultdict
from .aggregate import award_entry

GROUPS = {
    "priority": "优先完整评估：MVP、多项荣誉或Elite以上EVP",
    "big_evp": "补充评估：单项Big EVP",
    "medium_evp": "补充评估：单项Medium EVP",
    "watch": "无已确认奖项的原有观察名单",
}


def build_candidates(awards, players, config, watchlist, selection_date=None, award_date=None, order_date=None):
    groups = defaultdict(list)
    seen = set()
    for award in awards:
        key = (award["player_id"], award["event"])
        if key in seen:
            raise ValueError("Duplicate player/event award: " + str(key))
        seen.add(key)
        groups[award["player_id"]].append(award_entry(award, config))
    stats = {p["id"]: p for p in players}
    names = {a["player_id"]: a["player"] for a in awards}
    names.update({p["id"]: p["name"] for p in players})
    for pid in watchlist:
        if pid not in stats:
            raise ValueError("Watchlist requires existing evidence: " + pid)
    candidates = []
    for pid in set(groups) | set(watchlist):
        ledger = groups[pid]
        mvp = sum(a["type"] == "MVP" for a in ledger)
        evp = len(ledger)-mvp
        high = sum(a["type"] == "EVP" and a["tier"] in {"Major", "Super-elite", "Elite"} for a in ledger)
        group = "priority" if mvp or high or len(ledger) >= 2 else "big_evp" if any(a["tier"] == "Big" for a in ledger) else "medium_evp" if ledger else "watch"
        points = sum(a["points"] for a in ledger)
        candidates.append({"id": pid, "name": names[pid], "group": group,
                           "membership": "award_candidate" if ledger else "watchlist",
                           "mvp_count": mvp, "evp_count": evp, "high_tier_evp_count": high,
                           "award_points": points,
                           "A_contribution": config["weights"]["A"]*100*(1-math.exp(-points/config["award_scale"])),
                           "awards": sorted(ledger, key=lambda a: (-a["points"], a["event"])),
                           "statistics_status": "available" if pid in stats else "pending_collection",
                           "statistics_as_of": stats[pid].get("retrieved_on") if pid in stats else None,
                           "total_score": None, "rank": None,
                           "note": "候选名单按荣誉梳理，不生成全年总分或名次；缺失统计不等于零分。"})
    candidates.sort(key=lambda p: (list(GROUPS).index(p["group"]), -p["award_points"], p["id"]))
    return {"schema_version": "candidate-pool-1", "selection_date": selection_date,
            "award_snapshot_as_of": award_date, "evp_order_verified_on": order_date,
            "policy": "全部已存档MVP/EVP获得者自动纳入；样本门槛只用于评分，不用于候选排除。",
            "priority_note": "分组及组内荣誉排序用于安排评估，不代表入榜概率；各档均为正式候选。",
            "pending_awards": config.get("pending_awards", []),
            "award_count": len(awards), "award_candidate_count": len(set(a["player_id"] for a in awards)),
            "watch_count": sum(p["membership"] == "watchlist" for p in candidates),
            "pending_statistics_count": sum(p["statistics_status"] == "pending_collection" for p in candidates),
            "groups": GROUPS, "candidates": candidates}
