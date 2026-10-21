# 02_AFML_BIG_WINNER 研究日志

初版生成日期：2026-06-30；EP17—EP29增补：2026-10-21

本文档上方第0—7节归档截至 Episode 16 的研究历程；第8—10节追补至 EP29。范围包括根目录 `README.md`、`research_direction_discussion_20260614.md`、`topic_retrospective_20260625_short.md`，以及 `experiments/pending/01` 到 `16` 的 publishable/final reports。

状态说明：当前 `experiments/completed/` 为空，所有研究仍位于 `experiments/pending/`。因此本文记录的是研究证据、失败边界和后续方向，不是生产信号、交易建议或部署授权。

对应结论版见 `research_conclusions.md`。

## 0. 总体主线

项目最初的核心判断是：所谓 "big winner" 不应被当成稠密的 stock-day 标签，而应被建模为 episode lifecycle。推荐管线是：

```text
Event Generator -> Episode -> Failure Filter -> Confirmation -> Continuation/Winner -> Bet Sizing -> Backtesting
```

早期 README 设计了分段标签：

```text
failure_10 -> confirm_20 -> continuation_60 -> winner_120
```

之后 01-16 的研究基本沿这条逻辑推进：先建立 PIT 数据和 winner 画像，再寻找可观测 anchor/event，再提高 recall，再压缩成本和 fast-fail，随后尝试 native sparse event、path-defined winner label，最后转向 sequential continuation。到 Episode 16 为止，结论已经收敛为：

1. winner/repair/survival 相关的统计信号确实存在；
2. 这些信号多次无法稳定转化为 after-cost、full-denominator、OOS 可确认的 utility；
3. 当前没有任何 entry、exit、holding、portfolio backtest、model deployment、production signal 或 live trading 授权。

## 1. 数据地基与初始画像

### 01_data_prepare_pit_largecap_akshare_qlib_v0

目标：构建 PIT largecap A 股股票池和 qlib 数据地基，覆盖 2017-01-01 到 2026-05-31。

裁决：`full_run_complete`。

关键结果：

- 交易日范围为 2017-01-03 到 2026-05-29，共 2,281 个 sessions。
- 选入 instruments 4,915 个。
- raw membership rows 471,140，executable membership rows 470,682。
- qlib provider check 通过。
- AkShare 数据源可用；状态过滤包含 SZ dated ST 与 SH lifetime ST exclusion 策略。

结论：PIT 数据地基可用于后续研究，但后续 top-N universe 仍需承认 available-source caveat。

### 02_big_winner_reverse_lifecycle_profile_v0

目标：从大赢家事件反向观察生命周期，识别低点、修复、确认、延续路径上的可观测结构。

裁决：`reverse_lifecycle_sequence_supported_universal_dominance`。

关键结果：

- big-winner episodes 866 个。
- low-axis matched 851 个，覆盖率 98.3%。
- controls 约为 winners 的 4.55 倍。
- 最强证据不是 t0 单点因子，而是 post-low sequence/path。
- S3 `repair_rank_persistence`、S6 `continuation_discriminator`、S2 `repair_money_vwap` 是核心结构。
- low-day leading factors 弱；ATR SMD 约 0.35。
- EMA60 reclaim 可观察，但 false-repair rate 高，controls 中约 74.4% 会出现假修复。

结论：不应简单 "buy low"。更合理方向是 staged repair/confirmation 与 false-repair detection。

## 2. Anchor/Event 与 Recall 扩张

### 03_observable_anchor_event_contract_v0

目标：把 02 的 lifecycle 画像转成可观测事件合约：`first_ema60_reclaim -> rank jump -> rank persistence`，在 rank persistence close 作为 t0，以下一 open 进入标签。

裁决：`event_contract_sample_blocked`。

关键结果：

- event count 与可执行性本身可用。
- 但 `baseline_false_repair_excluded` match coverage 不达标：all 63.5%，validation 54.8%。
- E_S3 改善 `confirm_20`，但同时增加 `failure_10`。
- forward20 edge 小或在稳健性上为负。

结论：可观测 anchor 不是 universal entry。03 证明事件合约可以被构造，但不能直接作为 entry contract。

### 04_high_recall_repair_event_candidate_generator_v0

目标：在 02/03 基础上扩大高 recall candidate pool。

裁决：`candidate_generator_total_recall_blocked`。

关键结果：

- target episodes 866。
- before-first-50 actionable recall：all 55.3%，validation 59.2%，robustness 54.6%。
- low+30 fixed recall 39.5%，low+20 fixed recall 23.6%。
- reclaim-based recall before-first 69.6%。
- density 和 executability 可接受。
- event-anchored +120d positive rate 低，validation 约 6.4%，false repair 高。

结论：04 是 candidate pool，不是 signal。它提高了候选覆盖，但没有解决 precision 和 false repair。

### 05_pit_topn_400_100_universe_v0

目标：构建 PIT top-N proxy universe：主板 top 400，创业板 top 100，按 PIT 市值形成日度 500 成员。

裁决：`topn_universe_candidate_panel_blocked`。

关键结果：

- active source gap 229，source gap 318。
- 精确历史 top-N 不被当前数据源完全支持。
- 仍可作为 available-source top-N proxy 使用，但必须带 caveat。

结论：05 未给出严格 top-N 真值 universe，但提供了后续 06-08 的可用 proxy 分母。

### 06_rerun_02_reverse_lifecycle_on_topn_universe_v0

目标：在 05 的 top-N proxy universe 上重跑 02 反向生命周期画像。

裁决：`topn_reverse_lifecycle_sequence_supported_universal_dominance`。

关键结果：

- big-winner episodes 从 866 增至 2,493，约 2.88 倍。
- denominator 为 912,851 evaluated instrument-days，3,622.4 universe-years。
- episode rate 为 68.82 per 100 universe-years。
- S3 与 S6 仍最强。
- risk_on 与 ChiNext episode density 高，但 matched comparison 显示 regime 本身不能完全解释 winner/control 差异。

结论：02 的 lifecycle sequence 在 top-N proxy 分母上复现。此分母成为 07/08 的基础，但 available-source caveat 继续保留。

### 07_topn_multichannel_repair_candidate_generator_v0

目标：在 06 分母上构造多通道 repair candidate union。

裁决：`topn_multichannel_candidate_generator_density_blocked`。

关键结果：

- before-first-50 any-event recall：all 72.0%，validation 79.3%，robustness 68.9%。
- density mean/p95 可接受，executability 99.9%。
- 被密度拖累的通道主要是 E2 与 E6：canonical share 高但 incremental recall 很小。
- E1 单独 recall 71.1%，几乎等同 full union，且只有约 45% density。
- +50 bridge recall 未改善：34.8%，旧 04 reference 为 35.2%。

结论：E1 是 repair candidate backbone。E2 更适合作为 feature/confirmation，E6 更像 continuation readout。高 recall 仍不等于 precision。

## 3. Risk-on、Fast-fail 与 Layered Rejector

### 08_risk_on_transition_recall_exploration_v0

目标：探索 risk_on/transition regime 下的 recall source、成本压缩和 transition 子结构。

总裁决：`risk_on_transition_recall_exploration_density_blocked`。

分项裁决：

- A: `density_fast_fail_audit_partial_source_complete`
- B: `regime_family_matrix_source_caveated_complete`
- C: `risk_on_r_series_ranker_source_caveated_complete`
- D: `post_replay_retention_source_source_caveated_complete`
- E: `risk_on_cost_rejector_feature_source_caveated_supported`
- F/G: diagnostic transition only
- H: `risk_on_cost_rejector_diagnostic_only_or_no_candidate`
- I: `transition_previous_regime_context_cost_rejector_diagnostic_no_uplift`

关键结果：

- R-core/R6 是强 risk_on recall source，但密度高、成本重。
- R-core risk_on post-replay recall：train 98.2%，robustness 94.5%。
- E/H cost rejector 在 OOS 有稳定信号：robustness ROC-AUC 约 0.686，top-decile lift 约 2.03。
- 但 threshold frontier 很窄：
  - keep_0800 训练 recall 90.045% 通过，但 cost reduction 14.139% 不足；
  - keep_0775 cost reduction 15.345% 通过，但 recall 89.140% 不足。
- transition residual label 不稳定；previous-regime context OOS 反而更差。

结论：risk_on 有 recall source，瓶颈在 cost/fast-fail/false-repair sorting。transition 线冻结，不再消耗主线研究预算。

### 09_riskon_fastfail_label_feature_uplift

目标：围绕 08 的成本拒绝器瓶颈，重定义 fast-fail label、构建 feature foundation，并尝试 uplift。

09A 裁决：`09A_label_frontier_candidate_source_caveated_selected`。

- 选定 `break_swing_low_20` 为 primary fast-fail label，`fixed_mae10_neg_12` 为 sensitivity。
- `break_swing_low_20` train positive rate 7.543%，winner injury 3.706%，episode retention 100%。
- 但 non-winner hit 仅 8.38%，更像保守标签而非强筛选器。
- hybrid target 几乎被 false-repair dominated。

09B 裁决：`09B_feature_foundation_complete`。

- 构建 41,937 target binding rows。
- feature matrix 为 40,050 x 56。
- fast-fail-only 主要读 FS2 basis/path。
- false-repair/hybrid 主要读 FS0/FS3。

09C 裁决：`09C_riskon_cost_rejector_diagnostic_only_or_no_candidate`。

- hybrid model OOS 有信号：robustness AUC 0.6664，top-decile lift 1.9979。
- 但无 research-entry：
  - selected keep_7000 cost reduction train 20.34%，robustness 22.54%；
  - winner retention 仅约 67%-70%；
  - OOS rejected spread fail；
  - fast-fail attribution negative；
  - density cap fail。

结论：成本信号存在，但 winner retention 不足。fast-fail mechanism 没有给出可部署增量；不能靠调 threshold 解决。

### 10_riskon_layered_rejector_system_v0

目标：把 09 的信号改写为分层 rejector system，先处理密度和 fast-fail，再尝试 false-repair。

10A 裁决：`10A_density_population_source_caveated_frozen`。

- same-instrument cooldown 10d suppress 约 48.5% R-core rows。
- admitted events 15,802，winners 2,647，fast-fail 1,280，false-repair 5,033。
- density p95 = 1，rolling 10d density 0.1。
- 10A 只是 frozen population，不是 signal。

10B 裁决：`10B_fast_fail_structural_gate_source_caveated_supported`。

- 选定 10A default 与 `keep_9400`。
- train reject 6%，captures 26.5% fast-fail。
- winner retention 94.03%，接近但略低于 6% wrong-kill cap。
- train utility 0.2813。
- validation/robustness 未出现严重 reversal。
- 相对 rule-only 的 robustness lift 约 +5.26pp。

10C 裁决：`10C_false_repair_feature_source_supported`，但没有 selected gate。

- full/keep_9000 rejects 10%。
- train false-repair lift +7.80pp，exposure lift +6.90pp，utility +0.0795。
- 但 E1-missed retention 84.34% 低于 85%，validation retention collapse。

补充画像裁决：`big_winner_archetype_profiling_statistics_complete`。

- PIT-filtered winners 3,075。
- 大赢家高度异质。
- risk_on winners 更慢、drawdown 更深。
- 10C injury 集中在 shakeout/volatile/gap。

结论：10B 是当前最强的 source-caveated risk-defense gate；10C 不能作为 winner-safe false-repair gate。10B-only cascade 是当时可保留的基线，但仍非 production。

## 4. Archetype Proxy、C0 State-change 与 Morphology 失败链

### 11_archetype_proxy_validation_system_v0

目标：验证 regime 与 t0 archetype proxy 能否形成 payoff/risk screen 或两阶段策略。

11A0 裁决：`11A0_regime_pit_available_stable_supported`。

- risk_on/risk_off/transition 在 t0 可用。
- risk_on/risk_off 稳定，transition provisional。

11A1 裁决：`11A1_archetype_proxy_robust_payoff_risk_screen_empty`。

- strict risk_on and PIT-valid evaluated rows 4,665。
- 8 个 t0 proxies 无一通过 right-tail/payoff/failure/matched-base/top-k。
- P4/P6 有 winner uplift，但 failure 也上升。
- P7/P8 太宽。

11A2 裁决：`11A2_post_t0_archetype_path_divergence_separation_detected_tradable`，但仅 diagnostic。

- winner vs failure proxy 在 post-t0 K=3 后出现 return 与 structure 分离。
- tradability lag 可接受，但不授权 routing/entry。

11B 裁决：`11B_archetype_protected_retention_statistics_incomplete`。

- 10C keep_9000 reference slice retention 与 10C frontier reconcile drift > 0.02。
- PIT-valid train 无明显 retention injury，robustness 模糊，validation low power。
- shakeout winners 最受伤。

11C 裁决：`11C_two_stage_policy_statistics_incomplete`。

- K3 wait-confirm 减少 failure exposure，但仍为 negative EV / exposure-day，并损失 winners。
- trial sizing 更差。

结论：t0 archetype proxy 不能形成 robust payoff/risk screen。post-t0 divergence 存在，但不能转化为 entry/routing 策略。

### 12_multi_k_winner_failure_path_morphology_research_v0

目标：围绕多 K 路径形态、state-change candidate、meta-label、fast-fail defense、stage-2 continuation 继续寻找可用结构。

主要裁决链：

- 12A0/A1: `12A1_r_core_recall_benchmark_only`。R-core raw recall 高但 precision 低，降级为 recall benchmark。
- 12A2: `12A2_state_change_candidate_generation_supported`。C0 生成 28,691 primary canonical events，next-open executable 100%，density 7.9204 events/inst-year。
- 12A3: `12A3_state_change_backbone_partial_feature_source`。C0 low-to-high recall 98.6%，但 precision 5.32% 低于 R-core 6.39%，不能当 backbone。
- 12A4: `12A4_meta_label_partial_feature_source`。risk_on C0 model 可把 robustness top bucket precision 提到 11.86%，但未达 13.90% gate，bad-side 升至 40.59%。
- 12A5A: `12A5A_no_decoupling_stop_keep_feature_source`。bad-side 与 winner 不稳定可分，停止 standalone timing。
- 12A6: `12A6_survival_threshold_candidates_supported`。可形成 survival episode label candidates，例如 `survival_U0.10_L0.20_H120`，但不是策略。
- 12A6b: `12A6b_c0_fast_fail_survival_uplift_partial`。C0 是 high-vol continuation opportunity，不是 survival filter。
- 12A6c: `12A6c_stage1_partial`。stage thresholds transport fail。
- 12A7: `12A7_simple_backbone_supported_complex_model_not_supported`。rank transport 好于 absolute thresholds；复杂模型输给简单 low-vol/defense backbone。
- 12A7b: `12A7b_simple_backbone_supported_low_capacity_not_supported`。`volatility_20d` ascending、X=0.30 对 fast-fail defense 有稳健效果，robust fast-fail 14.30%，相对 random delta -8.20pp，CI [-9.96, -6.37]。
- 12A7c: `12A7c_blocked_input_or_stage1_anchor_failure`。stage-2 decoupled continuation 在 true survivors 中有信号，但 random replay gates fail。
- 12A7d: `12A7d_stage2_signal_diagnostic_only`。chained stage-2 robustness rate 0.129 vs random 0.1039，delta +2.51pp，但 CI 跨 0。
- 12A7e: `12A7e_x030_defense_optimal_for_downside_not_winner`。X=0.30 更像 participation throttle；X=0.20 因 fast-fail penalty 更合适。
- 12A7f: `12A7f_c0_winner_enrichment_weak_or_horizon_dependent`。C0 winner enrichment 弱且 horizon-dependent。
- 12A7g: `12A7g_baserate_only_not_separable_stop_winner_selection`。vol-scaled label 稳定、C0 entry 弱、deployable stage2 无 separability/negative utility。

结论：12 最大收获是防守侧：简单 `volatility_20d` 低波/防御 backbone 有价值。C0 可以作为 feature source 或 defense/participation context，但不能作为 winner selector。

### 13_full_pit_native_event_discovery_v0

目标：摆脱前面手工 morphology，用 full-PIT native token / directional filter / residual / nonlinear / delayed entry / survival overlay 重新挖事件。

裁决链：

- 13A: `13A_no_native_token_survives_stop_event_mining`。`volatility_20d__bottom_20pct` 有 winner enrichment，但 bad-side/lower-first 同时放大，utility negative。
- 13A2: `13A2_no_directional_filter_survives_stop_event_mining`。162 个 directional filters 无候选通过 train selection，control quality 为 0。
- 13A3: `13A3_selected_composite_state_not_supported`。`repair_range_participation_core_30` winner uplift positive，但 left-tail 同时上升，validation 0bps utility negative。
- 13C: `13C_stop_residual_probability_only_no_utility`。morphology controls 后仍有 residual winner/ranking info，但 selected-state residual utility 不正。
- 13E: `13E_stop_no_nonlinear_auc_improvement`。HGB 非线性模型不优于 logistic baseline。
- 13F: `13F_stop_no_delayed_utility_improvement`。k=3 delayed entry 降低同事件 utility。
- 13G: `13G_stop_label_panel_only_no_overlay_utility`。overlay 避免 83%-88% bad-side，但只保留 10%-12% winner opportunity，utility 变差。

结论：full-PIT native mining 没有找到可部署 native event。弱 residual signal 不能变成 utility。

### 14_full_native_sparse_state_change_event_utility_preflight_v0

目标：进一步测试 full-native sparse state-change event 是否能直接形成 utility。

14A 裁决：`14A_diagnostic_cohort_signal_only_no_utility`。

- sparse events 构造成功，raw opportunity 存在。
- 唯一 density-split-pass raw arm 是 F4 board rank jump ret60 jump3。
- 最好 F4/C3/top20pct：train utility +0.00356，validation -0.00372，robustness +0.00902，但不优于 raw-all robustness。
- same-event 50bps utility gate fail，且有 morphology rediscovery。

14C 裁决：`14C_stress_cohort_rank_monotonicity_not_supported`。

- C3 rank 有 bad-side suppression point estimate，但 validation bootstrap CI 跨 0。
- C5/C6 diagnostic 更好但不是 primary。

结论：14 没有提供 confirmatory defense overlay 或 utility-positive sparse event。14B 不被授权。

### 15_path_defined_winner_episode_label_v0

目标：怀疑 fixed 120d winner label censoring 造成问题，改用 path-defined winner episode label，并验证 path shape taxonomy。

15A 裁决：`15A_material_censoring_but_slow_winner_overlaps_known_failed_morphology`。

- fixed 120d 严重 censor slow path winners。
- up50 train path winner rate 60%，fixed120 16.28%。
- share beyond 120d 约 72.86%，all share beyond 71.22%。
- 但 slow winners 与已失败 morphology 高度重叠。

15B 裁决：`15B_no_stable_path_shape_taxonomy`。

- realized path types 可描述，但不稳定。
- unclassified 约 34.5%。
- validation 只有 1 个 material path type。
- representative taxonomy disagreement 72.65%。

15C 裁决：`15C_entry_phase_reduces_heterogeneity_but_coverage_insufficient`。

- outcome-relative phase 能降低异质性，但 PIT-observable phase 不优于 random。
- coverage 过低：single subtype 11.88%，mixed 82.23%。

15C2 裁决：`15C2_winner_shape_not_real_over_baselines`。

- soft membership atlas 只是描述性。
- primary sharpness 没有超过 cluster-blocked baseline。
- winner shape 是连续谱，不适合部署为 t0 label。

结论：fixed 120d censoring 是真实问题，但 path-defined label 没有给出可预测、可部署的 winner shape taxonomy。它直接推动 Episode 16 从 "预测整段 winner path" 转向 "持有中逐段 continuation"。

## 5. Sequential Continuation 主线

### 16_winner_episode_sequential_sampling_geometry_preflight_v0

目标：承接 15 的失败，不再预测终局 winner path，而是问：如果只在持有过程中逐段判断是否继续参与，non-overlap sequential sampling、continuation label、score、policy、utility 是否能形成可审计链条。

最终裁决：`EP16_closed_no_next_requirement`。

总授权状态：

```text
next_allowed_requirement = none
continuation_as_action_mainline_closed = true
payoff_aligned_label_redo_authorized = false
16F_chained_action_transition_freeze_authorized = false
16B2_payoff_aligned_label_redesign_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

#### 16A Sampling Geometry

裁决：`16A_sampling_geometry_ready_for_sequential_label_design`。

关键结果：

- selected threshold 为 `up50pct`，primary horizon 为 20 sessions。
- 推荐 sample unit 为 `non_overlapping_time_blocked_sampling_geometry_step`。
- h20 anchor overcount 明确：
  - train anchor 57,524，episode clusters 667，full-horizon steps 20,245；
  - robustness anchor 11,302，episode clusters 218，full-horizon steps 2,496；
  - validation anchor 1,083，episode clusters 45，full-horizon steps 664。
- anchor-to-full-horizon ratio：train 2.8414，robustness 4.5280，validation 1.6310。

结论：anchor 不能作为独立样本。后续所有 sequential 研究必须使用 non-overlap / episode-cluster discipline。

#### 16B Continuation Label Design

裁决：`16B_continuation_label_ready_for_separability_diagnostic`。

Primary label：

```text
continuation_survival_h20_no_deep_drawdown
positive = max_drawdown > -0.10 and step_end_return >= 0
negative = max_drawdown <= -0.10
neutral = neither positive nor negative
```

关键结果：

- train: labelable 20,245，positive 10,078，negative 4,884，neutral 5,283。
- robustness: labelable 2,496，positive 1,346，negative 526，neutral 624。
- validation: labelable 664，positive 325，negative 180，neutral 159。
- label 不退化，neutral 占比约四分之一，必须单独保留。

结论：h20 continuation survival label 形式可用于 separability diagnostic，但不代表 action utility。

#### 16C Separability

裁决：`16C_sequential_continuation_separability_ready_for_policy_preflight`。

关键结果：

- 使用 27 个 t0 observable primary features。
- ridge logistic 在 train-only grouped CV median AUC 0.675971，purged chronological CV median AUC 0.646587。
- OOS robustness AUC 0.672220，PR-AUC lift 0.099183，cluster bootstrap AUC CI low 0.647004。
- validation AUC 0.610632，仅作为 stress readout。
- non-known-failed robustness AUC 0.688768，说明 signal 不只来自 15B known-failed morphology context。

结论：持有中 t0 状态对下一 h20 survival/no-deep-drawdown 有真实 OOS separability。这个结论成立，但仍不等于交易授权。

#### 16D Policy Preflight

裁决：`16D_policy_preflight_ready_for_utility_diagnostic`。

Primary policy：

```text
defense_bottom_30pct_continuation_score_v1
defend if score <= 0.457071
```

关键结果：

- train defense precision 51.21%，高于 negative base rate 32.64%，lift +18.57pp。
- robustness defense precision 49.37%，高于 negative base rate 28.10%，lift +21.27pp。
- validation defense precision 51.27%，lift +15.62pp。
- robustness negative capture 37.26%，positive sacrifice 14.93%。
- negative leakage 仍高：robustness 62.74% negative 被 continue。

结论：score 能富集 negative risk，可进入 utility diagnostic。但 positive sacrifice 与 negative leakage 已经显示后续 utility 风险。

#### 16E Utility Diagnostic

裁决：`16E_utility_diagnostic_not_supported`。

Primary semantics：

```text
full_avoidance_cash_h20_close_to_close_v1
primary cost = 50 bps
baseline = blind_continue_next_h20
defend exposure = 0.0
continue exposure = 1.0
```

关键结果：

- 50bps full-denominator mean incremental return：
  - train -0.002316；
  - robustness -0.005529；
  - validation -0.005812。
- 0bps 下仍为负：train -0.000937，robustness -0.004556，validation -0.004434。
- drawdown avoidance gate 通过：
  - robustness defended-negative drawdown avoided mean 0.164024。
- 但 defended positive opportunity cost 压倒 avoided negative：
  - robustness defended_positive incremental sum -32.499665；
  - defended_negative incremental sum +15.693211；
  - defended_neutral incremental sum +3.005729；
  - full-denominator net -13.800725。
- non-known-failed context train/robustness 也失败。

结论：16D 的分类价值没有转化为 positive utility。16E 只能解释为 drawdown reduction only，不授权 16F chained simulation。

#### 16E-postmortem

裁决：`16E_postmortem_mainline_closed_no_path_supported`。

关键结果：

- no-new-computation audit 通过；没有新 return/cost/drawdown/refit/threshold/action semantics。
- 厚尾错配存在：defended positive upside 高于 all positive，robustness mean ratio 1.3127，q75 ratio 1.3966。
- 但 directionality gate 失败：
  - train score-decile payoff Spearman 0.903030；
  - robustness 0.030303；
  - validation 0.054545。
- robustness 中 survival base rate 随 score 上升，但 realized h20 return 在中段 D5 达峰后回落。
- A/B/C 三条修补路径都不授权：
  - utility-weighted objective；
  - risk-budget overlay；
  - participation filter。

结论：survival probability 与 realized payoff magnitude 在 OOS 上解耦。不能继续在旧 survival score 上调 threshold、套 overlay 或改名为 meta filter。

#### 16X Payoff-aligned Continuation Label Power Precheck

裁决：`16X_payoff_precheck_not_supported`。

目标：在 16E-postmortem 关闭 survival-score 主线后，检查把 target 换成 realized h20 payoff severity 是否具备 OOS payoff rank separability。

关键结果：

- lineage / feature contract / power / search accounting 全部 pass。
- 使用同一 16C frozen 27-feature contract。
- payoff target 来自既有 `step_end_price_ratio_minus_one_for_label_rule`，未重算价格。
- train payoff rank IC 0.186701，高于 survival 0.157138。
- robustness payoff rank IC 0.051877，低于 0.06 floor。
- robustness payoff minus survival = -0.000723，没有正增量。
- robustness decile monotonicity Spearman 0.163636，未达 0.6。
- cluster-bootstrap CI [0.007706, 0.097324] 排除 0，只说明弱信号存在，不说明值得重链。

结论：payoff target 有弱 OOS rank signal，但太弱、不单调、且不优于 survival probe。Episode 16 不授权 16B2 payoff label redesign。

## 6. 截至 Episode 16 的研究日志总评

按研究演化看，02_AFML_BIG_WINNER 走过了六次关键范式转换：

1. 从 stock-day winner label 转向 episode lifecycle。
2. 从低点预测转向 staged repair/confirmation。
3. 从全市场候选转向 top-N/risk_on recall source。
4. 从 recall generator 转向 cost/fast-fail/false-repair rejector。
5. 从手工 morphology 转向 full-PIT native state-change 与 path-defined label。
6. 从终局 winner shape 转向 sequential continuation-as-action。

每一次转换都保留了某些真实信号，但最终瓶颈高度一致：信号能排序概率或风险，却不能稳定排序 payoff/utility。Episode 16 的 closure 是这一模式的最新、最清晰版本：survival 可分性和 negative-risk 富集成立，但 action utility 失败；payoff-aligned 重做预检也没有足够 OOS separability。

因此，当前 topic 级日志的最后状态是：

```text
deployable_strategy_found = false
production_signal_authorized = false
continuation_as_action_mainline_closed = true
strongest_supported_components = risk-defense / feature-source / diagnostic readout
main_unsolved_problem = OOS payoff/utility ranking, not recall
```

## 7. 主要来源索引

- `README.md`
- `research_direction_discussion_20260614.md`
- `topic_retrospective_20260625_short.md`
- `experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/outputs/reports/data_prepare_final_report.md`
- `experiments/pending/02_big_winner_reverse_lifecycle_profile_v0/outputs/publishable/reports/reverse_lifecycle_profile_report.md`
- `experiments/pending/03_observable_anchor_event_contract_v0/outputs/publishable/reports/observable_anchor_event_contract_report.md`
- `experiments/pending/04_high_recall_repair_event_candidate_generator_v0/outputs/publishable/reports/high_recall_repair_event_candidate_report.md`
- `experiments/pending/05_pit_topn_400_100_universe_v0/outputs/publishable/reports/pit_topn_400_100_universe_report.md`
- `experiments/pending/06_rerun_02_reverse_lifecycle_on_topn_universe_v0/outputs/publishable/reports/topn_reverse_lifecycle_profile_report.md`
- `experiments/pending/07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/reports/topn_multichannel_candidate_generator_report.md`
- `experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/08_all_experiments_final_report.md`
- `experiments/pending/09_riskon_fastfail_label_feature_uplift/outputs/publishable/reports/09A_fast_fail_label_frontier_report.md`
- `experiments/pending/09_riskon_fastfail_label_feature_uplift/outputs/publishable/reports/09B_feature_foundation_ablation_report.md`
- `experiments/pending/09_riskon_fastfail_label_feature_uplift/outputs/publishable/reports/09C_riskon_cost_rejector_uplift_report.md`
- `experiments/pending/10_riskon_layered_rejector_system_v0/outputs/publishable/reports/10A_density_rule_system_report.md`
- `experiments/pending/10_riskon_layered_rejector_system_v0/outputs/publishable/reports/10B_fast_fail_structural_gate_report.md`
- `experiments/pending/10_riskon_layered_rejector_system_v0/outputs/publishable/reports/10C_false_repair_rejector_report.md`
- `experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/reports/11A0_regime_pit_availability_audit_report.md`
- `experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/reports/11A1_archetype_proxy_robust_payoff_risk_audit_report.md`
- `experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/reports/11A2_post_t0_archetype_path_divergence_diagnostic_report.md`
- `experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/reports/11B_archetype_protected_retention_readout_report.md`
- `experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/reports/11C_two_stage_observed_state_policy_replay_v0_report.md`
- `experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/outputs/publishable/reports/*`
- `experiments/pending/13_full_pit_native_event_discovery_v0/outputs/publishable/reports/*`
- `experiments/pending/14_full_native_sparse_state_change_event_utility_preflight_v0/outputs/publishable/reports/*`
- `experiments/pending/15_path_defined_winner_episode_label_v0/outputs/publishable/reports/*`
- `experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/episode_16_final_report.md`
- `experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/sequential_sampling_geometry_preflight_report.md`
- `experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/sequential_continuation_label_design_diagnostic_report.md`
- `experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/sequential_continuation_separability_diagnostic_report.md`
- `experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/sequential_continuation_policy_preflight_report.md`
- `experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/sequential_continuation_utility_diagnostic_report.md`
- `experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/continuation_utility_failure_postmortem_report.md`
- `experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/reports/payoff_aligned_continuation_label_power_precheck_report.md`


---

## 8. 2026-10-21 增补：EP17—EP29 研究日志

> 版本来源：截至 commit `ab048ce7f361743f3d846b76986ae0c11b30690b` 的已发布实验。上方第 0—7 节为 2026-06-30 封存的 **EP1—EP16 历史记载**，不是截至 EP29 的当前状态。以下“支持”均限定对应报告的样本、标签、时点和证据等级；`pending/` 表示目录位置，不等于实验尚未跑完，也不表示生产授权。
>
> **统一判定：截至 EP29，无可独立确认、可部署且持续优于可比简单基准的投资策略。** 历史探索中存在价格路径、尾部风险、短期收益排序的局部信号；其经济效用、校准、市场状态稳定性或真正前瞻泛化未形成完整证据链。

### EP17 — Oracle Action Value Upper Bound

[主要报告](experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/reports/ep17_oracle_action_value_diagnostic_report.md)

- 裁决：`oracle_payoff_state_research_allowed`，仅授权 payoff-state 表征研究。
- 在固定行动空间及 50bps 成本条件下，robustness 的完美效用 Oracle O5 平均增量回报约 **+2.9467%**；路径/标签 Oracle O1/O4 约 +2.4681%，回撤 Oracle O2 约 +1.8511%。
- Oracle 使用不同程度的未来信息，**不是可以交易的回测成绩**。意义是行动空间存在事后上限价值，而现有可观察特征未能逼近它。

### EP18 — Payoff-state Representation / Utility Bridge

[18F 报告](experiments/pending/18_payoff_state_representation_research/outputs/publishable/reports/payoff_state_oracle_gap_bridge_report.md)

- 裁决：`18F_utility_bridge_not_supported`。
- 学习模型的 `defend_bottom30_continue_rest` 在 robustness 全分母的增量回报为 **−1.0552%**，而 Oracle O5 为 +2.9467%；被错误防守的正收益机会超过避开的负收益。
- 冻结训练阈值在 robustness 实际防守比例由 30%升至44.11%，暴露分布迁移。**排序证据不等于行动效用证据**，不能继续将 survival/ranking score 直接阈值化为仓位规则。

### EP19 — PIT Entry Universe / Double-tail Exposure

[结题报告](experiments/pending/19_entry_universe_pit_tradability_preflight/outputs/publishable/reports/episode_19_final_report.md)

- 裁决：`EP19_closed_entry_enrichment_only_no_tradeable_alpha_path`。
- 建立 close-observed、next-executable-open、cooldown、成交可行性和真实候选分母的研究合同。
- B2 在 robustness 具有较高的未来 +50% MFE 机会暴露，但**左尾同步扩大**；静态抑制规则降低左尾也舍弃右尾，不能确认方向性剩余 Alpha。
- EP19 主线关闭；右尾机会率、实际固定期限净收益、相对市场 Beta 的超额收益必须分别报告。

### EP20 — OHLCV / TrendPV / Residual Momentum

[TrendPV/Residual Momentum v5](experiments/pending/20_ohlcv_positive_beta_exposure_research/outputs/20B_trendpv_residual_momentum_design_and_replication_diagnostic_v5_detailed_report_cn.md) · [学习排序诊断](experiments/pending/20_ohlcv_positive_beta_exposure_research/outputs/20B_P4_learned_monotonic_return_ranking_diagnostic_v1/20B_P4_learned_monotonic_return_ranking_diagnostic_report.md)

- **多项子实验，不能归纳为单个通过/失败判决**：P4 市场残差动量点估计存在正向历史迹象，但可评价月份未达预冻结门槛（P4 43 月，相对要求 60 月）；没有确认式授权。
- P4 学习排序 v1 存在指标物化阻断（LambdaRank 常数分数）；冻结的 Full 排序在21个 robustness 月中的十桶聚合 Spearman 为负，叠加交叉因子不改善原始P4。
- 事后事件月份诊断发现高弹性 Risk-on rotation 时交叉因子可反向失效；**不能删除异常月份或把事后新闻标签用于PIT切换**。成本/止损敏感性研究未确认静态行业倾斜或硬止损可修复问题。

### EP21 — REAKA / Koopman / DRC

[21C 已密封实证](experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21C_full_reaka_pit_proxy_replication_v4_detailed_report_cn.md) · [21F 暂定诊断](experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21F_reaka_data_first_reverse_validation_v1.building/21F_v5_data_first_provisional_report.md)

- 21C 裁决：`21C_FULL_r2_direction_not_supported`。Early ensemble RankIC +0.015658，Late −0.002304；不同 seed 的 Top30 重合接近随机，目标换手极高。
- 21E 确认论文未披露的实现细节对结果有实质影响；不能声称作者模型精确复现。
- 21F 对收益输入使用 decision-date 横截面标准化后有**暂定**RankIC增量，但 Top30 身份和换手未稳，`REVERSE_VALIDATION` 未执行，`seal_authorized=false`；不能把未完成的暂定结果改写为正式模型成功。

### EP22 — 四阶段交易方法机制量化

[研究计划](experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/research_plan.md)

- 仓库可见 `research_plan.md`、22A/22B需求和来源叙事，**未找到已发布的正式实证结果/结题报告**。
- 状态：`plan / requirements only`；不得写作已验证、已否定或生产就绪。来自交易者的业绩叙述没有独立验证。

### EP23 — R&D-Agent-Quant PIT 研究迁移

[完整报告](experiments/pending/23_rdagent_quant_pit_replication_v0/EP23_rdagent_quant_pit_replication_full_report_cn.md)

- 总裁决：`model_branch_only_supported`，历史样本经过多轮研究选择，**不是新独立测试**。
- Last-state GRU 相对容量匹配的 Flattened MLP，在五个正式种子的历史 IC/RankIC 均表现为正向增量；完整 next-open 执行状态机中五种子绝对净 ARR 为正。
- 但策略**未超过同期市场和PIT股票池等权**；Winner episode recall 291/545（53.39%），右尾机会富集只有0.872×。严重左尾暴露率较股票池降低（4.59%→1.13%），同时右尾机会暴露率下降（55.55%→48.44%）。
- 价值在于受控模型结构归因与潜在防御性排序；不支持直接部署，也不支持把Agent自动生成代码等同于Alpha。

### EP24 — Conditional Return Distribution Exploration

[研究报告](experiments/pending/24_conditional_return_distribution_exploration/EP24_research_report.md)

- 尝试用波动率、市值、估值、财务、信用、宏观、技术与多种算法预测1/3/6/12月方向和条件收益分布。
- 原双20%多指标、跨期限联合改善目标过于苛刻，**167个候选无一通过**；但失败不仅是门槛问题：相对简单风险/市值条件基线，新因子/模型没有持续可重复的经济增量。
- 早期动态组合暴露降低风险但显著增加现金、牺牲收益；不得把风险降低单独解释为投资优越性。EP24不同子阶段的预测期限/标签口径有过变化，不可跨版混算。

### EP25 — 估值/财务完整分布增量

[最终结论](experiments/pending/25_incremental_distribution_validation/final_conclusion.md)

- 主6个月CRPS：风险/市值基线 **0.146129**，估值+财务候选 **0.147689**，`Δ=+0.001560`（越低越好），95%区间跨0。
- 重复历史中尾部Brier存在局部线索，但不能把同算法 M_R 比较中未确认的差异归因于估值/财务。
- 仅59个重叠预测月份，统计功效有限；控制实验说明管道能够识别已知信号，却不能据此证明A股真实信息增量。

### EP26 — 6个月重大亏损概率

[最终结论](experiments/pending/26_left_tail_probability_validation/final_conclusion.md)

- 主事件固定为 `R_6m < −20%`，27,230已知股票月、4,581事件、59个重叠月。
- M_R（风险/市值同算法）Brier **0.138095**、月内AUC **0.673902**；估值组曾提高风险排序AUC，但联合估值+财务没有稳定Brier增量。
- 整体偏差掩盖2021—2023低估和2024年后高估，概率校准明显漂移。历史风险排序不等于可靠绝对赔率或可交易经济价值。

### EP27 — 分层风险归因

[最终结论](experiments/pending/27_hierarchical_tail_risk_attribution/final_conclusion.md)

- Full 相对市场/行业扩展基线 RMI，Brier **0.141732→0.138253**，点改善2.45%，注册比较时间块区间支持；行业内AUC增量约 +0.0301（只在有限可评价群体）。
- **Full Brier仍略差于更简单的M_R 0.138095。** 主要是估值条件贡献，财务单组贡献不稳；不能把“击败被扩展特征拉差的RMI”解释为“超越最佳简单风险基线”。
- 原始股票池、退市结算、PIT原版本及跨市场状态校准未闭合；行业/风格匹配的组合尾部价值未确认。

### EP28 — 文献驱动风险机制迁移

[最终结论](experiments/pending/28_literature_guided_tail_risk/reports/final_conclusion.md) · [数据审计](experiments/pending/28_literature_guided_tail_risk/reports/data_integrity.md)

- L1共同尾部、L2市场/行业/个股风险结构、L4量价分歧迁移到相同的6个月重大亏损标签；L3财务困境变化因首次财报版本及公式/字段不完备停止，**不能判断该机制无效**。
- L2 Brier **0.136503**，相对M_R点改善约1.15%，但主比较95%区间 **[−0.004729,+0.001089]** 跨0；月内AUC约0.695。去掉残差风险特征组的消融有历史增量，不能归为单一特质波动因子的已确认作用。
- L2的2021—2023与2024年后主效应变号；月均ECE约0.11。部分CHS价量历史特征改善未来偏度目标，但不是6个月累计−20%事件成功。
- 恢复228只过去缺价退市证券的公开历史报价；恢复报价子群已知事件率30.61%，旧报价群体14.22%，**两组人群不可直接比较**；退市结算/公司行动及D1完整PIT训练样本仍未认证。未完成任何原市场Level A忠实复现，也没有确认真实执行经济价值。

### EP29 — Global / Peer / Individual Adaptation

[最终结论](experiments/pending/29_global_stock_adaptation/reports/final_conclusion.md) · [统计报告](experiments/pending/29_global_stock_adaptation/reports/statistical_validation.md)

- 五模型：G全局Brier **0.138095**、GP全局+同行 **0.138327**、GI全局+个股 **0.138036**、GPI联合 **0.138272**、L纯局部 **0.138553**。
- 主比较GPI−G = **+0.000177**，95%区间跨0；同行迁移没有总体增量，联合适配未优于全局。GI−G = **−0.0000593**（约0.043%相对改善），仅为极小的探索性公司历史边际线索，主要出现在2024年后；公司等权与前瞻证据不支持推广。
- 全29,596预测行仅2,663行触发个股修正（约9%），其余大多因样本少、独立风险窗口不足或效应不稳回退。预选40家公司仅866条已知标签，月份等权与公司等权结论相反。
- 单股案例万科A：59个成熟重叠月、27个重大亏损标签仅5个合并风险阶段；GPI均值预测15.88%，实际重叠标签事件率45.76%，依旧明显失准。真实新样本与可用于仓位的概率尚未获得。

## 9. EP1—EP29 跨阶段归纳（研究判断，不是新实证）

| 证据链 | 主要实验 | 当前结论与边界 |
| --- | --- | --- |
| 右尾生命周期、修复、持续 | EP2/3/6/7 | 事后结构强；前瞻入场精度、匹配覆盖和经济效用不足 |
| 事件召回、坏侧拒绝、动作效用 | EP8—EP18 | 常能规避部分负面路径，但正收益机会牺牲和现金拖累较大 |
| PIT入场、方向性Alpha、复杂模型 | EP19—EP23 | 市场/个股排序局部线索；EP22只有计划；EP23模型增量不等于超越股票池等权 |
| 完整收益分布 | EP24—EP25 | 新增估值/财务等特征没有建立稳定分布预测增量 |
| 6月−20%亏损概率 | EP26—EP28 | 传统波动/市值排序与L2风险结构线索；绝对概率校准和经济价值不支持 |
| 全局→同行→个股 | EP29 | 同行和联合适配未改善整体预测；极小个股修正线索未具跨公司/前瞻支持 |

跨阶段核心教训：

1. 观察到 `P(特征 | Winner)` 的后验区别，不等于已验证 `P(Winner | PIT特征)`。
2. 未来MFE/MAE、Winner episode recall、月内AUC、CRPS、RankIC、净组合收益都是不同的 estimand，不能跨事件/样本/期限直接排名。
3. 风险排序、绝对概率校准、收益排序和行动净效用必须分开评分；过滤尾部事件可能同时牺牲巨大右尾。
4. 时间状态漂移、重叠标签、反复审视历史造成的研究选择，以及ST/退市/公司行动/PIT数据缺口，在所有正面结果解释时必须优先披露。
5. 有些“失败”是数据/统计功效或复现条件未满足，不能解释成相应经济理论已被证伪。

## 10. 下一步执行边界与研究提议（尚未授权的新实验）

**P0 数据闭合**：历史时点股票池、ST和退市收益、公司行动、首次财报及估值历史版本、停复牌可交易性。EP28恢复报价不等于D1全部可用。

**P1 前瞻冻结**：遵守EP27—EP29已有协议；最早计划2026-10-30真实月末，当日生成不可改写的M_R、L2、G/GP/GI/GPI等注册概率，六个月标签到期后再追加；这只是一项协议，当前尚无真实前瞻记录。相同市场月不得计作多份独立验证。

**P2 两条预测研究分离**：收益机会线谨慎保留EP20/EP23历史线索；条件风险线保留M_R、L2、GI作研究对照。不得按历史成绩自行修改已经冻结的前瞻候选或选股规则。

**P3 经济价值合同**：将未来买入/持有/过滤/退出的行动定义、机会成本、敞口、延迟、现金、退市结算、净收益和ES预先冻结；不能把风险控制改善或“跑赢弱模型”当成完成投资闭环。

**当前状态**：`deployable_strategy_found=false`；`production_signal_authorized=false`；`independent_forward_confirmation=false`。本段是EP17—EP29追加性主题总结，不覆盖各实验自身授权和封存裁决。

## 11. EP30 D2 PIT 数据基础与缺口审计（2026-10-21）

本轮从模型搜索转向数据地基，交付版本化事实、两类as-of、Parquet/Qlib适配、执行及现金权利标签合同、源/字段覆盖矩阵和D0/D1/D2桥接；原EP01—EP29文件按SHA保留，不重训模型。[完整报告与裁决](experiments/pending/30_pit_data_foundation_v1/reports/final_conclusion.md)、[逐域质量门禁](experiments/pending/30_pit_data_foundation_v1/reports/quality_gate_report.md)、[复现说明](experiments/pending/30_pit_data_foundation_v1/README.md)。

4,915与4,819的差额核实为90只首月前退市、6只末月后上市；EP05的229缺源是“请求窗口内曾上市”，不是229只今日正常活跃证券。D2读到4,825只、9,091,310条有效未复权报价，新增625条现时官方身份观察，但5,540条临时身份仍不是认证全历史全A股。旧行情截止2026-05-29未伪装成运行日已更新。

巨潮原始年报与更正公告支持SZ000584一个2023年财务附注字段的PIT-reconstructed回放，证明局部原始版本有可取得路径；不外推全财务域认证。D0的43,960股票月与D1重合旧六个月收益逐值一致，旧D1成熟结果仍缺2,411个。完整历史成员、ST/停复牌、权益和退市结算、全域首次版本与独立人工核查尚缺；严格全市场PIT及可执行总收益标签保持BLOCKED。工程和审计交付完成不等于发放完整PIT READY，后续只追加新数据版本。


## 12. EP30 D2 v2 实际补数（2026-10-21）

按“补足缺失数据”追加独立 v2，见[补数报告](experiments/pending/30_pit_data_foundation_v1/reports/backfill_v2.md)。原始行情增至 5,827 只、10,545,492 条，新增 1,454,182 个证券日；5月末至10月21日的101个交易日窗口全部补采，另对已有历史的13个提前结束候选追加查询，恢复SH600249内部断档。股本历史覆盖5922个临时身份；补入56965条公司行动、984条配股、471份原始年报、1822个财务候选，以及北交所352只当前官方名单、286份原始上市公告、248家代码切换与5条离场原始证据。

52项测试及全部已采原字节重放通过。v1桥表486561行旧列逐值保留，33666个旧缺失/未知起点新增原始收盘观察，原有起点报价在v2的raw缺失数归零；旧收益、D1的2411个到期未知结论和模型均未改写。批量历史字段仍为proxy，实际支付、退市最终权益、全历史成员及财报首次/更正版本未全部补齐。3只早期北交所转板区间仍缺有效A股报价，另2只截至采集日尚未上市，90只在2017年前已退市；均不伪造行情或填0。v2另作独立复制冻结，不覆盖v1与EP01—EP29。


## 2026-10-21：EP30 D2-v3 历史资格与退市权益

按用户要求先补历史资格/状态与退市权益，再重建严格标签并推进财报版本链与全量桥接。新增264份交易所站点历史观察，补回304894个原缺字段，2157个新冲突保留双方并置未知。原文补正7个2026年退市漏标，提取2095条状态事件，67个退市代码对应；229份扫描件完成OCR，147条候选独立待核，未自动认证。

归档3120份选定年报，25999条报告链及8860个数值候选；原v2缺报队列恢复62个公司年度。泰鹏智能2020年经营现金流三版本5字段建立追加修订链，未来更正不提前出现。全量候选月表5823个身份、525917个证券月份，6311004条四期限/三口径严格标签保持UNKNOWN或CENSORED，严格已知0，不把留价或摘牌当作终值。

65项测试和原字节回放、7064个旧保护文件及v1/v2冻结字节核验通过。独立v3封存入口为EP30 outputs/pit_v3/release.json；全部原始PDF和大表保留本地。附件详情源持续567/断连后已停止，267条当前文档缺口可追溯。每日资格、开盘执行、完整现金/股份/退市结算、财报全字段修订和独立人工验收仍阻断完整PIT准入。未训练模型、购买数据或提交推送。详见[本轮报告](experiments/pending/30_pit_data_foundation_v1/reports/pit_v3.md)。


## 2026-10-21：EP30 D2-v4 连续身份纠错与退市后披露

2026-10-21：EP30 追加 D2-v4，三组原件证明的连续代码变更修复重复身份及误报退市，删除155个重复证券月；退市披露代码桥接85家，原缺年报期66→43，重建6309144条严格标签，严格已知仍为0。79项测试通过；旧研究与三版封存保留。详见[本轮报告](experiments/pending/30_pit_data_foundation_v1/reports/pit_v4.md)。

普查10组同披露主体标识，仅合并原件明确连续的000022/001872、000043/001914、300114/302132；其余7组转板、重新上市或历史换股保留待核。暂定身份5922→5919，2017年以来退市/转板分母252→249。原486561条桥接记录及原列保留；原始行情按实际代码区间拼接，未以旧代码终止报价认定权益归零。

18家扫描确权代码原页核验、两条摘牌事实、1183条新增财报披露索引、208份完整年报PDF及15条已核报告值独立追加。长生2018年补发报告自2020-11-24才可见。完整逐日资格、开盘执行、权益流水/实际支付/退市终值、全财务修订和独立人工验收继续阻断完整PIT；未训练模型、购买权限或提交推送。


2026-10-22：EP30 追加 D2-v5，按用户指定将当前收益标签统一为前复权价格变化推断。原 D2 主行情确认未复权；新生成10541309行前复权开收盘可用报价，6309144行标签中6007218行可推断；24只证券的跨供应商复权差异单列标记。旧严格结果保留，未知退市终值不填零。详见[本轮报告](experiments/pending/30_pit_data_foundation_v1/reports/pit_v5.md)。
