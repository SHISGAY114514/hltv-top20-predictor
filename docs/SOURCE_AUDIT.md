# 当前来源与审计

## 权威事实输入

1. data/2026/aggregate_snapshot.json：58人年度、累计Top N和逐赛事Rating 3.0快照，统一采集于2026-11-17。每人来源URL保留。年度URL的12-31上限不等于有未来数据。
2. data/2026/award_snapshot.json：23项MVP与124项EVP档案（原120项EVP，11月17日补入香港4项），共55人。原文件中的顺位为空反映最初采集状态；构建时读取独立顺位证据覆盖，不猜顺位。
3. data/reference/evp_orders_2026.json：23项官方有序名单：原22项于2026-11-16核实，香港于11月17日增补；保留池外选手位置。构建时逐事件核对成员集合。
4. data/reference/event_tiers_2026_user.json：用户固定分级及MVP奖章证据，主赛事共1/1/4/12/5项。
5. 2025_top10_20_rationale.json及official_top20_2025.json：历史参考，只用于定性设计与未来验证，不进入2026评分。

EWC的try第一EVP、xfl0ud第六、tenzy第十此前有奖项记录但缺少完整统计，本次均已补齐并参与评估。全部档案获奖者自动纳入；未采集者保留空总分、空名次，不能视为落选。

## 构建时的明确处理

EVP顺位从有来源的目录覆盖到原档案；不混用新闻中的Rating与数据库快照。赛事级别从奖章与用户覆盖规则确定。Bounty S1荣誉系数0.60及各项评分参数属于模型假设。

zweih、frozen的年度网页中有名为2027 Cluj预选赛的已打地图。本次直接保留新采集的逐赛事记录，已删除构建器中补1图/3图的旧修正。名称中的2027不代表比赛发生在未来；这些预选赛仍排除在主赛事评分外。

香港Rivals S2已于2026-11-17依据[官方文章](https://www.hltv.org/news/45998/the-evps-and-all-stars-of-blast-rivals-2026-season-2)补齐：MVP KSCERATO原已存在，EVP依次molodoy、donk、ropz、m0NESY。All-Star的FalleN与PR只归档，不添加EVP。官方MVP与All-Star图确认整站KSCERATO Rating为1.55，正文1.52属于特定对手范围。原始表现快照未改，更新前后哈希见rivals_s2_2026_update_audit.json。全池关键阶段和交叉统计仍缺。

## 3.4重构与删除

删除旧逐图2.2引擎、模拟演示、空模板、早期不完整快照、人工预测、旧配置、旧版输出及依赖它们的比较脚本。保留当前事实快照与来源证据。清理清单及被删除文件SHA256见cleanup_manifest.json，避免旧结果继续作为当前输入。

2025依据版参数config/model.json与输出output/current保持现行入口；2024依据版参数config/model_2024.json，历史构建historical、同源双模型比较compare为新增独立入口。原39人数学评分、分项与名次在重构前后逐项完全一致。以上为3.4历史重构核对；3.5现已补齐58人统计，并增加日期一致性校验及逐人解释。

## 11月17日采集核对

58人均已对齐年度地图数与逐赛事地图数，Top5/10/20/30/50累计图数满足嵌套关系。年度URL以12月31日为筛选上限，内容仅限采集时已经发生的比赛。lauNX、Staehr、dgt、luchov、xelex的普通年度概览请求受限，改用同年度CS2筛选页；其总地图数与未限制版本的2026逐赛事页完全一致。公开页面的Rating以本次数据库值为准，不用颁奖新闻当时的旧Rating替换。完整对账与来源见output/current/collection_audit.json。

