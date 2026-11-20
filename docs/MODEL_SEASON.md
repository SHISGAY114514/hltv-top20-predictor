# 逐图来源与候选范围


两季使用同一种逐图数据。按赛事名称和正赛起点筛选 2025 年的 24 项赛事、2026 年的 23 项赛事。2025 年分档取 HLTV 年终标准，2026 年遵守工作区固定分档。每行记录选手、对手、地图、回合数、击杀、死亡、ADR、KAST、输赢、阶段和场地。只使用记分完整且两队各有五人的地图。香港决赛在数据集截止日之后，另外从 HLTV 全图记分板补录三张地图。选手在赛前最近一次 Valve 月度全球榜上以至少三名相同队员匹配对手阵容。此处 VRS Top 10 与 3.5 的 HLTV 累计 Top 10 分开显示。[逐图来源](https://www.kaggle.com/datasets/ektarr/counter-strike-pro-matches) · [香港决赛](https://www.hltv.org/matches/2400208/spirit-vs-furia-blast-rivals-2026-season-2) · [VRS 快照](../data/reference/vrs_top10_monthly.json)

所有在逐图资料中出现的正式获奖者均可参评；其他选手在至少两站合计 20 张完整地图即可进入比较。这是发现候选的低门槛。小样本在赛事表现、对手表现、关键赛、赛事高峰和覆盖分中受到约束。旧模型的 50/20/10 门槛继续用于解释原评分的证据充分度。不同来源对正赛、在线阶段和场馆的定义会造成图数差异。逐图资料还存在缺失的地图，已赛分组数不应解读为 HLTV 年度官方总图数。[赛事与阶段清单](../data/reference/season_stage_catalog.json) · [逐赛事采集审计](../data/reference/stage_collection_audit.json)
