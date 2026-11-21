"""Transferable year-end features. No annual selection labels are used here."""
import csv
import gzip
import math
from collections import defaultdict
from statistics import mean

from .core import HIGH, require
from .event_policy import quality_factor
from .pipeline import ROOT, load


def series_cell(rows, config):
    """Weight series or single-stage event Ratings by covered maps, retaining box scores elsewhere."""
    n = len(rows)
    covered = [row for row in rows if row[6] is not None or row[7] is not None]
    raw = mean(r[0] for r in rows) if n else None
    value = raw
    rating = None
    if covered:
        rating = mean(r[7] if r[7] is not None else r[6] for r in covered)
        observed = 50 + (rating-config["rating_center"])/config["rating_index_slope"]
        value += config["measured_series_share"]*len(covered)/n*(observed-mean(r[0] for r in covered))
    return {"maps":n, "box_index":raw, "rating_maps":len(covered), "observed_rating":rating,
            "whole_stage_maps":sum(r[7] is not None for r in rows),"index":value}


def regularized(cell, prior, prior_maps):
    if not cell["maps"]:
        return prior
    return prior + cell["maps"]/(cell["maps"]+prior_maps)*(cell["index"]-prior)


def mvp_quality(rows, config, overall, event_overall=None):
    playoff_rows = [r for r in rows if r[1] in ("playoff","final")]
    late = series_cell(playoff_rows, config)
    if len(playoff_rows)==len(rows):
        late["index"] = overall
    wins = shrunk([r[0] for r in rows if r[5]], overall, 5)
    whole = overall if event_overall is None else event_overall
    return .45*whole + .35*regularized(late,overall,4) + .20*wins


def event_signals(inputs, config):
    catalog,_,stats,_,_ = inputs
    signals = {}
    fields = defaultdict(list)
    for pid,events in stats.items():
        for event,rows in events.items():
            cell = series_cell(rows,config)
            index_value = cell["index"]
            rating = catalog[event].get("event_ratings",{}).get(pid)
            partial = catalog[event].get("partial_ratings", {}).get(pid)
            if partial:
                rating = partial["rating"]
            if rating is not None:
                measured = 50+(rating-config["rating_center"])/config["rating_index_slope"]
                index_value = cell["box_index"]+config["measured_series_share"]*(measured-cell["box_index"])
            # The longer event observation cannot replace a stage or map-win sample.
            local = cell["index"] if partial else index_value
            quality = mvp_quality(rows,config,local,index_value)
            quality_with_overall = .70*quality+.30*index_value
            signals[pid,event] = (index_value,quality,quality_with_overall)
            if len(rows)>=config["peak_min_maps"]:
                fields[event].append(quality_with_overall)
    thresholds = {e:sorted(v)[math.ceil(config["peak_percentile"]*len(v))-1] for e,v in fields.items()}
    return signals,thresholds


def clip(x, low=0., high=100.):
    return max(low, min(high, x))


def shrunk(values, prior=50., k=18):
    return (sum(values) + k*prior)/(len(values)+k)


def index(row):
    """Transparent box-score index on our own scale; not a Rating 3.0 estimate."""
    rounds = int(row["rounds"])
    return (50 + 105*(int(row["kills"])/rounds-.67) - 65*(int(row["deaths"])/rounds-.67)
            + .55*(float(row["adr"])-74) + .30*(float(row["kast"])-72))


def season_inputs(year, detailed_rosters=False, stage_exceptions=None, preserve_unknown=False, partial_event_ratings=False):
    catalog = {e["event"]: e for e in load("data/reference/season_stage_catalog.json")[str(year)]}
    formats=load("data/reference/event_formats_4_3.json")[str(year)] if detailed_rosters else {}
    if year == 2025:
        awards = load("data/2025/awards.json")
    else:
        awards = {e["event"]:e for e in load("data/reference/evp_orders_2026.json")["events"]}
        fixed = {e["event"]:e["tier"] for e in load("data/reference/event_tiers_2026_user.json")["events"]}
        require(fixed == {k:v["tier"] for k,v in catalog.items()}, "Stage catalog changed fixed tiers")
    require(set(awards) == set(catalog), "Incomplete awards scope")
    for event, (pid, signal, note) in load("data/reference/first_evp_context.json")[str(year)].items():
        require(awards[event]["evps"][0] == pid and signal in ("close", "clear"),
                "Editorial evidence does not match the first EVP at "+event)
        awards[event]["first_evp_context"] = {"signal": signal, "note": note}
    for event, players in load("data/reference/peak_context.json")[str(year)].items():
        for pid, record in players.items():
            require(pid in awards[event]["evps"] and record["source"]==awards[event]["source"]
                    and record["signal"] in ("close","clear"), "Unverified peak context")
        awards[event]["peak_context"] = players
    stats, names = defaultdict(lambda: defaultdict(list)), {}
    rosters=defaultdict(lambda:defaultdict(set))
    starts={}
    lineup_rows=defaultdict(list)
    series = {(r["event"],r["match"]):r for r in load(f"data/{year}/series_ratings.json")["series"]}
    cap_date = str(year)+"-12-31" if year == 2025 else load("config/season_model.json")["cutoff"]
    exceptions = {(e["event"], e["match"]): e for e in stage_exceptions or ()}
    require(len(exceptions) == len(stage_exceptions or ()), "Duplicate stage exception")
    observed = defaultdict(set)
    with gzip.open(ROOT/"data"/str(year)/"stage_maps.csv.gz","rt",encoding="utf8") as stream:
        for r in csv.DictReader(stream):
            require(r["date"][:4] == str(year) and r["date"] <= cap_date and r["event"] in catalog,
                    "Map outside the requested season")
            pid = r["player"].casefold()
            if detailed_rosters:
                env=formats[r["event"]].get("match_venues",{}).get(r["match"])
                if env:
                    r["venue"]=env
                lineup_rows[r["event"]].append({k:r[k] for k in ("team","date","match","map","player")})
            names[pid] = r["player"]
            rosters[r["event"]][r["team"]].add(pid)
            starts[r["event"]]=min(starts.get(r["event"],r["date"]),r["date"])
            measured = series.get((r["event"],r["match"]))
            if measured:
                require(measured["stage"] == r["stage"] and pid in measured["ratings"], "Series mismatch")
            stage = r["stage"]
            key = r["event"], r["match"]
            if key in exceptions:
                rule = exceptions[key]
                require(stage == rule["raw_stage"] and r["map"] in rule["maps"]
                        and rule["official_playoff"] is False
                        and rule["phase"] in ("placement", "quarterfinal"), "Stage exception mismatch")
                stage = rule["phase"]
                observed[key].add(r["map"])
            rank = int(r["opponent_rank"]) if r["opponent_rank"] else (None if preserve_unknown else 99)
            stats[pid][r["event"]].append((index(r), stage, r["venue"], rank, r["team"], int(r["win"]),
                                          measured["ratings"][pid] if measured else None, None))
    for key, rule in exceptions.items():
        require(observed[key] == set(rule["maps"]), "Missing maps for stage exception " + str(key))
    if year == 2026:
        for p in load("data/2026/aggregate_snapshot.json")["players"]:
            for e in p["events"]:
                event = e["name"]
                rows = stats.get(p["id"],{}).get(event,[])
                if rows and len(rows)==e["maps"]:
                    catalog[event].setdefault("event_ratings",{})[p["id"]]=e["rating"]
                    if len({r[1] for r in rows})==1:
                        stats[p["id"]][event]=[(*r[:7],e["rating"]) for r in rows]
                elif (partial_event_ratings and rows and len(rows) < e["maps"]
                      and e["rating"] is not None and catalog[event]["start"] is None
                      and formats[event]["qualifying"] == "not_scored"):
                    require(p["retrieved_on"] <= cap_date, "Late event rating")
                    catalog[event].setdefault("partial_ratings", {})[p["id"]] = {
                        "rating": e["rating"], "maps": e["maps"], "source": p["event_source"],
                        "as_of": p["retrieved_on"], "archived_maps": len(rows),
                    }
    standings=load("data/reference/vrs_top10_monthly.json")
    for event,teams in rosters.items():
        stamp=max(k for k in standings if k<starts[event])
        snapshot=standings[stamp]
        if detailed_rosters:
            from .event_policy import roster_evidence
            catalog[event]["roster_evidence"]=roster_evidence(lineup_rows[event],snapshot,stamp,
                                              supplements=formats[event].get("opening_lineups",[]))
            catalog[event]["last_played"]=max(r["date"] for r in lineup_rows[event])
        entered=[rank for rank,_,lineup in snapshot["teams"] if
                 any(len(roster.intersection(p.casefold() for p in lineup))>=3 for roster in teams.values())]
        catalog[event]["field_strength"]=sum(1 if k<=5 else .5 for k in entered)/7.5
    finals = {e["event"]:set(e["finalists"]) for e in load("data/reference/stage_collection_audit.json")["events"]
              if e["year"] == str(year)}
    return catalog,awards,stats,names,finals


def features(inputs, base, config, year, near=True, venue=True, tier_override=None, within_tier=True, peak_proximity=True):
    catalog,awards,stats,names,finalists = inputs
    tiers = {event:e["tier"] for event,e in catalog.items()}
    if tier_override:
        event, tier = tier_override
        require(event in tiers and tier in base["tiers"], "Unknown sensitivity event or tier")
        tiers[event] = tier
    strength = {t:p["weight"] for t,p in base["tiers"].items()}
    field_means={t:mean(e["field_strength"] for k,e in catalog.items() if tiers[k]==t) for t in set(tiers.values())}
    field={k:clip(1+.30*(e["field_strength"]-field_means[tiers[k]]),.86,1.14) if within_tier else 1.
           for k,e in catalog.items()}
    policies=config.get("event_policies",{})
    if policies:
        field={k:v["event_factor"] for k,v in policies.items()}
    award_log = defaultdict(list)
    resume_factors = {event: config["tier_resume_factors"][tier] *
                      (config["big_event_resume_adjustments"].get(event,1.) if tier=="Big" else 1.)
                      for event,tier in tiers.items()}
    signals,peak_thresholds = event_signals(inputs,config)
    benchmarks = {}
    for event,a in awards.items():
        tier = tiers[event]
        require(len(set([a["mvp"]]+a["evps"]+a.get("unranked_evps",[]))) ==
                1+len(a["evps"])+len(a.get("unranked_evps",[])), "Duplicate award at "+event)
        grades = base["tiers"][tier]
        entries = ([(a["mvp"],"MVP",None)] if a["mvp"] else []) + [(pid,"EVP",i) for i,pid in enumerate(a["evps"],1)]
        entries.extend((pid,"EVP",None) for pid in a.get("unranked_evps",[]))
        mvp_rows = stats.get(a["mvp"],{}).get(event,[])
        if mvp_rows:
            benchmarks[event] = signals[a["mvp"],event][1]
        rivals = [value[2] for (pid,name),value in signals.items()
                  if name==event and pid!=a["mvp"] and len(stats[pid][event])>=config["peak_min_maps"]]
        documented_challenger = (a.get("first_evp_context",{}).get("signal")=="close" or
                                 any(record["signal"]=="close" for record in a.get("peak_context",{}).values()))
        for pid,kind,pos in entries:
            points = grades["MVP"] if kind=="MVP" else grades.get("EVP"+str(pos),grades["EVP"])
            if pos and pos>=3:
                points *= max(base["evp_tail_floor"],1-base["evp_tail_step"]*(pos-3))
            dominance = 0.
            if kind=="MVP" and not a.get("pending") and not documented_challenger and len(mvp_rows)>=config["peak_min_maps"] and rivals:
                quality=signals[pid,event][2]
                margin=quality-max(rivals)
                if quality>=config["exceptional_peak_threshold"]:
                    dominance=points*config["dominant_mvp_max_premium"]*clip(margin/20,0,1)
            gap = None
            near_bonus = 0.
            context = a.get("first_evp_context") if pos == 1 else a.get("peak_context",{}).get(pid)
            if pos==1 or context:
                other = stats.get(pid,{}).get(event,[])
                fraction = 0.
                if mvp_rows and other:
                    gap = benchmarks[event]-signals[pid,event][1]
                    sample = min(len(other),len(mvp_rows))
                    fraction = .325*clip(1-max(0,gap)/18,0,1)*sample/(sample+5)
                if context:
                    fraction = .65 if context["signal"] == "close" else 0.
                if near:
                    near_bonus = fraction*(grades["MVP"]-points)
            discount = base["honor_factors"].get(event,1)*field[event]*resume_factors[event]
            if policies and (pid,event) in signals:
                discount*=quality_factor(signals[pid,event][2],config["honor_quality_span"])
            award_log[pid].append(dict(event=event,kind=kind,position=pos,points=(points+near_bonus+dominance)*discount,
                                       dominance_points=dominance*discount,
                                       mvp_index_gap=gap,first_evp_context=context if pos==1 else None,proximity_points=near_bonus*discount,field_factor=field[event],source=a["source"]))
        for pid,record in a.get("verified_vps",{}).items():
            fraction=config["vp_fraction_of_basic_evp"][record["grade"]]
            points=grades["EVP"]*fraction*policies[event]["honor_multiplier"]
            award_log[pid].append(dict(event=event,kind="VP",grade=record["grade"],position=None,
                                       points=points,source=record["source"],published_on=record["published_on"],
                                       evidence=record["evidence"]))
    results = []
    for pid in sorted(set(stats)|set(award_log)):
        ledgers = award_log[pid]
        awarded_events = {award["event"] for award in ledgers}
        tier_values=defaultdict(list)
        opponents,top5,elite,late,elite_late,arena,studio,final,all_maps=[],[],[],[],[],[],[],[],[]
        next_five, unknown_ranks = [], []
        known_outside = 0
        events=[]
        stage_values=defaultdict(list)
        tier_rows = defaultdict(list)
        tier_all = defaultdict(list)
        tier_playoffs = defaultdict(list)
        late_strong,winning_maps,big_late=[],[],[]
        team_points=0.
        for event,rows in stats.get(pid,{}).items():
            tier=tiers[event]
            values=[r[0] for r in rows]
            event_mean=mean(values)
            n=len(rows)
            tier_rows[tier].extend(rows)
            event_index,quality,peak_quality = signals[pid,event]
            full_rating = catalog[event].get("event_ratings",{}).get(pid)
            whole_event = [(*r[:7],full_rating) for r in rows] if full_rating is not None else rows
            tier_all[tier].extend(whole_event)
            playoff_rows = [r for r in rows if r[1] in ("playoff","final")]
            tier_playoffs[tier].extend(whole_event if len(playoff_rows)==n else playoff_rows)
            if policies:
                policy=policies[event]
                event_index=50+(event_index-50)*policy["event_factor"]
                for phase,subset in (("group",[r for r in rows if r[1]=="group"]),
                                     ("playoff",whole_event if len(playoff_rows)==n else playoff_rows)):
                    if subset:
                        groups=defaultdict(list)
                        for r in subset:
                            bucket=phase
                            if phase=="group" and policy.get("match_venues"):
                                bucket="group_arena" if r[2]=="arena" else "group_lan"
                            if r[1]=="final" and "final" in policy:
                                bucket="final"
                            groups[bucket].append(r)
                        for bucket,observed in groups.items():
                            cell=series_cell(observed,config)
                            stage_values[tier,phase].append((len(observed),(cell["index"]-50)*policy["stage_factors"][bucket]))
            tier_values[tier].append((event_index,min(n,base["event_map_cap"])))
            all_maps.extend(values)
            for value,stage,place,rank,team,won,_,_whole in rows:
                if won: winning_maps.append(value)
                if rank is None:
                    unknown_ranks.append(value)
                    if config.get("assume_unknown_6_10"):
                        opponents.append(value)
                        rank = 10
                elif rank <= 10:
                    opponents.append(value)
                    if rank <= 5:
                        top5.append(value)
                    else:
                        next_five.append(value)
                else:
                    known_outside += 1
                if tier in HIGH: elite.append(value)
                if stage in ("playoff","final"):
                    late.append(value)
                    if tier in HIGH: elite_late.append(value)
                    if tier!="Medium": big_late.append(value)
                    if rank is not None and rank<=10: late_strong.append(value)
                if place=="arena": arena.append(value)
                if place=="studio": studio.append(value)
                if stage=="final": final.append(value)
            final_maps = sum(r[1]=="final" for r in rows)
            playoff_maps = sum(r[1] in ("playoff","final") for r in rows)
            # Actual participation, including late substitutes. Tournament placement alone is insufficient.
            if not policies and (final_maps or playoff_maps):
                place = .70 if final_maps else .22
                team_points += place*field[event]*strength[tier]*clip(event_mean/65,0,1.25)*min(n/8,1)*base["honor_factors"].get(event,1)
            gap = benchmarks[event]-quality if event in benchmarks else None
            evidence = awards[event].get("peak_context",{}).get(pid)
            if awards[event]["evps"][:1]==[pid]:
                evidence = awards[event].get("first_evp_context",evidence)
            if pid == awards[event]["mvp"]:
                proximity, basis = 1., "MVP"
            elif evidence:
                proximity = 1. if evidence["signal"]=="close" else 0.
                basis = "官方评语·接近" if proximity else "官方评语·距离明显"
            else:
                proximity = clip(1-max(0.,gap)/18,0,1) if gap is not None else .5
                order = awards[event]["evps"]
                position = order.index(pid)+1 if pid in order else None
                # A statistical tie with the winner carries less evidence down the published award order.
                ceiling = 1/(1+.25*(position-1)) if position else .40
                proximity = min(proximity,ceiling)
                basis = "表现估计" if gap is not None else "缺少对照"
            threshold = peak_thresholds.get(event)
            standout = (n>=config["peak_min_maps"] and threshold is not None and
                        peak_quality>=max(config["peak_min_quality"],threshold))
            confirmed = pid==awards[event]["mvp"] or (evidence is not None and evidence["signal"]=="close")
            peak_class = "官方争奖高峰" if confirmed else ("数据高峰" if standout else "普通站次")
            excess = (peak_quality-50)*n/(n+5)
            multiplier = field[event]*strength[tier]/1.30*resume_factors[event]
            peak_factor = 1-config["peak_proximity_share"]*(1-proximity) if peak_proximity and excess>0 else 1.
            if excess>0 and not (standout or confirmed):
                peak_factor *= .85
            verified_peak = 50 + multiplier*excess*peak_factor
            exceptional_bonus = 0.
            if confirmed:
                exceptional_bonus = (config["exceptional_peak_bonus"]*max(0.,peak_quality-config["exceptional_peak_threshold"])
                                     *n/(n+5)*multiplier)
                verified_peak += exceptional_bonus
            # Distinct from published VP points: recognize unawarded performances using the same observations in both seasons.
            event_credit = 0.
            if event not in awarded_events and n>=config["peak_min_maps"]:
                positive = clip((peak_quality-55)/20,0,1)*.45
                negative = clip((45-peak_quality)/20,0,1)*.25
                event_credit = (positive-negative)*n/(n+8)*base["tiers"][tier]["EVP"]*field[event]*resume_factors[event]
            events.append(dict(event=event,tier=tier,maps=n,index=event_mean,peak=verified_peak,playoff_maps=playoff_maps,
                               event_credit=event_credit,exceptional_bonus=exceptional_bonus,proximity=proximity,
                               mvp=awards[event]["mvp"],mvp_gap=gap,proximity_basis=basis,peak_multiplier=multiplier,
                               peak_factor=peak_factor,event_rating=full_rating,peak_class=peak_class,peak_quality=peak_quality,
                               field_peak_threshold=threshold,source=awards[event]["source"]))
            partial = catalog[event].get("partial_ratings", {}).get(pid)
            if partial:
                events[-1]["whole_event_observation"] = partial
        if not events:
            continue
        n=len(all_maps)
        average=shrunk(all_maps,50,20)
        e_score=0.
        stage_score=0.
        matrix={}
        for tier,params in base["tier_samples"].items():
            cells=tier_values[tier]
            count=sum(w for _,w in cells)
            effective_events=count**2/sum(w*w for _,w in cells) if count else 0
            reliability=count/(count+params["prior_maps"])*effective_events/(effective_events+params["prior_events"])
            value=sum(v*w for v,w in cells)/count if count else 50.
            tier_share = config["tier_shares"][tier]
            e_score+=tier_share*(50+reliability*(value-50))
            rows = tier_rows[tier]
            matrix[tier] = {name:series_cell(subset, config) for name,subset in (
                ("all",tier_all[tier]),("group",[r for r in rows if r[1]=="group"]),
                ("playoff",tier_playoffs[tier]),
                ("final",[r for r in rows if r[1]=="final"]),
                ("placement",[r for r in rows if r[1]=="placement"]))}
            if config.get("version") in ("HTPM-4.4", "HTPM-4.4.1"):
                matrix[tier]["quarterfinal_outside_filter"] = series_cell([r for r in rows if r[1]=="quarterfinal"], config)
            group = regularized(matrix[tier]["group"],50.,params["prior_maps"])
            playoff = regularized(matrix[tier]["playoff"],50.,params["prior_maps"])
            if policies:
                def weighted_phase(phase):
                    cells=stage_values[tier,phase]
                    return 50+sum(n*delta for n,delta in cells)/(params["prior_maps"]+sum(n for n,_ in cells))
                group,playoff=weighted_phase("group"),weighted_phase("playoff")
            stage_score += tier_share*(config["group_share"]*group+(1-config["group_share"])*playoff)
        bands = config.get("opponent_bands")
        if bands:
            six_to_ten = next_five + unknown_ranks if config.get("assume_unknown_6_10") else next_five
            o_score = sum(bands[key]["share"] * shrunk(values, 50, bands[key]["prior_maps"])
                          for key, values in (("1-5", top5), ("6-10", six_to_ten)))
        else:
            o_score=.55*shrunk(top5,50,30)+.45*shrunk(opponents,50,25)
        phase=.80*shrunk(big_late,shrunk(all_maps,50,45),18)+.20*shrunk(late,average,18)
        # Overlapping groups share a fixed budget. Missing slices contribute zero residual.
        pressure=phase+config["elite_playoff_residual"]*(shrunk(elite_late,phase,15)-phase)+.15*(shrunk(final,phase,12)-phase)
        pressure+=.15*(shrunk(late_strong,phase,18)-phase)
        if venue:
            contrast=shrunk(arena,phase,18)-shrunk(studio,phase,18)
            joint=min(len(arena),len(studio))
            pressure+=.20*(shrunk(arena,phase,18)-phase)+.05*joint/(joint+18)*contrast
        pressure += config["tier_stage_share_of_K"]*(stage_score-pressure)
        best=sorted(events,key=lambda e:-e["peak"])
        peak=.55*best[0]["peak"]+.30*(best[1]["peak"] if len(best)>1 else 50)
        # Every event can supply a peak, including performances that earned no award.
        peak+=.15*(best[2]["peak"] if len(best)>2 else 50)
        high_peak = next((e["peak"] for e in best if e["tier"] in HIGH),50.)
        peak += config["top_tier_peak_share"]*(high_peak-peak)
        good=sum(e["index"]>=50 for e in events)
        floor=(sum(v>=35 for v in all_maps)+12*.75)/(n+12)
        resilience=.75*(good+2.6)/(len(events)+4)+.25*floor
        coverage=100*(.25*min(n/145,1)+.35*min(len(elite)/55,1)+.25*min(len(opponents)/75,1)+.15*min(len(elite_late)/20,1))
        event_credit = config["event_credit_share"]*clip(sum(e["event_credit"] for e in events),-config["event_credit_cap"],config["event_credit_cap"])
        resume_points = max(0.,sum(a["points"] for a in ledgers)+event_credit)
        parts=dict(A=100*(1-math.exp(-resume_points/base["award_scale"])),
                   E=clip(e_score),O=clip(o_score),K=clip(pressure),P=clip(peak),
                   T=100*(1-math.exp(-team_points/base["team_scale"])),C=100*resilience,N=coverage)
        eligible=any(a["kind"] in ("MVP","EVP") for a in ledgers) or (n>=config["minimum_discovery_maps"] and len(events)>=config["minimum_discovery_events"])
        def detail(rows):
            return {"maps":len(rows),"index":mean(rows) if rows else None}
        results.append(dict(id=pid,name=names.get(pid,pid),features=parts,eligible=eligible,events=events,awards=ledgers,tier_stages=matrix,
                            event_credit=event_credit,resume_points=resume_points,good_events=good,details={key:detail(rows) for key,rows in
                            zip(("main","elite","top10","top5","playoff","elite_playoff","arena","studio","final","pressure_top10","won","big_playoff"),
                                (all_maps,elite,opponents,top5,late,elite_late,arena,studio,final,late_strong,winning_maps,big_late))}))
        if config.get("version") in ("HTPM-4.4", "HTPM-4.4.1"):
            # Keep observed coverage independent of the counterfactual used for scoring.
            results[-1]["vrs_coverage"] = {
                "top5": len(top5), "six_to_ten": len(next_five),
                "known_outside": known_outside, "unmatched": len(unknown_ranks), "total": n,
                "resolved_fraction": (n-len(unknown_ranks))/n,
            }
            results[-1]["details"]["vrs_6_10"] = detail(next_five)
            results[-1]["details"]["vrs_unmatched"] = detail(unknown_ranks)
    return results
