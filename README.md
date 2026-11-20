# HTPM · HLTV 年度 TOP 20 预测模型

HTPM 用公开比赛统计估计 Counter-Strike 选手的年度排名。这里发布两个可以离线运行的版本。HTPM‑3.5 是原稿采用的模型，HTPM‑4.1.1 是当前默认模型。预测使用截至 **2026 年 11 月 17 日**的快照。2025 年榜用于历史回测。本项目独立于 HLTV。

| 版本 | 如何评分 | 参数与规则 | 预测结果 |
|---|---|---|---|
| **3.5** | 综合赛事荣誉、分档整站 Rating、对强队表现、团队成绩、稳定性和样本质量 | [参数](config/model.json) · [模型说明](docs/MODEL_AGGREGATE.md) · [高清图](output/model_cards/HTPM-3.5.png) | [逐人理由](output/current/evaluation.md) · [完整得分](output/current/scores.json) · [Major 条件情景](output/scenarios/major_projection.md) |
| **4.1.1** | 加入分档小组赛与淘汰赛、场馆、赛事高峰和接近 MVP 的表现 | [参数](config/season_model.json) · [模型说明](docs/MODEL_4_1_1.md) · [高清图](output/model_cards/HTPM-4.1.1.png) | [全榜与逐人理由](output/forecast_4_1_1/ranking.md) · [分项、敏感性与 Major 情景](output/forecast_4_1_1/scores.json) |

## 离线复现

安装 Python 3.9 或以上版本。在仓库根目录依次运行以下命令。评分、回测、生成榜单和测试仅使用 Python 标准库，所需快照随仓库提供。

```sh
python -B -m htpm build
python -B -m htpm validate
python -B -m analysis.replay_aggregate_2025
python -B -m unittest discover -s tests
```

第一条命令生成两版的 2026 预测，也运行 4.1.1 的 2025 回测。第二条逐人校验两版保存的结果。第三条单独重跑 3.5 的 2025 回测。要重新计算 3.5 的 Major 条件情景，运行 `python -B -m analysis.major_projection`。

## 2025 年官方榜单回测

| 同一批 151 名候选人 | TOP20 入选 | TOP10 入选 | 官方前 20 名次全对 | 官方前 20 平均名次误差 |
|---|---:|---:|---:|---:|
| HTPM‑3.5 | 19/20 | 10/10 | 8/20 | 1.50 名 |
| HTPM‑4.1.1 | 19/20 | 7/10 | 5/20 | 3.05 名 |

3.5 固定权重，按选手分五折再合并，结果相同。4.1.1 在 2025 年选择参数，按选手分五折重选参数后，TOP20 命中 18/20，平均误差 3.40 名。以上是同一赛季的历史结果，跨赛季准确率仍需独立验证。[3.5 逐人回测](output/replay_3_5_2025/scores.json) · [4.1.1 回测和逐项检验](output/forecast_4_1_1/scores.json) · [HLTV 官方榜单](https://www.hltv.org/news/43492/top-20-players-of-2025-final-list)

## 数据和代码入口

- [两版评分代码](htpm/)和[测试](tests/)包含候选人筛选、评分、参数选择、敏感性分析与榜单生成。
- [2025 输入](data/2025/)、[2026 输入](data/2026/)和[证据目录](data/reference/)包含逐图比赛记录、年度及逐站统计、赛事分档、奖项及其来源。
- [分析工具](analysis/)提供回测、条件情景、逐图归档提取及战报采集。可选的联网战报采集需安装 requests、beautifulsoup4 和 lxml。可选的制图脚本使用 Pillow 和 Windows 系统字体。两张成品 PNG 已随仓库提供。

## 许可与署名

原创代码、配置、项目文档与两张模型信息图采用 [MIT 许可](LICENSE)。上游逐图数据及其改编数据适用 CC BY-SA 4.0。HLTV、Valve 与社区统计的出处、归属和使用范围见[数据来源与许可](DATA-LICENSE.md)。
