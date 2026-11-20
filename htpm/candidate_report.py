"""Candidate coverage and honor-only ledgers, separate from full scoring."""
import html
from .core import fmt


def page(title, intro, headers, rows):
    esc = html.escape
    return "<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+esc(title)+"</title><style>body{font:16px/1.6 system-ui;max-width:1400px;margin:30px auto;padding:20px;background:#09111f;color:#dfe9f5}a{color:#94c9ff}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;border:1px solid #30435d;text-align:left}small{color:#aabbcc}.scroll{overflow:auto}</style><h1>"+esc(title)+"</h1><p>"+esc(intro)+"</p><p><a href='candidates.html'>候选名单</a> · <a href='report.html'>模型评分</a> · <a href='evaluation.html'>逐人理由</a> · <a href='bounty.html'>Bounty对照</a></p><div class='scroll'><table><tr>"+"".join("<th>%s</th>" % esc(h) for h in headers)+"</tr>"+"".join("<tr>"+"".join("<td>%s</td>" % v for v in row)+"</tr>" for row in rows)+"</table></div></html>"


def write_candidates(pool, folder):
    intro = "%d名正式荣誉候选＋%d名观察选手；%d名待补完整统计。组内按荣誉积分排序，仅为评估安排，不是全年排名。待补赛事荣誉：%s。" % (pool["award_candidate_count"], pool["watch_count"], pool["pending_statistics_count"], '、'.join(pool.get('pending_awards',[])) or '无已知待补项')
    headers = ["选手", "评估分组", "MVP/EVP", "荣誉原始分", "A对总分贡献（非总分）", "统计状态", "全部荣誉与来源"]
    md = ["# 2026 Top20候选名单", "", intro, "", pool["policy"], "", "| "+" | ".join(headers)+" |", "|"+"---|"*len(headers)]
    rows = []
    for p in pool["candidates"]:
        honors, links = [], []
        for a in p["awards"]:
            label = "%s · %s · %s%s · %.2f分" % (a["event"], a["tier"], a["type"], "#"+str(a["evp_rank"]) if a.get("evp_rank") else "", a["points"])
            source = a.get("order_evidence") or a["source"]
            honors.append("[%s](%s)" % (label, source))
            links.append("<a href='%s'>%s</a>" % (html.escape(source, quote=True), html.escape(label)))
        values = [p["name"], pool["groups"][p["group"]], "%d / %d" % (p["mvp_count"], p["evp_count"]), fmt(p["award_points"]), fmt(p["A_contribution"]), "已采集 "+str(p["statistics_as_of"]) if p["statistics_status"] == "available" else "待补：不评分"]
        md.append("| "+" | ".join(values+["；".join(honors) or "档案内暂无"])+" |")
        rows.append([html.escape(v) for v in values]+["<br>".join(links) or "档案内暂无"])
    (folder/"candidates.md").write_text("\n".join(md)+"\n", encoding="utf-8")
    (folder/"candidates.html").write_text(page("2026 Top20候选池", intro, headers, rows), encoding="utf-8")


def write_bounty(scenarios, folder):
    lookup = {key: {p["id"]: p for p in rows} for key, rows in scenarios.items()}
    rows = []
    for p in scenarios["0.6"]:
        rows.append([html.escape(p["name"])]+["%s / %s" % (lookup[k][p["id"]]["rank"] or "待核", fmt(lookup[k][p["id"]]["score"])) for k in scenarios])
    (folder/"bounty.html").write_text(page("Bounty S1荣誉系数对照", "相同当前模型，仅改变A/T荣誉系数。表内为当前可排名选手的名次 / 总分；不含后续赛果。", ["选手", "0.40", "0.60基线", "0.80", "1.00"], rows), encoding="utf-8")
