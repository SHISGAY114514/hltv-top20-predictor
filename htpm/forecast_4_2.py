"""The 2026 two-Major release. All inputs are observed through one explicit cutoff."""
import json
import os
import shutil
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from .aggregate import score
from .core import fingerprint, number, require
from .major_import import DEFAULT_INPUT, import_event, link, read_json
from .pipeline import ROOT, load, prepare
from .season import features, season_inputs
from .season_forecast import metrics, predict, ranked

DEST = ROOT/"output/forecast_4_2"
LABEL = {"A":"荣誉履历","E":"分档赛事表现","O":"强敌表现","K":"关键阶段","P":"高峰",
         "T":"团队成绩","C":"稳定性","N":"样本覆盖","H":"年度汇总校正","R":"公开阶段表校正"}
STATES = {"snapshot":"单 Major 赛前快照", "provisional":"双 Major 暂行预测（官方奖项待齐）",
          "formal":"双 Major 正式预测"}


def settings():
    spec = load("config/season_4_2.json")
    config = load("config/season_model.json")
    config.update({k:spec[k] for k in ("version","tier_stage_share_of_K","event_credit_share")})
    return spec, config, config["profiles"][spec["profile"]]


def dated_file(path, cutoff, key):
    if not path.exists():
        return None, "未提供"
    data = read_json(path)
    stamp = data["metadata"]["snapshot_as_of"] if key == "H" else data["as_of"]
    if stamp != cutoff:
        return None, f"日期 {stamp} 与榜单截止日不同"
    return data, "已采用"


def individual_reference(params):
    weights=params["weights"]
    remaining=sum(w for k,w in weights.items() if k!="T")
    return {**params,"weights":{k:w/remaining if k!="T" else 0 for k,w in weights.items()}}


def additions(inputs, folder, audit, spec, config):
    catalog,awards,stats,_,_ = inputs
    old, published = {}, {}
    h, h_note = dated_file(folder/"aggregate.json", audit["cutoff"], "H")
    if h:
        meta = h["metadata"]
        require(meta["year"] == 2026 and meta["query_end"] == audit["cutoff"], "H 年度统计筛选范围不符")
        _, params, _ = prepare()
        event = spec["event"]
        params["event_tiers"][event] = "Major"
        params["event_medals"][event] = "gold"
        params["tier_samples"]["Major"].update(target_events=2, target_maps=2*spec["major_target_maps_per_event"])
        for p in h["players"]:
            pid = p["id"]
            maps = sum(e["maps"] for e in p["events"] if e["name"] == event)
            require(maps == len(stats.get(pid,{}).get(event,[])), f"H 新加坡地图数不符 {pid}")
            expected = {(name,"MVP",None) for name,a in awards.items() if a["mvp"] == pid}
            for name,a in awards.items():
                if pid in a["evps"]:
                    expected.add((name,"EVP",a["evps"].index(pid)+1))
                if pid in a.get("unranked_evps",[]):
                    expected.add((name,"EVP",None))
            require(expected == {(a["event"],a["type"],a.get("evp_rank")) for a in p["awards"]}, f"H 荣誉不一致 {pid}")
        old = {p["id"]:p for p in score(h,individual_reference(params) if spec.get("detailed_rosters") else params)["players"]}
    table, r_note = dated_file(folder/"published.json", audit["cutoff"], "R")
    if table:
        link(table["source"])
        require(set(table["events"]) == set(catalog) and table["rating_version"] == "3.0", "R 赛事白名单或 Rating 版本不符")
        for pid, row in table["players"].items():
            require(pid in stats, f"R 未识别选手 {pid}")
            for k in {"big", *config["published_weights"]}:
                n,r = row[k]
                require(type(n) is int and n >= 0 and (n==0)==(r is None), f"R 样本错误 {pid}/{k}")
                if n:
                    number(r,0,10,"R Rating")
        published = table["players"]
    return old,published,{"H":h_note,"R":r_note}


def calculate(folder=None, today=None, model="4.2", *, scenario=None):
    spec, config, weights = settings()
    revision = model == "4.4"
    detailed = model in ("4.3", "4.4")
    require(scenario is None or revision and scenario in {
        "legacy_stage", "nested_opponents", "unknown_6_10", "no_vp", "equal_tiers"
    }, "Unknown model scenario")
    if detailed:
        policy_config=load("config/season_4_3.json")
        config.update(policy_config)
        weights=[policy_config["weights"][k] for k in config["feature_order"]]
        spec={**spec,"version":policy_config["version"],"detailed_rosters":True}
    exceptions = None
    if revision:
        from .frozen_4_4 import configure
        exceptions = configure(config, load("config/season_4_4.json"), scenario)
        spec["version"] = config["version"]
    folder = Path(folder) if folder is not None else ROOT/DEFAULT_INPUT
    today = today or date.today()
    if revision:
        today = date.fromisoformat(config["cutoff"])
        require(folder == ROOT/DEFAULT_INPUT and not any((folder/name).exists() for name in ("results.zip","vps.json")),
                "4.4 requires the frozen pre-Singapore input")
    inputs = season_inputs(2026, detailed_rosters=detailed, stage_exceptions=exceptions, preserve_unknown=revision)
    base = load("config/model.json")
    meta = read_json(folder/"event.json")
    if revision:
        require(meta["as_of"] is None, "4.4 requires the frozen pre-Singapore input")
    if meta["as_of"] is None and (folder/"results.zip").is_file() and not meta["awards"].get("mvp"):
        meta["as_of"] = spec["end"]
    if meta["as_of"] is None:
        require(today.isoformat() < spec["end"], "决赛日已到，需要导入实际赛程、逐图统计并填写 as_of 后再出榜")
        audit = {"state":"snapshot","cutoff":config["cutoff"]}
        raw, params, _ = prepare()
        old = {p["id"]:p for p in score(raw,individual_reference(params) if detailed else params)["players"]}
        table = load("data/2026/published_stage_ratings.json")
        require(raw["metadata"]["snapshot_as_of"] == table["as_of"] == audit["cutoff"], "快照日期冲突")
        published = table["players"]
        adjustments = dict(H="已采用",R="已采用")
    else:
        audit = import_event(inputs,folder,spec,today,meta)
        old,published,adjustments = additions(inputs,folder,audit,spec,config)
    if detailed:
        from .event_policy import attach_vps,event_policy,apply_stage_context
        records=load("data/reference/official_vps_4_3.json")["2026"]
        if (folder/"vps.json").exists():
            records=records+read_json(folder/"vps.json")
        config["event_policies"]=event_policy(inputs,2026,config)
        apply_stage_context(inputs,config["event_policies"])
        audit["event_weights"]=config["event_policies"]
        audit["confirmed_vps"]=attach_vps(inputs, [] if scenario == "no_vp" else records, audit["cutoff"])
    rows = features(inputs,base,config,2026)
    # Even with a fresh partial aggregate, alignment needs a usable shared distribution.
    alignment = None
    if old:
        shared = [old[p["id"]]["score"] for p in rows if p["eligible"] and p["id"] in old and old[p["id"]]["rank"]]
        shared.sort()
        if len(shared)<4 or shared[3*len(shared)//4] == shared[len(shared)//4]:
            old = {}
            adjustments["H"] = "共同样本不足以校准"
    if not old:
        alignment = (0.,0.,1.)
    people,_ = predict(rows,weights,config,old,published,alignment,legacy=bool(old),article=bool(published))
    # Only the displayed comparison rank uses the archived release.
    baseline = (load(f"output/forecast_4_3/snapshot/{config['base_snapshot']}/scores.json")
                if revision else load("output/forecast_4_1_1/scores.json"))
    previous = {p["id"]:p["rank"] for p in baseline["players"]}
    for p in people:
        p["snapshot_rank"] = previous.get(p["id"])
    if revision:
        audit["stage_exceptions"] = exceptions or []
        audit["opponent_source"] = "Pre-map monthly global VRS top ten, three-player overlap"
        audit["scenario"] = scenario
        audit["input_hash"] = config["input_hash"]
        audit["baseline_snapshot"] = config["base_snapshot"]
    majors = [k for k,e in inputs[0].items() if e["tier"] == "Major"]
    return {"version":spec["version"],**audit,"adjustments":adjustments,"weights":dict(zip(config["feature_order"],weights)),
            "scope":list(inputs[0]),"majors":majors,"major_share":config["tier_shares"]["Major"],"players":people}


def refresh(folder=None, model="4.2"):
    """Verify a new archive before replacing a previously usable local input."""
    folder = Path(folder) if folder else ROOT/DEFAULT_INPUT
    spec,_,_ = settings()
    require(date.today().isoformat() >= spec["end"], f"赛事计划于 {spec['end']} 结束，当前可用 build 查看快照")
    with TemporaryDirectory(dir=folder) as tmp:
        work = Path(tmp)
        for name in ("event.json","ratings.csv","maps_patch.csv","aggregate.json","published.json","vps.json"):
            if (folder/name).is_file():
                shutil.copyfile(folder/name,work/name)
        url = "https://www.kaggle.com/api/v1/datasets/download/ektarr/counter-strike-pro-matches"
        try:
            import requests
        except ImportError as exc:
            raise ValueError("在线取数需要 requests，也可将下载好的 results.zip 放入数据包后运行 build") from exc
        with requests.get(url,stream=True,timeout=(12,45)) as response, (work/"results.zip").open("wb") as stream:
            response.raise_for_status()
            for chunk in response.iter_content(1024*1024):
                stream.write(chunk)
        result = calculate(work,model=model)
        os.replace(work/"results.zip",folder/"results.zip")
        return result


def compare(a,b,sign):
    if b is None:
        return "榜首" if sign == -1 else "已到合格榜末"
    if a["score"] == b["score"]:
        return f"{b['name']}（同分，按选手 ID 决定顺位）"
    diffs = {k:sign*(a["contributions"][k]-v) for k,v in b["contributions"].items()}
    positive = sorted((k for k in diffs if diffs[k]>1e-9),key=diffs.get,reverse=True)
    why = "、".join(f"{LABEL[k]} {diffs[k]:.2f}" for k in positive[:3]) or "分差小于显示精度"
    return f"{b['name']}（总分差 {abs(a['score']-b['score']):.3f}；{why}）"


def render(result):
    people = [p for p in result["players"] if p["eligible"]]
    cutoff = result["cutoff"]
    version=result["version"].replace("-"," ")
    lines = [f"# {version} · {STATES[result['state']]}","",
             f"数据截至 {cutoff}。纳入 {len(result['scope'])} 项赛事，{len(people)} 人达到排名门槛。两届 Major 共用 E、K 分档中的 30%。",
             "",f"年度汇总 H：{result['adjustments']['H']}。公开阶段表 R：{result['adjustments']['R']}。",
             "","|排名|选手|分数|较 11 月 17 日|Major 实际地图（按站）|","|---:|---|---:|---:|---|"]
    for i,p in enumerate(people,1):
        events = {e["event"]:e for e in p["events"]}
        delta = p["snapshot_rank"]-i if p["snapshot_rank"] else None
        maps = " / ".join(str(events[e]["maps"]) if e in events else "未出场" for e in result["majors"])
        lines.append(f"|{i}|{p['name']}|{p['score']:.3f}|{delta:+d}|{maps}|" if delta is not None else
                     f"|{i}|{p['name']}|{p['score']:.3f}|新入榜|{maps}|")
    lines += ["","Major 列依次为 " + "、".join(result["majors"]) + "。名次变化的正号表示上升。",
              "","## 入围线与榜外档位",""]
    for start,end in ((20,21),(30,31),(31,50),(51,60),(61,70)):
        group = people[start-1:end]
        if group:
            lines.append(f"- 第 {start}–{start+len(group)-1} 名：" + "、".join(p["name"] for p in group))
    if "confirmed_vps" in result:
        reference_version = "4.3" if result["version"] == "HTPM-4.4" else "4.2"
        lines += ["",f"逐站核实的官方 VP 共 {result['confirmed_vps']} 人次。未点名的表现保留数据估计。名次变化以 {reference_version} 的 11 月 17 日快照为基准。"]
    if "maps" in result:
        lines += ["",f"新加坡实收 {result['series']} 场系列赛、{result['maps']} 张地图、{result['participants']} 名选手。"]
    lines += [
              "","## Top 30 逐人理由",""]
    for i,p in enumerate(people[:30]):
        best = max(p["events"],key=lambda e:e["peak"])
        vp_info=(f"另有 {sum(a['kind']=='VP' for a in p['awards'])} 站已核实官方 VP。" if "confirmed_vps" in result else "")
        lines += [f"### {i+1}. {p['name']} · {p['score']:.3f}","",
                  f"全年 {p['details']['main']['maps']} 张主赛事地图，{p['details']['elite_playoff']['maps']} 张高档淘汰赛地图。"
                  f"获得 {sum(a['kind']=='MVP' for a in p['awards'])} 次 MVP、{sum(a['kind']=='EVP' for a in p['awards'])} 次 EVP。{vp_info}"
                  f"最高峰来自 {best['event']}（{best['peak_class']}，峰值指数 {best['peak']:.1f}）。",""]
        for name in result["majors"]:
            event = next((e for e in p["events"] if e["event"]==name),None)
            if event:
                rating = "缺少整站实测 Rating" if event["event_rating"] is None else f"整站 Rating {event['event_rating']:.2f}"
                award = next((a for a in p["awards"] if a["event"]==name),None)
                pending = result["state"]=="provisional" and name==result["majors"][-1]
                honor = ("荣誉待公布" if pending else "未获 MVP/EVP") if not award else award["kind"]
                if award and award["position"]:
                    honor += f" 第 {award['position']} 顺位"
                lines.append(f"- {name}：{event['maps']} 图，淘汰赛 {event['playoff_maps']} 图，{rating}；"
                             f"{honor}，{event['peak_class']}（峰值指数 {event['peak']:.1f}）。")
            else:
                lines.append(f"- {name}：无主赛出场记录。")
        lines += ["- 高于下一位：" + compare(p,people[i+1] if i+1<len(people) else None,1),
                  "- 低于上一位：" + compare(p,people[i-1] if i else None,-1),""]
    if result["version"] == "HTPM-4.4" and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)+"\n"


def atomic_text(path, content):
    path.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,delete=False) as stream:
        tmp = Path(stream.name)
        try:
            stream.write(content)
        except BaseException:
            stream.close()
            tmp.unlink()
            raise
    try:
        os.replace(tmp,path)
    finally:
        tmp.unlink(missing_ok=True)


def publish(result, verify=False, dest=None):
    # Reports are immutable by content. Switch the reader entry point only after both files exist.
    if result["version"] == "HTPM-4.4" and dest is None:
        dest = ROOT/"output/forecast_4_4"
    dest=dest or (ROOT/"output/forecast_4_3" if result["version"]=="HTPM-4.3" else DEST)
    report = render(result)
    artifacts=[result,report]
    if "event_weights" in result:
        from .forecast_4_3 import weight_table
        pending=settings()[0]["event"] if result["state"]=="snapshot" else None
        event_report=weight_table(result["event_weights"],pending)
        artifacts.append(event_report)
    digest = fingerprint(artifacts)
    folder = dest/result["state"]/digest[:16]
    payload = json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(",",":"))+"\n"
    latest = f"# {result['version'].replace('-',' ')} · {STATES[result['state']]}\n\n截至 {result['cutoff']} · [详细榜单]({folder.relative_to(dest).as_posix()}/ranking.md) · [完整分数]({folder.relative_to(dest).as_posix()}/scores.json)\n"
    files = [(folder/"ranking.md",report),(folder/"scores.json",payload),(dest/"latest.md",latest)]
    if "event_weights" in result:
        files.insert(2,(folder/"events.md",event_report))
        files[-1]=(dest/"latest.md",latest+f"\n[逐站赛事权重]({folder.relative_to(dest).as_posix()}/events.md)\n")
    for path,value in files:
        if verify:
            require(path.is_file() and path.read_text(encoding="utf-8")==value, f"与复算结果不符 {path}")
        else:
            atomic_text(path,value)
    return folder/"ranking.md"


def replay():
    from analysis.replay_aggregate_2025 import run, score_inputs
    spec,c,w = settings()
    inputs = season_inputs(2025)
    require(sum(e["tier"]=="Major" for e in inputs[0].values()) == 2, "2025 双 Major 档案不全")
    labels = {**load("data/reference/official_top20_2025.json")["ranks"],**load("data/2025/boundary_ranks.json")["ranks"]}
    rows = features(inputs,load("config/model.json"),c,2025)
    ids = ranked(rows,w,c["feature_order"])
    core = metrics(ids,labels)
    checks, combined = {}, {}
    orders = []
    for n in (1,2):
        targets = {"target_events":n,"target_maps":n*spec["major_target_maps_per_event"]}
        report = run(major_targets=targets,write=False)
        scope = report["scopes"]["shared_4_x"]
        checks[str(n)] = {k:scope["metrics"][k] for k in ("top20_hits","top10_hits","mae_top20_ranked","comparable_pairs","ordered_pairs_top30")}
        orders.append({p["id"]:p["rank"] for p in scope["scores"] if p["rank"]})
        raw,params,_,_ = score_inputs(targets)
        old = {p["id"]:p for p in score(raw,params)["players"]}
        predicted,_ = predict(rows,w,c,old,{},article=False)
        combined[str(n)] = metrics([p["id"] for p in predicted if p["eligible"]],labels)
    archive = load("data/2025/aggregate_replay_3_5.json")["eligibility_audit"]["events"]
    result = {"year":2025,"core":core,"H_reference_only":checks,"core_plus_H":combined,
              "major_map_coverage":{e["official_event"]:[archive[e["official_event"]][k] for k in ("archived_maps","reported_maps")]
                                    for e in inputs[0].values() if e["tier"]=="Major"},
              "H_rank_changes":{p:[rank,orders[1][p]] for p,rank in orders[0].items() if rank!=orders[1][p]}}
    atomic_text(DEST/"replay_2025.json",json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    return result
