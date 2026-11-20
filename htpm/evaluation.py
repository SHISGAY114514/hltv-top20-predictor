"""Evidence-based per-player explanations and exact adjacent-score comparisons."""
import html
from .core import fmt, dump_json

LABELS = {"A": "个人荣誉", "E": "分层赛事表现", "O": "强队对抗", "T": "团队贡献", "C": "跨赛事稳定性", "N": "样本质量"}
TIERS = {"Major": "Major", "Super-elite": "超级精英", "Elite": "精英", "Big": "大型", "Medium": "中型"}


def explain(result, sensitivity):
    ranked = [p for p in result["players"] if p["rank"] is not None]
    ranges = {p["id"]: p for p in sensitivity["players"]}
    boundary = next((p for p in ranked if p["rank"] == 20), None)
    output = []
    for p in result["players"]:
        paragraphs = []
        mvp = sum(a["type"] == "MVP" for a in p["awards"])
        evp = len(p["awards"])-mvp
        awards = sorted(p["awards"], key=lambda a: (-a["points"], a["event"]))
        highlights = "；".join("%s（%s，%s%s，%.2f荣誉分）" % (a["event"], TIERS[a["tier"]], a["type"], "#"+str(a["evp_rank"]) if a.get("evp_rank") else "", a["points"]) for a in awards[:4])
        paragraphs.append("荣誉：%d MVP、%d EVP；累计荣誉原始分%.2f，折算为总分中的%.2f分。%s" % (mvp, evp, p["award_points"], p["contributions"]["A"], "主要支撑是"+highlights+"。" if awards else "当前档案没有已确认奖项，不能凭高Rating自动补记EVP。"))
        bounty = next((a for a in awards if a["event"] == "BLAST Bounty 2026 Season 1 Finals"), None)
        if bounty:
            paragraphs.append("Bounty S1特殊规则：该项%s按%.2f×%.2f×%.2f=%.2f计入荣誉原始分；其他赛事荣誉不受此系数影响。" % (bounty["type"], bounty["base_points"], bounty["rank_factor"], bounty["honor_factor"], bounty["points"]))
        tier_text = []
        for tier, t in p["event_rating"]["tier_samples"].items():
            tier_text.append("%s %d场/%d图，R %s，可靠性%.1f%%" % (TIERS[tier], t["events"], t["maps"], fmt(t["raw_rating"]), 100*t["shrinkage_weight"]))
        paragraphs.append("赛事与覆盖："+"；".join(tier_text)+"。分层表现E贡献%.2f分；缺失层留在先验，不能用其他档次图数代替。" % p["contributions"]["E"])
        paragraphs.append("强队对抗："+"；".join("Top%s R %s/%d图，收缩后%.3f" % (k, fmt(p["opponents"][k]["raw_rating"]), p["opponents"][k]["maps"], p["opponents"][k]["adjusted"]) for k in ("5", "10", "20", "30"))+"。O贡献%.2f分。累计Top组互相嵌套，不能相加为独立地图数。" % p["contributions"]["O"])
        main = [e for e in p["events"] if e["in_scope"]]
        low = sorted(main, key=lambda e: (e["rating"], e["name"]))[:3]
        if main:
            paragraphs.append("团队与下限：%d次主赛事冠军、%d次亚军，个人表现调节后的T贡献%.2f分。%d/%d场主赛事R≥1.00；较弱赛事为%s，C贡献%.2f分。" % (p["title_count"], p["runnerup_count"], p["contributions"]["T"], p["consistency"]["positive"], len(main), "、".join("%s %.2f/%d图" % (e["name"], e["rating"], e["maps"]) for e in low), p["contributions"]["C"]))
        else:
            paragraphs.append("团队与下限：当前没有白名单主赛事记录，不能从其他比赛成绩推断主赛事团队贡献或稳定性；先验分项仅供解释，不输出可比较总分。")
        paragraphs.append("样本质量N贡献%.2f分：主赛事%d图、Elite以上%d图、全年Top10对抗%d图。全年R %s/%d图只作背景展示，未另加一份年度Rating分。" % (p["contributions"]["N"], p["counts"]["main_maps"], p["counts"]["elite_maps"], p["counts"]["top10_maps"], fmt(p["annual"]["rating"]), p["annual"]["maps"]))
        comparisons = []
        if p["rank"] is not None:
            index = ranked.index(p)
            if index > 0:
                comparisons.append(compare(p, ranked[index-1], "上一名"))
            if index+1 < len(ranked):
                comparisons.append(compare(p, ranked[index+1], "下一名"))
            paragraphs.extend(x["text"] for x in comparisons)
            r = ranges[p["id"]]
            paragraphs.append("选择结论：基线第%d名，%s。%d种参数情景中的名次为%d–%d；这不是置信区间，不含未来赛果、待公布EVP或缺失关键阶段数据的影响。" % (p["rank"], "入选本次Top20" if p["rank"] <= 20 else "本次未入选Top20，距第20名差%.3f分" % (boundary["score"]-p["score"]), sensitivity["scenario_count"], r["min_rank"], r["max_rank"]))
        else:
            labels = {"main_maps": "主赛事图数", "elite_maps": "Elite以上图数", "top10_maps": "Top10对抗图数"}
            issues = "；".join(next((x.replace(k, v) for k, v in labels.items() if k in x), x) for x in p["issues"])
            paragraphs.append("选择结论：%s。按当前模型的50张主赛事/20张Elite以上/10张Top10自定义门槛，不进入基线名次；%s。这不是HLTV官方落选判断。" % (issues, "保留暂定总分%s供复核" % fmt(p["score"]) if p["score"] is not None else "没有主赛事数据，不输出可比较总分"))
        output.append({"id": p["id"], "name": p["name"], "rank": p["rank"], "score": p["score"],
                       "selected": p["rank"] is not None and p["rank"] <= 20,
                       "eligible": p["eligible"], "paragraphs": paragraphs, "comparisons": comparisons})
    return output


def compare(p, other, relation):
    deltas = {k: p["contributions"][k]-other["contributions"][k] for k in LABELS}
    positive = sorted(((k, v) for k, v in deltas.items() if v > 1e-9), key=lambda x: -x[1])[:2]
    negative = sorted(((k, v) for k, v in deltas.items() if v < -1e-9), key=lambda x: x[1])[:2]
    describe = lambda items: "、".join("%s%+.3f" % (LABELS[k], v) for k, v in items) or "无"
    difference = p["score"]-other["score"]
    text = "与%s%s相比，总分%+.3f；主要优势为%s，主要劣势为%s。以上是同一公式的精确贡献差，并非单一数据的因果解释。" % (relation, other["name"], difference, describe(positive), describe(negative))
    return {"other_id": other["id"], "score_delta": difference, "module_deltas": deltas, "text": text}


def write_evaluation(result, sensitivity, folder):
    people = explain(result, sensitivity)
    dump_json(folder/"evaluation.json", {"metadata": result["metadata"], "players": people})
    intro = "统计采集日期%s；候选池共%d人，已评估%d人，待补统计%d人；%d人达到模型样本门槛。基线遵守固定赛事事实等级及Bounty S1荣誉0.60规则，评分分组以相应config.json为准。样本资格未达者单列，不填虚假名次。这是当前表现排序，不是HLTV官方结论，未模拟剩余赛程。全池关键阶段统计尚缺；荣誉目录已核实%d项赛事。" % (result["metadata"]["snapshot_as_of"], result["metadata"]["candidate_count"], len(people), result["metadata"]["pending_statistics_count"], sum(p["eligible"] for p in people), result["metadata"]["evp_order_events"])
    md = ["# HLTV Top20预测与逐人排名理由", "", intro, "", "| 名次 | 选手 | 分数 | 结论 |", "|---:|---|---:|---|"]
    table, sections = [], []
    for p in people:
        status = "入选Top20" if p["selected"] else "候补" if p["eligible"] else "样本门槛未达"
        md.append("| %s | %s | %s | %s |" % (p["rank"] or "—", p["name"], fmt(p["score"]), status))
        table.append("<tr><td>%s</td><td><a href='#%s'>%s</a></td><td>%s</td><td>%s</td></tr>" % (p["rank"] or "—", html.escape(p["id"]), html.escape(p["name"]), fmt(p["score"]), status))
    for p in people:
        title = "%s · %s · %s分" % (p["rank"] or "未达门槛", p["name"], fmt(p["score"]))
        md += ["", "## "+title, ""]
        for paragraph in p["paragraphs"]:
            md += [paragraph, ""]
        md += ["[逐赛事及奖项来源](report.html#%s)" % p["id"], ""]
        sections.append("<section id='%s' data-name='%s'><h2>%s</h2>%s<p><a href='report.html#%s'>查看全部赛事、荣誉来源与可靠性表</a></p></section>" % (html.escape(p["id"]), html.escape(p["name"].lower()), html.escape(title), "".join("<p>%s</p>" % html.escape(x) for x in p["paragraphs"]), html.escape(p["id"])))
    (folder/"evaluation.md").write_text("\n".join(md), encoding="utf-8")
    content = """<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>HLTV Top20逐人评估</title>
<style>body{font:16px/1.75 system-ui;max-width:1200px;margin:30px auto;padding:20px;background:#09111f;color:#dfe9f5}a{color:#94c9ff}section{background:#142033;border:1px solid #30435d;padding:24px;margin:22px 0;border-radius:12px}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #30435d;text-align:left}input{padding:12px;font:inherit}h2{color:#79e5c4}</style><h1>HLTV Top20预测与逐人排名理由</h1><p>__INTRO__</p><p><a href='report.html'>完整计算明细与来源</a> · <a href='candidates.html'>候选名单</a> · <a href='bounty.html'>Bounty系数对照</a></p><table><tr><th>名次</th><th>选手</th><th>得分</th><th>结论</th></tr>__TABLE__</table><p><input id='search' placeholder='搜索选手的详细理由'></p>__SECTIONS__<script>document.querySelector('#search').addEventListener('input',e=>document.querySelectorAll('[data-name]').forEach(x=>x.hidden=!x.dataset.name.includes(e.target.value.toLowerCase().trim())));</script></html>"""
    for key, value in {"INTRO": html.escape(intro), "TABLE": "".join(table), "SECTIONS": "".join(sections)}.items():
        content = content.replace("__"+key+"__", value)
    (folder/"evaluation.html").write_text(content, encoding="utf-8")
    return people
