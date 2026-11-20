# 数据维护与候选池

人工维护事实位于data/2026，证据位于data/reference；参数位于config。output/current全部可由构建重建，不手工修改。

## 新候选人

MVP/EVP档案中的每个player_id自动成为正式候选人，名单不依赖完整统计或样本资格。新获奖者无需手工加进另一份名单。无奖项观察选手放入config/watchlist.json，需有原始统计支持，当前观察池非穷尽。

新增选手统计必须采集年度Rating/图数、Top5/10/20/30/50累计Rating/图数、完整逐赛事记录及来源。全部逐赛事图数必须等于年度图数。缺失组使用null且地图数为0，不能将未知Rating填0。缺少完整统计者保留在candidates.json并标pending_collection，不进入评分输入。

新一轮统计应统一截止日期、Rating版本及筛选口径；不能把11月16日新抓取的全年数值冒充11月15日旧快照。本次58人统一采集于2026-11-17，均已补齐。每人的retrieved_on必须与快照日期一致，否则拒绝构建。

## 奖项与分级

每名选手每场最多一项MVP或EVP。EVP顺位目录包含完整官方序列及URL，MVP单列、池外选手保留位置；与原档案成员不一致则拒绝构建。新增赛事需要补入奖章/分级目录。荣誉积分来自现行参数，不保存另一套手工分数。

## 输出

candidates.json是全体候选与观察人员；input.json仅含可评分者；scores.json包含已评估人员及资格判断，当前已覆盖全部58人；未达门槛者无名次。evaluation.json/html/md提供逐人理由与相邻名次贡献差。config.json是解析分级和顺位后的配置，源参数为config/model.json。manifest.json记录来源哈希与人数。candidates.html展示全池，report.html明确显示待补人数，bounty.html对照四种荣誉系数。
