# HTPM 4.4 · 2026-11-17 固定快照

23 项主赛事已结束，其中只有科隆 Major。逐图档案有 301 名出场选手，4.3 和 4.4 各有相同的 177 人达到资格门槛。比较以 4.3 入围者的小写选手 ID 为键。新加坡尚未开赛。4.4 显式选择，默认的 4.3 入口继续支持赛后导入。[全榜](../output/forecast_4_4/latest.md) · [两版中文分析](../output/comparison_4_4/分析.md) · [177 人对照 CSV](../output/comparison_4_4/comparison.csv)

## 七张地图的两种记录

|对局与公开比赛页|内部系列赛 / 地图 ID|原始标签|4.4 的赛段归属|
|---|---|---|---|
|[克拉科夫 Spirit–MOUZ](https://www.hltv.org/matches/2389665/spirit-vs-mouz-iem-krakw-2026)|6258176 / 125292、125294|playoff|季军赛，单列 placement|
|[香港 Vitality–MOUZ](https://www.hltv.org/matches/2400204/vitality-vs-mouz-blast-rivals-2026-season-2)|7313139 / 156054、156055|playoff|八强赛制下的四分之一决赛，单列 quarterfinal|
|[香港 G2–Falcons](https://www.hltv.org/matches/2400205/g2-vs-falcons-blast-rivals-2026-season-2)|7313138 / 156056、156057、156058|playoff|同上|

克拉科夫 EVP 文用 sh1ro 作例，指出对 MOUZ 的季军赛提高了他的整站 Rating，但 HLTV 将这场排除在季后赛统计之外。香港 EVP 文在解释 ropz 时说明，八队赛事的四分之一决赛尚未决定上半区名次，其 playoff 筛选排除该轮。模型只对表内已核对的比赛使用例外。香港仍有真实的淘汰赛对阵和最终名次，模型将这五图单列，未转入小组样本。其他场次沿用归档与 4.3 的赛制规则，其统计范围仍受原档案证据限制。[克拉科夫颁奖说明](https://www.hltv.org/news/43853/the-evps-and-all-stars-of-iem-krakow-2026) · [香港颁奖说明](https://www.hltv.org/news/45998/the-evps-and-all-stars-of-blast-rivals-2026-season-2) · [逐场例外](../config/season_4_4.json)

七张图均保留原始技术统计、胜负、队伍、原标签和场馆归属，每张图两队共十条选手记录。E 使用整站数据。K 的季后赛及其高档、强敌子样本按修正标签重算，场馆分量继续使用这些图。A 的荣誉质量和无奖调整、P 的争奖质量与高峰、N 的高档季后赛覆盖随适用条件重算。全池减少 70 个季后赛选手地图，其中高档减少 20 个；E、C、T 和既有外部 R 表的逐人贡献均通过相等性核验。H 根据新的核心分重新对齐。赛事名次与官方奖项单独留档。[逐人赛段与贡献](../output/forecast_4_4/latest.md) · [原始档案与署名](../DATA-LICENSE.md)

## 对手排名与覆盖

O 读取每图赛前最近一期月度全球 VRS 前十，按实战对手与归档阵容至少三人重合匹配。2026 档案只给出匹配到的前十名次或空值。空值保留为未知，明确记录的十名以外另计。4.4 将 1–5 和 6–10 两组分别向中性指数 50 收缩，再合成 O。4.3 的两个系数为 0.55、0.45，先验图数为 30、25，第二组原来包含整个前十。4.4 沿用这些数值，把第二项的样本限定到 6–10，每张图只进入 O 的一个分组。该分组变化属于模型设定。地图指数由技术统计计算，单位与 HLTV Rating 3.0 不同。[原采集逻辑](../analysis/collect_season_maps.py) · [月度 VRS](../data/reference/vrs_top10_monthly.json) · [4.4 参数](../config/season_4_4.json)

177 人有 12,894 个选手地图，其中 3,490 个匹配前五，2,927 个匹配第六至十，6,477 个未匹配，可解析率 49.8%。该输入中明确记录前十以外的数量为零。N 仍按匹配到的前十地图衡量覆盖，K 的强敌季后赛分量也使用前十并集。单项压力测试把未匹配全部假设为 6–10，重算 O、K、N 及 H，用于量化缺口。另列有公开年度统计的 56 人，其 HLTV Top 5/10/20/30 属全年累计筛选，和 23 站逐图代理的赛事、对手及样本范围均可不同。其余 121 人的公开年度表位置为 null。沿用的 H 汇总本身含累计对手统计，移除 H 的情景检验这部分重叠的整体影响。[逐人覆盖与压力测试](../output/comparison_4_4/comparison.csv) · [固定日期的 HLTV 累计表](../output/comparison_4_4/hltv_opponents.json)

## 第 4–7 名怎样读

|选手|MVP / EVP|高档季后赛图 / 其中 Major 图|23 站 VRS 前五图|HLTV 年度 Top 5 图 / Rating|H / R 总分贡献|
|---|---:|---:|---:|---:|---:|
|ropz|1 / 6|28 / 3|47|57 / 1.17|+0.026 / +0.167|
|flameZ|0 / 5|28 / 3|47|57 / 1.15|−0.247 / +0.188|
|KSCERATO|2 / 4|26 / 8|63|51 / 1.13|+0.168 / −0.561|
|sh1ro|0 / 5|29 / 6|39|54 / 1.14|−1.053 / +0.460|

ropz 与 flameZ 的两组地图数相同。ropz 的 K、O 分别高约 0.81、0.65 个总分点，flameZ 的 A、P 分别高约 0.67、0.58。中间一对只差 0.0105 分，单独移除 R 或恢复 4.3 的赛段归属，KSCERATO 都会超过 flameZ。sh1ro 的科隆 Major 季后赛有六图，年度 R 给他正调整，但 H 扣约 1.05 分。移除 H 时他升至第四。八个情景的 Top 20 成员一致，这四人的内部次序对口径敏感。此处所有数据均取自 11 月 17 日快照。[实跑与消融](../output/comparison_4_4/分析.md) · [逐人分数](../output/forecast_4_4/latest.md)

以 4.3 为共同起点，只改赛段时 sh1ro 的总分变动为 −0.2764，只改对手档时为 −0.0343。KSCERATO 对应为 −0.0172 和 +0.1754。两项改动均会通过核心分影响 H 的对齐，所以未直接参加例外场次的人也可能有微小变动。CSV 的 `stage_only_delta` 与 `opponent_only_delta` 记录这两次独立重算，`joint_interaction` 是两者合用后的交互余量，三列之和等于该选手的总分差。[177 人逐项归因](../output/comparison_4_4/comparison.csv)

## 荣誉、Rating 和赛事分级的依据

HLTV 的 2025 年度方法提到重要赛事、压力、对手质量、样本规模与荣誉的层次，文章未给出能确定年度分数的固定系数。公开节目可说明编辑如何讨论 MVP。模型沿用 4.3 的 A/E/O/K/P/T/C/N 权重 31/23/13/14/11/0/4/4 和五档份额 30/27/23/16/4。五档均分仅用于消融。两个各占 4 的模块是 C 和 N；另有 H、R 校正，上限分别为 2.5、2 个总分点。R 来自冻结的社区公开分组表，缺少逐图成员清单，无法逐场校正其筛选。[HLTV 年度方法](https://www.hltv.org/news/43492/top-20-players-of-2025-final-list) · [公开节目](https://www.hltv.org/news/45709/mvp-haters-come-here-ft-mauisnake-and-striker) · [4.3 参数与校准](MODEL_4_3.md) · [R 的日期与来源](../data/2026/published_stage_ratings.json)

香港官方 MVP 为 KSCERATO。截点的整站 Rating 3.0 为 1.55（10 图）。官方 EVP 顺位依次为 molodoy、donk、ropz、m0NESY，快照 Rating 分别是 1.29、1.29、1.32、1.24。第三顺位的 ropz 有最高 EVP Rating。逐站对照保留颁奖来源、顺位、奖项档案的 Rating、同期整站 Rating 3.0、地图数、名次和统计来源。147 项 MVP/EVP 中，两个 Rating 字段有四项相差 0.01。现有档案不足以判定差异成因，评分仍使用固定的整站输入；档案未给出的更细 Rating 修订号留作未知。[MVP 原文](https://www.hltv.org/news/45996/kscerato-dominates-to-claim-blast-rivals-s2-mvp) · [EVP 原文](https://www.hltv.org/news/45998/the-evps-and-all-stars-of-blast-rivals-2026-season-2) · [同站奖项与 Rating](../output/comparison_4_4/award_rating.csv)

Bounty S1 的文章明确将 Jame 评为 strong VP 级表现。在本快照可定位到一人一站，全年总量未知。普通 VP 的 25%、strong VP 的 40% 均来自 4.3 的模型配置。逐人逐站最多计一个正式荣誉，已有 VP 的站次关闭无奖履历加分。普通提及没有单独的 VP 称谓时不计。逐站移除实验另量化同一站同时影响 A/E/K/P 的频率。现有公开证据不足以确定消除重叠时该扣几分，本版保留分项权重。[Jame 颁奖原文](https://www.hltv.org/news/43729/the-evp-and-all-stars-of-blast-bounty-2026-season-1-finals) · [逐站移除明细](../output/comparison_4_4/event_overlap.csv)

## 离线复算

本次发布分支为 `model/htpm-4.4-verified`。全仓 64 项测试均通过，含 7 项 4.4 回归测试。双版本在另一个输出目录再次完整复算，四个版本文件各两套及六个对照文件，共 14 个文件逐一通过文本一致性校验。关闭赛段例外、恢复嵌套 O 时，301 人的各项贡献和资格排名均与 4.3 重合。

在本分支的仓库根目录运行。发布验证环境为 Windows、CPython 3.9.13（32 位），哈希种子固定为 0，评分没有随机抽样。比较程序先实跑 4.3 并校验存档的四个文件，再实跑 4.4、五种参数或证据变体、三种 H/R 消融和 23 次逐站移除。资格变化单独列于清单。独立重建可给比较程序传入目标目录，两个版本的完整结果都会写入该目录。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONHASHSEED='0'
python -B -m analysis.compare_4_4
python -B -m htpm build --model 4.4
python -B -m htpm validate --model 4.4
python -B -m unittest discover -s tests -v
```

输入清单对 21 个计算或基线展示文件逐项计算 SHA-256，历史展示文件按 LF 规范化。4.3 的四个存档文件为完整分数、榜单、赛事权重和 latest 入口，校验按 UTF-8 文本比较。4.4 构建前校验输入摘要。177 人 CSV 的十个分项均为对总分的贡献，分项差之和可以逐人复核。名次上升为正，固定队列排名、自然资格和越过的选手均单列。各消融都以完整的 4.4 为参照，情景差值不可视为相互独立的贡献再相加。[复算清单及两版快照](../output/comparison_4_4/manifest.json) · [回归测试](../tests/test_forecast_4_4.py)
