# 2025年第10–20名：样本量、赛程难度与入选理由

这些内容摘述自HLTV各选手文章的排名解释段落，非逐字引文。用途是检查3.5 汇总模型的设计方向，不是用11个名次拟合权重。完整结构化摘述见 `data/reference/2025_top10_20_rationale.json`；[官方最终榜单](https://www.hltv.org/news/43492/top-20-players-of-2025-final-list)提供整体背景。

## 逐人依据

| 2025名次、官方来源 | 入选或排序支撑 | 限制更高排名的因素 | 对模型的启示 |
|---|---|---|---|
| [10 Spinx](https://www.hltv.org/news/43547/top-20-players-of-2025-spinx-10) | 14项赛事均至少VP水平；10项强表现、4EVP，较难赛程中稳定 | Top5 1.09；季后赛1.05，关键阶段下滑 | 区分跨多项赛事持续贡献和少数峰值 |
| [11 Twistzz](https://www.hltv.org/news/43533/top-20-players-of-2025-twistzz-11) | 全年1.17；Top5/10均1.15；季后赛1.22 | 季后赛仅26图，为该届Top20最少；高端赛事深度不足 | 高Rating应受其实际样本量约束 |
| [12 mezii](https://www.hltv.org/news/43534/top-20-players-of-2025-mezii-12) | 两届Major决赛合计1.33；全年决赛42图；3EVP、12VP、16项赛事 | Top5 0.99、Top10 1.05；总体关键赛表现弱于Major决赛峰值 | 团队成绩须联系个人表现，经历数量不能抹去个人弱项 |
| [13 Senzu](https://www.hltv.org/news/43528/top-20-players-of-2025-senzu-13) | 4EVP，包括Austin Major决赛之路的1.30；缺席年末Major仍入选 | Top5 1.03；Elite EVP仅1项；关键阶段一般 | 不以打满全年为硬前提，保留高质量短赛季入榜可能 |
| [14 XANTARES](https://www.hltv.org/news/43524/top-20-players-of-2025-xantares-14) | 全年1.16；1MVP、3EVP，多次接近EVP | 主要高峰来自Medium PGL Masters；Big matches 1.05、Arena 0.99；Elite+表现与覆盖不足 | 低等级高Rating和总图数不能代替最高水平验证 |
| [15 YEKINDAR](https://www.hltv.org/news/43518/top-20-players-of-2025-yekindar-15) | 三项夺冠赛事EVP；决赛17图1.17；Top5 43图1.13 | 晚加入与磨合导致强赛事表现总量不足 | 同时看经历数量、对手质量与关键贡献 |
| [16 xertioN](https://www.hltv.org/news/43512/top-20-players-of-2025-xertion-16) | 3EVP及6项强VP，九项较好赛事表现 | Top5、季后赛均1.02；决赛0.89 | 多项稳定表现有价值，但不能用数量掩盖关键阶段弱势 |
| [17 torzsi](https://www.hltv.org/news/43509/top-20-players-of-2025-torzsi-17) | 4EVP均伴随决赛；63%的比赛对Top10；40%的地图在Elite、38%在季后赛 | 全年1.07、Top5 1.00、季后赛1.02；Major 0.96、决赛0.90 | 同样Rating应结合赛程难度解释；比赛比例与地图比例不能混用 |
| [18 NiKo](https://www.hltv.org/news/43505/top-20-players-of-2025-niko-18) | 1MVP、2EVP；全年1.13；Top5 1.06、Top10 1.08 | 荣誉来自Big档较低端；Elite季后赛仅4图、0.96；决赛24图、0.98 | 年度总量不能掩盖高等级关键阶段缺少验证 |
| [19 iM](https://www.hltv.org/news/43503/top-20-players-of-2025-im-19) | 最高级赛事平均1.16；2EVP；Top5 1.11、Top10 1.10 | 季后赛38图1.05、Arena20图1.02，四项赛事低于1.00 | 样本数量与表现质量需同时展示，缺失关键赛不能默认为平均 |
| [20 b1t](https://www.hltv.org/news/43502/top-20-players-of-2025-b1t-20) | Katowice、Cologne两个高等级峰值和Bounty EVP；淘汰风险比赛1.14 | Major 1.00、Top5 1.02；季后赛1.06、Arena1.05；四项明显低谷 | 榜尾不能只数奖项，须检查等级、下限及关键表现 |

## 3.5 的落实与边界

E分档计算可靠性，O按Top N分别收缩，N衡量覆盖与困难赛程。单次高峰不能自动替代跨赛事验证，年度低等级图数也不替代Elite以上覆盖。已有奖项不因为全年样本少再打折；Bounty S1折扣是另行指定的赛事荣誉规则。

全池关键阶段统计仍缺失，不将团队名次冒充决赛表现。上述官方评语只约束设计方向，不能拟合精确数值或证明准确率。具体规则见[3.5 模型](MODEL_AGGREGATE.md)，事实边界见[来源审计](SOURCE_AUDIT.md)。
