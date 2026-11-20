"""Reports and historical checks for the individual-only season forecast."""
import json
from .aggregate import score
from .event_policy import attach_vps,event_policy,apply_stage_context
from .forecast_4_2 import settings,individual_reference,atomic_text
from .pipeline import ROOT,load
from .season import season_inputs,features
from .season_forecast import predict,metrics


def weight_table(policies, pending=None):
    names={"arena":"场馆","studio_audience":"有观众演播厅","studio":"演播厅","lan":"线下，场地细分未核实",
           "online":"线上","unknown":"待核实","absent":"主赛无小组样本"}
    lines=["# 逐站赛事权重","",
           "整站系数用于衡量超过或低于中性水平的表现。基础 MVP 履历分包含档位及赛事折算，选手的最终荣誉积分还取决于个人发挥与争奖差距。阵容列给出与赛前全球前十至少重合三人的队数，以及档案实收的总队数。","","|赛事|档位|实收阵容（前十／总数）|小组样本|淘汰环境|小组／淘汰系数|整站系数|基础 MVP 履历分|",
           "|---|---|---:|---|---|---:|---:|---:|"]
    for event,p in policies.items():
        roster=p["roster"]
        s=p["stage_factors"]
        g=names[p["group"]]+("（另有线上前段）" if p["qualifying"]=="online_outside" else "")
        group_score="—" if p["group"]=="absent" else f"{s['group']:.3f}"
        playoff=names[p["playoff"]]
        if "final" in p:
            playoff+=f"（决赛{names[p['final']]}，{s['final']:.3f}）"
        if "match_venues" in p:
            g+=f"（已核实的场馆场次按 {s['group_arena']:.3f}）"
        if p.get("audience_note"):
            playoff+=f"（[{p['audience_note']}]({p['audience_source']})）"
        lines.append(f"|[{event}]({p['source']})|{p['tier']}|{len(roster['matches'])}／{roster['teams']}|{g}|"
                     f"{playoff}|{group_score}／{s['playoff']:.3f}|{p['event_factor']:.3f}|{p['mvp_base_points']:.2f}|")
    if pending:
        fmt=load("data/reference/event_formats_4_3.json")["2026"][pending]
        lines+=["",f"[{pending}]({fmt['source']}) 已登记。主赛小组按{names[fmt['group']]}、淘汰赛按{names[fmt['playoff']]}处理。赛后导入实战阵容后计算数值。"]
    return "\n".join(lines)+"\n"


def replay():
    from analysis.replay_aggregate_2025 import score_inputs
    _,c,_=settings()
    c.update(load("config/season_4_3.json"))
    weights=[c["weights"][k] for k in c["feature_order"]]
    inputs=season_inputs(2025,detailed_rosters=True)
    base=load("config/model.json")
    c["event_policies"]=event_policy(inputs,2025,c)
    apply_stage_context(inputs,c["event_policies"])
    labels={**load("data/reference/official_top20_2025.json")["ranks"],**load("data/2025/boundary_ranks.json")["ranks"]}
    raw,params,_,_=score_inputs({"target_events":2,"target_maps":24})
    old={p["id"]:p for p in score(raw,individual_reference(params))["players"]}
    records=load("data/reference/official_vps_4_3.json")["2025"]
    from .honor_calibration import calibrate
    calibration=calibrate(inputs,c,base)
    from .core import require
    require(all(c[k]==v for k,v in calibration["weights"].items()),"荣誉校准系数与发布配置不符")
    output={"calibration":calibration}
    for label,cutoff in (("pre_reveal","2025-12-23"),("with_year_end_articles",c["evidence_cutoff_2025"])):
        used=attach_vps(inputs,records,cutoff)
        rows=features(inputs,base,c,2025)
        data={"vp_evidence_cutoff":cutoff,"confirmed_vps":used}
        for name,reference in (("core",{}),("core_plus_H",old)):
            people,_=predict(rows,weights,c,reference,{},alignment=None if reference else (0,0,1),article=False)
            data[name]=metrics([p["id"] for p in people if p["eligible"]],labels)
        output[label]=data
    dest=ROOT/"output/forecast_4_3"
    atomic_text(dest/"replay_2025.json",json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    atomic_text(dest/"events_2025.md",weight_table(c["event_policies"]))
    return output
