from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageFont, ImageDraw
import os,json
root=Path(__file__).resolve().parents[1]
load=lambda p:json.loads((root/p).read_text(encoding="utf-8"))
cfg=load("config/model.json")
c4=load("config/season_model.json")
score4=load("output/forecast_4_1_1/scores.json")
score3=load("output/replay_3_5_2025/scores.json")
out=root/"output"/"model_cards"
out.mkdir(exist_ok=True)
S=2
W,H=1220,1500
fonts={'t':'msyh.ttc','b':'msyhbd.ttc','n':'bahnschrift.ttf','nb':'segoeuib.ttf'}
@lru_cache(None)
def font(k,size):
    return ImageFont.truetype(str(Path(os.environ['WINDIR'])/'Fonts'/fonts[k]),size*S)
def render(v):
    is3=v=='3.5'
    ink='#162f3b'; navy='#102b39'; muted='#405d68'; light='#d0dedc'; paper='#f6f7f2'; white='#ffffff'
    tint,accent,pale=('#91e7d4','#097568','#e3f3ee') if is3 else ('#ffc18e','#a64b1d','#fff0e1')
    im=Image.new('RGB',(W*S,H*S),paper); d=ImageDraw.Draw(im)
    def box(x,y,w,h,fill):
        d.rectangle((x*S,y*S,(x+w)*S-1,(y+h)*S-1),fill)
    def line(x1,y1,x2,y2,color=light,width=1):
        d.line((x1*S,y1*S,x2*S,y2*S),fill=color,width=round(width*S))
    def tx(x,y,s,size=21,color=ink,k='t',align='left',width=None):
        f=font(k,size)
        length=d.textlength(s,font=f)/S
        if width is not None: assert length<=width, (v,s,round(length),width)
        x=x-length if align=='right' else x-length/2 if align=='center' else x
        assert x>=0 and x+length<=W+1 and y+size<H+1,(s,x,length)
        d.text((round(x*S),round(y*S)),s,font=f,fill=color,anchor='lt',stroke_width=0)
    box(0,0,W,219,navy);box(0,0,12,219,tint)
    tx(49,32,'HLTV 年度 TOP 20 预测模型',22,tint,'b')
    tx(1170,33,'原稿采用版本' if is3 else '工作区默认版本',19,'#def0ea','t','right')
    tx(45,73,'HTPM  '+v,68,white,'nb')
    tx(49,165,'用赛事荣誉、整站 Rating 和全年强敌表现排序' if is3 else '把赛事阶段、关键赛和争夺 MVP 的高峰纳入排序',29,white,'b')
    # Input and eligibility use identical coordinates on both cards.
    box(0,219,W,153,pale)
    tx(49,248,'数据输入',21,accent,'b');tx(205,246,'HLTV 年度与逐站 Rating 3.0、累计对 Top N 的表现、赛事名次与 MVP / EVP。' if is3 else '逐图击杀、死亡、ADR、KAST，结合可核实的系列赛 Rating 3.0、赛制阶段与荣誉。',22,ink,width=971)
    line(49,285,1170,285,'#c4d5ce')
    tx(49,309,'排名资格',21,accent,'b')
    tx(205,305,'主赛事 ≥50 图，且精英及以上 ≥20 图，且对 Top 10 ≥10 图。' if is3 else '获得正式 MVP / EVP，或参加至少 2 站且主赛事合计 ≥20 图。',24,ink,'b',width=970)
    tx(205,342,'候选来自赛事获奖者和观察名单。' if is3 else '覆盖所有有主赛事逐图记录的选手，再判断排名资格。',18,muted)
    # Paired panels
    tx(49,408,'总分由什么组成',31,ink,'b');tx(1170,414,'模块权重合计 100%',21,muted,'t','right')
    box(49,461,552,401,white);box(619,461,551,401,white)
    tx(69,482,'六项固定权重' if is3 else '八项核心权重',23,accent,'b')
    tx(579,487,'占总分' if is3 else '占核心分',17,muted,'t','right')
    mods=[('A','个人荣誉'),('E','分档整站 Rating'),('O','全年强敌表现'),('N','样本质量'),('T','团队成绩'),('C','跨赛事稳定性')] if is3 else [('A','赛事履历'),('E','分档整站表现'),('O','强敌表现'),('K','关键赛'),('P','赛事高峰'),('C','稳定性'),('N','样本覆盖'),('T','团队深轮次')]
    weights=cfg['weights'] if is3 else dict(zip(c4['feature_order'],c4['profiles'][score4['profile']]))
    for i,(code,name) in enumerate(mods):
        row=534+i*(50 if is3 else 39)
        value=round(weights[code]*100) if is3 else weights[code]
        tx(70,row+2,code,20,accent,'nb');tx(108,row,name,20,ink,width=180)
        box(309,row+8,178,7,'#e4ece8')
        box(309,row+8,round(178*value/30),7,accent)
        tx(578,row-1,str(value)+'%',22,ink,'nb','right')
    tx(641,482,'赛事档次如何影响得分',23,accent,'b')
    tx(641,532,'档次',18,muted,'b')
    for x,t in ([(879,'整站份额'),(997,'MVP 分'),(1143,'第一 EVP 分')] if is3 else [(952,'整站 / 阶段份额'),(1143,'履历 / 高峰修正')]):
        tx(x,532,t,17,muted,'b','right')
    tiers=['Major','Super-elite','Elite','Big','Medium']
    for i,(key,label) in enumerate(zip(tiers,['Major','超级精英','精英','大型','中型'])):
        row=571+42*i
        line(641,row-8,1146,row-8)
        tx(641,row,label,20,ink,'b' if i==0 else 't')
        if is3:
            tx(879,row,str(round(cfg['tier_samples'][key]['weight']*100))+'%',21,accent,'nb','right')
            tx(997,row,str(cfg['tiers'][key]['MVP']),21,ink,'n','right')
            tx(1143,row,str(cfg['tiers'][key]['EVP1']),21,ink,'n','right')
        else:
            tx(952,row,str(round(c4['tier_shares'][key]*100))+'%',21,accent,'nb','right')
            tx(1143,row,'×'+format(c4['tier_resume_factors'][key],'.2f'),21,ink,'n','right')
    tx(641,788,'份额在 E 模块内分配。奖项分累积后折算为 A。' if is3 else '份额用于整站和分档阶段。修正乘在原等级系数上。',17,muted,width=512)
    tx(641,820,'单站最多计 16 图，少样本 Rating 向 1.05 收缩。' if is3 else '同一档内还会按实际参赛阵容强度调整。',17,muted,width=510)
    tx(49,901,'影响名次的关键规则',31,ink,'b')
    details=[
      ('荣誉顺位','MVP、第一 EVP 和第二 EVP 各有档次分。第三 EVP 起每后移一位减 5%，最低取基准分的 75%。','2026 年 Bounty S1 的个人荣誉和团队名次奖励均乘 0.60。'),
      ('强敌与样本','全年对 Top 5 / 10 / 20 / 30 的 Rating 在 O 内分别占 40% / 30% / 20% / 10%。','各组按图数收缩。N 单独衡量覆盖量与赛程难度，两者占 N 的 70% 和 30%。'),
      ('成绩与稳定性','团队名次按赛事档次、个人 Rating 和参赛图数折算。','稳定性看整站 Rating 达到 1.00 和 0.90 的比例，两项分别占 C 的 70% 和 30%。')
    ] if is3 else [
      ('分档关键赛','K 的一半来自分档阶段，每档按小组 40%、淘汰 60% 合成。','另一半考察关键赛中的发挥，结合高档淘汰赛、决赛、强敌与场馆表现。'),
      ('履历与高峰','至少打 5 图的无奖选手也可获履历加减分。高峰分取最佳三站（65%）和高档最佳一站（35%）。','最佳三站按 55% / 30% / 15% 合成。与同站 MVP 的差距及官方评语用于判断争奖程度。'),
      ('预测分校正','2026 预测在核心分上叠加校正。3.5 对照项按差值的 20% 计入，封顶 ±2.5 分。','社区公布的整站、淘汰赛、场馆及决赛数据另校正最多 ±2 分。2025 回测检验核心分。')
    ]
    for i,(head,s1,s2) in enumerate(details):
        y=960+i*81;line(49,y-11,1170,y-11)
        tx(49,y+3,head,22,accent,'b')
        tx(231,y+1,s1,19,ink,width=939);tx(231,y+32,s2,19,muted,width=939)
    box(0,1224,W,276,navy)
    tx(49,1252,'2025 年榜回测',29,white,'b');tx(1170,1259,'同一候选池 · 151 人',20,'#d3e1e2','t','right')
    met=score3['scopes']['shared_4_x']['metrics'] if is3 else score4['replay']['metrics']
    exact=met['exact_top20'] if is3 else sum(p['actual']==p['predicted'] for p in score4['replay']['players'].values() if p['actual']<=20)
    vals=[(str(met['top20_hits'])+'/20','TOP20 入选命中'),(str(met['top10_hits'])+'/10','TOP10 入选命中'),(str(exact)+'/20','TOP20 名次全对'),(format(met['mae_top20_ranked' if is3 else 'mae_top20'],'.2f'),'平均名次误差（名）')]
    for j,(val,desc) in enumerate(vals):
        x=49+j*287
        if j:line(x-21,1311,x-21,1394,'#47616a')
        tx(x,1307,val,48,tint,'nb');tx(x+1,1371,desc,21,white,'t')
    line(49,1419,1170,1419,'#47616a')
    tx(49,1444,'固定公式按选手分五折，合并排序一致。' if is3 else '54 组候选参数按 2025 年榜择优。同年按选手分五折，TOP20 命中 18/20，平均误差 3.40 名。',18,'#d8e9e9',width=1120)
    file=out/('HTPM-'+v+'.png');im.save(file,dpi=(180,180),optimize=True)
    print(file,Image.open(file).size)
for v in ('3.5','4.1.1'):render(v)
