"""Recalculate the latest 2025-basis model using statistics through Nov 10.

This is a retrospective reconstruction retrieved on Nov 17, not an archived
prediction published before the event. Current production outputs stay intact.
"""
import copy
import json
from pathlib import Path

from htpm.aggregate import score, sensitivity
from htpm.core import dump_json, fingerprint, require
from htpm.pipeline import prepare

ROOT = Path(__file__).resolve().parents[1]
EVENT = "BLAST Rivals 2026 Season 2"
QUALIFIER = "PGL Cluj-Napoca 2027 Closed Qualifier"


def run():
    data, config, _ = prepare()
    current = score(data, config)
    source = json.loads((ROOT / "data/reference/hong_kong_pre_event_2026_stats.json").read_text(encoding="utf-8"))
    stats = {p["name"]: p for p in source["players"]}
    require(set(stats) == {p["name"] for p in data["players"]}, "Historical statistics must cover the same candidate pool")
    data, config = copy.deepcopy(data), copy.deepcopy(config)
    removed_events = []
    for p in data["players"]:
        historical = stats[p["name"]]
        p["annual"] = {**historical["annual"], "source": source["sources"]["annual"]}
        p["opponents"] = {g: historical[g] for g in ("5", "10", "20", "30", "50")}
        p["source"] = source["sources"]["annual"]
        p["opponent_source"] = source["sources"]
        p["event_source"] = p["event_source"].replace("2026-12-31", source["statistics_through"])
        removed = [e for e in p["events"] if e["name"] == EVENT or e["name"] == QUALIFIER]
        removed_events.extend({"player": p["name"], **e} for e in removed)
        p["events"] = [e for e in p["events"] if e not in removed]
        for e in p["events"]:
            e["source"] = p["event_source"]
            if p["id"] == "tenzy" and e["name"] == "PGL Cluj-Napoca 2027 Open Qualifier 1":
                e.update(maps=3, rating=1.40, historical_scope_note="Only 3 maps were played through Nov 10; final placement is unused outside main-event scope")
        p["awards"] = [a for a in p["awards"] if a["event"] != EVENT]
        require(sum(e["maps"] for e in p["events"]) == p["annual"]["maps"], p["name"] + ": historical map reconciliation failed")
    for key in ("event_tiers", "event_medals", "verified_evp_orders"):
        config[key].pop(EVENT, None)
    # Keep collection date truthful: these historical-date filters were read Nov 17.
    # The model's old metadata schema calls its collection day `cutoff`; the
    # historical observation boundary is recorded separately and in the report.
    data["metadata"].update(
        statistics_through=source["statistics_through"],
        query_filter_end=source["statistics_through"],
        reconstruction=True,
        reconstruction_method="Latest 2025-basis parameters; observed date-filtered annual/opponent statistics; Hong Kong event and all its awards excluded",
        evp_order_events=len(config["verified_evp_orders"]),
        limitations=[
            "回溯重算：统计范围截至2026-11-10，采集于2026-11-17；不是当时已发布的历史预测。",
            "沿用最新HTPM 3.5的全部数学参数和赛事分档；剔除香港整站比赛、冠军、MVP和EVP。",
            "年度及累计Top5/10/20/30/50统计从HLTV历史日期筛选页重新读取，未从赛后Rating按图数倒减。",
            "同期预选赛按截止日核对：frozen/zweih/tenzy的封闭预选赛排除，tenzy公开预选赛仅保留截止日前3图。",
            "关键阶段全池数据尚缺；模型分数不是HLTV官方分数，也不是入选概率。",
        ],
    )
    result = score(data, config)
    ranges = sensitivity(data, config)
    folder = ROOT / "output/hong_kong_pre_event"
    dump_json(folder / "input.json", data)
    dump_json(folder / "config.json", config)
    dump_json(folder / "scores.json", result)
    dump_json(folder / "sensitivity.json", ranges)
    after = {p["id"]: p for p in current["players"]}
    comparison = []
    for p in result["players"]:
        q = after[p["id"]]
        comparison.append({"id": p["id"], "name": p["name"], "before_rank": p["rank"], "before_score": p["score"], "after_rank": q["rank"], "after_score": q["score"],
                           "contribution_change": {k: q["contributions"][k] - p["contributions"][k] for k in config["weights"]}})
    dump_json(folder / "comparison.json", comparison)
    dump_json(folder / "audit.json", {"statistics_through": source["statistics_through"], "retrieved_on": source["retrieved_on"], "source_sha256": fingerprint(source), "same_model_parameters": True,
                                     "candidate_count": len(result["players"]), "eligible_count": sum(p["eligible"] for p in result["players"]), "all_annual_event_maps_reconciled": True, "removed_events": removed_events,
                                     "extra_event_sources": [p["event_source"] for p in data["players"] if p["id"] in ("frozen", "tenzy", "zweih")]})
    lines = ["# BLAST香港开赛前TOP20：2025依据版最新模型回溯重算", "", *data["metadata"]["limitations"], "",
             "58名候选全部重新评分；%d人达到模型样本门槛。" % sum(p["eligible"] for p in result["players"]), "",
             "| 赛前名次 | 选手 | 赛前得分 | 香港赛后名次 | 赛后得分 | 赛后得分变化 |", "|---:|---|---:|---:|---:|---:|"]
    for p in comparison:
        if p["before_rank"] is not None:
            lines.append("| %d | %s | %.4f | %s | %.4f | %+.4f |" % (p["before_rank"], p["name"], p["before_score"], p["after_rank"], p["after_score"], p["after_score"]-p["before_score"]))
    lines += ["", "## 统计来源", ""] + ["- [%s](%s)" % (g, u) for g, u in source["sources"].items()]
    lines += ["", "复算：`python -B -m analysis.hong_kong_pre_event`。生产目录output/current和既有比较文件未修改。", ""]
    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:32]))
    return result


if __name__ == "__main__":
    run()
