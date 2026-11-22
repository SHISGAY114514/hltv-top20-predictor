# HTPM 4.4.3 · 2026 年度选手预测

**截至 2026-11-17，301 名参赛者中有 177 人取得排名资格。** 本版使用新加坡 Major 赛前已赛的 23 站。正式 MVP/EVP 得主只要有实收赛事记录即可入榜，其他选手须至少两站合计 20 图。前 30 名附相邻顺位理由。[177 人全榜](../output/forecast_4_4_3/snapshot/36985ce4e8239e62/ranking.md) · [排名长图](../output/model_cards/HTPM-4.4.3-ranking.png) · [逐人逐项得分](../output/forecast_4_4_3/snapshot/36985ce4e8239e62/scores.json) · [23 站系数](../output/forecast_4_4_3/snapshot/36985ce4e8239e62/events.md)

## 评分与数据范围

核心分按百分制计算。个人荣誉占 31%，分档整站表现 23%，对强队表现 13%，关键阶段 14%，赛事峰值 11%，稳定性和样本覆盖各 4%。团队名次的直接贡献为零。核心分加同日年度汇总校正 H 得到最终分数，H 上限为 ±2.5 分。社区阶段表用于敏感性比较，正式榜 R 为零。这些份额来自 HTPM 参数。各分项怎样取样、收缩，以及它们实际怎样影响前 20 名，见[与 3.5 的详细对照](COMPARE_3_5_4_4_3.md)。

赛事强度参考收录赛段开赛前的 VRS 和实际参赛阵容。对手强度按每图赛前的月度 VRS，分别评价第 1–5 与第 6–10 名。季后赛和场馆按实际收到的地图计数；整站 Rating 的补充只用于覆盖范围相符的整站表现。鹿特丹、香港和沃斯堡各有比赛或颁奖文章可追溯。[逐站计算方法](MODEL_4_3.md) · [赛段与 VRS 分组](MODEL_4_4.md) · [整站补充及社区表处理](MODEL_4_4_1.md) · [鹿特丹峰值规则](MODEL_4_4_2.md)

## 相对 4.4.2 的修正 · 沃斯堡六进四

2026 年 11 月 17 日冻结快照覆盖 23 站、177 人。BLAST Rivals 沃斯堡站为八队赛。按 HLTV 编辑用于评奖的统计口径，六进四决定第 5–6 名，季后赛 Rating 从半决赛起算。[HLTV 编辑说明](https://www.hltv.org/news/43219/the-evps-and-all-stars-of-blast-rivals-2025-s2) · [沃斯堡赛程](https://www.hltv.org/news/44494/blast-rivals-fort-worth-playoff-bracket-set)

GamerLegion–Astralis 对应 HLTV 比赛 2393347。冻结档案有两张图，编号 153567、153575。4.4.3 在两队共十名选手的逐图记录上应用已有的六进四分类，两图仍属于整站、场馆及适用的对手样本。GamerLegion 五人在本站的实收季后赛样本从每人 4 图降到 2 图，Astralis 五人从 2 图降到 0 图。另一场六进四 G2–FaZe 缺少逐图记录，沿用固定输入，贡献 0 张季后赛地图。[比赛页](https://www.hltv.org/matches/2393347/gamerlegion-vs-astralis-blast-rivals-2026-season-1) · [G2–FaZe](https://www.hltv.org/matches/2393346/g2-vs-faze-blast-rivals-2026-season-1) · [分类规则](../config/season_4_4_3.json)

4.4.2 快照 `463b1b66c3749110` 与 4.4.3 快照 `36985ce4e8239e62` 使用相同的比赛输入、权重与资格门槛。10 人总分变化，5 人名次变化。hypex 从第 67 升至第 65，syph0、Twistzz 各退一位；s1ren 升至第 70，Ryu 退至第 71。前 30 名顺序相同，其中 PR 的分数从 41.142 降至 41.091。分项根据重新分类的样本计算，移出某轮比赛后，个人总分可升可降。[177 人名次、总分与分项对照](../output/comparison_4_4_3/comparison.csv) · [完整榜单及前 30 名理由](../output/forecast_4_4_3/latest.md) · [排名长图](../output/model_cards/HTPM-4.4.3-ranking.png)

## 离线核验

在本发布分支的仓库根目录运行。`validate` 使用冻结输入核对快照，另外三条命令分别用于生成与 4.4.2 的对照、绘图和测试。

```powershell
$env:PYTHONHASHSEED='0'
$env:PYTHONUTF8='1'
python -B -m analysis.compare_4_4_2 --model 4.4.3
python -B -m htpm validate --model 4.4.3
python -B -m analysis.render_ranking_4_4_2 --model 4.4.3
python -B -m unittest discover -s tests
```
