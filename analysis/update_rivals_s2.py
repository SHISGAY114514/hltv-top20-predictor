"""Apply the verified Hong Kong award publication without altering match statistics."""
import json
from pathlib import Path
from htpm.core import dump_json, fingerprint, require

ROOT=Path(__file__).resolve().parents[1]
def load(p):
    return json.loads((ROOT/p).read_text(encoding='utf-8'))

def update():
    proof=load('data/reference/rivals_s2_2026_honors.json'); event=proof['event']
    archive=load('data/2026/award_snapshot.json'); orders=load('data/reference/evp_orders_2026.json')
    raw=load('data/2026/aggregate_snapshot.json'); stats={p['id']:p for p in raw['players']}
    baseline_path=ROOT/'output/comparison/hong_kong_before.json'
    if not baseline_path.exists():
        before=load('output/current/scores.json')
        dump_json(baseline_path,{'description':'Before new Rivals S2 EVP publication; existing MVP already included',
            'source_hashes':{'aggregate':fingerprint(raw),'awards':fingerprint(archive),'orders':fingerprint(orders)},
            'players':[{k:p[k] for k in ('id','name','score','rank','contributions')} for p in before['players']]})
    existing=[a for a in archive['awards'] if a['event']==event]
    require({a['player_id'] for a in existing if a['type']=='MVP'}=={proof['mvp']},'现有MVP与官方不符')
    require({a['player_id'] for a in existing if a['type']=='EVP'}<=set(proof['evps']),'现有EVP出现冲突')
    keys={(a['event'],a['player_id']) for a in archive['awards']}
    added=[]
    for i,pid in enumerate(proof['evps'],1):
        require(pid in stats,'新获奖者须纳入候选并补齐统计：'+pid)
        rows=[e for e in stats[pid]['events'] if e['name']==event]
        require(len(rows)==1 and rows[0]['rating']==proof['award_ratings_3_0'][pid],'整站Rating核对不一致')
        if (event,pid) in keys:
            continue
        archive['awards'].append({'player':stats[pid]['name'],'player_id':pid,'event':event,
            'rating':rows[0]['rating'],'type':'EVP','evp_rank':i,'source':proof['source'],
            'order_evidence':proof['source'],'retrieved_on':proof['verified_on']})
        added.append(pid)
    for e in orders['events']:
        e.setdefault('verified_on',orders['verified_on'])
    replacement={k:proof[k] for k in ('event','source','mvp','evps','verified_on')}
    orders['events']=[e for e in orders['events'] if e['event']!=event]+[replacement]
    orders['pending']=[e for e in orders.get('pending',[]) if e!=event]
    orders['verified_on']=proof['verified_on']
    archive['retrieved_on']=proof['verified_on']
    archive['note']='11月15日原档案，11月17日依据官方文章增补香港Rivals S2四项EVP并核实MVP；其他赛事非本次重新采集。全部23项赛事顺位现有来源。'
    dump_json(ROOT/'data/2026/award_snapshot.json',archive)
    dump_json(ROOT/'data/reference/evp_orders_2026.json',orders)
    log_path=ROOT/'data/reference/rivals_s2_2026_update_audit.json'
    if not log_path.exists():
        dump_json(log_path,{'verified_on':proof['verified_on'],'event':event,'source':proof['source'],
            'added_evp_ids':added,'mvp_already_present':proof['mvp'],
            'statistics_modified':False,'aggregate_sha256':fingerprint(raw),
            'all_star_additional_A_points':0,'event_order':['kscerato']+proof['evps']})
    print('Rivals S2: MVP confirmed, %d newly added EVP; %d total awards'%(len(added),len(archive['awards'])))

if __name__=='__main__':
    update()
