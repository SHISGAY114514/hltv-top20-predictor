"""Offline report for the observed 2026 prediction and its 2025 calibration."""
import html

from .core import fmt

LABELS={"A":"赛事履历","E":"分档表现","O":"强敌对抗","K":"关键赛","P":"赛事高峰","T":"团队深轮次",
        "C":"稳定性","N":"样本覆盖","H":"原模型校正","R":"文章阶段数据校正"}


def neighbor(p,q):
    diffs={k:p["contributions"][k]-q["contributions"][k] for k in LABELS}
    if abs(sum(diffs.values())-(p["score"]-q["score"]))>1e-8:
        raise ValueError("Adjacent score breakdown does not reconcile")
    def terms(positive):
        items=[(k,x) for k,x in diffs.items() if (x>0 if positive else x<0)]
        items.sort(key=lambda item:abs(item[1]),reverse=True)
        return "、".join("%s %+.2f"%(LABELS[k],x) for k,x in items[:2]) or "无"
    return "对第 %d 名 %s，总分 %+.3f。拉开差距的分项有%s，对方追回分数的分项有%s。" % (
        q["rank"],q["name"],p["score"]-q["score"],terms(True),terms(False))


def report(result,folder):
    people=[p for p in result["players"] if p["eligible"]]
    top=people
    cutoff=people[19]
    replay=result["replay"]
    stats=replay["metrics"]
    cv=replay["cross_fitted"]
    pages=[]
    md=[]
    def heading(level,title):
        md.extend(["#"*level+" "+title,""])
        anchor = ' id="rank-%d"'%int(title.split()[0][1:]) if level==3 and title.startswith("#") else ""
        pages.append(f"<h{level}{anchor}>{html.escape(title)}</h{level}>")
    def para(s):
        md.extend([s,""])
        pages.append("<p>"+html.escape(s)+"</p>")
    def table(labels,rows):
        md.extend(["| "+" | ".join(labels)+" |","|"+"|".join("---" for _ in labels)+"|"])
        pages.append("<table><thead><tr>"+"".join("<th>"+html.escape(t)+"</th>" for t in labels)+"</tr></thead><tbody>")
        for row in rows:
            row=list(map(str,row))
            md.append("| "+" | ".join(row)+" |")
            cells=[html.escape(s) for s in row]
            if labels[:2]==["名次","选手"]:
                cells[1]='<a href="#rank-%d">%s</a>'%(int(row[0]),cells[1])
            pages.append("<tr>"+"".join("<td>"+s+"</td>" for s in cells)+"</tr>")
        pages.append("</tbody></table>")
        md.append("")
    heading(1,"2026 HLTV 年度选手预测全榜")
    para(result["version"]+" · 模型更新于 "+result["release_date"]+" · 依据 2025 评选 · 已赛数据截至 "+result["cutoff"])
    para("本次录得 %d 名选手的逐图表现，%d 名获奖或达到观察门槛。前 20 名为当前预测入榜者，21–30 名为追赶者。基线只使用已发生的比赛，下一届 Major 的条件结果单列。"%(
         len(result["players"]),len(people)))
    para("各名次均有下方的逐人说明，包含五档赛事的小组赛、淘汰赛、决赛实测覆盖和高峰来源。")
    table(["名次","选手","得分","3.5 名次","结构情景范围","距第 20 名"],[
        (p["rank"],p["name"],"%.3f"%p["score"],p["legacy_rank"] or "未排",
         "%d–%d"%tuple(p["range"]),"%+.3f"%(p["score"]-cutoff["score"])) for p in top])
    heading(2,"2025 年能验证到哪一步")
    para("2025 和 2026 分别核实了 %d、%d 场完整系列赛战报。每份战报的十人名册与十组击杀、死亡数均已和本机记分板吻合。下表给出 2026 年的分档覆盖，单位为选手×地图；同一张图可以有十名选手。" % tuple(result["rating_coverage"][y]["verified_series"] for y in ("2025","2026")))
    table(["赛事档次","整站实测覆盖","小组实测覆盖","淘汰赛实测覆盖"],[
        (tier,*("%d/%d"%(s[k]["rating_maps"],s[k]["maps"]) for k in ("all","group","playoff")))
        for tier,s in result["rating_coverage"]["2026"]["tiers"].items()])
    current_events=result["rating_coverage"]["2026"]["events"]
    for tier in ("Major","Super-elite","Elite"):
        para(tier+" 赛事及已核实的系列赛战报场数："+"、".join(
            "%s（%d 场）"%(name,e["verified_series"]) for name,e in current_events.items() if e["tier"]==tier)+"。")
    para("历史候选池共 %d 人。在六组核心权重、三种阶段份额及三种无奖赛事履历比例中选择组合。选中 %s，分档与阶段交叉表现占关键赛模块的 %.1f%%，无奖赛事履历采用封顶后净值的 %.0f%%。"%(
        replay["eligible"],result["profile"],100*replay["tier_stage_share_of_K"],100*replay["event_credit_share"]))
    table(["2025 检查","Top 20 命中","Top 10 命中","官方前 20 平均名次误差","前 30 成对顺序正确"],
          [(n,s["top20_hits"],s["top10_hits"],"%.2f"%s["mae_top20"],"%d/435"%s["ordered_pairs_top30"])
           for n,s in [("仅赛事履历（同分按 ID）",replay["awards_only"]),("仅分档表现",replay["event_performance_only"]),
                       ("均衡权重",replay["balanced"]),("选定权重·同年拟合",stats),("按选手五折交叉预测",cv)]])
    table(["固定权重，移除一项", "Top 20 命中", "前 20 平均名次误差", "前 30 成对顺序正确"],
          [(label, s["top20_hits"], "%.2f"%s["mae_top20"], "%d/435"%s["ordered_pairs_top30"])
           for key,label in [("flat_first_evp","第一 EVP 接近度"),("flat_within_tier","同档参赛强度"),
                             ("no_arena_residual","场馆差异"),("without_K","整个关键赛模块"),
                             ("without_tier_stage","分档与阶段的交叉评分"),("without_series_rating","战报 Rating 的替换份额"),
                             ("without_peak_proximity","高峰分中的 MVP 距离"),("original_tier_shares","改回原 4.1 五档份额"),
                             ("without_high_peak","高档最佳站份额"),("without_event_credit","无奖赛事履历项")]
           for s in [replay["ablations"][key]]])
    para("选定权重的漏选为 %s，错选为 %s。五折按选手留出，重新选择核心权重、阶段份额和无奖赛事履历比例，所有比赛来自同一年。2026 另有原始整站 Rating、3.5 汇总、社区阶段值及香港与雷电杯的分量调整。两年的战报覆盖也有差别，上表只衡量 2025 可重建的核心。"%(
        "、".join(stats["missed"]) or "无","、".join(stats["false_positives"]) or "无"))
    audit=replay["boxscore_audit"]
    para("独立检查逐图表现指数的尺度：在 2025 官方个人年表中匹配 %d 条选手赛事记录，用它们拟合指数与整站 Rating 之间的线性关系。随后对 2026 年 %d 条有官方 Rating 的选手赛事记录检查，平均绝对偏差 %.3f Rating；其中图数也相同的 %d 条偏差 %.3f。该线性关系只做审计。"%(
        audit["event_cells_2025"],audit["event_cells_2026"],audit["mae_rating_2026"],audit["same_count_cells"],audit["same_count_mae"]))
    table(["2025 选手","实际","共用模型","偏差"],[(pid,v["actual"],v["predicted"],"%+d"%(v["predicted"]-v["actual"]))
            for pid,v in sorted(replay["players"].items(),key=lambda pair:pair[1]["actual"])])
    heading(2,"逐人入榜及相邻名次理由")
    para("¹ 整站 Rating 摘要取 3.5 同档整站 Rating 的模型加权汇总。² 每格依次为融合指数／已核实 Rating 均值（实测覆盖图数／已收录图数）。官方系列赛 Rating 按系列赛图数加权；若本站收录图数与个人整站统计吻合，整站栏优先采用该选手整站 Rating。只有这些地图全部属于某个阶段时，该阶段栏才可采用整站 Rating。混合阶段不倒推小组或淘汰赛 Rating。决赛包含于淘汰赛，排位赛另列。破折号表示该值未取得。")
    para("下文的逐图指数由击杀、死亡、ADR、KAST 计算，50 是参考水平，单位为本模型指数。Rating 字样均指来源列出的 Rating 3.0。来源之间的地图范围不同；阶段分组彼此重叠。相邻比较为总分贡献差，正号一律表示本行选手领先。")
    for i,p in enumerate(top):
        heading(3,"#%d  %s · %.3f 分"%(p["rank"],p["name"],p["score"]))
        d=p["details"]
        awards=sorted(p["awards"],key=lambda a:-a["points"])
        para("正式奖项累计 %.2f 履历分，无奖赛事的净修正为 %+.2f，合计 %.2f（下限为零）。"%
             (sum(a["points"] for a in awards),p["event_credit"],p["resume_points"]))
        for a in awards:
            if a["dominance_points"]>0:
                para("%s 的 MVP 在本站合格选手中拉开数据差距，获得 %.2f 履历分的领先幅度奖励，已计入正式奖项累计。"%(a["event"],a["dominance_points"]))
            elif a["position"] and a["position"]>1 and a["proximity_points"]>0:
                para("%s 的第 %d 顺位 EVP 获得官方争奖认可，接近度奖励为 %.2f 履历分。"%(a["event"],a["position"],a["proximity_points"]))
        event_peaks=sorted(p["events"],key=lambda e:-e["peak"])[:3]
        peaks=[e for e in p["events"] if e["peak_class"]!="普通站次"]
        para("达标高峰共 %d 站，其中 Major、超级精英或精英赛事 %d 站。以下列出个人得分最高的三站及判定。" % (
            len(peaks),sum(e["tier"] in ("Major","Super-elite","Elite") for e in peaks)))
        award_text="、".join(a["event"]+" "+(a["kind"] if not a["position"] else "EVP #"+str(a["position"])) for a in awards[:3])
        para("已核实 %d MVP、%d EVP。%s个人高峰分排在前列的站次为%s。共 %d/%d 站的表现指数达到 50。"%(
            sum(a["kind"]=="MVP" for a in awards),sum(a["kind"]=="EVP" for a in awards),
            "分值最高的荣誉包括 "+award_text+"。" if awards else "",
            "、".join("%s（%s，%d 图，整站 Rating %s，%s，高峰分 %.1f，赛事倍率 %.2f，同站 MVP %s，%s，MVP 指数减本人 %s）"%(
                e["event"],e["tier"],e["maps"],fmt(e["event_rating"]),e["peak_class"],e["peak"],e["peak_multiplier"],e["mvp"],e["proximity_basis"],fmt(e["mvp_gap"])) for e in event_peaks),
            p["good_events"],len(p["events"])))
        for e in event_peaks:
            if e["proximity_basis"].startswith("官方评语"):
                label="HLTV 对 "+e["event"]+" 的颁奖说明"
                md.extend(["["+label+"]("+e["source"]+")",""])
                pages.append('<p><a href="%s">%s</a></p>'%(html.escape(e["source"],quote=True),html.escape(label)))
        for a in [x for x in awards if x["position"]==1]:
            gap = a["mvp_index_gap"]
            context = a["first_evp_context"]
            basis = context["note"] if context else "按整站、胜图和淘汰赛的指数差及双方图数保守估算。"
            para("第一 EVP。%s 的 MVP 相对 %s 的表现指数差为 %s。%s 本站计入荣誉累计的接近度奖励为 %.2f 奖项分。"%(
                a["event"],p["name"],"%+.1f"%gap if gap is not None else "未观测",basis,a["proximity_points"]))
            if context and not any(e["event"]==a["event"] for e in event_peaks):
                md.extend(["[HLTV 本站颁奖评语](%s)"%a["source"],""])
                pages.append('<p><a href="%s">HLTV 本站颁奖评语</a></p>'%html.escape(a["source"],quote=True))
        keys=[("主赛事","main"),("Elite 及以上","elite"),("对赛前 VRS Top 10","top10"),("淘汰赛","playoff"),
              ("Elite 及以上淘汰赛","elite_playoff"),("淘汰赛对 Top 10","pressure_top10"),("场馆","arena"),("演播厅","studio"),("决赛","final")]
        para("比赛证据（图数／指数）。"+"，".join("%s %d／%s"%(name,d[k]["maps"],fmt(d[k]["index"])) for name,k in keys)+"。")
        if p.get("hltv_top5"):
            o=p["hltv_top5"]
            para("HLTV 全年累计对 Top 5 为 %s Rating／%d 图。"%(fmt(o["raw_rating"]),o["maps"]))
        if p["published"]:
            r=p["published"]
            para("完美世界社区表的独立口径（Rating／图）。"+"，".join("%s %s／%d"%(name,fmt(r[k][1]),r[k][0])
                for name,k in [("超级精英赛事","super"),("精英赛事","elite"),("大型淘汰赛","playoff"),("精英淘汰赛","elite_playoff"),("场馆","arena"),("决赛","final")])+"。")
        def cell(data):
            return "%s／%s（%d/%d 图）"%(fmt(data["index"]),fmt(data["observed_rating"]),data["rating_maps"],data["maps"])
        table(["本机赛事档次","整站 Rating 摘要¹","整站²","小组赛²","淘汰赛²","其中决赛²","排位赛²"],
              [(tier,fmt(p.get("hltv_tiers",{}).get(tier,{}).get("rating")),
                *(cell(s[k]) for k in ("all","group","playoff","final","placement"))) for tier,s in p["tier_stages"].items()])
        para("为什么在这里。"+" ".join(neighbor(p,people[j]) for j in (i-1,i+1) if 0<=j<len(people)))
        if p["rank"]>=16:
            para("入榜线。相对第 20 名 %s 的分差为 %+.3f，%d 个已赛结构情景中排第 %d–%d。此处范围不含未来比赛。"%(
                cutoff["name"],p["score"]-cutoff["score"],len(result["scenarios"]),*p["range"]))
    heading(2,"已观察但样本未达门槛的选手")
    para("以下选手均未获正式荣誉，参赛站数或地图数也未达门槛。当前规则为有正式奖项，或至少两站且累计 20 图。观察分用于追踪，正式名次留空。")
    table(["选手","观察分","已收录赛事","主赛事图数","未达条件"],[
        (p["name"],"%.3f"%p["score"],len(p["events"]),p["details"]["main"]["maps"],
         "、".join(reason for condition,reason in ((len(p["events"])<2,"少于两站"),
                         (p["details"]["main"]["maps"]<20,"少于 20 图")) if condition))
        for p in result["players"] if not p["eligible"]])
    heading(2,"如果最后一届 Major 改变格局")
    para("每个情景把一届已赛比赛的整套参赛阵容、地图、对手、轮次和奖项复制为一届额外 Major，所有出场选手同时更新。仅将赛事档次改为 Major，保留模板赛制、场馆和当时的对手强度。外部 Rating 校正冻结在快照值。情景展示翻盘路径，不给出发生概率。")
    base_ids=[p["id"] for p in top[:20]]
    for event,ids in result["major_scenarios"].items():
        inside=ids[:20]
        para("%s 模板。前三为 %s；进入前 20 的有 %s，移出前 20 的有 %s。"%(
            event,"、".join(inside[:3]),"、".join(x for x in inside if x not in base_ids) or "无",
            "、".join(x for x in base_ids if x not in inside) or "无"))
    heading(2,"证据与复算")
    for label,url in [("HLTV 2025 评选标准与结果","https://www.hltv.org/news/43492/top-20-players-of-2025-final-list"),
                      ("2025 年第 21–30 名","https://www.dust2.in/news/69500/hltv-top-20-players-of-2025-21-to-30-revealed"),
                      ("跨年逐图原始数据","https://www.kaggle.com/datasets/ektarr/counter-strike-pro-matches"),
                      ("Valve 月度全球排名","https://github.com/ValveSoftware/counter-strike_regional_standings"),
                      ("香港决赛补录","https://www.hltv.org/matches/2400208/spirit-vs-furia-blast-rivals-2026-season-2"),
                      ("MartisLaw 文章与分组原表","https://news.wmpvp.com/community-pcDetail.html?id=392821231"),
                      ("评分口径与验证限制","../../docs/MODEL_4_1_1.md"),("完整分项和情景名次","scores.json"),
                      ("逐系列赛 Rating 与 HLTV 原文链接","../../data/2026/series_ratings.json")]:
        md.append("- [%s](%s)"%(label,url))
        pages.append('<p><a href="%s">%s</a></p>'%(html.escape(url,quote=True),html.escape(label)))
    (folder/"ranking.md").write_text("\n".join(md)+"\n",encoding="utf8")
    style="body{max-width:1000px;margin:3rem auto;padding:0 1rem;font:16px/1.65 system-ui;color:#18212d}h2{margin-top:3rem;border-bottom:2px solid #187469}h3{margin-top:2rem;color:#075f59}table{border-collapse:collapse}td,th{padding:.35rem .75rem;border-bottom:1px solid #ccd6db;text-align:left}thead{background:#e7f2ef}a{color:#075f59}"
    (folder/"ranking.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>HTPM 4.1.1 · 全榜</title><style>'+style+'</style><main>'+"\n".join(pages)+'</main></html>',encoding="utf8")
