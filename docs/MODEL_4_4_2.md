# HTPM 4.4.2 · 鹿特丹峰值与年度第 5 名

按 2026 年 11 月 17 日的 23 站、177 人重算，ropz 以 63.445122 分列第 5，flameZ 以 63.282962 分列第 6。4.4.1 中 flameZ 领先 0.317572 分，本版 ropz 领先 0.162161 分。[全榜](../output/forecast_4_4_2/latest.md) · [177 人分项对照](../output/comparison_4_4_2/comparison.csv)

## 证据与规则

HLTV 将鹿特丹 MVP 颁给 ropz。他在场馆阶段的 Rating 为 1.54，ZywOo 和 flameZ 均为 1.28。整站统计则支持两位挑战者。编辑在 EVP 文章中点名三人，说明他们在本站的表现对年终 Top 20 会获得相近认可。克卢日提供了另一种情形，编辑明确表示 flameZ 的 EVP 对年终评选的价值明显高于 ropz 的 EVP。[鹿特丹 MVP](https://www.hltv.org/news/44213/pristine-playoffs-takes-ropz-to-blast-open-rotterdam-mvp) · [鹿特丹 EVP](https://www.hltv.org/news/44217/the-evps-and-all-stars-of-blast-open-rotterdam-2026) · [克卢日 EVP](https://www.hltv.org/news/43957/the-evps-and-all-stars-of-pgl-cluj-napoca-2026)

4.4.2 只在编辑明确比较本站 MVP 与具名挑战者的**年终价值相近**时启用一条单站规则。每个具名挑战者计入年度峰值模块 P 的本站指数，取其原始峰值与本站 MVP 原始峰值中的较小值。低于上限的峰值照实入账。文章只提到“接近 MVP”、同属第一 EVP 或选手同队，均不足以触发此规则。当前配置有一条记录，列出鹿特丹三人、原文、发布日期及引文。程序核对赛事、正式获奖人、EVP 顺序、来源与截止日。[证据配置](../config/season_4_4_2.json)

这个单向上限是模型对“相近”的保守解释。编辑没有规定峰值指数相等，也没有公布换算方式。整站表现仍计入 E，MVP 与各档 EVP 仍按 A 计分，官方赛段和对强队表现仍由 K、O 反映。完整分数 JSON 同时保留三人的原始峰值 `raw_peak` 和实际送入 P 的 `peak`。

|鹿特丹选手|原始峰值|计入 P 的本站峰值|年度总分变化|
|---|---:|---:|---:|
|ropz|86.5133|86.5133|0|
|ZywOo|95.7600|86.5133|0|
|flameZ|94.2186|86.5133|−0.479733|

flameZ 的 P 贡献下降 0.599666 分，既有年度汇总校正 H 随核心分重算后回补 0.119933 分。ZywOo 有更高的其他赛站峰值，年度 P 仍为满分。177 人中只有 flameZ 的总分变化，也只有他与 ropz 交换名次。KSCERATO 第 4、sh1ro 第 7；HeavyGod 第 20、try 第 21。

## 验证与限制

4.4.1 与 4.4.2 之间只有这项评分差异，撤回上限即可重现旧顺序。两版本共用比赛输入摘要，4.4.1 复算快照为 `9a7ba5fd6d60709b`，4.4.2 为 `463b1b66c3749110`。本次按已讨论的选手对修正，能验证改动范围和复现性；跨赛季预测准确率仍待独立数据检验。

```powershell
$env:PYTHONHASHSEED='0'
$env:PYTHONUTF8='1'
python -B -m analysis.compare_4_4_2
python -B -m htpm validate --model 4.4.2
python -B -m unittest discover -s tests
```
