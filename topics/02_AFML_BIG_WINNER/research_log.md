# 02_AFML_BIG_WINNER 研究日志

生成日期：2026-06-30

本文档整理 `topics/02_AFML_BIG_WINNER` 截至 Episode 16 的研究历程。范围包括根目录 `README.md`、`research_direction_discussion_20260614.md`、`topic_retrospective_20260625_short.md`，以及 `experiments/pending/01` 到 `16` 的 publishable/final reports。

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
