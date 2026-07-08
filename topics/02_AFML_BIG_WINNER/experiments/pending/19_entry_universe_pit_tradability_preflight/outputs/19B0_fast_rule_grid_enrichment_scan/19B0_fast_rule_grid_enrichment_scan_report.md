# 19B0 快速规则网格右尾富集扫描报告

## 1. 19A Ready 和 Train-only 边界
- decision_state: `19B0_candidate_family_eligible_for_19B`
- next_allowed_requirement: `requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md`
- validation outcome read: `false`
- robustness outcome used for selection: `false`
- 19A ready 证据来自 upstream contract audit、manifest hash audit 和 frozen output hash 校验。

## 2. 支持/不支持 Family 和 Grid Materialization
- supported primary families: `B1_near_120d_high_plus_volume_expansion, B2_relative_strength_breakout, B4_volatility_contraction_then_breakout, B5_recent_high_close_plus_amount_expansion, B6_low_drawdown_reclaim_or_ema_reclaim, EP07_topn_multichannel_recommended_union`
- unsupported family: `B3_industry_or_theme_breadth_expansion`，原因是 no genuine PIT industry source。

| family | declared_grid_cell_n | materialized_grid_cell_n | materialization_status | blocking_reason |
|---|---:|---:|---|---|
| B1_near_120d_high_plus_volume_expansion | 36 | 36 | materialized_before_label_readout |  |
| B2_relative_strength_breakout | 36 | 36 | materialized_before_label_readout |  |
| B4_volatility_contraction_then_breakout | 36 | 36 | materialized_before_label_readout |  |
| B5_recent_high_close_plus_amount_expansion | 36 | 36 | materialized_before_label_readout |  |
| B6_low_drawdown_reclaim_or_ema_reclaim | 36 | 18 | materialized_before_label_readout |  |
| EP07_topn_multichannel_recommended_union | 1 | 1 | materialized_before_label_readout |  |

## 3. Label Anchor 和 Label Source Map
- 19B0 使用 `executable_next_open_anchored` 标签。
- EP07 `event_anchored` ready-made label 仅作为 diagnostic，不进入 primary metric 或 selection。
- label source map: `executable_next_open_anchored`; label_anchor_rebuild_audit: `{"blocking_reason": "", "entry_anchor_available_n": 7328, "event_anchored_diagnostic_available_n": 7320, "event_anchored_vs_executable_big_winner_120d_match_rate": 0.9991803278688525, "executable_entry_path_complete_120_rate": 1.0, "executable_entry_path_complete_20_rate": 1.0, "executable_entry_path_complete_30_rate": 1.0, "executable_entry_path_complete_60_rate": 1.0, "family_id": "EP07_topn_multichannel_recommended_union", "grid_cell_id": "EP07_identity_cell", "ready_made_label_used_for_primary": false, "ready_made_label_used_for_selection": false, "row_n": 7328, "row_scope": "ep07_train_candidate_rows", "split": "train", "trade_open_price_positive_rate": 1.0}`

## 4. Denominator
- EP07 identity primary denominator: `5116`
- EP07 identity path-complete denominator: `5116`
- materialized family count: `6`
- total candidate denominator rows audited: `181`

## 5. Matching Feature Source Map
- matching feature source map 明确候选与 baseline 使用同一 qfq/universe 重建路径。
- matching keys: `decision_month, market_cap_bucket_asof_decision_date, rolling_20d_amount_bucket_asof_decision_date, rolling_60d_volatility_bucket_asof_decision_date, recent_20d_return_bucket_asof_decision_date, instrument_or_industry_bucket_if_supported`

## 6. Baseline Materialization 和 Matching Quality
- baseline materialization rows: `489`
- baseline matching quality failure blocks residual-alpha attribution only.
- It does not by itself invalidate a positive beta/exposure candidate.
- positive_beta_exposure_candidate 不是 independent alpha / residual alpha claim。

| baseline_family | rows | pass_n | median_smd | median_unmatched_rate |
|---|---:|---:|---:|---:|
| calendar_time_random_same_budget | 163 | 0 | 0.803 | 0.129 |
| instrument_matched_random_same_budget | 163 | 0 | 0.897 | 0.024 |
| liquidity_size_volatility_matched_same_budget | 163 | 0 | 0.374 | 0.296 |

## 7. Metric Readout 和 Positive Beta/Exposure Track
- 三类 baseline 分臂计算，selection 使用 conservative margin-adjusted score。

| family | grid_cell | primary_n | p_candidate_50 | broad_base_rate | conservative_lift | conservative_adjusted | abs_margin | rel_margin | positive_margin | positive_score | promotion_claim_type | lift_margin_pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | 4061 | 0.229 | 0.163 | 1.101 | 0.001 | 0.020 | 0.033 | 0.033 | 0.0340 | positive_beta_exposure_candidate | True |
| B2_relative_strength_breakout | B2-relative-strength-breakout__3206f2976d28 | 4057 | 0.229 | 0.163 | 1.089 | -0.011 | 0.020 | 0.033 | 0.033 | 0.0339 | positive_beta_exposure_candidate | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__d0f0fb1727c9 | 5927 | 0.225 | 0.163 | 1.081 | -0.019 | 0.020 | 0.033 | 0.033 | 0.0297 | positive_beta_exposure_candidate | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__e7b68ff136d7 | 5923 | 0.225 | 0.163 | 1.081 | -0.019 | 0.020 | 0.033 | 0.033 | 0.0298 | positive_beta_exposure_candidate | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__377c3e689ae8 | 6047 | 0.216 | 0.163 | 1.075 | -0.025 | 0.020 | 0.033 | 0.033 | 0.0213 | positive_beta_exposure_candidate | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__1d4b408e8ccc | 7927 | 0.211 | 0.163 | 1.066 | -0.034 | 0.020 | 0.033 | 0.033 | 0.0158 | positive_beta_exposure_candidate | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__0f91aad80911 | 3463 | 0.222 | 0.163 | 1.064 | -0.036 | 0.020 | 0.033 | 0.033 | 0.0267 | positive_beta_exposure_candidate | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__6cc7775eba3a | 7018 | 0.217 | 0.163 | 1.060 | -0.040 | 0.020 | 0.033 | 0.033 | 0.0215 | positive_beta_exposure_candidate | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__6e8b74238e42 | 5058 | 0.223 | 0.163 | 1.058 | -0.042 | 0.020 | 0.033 | 0.033 | 0.0276 | positive_beta_exposure_candidate | False |
| B2_relative_strength_breakout | B2-relative-strength-breakout__ff7adaf093c4 | 3570 | 0.221 | 0.163 | 1.055 | -0.045 | 0.020 | 0.033 | 0.033 | 0.0260 | positive_beta_exposure_candidate | False |

## 8. Sensitivity 和 Instrument Concentration
- sensitivity 指标均为 diagnostic-only: `rows=489, diagnostic_only=True, median_tail_lift_20=1.401, median_tail_lift_60=1.096`
- instrument concentration / top-k removal 风险: `rows=489, max_instrument_candidate_share=0.010, max_instrument_winner_share=0.021`

## 9. Selected Family/Cell Manifest
- selected family/cell pairs: `2`
- selected residual-alpha pairs: `0`
- selected positive-beta/exposure pairs: `2`
- diagnostic family count: `3`
- residual_alpha_correction_scope: `0 * primary_tail_lift_50`
- positive_beta_exposure_correction_scope: `2 * positive_exposure_score_50`
- residual-alpha and positive-beta tracks use separate correction scopes.
- positive-beta 候选若无 19B matched-baseline residual pass，只能支持 `19_entry_universe_enrichment_only_diagnostic`，不授权 EP20 policy preflight。

| selected_family | selected_grid_cell | selection_track | promotion_claim_type | residual_alpha_claim_allowed |
|---|---|---|---|---:|
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | positive_beta_exposure | positive_beta_exposure_candidate | False |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | positive_beta_exposure | positive_beta_exposure_candidate | False |

## 10. Search Accounting 和 19B Handoff
- search accounting: `{"N_family_brought_to_robustness": 2, "N_materialized_family": 6, "N_positive_beta_exposure_candidate_pairs": 2, "N_residual_alpha_candidate_pairs": 0, "N_supported_primary_family": 6, "N_tested_family_cell_pairs": 2, "blocking_reason": "", "cell_level_accounting": "all_tried_cells_counted", "expanded_cell_rule_enabled": false, "family_level_correction": "Bonferroni-Sidak", "positive_beta_exposure_correction_scope": "2 * positive_exposure_score_50", "promotion_claim_type_counts": "{\"positive_beta_exposure_candidate\": 2}", "residual_alpha_correction_scope": "0 * primary_tail_lift_50", "search_accounting_gate": "pass", "selected_cell_rule": "one_train_selected_cell_per_family_by_default", "selection_track_counts": "{\"positive_beta_exposure\": 2}", "track_correction_scope_policy": "separate_by_promotion_claim_type", "validation_selected_cells": 0}`
- N_family_brought_to_robustness: `2`
- N_tested_family_cell_pairs: `2`
- positive_beta_exposure_candidate without matched-baseline residual pass can only support 19_entry_universe_enrichment_only_diagnostic, not EP20 authorization.

## 11. Authorization 和 Final Decision
- final decision_state: `19B0_candidate_family_eligible_for_19B`
- final next_allowed_requirement: `requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md`
- 19B0 不授权模型、entry/exit/holding policy、回测、生产信号或交易。
- 进入 19B 的资格不是 support claim。
- 19B0 不是 robustness confirmation。
- 19B0 不证明策略有效。
- 19B0 不授权 19C replay。
