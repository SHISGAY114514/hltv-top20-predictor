"""Fit shared context coefficients to published ordinal evidence, never to player names in deployment."""
from itertools import combinations,product
from .core import require
from .event_policy import event_policy,quality_factor
from .pipeline import load
from .season import features


def calibrate(inputs,c,base):
    evidence=load("data/reference/award_order_2025.json")
    # Unweighted unit award: preserve grade, EVP proximity and MVP dominance.
    initial=event_policy(inputs,2025,c,constrain_history=False)
    ref={**c,"event_policies":initial,"honor_quality_span":0}
    rows=features(inputs,base,ref,2025)
    unit={}
    for p in rows:
        if p["id"] not in evidence["within_player"]:
            continue
        quality={e["event"]:e["peak_quality"] for e in p["events"]}
        for a in p["awards"]:
            e=a["event"]
            unit[p["id"],a["kind"],e]=(a["points"]/initial[e]["honor_multiplier"],quality.get(e,70.))
    def concordance(sequences,values):
        diffs=[values[a]-values[b] for seq in sequences for a,b in combinations(seq,2)]
        return sum(1 if d>1e-9 else .5 if abs(d)<=1e-9 else 0 for d in diffs),len(diffs)
    names=("roster_span","field_size_span","venue_span","honor_quality_span")
    candidates=[]
    for a,b,v,q in product((.15,.30,.45),(.04,.08,.12),(.5,1.,1.5),(0.,.15,.30)):
        chosen=dict(zip(names,(a,b,v,q)))
        policy=event_policy(inputs,2025,{**c,**chosen},constrain_history=False)
        evt=concordance(evidence["within_tier"].values(),{e:p["event_factor"] for e,p in policy.items()})
        indiv={}
        for pid,awards in evidence["within_player"].items():
            values={}
            groups=[]
            for kind,order in awards.items():
                groups.append([(kind,e) for e in order])
                for e in order:
                    require((pid,kind,e) in unit,"播客荣誉顺序与档案不符")
                    magnitude,quality=unit[pid,kind,e]
                    values[kind,e]=magnitude*policy[e]["honor_multiplier"]*quality_factor(quality,q)
            indiv[pid]=concordance(groups,values)
        distance=sum(((x-center)/step)**2 for x,center,step in zip((a,b,v,q),(.3,.08,1.,.15),(.15,.04,.5,.15)))
        def loss(ids):
            player_hits=sum(indiv[k][0] for k in ids)/sum(indiv[k][1] for k in ids)
            return .5*(1-evt[0]/evt[1])+.5*(1-player_hits)+.005*distance
        candidates.append((chosen,evt,indiv,{k:loss([k]) for k in indiv},loss(list(indiv))))
    selected=min(candidates,key=lambda t:t[-1])
    heldout={}
    for test,train in (("zywoo","donk"),("donk","zywoo")):
        other=min(candidates,key=lambda t:t[3][train])
        heldout[test]={"weights":other[0],"correct_and_pairs":other[2][test]}
    return {"weights":selected[0],"tier_pairs_before_monotone_projection":selected[1],
            "player_award_pairs":selected[2],"held_out_player":heldout,"candidates":len(candidates),
            "source":evidence["podcast"],"slide":evidence["slide"]}
