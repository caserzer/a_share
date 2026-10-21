# D2 数据字典与实际支持范围

`schemas/*.schema.json` 是逐域字段语义合同；它们不是宣称现有代理表已满足全部PIT列，也不是JSON Schema自动认证器。事实层由 `FactStore.append` 强制时间、来源、修订链和质量规则；价格/股本/财务等规范分区是独立proxy交换层，缺认证列时不能直接送入严格层。

| 域 | 位置（外部缓存根下） | 单位/关键键 | 已实现与限制 |
| --- | --- | --- | --- |
| 身份 | identity/security_inventory.parquet | security_id；交易所/代码/上市事件UUID | 旧清单+本次官方增量，临时身份；跨代码连续性BLOCKED |
| 身份事实 | identity/facts.parquet | listed/code/exchange/board；effective_time | known_at=null，质量Historical-proxy，不回填今天简称和ST |
| 行情 | prices/{security_id}.parquet | date；OHLC=CNY/股，volume=股，money=CNY | 原始未复权；can_buy/can_sell=null，不从bar推断执行 |
| 股本 | shares/{security_id}.parquet | effective_date；total_shares=股 | 仅生效日代理；原中文和规范schema均支持，无首次可用证明 |
| 状态事件 | status/sz_name_events.parquet | effective_date、新旧简称 | 更名日期代理，缺原风险公告；沪市无日期记录单独盘点 |
| 财务供应商 | proxy/financials/*.parquet | SECUCODE/REPORT_DATE/NOTICE_DATE/UPDATE_DATE | 原字段不覆盖；财务查询报告期显式，不用修订日期冒充首次公开 |
| 估值供应商 | proxy/valuation/*.parquet | TRADE_DATE；PE/PB/PS与原股本 | 保留原始列，日期不认证供应商首次版本 |
| 行业 | proxy/industry/*.parquet | code/published/source_pdf_sha256/page | 19份历史表，缺口与陈旧不填当前分类；原PDF留原缓存 |
| 公司行动 | proxy/corporate_actions/*.parquet | 原供应商事件列 | 分页/all/probe有重叠，读取总行数不是独立事件数；未作完整持仓账 |
| 宏观 | proxy/macro/*.parquet | 原观察日期 | 未认证首次发布与修订，预测/概念未擅自补齐 |
| 真实财务版本例 | vintages/facts.parquet | 一个附注字段、两个版本、元 | PIT-reconstructed；原年报/更正+索引字节SHA+页码；独立人工未审核 |
| 桥接 | bridge/security_month_labels.parquet；security_month_labels_expanded.parquet | date/instrument | 前者为旧兼容投影，后者覆盖新增D2临时成员；旧收益原样，新增成员的旧/新收益均UNKNOWN |
| 日历 | calendar/sessions.parquet | date | 2,281个已核验旧窗口交易日；不把2026-05-29后计划日历冒充已核验数据 |

所有版本事实保留 event_time、effective_time、known_at、source_observed_at、ingested_at、vendor_revision_time（未知为null）、source_uri、source_path、source_sha256、unit、original_version、transform_sha256、quality_tier、publication_evidence、reconstruction、supersedes。异类标量以JSON编码存Parquet，读取恢复类型；源字节哈希与表级哈希分别校验。

`PIT-certified` 仅接受原始披露/归档证据；`PIT-reconstructed` 另需确定性重建步骤。`Historical-proxy` 必须显式请求，严格默认拒绝；`UNKNOWN/BLOCKED` 不作为可输入数据。冲突保留记录并返回UNKNOWN；修订必须保留同一逻辑事实的前驱及更晚可用时间。

Historical as-of 依据历史可核验的可用时间；Archived as-of 还要求本系统已采集保存。今日下载旧年报可以支持历史重建，但不能生成十年前系统已归档的假记录。仅日期的公告用下一已核验交易日09:30可用；日线用收盘后可读。日线和股本查询会返回实际观测/生效日期，计算同日市值必须核对日期及财务可用版本。

LabelBuilder 输出 KNOWN/CENSORED/UNKNOWN，包含 origin、entry、target、exit、mature_at、return_policy、value、loss_below_minus20、mfe、mae、原因及质量。未知不是0。20%阈值用十进制比较；毛现金股息不再投资；若退出后才实际到账，executable标签等待支付再成熟。MFE/MAE以收盘权益标记并包含入场和实际退出；不是日内极值。复杂权益及终止结算尚无完整实现材料，保持精确阻断。


## D2 v2 补数扩展（2026-10-21）

- `normalized/securities.parquet`：保留 v1 ID，追加身份；`bse_listing_proxy` 与原 `listing_date` 分开，精选层日期不能覆盖实际 BSE 市场起点；5 条原始离场日期另存证明。
- `observations/{security_id}.parquet`：供应商所有原始数值及 SHA；不按表现删冲突行。`prices/` 为按字段核对的单日结果，`*_conflict=true` 的字段为未知。成交额容许 0.51 元表示精度差，量为股、换手为比例。
- `vendor_trade_status` / `vendor_is_st`：供应商回溯状态，不代表完整停复牌公告、开盘排队或成交证明；零成交停牌留价不可当作真实交易。`can_buy/can_sell` 默认未知，只有单独原始证据能重建阻断。
- `shares/`：按生效日期保存总股本等观察，同日不同股数阻断；已取得上市前记录不意味着彼时属于 A 股。北交所旧代码/NQ 股本按组织别名对接，仅属 proxy。
- `corporate_actions.parquet`：现金及送转数值每股化；`payment_date` 缺失保持 NaT。`rights_issues.parquet` 保存认购价与缴款窗口，实际参与/到账另需证据。原始表中事后 10/30 日涨跌幅未进入特征表。
- `vendor_valuations.parquet`：PE/PB/PS/PCF 的供应商值，财务分母版本未证明，不是已知财务分母重建估值。
- `code_intervals.parquet`：496 条北交所旧新代码区间，起点含、终点不含；与上市成员区间独立。六只试点 2025-05-06，其他 242 只 2025-10-09。
- `reviewed_facts.parquet`：v1 两条财务版本 + 本轮 23 条逐项原文核对；其中 5 个财务值使用 `financial:original_*:2025-12-31`，只承诺原始披露值，不声称已取得全部更正。独立人工核对尚未完成。
- `financials/original_extraction_candidates.parquet` 位于私有采集工作树：批量候选须单位、列、年度复核，未混入严格接口。
- `legacy_bridge_with_v2_quote_availability.parquet`：旧桥表所有列逐值保留，只追加 v2 原始收盘可用性；不把 raw 价格代入旧复权收益。
- `normalized_manifest.json`：规范化分区、代码与配置 SHA；`release.json` / `release_verification.json`：独立复制快照和验证收据。`archived` 不允许回放为采集前已存在。


## D2-v3新增交换层

- `status_facts.parquet`：原文事件、六个时间字段、源SHA及转换SHA；日期级日内状态不当作午夜已生效。部分事件不认证持续每日状态。
- `securities.parquet`：保留v2元数据日期，另列唯一原文摘牌日；冲突不静默选取，原上市身份冲突不清空。
- `original_distribution_contracts.parquet`：登记、除息、计划现金/股份交付及明确每股毛额。未提及的比例保持空值；实际支付和区间完整性独立标记。
- `retired_equity_links.parquet`、`merger_rights_contracts.parquet`：原文代码对应与有理数换股比例，非真实交付或终值；`ocr_retired_equity_candidates.parquet`独立存储未核候选。
- `financial_version_chains.parquet`：稳定身份、报告期、全文/摘要/更正公告类别、原始版本ID、前驱集合和同日排序歧义；不凭索引认证数值。
- `financial_original_value_candidates.parquet`：原页、单位、原文字面值、候选可知日和版本，质量为UNKNOWN/BLOCKED。`financial_reviewed_facts.parquet`仅追加独立的reviewed_reported字段及明确supersedes链。
- `full_monthly_bridge.parquet`：证券×完整月份；所有旧列逐值保留，v3成员与原点前可知的原文事件数单列。历史重建不等于实际系统归档。
- `labels/<horizon>/<policy>.parquet`：UNKNOWN/CENSORED独立、值为空，完整执行与权益门槛分别保留。`scheduled_open_price_proxy`仅诊断且屏蔽停牌留价和跨摘牌终点，不是严格标签或退市财富。
- `D2V3Dataset`：必须指向独立封存版；逐分区验证SHA，历史/归档模式分开，完整状态不足返回UNKNOWN，原始事件另由latest_status_event读取。

## D2-v4 身份连续性与退市披露扩展

- `security_id_redirects.parquet`：三组有实施原件证明的连续上市代码变更；保留旧稳定ID，弃用的重复ID另列，不按相同org_id自动合并。有效日期、保守可知时刻、原件SHA与核验页可追溯。
- `securities.parquet`：5919个暂定规范身份；`metadata_instrument_v3`、`metadata_delist_date_v3`保留旧观察，三组代码变更不再视为证券退市。身份纠错不认证全市场总体和每日资格。
- `code_intervals.parquet`：上述三组A股旧、新代码区间，终点不含；与v2北交所代码区间分开。`boundary_known_at`控制严格as-of，不能以当前代码倒填旧日期。
- 三条规范化行情按旧码截至生效前、新码自生效日起选取，`code_interval_source_instrument`保留真实输入别名。过期代码留价、新代码回填的旧日期不重复拼入；不插值补缺，不据正成交量设置可成交标记。
- `alias_facts.parquet` / `retired_equity_links.parquet`：85个证券主体的退市披露代码与原件关联；这是披露别名，不是可执行交易代码，也不证明账户股份已经交付。
- `status_reviewed_facts.parquet` / `code_change_facts.parquet`：两条扫描原件摘牌事实和三条代码变更事件，分别保留生效、披露、采集时间；不外推持续ST/停复牌状态。
- `financial_version_chains.parquet`：含原v3记录、1181条已核退市身份下披露及两份独立巨潮关联年报；规范身份、报告期、同日歧义和前驱集合保持可审计。`known_at`不早于需依赖的身份桥接可知日。
- `financial_reviewed_facts.parquet`：新增15条明确报告版本的原页核验值，不声明已取得所有修订。2018年补发报告于2020年披露，不向2019年末泄漏。
- `full_monthly_bridge.parquet`：所有旧桥接行与原列保留，新增 `v4_canonical_security_id`、`v4_retained_legacy_alias_row`、`v4_provisional_member`；旧别名行不重复计入规范总体。525762个规范候选证券月，不等于PIT认证总体。
- `D2V4Dataset`：逐分区SHA验证；规范身份查询、报告值、代理行情、严格标签与历史/归档查询分开。完整其他域可显式传入不可变v3依赖，代理整体不得冒充严格资格。
# D2-v5 追加字段：前复权价格推断

本节仅改变用户指定的新收益推断口径，既有原始行情、严格权益标签和 PIT 特征字段的定义保留。证券总体仍采用 v4 暂定候选总体，不升级为认证全市场。

| 字段 | 定义 |
|---|---|
| `qfq_open/high/low/close` | 未复权价除以新浪有效日期对应的 `qfq_divisor`，不取两位小数 |
| `factor_effective_date` | backward-asof 匹配到的因子日期；早于首条因子的价格保持缺失 |
| `factor_source_sha256` | 原始前复权因子响应的 SHA256 |
| `factor_series_instrument` | 实际采用的因子代码；与原始报价代码可因已记录的代码变更而不同 |
| `factor_chain_id` | 可比较的复权尺度链；未完成尺度核对的跨链收益保持未知 |
| `factor_alias_scale` | 同身份两代码在整个共有区间的阶梯因子曲线核对后得到的固定尺度比 |
| `entry_date/exit_date` | 决策后首个观测到正成交量的开盘，以及目标日或之后的首个观测开盘；入场必须早于目标日 |
| `value` | `exit_qfq_open / entry_qfq_open - 1`，仅在 `KNOWN_INFERRED` 时非空 |
| `raw_price_return` | 相同入场与出场日期的未复权价格变化，用于除权影响比较 |
| `mature_at` | 推断出场日 09:30，北京时间；训练/回放必须检查此时刻早于评分时点 |
| `loss_below_minus20` | 前复权推断收益是否严格小于 −20% |
| `mfe/mae` | 持有期间完整前复权收盘路径、初始零收益与出场开盘收益的最大/最小变化；不包含出场日收盘 |
| `path_missing_sessions` | 路径缺失/冲突或跨未衔接尺度的日数；端点收益可知而路径指标仍未知 |
| `execution_assumed` | 始终为 true，表示观测价格上的推断，没有证明实际成交 |
| `return_policy/effective_policy` | 原三个请求名均明确映射到同一前复权价格推断方法 |
| `status` | `KNOWN_INFERRED`、`UNKNOWN`、`CENSORED`；不改变旧严格结果的状态 |

完整月度桥表保留 v4 全部原列，追加 `v5_qfq_{6m/20d/60d/120d}_{value/status/reason/...}`。前复权因子和价格为回溯代理，不自动进入认证 PIT 特征。认证市值与股本计算继续使用未复权行情。


`D2PriceInferenceDataset.price_and_corporate_action_path(policy="qfq")` 返回的标准 `open/high/low/close` 为前复权价，并显式附带 `raw_open/raw_high/raw_low/raw_close`。底层交换分区保留原 OHLC 与独立的 `qfq_*` 列。
