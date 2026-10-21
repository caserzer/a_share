# 质量指标、下游准入与阻断范围

执行日：2026-10-21，Asia/Shanghai。质量门槛在 P0 冻结；不训练 Alpha，不覆盖 EP01—EP29。

质量门槛见冻结配置。READY要求原始版本、完整分母、源哈希/快照重建、独立人工核验及零泄漏共同满足。代码能跑不发READY。

| domain | strict | available | reason |
| --- | --- | --- | --- |
| identity | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 历史成员/跨代码连续性/官方历史对账未闭合 |
| raw_prices | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 首次报价版本未认证；新增板块和2026-05-29后OHLCV未补齐 |
| status | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | ST/停复牌/整理期/价格限制/可执行开盘缺逐日公告链 |
| shares | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 有生效日代理，缺首次披露版本与全证券覆盖 |
| corporate_actions | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 缺完整实施、支付、股份权利及终止结算持仓账 |
| financials | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 仅一个附注字段原始/更正重建；非完整财报覆盖 |
| valuation | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 价格、股本、财务分母首次版本未全闭合 |
| industry | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 历史快照存在；完整历史分类与版本认证不足 |
| macro_forecasts | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 宏观首次发布/修订及预测原件未认证 |
| labels | BLOCKED | PARTIAL_PROXY_OR_ONE_FIELD_RECONSTRUCTION | 可执行时点/权利账阻断，不能借前复权代理充数 |

| 强制指标 | 本次结果 | 分母和限制 |
| --- | --- | --- |
| 历史全市场元数据/退市对账 | BLOCKED | 临时5,540条，非认证全市场 |
| 原始行情覆盖 | 4,825只、9,091,310条 | 各板块年份及代理分母逐格列示 |
| ST/停复牌覆盖 | 深市7,398更名事件，完整日状态0认证 | 不能将0认证解释成0次停牌 |
| 股本冲突/缺失 | 冲突日期0，非法行0；临时清单缺源943只 | 仅现存4,597个文件；首次版本仍未认证 |
| 退市最终权益未知率 | 100%未认证 | D1范围229只退市证券；不是断言其权益为0 |
| D1到期6月价格代理 | 256,637已知 / 2,411缺失 | 另22,926尚未成熟，按旧截止 |
| D2总收益/执行收益 | 0获准、原点条件下全部UNKNOWN/CENSORED | 不将其填入模型 |
| 财报原版/首次时间 | 1个字段、2个版本可重建 | 不外推完整三表覆盖；小时未知用次日规则 |
| 历史行业版本 | 19份可追溯代理快照 | 认证全市场历史版本覆盖仍UNKNOWN |
| 泄漏测试 | 见adversarial_validation.json及tests.json | 同时包含合成机制与真实财报回放 |
| 独立人工核查一致率 | UNKNOWN，0独立人工样本 | 6条机器辅助时间线不冒充人工 |
| 原始快照重建 | SHA/Parquet与as-of往返回放 | 验证报告列出实际分子分母 |

各域×板块×年份详见 `quality_by_domain_year_board.csv`；各字段×证券×年份×板块见压缩矩阵。科创板/北交所开市前NOT_APPLICABLE；开市当年的起点按真实日期，不能把全年当作已经上市。2017之前不扩展。本次2026-05-30至2026-10-21未复权OHLCV、状态与权益不是已验证数据，日历不自动生成事实。

关闭受阻域的补齐条件：可验证的历史成员总清单、真实状态公告区间、公司行动与退市现金/股份结算、首次财报原件和修订链、历史分类、原版宏观/预测及独立抽查。现有授权下已进行了缓存普查、官方名单与原文可达性调查；不作新增付费订阅或权限申请。受阻裁决仅对应当前证据范围，后续可以新增D2版本，不覆盖本版。

允许：源核验、显式proxy诊断、原财务样例as-of验证、补录原文及契约测试。禁止：认证全市场特征/标签训练、正式Alpha验证、部署、把D0/D1旧分数当D2表现。
