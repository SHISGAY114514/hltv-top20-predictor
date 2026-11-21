# HTPM 4.4.3 · 沃斯堡六进四

2026 年 11 月 17 日冻结快照覆盖 23 站、177 人。BLAST Rivals 沃斯堡站为八队赛。按 HLTV 编辑用于评奖的统计口径，六进四决定第 5–6 名，季后赛 Rating 从半决赛起算。[HLTV 编辑说明](https://www.hltv.org/news/43219/the-evps-and-all-stars-of-blast-rivals-2025-s2) · [沃斯堡赛程](https://www.hltv.org/news/44494/blast-rivals-fort-worth-playoff-bracket-set)

GamerLegion–Astralis 对应 HLTV 比赛 2393347。冻结档案有两张图，编号 153567、153575。4.4.3 在两队共十名选手的逐图记录上应用已有的六进四分类，两图仍属于整站、场馆及适用的对手样本。GamerLegion 五人在本站的实收季后赛样本从每人 4 图降到 2 图，Astralis 五人从 2 图降到 0 图。另一场六进四 G2–FaZe 缺少逐图记录，沿用固定输入，贡献 0 张季后赛地图。[比赛页](https://www.hltv.org/matches/2393347/gamerlegion-vs-astralis-blast-rivals-2026-season-1) · [G2–FaZe](https://www.hltv.org/matches/2393346/g2-vs-faze-blast-rivals-2026-season-1) · [分类规则](../config/season_4_4_3.json)

4.4.2 快照 `463b1b66c3749110` 与 4.4.3 快照 `36985ce4e8239e62` 使用相同的比赛输入、权重与资格门槛。10 人总分变化，5 人名次变化。hypex 从第 67 升至第 65，syph0、Twistzz 各退一位；s1ren 升至第 70，Ryu 退至第 71。前 30 名顺序相同，其中 PR 的分数从 41.142 降至 41.091。分项根据重新分类的样本计算，移出某轮比赛后，个人总分可升可降。[177 人名次、总分与分项对照](../output/comparison_4_4_3/comparison.csv) · [完整榜单及前 30 名理由](../output/forecast_4_4_3/latest.md) · [排名长图](../output/model_cards/HTPM-4.4.3-ranking.png)

```powershell
$env:PYTHONHASHSEED='0'
$env:PYTHONUTF8='1'
python -B -m analysis.compare_4_4_2 --model 4.4.3
python -B -m htpm validate --model 4.4.3
python -B -m analysis.render_ranking_4_4_2 --model 4.4.3
python -B -m unittest discover -s tests
```
