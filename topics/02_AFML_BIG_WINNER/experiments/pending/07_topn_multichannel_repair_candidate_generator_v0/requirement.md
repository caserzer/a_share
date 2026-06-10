# 需求：Top-N 多通道修复事件候选生成器 V0

## 1. 背景

本实验是 `04_high_recall_repair_event_candidate_generator_v0` 在新 denominator 上的重写版。

上游实验已经给出三个关键约束：

1. `05_pit_topn_400_100_universe_v0` 已构建 PIT Top-N 400/100 universe，但由于部分股票数据缺失，需接受它是 `available_source_topn_candidate`，不是精确全市场 top400/100。
2. `06_rerun_02_reverse_lifecycle_on_topn_universe_v0` 已在该 universe 上重跑 02 reverse lifecycle profile，并可冻结为新的 big-winner episode denominator。
3. `03_observable_anchor_event_contract_v0` 说明单一 E_S3 observable event 不能作为 universal entry contract，但可作为候选生成器中的一个确认 / 持续性通道。

因此，本实验不再使用旧 04 的固定市值 denominator，也不把 E0 setup 与后续修复事件混成一个单一 canonical event。目标是在 06 冻结 denominator 上，构建一个高召回、多通道、可审计的候选事件生成器，为后续模型、meta-label 或事件合约实验提供候选池。

## 2. 目标

在 06 冻结的 Top-N/proxy big-winner episode denominator 上，生成一个 point-in-time、observable、next-open executable 的多通道 repair / continuation candidate event set，并回答：

1. 多通道事件 union 能否显著提高 big-winner episode 的早期覆盖？
2. 各通道分别贡献多少 recall、unique recall 和 event density？
3. 高 recall 是否主要来自不可接受的事件密度、单一 regime 或单一 board？
4. 在 train / validation / robustness 上，候选事件覆盖是否稳定？
5. 与旧 04 denominator 上的结果相比，before-first-50pct bridge recall 是否有实质改善？

本实验只验证候选生成器是否适合作为下一阶段输入，不授权交易入场信号，不构建模型，不做组合回测。

## 3. 非目标

本实验明确不做以下事情：

1. 不生成 universal entry contract。
2. 不宣称任何单一事件通道是可交易入场点。
3. 不训练 primary model、meta model 或 ranking model。
4. 不做 portfolio backtest、收益曲线或仓位模拟。
5. 不用未来的 MFE、episode high、first-50pct touch 或 near-winner outcome 构造事件特征。
6. 不移动 06 已冻结的 split 边界。
7. 不在 validation / robustness 上调参。
8. 不把 E0 setup context 计入 headline event density 或 event precision。
9. 不因 risk_off 表现差而从 headline denominator 中排除 risk_off episode；risk_off 只能作为分层诊断或专门通道处理。
10. 不只在 target episode window 内生成事件；target episode 只能用于事后 link、recall 和 label 评估。

## 4. 上游输入

实现必须读取并记录以下上游 artifact：

1. `06_rerun_02_reverse_lifecycle_on_topn_universe_v0` 的 manifest、episode reference、denominator summary、split / regime / board 诊断和 sequence dominance 输出。
2. `05_pit_topn_400_100_universe_v0` 的 universe manifest 和 coverage audit，用于传播 `available_source_topn_candidate` caveat。
3. 01 基础日频 PIT 数据：qfq OHLCV、成交额、换手率、benchmark / regime 所需日频数据。
4. `03_observable_anchor_event_contract_v0` 的报告和表格，只作为事件通道设计证据。
5. 旧 `04_high_recall_repair_event_candidate_generator_v0` 的 manifest、报告和表格，只作为 baseline recall / density 对照。

如果 06 manifest 的最终状态不是 `topn_reverse_lifecycle_sequence_supported_universal_dominance`，本实验必须停止并输出 `topn_multichannel_candidate_generator_input_blocked`。

旧 04 density baseline 必须从 artifact 读取，不得硬编码：

1. 优先读取 `04_high_recall_repair_event_candidate_generator_v0/outputs/manifests/run_manifest.json` 中的 `gate_summary.setup_inclusive_events_per_instrument_year_mean`、`gate_summary.setup_inclusive_events_per_instrument_year_p95`、`gate_summary.reclaim_based_events_per_instrument_year_mean` 和 `gate_summary.reclaim_based_events_per_instrument_year_p95`。
2. 同时读取 `outputs/publishable/tables/event_density_audit.csv`，用于按 union / split / year 对照旧 04 density distribution。
3. 07 必须把读取到的旧 04 density baseline 写入 `topn_input_manifest_audit.csv` 和 `topn_vs_04_baseline_density_comparison.csv`。
4. 如果旧 04 density baseline 无法读取，07 仍可运行，但必须使用预声明绝对 density 上限，并在 report 中标记 `old_04_density_baseline_unavailable`。

05 的 `topn_universe_candidate_panel_blocked` 不能被静默忽略。只有同时满足以下条件，07 才能接受 05 作为输入：

1. 06 manifest / report 明确记录 `topn_candidate_gap_accepted = True`。
2. 06 manifest / report 明确记录 `universe_precision_status = available_source_topn_candidate_gap`。
3. 07 manifest、report 和所有 headline table 都携带同一 universe caveat。
4. 07 不声称结果代表 exact historical top 400/100，只能声称代表当前可审计数据源上的 PIT Top-N 400/100 proxy。

## 5. 固定 denominator

Headline denominator 必须使用 06 冻结的 Top-N/proxy big-winner episode reference。

当前预期 denominator：

| split | big-winner episodes | density per 100 universe-years |
|---|---:|---:|
| train | 1,290 | 71.90 |
| validation | 445 | 48.14 |
| robustness | 758 | 83.86 |
| all | 2,493 | 68.82 |

实现不得把这些数字硬编码为事实通过条件；必须从 06 manifest / output 读取并做一致性审计。如果读取到的 denominator 与报告数字不一致，必须在 report 中列出差异并降级为 input audit issue。

每个 target episode 至少需要携带：

1. `target_episode_id`
2. `symbol`
3. `episode_low_date`
4. `episode_high_date`
5. `mfe_120`
6. `episode_split`
7. `board`
8. `regime`
9. `universe_membership_source`
10. `universe_precision_status`

如果 06 episode reference 已提供 `first_50pct_touch_date` 或 `first_100pct_touch_date`，07 必须以 06 字段为 evaluation 权威口径。07 可以从 episode low 之后的 qfq high / close 路径重算 first-touch 日期，但只能用于一致性校验，不能覆盖 06 字段，不能作为 event feature。

如果 06 未提供 first-touch 字段，07 可以按 06 episode 的 qfq 路径派生 evaluation 字段，但必须在 `topn_first_touch_reconciliation_audit.csv` 中标记 `source = derived_in_07`。如果 06 字段与 07 重算结果不一致，必须列出 symbol、episode、06 value、recomputed value、difference_sessions 和 reconciliation_status。

## 6. 事件生成全集

事件必须先在完整 Top-N/proxy evaluated instrument-days 上生成，然后再事后 link 到 target episodes。

事件生成全集至少满足：

1. 覆盖 06 denominator 使用的全部可评估 Top-N/proxy instrument-days，而不是只覆盖 big-winner symbols 或 target episode windows。
2. 包含 target episode 内事件、target episode 外事件、non-target symbols 事件和后验失败事件。
3. event density 的 denominator 使用同一批 evaluated instrument-days / universe-years。
4. event precision 的 label universe 使用 canonical events，而不是 target episodes。
5. episode recall 只在事后把 canonical events link 回 06 target episodes。

禁止以下实现：

1. 先读取 target episode window，再只在这些 window 内寻找事件。
2. 先知道 big-winner episode，再向前搜索最优触发点。
3. 只输出 capture target 的事件，而丢弃 non-target / failed events。
4. 用 target episode 的 `episode_low_date`、`episode_high_date`、`first_50pct_touch_date` 参与事件生成或 channel threshold 选择。

必须输出 `topn_event_generation_universe_audit.csv`，证明 event generation universe 与 06 evaluated instrument-days 的关系，并列出 excluded instrument-days、excluded symbols 和 exclusion reasons。

## 7. 时间与可执行性约束

所有事件必须遵守以下时间定义：

1. `event_t0_date` 是事件被日收盘数据确认的日期。
2. `event_executable_date` 默认是 `event_t0_date` 后的下一可交易日。
3. 如果下一可交易日缺少 open / tradable 状态，事件必须标记为 not executable，并进入 completeness audit。
4. `event_split` 按 `event_t0_date` 归属。
5. `episode_split` 按 06 episode definition 归属。
6. headline recall 以 `episode_split` 汇总。
7. event precision / density 可同时按 `event_split` 和 `episode_split` 汇总，但必须明确标注。

任何使用 `event_t0_date` 之后价格、成交、排名或 outcome 的字段构造事件，均视为未来函数并必须失败。

## 8. 事件通道

实现至少包含以下通道。每个通道必须保留独立 event instance，并在 canonical union 中保留 `channel_id`、`channel_family`、`event_t0_date`、`event_executable_date` 和 as-of 特征快照。

### 8.1 E0：setup context

E0 只定义候选环境，不作为 headline event。

可用 setup context 包括：

1. drawdown / distance-to-high context
2. liquidity / turnover availability context
3. universe membership context
4. market regime context
5. board context

E0 可以用于分层、过滤或通道前置条件，但必须单独报告其覆盖率和过滤影响。E0 不得计入 event density、event precision 或 channel recall contribution。

### 8.2 E1：early EMA60 repair channel

捕捉 06 中 S1 repair-like sequence 对应的早期均线修复信号。

候选定义必须是收盘后可观测，例如：

1. close reclaim EMA60
2. distance-to-EMA60 从负转正或显著收敛
3. EMA60 reclaim 后不立即失效的短窗口确认

该通道必须报告 false-repair 率，因为 06 中 EMA60 repair-looking controls 的 false repair 率较高，不能单独作为强信号。

### 8.3 E2：money / VWAP repair confirmation channel

捕捉成交额、换手、VWAP 或成交强度修复。

可选 as-of 特征包括：

1. amount / turnover rank 的短期改善
2. VWAP reclaim 或 close-vwap relation 修复
3. price repair 与 liquidity repair 同日或短窗口共振

不得使用未来窗口内的累计成交改善作为触发条件。

### 8.4 E3：rank persistence channel

捕捉 03 中 E_S3 和 06 中 S3 所提示的 rank jump / rank persistence 结构。

该通道必须区分：

1. rank jump first observed date
2. rank persistence confirmed date
3. persistence window length

如果 persistence 需要多日确认，`event_t0_date` 必须是确认完成的日期，而不是 jump first date。

### 8.5 E6：continuation discriminator channel

捕捉 06 中 S6 显示出的更强 continuation / dominance 特征。

该通道允许更晚触发，但必须报告 lead time：

1. 相对 `episode_low_date` 的天数
2. 相对 `first_50pct_touch_date` 的天数
3. 相对 `episode_high_date` 的天数

如果 E6 主要在 first-50pct 之后出现，则只能作为 continuation / confirmation candidate，不能计入 before-first-50pct bridge success。

### 8.6 False-repair diagnostic channel

必须构造 false-repair 诊断，不得只保留幸存事件。

至少报告：

1. as-of repair event 后 10 日 failure rate
2. as-of repair event 后 20 日 failure rate
3. clean baseline match coverage
4. false-repair rejector 对 target recall 的损失
5. rejector 对 event density 的下降

如果 clean baseline match coverage 低于 gate，本实验不得做 precision superiority claim，但仍可在 recall gate 通过时发布 candidate generator。

### 8.7 Regime / board stratified channels

必须按以下维度输出分层诊断：

1. `risk_on`
2. `transition`
3. `risk_off`
4. `main_board`
5. `ChiNext`
6. 其他 board，如果 denominator 中存在

允许预先声明 risk_off 或 ChiNext 专门通道，但必须满足：

1. 阈值在 train 上确定。
2. validation / robustness 只评估，不调参。
3. headline denominator 仍包含所有 regime / board。
4. report 同时展示全局阈值与分层阈值的差异。
5. 如果专门通道进入 recommended union，其事件必须计入 headline event density、channel density、density drag 判定和 execution / label gate，不得绕过全局密度约束。

## 9. Canonical event union

同一股票同一交易日可能被多个通道触发。

输出必须同时保留：

1. `event_instances`：一行一个通道触发。
2. `canonical_events`：同一 symbol / event_t0_date 聚合后的一行 canonical event。

Canonical event 至少包含：

1. `canonical_event_id`
2. `symbol`
3. `event_t0_date`
4. `event_executable_date`
5. `triggered_channels`
6. `primary_channel`
7. `channel_count`
8. `asof_feature_snapshot_hash`
9. `event_split`
10. `episode_link_status`

Primary channel 只能用于排序和归因显示，不得覆盖原始 channel instance。

Recommended union 的 inclusion / exclusion 规则必须在运行前确定：

1. channel inclusion、channel ordering、primary channel priority、density cap 和 rejector 阈值只能来自 predeclared config 或 train split。
2. validation / robustness 只能用于评估，不得反向改变 recommended union。
3. 如果 report 展示 post-hoc exploratory union，必须标记为 diagnostic-only，不得作为 headline decision 依据。

## 10. Episode capture 规则

一个 target episode 被 capture，需要满足：

1. event symbol 与 episode symbol 相同。
2. event_t0_date 在 episode evaluation window 内。
3. event_t0_date 不晚于指定 capture cutoff。
4. event 使用的全部特征在 event_t0_date 收盘时可观测。

除非输出明确标记为 pre-low diagnostic，所有 headline capture window 的下界必须是 `episode_low_date`，即 `event_t0_date >= episode_low_date`。早于 episode low 的 setup / repair-like event 不能计入 headline episode capture、before-first-50pct recall 或 bridge recall。

必须至少计算以下 capture windows：

1. `low_to_high`
2. `low_to_first_50pct`
3. `low_plus_20`
4. `low_plus_30`
5. `low_plus_60`
6. `low_plus_120`
7. `before_first_50pct`
8. `before_episode_high`

Headline bridge recall 使用 `before_first_50pct`。如果 episode 没有可评估的 `first_50pct_touch_date`，必须进入 denominator exclusion / missing label audit，不得静默丢弃。

窗口边界必须在 report 和 audit 中明确：

1. `low_to_high`：`episode_low_date <= event_t0_date <= episode_high_date`。
2. `low_to_first_50pct`：`episode_low_date <= event_t0_date <= first_50pct_touch_date`。
3. `low_plus_N`：`episode_low_date <= event_t0_date <= episode_low_date + N trading sessions`。
4. `before_first_50pct`：`episode_low_date <= event_t0_date < first_50pct_touch_date`。
5. `before_episode_high`：`episode_low_date <= event_t0_date < episode_high_date`。

必须拆分两个不同口径：

1. `capture_any_event_before_first_50pct`：episode 在 first-50pct 之前至少有一个 canonical event，不要求该 event 自身未来达到 +50%。
2. `bridge_positive_event_before_first_50pct`：episode 在 first-50pct 之前至少有一个 canonical event，且该 event 从 executable basis 往后 120 日 MFE 达到 +50%。

旧 04 的 `35.2%` before-first-50pct bridge baseline 属于 `bridge_positive_event_before_first_50pct` 口径，不得拿来和 `capture_any_event_before_first_50pct` 直接比较。

`bridge_positive_event_before_first_50pct` 必须处理 forward-120 右删失：

1. 只有 `event_executable_date` 后 120 个交易日标签完整的 event，才可参与 bridge-positive numerator 判定。
2. forward-120 不完整的 event 必须标记 `bridge_label_status = forward_120_incomplete`，不得静默当作未命中。
3. 如果某 episode 在 bridge window 内至少有一个 label-complete event，则 bridge-positive 判定只基于 label-complete event，label-incomplete event 单独计入 audit。
4. 如果某 episode 在 bridge window 内有 event，但全部 event 都 forward-120 不完整，则该 episode 从 bridge-positive denominator 中排除，并以 `bridge_forward_120_incomplete` 写入 exclusion audit。
5. 如果某 episode 在 bridge window 内没有任何 event，且自身 first-touch label 完整，则它保留在 bridge-positive denominator 中，计为未捕获。

## 11. 核心指标

### 11.1 Episode-anchored recall

必须输出：

1. capture-any-event recall
2. bridge-positive-event recall
3. per-channel recall
4. unique recall
5. incremental recall over previous channels
6. channel overlap matrix
7. before-first-50pct bridge recall，必须同时给出 any-event 与 +50-positive event 两个 basis
8. low+20 / low+30 / low+60 / low+120 recall，必须同时给出 any-event 与 +50-positive event 两个 basis
9. recall by split / regime / board

所有 recall 表必须显式列出 numerator、denominator、excluded_count 和 exclusion_reason。

### 11.2 Event-anchored precision

必须输出：

1. event count
2. executable event count
3. event_big_winner_120d_rate
4. near_winner_rate
5. confirm_20
6. failure_10
7. forward_20_return
8. forward_60_return
9. label completeness rate

这些是 event-anchored 指标，不得与 episode-anchored recall 混写。

### 11.3 Event density

必须输出：

1. total events per 100 universe-years
2. canonical events per 100 universe-years
3. channel event density
4. events per captured target episode
5. density by split / regime / board
6. E0-filtered universe-years

如果某通道贡献的 incremental recall 很低但密度很高，report 必须标为 density drag。

### 11.4 Lead time

必须输出：

1. event_t0_date 相对 episode_low_date 的分布。
2. event_t0_date 相对 first_50pct_touch_date 的分布。
3. event_t0_date 相对 episode_high_date 的分布。
4. before-first-50pct 的提前天数分布。
5. late continuation event 的占比。

## 12. 通过 / 阻塞标准

### 12.1 输入 gate

全部满足才可继续：

1. 06 manifest 状态为 `topn_reverse_lifecycle_sequence_supported_universal_dominance`。
2. 06 denominator 可读取，且 target episodes > 0。
3. train / validation / robustness 均存在 target episode。
4. 05 / 06 universe caveat 可读，并写入本实验 manifest。
5. 如果 05 decision 为 `topn_universe_candidate_panel_blocked`，必须同时读取到 06 的 `topn_candidate_gap_accepted = True` 和 `universe_precision_status = available_source_topn_candidate_gap`。
6. 事件生成全集可覆盖 06 evaluated Top-N/proxy instrument-days，并可生成 `topn_event_generation_universe_audit.csv`。
7. 事件数据源具备 PIT as-of date 字段或等价审计字段。

任一失败，输出 `topn_multichannel_candidate_generator_input_blocked`。

### 12.2 Recall gate

候选生成器通过高召回 gate，需要同时满足以下硬条件。

`0.55 / 0.45 / 0.45` 是针对 06 Top-N/proxy denominator 的预声明研究目标，不是从旧 04 denominator 经验值直接推导出的可达性假设。实现不得用 validation / robustness 调整这些阈值；如果新 denominator 达不到这些目标，必须如实输出 blocked decision，而不是回调阈值。

1. all split `capture_any_event_before_first_50pct` >= 0.55。
2. validation `capture_any_event_before_first_50pct` >= 0.45。
3. robustness `capture_any_event_before_first_50pct` >= 0.45。
4. 至少两个非 E0 通道在 recommended union 内贡献 positive unique recall。
5. unique recall 必须按 recommended union inclusion / exclusion 后的 channel set 计算；全通道 exploratory unique recall 只能作为 diagnostic，不得替代 gate。

以下 readout 必须输出，但不作为硬通过条件：

1. `bridge_positive_event_before_first_50pct` by all / train / validation / robustness。
2. `bridge_positive_event_before_first_50pct` 的 validation+robustness OOS 合并读数。
3. 与旧 04 `35.2%` before-first-50pct bridge baseline 的对照。
4. `topn_vs_04_baseline_recall_comparison.csv` 必须分别展示 any-event basis 与 +50-positive bridge basis，不得混成单列 recall。
5. 旧 04 对照必须标注 denominator 不同、universe 不同、不能作为 07 pass/fail gate。

如果 all split 通过但 validation 或 robustness 失败，输出 `topn_multichannel_candidate_generator_split_recall_blocked`。

如果 all split 本身失败，或 recommended union 内非 E0 positive unique recall 通道数不足，输出 `topn_multichannel_candidate_generator_total_recall_blocked`。

### 12.3 Density gate

候选生成器不能只靠海量事件堆出 recall。

所有 density gate、recommended union、channel exclusion 和 density drag 判定必须基于 predeclared config 或 train split。validation / robustness 上发现的问题只能触发 fail / caveat / diagnostic，不得回头改变 recommended union。

Density gate 是独立于 recall gate 的硬 gate。只要 recommended union 超过预声明密度上限，即使 recall gate 已通过，也必须输出 `topn_multichannel_candidate_generator_density_blocked`。

07 必须在事件生成前冻结以下 density 上限：

1. `max_recommended_union_canonical_events_per_instrument_year_mean`
2. `max_recommended_union_canonical_events_per_instrument_year_p95`
3. `max_single_channel_density_share`
4. `max_density_drag_channel_share`

这些上限可以基于旧 04 density baseline 的倍数生成，例如使用旧 04 reclaim-based 或 setup-inclusive density 的 2 倍作为参考，但最终进入 gate 的必须是 07 config / manifest 中的显式数值。旧 04 baseline 只能作为上限来源说明和 sensitivity 对照，不能在运行中动态改写 gate。

必须满足：

1. canonical event density 可计算，且 finite。
2. 每个通道的 density、unique recall 和 incremental recall 可计算。
3. report 必须识别 density drag channel。
4. 如果某通道 incremental recall <= 0.02 且占 total canonical density >= 0.25，默认不允许进入 recommended union，除非 report 给出明确保留理由。
5. recommended union 的 canonical event density mean 必须 <= `max_recommended_union_canonical_events_per_instrument_year_mean`。
6. recommended union 的 canonical event density p95 必须 <= `max_recommended_union_canonical_events_per_instrument_year_p95`。
7. 单一通道占 recommended union total canonical density 的比例必须 <= `max_single_channel_density_share`，除非该通道同时贡献 >= 0.10 的 unique recall 且 report 明确列出保留理由。
8. 如果某通道无法按第 4 条从 recommended union 移除，且该通道占 total canonical density >= `max_density_drag_channel_share`，必须输出 `topn_multichannel_candidate_generator_density_blocked`。
9. 如果 recommended union 的 density 高于旧 04 baseline 的 2 倍但仍未超过 07 预声明硬上限，必须输出 density caveat，但不自动 block。

### 12.4 Execution / label gate

必须满足：

1. next-open executable rate >= 0.95。
2. event precision label completeness rate >= 0.70。
3. capture label completeness rate >= 0.90。
4. 所有不可执行或不可标注事件必须进入 audit table。

### 12.5 Precision claim gate

本实验可以通过 recall gate 但不做 precision superiority claim。

只有同时满足以下条件，才允许在 report 中写“precision 改善”：

1. clean baseline match coverage >= 0.70。
2. validation 与 robustness 的 event_big_winner_120d_rate 均不低于 clean baseline。
3. validation 与 robustness 的 failure_10 均不高于 clean baseline。
4. forward_20_return 在 validation 与 robustness 上不出现方向相反的大幅恶化。

否则只能写 candidate coverage / recall supported，不得写 precision edge supported。

### 12.6 Decision mapping

最终 decision 必须按以下优先级确定：

1. input gate 失败：`topn_multichannel_candidate_generator_input_blocked`。
2. recall all split gate 失败：`topn_multichannel_candidate_generator_total_recall_blocked`。
3. recall all split 通过但 validation / robustness split gate 失败：`topn_multichannel_candidate_generator_split_recall_blocked`。
4. recall gate 通过但 density gate 失败：`topn_multichannel_candidate_generator_density_blocked`。
5. recall gate 与 density gate 通过但 execution / label gate 失败：`topn_multichannel_candidate_generator_execution_label_blocked`。
6. recall gate 通过、density / execution / label gate 通过、precision claim gate 失败：`topn_multichannel_candidate_generator_supported_recall_only_precision_unproven`。
7. recall gate 通过、density / execution / label gate 通过、precision claim gate 通过：`topn_multichannel_candidate_generator_supported_high_recall`。
8. 只完成 exploratory analysis、或 recommended union 依赖 validation / robustness post-hoc selection：`topn_multichannel_candidate_generator_diagnostic_only`。

## 13. 决策状态

最终 manifest 的 `decision` 必须为以下之一：

1. `topn_multichannel_candidate_generator_supported_high_recall`
2. `topn_multichannel_candidate_generator_supported_recall_only_precision_unproven`
3. `topn_multichannel_candidate_generator_total_recall_blocked`
4. `topn_multichannel_candidate_generator_split_recall_blocked`
5. `topn_multichannel_candidate_generator_density_blocked`
6. `topn_multichannel_candidate_generator_execution_label_blocked`
7. `topn_multichannel_candidate_generator_input_blocked`
8. `topn_multichannel_candidate_generator_diagnostic_only`

不得使用模糊状态，例如 `pass`、`ok`、`partial_success`。

## 14. 输出文件

必须生成以下 publishable artifacts：

```text
outputs/publishable/reports/topn_multichannel_candidate_generator_report.md
outputs/publishable/tables/topn_multichannel_candidate_event_instances.csv
outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv
outputs/publishable/tables/topn_channel_density_summary.csv
outputs/publishable/tables/topn_episode_capture_audit.csv
outputs/publishable/tables/topn_any_event_recall_by_split_regime_board.csv
outputs/publishable/tables/topn_bridge_positive_recall_by_split_regime_board.csv
outputs/publishable/tables/topn_channel_recall_contribution.csv
outputs/publishable/tables/topn_channel_overlap_matrix.csv
outputs/publishable/tables/topn_event_precision_label_readout.csv
outputs/publishable/tables/topn_event_lead_time_distribution.csv
outputs/publishable/tables/topn_false_repair_diagnostic.csv
outputs/publishable/tables/topn_execution_and_label_completeness_audit.csv
outputs/publishable/tables/topn_event_generation_universe_audit.csv
outputs/publishable/tables/topn_first_touch_reconciliation_audit.csv
outputs/publishable/tables/topn_vs_04_baseline_recall_comparison.csv
outputs/publishable/tables/topn_vs_04_baseline_density_comparison.csv
outputs/publishable/tables/topn_input_manifest_audit.csv
outputs/manifests/run_manifest.json
```

允许生成 ignored local artifacts：

```text
outputs/local_cache/
outputs/large_raw/
```

但 publishable report 必须能从 manifest 找到所有核心输入 hash 和输出 hash。

`topn_input_manifest_audit.csv` 至少必须包含以下字段，确保 input gate 可机器校验：

1. `upstream_05_decision`
2. `upstream_06_decision`
3. `topn_candidate_gap_accepted`
4. `universe_precision_status`
5. `source_gap_count`
6. `active_source_gap_count`
7. `old_04_density_baseline_source`
8. `old_04_setup_inclusive_events_per_instrument_year_mean`
9. `old_04_setup_inclusive_events_per_instrument_year_p95`
10. `old_04_reclaim_based_events_per_instrument_year_mean`
11. `old_04_reclaim_based_events_per_instrument_year_p95`
12. `density_gate_config_source`
13. `max_recommended_union_canonical_events_per_instrument_year_mean`
14. `max_recommended_union_canonical_events_per_instrument_year_p95`
15. `max_single_channel_density_share`
16. `max_density_drag_channel_share`
17. `input_gate_status`
18. `input_gate_failure_reason`

## 15. Report 要求

`topn_multichannel_candidate_generator_report.md` 必须用中文撰写，并至少包含：

1. 最终 decision。
2. 06 denominator 摘要，包括 target episodes、universe-years、density、split distribution。
3. 05 / 06 的 `available_source_topn_candidate` caveat。
4. 与旧 04 recall baseline 的直接对照。
5. 事件生成全集说明，证明事件是在完整 Top-N/proxy evaluated instrument-days 上生成，而不是 target-only search。
6. episode-anchored recall 与 event-anchored precision 的分离说明。
7. any-event capture 与 +50-positive bridge capture 的分离说明。
8. 0.55 / 0.45 recall threshold 是预声明硬目标、不是旧 denominator 可达性证据。
9. bridge-positive forward-120 label censoring 处理。
10. 各通道的 recall / unique recall / density / lead time。
11. train / validation / robustness 分层结果。
12. risk_on / transition / risk_off 分层结果。
13. main_board / ChiNext 分层结果。
14. false-repair diagnostic。
15. precision claim 是否被允许；如果不允许，说明阻塞原因。
16. 下一步实验建议。
17. 明确说明本实验不是交易信号、不是模型、不是回测。

## 16. 实现要求

建议实现入口：

```bash
uv run python topics/02_AFML_BIG_WINNER/experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/src/run_topn_multichannel_candidate_generator.py --mode full
```

至少支持：

```bash
--mode validate-config
--mode full
--max-instruments N
--force
```

`validate-config` 必须只做输入发现、manifest 读取、schema 检查和输出路径检查，不跑全量事件生成。

`--max-instruments N` 只能用于 debug / smoke run：

1. 必须在 manifest 或 debug metadata 中标记 `run_scope = debug_subset`。
2. 不得生成 publishable report、publishable tables 或 publishable manifest。
3. 不得覆盖 full-run outputs。
4. 不参与 output manifest hash reproducibility 断言。
5. 只有 `--mode full` 且未设置 `--max-instruments` 的运行，才允许生成 publishable artifacts 和可复现 manifest hash。

## 17. 测试要求

至少覆盖：

1. 06 denominator manifest 读取失败时输出 input blocked。
2. 05 blocked 只有在 06 明确接受 source gap caveat 时才允许继续。
3. 事件生成全集不能只包含 target episode windows。
4. E0 setup 不计入 event density。
5. event_t0_date 与 event_executable_date 的 next-open 逻辑。
6. event_split 与 episode_split 的差异。
7. first_50pct_touch_date 只用于 evaluation，不用于 event feature。
8. channel overlap 与 unique recall 计算。
9. before-first-50pct any-event recall numerator / denominator。
10. before-first-50pct +50-positive bridge numerator / denominator。
11. forward-120 label incomplete event 不被静默算作 bridge miss。
12. first-touch 字段优先使用 06，07 重算只做 reconciliation audit。
13. density drag channel 判定。
14. density gate 超过预声明 mean / p95 上限时，即使 recall gate 通过，也输出 `topn_multichannel_candidate_generator_density_blocked`。
15. 旧 04 density baseline 从 manifest / `event_density_audit.csv` 读取，并写入 input audit / density comparison table。
16. risk_off / ChiNext 专门通道进入 recommended union 时计入 headline density gate。
17. execution / label gate 失败时输出 `topn_multichannel_candidate_generator_execution_label_blocked`。
18. validation / robustness 不参与阈值调参。
19. `--max-instruments` debug run 不生成 publishable manifest，full run output manifest hash 可复现。

语法与基本测试至少运行：

```bash
uv run python -m compileall topics/02_AFML_BIG_WINNER/experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/src
uv run pytest topics/02_AFML_BIG_WINNER/experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/tests
```

## 18. 成功定义

本实验成功不是证明某个事件可交易，而是证明：

1. 在 06 Top-N/proxy denominator 上，存在一个可审计、可执行、不过度依赖单一通道的候选事件 union。
2. 该 union 在 train / validation / robustness 上能稳定覆盖足够多的 big-winner episode，尤其是 before-first-50pct bridge window。
3. 该 union 的 event density、false repair、regime / board 偏置均被明确量化。
4. 后续实验可以在该候选池上继续做 entry contract、ranking model、meta-label 或 portfolio simulation，而不会混淆 denominator、未来函数和指标口径。
