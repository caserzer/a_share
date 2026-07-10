# EP20A 论文血缘、数据与复制合同报告

## 一页结论

- 决策状态：`20A_preoutcome_contract_ready`
- residual primary：`C3_RESMOM_R3_BOARD_ADAPTATION`
- project adaptation reachable：`true`
- forward beta test reachable：`true`
- exact replication reachable：`false`；它不是 20A 成功的必要条件。
- 冻结时间：`2026-07-10T15:21:02.424911Z`
- outcome 字段读取数：`0`；selection/tuning 授权读取数：`0`。
- 阻断原因：`none`

EP20 的 primary objective 是可部署的正 beta，不要求 matched alpha。

Scale matching 只解释收益来源，不是正 beta 的淘汰门。

2017–2026-05 的本地历史已经被 topic 反复消费，只能提供设计证据；唯一可信支持来自 post-freeze forward。

## 论文与公式血缘

本地缓存并通过内容校验的 allowlisted full-text/appendix 为 `9/11` 份；人工核验后的 formula registry 有 `11` 行。Material waiver source 为：`ma_portfolio_timing_full_paper、trend_china_full_working_paper`。这两项只记录“人工公式核验已完成但远端正文暂未缓存”，没有本地 full-text/hash claim，也不提高 exact replication claim。每个公式行仍绑定 source、page/equation、lag、warm-up、missing、tie 与 weighting 实现选择。20A 不以 requirement 摘要循环证明论文公式。

## 数据、denominator 与复制上限

U_project 的 top-N 截面不能冒充论文的全 A 股 U_paper。

全市场 qfq 文件只证明价格侧候选可用，不能替代宽截面 PIT market-cap、E/P、historical industry、risk-free 或 CH-3 vintage。所有本地历史都是 design-contaminated；历史结果未来只可用于设计，不可升级为 support。

## Exact 与 adaptation 路由

| gate_id                          | status   | highest_allowed_role         | fallback_arm                  |
|:---------------------------------|:---------|:-----------------------------|:------------------------------|
| wide_qfq_status_gate             | pass     | U_paper price-side candidate | nan                           |
| wide_pit_market_cap_gate         | fail     | exact size capable           | nan                           |
| pit_ep_timing_gate               | fail     | Trend/value exact capable    | C2_TRENDPV_RAW_ADAPTATION     |
| historical_pit_industry_gate     | fail     | industry exact               | C3_RESMOM_R3_BOARD_ADAPTATION |
| board_proxy_gate                 | pass     | R3 control                   | C3A_RESMOM_R2_MARKET_ONLY     |
| risk_free_vintage_gate           | fail     | excess-return exact          | C3_RESMOM_R3_BOARD_ADAPTATION |
| ch3_factor_vintage_gate          | fail     | CH3 exact                    | C3_RESMOM_R3_BOARD_ADAPTATION |
| paper_exact_history_support_gate | fail     | paper diagnostic calendar    | nan                           |
| project_adaptation_gate          | pass     | 20B/20C specification        | nan                           |
| forward_contract_gate            | pass     | forward beta test            | nan                           |
| cnn_training_support_gate        | fail     | 20F evaluable                | nan                           |

Exact route 失败不等于 project adaptation 失败。Residual primary 只由 pre-outcome board availability 决定；board gate 失败时机械回退 R2，primary family 仍固定为 2，不能按收益切换。

## 2025 板块代理

EP19 2025 板块数据是冻结的 multi-label concept-board proxy，不是 historical PIT industry。

原始 index `458` 行、member `43468` 行、去重后 board columns `240`，U_project overlap rate `0.9895`。Snapshot age 固定为 `decision_month - 2025-01`；未来更新 snapshot 必须建立新 cohort，旧新 cohort 不得混池。

## 执行、NAV、成本、容量与风险

每个 arm 只有一条 continuous no-injection NAV ledger；blocked exit 必须继续占用真实资本。

Primary return 是固定 calendar-month、cash-inclusive、full-capital、net NAV return。Blocked buy 留现金；blocked exit 继续 mark 并占资本；delisting recovery 不可得时使用 -100% conservative resolution。Attempted/realized turnover、ADV20、transfer fee、break-even multiple、daily-NAV drawdown 与集中度口径均已 pre-outcome 冻结。

EP19 daily B2 reference 不等于 EP20 B2 month-end adaptation；EP19 effect size 不得直接转移。

C5R2 只可在同一 month-end B2 candidates 内计算 linear p70，阈值相等者删除，被 trim 权重留现金；不得跨日期估计，也不得继承 19B3 的绝对阈值或收益。

## Power、CNN 与 forward

MDE 的证据单位是 distinct complete decision months。Effect=2%、long-run monthly volatility=8%、Holm worst-case alpha=2.5%、power=80%，得到 `n_required_primary=126`。6–11 月只是 interim；12–125 月只是 minimum directional evidence，不是 confirmatory support；达到 126 月才可评价 Holm/HAC、simultaneous lower bound 与 early/late direction，日历下限预计约 2037 Q1。

CNN 必须有严格时间分离的 72/18/24 个月。任何支持门不足均固定为 `cnn_underpowered_not_evaluable`，不能据此关闭日频 OHLCV 主线。

## 授权边界

20A 没有评价任何信号收益，也没有授权 20B 执行、policy、optimization 或 deployment。

20A 只授权生成 `requirement_20b_trendpv_residual_momentum_design_and_replication_diagnostic.md`；其执行仍为 false。
