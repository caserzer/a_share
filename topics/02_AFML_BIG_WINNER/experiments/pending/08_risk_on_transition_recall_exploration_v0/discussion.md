# 07 / 08 实验讨论与后续规划

本文汇总 07 与 08 当前 publishable reports，并把下一轮实验重点收敛到三个问题：

1. density 需要重新按 `failure_10` / 10d fast-fail 基础复核，不能只按 120d big-winner 或完整 episode 去重后判断。
2. 07 / 08 已显示不同 market regime 的结构差异很强，下一轮要测试“不同 event family 在不同 regime 下的表现”，而不是只看同一 family 跨 regime 是否稳定。
3. 在进入 primary model / meta-label 前，必须证明 OOS separability，特别是能否在 out-of-sample 中区分 bridge-positive、fast-fail 与普通 negative event。

## 已读报告

本次讨论基于以下报告与约束文件：

- `07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/reports/topn_multichannel_candidate_generator_report.md`
- `08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/risk_on_transition_recall_exploration_report.md`
- `08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/event_density_episode_interval_diagnostic.md`
- `08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/risk_on_r_series_density_compression/risk_on_r_series_density_compression_report.md`
- `topics/02_AFML_BIG_WINNER/README.md` 中关于 fail-fast、seed density、staged labels 的研究约束。
- 03 / 07 / 08 requirement 中关于 false-repair、density、bridge / label gate 的规则。

## 背景约束

当前研究链路已经确认：Top-N/proxy universe 下的 big-winner episode denominator 来自 06，样本为 2,493 个 `mfe_120 >= 50%` target episodes。该 denominator 绑定 available-source Top-N/proxy caveat，不能被解释成 exact historical top 400/100。

README 对后续 primary model 的关键约束是：`winner_120` 只用于 episode evaluation，不能作为唯一 entry label。entry / primary model 必须使用 staged labels：

- `failure_10`
- `confirm_20`
- `continuation_60`
- `winner_120`

因此，虽然 07 / 08 大量报告使用 before-first-50pct recall、bridge-positive recall 和 120d big-winner label 来评估候选事件，但下一轮 density / model admission 不能只围绕 120d label 或完整 episode。10d fast-fail 是第一层硬过滤：一个 120d big-winner primary model 也必须先回答“事件后 10d 是否快速失败”，再谈 120d winner separability。

早期 fail-fast 实验也给出相同教训：候选事件必须在 executable seed-day / event-day 层面稀疏。episode-level density 可能因为事后去重而显得不严重，但它不能替代实际交易日事件密度。07 / 08 的 density 复核应回到 10d 可执行事件层面：以 horizon-complete `failure_10` 事件为基础，比较事件发生频率、fast-fail rate、winner recall retention 与 bridge-positive retention。

## 现有 density 口径的误读风险

这里需要把 07 / 08 报告里的 `density high` 说清楚：它不等同于“同一股票在 10 个交易日内反复触发、无法执行”。

07 / 08 的报告、frontier 表与补充诊断中同时出现了三类 density 读数；这些读数服务于不同问题，不能被当成同一个 formal gate：

1. formal density gate：full evaluated denominator 下的 events per instrument-year / p95。
2. concentration gate / diagnostic：family share / mechanism share，即某个 family 在 union 事件中的占比过高。
3. episode-window diagnostic：在一个 big-winner episode 或 before-first-50pct window 内累计出现多个事件。

这些读数都能说明候选池太宽或机制过于集中，但它们不是 10d fast-fail density。尤其是 episode-window 口径会把同一个 60-120 session 修复过程中的多个阶段性事件都计为“同一 episode 内多次触发”。如果两个事件相隔 20、40 甚至更多交易日，它们在 episode 统计中仍会提高 density，但在 10d fast-fail / entry admission 口径下未必构成短间隔过密。

换句话说，07 / 08 中很多所谓 `density high` 实际上是 whole-episode / before-first-50pct window 的累计事件数高，或者是 family share 过于集中；这不自动意味着事件在 10d fast-fail 层面高频触发。

因此，07 / 08 中“density blocked”的正确解释不是“这些事件必然交易上太密”，而是：

- 当前 union 或 family 在 episode / 年化 / family-share 口径下过宽。
- 这些口径尚未回答 10d fast-fail 层面是否真的过密。
- 一些 deterministic compression arm 即使被 density_vs_e1 或 p95 判为不过，也可能已经把实际相邻触发间隔拉长；反过来，episode 内 event count 高也不必然等于 10d 拥挤。

下一轮必须把 episode-window density、calendar/instrument-year density、rolling 10d event-day density 分开报告，不能再用一个 `density` 字段概括三种问题。

## 07 结论：E1 是 backbone，但 full union 不能进入下一阶段

07 的最终 decision 是：

```text
topn_multichannel_candidate_generator_density_blocked
```

核心事实：

- 07 full union 的 before-first-50pct any-event recall 全样本为 72.0%，train / validation / robustness 分别为 71.4% / 79.3% / 68.9%，recall gate 强通过。
- E1 alone 捕获 1,773 / 2,493 个 target episodes，recall 71.1%，几乎等同 full union 的 72.0%。
- full union 的 canonical density mean / p95 为 3.94 / 7.00 events per instrument-year，未超过总量 hard limit。
- 阻塞来自 density drag：E2 占 recommended canonical events 的 44.1%，incremental recall 为 0；E6 占 32.5%，incremental recall 只有 0.4%。
- E1-only 只使用 full union 45.0% 的 canonical events，却保留 71.1% any-event recall 与 32.6% bridge recall，是最稳的下一步 backbone。
- validation event +50 rate 只有 7.2%，forward20 / forward60 mean 为 -1.1% / -2.3%，说明 07 不是 entry edge，而是 high-recall candidate pool。

07 还暴露了 regime 差异：risk_on miss rate 为 43.0%，transition miss rate 为 40.4%，明显高于 risk_off 的 20.1%。validation risk_on recall 只有 40.9%，robustness transition recall 也偏弱。后续不能只围绕 all-split 或 all-regime 调 density；需要检查哪些 family 天然适合 risk_off repair，哪些 family 适合 risk_on / transition momentum 或 breakout。

07 对下一轮的直接含义：

- E1 作为 candidate backbone 保留。
- E2 降级为 E1 同日 confirmation feature，不作为 headline event family。
- E6 降级为 continuation readout 或二阶段 label / feature，不作为 headline event family。
- E3 可保留为低权重辅助 family，但必须重新做 density / persistence / 10d fast-fail 检查。

## 08 结论：risk_on / transition 有可补召回信号，但低密度版本质量不够

08 主实验最终 decision 是：

```text
risk_on_transition_recall_exploration_density_blocked
```

核心事实：

- 08 从 07 E1-only baseline 出发，尝试补 risk_on / transition missed episodes。
- selected union 保留 T4 gated 与 T7 gated，绝对密度很低，full denominator density 为 0.5695 events per instrument-year，约为 E1 的 0.3025x。
- 但 T4 占 selected union 事件密度 70.9%，超过 35% family share gate。
- selected union 的 bridge-positive recall 在 focus split/regime 上显著低于 E1：train risk_on 为 6.2% vs E1 28.9%，train transition 为 8.6% vs E1 32.0%，validation transition 为 3.7% vs E1 30.9%。
- all-new union 证明信号空间存在：它在 robustness risk_on 的 incremental recall 达到 49.2%，bridge recall 达到 79.6%，但 density 是 E1 的 13.28x，不能直接作为 event union。
- T4 有价值但机制同质，需要拆解与 R3/T8 overlap；T7 更像 board/style context duplicate，不应作为独立 alpha family。

08 的核心 insight 是：risk_on / transition 的 missed recall 不是“找不到事件”，而是“找到的事件太密、太同质、且低密度版本的 bridge quality 不够”。

## R-series compression 结论：不是 recall 或 bridge 不行，而是 high-bridge event 太密

R-series density compression patch 的最终 decision 是：

```text
risk_on_r_series_no_compression_candidate
```

preflight 已确认 R1 / R2 / R6 / R7 / R8 是 risk_on high-recall / high-bridge / high-density source pool。R5 是低 density 但低质量反例，应排除或仅 diagnostic。

关键结果：

- raw R pool 事件数 61,960，density 9.09x E1，p95 24。
- event-regime-gated source pool 事件数 47,929，density 7.03x E1，p95 20。
- 24 个 deterministic compression arms 中，train recall 通过 24/24，train bridge 通过 19/24，但 density <= 1.0x 只通过 1/24，p95 <= 4 只通过 3/24。
- 唯一 density <= 1.0x 的 `consensus_family_count__min3` 把 density 压到 0.45x、p95 压到 2，但 train bridge delta 变成 -17.7 pct。
- `cooldown_after_selected_event__40d` 保留 train bridge +15.6 pct、robustness bridge +21.3 pct，但 density 仍为 2.05x、p95 5。
- `R7 single-family` 最接近可用：density 1.43x、p95 4、train bridge +6.7 pct、robustness bridge +11.6 pct，但 single-family share 100%，不能作为 direct entry union。
- R2 当前因为缺少 amount / volume 字段成为 unscored density floor；如果继续纳入 R2，必须补 volume / amount expansion 字段，或给 R2 单独 family budget / cooldown / bridge gate。

episode-interval diagnostic 进一步说明 R-series 的 density 问题中包含明显的 episode-window 累计效应：

- 07 E1 在全样本 episode 内 event count mean / median 为 0.80 / 1；只有 223 / 2,493 个 episode 有两个及以上 E1 event。
- R gated 在全样本 episode 内 event count mean / median 为 4.69 / 5；2,160 / 2,493 个 episode 有两个及以上 R gated event。
- risk_on 下 R gated event count mean / median 为 5.27 / 5，top 10% 为 9，相邻触发间隔中位数只有 4 个交易日。

这个诊断有用，但下一轮不能把 density pass/fail 只改成 episode 内部指标。episode 内部重复触发是问题形态，不是最终交易密度结论。原始 R gated pool 的 median gap 短，也不代表每个 family、compression arm 或 selected subset 都短；必须逐 family / arm 复算 adjacent gap p10 / median / p90。真正的 primary-model density gate 仍应回到 10d fast-fail 基础上的 executable event-day 统计，并额外报告相邻触发间隔分布，避免把相隔较长的阶段性事件误判成短期拥挤。

这也解释了为什么本文不直接采纳 `event_density_episode_interval_diagnostic.md` 中的 episode-level hard gate 建议，例如 `risk_on` episode 内 R-union event count median <= 2、top10 <= 4、相邻 event 间隔 median >= 10 trading days。这些阈值适合作为拥挤形态的诊断和 compression 设计提示，但不适合作为下一轮 admission hard gate。原因是它们绑定 target episode / before-first-50pct window，天然带有事后 episode 边界；如果直接硬化，会把相隔较长的阶段性事件和 10d 内短间隔触发混在一起，也可能让不同实验继续各自定义 density。下一轮保留这些 episode-level 阈值作为 `diagnostic_alert`，但 hard gate 只绑定 formal full-denominator density、family concentration、rolling 10d executable event-day density 与 fast-fail cost。

## 关键修正：density 复核必须以 10d fast-fail 为基础

下一轮 density 复核需要从以下口径重新计算，而不是沿用 120d 或完整 episode 口径。重点是把“episode 内累计多个事件”与“10d 内短间隔拥挤”拆开：

1. 以 event t0 后 `failure_10` horizon complete 的 executable canonical event 为主分母。
2. 对每个 candidate union / family / regime 计算 10d event-day density：
   - events per instrument-year
   - p95 events per instrument-year
   - per-instrument rolling 10d / 20d duplicate rate
   - same instrument same 10d-window event count
   - adjacent event gap distribution: p10 / median / p90
   - fast-fail 10d count / rate
3. 同时计算 10d 过滤后的 retention：
   - big-winner episode recall retention
   - bridge-positive recall retention
   - E1-missed capture retention
   - regime-specific retention
4. 10d fast-fail 只能作为 label / diagnostic / rejector 目标，不得在 t0 前使用未来 10d 信息触发事件。用于 admission 的模型必须通过 train-only fit、purged OOS evaluation 和 leakage audit。
5. density pass 不能因为 120d positive rate 高而放行；也不能因为 episode-level de-dup 后事件数少而放行。只有 10d executable event-day density 与 fast-fail cost 同时可控，才允许进入 primary model。

这个修正会改变 08 R-series 的评价重点：R 系列的 bridge quality 很强，但如果它在 10d fast-fail 基础上的重复触发和失败修复成本过高，就不能作为 direct entry pool。相反，如果 ranker 能在 10d 层面剔除快速失败、保留 bridge-positive episode coverage，即使 120d precision 不是最高，也可能成为可用的 primary-model candidate source。

下一份 requirement 应先产出一个跨实验口径冻结物：

```text
density_fast_fail_caliber_contract.md
```

这个文件是 A / B / C / D / E 的唯一权威 density / fast-fail 定义来源，至少固定：

- formal full-denominator density 的 denominator、calendar span、instrument-year 计算方式。
- rolling 10d / 20d executable event-day density 的计算方式。
- adjacent event gap p10 / median / p90 的计算方式。
- `failure_10` horizon completeness、non-executable next-open 与 censoring 处理。
- episode-window density 只能作为 diagnostic / alert，不作为 admission hard fail gate。
- train-only threshold freezing、validation / robustness readout 的禁止调参规则。

后续实验只引用该 contract，不在各自 requirement 中重新定义 10d density 口径。

## 历史后续实验规划（已由 A / B / C 修正）

以下保留 A / B / C 运行前的实验规划，作为研究路径追溯。当前有效优先级以后文“推荐优先级（修正后）”为准；本节不再作为下一步执行顺序。

### Experiment A：10d density / fast-fail audit replay

目的：重新检查 07 E1、07 E1+E3、08 selected T4/T7、R gated pool、R compression frontier arms 的 density 与失败成本。

输入：

- 07 canonical / instance events。
- 08 candidate family canonical / instance events。
- R-series compression frontier arms。
- 06 frozen episode denominator。
- event-level 10d / 20d / 60d / 120d label completeness 与 execution audit。
- `density_fast_fail_caliber_contract.md`。

输出：

- `candidate_10d_density_summary.csv`
- `candidate_10d_fast_fail_readout.csv`
- `candidate_10d_retention_by_split_regime.csv`
- `candidate_10d_density_vs_episode_density_comparison.csv`
- `candidate_adjacent_event_gap_diagnostic.csv`

核心 gate：

- `failure_10` horizon complete executable event rate >= 95%。
- 10d event-day density mean / p95 不高于 E1 baseline 的预声明倍数。
- rolling 10d duplicate rate 与 adjacent gap distribution 必须单独报告；不能仅凭 episode 内 event count 判定 dense。
- episode-window density 只能作为 diagnostic / explanation，不作为 Experiment A 的 hard fail gate；hard fail 必须绑定 formal full-denominator density、family concentration 或 10d executable event-day density。
- fast-fail 10d rate 相对 E1 不明显恶化，或恶化必须由更高 bridge-positive retention 补偿。
- big-winner episode recall retention 与 bridge-positive recall retention 不得因 10d rejector 坍塌。
- validation / robustness 只用于 OOS readout；阈值必须 train-only 冻结。
- episode-level alert 可以触发人工复核或进入 compression design，但不得单独触发 `density_blocked`。

### Experiment B：regime-specific event-family performance matrix

目的：严格测试“不同 event family 在不同 regime 下的表现”，而不是只测同一个 family 跨 regime 是否稳定。

方法：

- 固定 candidate universe，按 `risk_off`、`risk_on`、`transition` 分别评估 event family。
- family 维度至少包括：
  - E1 repair backbone
  - E3 persistence / quality
  - E2 confirmation tag
  - E6 continuation tag
  - T4 entropy compression
  - T7 board/style relative strength
  - R1 / R2 / R6 / R7 / R8 risk-on source families
- 每个 regime 内分别报告：
  - denominator n、candidate captured n、bridge denominator n、event n
  - before-first-50pct any recall
  - bridge-positive recall
  - E1-missed incremental recall
  - 10d fast-fail rate
  - 20d false-repair rate
  - event-day density mean / p95
  - single-family share / mechanism-cluster share
  - OOS separability metrics

样本量护栏：

- 每个 split / regime / family cell 必须报告 denominator n 与 bridge denominator n。
- 若 denominator n < 30 或 bridge denominator n < 30，该 cell 强制 `diagnostic_only`，不得作为 support / block 结论。
- 若 30 <= n < 100，该 cell 标记 `low_power_caution`，只能与 train / robustness 的一致性一起解释。
- validation risk_on 这类 n=22 的 cell 只能作为方向性读数，不能用于调阈值或支持 family selection。

预期判断：

- risk_off 可能由 E1 repair backbone 主导，R/T families 只做 context。
- risk_on 可能需要 R1 / R6 / R7 / R8 这类 momentum / breadth / rank-jump source，但必须通过 family budget 和 10d rejector。
- transition 可能需要 T4 entropy compression、T6 / T8 volatility / transition 类机制，但要先做 overlap deconcentration。

### Experiment C：risk_on R-series bridge-positive ranker

目的：从 R-series high-bridge source pool 中学习 event selection，而不是继续扩大 deterministic threshold grid。

建模目标：

- 第一目标：bridge-positive episode coverage / E1-missed bridge capture。
- 第一约束：10d fast-fail 与 event-day density。
- 第二目标：120d winner label，只作为 staged label 的后段评估，不作为唯一优化目标。

候选特征：

- R1 / R6 / R7 / R8 score fields。
- R2 仅在补齐 amount / volume expansion 字段后进入 score ranker；否则单独 family budget。
- family id、mechanism cluster、same-day overlap、rolling 10d duplicate count。
- false-repair 10d / 20d diagnostics、MAE、MFE、range position、market regime、board concentration。
- E2 / E3 / E6 同日 tags 作为 context feature，不作为 headline event。

验证方式：

- train-only fit threshold / quota。
- purged time split 或 anchored OOS。
- validation risk_on denominator 只有 22 个，只作为 diagnostic。
- robustness 用于 support / block，不用于调参。

结论档位：

1. `direct_entry_candidate_supported`
   - train risk_on incremental recall >= +8 pct。
   - train risk_on bridge delta >= +5 pct。
   - robustness risk_on incremental recall >= +8 pct。
   - robustness risk_on bridge delta >= +5 pct。
   - 10d event-day density <= E1 baseline 的预声明上限。
   - p95 density 不超上限。
   - downstream direct-entry family share <= 35%。
   - OOS separability 不反转。

2. `meta_label_feature_source_supported`
   - direct-entry 35% family-share 或更严格 density gate 未通过，但 feature-source concentration guard 通过。
   - single-family density share <= 65%。
   - train 与 robustness 的 bridge delta 不反转，且至少一个 OOS readout 保持正向。
   - 10d fast-fail cost 可审计且没有明显恶化。
   - 只能进入 meta-label / rejector feature source，不得作为 direct entry union。

3. `diagnostic_only_or_no_candidate`
   - direct-entry 与 feature-source 两档都未通过。
   - 这仍是有效 negative result，但必须输出 ranker scores、failure distribution、family budget audit 与 rejected-arm frontier，避免只留下 `no_candidate` 结论。

### Experiment D：transition T4 de-overlap / mechanism split

目的：确定 T4 的有效部分是独立 entropy-compression transition，还是 R3 / T8 / volatility contraction 的 duplicate。

方法：

- 将 T4 gated events 按与 R3 / T8 / VCP / volatility cluster overlap 拆成 buckets。
- 对每个 bucket 分别计算 recall、bridge、10d fast-fail、density、lead-time basis。
- 如果去掉 overlap 后 T4 incremental recall 近似归零，则 T4 只作为 context tag。
- 如果 non-overlap bucket 保留 bridge-positive recall 且 density 可控，则进入 ranker source pool。
- 无论 non-overlap 是否归零，都必须输出 `t4_overlap_decomposition.csv`、`t4_overlap_bucket_recall_bridge.csv` 与 `t4_context_tag_candidate.csv`。如果独立部分归零，结论写成 valid negative result，而不是无产物失败。

### Experiment E：OOS separability audit

目的：在模型化前确认事件是否真的可分，而不是只在全样本 label readout 上看起来有差异。

建议输出：

- `oos_separability_by_family_regime.csv`
- `oos_bridge_positive_ranker_readout.csv`
- `oos_fast_fail_rejector_readout.csv`
- `oos_calibration_by_split_regime.csv`

评估对象：

- bridge-positive vs bridge-negative。
- non-fast-fail vs fast-fail 10d。
- 120d winner vs non-winner，作为后段标签。
- E1-missed captured vs still-missed episode。

最低要求：

- AUC / PR-AUC / top-decile lift 必须按 train -> validation -> robustness 报告。
- 每个 regime 单独报告样本量；样本量不足时只能标记 diagnostic。
- threshold、feature selection、family budget 必须 train-only。
- separability 必须与 density / fast-fail cost 联合判断，不能只报告 event-level 120d positive rate。

## A / B / C / D 实证结果与方向修正（2026-06）

Experiment A / B / C / D 已全部运行完毕，结果改变了本文原本的规划。四者的最终 decision 分别是：

- A：`density_fast_fail_audit_partial_source_complete`
- B：`regime_family_matrix_source_caveated_complete`
- C：`risk_on_r_series_ranker_source_caveated_complete`
- D：`post_replay_retention_source_source_caveated_complete`

C 的关键结果是一个 negative result：21×3 个 risk_on / transition / risk_off arm **全部停在 `diagnostic_only_or_no_candidate`**，direct-entry pass 0、feature-source pass 0。这把本文原先的两条工作假设证伪：

1. 「risk_on 召回来自 R-series，先做 density compression 即可」——框架错了。C 显示 compression 确实能把 density/E1 从 4.5 压到 1.3、rolling 10d duplicate 从 54% 压到 0%，但 fast-fail excess 始终 +12~16pp、false-repair excess +12~16pp，卡死所有 arm。**真正的绑定约束是事件质量（fast-fail / false-repair），不是密度。** 继续扩 compression arm grid 不会解决问题。
2. 「transition 召回靠 T4/T7 或现有 R-series 压缩修补即可」——已被 C 证伪。C 显示当前 T4/T7 与 R-series arms 在从最密到最稀的设置上 robustness bridge delta 都是负（-5.8 到 -10pp），E1-missed capture 只有 2~4 个。这个结果不证伪所有 volatility / VCP / T6 / T8 类 transition family，但说明它们必须作为新的 family rediscovery 假设重新验证，不能沿用当前 T4/T7 或 R-series 修补路径。

C 最有价值的洞察是 risk_on 与 transition 是两类不同问题，必须分轨：

- **risk_on 是质量成本问题。** bridge 信号真实（robustness 仍保留 72~78 个 E1-missed capture、bridge recall 47~54%），但 fast-fail / false-repair 成本压不下来。OOS 上 bridge separability 偶尔为正，`non_fast_fail` / `non_false_repair` / `winner_120d` separability 从不可靠。
- **transition 是信号稳定性问题。** 增量召回在 robustness 上直接消失。

此外，A/B/C 三次都因 retention 只有 `pre_replay_capture_only`（缺 event-to-episode replay membership）而无法证明 post-filter retention。D 已经补齐这个前置缺口：本地 materialized membership 有 357,450 行，06 episode window 全部 ready（4,986/4,986），C arm pre-replay 对账 189/189 pass，leakage audit pass。D 仍是 `source_caveated_complete`，因为所有 published readout 继承 A/B/C 的 source-caveated / diagnostic 约束，不能直接作为 entry gate。

D 的新证据进一步把方向分清：

- **risk_on 的 recall source 已足够，成本侧没有解决。** R-core 在 risk_on train / robustness 的 post-replay recall 为 98.2% / 94.5%，R6 为 96.0% / 90.1%；E1-missed 中，R-core 抓到 train 80/83、robustness 84/92，R6 抓到 77/83、77/92。继续扩 entry-ranker / compression grid 的边际价值低于设计 cost rejector。
- **transition 不是同一个问题，且很可能发生了状态塌陷。** R-core 在 transition train / validation 很高（99.0% / 97.5%），但 robustness 只有 50.0%；C arm transition max recall 也从 train 65.1% 掉到 robustness 31.0%。这说明 transition 的问题不只是 event family 不稳定，也可能是 regime label 本身把不同机制混进了同一个桶，不能靠 T4/T7 或 raw R-core 修补。

需要特别注明的是，当前 `transition` 不是一个正向定义的单一市场状态，而是 risk_on / risk_off 以外的 residual bucket：`risk_on = market_trend_60d >= 0 且 market_drawdown_120d > -10%`，`risk_off = market_trend_60d < 0 且 market_drawdown_120d <= -10%`，`transition = 其余完整观测`。因此 transition 至少混合了两类相反过程：

1. **recovery transition**：`market_trend_60d >= 0` 但 `market_drawdown_120d <= -10%`，更像深回撤后的修复 / risk_off -> risk_on。
2. **deterioration transition**：`market_trend_60d < 0` 但 `market_drawdown_120d > -10%`，更像高位转弱 / risk_on -> risk_off。

这解释了为什么同一组 R-series 在 train / validation transition 里几乎全覆盖，却在 robustness transition 里塌陷：分母不是简单变少，而是子状态构成可能变了。下一步不应直接把所有 transition episode 作为同一目标去找 family，而应先做 **transition sub-regime taxonomy audit**，确认 train / validation / robustness 中各子状态占比、E1 / R-core / R6 / T4/T7 recall、E1-missed capture、fast-fail / false-repair 是否一致。

## E / F / G 实证结果与方向收敛（2026-06）

Experiment E / F / G 已全部运行完毕，三者各自排除了一条路径，整体证据已收敛。最终 decision 分别是：

- E（risk_on post-filter cost rejector）：`risk_on_cost_rejector_feature_source_caveated_supported`
- F（transition sub-regime taxonomy audit）：`transition_subregime_taxonomy_diagnostic_only`
- G（previous-regime conditioned transition outcome audit）：`transition_previous_regime_conditioning_diagnostic_only`

### E：risk_on cost rejector 有真实 OOS 信号，近门槛

E 证明「用 t0 可见特征做 risk_on 成本 rejector」这条路有信号且接近 research-entry：

- selected `supervised_joint_cost_rejector`（R-core，target `cost_bad_10_20`，logistic regression balanced L2）在 train / validation / robustness 的 ROC-AUC 为 0.692 / 0.682 / 0.686，PR-AUC 均高于 prevalence，robustness top-decile lift 2.02，decile 单调递增，**OOS 无反转**。
- selected threshold `keep_080`：robustness 成本相对下降 20.48%，同时保留 any recall 86.55%、E1-missed retention 84.52%、captured n=71。
- 未过 research-entry 的原因分两类：① 一个 selected-threshold 实证 gate 差 0.83pp，train 成本下降 14.17% 低于 15%（robustness 已 20.48% 过线）；② 两个工程/契约缺口，单个特征 `momentum_percentile_20d_lag20` train coverage 93.30% < 95%，以及 density 可审计但 E config 未预声明上限（`density_gate_not_configured`）。
- 核心 tradeoff：`keep_080` 保 recall 但成本差一点，`keep_075` 成本过线但 train any recall 跌破 90%，二者卡在很窄边界。报告未 cherry-pick。

### F：transition 不是独立第三态

F 把 residual transition 拆成 recovery / deterioration / boundary-or-mixed，结果不稳：

- boundary over-capture：train 79.2%、robustness 80.2% 的 transition events 落入 boundary 桶，core 子态被稀释。根因是默认 boundary 规则里 `short_trend_contradiction`（20d 与 60d 趋势反向）单独贡献 138 个 date——而该条件在 transition 里近乎同义反复。
- **robustness recovery core = 0**：即使不做 boundary 重分类，date 级 recovery 原始也只有 4 个交易日（train 21 / validation 16 / robustness 4）。`recovery = trend60≥0 ∧ drawdown120≤-10%` 是个短暂瞬态，在 2024-2026 robustness 窗口几乎不出现。**任何 taxonomy 都无法造出 out-of-time 不存在的样本。**
- 120d KMeans 选 k=3 但三簇全部退化为 boundary-like，block stability 失败（rolling k=3 vs block k=2，ARI=0.148）；有效独立窗口仅约 34.9（名义 230，lag1 自相关 0.736），说明滚动 120d 高重叠制造伪簇。
- 有价值的副产物：deterioration 是真实风险区（robustness false-repair 30%-34%、fast-fail 24%-27%，远高于 boundary 13%-14%）。

### G：前态条件化有解释力，但样本撑不起 supported taxonomy

G 把 transition 按前一个非 transition regime 拆成 `transition_from_risk_on` / `transition_from_risk_off`（PIT 可知），用 next regime 做 ex-post outcome（continuation / conversion，t0 不可知）：

- 前态确实带路径信息：risk_off→transition 转 risk_on 40.0%（16/40） vs risk_on→transition 转 risk_off 18.9%（14/74）。
- 但 400 个 grid rule **零个 structural-eligible**：robustness conversion 只有 3 段，per-direction conversion 只有 1-2 段（risk_off→risk_on 1 段、risk_on→risk_off 2 段），均 < supported 所需 segment power。
- universe drift：published transition 有 30.59% 没被 reconstructed transition 复现（60d/120d horizon mismatch），单独把上限钉死在 diagnostic。
- `effective segment n` 指标揭示隐性低 power：robustness conversion target episode n=78 看似不小，但来自 3 段、单段 top1 episode share 高达 93.8%-100%，是少数长段在主导。
- **最有价值的 readout 信号**：同样是 risk_on 进入的 transition，robustness 下 continuation 极干净（R-core fast-fail 2.3% / false-repair 5.3%），conversion 极脏（R-core fast-fail 23.0% / false-repair 29.0%）：fast-fail 约 10 倍，false-repair 约 5.5 倍。这个读数与 F 的 deterioration 风险抬升同向，提示 deterioration / conversion 可能在同一类转弱路径中重叠；但当前没有 F×G cross-tab，不能声称它已经解释了 F 的全部 deterioration 风险。conversion 判定依赖未来 next_regime，**只能当事后解释 / rejector 分层 readout，不能当 PIT 入场门或训练特征**。

### 收敛结论

三个实验联合给出明确收敛：

1. **risk_on 主线（E）是唯一已被证明有 OOS 信号、且离 supported 最近的方向**，应优先推过门。
2. **在当前 residual transition label / source 下，transition family rediscovery 应正式关闭**。F + G 已联合证明当前 transition 的问题是 residual bucket 的状态混合 + 样本稀缺，不是「缺 family」；继续在同一 label source 下找 volatility / VCP / T6 / T8 family 会把混合机制误当新 alpha。discussion 里「audit 通过后才做 rediscovery」的前置条件**没有满足**（F / G 都未 supported），rediscovery 不应启动。若未来扩样本时间跨度或重定义 regime label source，那是新数据 / 新标签问题，不属于当前主线。
3. **G 的前态信号不能直接喂进当前 E 的 risk_on-only gate**。E 的正式 scope 是 risk_on cost rejector；G 的 `transition_from_risk_on` / `transition_from_risk_off` 只定义在 transition segment 内。下一步应先把 E 原 scope 推过 research-entry。若要利用 G，只能另开 transition-side diagnostic ablation 或 future multi-regime cost-rejector extension：把 previous non-transition regime 当作 t0 可见分层，检验它是否改善 cost_bad 排序；conversion 仍只能作为 ex-post readout。

## 推荐优先级（修正后）

P0（已完成）：`density_fast_fail_caliber_contract.md` 与 Experiment A / B / C 已冻结。上方历史规划仅供追溯，下一步不再沿用 C 的 ranker-compression 主线。

P0（已完成）：**post-replay event-to-episode retention source** 已由 Experiment D 补齐。它不提供 direct-entry gate，但已经提供后续 cost rejector / meta-label 所需的 post-replay membership、fast-fail / false-repair audit label、以及 C arm 对账基础。

P1（已完成，risk_on）：**post-filter replay / cost rejector** 已由 Experiment E 跑完，decision 为 `risk_on_cost_rejector_feature_source_caveated_supported`。E 证明该路线有 OOS 信号（robustness ROC-AUC 0.686、cost 相对下降 20.48%、E1-missed retention 84.52%），但未过 research-entry：一个 selected-threshold 实证 gate 差 0.83pp（train cost reduction 14.17% < 15%），另有两个工程/契约缺口（`momentum_percentile_20d_lag20` coverage < 95%、density 上限未配置）。

P1（已完成，transition）：**transition sub-regime taxonomy audit** 已由 Experiment F 跑完，decision 为 `transition_subregime_taxonomy_diagnostic_only`。F 证明 transition 不是独立第三态：boundary over-capture 80%、robustness recovery core = 0、120d 自动聚类退化为单一 boundary-like 簇。前置 audit **未通过**，因此子状态级 family rediscovery 不得启动。后续 Experiment G 进一步用 previous-regime conditioning 复核，同样停在 diagnostic_only。

P0（新，最高 ROI）：**把 E 推过 research-entry**。这是整条线唯一已被证明有 OOS 信号、且离 supported 最近的方向。三个修补：① 在 E config 预声明 density / concentration 上限并写入 manifest；② 对 `momentum_percentile_20d_lag20` 二选一（剔除或补齐源数据，禁止未来填充）；③ 在同一 selected-threshold 规则下重审 `keep_080` / `keep_075` 边界，禁止从 cost frontier 与 recall frontier 分别 cherry-pick。

P1（新，diagnostic extension）：**G 的前态上下文只做 transition-side diagnostic / ablation，不并入当前 E research-entry gate**。`transition_from_risk_on` / `transition_from_risk_off` 是 t0 可知的 PIT context，但只在 transition universe 内有定义；它不应污染 E 的 risk_on-only training scope。若后续要验证其增益，应另开 E-extension / multi-regime rejector requirement，明确 scope、分母、leakage audit 与 selected-threshold 规则；目标是测试 previous-regime context 是否改善 cost_bad 排序，而不是训练 PIT conversion classifier。

P2（关闭）：**当前 residual transition label 下的 transition family rediscovery 正式停止**。F + G 已联合证明当前 transition 的问题是 residual bucket 的状态混合 + 样本稀缺（robustness recovery / conversion 段在 out-of-time 天然稀少），不是缺 family。若仍想复活 transition，唯一剩余路径是扩样本时间跨度或重定义 regime label source —— 这是数据采集 / 标签重构问题，短期 ROI 低，不在当前主线。

P2（降级）：原 Experiment D（T4 de-overlap）边际价值已很低，B 与 C 已一致把 T4/T7 钉死为 negative control / quality filter，可缩成一次性诊断或跳过。

P2（部分已完成）：原 Experiment E 中针对当前 R-series C arms 的 OOS separability 读数已由 C 产出，并证明这些 arms 下 fast-fail / winner 不可分。因此当前 R-series C arms 不需要重复做同口径 separability；risk_on cost rejector 必须沿当前 E scope 做 targeted OOS audit。若未来基于新样本或新 regime label source 复活 transition family，那应另起新问题并重新做 targeted OOS audit。

## 当前工作假设（修正后）

1. E1 是 candidate backbone，不应被移除。（保持）
2. E2 / E6 是 feature / tag，不是 headline family。（保持）
3. risk_on 的绑定约束是事件质量（fast-fail / false-repair），不是 density / recall source。下一步是 cost rejector + post-filter replay，不是继续 density compression。（已由 C/D 共同确认）
4. 当前 residual transition label 下的 family rediscovery 正式关闭。F（taxonomy audit）与 G（previous-regime conditioning）都停在 diagnostic_only：transition 不是独立第三态，boundary over-capture 80%、robustness recovery core = 0、conversion 段 OOS 仅 1-3 段。问题是 residual bucket 的状态混合 + 样本稀缺，不是缺 family。前置 audit 未通过，子状态级 family rediscovery 不启动。（已由 F/G 确认）
5. transition 的前态上下文（`transition_from_risk_on` / `transition_from_risk_off`，t0 可知）有解释力但不足以单独 supported；它只能作为 transition-side report / ablation 分层，或 future multi-regime rejector 的候选特征，不能直接并入当前 E 的 risk_on-only research-entry gate。G 已显示 from_risk_on/continuation 干净、from_risk_on/conversion 脏（fast-fail 约 10 倍、false-repair 约 5.5 倍），但 conversion 依赖未来 regime，只能当事后 readout。（已由 G 确认）
6. primary model 的第一关不是 120d big-winner precision，而是 OOS 下能否在可控 density 内减少 10d fast-fail，同时保留 bridge-positive / winner recall。E 已证明 risk_on cost rejector 有此 OOS 信号（robustness cost 降 20.48%、E1-missed retention 84.52%），但未过 research-entry：train cost reduction 差 0.83pp，且还缺 density config + 特征 coverage 两个工程/契约修补。（已由 E 确认）

下一份 requirement 应聚焦 **把 E 的 risk_on cost rejector 原 scope 推过 research-entry**：配置 density / concentration 上限、修正 `momentum_percentile_20d_lag20` coverage、在同一阈值规则下重审 keep fraction 边界。G 的前态上下文不得直接带入当前 E gate；如需验证，另开 transition-side diagnostic / multi-regime extension。不再沿用 C 的 R-series ranker-compression 主线，不再把 residual transition 当单一目标状态建模，也不启动当前 label source 下的 transition family rediscovery。
