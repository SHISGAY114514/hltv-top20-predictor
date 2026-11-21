# HTPM 4.4.1 · KSCERATO 与 flameZ 的 11 月 17 日比较

4.4 把 flameZ 列在 KSCERATO 前面 0.0105 分。用相同的 23 站、177 人和 11 月 17 日截止日复算，4.4.1 的 KSCERATO 为第 4 名，63.9324 分，flameZ 为第 5 名，63.7627 分。分差为 0.1697。下列选择是预测模型对证据用途的判断。HLTV 的年度方法强调重要赛事表现、对手、样本和不同分量的荣誉，未发表这两人的 2026 年度顺位或具体系数。[HLTV 年度方法](https://www.hltv.org/news/43492/top-20-players-of-2025-final-list) · [4.4.1 全榜](../output/forecast_4_4_1/latest.md) · [177 人分项与消融 CSV](../output/comparison_4_4_1/comparison.csv)

## 两人的证据

KSCERATO 有两个 MVP 和四个 EVP。香港站 10 图 1.55，半决赛 1.69、决赛 1.68。雷电杯颁奖时的整站 Rating 为 1.34，决赛结束时编辑明确认为他领先竞争者 Magnojez。克拉科夫两人同场，编辑将 KSCERATO 列为第二 EVP、flameZ 第三 EVP。冻结社区大赛表中 KSCERATO 为 200 图 1.19，flameZ 为 172 图 1.16。[香港 MVP](https://www.hltv.org/news/45996/kscerato-dominates-to-claim-blast-rivals-s2-mvp) · [雷电杯 MVP](https://www.hltv.org/news/45753/kscerato-crowned-thunderpick-world-championship-2026-mvp) · [克拉科夫 EVP](https://www.hltv.org/news/43853/the-evps-and-all-stars-of-iem-krakow-2026) · [社区表及日期](../data/2026/published_stage_ratings.json)

flameZ 的五个 EVP 中有三个第一顺位。鹿特丹颁奖文章指出三名队友都值得获得相近的年终认可，flameZ 在决赛前还领跑 MVP。Fort Worth 是明确的接近之争，EPL S24 的 flameZ 是第一 EVP 和最接近的挑战者。克卢日的文章确认他构成挑战，也记载 ZywOo 最终领先 0.10 Rating。年度 HLTV 对前五样本由 flameZ 领先，57 图 1.15 对 51 图 1.13。社区决赛统计同样支持 flameZ，23 图 1.23 对 20 图 1.13。[鹿特丹 MVP](https://www.hltv.org/news/44213/pristine-playoffs-takes-ropz-to-blast-open-rotterdam-mvp) · [鹿特丹 EVP](https://www.hltv.org/news/44217/the-evps-and-all-stars-of-blast-open-rotterdam-2026) · [Fort Worth](https://www.hltv.org/news/44521/the-evps-and-all-stars-of-blast-rivals-2026-season-1) · [EPL S24](https://www.hltv.org/news/45751/the-evps-and-all-stars-of-esl-pro-league-s24) · [克卢日](https://www.hltv.org/news/43957/the-evps-and-all-stars-of-pgl-cluj-napoca-2026)

## 对全体选手生效的改动

1. **社区阶段表 R 改为敏感性对照。** 39/177 人有表，表内精英、季后赛、精英季后赛、场馆和决赛样本重叠。核心 K 已经计入实收地图的阶段表现。现有表缺逐图清单，尚无法在 2025 回放中检验其对核心分以外的预测增益。保留原表、原算法和恢复 R 后的逐人排名。若补齐样本身份并在独立历史样本中验证增益，可以重新评价这一决定。
2. **用同一套赛事规则评价两站。** 取消原先雷电杯 ×0.33 和香港 ×1.25 两个额外倍率，A、P、无奖调整以及相应 VP 基准均使用现有档次、阵容与场地规则。两站同属模型的 Big 档，实际参赛阵容、个人发挥和争奖形势仍可产生不同分值。年度核心权重、五档份额及其他原有规则沿用 4.4。回退情景同时恢复两个倍率。
3. **分别处理整站观测与逐图观测。** 对冻结 HLTV 表中同名赛事、同一选手、已有部分地图、实收图数短于整站且无另设收录起日或外围赛段的记录，整站 Rating 进入 E 和 A/P 中的整站发挥部分。仍按实收图数估计可靠性。季后赛、胜图及其收缩基准使用实收样本，K、O、N 的地图数和数值不因此变化。每条新增整站观测带来源、快照日期、整站和实收图数。177 人中共 55 人的 258 个选手赛事组合满足此条件。其余缺口继续区分。H 的年度汇总也可能使用同一整站统计，另列移除 H 的结果。
4. **将官方颁奖措辞按既有规则入账。** Fort Worth 的第一 EVP flameZ 补上明确的接近争奖记录，雷电杯第一 EVP Magnojez 补上颁奖时胜者优势明确的记录。鹿特丹和 EPL S24 已有记录，克卢日保留第一 EVP。荣誉的类别、顺位和数量均逐人核对。接近度的数值折算仍是继承的模型假设。此次核对涉及的赛事有对应原文，全年编辑语境仍有待补齐的站次。[4.4.1 配置与原文链接](../config/season_4_4_1.json) · [原赛事修正规则](MODEL_4_1_1.md)

## 两个实收缺口怎样确定

在完整分数 JSON 中，`event_rating` 保留原来的同图数口径；`whole_event_observation` 单独给出更长的整站样本及其来源。后者进入整站质量部分，分档赛段表仍可逐图复核。

|选手与站次|整站 Rating 3.0 快照|实收图数|确认缺少的比赛地图|
|---|---:|---:|---|
|KSCERATO，雷电杯|12 图，1.34|11|决赛对 BETBOOM 的 Cache，13–6，11 杀 12 死|
|flameZ，鹿特丹|11 图，1.46|10|决赛对 NAVI 的 Dust2，13–10，17 杀 14 死|

雷电杯本地决赛有 19、35、22、24 回合四图。唯一的 19 回合记录是 KSCERATO 的 21 杀 8 死，对应 Dust2；另一张 19 回合图 Cache 缺失。鹿特丹本地决赛有 20 和 23 回合两图。23 回合记录为 flameZ 的 12 杀 17 死，对应 Anubis；另一张 23 回合图 Dust2 缺失。本次保持逐图输入固定，两张缺图的击杀或现时页面 Rating 均未补写进冻结输入。整站统计取自 11 月 17 日归档。[雷电杯决赛](https://www.hltv.org/matches/2399417/furia-vs-betboom-thunderpick-world-championship-2026) · [Dust2](https://www.hltv.org/stats/matches/mapstatsid/242084/betboom-vs-furia) · [Cache](https://www.hltv.org/stats/matches/mapstatsid/242114/betboom-vs-furia) · [鹿特丹决赛](https://www.hltv.org/matches/2391775/vitality-vs-natus-vincere-blast-open-rotterdam-2026) · [Anubis](https://www.hltv.org/stats/matches/mapstatsid/224510/natus-vincere-vs-vitality) · [Dust2](https://www.hltv.org/stats/matches/mapstatsid/224523/natus-vincere-vs-vitality)

败者出局系列赛可发生在小组阶段，季后赛也可能含位置赛。现有快照没有完整的败者出局逐图清单。本版沿用已核赛段，不把对话中重建的筛选图数写入评分。

## 名次因何改变

|相对完整 4.4.1 的单项试验|KSCERATO 名次|flameZ 名次|KSCERATO 减 flameZ（分）|
|---|---:|---:|---:|
|完整 4.4.1|4|5|+0.1697|
|恢复社区 R 加分|6|4|−0.5796|
|同时恢复两站特殊倍率|4|5|+0.1503|
|整站观测恢复地图数完全匹配门槛|4|6|+0.5064|
|恢复旧版的第一 EVP 评语档案|4|5|+0.4052|
|移除年度汇总 H|5|4|−0.3688|

其中 R 的处理决定了新旧两版的相对顺序。修复整站样本及补齐争奖证据均有利于 flameZ。用 4.4.1 规则，年度汇总 H 同样足以改变两人排序。这些试验分别从完整新模型出发。当前一季的变化不能衡量跨季准确率。

Top 20 成员相同，50/177 人有名次变化，Spearman ρ 为 0.999749。第 4–7 名依次为 KSCERATO、flameZ、ropz、sh1ro。HeavyGod 以 46.1767 分第 20，try 以 44.3505 分第 21。最大上升是 Magnojez（8 位），最大下降是 luchov（3 位）。每人八个核心模块与 H/R 的变动都可与总分差对账。[177 人对照](../output/comparison_4_4_1/comparison.csv) · [运行清单](../output/comparison_4_4_1/manifest.json)

## 离线复算

在仓库根目录使用本次验证的 Windows CPython 3.9.13（32 位）。4.4.1 为显式选择的固定快照版本。默认入口继续使用 4.3。

```powershell
$env:PYTHONHASHSEED='0'
$env:PYTHONUTF8='1'
python -B -m analysis.compare_4_4_1
python -B -m htpm validate --model 4.4.1
python -B -m unittest discover -s tests
```

比较命令先从同一输入重算 4.4 并核验快照 `d1ebc4b1e3c25d70`，再生成和核验 4.4.1 及四次逆向试验。移除 H 的第五行试验按每人的实际贡献重排名。历史情景通过同一比较命令复现。
