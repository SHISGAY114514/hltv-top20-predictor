"""Standalone, offline report, with complete factual ledgers and model calculations."""
import html
from pathlib import Path
from .core import dump_json, fmt

LABELS = {"A": "个人荣誉", "E": "分级赛事表现", "O": "强队对抗", "T": "团队成绩贡献", "C": "跨赛事稳定性", "N": "样本质量"}



def write_reports(result, sensitivity, config, destination):
    folder = Path(destination); folder.mkdir(parents=True, exist_ok=True)
    dump_json(folder / "scores.json", result)
    dump_json(folder / "sensitivity.json", sensitivity)
    dump_json(folder / "config.json", config)
    ranges = {p["id"]: p for p in sensitivity["players"]}
    esc = html.escape
    notice = "表现快照采集于%s；顺位目录截至%s，共核实%d项赛事。赛事事实等级遵守用户固定规则。Bounty S1个人与团队荣誉系数0.60，Rating与样本不打折。尚缺全池关键赛统计，未模拟未来比赛。分数与参数均非HLTV官方公式。" % (result["metadata"]["snapshot_as_of"], result["metadata"]["evp_order_verified_on"], result["metadata"]["evp_order_events"])
    if config.get("model_basis_year") == 2024:
        notice += "本页为2024依据版迁移到2026，Major与Super-elite仅在评分层合并；不是2024历史回测。"
    coverage = "%d名候选及观察选手；%d名已采集；%d名待补完整统计。" % (result["metadata"]["candidate_count"], len(result["players"]), result["metadata"]["pending_statistics_count"])
    ranking_label = result["ranking_label"]
    notice = coverage + notice
    formula = "S = 30%A + 27%E + 23%O + 5%T + 5%C + 10%N"
    md = ["# 2026 HLTV Top20模型评分 · " + config["version"], "", notice, "", formula,
          "", "完整候选名单见candidates.html；逐人排名理由见evaluation.html。Rating 3.0；对手分组为累计Top N。",
          "", "## " + ranking_label, "", "| 名次 | 选手 | 得分 | 年度R | Top5 R/图 | Top10 R/图 | MVP/EVP | 主赛事冠/亚 | 参数名次范围 |",
          "|---:|---|---:|---:|---|---|---|---|---|"]
    bodyrows, cards = [], []
    for p in result["players"]:
        s = ranges[p["id"]]
        span = "%s–%s" % (s["min_rank"], s["max_rank"]) if s["min_rank"] else "—"
        rank = p["rank"] or "待核"
        mvp = sum(a["type"] == "MVP" for a in p["awards"])
        evp = sum(a["type"] == "EVP" for a in p["awards"])
        opponent = lambda k: "%s / %s" % (fmt(p["opponents"][k]["raw_rating"]), p["opponents"][k]["maps"])
        values = [rank, p["name"], fmt(p["score"]), fmt(p["annual"]["rating"]), opponent("5"), opponent("10"),
                  "%d / %d" % (mvp, evp), "%d / %d" % (p["title_count"], p["runnerup_count"]), span]
        md.append("| " + " | ".join(map(str, values)) + " |")
        cells = "".join("<td>%s</td>" % ("<a href='#%s'>%s</a>" % (esc(p["id"]), esc(p["name"])) if i == 1 else esc(str(v))) for i, v in enumerate(values))
        bodyrows.append("<tr data-name='%s'%s>%s</tr>" % (esc(p["name"].lower()), " class='top'" if p["rank"] and p["rank"] <= 20 else "", cells))
    md += ["", "[逐人排名理由](evaluation.html) · [完整候选名单](candidates.html) · [Bounty系数对照](bounty.html) · [完整参数](config.json) · [模型公式](../../docs/MODEL_AGGREGATE.md)", "",
           "参数范围来自%d种确定性扰动，不是置信区间；不包含未来赛事、缺失EVP或关键赛造成的变动。" % sensitivity["scenario_count"],
           "", "## 模型与数据边界", ""] + ["- " + x for x in result["metadata"]["limitations"]]
    md += ["", "## 逐人分解与全部参赛事项", ""]
    for p in result["players"]:
        rank = p["rank"] or "待核"
        note = "已核实%d项MVP、%d项EVP；荣誉原始积分%.2f，贡献总分%.2f；分层赛事表现贡献%.2f，强队对抗贡献%.2f。请结合各层实际图数与可靠性评估，名次由完整精度总分计算。" % (sum(a["type"] == "MVP" for a in p["awards"]), sum(a["type"] == "EVP" for a in p["awards"]), p["award_points"], p["contributions"]["A"], p["contributions"]["E"], p["contributions"]["O"])
        md += ["### %s · %s · %s分" % (rank, p["name"], fmt(p["score"])), "", note, "",
               "样本：主赛事%d图；Elite+ %d图；全年Top10对抗%d图。%s" %
               (p["counts"]["main_maps"], p["counts"]["elite_maps"], p["counts"]["top10_maps"], "；".join(p["issues"])), "",
               "| 模块 | 分项/100 | 总分贡献 |", "|---|---:|---:|"]
        modules = []
        for k in config["weights"]:
            md.append("| %s | %.2f | %.2f |" % (LABELS[k], p["modules"][k], p["contributions"][k]))
            modules.append("<div><small>%s</small><b>%.2f</b><progress max='100' value='%.4f'></progress><small>贡献 %.2f 分</small></div>" % (LABELS[k], p["modules"][k], p["modules"][k], p["contributions"][k]))
        md += ["", "| 对手范围 | Rating 3.0 | 图数 | 收缩后Rating | 可靠性 | 总分名义/有效权重 |", "|---|---:|---:|---:|---:|---:|"]
        opprows = []
        for k, o in p["opponents"].items():
            values = ["Top "+k, fmt(o["raw_rating"]), o["maps"], "%.3f" % o["adjusted"], "%.1f%%" % (100*o["shrinkage_weight"]), "%.2f%% / %.2f%%" % (100*o["nominal_weight"], 100*o["effective_weight"])]
            md.append("| " + " | ".join(map(str, values)) + " |")
            opprows.append("<tr>"+"".join("<td>%s</td>" % esc(str(v)) for v in values)+"</tr>")
        tierrows = []
        tierheads = ["档次", "图数/赛事数", "封顶图/有效赛事", "原始/收缩R", "可靠性", "总分名义/有效权重", "覆盖率"]
        md += ["", "| " + " | ".join(tierheads) + " |", "|---|---:|---:|---:|---:|---:|---:|"]
        for tier, t in p["event_rating"].get("tier_samples", {}).items():
            values = [tier, "%d / %d" % (t["maps"], t["events"]), "%d / %.2f" % (t["capped_maps"], t["effective_events"]), "%s / %.3f" % (fmt(t["raw_rating"]), t["adjusted"]), "%.1f%%" % (100*t["shrinkage_weight"]), "%.2f%% / %.2f%%" % (100*t["nominal_weight"], 100*t["effective_weight"]), "%.1f%%" % (100*t["coverage"])]
            md.append("| " + " | ".join(map(str, values)) + " |")
            tierrows.append("<tr>"+"".join("<td>%s</td>" % esc(str(v)) for v in values)+"</tr>")
        tierhtml = "<h3>各评分档次独立验证</h3><div class='scroll'><table><tr>"+"".join("<th>%s</th>" % h for h in tierheads)+"</tr>"+"".join(tierrows)+"</table></div>"
        quality = p["sample_quality"]
        sample_text = "样本质量 %.1f/100（绝对覆盖 %.1f，赛程难度 %.1f）；有效赛事数 %.2f。E的观测数据有效权重 %.2f%%（名义27%%），O有效权重 %.2f%%（名义23%%）；其余权重回到先验，不转给其他模块。" % (p["modules"]["N"], 100*quality["volume"], 100*quality["difficulty"], p["event_rating"]["effective_events"], 100*p["effective_data_weights"]["E"], 100*p["effective_data_weights"]["O"])
        md += ["", sample_text, "", "年度统计与累计对手分组：[HLTV筛选统计](%s)。" % p["source"], "",
               "累计Top组互相嵌套，不将图数相加；分层有效赛事数是各层之和，不代表独立样本总数。缺失层保留先验，不向其他层转移权重。", "",
               "| 个人奖项赛事 | 等级 | 奖项 | 档次分×顺位系数×荣誉系数 | 计入分 |", "|---|---|---|---|---:|"]
        awardlines = []
        for a in p["awards"]:
            award_label = a["type"] + ("#"+str(a["evp_rank"]) if a.get("evp_rank") else "")
            award_source = a.get("order_evidence", a["source"])
            calculation = "%.2f × %.2f × %.2f" % (a["base_points"], a["rank_factor"], a["honor_factor"])
            md.append("| %s | %s | [%s](%s) | %s | %.2f |" % (a["event"], a["tier"], award_label, award_source, calculation, a["points"]))
            awardlines.append("<li>%s · %s · <a href='%s'>%s</a> · %s = %.2f分</li>" % (esc(a["event"]), esc(a["tier"]), esc(award_source), award_label, calculation, a["points"]))
        md += ["", "全部参赛记录：[HLTV年度赛事页](%s)。仅白名单主赛事进入E/T/C/N；其余赛事保留用于核对年度地图数。" % p["event_source"], "",
               "| 赛事 | 队伍 | 名次 | 图数 | Rating | 模型档次 | 团队原始分 |", "|---|---|---|---:|---:|---|---:|"]
        team = {t["event"]: t for t in p["team_ledger"]}
        erows = []
        for e in p["events"]:
            tp = team.get(e["name"], {}).get("points", 0)
            t = team.get(e["name"], {})
            values = [e["name"], e["team"], e["placement"], e["maps"], fmt(e["rating"]), e["tier"] or "不计分", "%.3f × %.2f = %.3f" % (t.get("base_points", 0), t.get("honor_factor", 1), tp)]
            md.append("| " + " | ".join(map(str, values)) + " |")
            erows.append("<tr%s>%s</tr>" % (" class='excluded'" if not e["in_scope"] else "", "".join("<td>%s</td>" % esc(str(v)) for v in values)))
        cards.append("<section id='%s' data-name='%s'><h2><span>#%s</span> %s <em>%s</em></h2><p>%s</p><p class='muted'>主赛事 %d 图 · Elite+ %d 图 · %s</p><div class='modules'>%s</div><details><summary>强队对抗、奖项及全部赛事</summary><p><a href='%s'>年度统计来源</a> · <a href='%s'>逐赛事来源</a></p><table><thead><tr><th>对手</th><th>Rating</th><th>图数</th><th>收缩Rating</th></tr></thead><tbody>%s</tbody></table><ul>%s</ul><div class='scroll'><table><thead><tr><th>赛事</th><th>队伍</th><th>名次</th><th>图数</th><th>Rating</th><th>档次</th><th>团队原始分</th></tr></thead><tbody>%s</tbody></table></div></details></section>" %
                     (esc(p["id"]), esc(p["name"].lower()), rank, esc(p["name"]), fmt(p["score"]), esc(note), p["counts"]["main_maps"], p["counts"]["elite_maps"], esc(("；".join(p["issues"]) or "暂定数据") + "。" + sample_text), "".join(modules), esc(p["source"]), esc(p["event_source"]), "".join(opprows), "".join(awardlines) or "<li>档案内暂无已核实奖项；不代表后续不会新增。</li>", "".join(erows)))
        cards[-1] = cards[-1].replace("<ul>", tierhtml+"<ul>", 1).replace("<th>收缩Rating</th>", "<th>收缩Rating</th><th>可靠性</th><th>名义/有效权重</th>")
    md += ["", "## 复算", "", "数据 SHA256：" + result["data_sha256"], "", "配置 SHA256：" + result["config_sha256"], ""]
    (folder / "report.md").write_text("\n".join(md), encoding="utf-8")
    template = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>2026 HLTV Top20 预测 · __VERSION__</title><style>
:root{font:16px/1.65 system-ui,'Microsoft YaHei',sans-serif;color:#dfe9f5;background:#09111f}body{max-width:1240px;margin:auto;padding:32px 22px}h1{font-size:clamp(26px,4vw,46px);line-height:1.2}h2{font-size:23px}h2 span,.eyebrow{color:#79e5c4}em{float:right;font-style:normal;color:#79e5c4}a{color:#94c9ff}section,.panel{background:#142033;border:1px solid #30435d;border-radius:12px;padding:22px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:10px 12px;border-bottom:1px solid #2d3f55;white-space:nowrap}th{color:#acbed4;background:#17283e}.top td:first-child{color:#79e5c4;font-weight:bold}.scroll{overflow-x:auto}.modules{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}.modules div{background:#0b1729;padding:12px;border-radius:8px;display:grid;gap:5px}.modules b{font-size:23px}progress{width:100%;height:6px;accent-color:#79e5c4}.muted,small,.excluded{color:#95a8c1}summary{cursor:pointer;color:#94c9ff;margin-top:20px}.notice{border-left:4px solid #f6c674;padding-left:18px;color:#e8d9b4}input{padding:12px;background:#09111f;border:1px solid #506782;border-radius:8px;color:white;width:min(350px,90%)}footer{word-break:break-all;font-size:12px;color:#8094ae}.formula{font-family:monospace;font-size:19px}details table{margin:16px 0}@media(max-width:850px){.modules{grid-template-columns:repeat(3,1fr)}}@media print{body{background:white;color:black}section,.panel{break-inside:avoid;background:white}details{display:block}input{display:none}}
</style></head><body><div class="eyebrow">HTPM / 2026 / RESEARCH SNAPSHOT</div><h1>HLTV Top 20<br>__RANKING__</h1><p>__COVERAGE__</p><p class="notice">__NOTICE__</p><div class="panel"><p class="formula">__FORMULA__</p><p>30%个人荣誉 + 27%赛事表现 + 23%强队对抗 + 5%团队贡献 + 5%跨赛事稳定性 + 10%样本质量。</p><p>参数名次范围来自__SCENARIOS__种扰动，不能理解为年终置信区间。名次即便范围很窄，也可能因后续比赛、EVP顺位或关键赛补录而变化。</p><details><summary>查看重要数据边界</summary><ul>__LIMITS__</ul></details></div><label for="search">查找选手</label><p><input id="search" placeholder="输入选手名，例如 NiKo" autocomplete="off"></p><div class="panel scroll"><table><thead><tr><th>名次</th><th>选手</th><th>得分</th><th>全年R</th><th>Top5 R/图</th><th>Top10 R/图</th><th>MVP/EVP</th><th>主赛事冠/亚</th><th>参数名次范围</th></tr></thead><tbody>__ROWS__</tbody></table></div>__CARDS__<footer>数据SHA256 __DATAHASH__<br>配置SHA256 __CONFIGHASH__<br>同目录scores.json为完整精度；sensitivity.json为参数分析；report.md为全部文字与表格。</footer><script>document.querySelector('#search').addEventListener('input',event=>{const q=event.target.value.toLowerCase().trim();document.querySelectorAll('[data-name]').forEach(el=>el.hidden=!el.dataset.name.includes(q));});</script></body></html>"""
    replacements = {"RANKING": esc(ranking_label), "COVERAGE": esc(coverage), "VERSION": config["version"], "NOTICE": esc(notice), "FORMULA": formula, "SCENARIOS": str(sensitivity["scenario_count"]),
                    "LIMITS": "".join("<li>%s</li>" % esc(x) for x in result["metadata"]["limitations"]),
                    "ROWS": "".join(bodyrows), "CARDS": "".join(cards), "DATAHASH": result["data_sha256"], "CONFIGHASH": result["config_sha256"]}
    for k, v in replacements.items():
        template = template.replace("__"+k+"__", v)
    template = template.replace("<label for=\"search\">", "<p><a href='evaluation.html'>逐人排名理由</a> · <a href='candidates.html'>完整候选名单</a> · <a href='bounty.html'>Bounty系数对照</a> · <a href='config.json'>完整参数</a></p><label for=\"search\">")
    (folder / "report.html").write_text(template, encoding="utf-8")
    if config.get("model_basis_year") == 2024:
        path=folder/'report.md'
        path.write_text(path.read_text(encoding='utf-8').replace('MODEL_AGGREGATE.md','MODEL_2024.md'),encoding='utf-8')
