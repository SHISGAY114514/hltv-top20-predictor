# HTPM · Counter-Strike 2 年度选手排名预测

**当前发布版本为 HTPM 4.4.3。** 模型估计截至 **2026 年 11 月 17 日**，哪些选手的赛季表现最接近 HLTV 年度 Top 20 的评选口径。覆盖 23 项已赛主赛事，301 名出场选手中有 177 人达到排名资格。科隆 Major 已计入，新加坡 Major 尚未开赛。HTPM 是独立预测项目，HLTV 负责发布官方年榜。

**[177 人全榜与前 30 名理由](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/output/forecast_4_4_3/snapshot/36985ce4e8239e62/ranking.md)** · [高清排名长图](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/output/model_cards/HTPM-4.4.3-ranking.png) · [逐人分数与分项](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/output/forecast_4_4_3/snapshot/36985ce4e8239e62/scores.json) · [23 站权重](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/output/forecast_4_4_3/snapshot/36985ce4e8239e62/events.md)

## 4.4.3 怎么排

- **荣誉与赛场表现**占核心分中的 31 分和 23 分。正式 MVP、EVP 顺位、争奖评语及有明确出处的 VP 进入赛事履历。这些权重是 HTPM 的设定。整站表现按 Major、超级精英、精英、大型、中型五档汇总，档内参考赛前阵容、赛制、场地及个人样本。
- **对强队表现、关键阶段、峰值**分别占 13、14、11 分。对手按每张图赛前的月度全球 VRS 匹配。季后赛、决赛、场馆数据按实收地图统计，同一张图可以回答不同问题。4.4.3 将沃斯堡八队赛的六进四单列，保留整站和场馆记录。
- **稳定性和样本覆盖**各占 4 分，团队名次直接权重为零。模型在核心分上叠加同日年度汇总校正 H，幅度最多 ±2.5 分。社区阶段表 R 用于敏感性比较。当前快照的前六名依次为 ZywOo、donk、m0NESY、KSCERATO、ropz、flameZ。[评分代码](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/htpm/season.py) · [4.4.3 修正记录](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/model/htpm-4.4-verified/docs/MODEL_4_4_3.md)

## 与 HTPM 3.5 的区别

3.5 从获奖者和观察名单出发，使用整站 Rating、年度累计强队统计和团队名次。4.4.3 从逐图参赛者出发，能单独评价一名选手在哪个赛段、面对什么强度的对手打出了高峰。用同一截止日实算，资格人数从 **46 增至 177**。两版预测的 Top 20 成员相同，内部有 9 人名次不同；第 20 名均是 HeavyGod，第 21 名由 tN1R 变为 try。[逐项方法、Top 20 分数与历史检验](docs/COMPARE_3_5_4_4_3.md) · [177 人版本对照 CSV](docs/ranks_3_5_4_4_3.csv)

## 从 GitHub 离线复算

完整代码和发布输入在 `model/htpm-4.4-verified` 分支。首次获取用下面的命令；已有完整仓库可执行 `git fetch origin` 和 `git switch model/htpm-4.4-verified`。评分和测试使用 Python 标准库，本次快照的验证环境为 Windows CPython 3.9.13。

```powershell
git clone --branch model/htpm-4.4-verified https://github.com/SHISGAY114514/hltv-top20-predictor.git
cd hltv-top20-predictor
$env:PYTHONHASHSEED='0'
$env:PYTHONUTF8='1'
python -B -m htpm validate --model 4.4.3
```

`build --model 4.4.3` 生成榜单，`validate --model 4.4.3` 核对存档，预期快照为 `36985ce4e8239e62`。公开仓库 CLI 省略 `--model` 时仍选择 4.3。4.4.3 只接受冻结输入；4.3 的新加坡赛后导入流程见其版本说明。复现 3.5 时运行 `python -B -m htpm build --model 4.1.1`，读取 `output/current/scores.json`，这个入口会一起重建 3.5 与 4.1.1。[3.5 原始分数](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/output/current/scores.json) · [4.3 赛后流程](docs/MODEL_4_3.md)

## 版本与验证记录

| 版本 | 可核对的主要变化 |
|---|---|
| [4.4.3](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/model/htpm-4.4-verified/docs/MODEL_4_4_3.md) | 沃斯堡两张六进四地图移出季后赛筛选，10 人分数、5 人名次变化。 |
| [4.4.2](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/docs/MODEL_4_4_2.md) | 按鹿特丹编辑年终评语限制本站计入 P 的峰值。 |
| [4.4.1](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/docs/MODEL_4_4_1.md) | 统一两站履历倍率，区分整站观测和逐图样本，社区阶段表转作对照。 |
| [4.4](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/docs/MODEL_4_4.md) | 冻结 23 站、修正赛段、区分互斥 VRS 对手档与未知对手。 |
| [4.3](docs/MODEL_4_3.md) | 引入逐站阵容与赛制系数、明确 VP；移除直接团队得分。 |
| [4.2](docs/MODEL_4_2.md) | 引入双 Major 口径及赛后导入。 |
| [4.1](docs/MODEL_4_1.md) / [4.1.1](docs/MODEL_4_1_1.md) | 逐图阶段与峰值模型，以及首轮赛事履历修订。 |
| [3.5](docs/MODEL_AGGREGATE.md) | 六模块汇总模型，保留候选、资格与来源审计。 |

2025 赛季回放中，3.5 对官方 Top 20 的入选命中为 19/20，平均绝对名次误差 1.50 位。4.3 的同季回放另有记录。4.4.3 已验证的是 2026 冻结快照的可复算性，仓库尚无它在独立赛季的准确率结果。[3.5 回放](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/output/replay_3_5_2025/scores.json) · [4.3 回放](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/output/forecast_4_3/replay_2025.json)

## 数据来源与许可

HLTV 提供奖项顺位、评语和统计来源，Valve 发布月度 VRS，逐图技术统计来自注明出处的赛事档案。各站与逐人记录留存来源、范围及适用日期。原创代码与文档适用 MIT；上游逐图数据及改编数据适用 CC BY-SA 4.0。[数据口径](docs/DATA.md) · [数据来源及再分发条件](DATA-LICENSE.md) · [MIT 许可](LICENSE)
