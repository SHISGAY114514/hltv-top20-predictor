"""Recompute both frozen releases and their paired, fixed-cohort diagnostics."""
import argparse
import csv
import hashlib
import io
import json
import os
import platform
import sys
from datetime import date
from pathlib import Path

from htpm.core import fingerprint, require
from htpm.event_policy import apply_stage_context, attach_vps, event_policy
from htpm.forecast_4_2 import atomic_text, calculate, publish, settings
from htpm.frozen_4_4 import input_hashes
from htpm.pipeline import ROOT, load
from htpm.season import features, season_inputs

DAY = date(2026, 11, 17)
SCENARIOS = {
    "legacy_stage": "恢复旧赛段",
    "nested_opponents": "恢复嵌套 O",
    "unknown_6_10": "未匹配全部假设为第 6–10 名",
    "no_vp": "移除已核实 VP 并恢复无奖规则",
    "equal_tiers": "E、K 五档份额均为 20%",
    "no_H": "移除 H",
    "no_R": "移除 R",
    "no_HR": "同时移除 H、R",
}


def write_csv(path, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, "\ufeff" + stream.getvalue())


def json_file(path, data):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def keyed(result):
    players = {p["id"]: p for p in result["players"]}
    require(len(players) == len(result["players"]), "Duplicate player ID")
    return players


def rank(scores):
    return {pid: i for i, pid in enumerate(sorted(scores, key=lambda k: (-scores[k], k)), 1)}


def fixed_scores(result, ids, omit=()):
    players = keyed(result)
    return {pid: sum(v for k, v in players[pid]["contributions"].items() if k not in omit) for pid in ids}


def compare(old, new):
    left, right = keyed(old), keyed(new)
    ids = [pid for pid, p in left.items() if p["eligible"]]
    require(len(ids) == 177 and set(ids) <= right.keys()
            and fingerprint(sorted(ids)) == load("config/season_4_4.json")["base_cohort_hash"],
            "Frozen cohort mismatch")
    scores = fixed_scores(new, ids)
    ranks = rank(scores)
    rows = []
    for pid in sorted(ids, key=ranks.get):
        a, b = left[pid], right[pid]
        delta = b["score"] - a["score"]
        row = dict(id=pid, name=b["name"], old_rank=a["rank"], new_rank=ranks[pid],
                   rank_gain=a["rank"]-ranks[pid], natural_rank=b["rank"], eligible_4_4=b["eligible"],
                   old_score=a["score"], new_score=b["score"], score_delta=delta)
        parts = {}
        for k, value in a["contributions"].items():
            after = b["contributions"][k]
            parts[k] = after - value
            row.update({k+"_old": value, k+"_new": after, k+"_delta": parts[k]})
        require(abs(sum(parts.values()) - delta) < 1e-10, "Score attribution does not reconcile")
        for k in ("main", "playoff", "elite_playoff", "pressure_top10", "arena", "final"):
            row[k+"_maps_old"] = a["details"][k]["maps"]
            row[k+"_maps_new"] = b["details"][k]["maps"]
        row.update(b["vrs_coverage"])
        row["H_available"] = b["legacy_score"] is not None
        row["R_available"] = b["published"] is not None
        row["reason"] = "、".join(f"{k} {parts[k]:+.4f}" for k in sorted(parts, key=lambda k: -abs(parts[k]))
                                if abs(parts[k]) >= .00005) or "各项变动小于 0.00005"
        row["passed"] = ",".join(k for k in ids if left[k]["rank"] < a["rank"] and ranks[k] > ranks[pid])
        row["passed_by"] = ",".join(k for k in ids if left[k]["rank"] > a["rank"] and ranks[k] < ranks[pid])
        rows.append(row)
    return rows


def event_overlap(new, ids):
    """Leave out one event at a time, holding field factors and other events' ratings fixed."""
    config = settings()[1]
    config.update(load("config/season_4_3.json"))
    config.update(load("config/season_4_4.json"))
    inputs = season_inputs(2026, True, config["stage_exceptions"], True)
    catalog, awards, stats, names, finalists = inputs
    config["event_policies"] = event_policy(inputs, 2026, config)
    apply_stage_context(inputs, config["event_policies"])
    attach_vps(inputs, load("data/reference/official_vps_4_3.json")["2026"], DAY.isoformat())
    people, base, rows = keyed(new), load("config/model.json"), []
    for event in catalog:
        def remaining(mapping):
            return {k: v for k, v in mapping.items() if k != event}
        reduced = remaining(catalog), remaining(awards), {pid: remaining(events) for pid, events in stats.items()}, names, remaining(finalists)
        alt = {p["id"]: p for p in features(reduced, base, config, 2026)}
        for pid in ids:
            if event not in stats.get(pid, {}):
                continue
            person = people[pid]
            award = next((a["kind"] for a in person["awards"] if a["event"] == event), "")
            row = dict(id=pid, event=event, award=award)
            for k in ("A", "E", "K", "P"):
                row[k] = (person["features"][k]-alt[pid]["features"][k])*new["weights"][k]/100 if pid in alt else None
            rows.append(row)
    return rows


def award_ratings(result, raw):
    archive = load("data/2026/award_snapshot.json")
    awards = {(a["player_id"], a["event"]): a for a in archive["awards"]}
    rows = []
    for p in result["players"]:
        events = {e["name"]: e for e in raw.get(p["id"], {}).get("events", [])}
        for award in p["awards"]:
            event = award["event"]
            a = awards.get((p["id"], event), {})
            stats = events.get(event, {})
            rows.append(dict(id=p["id"], event=event, award=award["kind"], evp_order=award["position"],
                             award_source=award["source"], award_snapshot_source=a.get("source"),
                             award_snapshot_rating=a.get("rating"),
                             award_snapshot_date=a.get("retrieved_on", archive["retrieved_on"]) if a else None,
                             event_rating=stats.get("rating"), maps=stats.get("maps"), placement=stats.get("placement"),
                             rating_version="HLTV Rating 3.0" if stats else None,
                             rating_snapshot_date=raw[p["id"]]["retrieved_on"] if stats else None,
                             rating_source=raw[p["id"]]["event_source"] if stats else None))
    return rows


def summary(rows, variants, overlap, official_count):
    ids = {r["id"] for r in rows}
    top = {r["id"] for r in rows[:20]}
    old_top = {r["id"] for r in rows if r["old_rank"] <= 20}
    n = len(rows)
    rho = 1 - 6*sum(r["rank_gain"]**2 for r in rows)/(n*(n*n-1))
    inversions = sum(a["old_rank"] > b["old_rank"] for i, a in enumerate(rows) for b in rows[i+1:])
    names = lambda values: "、".join(sorted(values)) or "无"
    gap = lambda a, b: rows[a-1]["new_score"]-rows[b-1]["new_score"]
    total = sum(r["total"] for r in rows)
    unmatched = sum(r["unmatched"] for r in rows)
    by_id = {r["id"]: r for r in rows}
    jame = by_id["jame"]
    top_moves = sum(r["rank_gain"] != 0 for r in rows[:20])
    text = ["# HTPM 4.4 与 4.3 · 2026-11-17", "",
            f"固定队列有 {n} 人，覆盖 23 项赛事，其中一项为 Major。Top 20 新入 {len(top-old_top)} 人"
            f"（{names(top-old_top)}），退出 {len(old_top-top)} 人（{names(old_top-top)}），{top_moves} 人名次变化。"
            f"Spearman ρ = {rho:.8f}，{n*(n-1)//2} 对选手中有 {inversions} 对交换顺序。",
            "", "|4.4|选手|4.3|旧分|新分|分差|分项贡献变动（总分单位）|",
            "|---:|---|---:|---:|---:|---:|---|"]
    for r in rows[:22]:
        text.append("|{new_rank}|{name}|{old_rank}|{old_score:.4f}|{new_score:.4f}|{score_delta:+.4f}|{reason}|".format(**r))
    text += ["", f"第 4–7 名依次为 {', '.join(r['name'] for r in rows[3:7])}，相邻分差为 "
             f"{gap(4,5):.4f}、{gap(5,6):.4f}、{gap(6,7):.4f}。第 20 名 {rows[19]['name']} "
             f"领先第 21 名 {rows[20]['name']} {gap(20,21):.4f} 分。",
             "", f"4.3 的第 5、6 名相差 {by_id['flamez']['old_score']-by_id['kscerato']['old_score']:.4f} 分。"
             f"互斥对手档让 KSCERATO 的 O 贡献变化 {by_id['kscerato']['O_delta']:+.4f}，"
             f"flameZ 为 {by_id['flamez']['O_delta']:+.4f}。"
             f"sh1ro 计入季后赛的地图从 {by_id['sh1ro']['playoff_maps_old']} 减到 {by_id['sh1ro']['playoff_maps_new']}，"
             f"K 贡献变化 {by_id['sh1ro']['K_delta']:+.4f}。"
             f"原票线分差为 {by_id['heavygod']['old_score']-by_id['try']['old_score']:.4f} 分。",
             "", "## 名次波动与敏感性", ""]
    for gain in (max(r["rank_gain"] for r in rows), min(r["rank_gain"] for r in rows)):
        for r in rows:
            if r["rank_gain"] == gain:
                text.append(f"- {r['name']} 从第 {r['old_rank']} 到第 {r['new_rank']} 名，净变化 {gain:+d} 位。{r['reason']}。")
    text += ["", f"以选手地图为分母，VRS 可解析 {total-unmatched}/{total}（{1-unmatched/total:.1%}），"
             f"第 1–5 名 {sum(r['top5'] for r in rows)}，第 6–10 名 {sum(r['six_to_ten'] for r in rows)}，"
             f"未匹配 {unmatched}，明确前十以外 {sum(r['known_outside'] for r in rows)}。同一张比赛地图可有多名入围选手。"
             f"年度 HLTV 对手表覆盖 {official_count}/{n} 人。H 有年度汇总输入 {sum(r['H_available'] for r in rows)} 人，"
             f"R 有公开阶段表输入 {sum(r['R_available'] for r in rows)} 人。",
             "", "|4.4 单项消融或压力测试|Top 20 重合|最大位移|第 4–7 名|第 20 / 21 名|", "|---|---:|---:|---|---|"]
    for tag, label in SCENARIOS.items():
        ranks = rank(variants[tag])
        order = sorted(ids, key=ranks.get)
        shift = max(abs(ranks[r["id"]]-r["new_rank"]) for r in rows)
        text.append(f"|{label}|{len(top & set(order[:20]))}/20|{shift}|{', '.join(order[3:7])}|{order[19]} / {order[20]}|")
    text += ["", "分档测试仅改变 E、K 中的五档年度份额。恢复旧赛段会同时影响季后赛样本、争奖质量及其下游分项。"
             "未匹配全归 6–10 是极端假设，连同 K、N 的强敌样本一起重算。H 在上述核心变动后重新对齐。"
             "移除 H、R 的三行则直接从同一人的总分扣除相应校正。",
             "", f"Jame 计入已核实 VP 时为第 {jame['new_rank']} 名。关闭 VP、恢复无奖规则后为第 {jame['no_vp_rank']} 名，"
             f"总分相差 {jame['new_score']-jame['no_vp_score']:.4f}。上述情景都保留相同的 177 人。",
             "", "## 同站贡献", ""]
    for pid in ("zywoo","donk"):
        observed = [r for r in overlap if r["id"] == pid and r["award"]]
        simultaneous = [r for r in observed if all(r[k] is not None and r[k] > 0 for k in ("A","E","K","P"))]
        multiple = sum(sum(r[k] is not None and r[k] > 0 for k in ("A","E","K","P")) >= 2 for r in observed)
        text.append(f"- {pid} 的 {len(observed)} 个获奖站中，移除单站后有 {multiple} 站至少两项下降，"
                    f"{len(simultaneous)} 站 A/E/K/P 全部下降。")
    text += ["", "逐站移除结果见 event_overlap.csv，正数是加入该站后增加的加权分。各次反事实使用同一站外资料，"
             "保留其余赛事的场地和阵容系数。A 有饱和、P 选择高峰，逐站差不能相加。重合说明同一证据影响多个分项，"
             "据此无法识别应扣多少分。全年 VP 总量未知，已核实的 Jame 一站沿用模型的 strong VP 参数 40%。",
             "", "官方对手榜与赛前月度 VRS 口径不同。comparison.csv 的互斥覆盖来自 23 项赛事。"
             "hltv_opponents.json 单列已有年度 HLTV 累计档，缺失者为 null，各档地图不能相加。"
             "新加坡尚未参赛。分数和稳定性指标均衡量本快照的模型差异，预测误差需等待独立结果检验。"]
    return "\n".join(text)+"\n"


def run(dest=None):
    revision = load("config/season_4_4.json")
    old = calculate(today=DAY, model="4.3")
    archive = publish(old, verify=True)
    require(archive.parent.name == revision["base_snapshot"], "Wrong 4.3 archive")
    new = calculate(today=DAY, model="4.4")
    require(old["scope"] == new["scope"] and len(new["scope"]) == 23 and old["cutoff"] == new["cutoff"] == DAY.isoformat()
            and old["state"] == new["state"] == "snapshot", "Snapshot scope mismatch")
    rows = compare(old, new)
    ids = [r["id"] for r in rows]
    variants = {}
    for tag in SCENARIOS:
        if tag in ("no_H", "no_R", "no_HR"):
            variants[tag] = fixed_scores(new, ids, tuple(tag.removeprefix("no_")))
        else:
            variants[tag] = fixed_scores(calculate(today=DAY, model="4.4", scenario=tag), ids)
        ranks = rank(variants[tag])
        for row in rows:
            row[tag+"_rank"] = ranks[row["id"]]
            row[tag+"_score"] = variants[tag][row["id"]]
    # Report both paths between the two policies. No diagnostic enters scoring.
    for row in rows:
        old_score, new_score = row["old_score"], row["new_score"]
        stage_only, opponent_only = row["nested_opponents_score"], row["legacy_stage_score"]
        row["stage_only_delta"] = stage_only - old_score
        row["opponent_only_delta"] = opponent_only - old_score
        row["joint_interaction"] = (new_score - stage_only) - (opponent_only - old_score)
        require(abs(row["stage_only_delta"] + row["opponent_only_delta"] + row["joint_interaction"]
                    - row["score_delta"]) < 1e-10, "Policy attribution does not reconcile")
    overlap = event_overlap(new, ids)
    hashes = input_hashes()
    if dest is None:
        dest = ROOT/"output/comparison_4_4"
        paths = [archive, publish(new)]
        publish(new, verify=True)
    else:
        dest = dest.resolve()
        paths = []
        for result, model in ((old,"4.3"), (new,"4.4")):
            paths.append(publish(result, dest=dest/model))
            publish(result, verify=True, dest=dest/model)
    write_csv(dest/"comparison.csv", rows)
    write_csv(dest/"event_overlap.csv", overlap)
    raw = {p["id"]: p for p in load("data/2026/aggregate_snapshot.json")["players"]}
    write_csv(dest/"award_rating.csv", award_ratings(new, raw))
    json_file(dest/"hltv_opponents.json", {pid: raw[pid]["opponents"] if pid in raw else None for pid in ids})
    json_file(dest/"manifest.json", dict(cutoff=old["cutoff"], scope=old["scope"], cohort=len(ids),
              cohort_hash=fingerprint(sorted(ids)), natural_additions=sorted(k for k,p in keyed(new).items() if p["eligible"] and k not in ids),
              natural_losses=[r["id"] for r in rows if not r["eligible_4_4"]], python=sys.version, architecture=platform.architecture()[0],
              pythonhashseed=os.environ.get("PYTHONHASHSEED"), randomness="none", shared_inputs=hashes, input_hash=fingerprint(hashes),
              revision_config_sha256=hashlib.sha256((ROOT/"config/season_4_4.json").read_bytes()).hexdigest(),
              models=[old["version"],new["version"]], snapshots=[p.parent.name for p in paths],
              baseline_verification="live 4.3 scores.json, ranking.md, events.md and latest.md matched archive"))
    atomic_text(dest/"分析.md", summary(rows, variants, overlap, sum(pid in raw for pid in ids)))
    print(dest, len(rows), [p.parent.name for p in paths])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dest", type=Path, nargs="?", help="Optional directory for both full rebuilds and diagnostics")
    run(parser.parse_args().dest)
