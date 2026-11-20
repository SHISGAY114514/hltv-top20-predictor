"""Auditable event-specific policies and dated, explicitly named HLTV VP evidence."""
from collections import defaultdict
from urllib.parse import urlsplit

from .core import iso, require
from .pipeline import load


def roster_evidence(rows, snapshot, day, aliases=None, supplements=()):
    """Match one real opening five per team, without pooling substitute lineups."""
    aliases = aliases or {}
    teams = defaultdict(lambda: defaultdict(set))
    for r in rows:
        pid = r["player"].strip().casefold()
        teams[r["team"]][r["date"],r["match"],r["map"]].add(aliases.get(pid,pid))
    opening = {team:maps[min(maps)] for team,maps in teams.items()}
    for record in supplements:
        team=record["team"]
        require(urlsplit(record["source"]).hostname=="www.hltv.org", "补充阵容缺少 HLTV 比赛来源")
        players={p.casefold() for p in record["players"]}
        if team in opening:
            require(opening[team]==players, "补充首阵与地图不一致")
        else:
            require(all(len(players & observed)<3 for observed in opening.values()), "补充阵容与实收队重复")
            opening[team]=players
    require(all(len(s)==5 for s in opening.values()), "赛事阵容档案缺少首张实收地图的五人")
    matches = []
    for rank,name,ids in snapshot["teams"]:
        expected = set(p.casefold() for p in ids)
        count,team = max((len(expected & roster),t) for t,roster in opening.items())
        if count>=3:
            matches.append(dict(rank=rank, vrs_team=name, team=team, returning=count))
    require(len({m["team"] for m in matches})==len(matches),"同一参赛阵容匹配多个 VRS 核心")
    return dict(date=day,source=snapshot["source"],teams=len(opening),matches=matches)


def event_policy(inputs, year, config, constrain_history=True):
    catalog=inputs[0]
    special_counts=defaultdict(lambda:defaultdict(int))
    formats=load("data/reference/event_formats_4_3.json")[str(year)]
    for events in inputs[2].values():
        for event,rows in events.items():
            if "final" in formats[event] or "match_venues" in formats[event]:
                for _,phase,venue,*_ in rows:
                    special_counts[event][phase]+=1
                    if phase=="group" and venue=="arena":
                        special_counts[event]["group_arena"]+=1
    require(set(catalog) <= set(formats), "缺少逐站赛制")
    scales=config["environment"]
    base=load("config/model.json")
    result={}
    for event,info in catalog.items():
        fmt=formats[event]
        roster=info["roster_evidence"]
        strength=sum((1 if m["rank"]<=5 else .5)*m["returning"]/5 for m in roster["matches"])/7.5
        field=1+config["roster_span"]*(strength-.5)
        size=1+config["field_size_span"]*(min(32,roster["teams"])-16)/16
        g,p=fmt["group"],fmt["playoff"]
        require(g in scales and p in scales and p!="absent" and fmt["source"],"无效赛事环境")
        format_factor=config["online_preliminary_factor"] if fmt["qualifying"]=="online_outside" else 1.
        stage={k:field*size*format_factor*(1+config["venue_span"]*(scales[tag]-1))
               for k,tag in (("group",g),("playoff",p))}
        local=dict(stage)
        counts=special_counts[event]
        if "final" in fmt:
            stage["final"]=field*size*format_factor*(1+config["venue_span"]*(scales[fmt["final"]]-1))
            frac=counts["final"]/max(1,counts["playoff"]+counts["final"])
            local["playoff"]+=frac*(stage["final"]-stage["playoff"])
        if "match_venues" in fmt:
            stage["group_lan"]=stage["group"]
            stage["group_arena"]=field*size*format_factor*(1+config["venue_span"]*(scales["arena"]-1))
            frac=counts["group_arena"]/max(1,counts["group"])
            local["group"]+=frac*(stage["group_arena"]-stage["group_lan"])
        # Out-of-scope online stages affect format breadth, never the LAN map sample.
        factor=(local["playoff"] if g=="absent" else
                sum(config["stage_mix"][k]*v for k,v in local.items()))
        tier=info["tier"]
        resume=config["tier_resume_factors"][tier]*config["big_event_resume_adjustments"].get(event,1.)
        honor=factor*resume*base["honor_factors"].get(event,1.)
        result[event]=dict(tier=tier,**fmt,roster=roster,roster_factor=field,field_size_factor=size,
                           stage_factors=stage,event_factor=factor,honor_multiplier=honor,
                           mvp_base_points=base["tiers"][tier]["MVP"]*honor)
    if year==2025 and constrain_history:
        orders=load("data/reference/award_order_2025.json")["within_tier"]
        require({n for names in orders.values() for n in names}==set(result),"2025 官方档内清单不完整")
        for tier,names in orders.items():
            # Least-squares monotone projection of the format/lineup estimates.
            blocks=[]
            for name in names:
                require(result[name]["tier"]==tier,"官方分档与赛事目录不符")
                blocks.append(([name],result[name]["event_factor"]))
                while len(blocks)>1 and blocks[-2][1]<blocks[-1][1]:
                    b,y=blocks.pop()
                    a,x=blocks.pop()
                    blocks.append((a+b,(len(a)*x+len(b)*y)/(len(a)+len(b))))
            for block,value in blocks:
                for name in block:
                    p=result[name]
                    adjustment=value/p["event_factor"]
                    p.update(official_tier_order=names.index(name)+1,unconstrained_factor=p["event_factor"],
                             event_factor=value,honor_multiplier=p["honor_multiplier"]*adjustment,
                             mvp_base_points=p["mvp_base_points"]*adjustment)
                    p["stage_factors"]={k:v*adjustment for k,v in p["stage_factors"].items()}
    return result


def quality_factor(quality,span):
    return 1+span*max(-1.,min(1.,(quality-70)/30))


def apply_stage_context(inputs, policies):
    """Fill unknown settings, preserving map-specific venue observations."""
    for events in inputs[2].values():
        for event,rows in events.items():
            policy=policies[event]
            corrected=[]
            for idx,stage,venue,*stats in rows:
                if policy.get("opening_knockout") and stage=="group":
                    stage="playoff"
                context=policy.get("final",policy["playoff"]) if stage=="final" else policy["group" if stage=="group" else "playoff"]
                if venue=="unknown":
                    venue={"arena":"arena","studio":"studio","studio_audience":"studio"}.get(context,venue)
                corrected.append((idx,stage,venue,*stats))
            events[event]=corrected


def attach_vps(inputs, records, cutoff):
    catalog,awards,stats,_,_=inputs
    by_event=defaultdict(dict)
    cap=iso(cutoff,"VP cutoff")
    for r in records:
        stamp=iso(r["published_on"],"VP publication")
        if stamp>cap:
            continue
        name,pid=r["event"],r["player"]
        url=urlsplit(r["source"])
        require(url.scheme=="https" and url.hostname in ("hltv.org","www.hltv.org") and url.path.startswith("/news/")
                and r["evidence"] and r["grade"] in ("VP","high VP"),"VP 需附 HLTV 明确评语、日期与级别")
        require(name in catalog and stats.get(pid,{}).get(name),f"VP 缺少本站出场记录 {name}/{pid}")
        require(stamp>=iso(catalog[name]["last_played"],"event end"),f"VP 早于赛事结束 {name}/{pid}")
        a=awards[name]
        require(pid not in [a["mvp"],*a["evps"],*a.get("unranked_evps",[])] and pid not in by_event[name],
                f"同站荣誉重复 {name}/{pid}")
        by_event[name][pid]=dict(r)
    for name,a in awards.items():
        a["verified_vps"]=by_event[name]
    return sum(map(len,by_event.values()))
