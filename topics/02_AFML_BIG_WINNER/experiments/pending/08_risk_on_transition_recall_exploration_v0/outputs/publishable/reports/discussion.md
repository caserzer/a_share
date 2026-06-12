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

## 后续实验规划

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

## 推荐优先级

P0：先冻结 `density_fast_fail_caliber_contract.md`，再做 Experiment A。没有统一 contract 与 10d density / fast-fail replay，后续所有 ranker 与 union admission 都会继续混用 120d、episode 与 event-day 口径。

P1：并行设计 Experiment B 与 C。B 给出带样本量护栏的 family-regime matrix，C 聚焦 risk_on R-series ranker，并采用 direct-entry / meta-label feature-source 双档结论。二者共享同一套 contract 与 10d density / fast-fail audit。

P1：做 Experiment D，避免 T4 在 transition 中被重复机制误判为独立 family。

P2：在 A / B / C 的输出稳定后再做 Experiment E 的完整 OOS separability package。若 C 已经训练 ranker，E 应作为其 admission audit；若 C 仍失败，E 仍可用于判断 R-series 是否只适合作为 diagnostic feature source。

## 当前工作假设

1. E1 是 candidate backbone，不应被移除。
2. E2 / E6 是 feature / tag，不是 headline family。
3. risk_on 的召回修复主要来自 R-series，但必须先通过 10d fast-fail 与 density compression。
4. transition 的召回修复可能来自 T4 / volatility-compression family，但必须先 de-overlap。
5. primary model 的第一关不是 120d big-winner precision，而是 OOS 下能否在可控 density 内减少 10d fast-fail，同时保留 bridge-positive / winner recall。

下一份 requirement 应优先冻结 `density_fast_fail_caliber_contract.md` 与 Experiment A 的产物，然后再冻结 regime-specific family matrix、R-series bridge-positive ranker 与 T4 overlap decomposition。
