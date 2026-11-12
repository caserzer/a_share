# 证据与未完成要求

## 可复核证据索引

|业务问题|权威证据|可支持的结论|
|---|---|---|
|为什么旧36%左右变为高匹配率|[E01统一重评](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/V2_E01_corrected_revaluation.md)|修订评价对象与归属，不能当模型提升|
|20日与5日取舍|[B06同负担实验](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/V2_B06_result.md)|20日质量/总覆盖较高、及时覆盖较低|
|是否优于随机观察|[B07同准入随机对照](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/V2_B07_result.md)|质量和总覆盖增量有支持，及时增量无支持|
|市场共同波动调整有无用|[B08固定实验](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/V2_B08_market_adjustment_result.md)|没有支持，停止该分支|
|为什么漏掉过程|[S03全量遗漏审计](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/V2_S03_missed_process_decisions.md)|真实排序/数量限制为主，不能直接归咎退出慢|
|弱势、市场背景与行业相关性|[S06独立池分层](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/V2_S06_business_strata.md)|弱势后发现更晚；同期行业并非独立样本|
|独立主池计数|[S05主池摘要](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/outputs/evaluation_versions/s05_20261021/runs/A/summary.json)|1459新增、5759父分母，完整未知和失败|
|后续走势|[S04固定窗口跟踪](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/outputs/followup_versions/s04_20261021/summary.csv)|20/60日后续中位表现偏弱，不改覆盖标签|
|目录缺口|[逐周覆盖表](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/outputs/refresh/s02_chain_safe_v2_20261112/calendar_coverage.csv)|496支持周及5个明确未知周|

## 完成审计

独立过程定义、冻结计数协议、全目录历史逐期清单、负担限制和成熟追踪已有可运行可复核产物。年度、市场背景、此前状态及共同时间块证据已存在。它们支持“可使用的研究原型”，尚不足以支持“完整业务目标已验收”。

剩余要求必须具体区分：

1. **业务验收没有完整通过证据。** 用户确认约一半有效、5/20容量及优先质量/总覆盖；没有确认最低覆盖率、最大可接受迟到或最低样本量。不能自行补上回测必过的数值，也不把这些未确认数值说成用户要求。E01在方法比较前冻结了研究口径，但约50%不是其自动过关线。
2. **研究原型语义与实际观察价值仍有边界。** 过程匹配率高，随机同准入也较高；单看匹配率不足以认证“值得继续研究”。案例核验和完整反例不能替代业务有效性证明，迟到质量需保持可见。
3. **现有数据能证明的范围有限。** 历史代理及反复使用不等于独立样本外。新的确认性评价需要事先登记范围与标准，并诚实标记历史复用；不能把再次重跑、改编号或时间切片包装为新证据。这里不擅自新增“必须独立样本外”的唯一门槛。
4. **未来维护尚有审查环节。** 新价格链、分类和标签拆分/合并需明确复核；哈希追踪不保证外部缓存永久可读。尚未部署或形成实时运行系统，而部署本来也不在当前授权中。

[S05逐项审计](/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/reports/V2_S05_scope_and_completion_audit.md)中的此前状态分层缺口现已由S06补充；不能继续把它当未完成任务反复重做。B08已补充信息实验并失败，也不能换编号重试。

## 下一步边界

应将“有效观察”的业务验收条件收敛为可检验、事前登记的确认方案，明确约一半参考如何与覆盖、迟到及实际工作量共同判断。已有数值只能作为设计依据，不能追认为事前验收通过。若没有新的信息依据或遗漏的必要比较，不继续调模型/窗口；如实保留未验证结论。

本交付没有修改完整目标、没有宣布完成，也没有申请交易或部署。用户的实验授权持续有效，不需要逐轮重复许可。
