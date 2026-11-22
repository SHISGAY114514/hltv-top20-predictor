# 2026赛事分级：2026-11-16用户固定规则

科隆Major为Major；克拉科夫为超级精英；EWC、EPL S24、BLAST波尔图、鹿特丹为精英；其余铜色MVP为中型、银色MVP为大型。

奖章来源：[HLTV MVP档案](https://www.hltv.org/players/mvp)，2026-11-16复核。T1/T2/T3对应金/银/铜奖章类别；五档是本模型的用户规则，非HLTV官方年度分档。

共23项：Major 1、超级精英1、精英4、大型12、中型5。奖项档案截至11月15日，分级及顺位于11月16日复核；58名选手表现已于11月17日统一重新采集。

| 等级 | 赛事 | MVP | 奖章 |
|---|---|---|---|
| Major | IEM Cologne Major 2026 | m0NESY | 金 |
| 超级精英 | IEM Kraków 2026 | ZywOo | 银 |
| 精英 | Esports World Cup 2026 | donk | 银 |
| 精英 | ESL Pro League Season 24 | ZywOo | 银 |
| 精英 | BLAST Open Porto 2026 | donk | 银 |
| 精英 | BLAST Open Rotterdam 2026 | ropz | 银 |
| 大型 | BLAST Bounty 2026 Season 1 Finals | NiKo | 银 |
| 大型 | BLAST Rivals 2026 Season 1 | ZywOo | 银 |
| 大型 | BLAST Rivals 2026 Season 2 | KSCERATO | 银 |
| 大型 | ESL Pro League Season 23 Finals | makazze | 银 |
| 大型 | IEM Atlanta 2026 | w0nderful | 银 |
| 大型 | IEM Beijing 2026 | xertioN | 银 |
| 大型 | IEM Rio 2026 | ZywOo | 银 |
| 大型 | PGL Astana 2026 | donk | 银 |
| 大型 | PGL Cluj-Napoca 2026 | ZywOo | 银 |
| 大型 | PGL Masters Bucharest 2026 | YEKINDAR | 银 |
| 大型 | StarLadder StarSeries Fall 2026 | ZywOo | 银 |
| 大型 | Thunderpick World Championship 2026 | KSCERATO | 银 |
| 中型 | BLAST Bounty 2026 Season 2 Finals | Spinx | 铜 |
| 中型 | PGL Bucharest 2026 | cmtry | 铜 |
| 中型 | XSE Pro League Guangzhou 2026 | HUASOPEEK | 铜 |
| 中型 | CS Asia Championships 2026 | latto | 铜 |
| 中型 | FISSURE Playground 3 | latto | 铜 |

Bounty S1为银色、大型；Bounty S2为铜色、中型。PGL Bucharest为铜色、中型；PGL Masters Bucharest为银色、大型。Thunderpick 2026为银色、大型，不能沿用2025年的铜色分类。

## 两版怎样使用这 23 站

4.4.3 在固定档位内按参赛阵容、规模及场地逐站计算系数。E 与 K 分档部分按 Major、超级精英、精英、大型、中型分配 30%、27%、23%、16%、4%。赛事强度以收录赛段开赛前最近一期归档 VRS 匹配各队首张实收地图的阵容；对手强度另按每张图赛前的快照匹配。[23 站实际系数](https://github.com/SHISGAY114514/hltv-top20-predictor/blob/32eca4c96118324034ab15f5cb85377b6dc0cb55/output/forecast_4_4_3/snapshot/36985ce4e8239e62/events.md) · [版本对照](COMPARE_3_5_4_4_3.md)

### 3.5 的用法

分级用于A荣誉、E分档表现、T团队奖励及N覆盖。Major/Super-elite/Elite各层覆盖目标为1/1/4项。30种参数情景均不改动用户固定等级。Bounty S1仍属Big，仅A/T荣誉乘0.60。

未举行的新加坡Major不列入已赛清单；预选、Major早期阶段及Bounty线上阶段不另算独立MVP赛事。3.5 的报告保存在 `output/current`。
