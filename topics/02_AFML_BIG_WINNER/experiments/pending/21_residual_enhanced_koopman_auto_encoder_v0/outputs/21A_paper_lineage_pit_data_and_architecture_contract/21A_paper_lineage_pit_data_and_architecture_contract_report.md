# EP21A 论文谱系、PIT 数据与架构契约报告

## 1. Decision summary

- decision_state: `21A_pit_timing_or_denominator_contract_blocked`
- critical gates: `27/28` pass
- blocking_reasons: `["pit_membership_timing_gate"]`
- freeze_bundle_hash: `b13636af7716da6dcb31832782e123fb0a56d4edab4626f6c6e073cc5fd8ec99`
- bundle verification error: `none`

## 2. Human restart 与历史授权边界

- historical_sample_role: `design_contaminated_historical`
- historical_support_claim_allowed: `false`

历史 2017-01 至 2026-05 已被本 topic 反复观察，只能作为 design_contaminated_historical；可信支持只能来自最终候选密封后的 forward cohort。

## 3. Paper identity 与公式授权

- title: `Residual-Enhanced Adaptive Koopman Autoencoder: A Deep Latent Dynamics Model for Stock Prediction`
- authors: `Lei Liao|Yang Zhang|Jun Wang|Jinghua Tan|Yinchao Liao`
- DOI: `10.1109/ICASSP55912.2026.11465125`
- pages: `5`
- local SHA-256: `1041d8693c5ef80fcafc613d77f09bf3ec2a2df673f468785255da27d7d9a472`
- authorized formula rows: `23/23`
- official_code_status: `not_disclosed_in_allowlisted_sources`

Official code 或 appendix 未披露不阻断 project adaptation，但必须限制复现 claim。

## 4. Claim ceiling

EP21 只能声明 paper_architecture_grounded_project_adaptation，不能声明 exact_replication 或 paper_result_reproduced。

## 5. PIT universe 与 denominator

- support-ready days (train/validation/historical): `1215/242/579`

U_t_decision 在 outcome 前固定；unknown data gap 和 data cutoff 使整日不可评价，不允许逐股静默删除后改变 denominator。

## 6. Label semantics 与 outcome firewall

- preoutcome hard counts: `{"historical_holdout_outcome_access_count": 0, "outcome_columns_detected_count": 0, "outcome_formula_executed_count": 0, "real_label_materialization_count": 0, "real_model_score_count": 0, "selection_or_tuning_allowed_count": 0}`

21A 没有训练或评价任何真实 outcome model，也没有生成真实股票 score、RankIC 或策略 PnL。

## 7. qfq/raw unit 与 feature route

- primary route: `ALPHA158_NO_VWAP_REGISTERED_ADAPTATION` (`registered_primary_route_adaptation`)
- global overlap/factor/auditable/range: `0.999869357597/0.358485206002/0.999997609888/0.99475744684`

## 8. Alpha158 与 corporate-action sensitivity

- canonical feature rows: `158`
- expression hash: `da50206946efd49cf7103a56561b7a5702503c18f70b4d8c5f48e8c1e9592188`
- exact local materialization: `false`

## 9. Feature-only support、normalization 与 split/purge

Feature support 只使用 membership、截至 feature date 的 bar/history readiness；normalizer 只在 original train 拟合，12-session purge 已在 freeze artifact 固定。

## 10. Source/teacher/inference graph

Primary REAKA 对全部 T 个 shifted transitions 计算 Koopman 和 residual loss；last-transition-only 只能是独立 diagnostic adaptation。

Teacher tensors 只允许构造 train-only Koopman/residual target，并经 residual_target->x_s 影响训练重构/loss；不进入 selector、gate、residual condition 或任何 inference-score ancestor。

## 11. Mandatory arms 与公平性

- mandatory arm rows: `10`
- K1C 的 train/inference mixture 在 batch/time 上全局共享；R1/K1C 参数差异与机制结论按冻结公平性规则处理。

## 12. Search、seed 与 batch ladder

- selected_batch_size: `256`
- model seeds、S01-S06 单因素 sensitivity 与 256→128→64→32→16 ladder 均由 freeze artifact 约束。

## 13. Dependency 与 GPU dry-run

- runtime audit rows: `22`
- GPU gate: `pass`

## 14. Statistics 与 economic boundary

- forward complete-day target: `291`
- RankIC average-rank tie、undefined day、seven-hypothesis Holm family 和 execution ledger 边界均在 freeze 中固定。

## 15. 21F comparator/refit

21F 只前瞻确认 R2 相对预冻结 M1/M3 的预测与执行；21C/21D 模块归因仍是 historical_design_diagnostic。

## 16. Next authorization

- next requirement: `requirement_21b_alpha158_sequence_baseline_benchmark.md`
- generation authorized: `false`
- execution authorized: `false`

21A 成功只允许生成并人工评审 21B requirement，不授权 21B 执行、historical holdout readout、policy、optimization 或 deployment。
