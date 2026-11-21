# HTPM · HLTV 年度 TOP 20 预测模型

HTPM 用公开比赛统计估计 Counter-Strike 选手的年度排名。**当前默认版本为 HTPM‑4.3**。本版删除团队名次加分，纳入 HLTV 明确点名的个人 VP，并按实战阵容、赛段和场地逐站计权。**2026 年 11 月 17 日快照**覆盖 23 项赛事，177 名选手达到排名门槛。新加坡 Major 赛后可导入第 24 站并重算年度榜单。项目独立于 HLTV。

| 版本 | 如何评分 | 参数与规则 | 预测结果 |
|---|---|---|---|
| **4.4.3（11 月 17 日修订）** | 沃斯堡六进四按八队赛口径归类，保留整站与场馆数据 | [修正范围及复算](docs/MODEL_4_4_3.md) | [全榜](output/forecast_4_4_3/latest.md) · [177 人排名长图](output/model_cards/HTPM-4.4.3-ranking.png) · [与 4.4.2 的逐人对照](output/comparison_4_4_3/comparison.csv) |
| **4.4.2（11 月 17 日修订）** | 按鹿特丹年终评语限制本站计入 P 的峰值 | [规则与验证](docs/MODEL_4_4_2.md) | [全榜](output/forecast_4_4_2/latest.md) · [177 人排名长图](output/model_cards/HTPM-4.4.2-ranking.png) · [与 4.4.1 的 177 人对照](output/comparison_4_4_2/comparison.csv) |
| **4.4.1（11 月 17 日修订）** | 统一赛事履历倍率、补用整站观测及官方争奖评语，社区阶段表作敏感性对照 | [模型、原文与逐图核验](docs/MODEL_4_4_1.md) | [全榜](output/forecast_4_4_1/latest.md) · [与 4.4 的 177 人逐项对照](output/comparison_4_4_1/comparison.csv) |
| **4.4（11 月 17 日固定快照）** | 三场比赛的季后赛口径与互斥 VRS 对手档 | [模型、证据与离线复算](docs/MODEL_4_4.md) | [全榜](output/forecast_4_4/latest.md) · [与 4.3 的分析](output/comparison_4_4/分析.md) · [177 人逐项对照](output/comparison_4_4/comparison.csv) |
| **4.3** | 个人荣誉、逐站赛事权重、去除团队分的年度校正 | [参数](config/season_4_3.json) · [模型、证据与赛后操作](docs/MODEL_4_3.md) | [当前榜单与逐站赛事权重](output/forecast_4_3/latest.md) · [2025 回放](output/forecast_4_3/replay_2025.json) |
| **4.2** | 两届 Major 共用年度分档份额，按实际出场、阶段表现和荣誉重算全榜 | [参数](config/season_4_2.json) · [赛后出榜与补录说明](docs/MODEL_4_2.md) | [当前榜单](output/forecast_4_2/latest.md) · [2025 双 Major 回放](output/forecast_4_2/replay_2025.json) |
| **3.5** | 综合赛事荣誉、分档整站 Rating、对强队表现、团队成绩、稳定性和样本质量 | [参数](config/model.json) · [模型说明](docs/MODEL_AGGREGATE.md) · [高清图](output/model_cards/HTPM-3.5.png) | [逐人理由](output/current/evaluation.md) · [完整得分](output/current/scores.json) · [Major 条件情景](output/scenarios/major_projection.md) |
| **4.1.1** | 加入分档小组赛与淘汰赛、场馆、赛事高峰和接近 MVP 的表现 | [参数](config/season_model.json) · [模型说明](docs/MODEL_4_1_1.md) · [高清图](output/model_cards/HTPM-4.1.1.png) | [全榜与逐人理由](output/forecast_4_1_1/ranking.md) · [分项、敏感性与 Major 情景](output/forecast_4_1_1/scores.json) |

## 离线复现

安装 Python 3.9 或以上版本。在仓库根目录依次运行以下命令。评分、回测、生成榜单和测试仅使用 Python 标准库，所需快照随仓库提供。

```sh
python -B -m htpm build
python -B -m htpm validate
python -B -m htpm replay
python -B -m unittest discover -s tests
```

前两条命令生成并核对 4.3 榜单，第三条复算 2025 年荣誉权重和双 Major 回放。新加坡决赛结束后，安装 requests 并运行 `python -B -m htpm refresh` 获取逐图数据。HLTV 公布完整奖项后，将核实的 MVP、EVP 和来源填入数据包，执行 build 生成正式预测。逐站核实的 VP 可通过 vps.json 补入。[赛后操作说明](docs/MODEL_4_3.md) · [赛果模板](data/2026/singapore/)

要在决赛日之后离线复核本次发布的赛前快照，可在本版的干净检出中运行 `python -B -c "from datetime import date; from htpm.forecast_4_2 import calculate, publish; print(publish(calculate(today=date(2026,11,17), model='4.3'), verify=True))"`。复算 4.2 时显式指定 `--model 4.2`。3.5 和 4.1.1 的预测可用 `python -B -m htpm build --model 4.1.1` 和 `python -B -m htpm validate --model 4.1.1` 重建、核对。3.5 单独回测使用 `python -B -m analysis.replay_aggregate_2025`，Major 条件情景使用 `python -B -m analysis.major_projection`。

## 2025 年官方榜单回测

4.3 在同季回放中启用年度汇总校正、将 VP 证据截止日设在揭榜前时，Top 20 入选命中 19 人，Top 10 命中 8 人，官方 Top 20 平均名次误差为 2.70 位。补入年终文章可逐站定位的三次 VP 后，入选命中数相同，平均名次误差变为 2.90 位。2025 年同时用于参数校准。[4.3 回放明细](output/forecast_4_3/replay_2025.json)

4.2 核心评分在 2025 年命中 Top 20 中的 19 人，实际 Top 20 的平均名次误差为 3.05 位。加入同期年度汇总校正后，Top 20 仍命中 19 人，Top 10 命中 8 人，平均误差为 2.80 位，Top 30 的 435 对相对顺序中排对 388 对。该季也用于参数校准。[4.2 回放与地图覆盖](output/forecast_4_2/replay_2025.json)

| 同一批 151 名候选人 | TOP20 入选 | TOP10 入选 | 官方前 20 名次全对 | 官方前 20 平均名次误差 |
|---|---:|---:|---:|---:|
| HTPM‑3.5 | 19/20 | 10/10 | 8/20 | 1.50 名 |
| HTPM‑4.1.1 | 19/20 | 7/10 | 5/20 | 3.05 名 |

3.5 固定权重，按选手分五折再合并，结果相同。4.1.1 在 2025 年选择参数，按选手分五折重选参数后，TOP20 命中 18/20，平均误差 3.40 名。以上是同一赛季的历史结果，跨赛季准确率仍需独立验证。[3.5 逐人回测](output/replay_3_5_2025/scores.json) · [4.1.1 回测和逐项检验](output/forecast_4_1_1/scores.json) · [HLTV 官方榜单](https://www.hltv.org/news/43492/top-20-players-of-2025-final-list)

## 数据和代码入口

- [评分代码](htpm/)和[测试](tests/)包含候选人筛选、评分、参数选择、敏感性分析与榜单生成。
- [2025 输入](data/2025/)、[2026 输入](data/2026/)和[证据目录](data/reference/)包含逐图比赛记录、年度及逐站统计、赛事分档、奖项及其来源。
- [分析工具](analysis/)提供回测、条件情景、逐图归档提取及战报采集。可选的联网战报采集需安装 requests、beautifulsoup4 和 lxml。可选的制图脚本使用 Pillow 和 Windows 系统字体。两张成品 PNG 已随仓库提供。

## 许可与署名

原创代码、配置、项目文档与两张模型信息图采用 [MIT 许可](LICENSE)。上游逐图数据及其改编数据适用 CC BY-SA 4.0。HLTV、Valve 与社区统计的出处、归属和使用范围见[数据来源与许可](DATA-LICENSE.md)。
