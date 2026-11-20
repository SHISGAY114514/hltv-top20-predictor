"""Fit on 2025, deploy on the observed season, and audit the selection boundary."""
import copy
import hashlib
from statistics import mean, median

from .core import dump_json, fingerprint, require
from .pipeline import ROOT, load
from .season import clip, features, season_inputs


def ranked(rows, weights, order, omitted=()):
    selected = [(sum(p["features"][k]*w/100 for k,w in zip(order,weights)),p["id"])
                for p in rows if p["eligible"] and p["id"] not in omitted]
    return [pid for _,pid in sorted(selected,key=lambda pair:(-pair[0],pair[1]))]


def metrics(ids, labels):
    pos={p:i for i,p in enumerate(ids,1)}
    order=sorted(labels,key=labels.get)
    top=[p for p in order if labels[p]<=20]
    missing=set(order)-set(ids)
    require(not missing, "Official players absent from replay: "+str(missing))
    comparisons=[pos[a]<pos[b] for i,a in enumerate(order) for b in order[i+1:]]
    return {"top20_hits":len(set(ids[:20]) & set(top)), "top10_hits":len(set(ids[:10]) & set(order[:10])),
            "mae_top20":mean(abs(pos[p]-labels[p]) for p in top),
            "ordered_pairs_top30":sum(comparisons),"pairs":len(comparisons),
            "missed":[p for p in top if pos[p]>20],"false_positives":[p for p in ids[:20] if p not in top]}


def fit(rows,labels,c,omitted=()):
    # Withheld players are removed from both the feature ranking and training targets.
    target=[p for p in sorted(labels,key=labels.get) if p not in omitted]
    positives=[p for p in target if labels[p]<=20]
    records={}
    for name,weights in c["profiles"].items():
        ids=ranked(rows,weights,c["feature_order"],omitted)
        pos={pid:i for i,pid in enumerate(ids,1)}
        error=.5*mean(abs(pos[pid]-i) for i,pid in enumerate(target,1))
        error+=.5*mean(abs(pos[pid]-i) for i,pid in enumerate(positives,1))
        misses=len(set(positives)-set(ids[:len(positives)]))
        records[name]=error+misses*.7
    return min(records,key=records.get),records


def fit_stage_share(variants, labels, config, omitted=()):
    trials = []
    for share,rows in variants.items():
        profile,losses = fit(rows,labels,config,omitted)
        trials.append((share,profile,losses))
    return min(trials,key=lambda trial:trial[2][trial[1]])


def align_legacy(rows, old):
    # Align score units only. Both distributions come from the same eligible players.
    pairs=[(p["portable"],old[p["id"]]["score"]) for p in rows if p["eligible"] and
           p["id"] in old and old[p["id"]]["rank"] is not None]
    def anchors(values):
        xs=sorted(values)
        return median(xs),xs[3*len(xs)//4]-xs[len(xs)//4]
    center,span=anchors([p[0] for p in pairs])
    old_center,old_span=anchors([p[1] for p in pairs])
    require(old_span>0 and span>0,"No dispersion for reference alignment")
    return center,old_center,span/old_span


def published_adjustment(row,cap,config=None):
    if not row:
        return 0.
    config = config or load("config/season_model.json")
    correction=0.
    for stage,w in config["published_weights"].items():
        reference = "elite" if stage=="elite_playoff" else "big"
        n,r=row[stage]
        if n and row[reference][1] is not None:
            correction+=w*n/(n+18)*(r-row[reference][1])
    return clip(config["published_scale"]*correction,-cap,cap)


def predict(rows,weights,c,old,published,alignment=None,legacy=True,article=True):
    people=[]
    for p in rows:
        p=dict(p)
        p["contributions"]={k:p["features"][k]*w/100 for k,w in zip(c["feature_order"],weights)}
        p["portable"]=sum(p["contributions"].values())
        people.append(p)
    center,old_center,slope=alignment or align_legacy(people,old)
    for p in people:
        other=old.get(p["id"])
        official=published.get(p["id"])
        p["legacy_rank"]=other["rank"] if other else None
        p["legacy_score"]=other["score"] if other else None
        p["published"]=official
        if other:
            p["name"]=other["name"]
            p["hltv_top5"]=other["opponents"]["5"]
            p["hltv_tiers"]={k:{"rating":v["raw_rating"],"maps":v["maps"]}
                             for k,v in other["event_rating"]["tier_samples"].items()}
        correction=0.
        if legacy and other and other["score"] is not None:
            projected=center+slope*(other["score"]-old_center)
            correction=clip(c["legacy_share"]*(projected-p["portable"]),-c["legacy_adjustment_cap"],c["legacy_adjustment_cap"])
            if other["rank"] is None:
                counts=other["counts"]
                correction*=min(1,counts["main_maps"]/50,counts["elite_maps"]/20,counts["top10_maps"]/10)
        p["contributions"]["H"]=correction
        p["contributions"]["R"]=published_adjustment(official,c["published_stage_cap"],c) if article else 0.
        p["score"]=sum(p["contributions"].values())
    people.sort(key=lambda p:(not p["eligible"],-p["score"],p["id"]))
    for i,p in enumerate(people,1):
        p["rank"]=i if p["eligible"] else None
    return people,(center,old_center,slope)


def major_replay(inputs,template):
    catalog,awards,stats,names,finals=copy.deepcopy(inputs)
    event="条件情景："+template
    catalog[event]={**catalog[template],"tier":"Major"}
    awards[event]=awards[template]
    finals[event]=finals[template]
    for events in stats.values():
        if template in events:
            events[event]=events[template]
    return catalog,awards,stats,names,finals


def rating_audit(past,current,legacy):
    """Check the box-score signal on a different season without changing any ranks."""
    reference=load("data/2025/official_event_tables.json")
    aliases={e["official_event"]:e["event"] for e in load("data/reference/season_stage_catalog.json")["2025"]}
    indexes={(p["id"],e["event"]):e["index"] for p in past for e in p["events"]}
    sample=[(indexes[pid,aliases[e["event"]]],e["rating"]) for pid,person in reference.items()
            for e in person["events"] if (pid,aliases[e["event"]]) in indexes]
    xbar,ybar=(mean(col) for col in zip(*sample))
    slope=sum((x-xbar)*(y-ybar) for x,y in sample)/sum((x-xbar)**2 for x,y in sample)
    current_by={(p["id"],e["event"]):e for p in current for e in p["events"]}
    matched=[]
    comparable=[]
    for p in legacy.values():
        for e in p["events"]:
            mine=current_by.get((p["id"],e["name"]))
            if e["in_scope"] and mine:
                error=abs(ybar+slope*(mine["index"]-xbar)-e["rating"])
                matched.append(error)
                if mine["maps"]==e["maps"]:comparable.append(error)
    return {"event_cells_2025":len(sample),"slope":slope,"intercept":ybar-slope*xbar,
            "event_cells_2026":len(matched),"mae_rating_2026":mean(matched),"same_count_cells":len(comparable),
            "same_count_mae":mean(comparable)}


def run(base_result,write=True):
    config=load("config/season_model.json")
    base=load("config/model.json")
    labels={**load("data/reference/official_top20_2025.json")["ranks"],**load("data/2025/boundary_ranks.json")["ranks"]}
    order=config["feature_order"]
    require(all(len(w)==len(order) and sum(w)==100 for w in config["profiles"].values()),"Invalid profiles")
    for shares in (config["tier_shares"],config["published_weights"]):
        require(all(w>=0 for w in shares.values()) and abs(sum(shares.values())-1)<1e-8,"Invalid evidence shares")
    require(set(config["tier_shares"])==set(base["tier_samples"])==set(config["tier_resume_factors"]),"Tier mismatch")
    past_inputs=season_inputs(2025)
    current_inputs=season_inputs(2026)
    variants={(stage,credit):features(past_inputs,base,{**config,"tier_stage_share_of_K":stage,"event_credit_share":credit},2025)
              for stage in config["stage_share_candidates"] for credit in config["event_credit_candidates"]}
    selected_variant,profile,losses=fit_stage_share(variants,labels,config)
    share,credit=selected_variant
    config={**config,"tier_stage_share_of_K":share,"event_credit_share":credit}
    past=variants[selected_variant]
    weights=config["profiles"][profile]
    past_ids=ranked(past,weights,order)
    replay={"profiles":losses,"chosen":profile,"tier_stage_share_of_K":share,"event_credit_share":credit,"metrics":metrics(past_ids,labels),
            "balanced":metrics(ranked(past,config["profiles"]["balanced"],order),labels),
            "awards_only":metrics(ranked(past,[100,0,0,0,0,0,0,0],order),labels),
            "event_performance_only":metrics(ranked(past,[0,100,0,0,0,0,0,0],order),labels),
            "eligible":len(past_ids),"players":{p:{"actual":r,"predicted":past_ids.index(p)+1} for p,r in labels.items()}}
    # Cross-fit profile selection. All 2025 fixtures and labels belong to the same season.
    fold=lambda pid:int(hashlib.sha256(pid.encode()).hexdigest(),16)%5
    heldout=[]
    pred_scores={}
    for i in range(5):
        omitted={p["id"] for p in past if fold(p["id"])==i}
        fold_share,training,_=fit_stage_share(variants,labels,config,omitted)
        selected=config["profiles"][training]
        heldout.append({"fold":i,"profile":training,"stage_share":fold_share[0],"event_credit_share":fold_share[1],"target_count":len(omitted & labels.keys())})
        for p in variants[fold_share]:
            if p["eligible"] and p["id"] in omitted:
                pred_scores[p["id"]]=sum(p["features"][k]*w/100 for k,w in zip(order,selected))
    replay["folds"]=heldout
    replay["cross_fitted"]=metrics(sorted(pred_scores,key=lambda p:(-pred_scores[p],p)),labels)
    old={p["id"]:p for p in base_result["players"]}
    article=load("data/2026/published_stage_ratings.json")
    require(article["as_of"]==config["cutoff"]==base_result["metadata"]["snapshot_as_of"],"Incompatible snapshots")
    current=features(current_inputs,base,config,2026)
    replay["boxscore_audit"]=rating_audit(past,current,old)
    people,alignment=predict(current,weights,config,old,article["players"])
    scenarios={}
    def scenario(name,rows=current,w=weights,legacy=True,external=True):
        result,_=predict(rows,w,config,old,article["players"],alignment,legacy,external)
        scenarios[name]={p["id"]:p["rank"] for p in result if p["eligible"]}
    scenario("base")
    for candidate_share in config["stage_share_candidates"]:
        if candidate_share != share:
            scenario("stage_share_"+str(candidate_share),features(current_inputs,base,{**config,"tier_stage_share_of_K":candidate_share},2026))
    for candidate_credit in config["event_credit_candidates"]:
        if candidate_credit != credit:
            scenario("event_credit_"+str(candidate_credit),features(current_inputs,base,{**config,"event_credit_share":candidate_credit},2026))
    for name,w in config["profiles"].items():
        if name!=profile:
            scenario("profile_"+name,w=w)
    scenario("portable_only",legacy=False,external=False)
    scenario("no_legacy",legacy=False)
    scenario("no_published_stage",external=False)
    for key in ("K","T","N"):
        reduced=[0 if name==key else w for name,w in zip(order,weights)]
        scenario("without_"+key,w=[100*w/sum(reduced) for w in reduced])
    scenario("flat_first_evp",features(current_inputs,base,config,2026,near=False))
    scenario("flat_within_tier",features(current_inputs,base,config,2026,within_tier=False))
    scenario("no_arena_residual",features(current_inputs,base,config,2026,venue=False))
    for tag,event,tier in (("cluj_in_elite","PGL Cluj-Napoca 2026","Elite"),
                           ("hong_kong_in_elite","BLAST Rivals 2026 Season 2","Elite"),
                           ("ewc_in_super_elite","Esports World Cup 2026","Super-elite")):
        scenario(tag, features(current_inputs,base,config,2026,tier_override=(event,tier)))
    replay["ablations"]={}
    for tag,overrides in (("without_tier_stage",{"tier_stage_share_of_K":0}),
                          ("without_dominant_mvp",{"dominant_mvp_max_premium":0,"exceptional_peak_bonus":0}),
                          ("without_event_credit",{"event_credit_cap":0}),
                          ("without_high_peak",{"top_tier_peak_share":0}),
                          ("without_event_adjustments",{"big_event_resume_adjustments":{}}),
                          ("original_tier_shares",{"tier_shares":{t:v["weight"] for t,v in base["tier_samples"].items()}}),
                          ("without_series_rating",{"measured_series_share":0})):
        alternate=features(past_inputs,base,{**config,**overrides},2025)
        replay["ablations"][tag]=metrics(ranked(alternate,weights,order),labels)
        scenario(tag,features(current_inputs,base,{**config,**overrides},2026))
    for tag,options in (("flat_first_evp",{"near":False}),("flat_within_tier",{"within_tier":False}),
                        ("no_arena_residual",{"venue":False}),("without_peak_proximity",{"peak_proximity":False})):
        alternate=features(past_inputs,base,config,2025,**options)
        replay["ablations"][tag]=metrics(ranked(alternate,weights,order),labels)
    no_k=[0 if k=="K" else w for k,w in zip(order,weights)]
    scenario("without_peak_proximity",features(current_inputs,base,config,2026,peak_proximity=False))
    replay["ablations"]["without_K"]=metrics(ranked(past,no_k,order),labels)
    for p in people:
        if p["rank"]:
            ranks=[r[p["id"]] for r in scenarios.values()]
            p["range"]=[min(ranks),max(ranks)]
    futures={}
    for event in ["IEM Cologne Major 2026","BLAST Rivals 2026 Season 2","IEM Beijing 2026"]:
        projected=features(major_replay(current_inputs,event),base,config,2026)
        alt,_=predict(projected,weights,config,old,article["players"],alignment,legacy=False,article=False)
        # The observable legacy and article evidence belongs to the original cutoff.
        offsets={p["id"]:p["contributions"]["H"]+p["contributions"]["R"] for p in people}
        eligible=sorted((p for p in alt if p["eligible"]),
                        key=lambda p:(-p["portable"]-offsets.get(p["id"],0),p["id"]))
        futures[event]=[p["id"] for p in eligible[:30]]
    coverage={}
    for year,rows,inputs in ((2025,past,past_inputs),(2026,current,current_inputs)):
        series=load(f"data/{year}/series_ratings.json")["series"]
        coverage[str(year)]={"verified_series":len(series),"tiers":{},
                             "events":{name:{"tier":entry["tier"],"verified_series":sum(r["event"]==name for r in series)}
                                       for name,entry in inputs[0].items()}}
        for tier in base["tier_samples"]:
            coverage[str(year)]["tiers"][tier]={}
            for stage in ("all","group","playoff","final","placement"):
                cells=[p["tier_stages"][tier][stage] for p in rows]
                coverage[str(year)]["tiers"][tier][stage]={k:sum(c[k] for c in cells) for k in ("maps","rating_maps","whole_stage_maps")}
    result={"version":config["version"],"release_date":config["release_date"],"cutoff":config["cutoff"],"profile":profile,"weights":dict(zip(order,weights)),
            "alignment":list(alignment),"replay":replay,"rating_coverage":coverage,
            "scenarios":scenarios,"major_scenarios":futures,"players":people}
    if write:
        folder=ROOT/"output/forecast_4_1_1"
        dump_json(folder/"scores.json",result)
        inputs=["config/model.json","config/season_model.json","data/2025/awards.json","data/2025/boundary_ranks.json",
                "data/reference/official_top20_2025.json","data/reference/season_stage_catalog.json",
                "data/reference/vrs_top10_monthly.json","data/reference/evp_orders_2026.json","data/reference/first_evp_context.json",
                "data/reference/stage_collection_audit.json","data/2026/published_stage_ratings.json",
                "data/2026/hong_kong_final_maps.json","data/2025/official_event_tables.json",
                "data/2025/stage_maps.csv.gz","data/2026/stage_maps.csv.gz","data/2025/series_ratings.json",
                "data/2026/series_ratings.json","data/reference/event_tiers_2026_user.json","data/reference/peak_context.json",
                "data/2026/aggregate_snapshot.json"]
        dump_json(folder/"manifest.json",{"sha256":{k:hashlib.sha256((ROOT/k).read_bytes()).hexdigest() for k in inputs},
                                         "legacy_result":fingerprint(base_result),"historical_fit":replay["chosen"]})
        from .season_report import report
        report(result,folder)
    return result
