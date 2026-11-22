# HTPM 4.2 · 新加坡 Major 赛后出榜

4.2 默认预测 2026 年 HLTV 年度排名。赛前使用截至 11 月 17 日的 23 站真实数据。赛后把新加坡作为第 24 站并入，重算全体选手。报告包含全榜、Top 20 与 Top 30 入围线、Top 50/60/70 档位、Top 30 的相邻名次解释、两届 Major 逐站履历及相对赛前的升降。完整 JSON 保存每人逐模块贡献、分档分阶段样本、峰值和奖项证据。[4.2 榜单入口](../output/forecast_4_2/latest.md)

## 决赛后怎样用

在工作区根目录执行。只需 Python 3.9 或以上，在线取数另需 requests。默认数据包为 `data/2026/singapore/`，也可向命令传 `--input "数据包目录"`。

1. **决赛打完**，执行 `python -B -m htpm refresh --model 4.2`。程序下载公开逐图 ZIP，自动选取主赛日期内的系列赛，识别四分之一决赛、半决赛、季军赛和总决赛。逐场总比分、实收图数和十人技术统计对齐后，生成双 Major 暂行榜。模板未填任何荣誉时，截止日自动取决赛日。上游尚未更新完整时，补齐或更新数据后重复运行即可。[公开数据源](https://www.kaggle.com/datasets/ektarr/counter-strike-pro-matches)
2. **HLTV 公布奖项**，打开 [event.json](../data/2026/singapore/event.json)。把 `as_of` 设为本次真实统计截止日，`awards.mvp` 填 MVP 小写 ID，`awards.evps` 按官方顺序填小写 ID，将只有身份、没有顺位依据的 EVP 放在 `unranked_evps`。填上 `awards.source` 的 HLTV 链接和 `awards.published_on` 的发布日期。只有 MVP 已官宣时可先保存并保留 `pending`。完整名单核实后，把 `awards_status` 设成 `complete`。
3. **生成正式榜**，执行以下命令。已下载的 ZIP 会被复用。每次生成的正式、暂行或赛前报告各存一份，最新入口随成功的构建更新。

```powershell
python -B -m htpm build --model 4.2
python -B -m htpm validate --model 4.2
```

有官方明确争奖评语时，可在 `awards.peak_context` 中按 EVP 的 ID 填入含 `signal`、`note`、`source` 的对象。官方明确评价接近 MVP 时用 `close`，明确有差距时用 `clear`。该入口也支持第二及以后顺位的 EVP。留空时按 4.1.1 的顺位和实测表现规则计算。

## 赛果导入与补录

新加坡主赛事为 HLTV 8302，预定 12 月 2–6 日 Stage 3、12 月 10–13 日淘汰赛。当前赛制对应 33 场瑞士轮、6 场四分之一决赛及半决赛、1 场季军赛、1 场 BO5 总决赛，共 41 场。Stage 1、Stage 2 与表演赛排除。季军赛进整站样本并在阶段矩阵单列。赛事范围固定为赛前 23 站加本届主赛。赛程若由主办方调整，应先按正式公告修订配置。[HLTV 主赛事](https://www.hltv.org/events/8302/pgl-major-singapore-2026) · [赛程](https://www.hltv.org/major/matches) · [4.2 配置](../config/season_4_2.json)

|可用资料|怎么使用|
|---|---|
|已下载公开 ZIP|原样放成 `results.zip` 并运行 build。若数据源的赛事名称有别，在 event.json 的 `dataset_name` 写入归档名称。赛后程序优先读取 ZIP。|
|ZIP 缺个别地图或技术统计|用 `maps_patch.csv` 补录整张地图的十人统计，格式同 maps.csv，另加 `source` 的 HLTV 比赛页链接。用数据集的系列赛 ID，同一张已存在的地图也需沿用原图 ID。程序将合并后的逐图胜负与独立的系列赛总比分行再核对。|
|上游 ZIP 更新慢，已有完整赛果|在单独的数据包中复制 event.json，填写 `as_of`、`map_source`。填 [matches.csv](../data/2026/singapore/matches.csv) 与 [maps.csv](../data/2026/singapore/maps.csv)，用 `build --input "数据包目录"`。每场写实际图数及唯一 HLTV 比赛页；每张图写两队各 5 名选手的 K/D、ADR、KAST、局数和胜负。|
|HLTV 已给出系列或整站 Rating 3.0|可选 `ratings.csv`，表头 `match,player,rating,source`。match 留空表示整站，否则与导入数据的系列赛 ID 一致。player 填小写 ID，source 填对应 HLTV 页。手工 maps.csv 也可以填可选的 series_rating、event_rating。|
|同一选手出现拼写差异|`aliases` 填“小写来源别名 → 小写模型 ID”。正式替补按实际地图出场，每张图独立识别五人阵容。|

手工赛程阶段取 `group/playoff/placement/final`，场馆取 `arena/studio/unknown`，win 取 1 或 0，KAST 取百分数。一个系列赛的地图均以该系列开赛日归档。出现判负或未实际打出的地图时，以官方比赛页的实打图数为准，在 matches.csv 的 `exception` 写明原因。自动导入默认把可核实的淘汰赛现场记为 arena，Stage 3 场馆记为 unknown。未知场馆继续进入阶段统计。强敌与参赛阵容使用本届邀请日 11 月 2 日的全球 VRS Top 10，至少三名选手重合才匹配球队。

## 双 Major 如何计分

核心八项权重依次为荣誉 30%、分档赛事 22%、强敌 13%、关键阶段 13%、高峰 11%、团队成绩 3%、稳定性 4%、样本覆盖 4%。Major、超级精英、精英、大型、中型在 E 和 K 的分档部分依次占 30%、27%、23%、16%、4%。K 的一半来自分档阶段，小组/淘汰在该部分占 40%/60%。无奖履历系数固定为 0.25，与 4.1.1 经 2025 校准后实际使用的值一致。

两届 Major 共用年度档位。E 每站至多取 16 张图作为合并权重，按地图数和有效站数收缩；K 使用实打阶段地图。荣誉逐站记入 A，累积后按递减收益换分；P 重新选出赛季高峰，单独的高档峰值位置只取最佳一站。缺席者保留实际已打的一届；没有出场的站次不生成 Rating。参加两届也没有固定名次或固定加分。

H 是 3.5 年度汇总的有上限校正。正式赛季对照的 Major 覆盖目标改为两站、24 图，只改变 H 的覆盖衡量；单站 12 图和 0.5 站的收缩先验沿用。R 是公开阶段表的有上限校正。两者分别检查日期，各自缺失或过期时该项为零。赛前数据可完全复现 4.1.1。赛后以可取得的同期证据出榜，报告记录每项是否启用。

- H 可选 `aggregate.json`，使用 [3.5 原始输入结构](../output/current/input.json) 的 `aggregate-1` 全年同期数据；查询结束日与快照截止日一致，新加坡参赛图数和每名选手的荣誉需与档案对齐。共同合格样本太少时停用 H。
- R 可选 `published.json`，沿用 [公开阶段表格式](../data/2026/published_stage_ratings.json)，另填 `rating_version` 为 `3.0`，`events` 为此次 24 站名称数组。按原表相同分组填写 maps 与 Rating。源表未覆盖的选手不做此项调整。

分数对应纳入范围内的年度预测。JSON 的 box_index 是击杀、死亡、ADR、KAST 等逐图统计合成的模型指标，observed_rating 和 event_rating 才是已导入的实测 Rating。排名理由给出上下相邻者、实际总分差和形成该方向差距的最大正贡献，各模块还可能相互抵消。

## 2025 年回放

运行 `python -B -m htpm replay --model 4.2` 可复算奥斯汀与布达佩斯两届 Major 所在的整个年度。Top 20 平均名次误差按实际入选的 20 人计算，Top 30 两两顺序共 435 对。

|可用证据|Top 20 命中|Top 10 命中|Top 20 平均误差|排对的 Top 30 顺序|
|---|---:|---:|---:|---:|
|4.2 核心|19/20|7/10|3.05 位|382/435|
|核心加同期 H，1 站/12 图对照|19/20|8/10|2.80 位|387/435|
|核心加同期 H，2 站/24 图正式口径|19/20|8/10|2.80 位|388/435|

该年用于校准，属于同季回放。2025 两届 Major 逐图档案分别覆盖 68/71 和 62/68 图，缺图保留为缺失。2025 没有同口径同期 R，以上结果未使用该项。[完整回放与覆盖审计](../output/forecast_4_2/replay_2025.json)
