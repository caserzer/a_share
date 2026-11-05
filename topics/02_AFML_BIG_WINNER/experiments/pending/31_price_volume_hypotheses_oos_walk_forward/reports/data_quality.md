# EP31 数据质量与准入

冻结 release `9ba9324e4ff8f3a5db14c03893d76c77097855d3f83e9dde2b476f2760aec72e`；全量核验 35,170 文件、3,062,382,512 字节。独立重派生并对账 2,103,048 条四期限月末标签，全部字段差异 0；其中 84 条无报价标签保持 UNKNOWN。

price / total / executable 三者是同一前复权价格推断，只使用一次 price。所有预测、收益和费用结果均为 Historical-proxy / inferred；不是实际含息总回报或可执行成交。

| field | quality | reason |
| --- | --- | --- |
| OHLCV_money_turnover | Historical-proxy | sealed vendor rows; conflict flags masked |
| qfq_ratio_features | Historical-proxy | scalar-reanchor invariant; actual company-action ledger unverified |
| security_identity | Historical-proxy | includes delisted; continuous aliases preserved by EP30 |
| ST_suspension | Historical-proxy | vendor row flags; no daily qualification certification |
| float_cap | Historical-proxy | raw close * volume / contemporaneous turnover; no independent shares |
| industry | UNKNOWN | no sealed industry version table |
| true_total_return_and_execution | UNKNOWN | price aliases used once; cash/terminal/fills unverified |
| trade_size_trade_count | UNKNOWN | no timestamp-attested microstructure; H09 BLOCKED_DATA |

逐个特征的血缘与时点等级见 feature_field_lineage.csv，逐证券封存行情哈希见 security_source_lineage.csv。provider_disagreement / is_delisted 是事后审计字段，不进入预测器。市场状态 mom20/RV20 为可用性归一化代理，分母为两项同时可用的当日证券数；不是已认证全市场指数。

逐行流通市值由 raw close × volume / turnover 推断，未独立验证股本与单位；它只能作为规模代理。历史行业版本不存在，板块不能替代行业。公司行动通过 qfq 比率重锚不变性、历史换手重算及最近因子跳变/隐含股本变化剔除诊断，不能将其视作已完成权益账本认证。当日 ST 与停牌是厂商行记录代理；保留后来退市证券，不用终生 ST 或当前存续名单回填。未知终值、冲突与未来期限不填零。

完整分母见 `outputs/audits/population_by_year_board.csv`、`security_coverage.csv`、`label_coverage.csv`、`metrics/maturity_coverage.csv`。日线事件与冷却 episode 分别计数；缺报价身份也保留周末分母。没有独立行业控制的完整 Alpha 主张、严格 PIT、H09 与实际执行分别受阻，七项代理诊断仍可独立评估。
