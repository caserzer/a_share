# 21B_v6 gate-registry compatibility successor

本 bundle byte-preserving 继承 sealed 21B_v5 的模型、panel、score、metric、QFQ runtime log 与 aggregate evidence；仅将 integration acceptance 正式冻结为唯一 27-row gate registry，并更新版本、root 与 hash closure。未重训、未重选 checkpoint、未访问 historical holdout。

- source sealed inventory hash: `0d16cb3d1c8cdcd620d8b8e9244a367cfea82c8df0dd0737762675ea3b90c806`
- upstream_21b_contract_erratum_gate: `pass`
- gate registry rows: `27`

# 21B_v5 corrected successor

本 bundle byte-preserving 继承 sealed 21B_v4 model/panel/score/metric payload，并通过真实 QFQ cutoff-prefix replay 修正 runtime-counter provenance。

- upstream_21b_contract_erratum_gate: `pass`
- source sealed inventory hash: `daebbe0be139380cf3f6e2580dd300d3fb859c3f4b187a4033ac36061e1dc63f`
- runtime access event rows: `2716`
- post-cutoff value-token/decode counts: `0 / 0`
- historical holdout outcome/label/join/metric counts: `0 / 0 / 0 / 0`
- M2 role: `project_return_only_diagnostic`; not paper LSTM or w/o GM

# EP21 21B Alpha158/序列基线基准报告

generated_at_utc:2026-07-14T11:52:33.482908Z

## 决策结论

基线信息得到支持，允许生成人工评审用 21C requirement，但不授权执行。

- 通过的信息基线：M1_LIGHTGBM_ALPHA158 | M3_GATED_DUAL_PATH_LSTM
- semantic payload bundle hash：`16700a11f20c41f7f5b607da88720f04aa21515f6bfc402bf2808a8c6a2cda43`
- 本报告只使用 2023 validation；历史 design holdout 的 outcome/label/join/metric 读取均为 0。

## Validation-late 冻结门结果

| 模型 | late mean RankIC | 正向 seed | 正向 LOMO | 月度集中度 | 信息门 |
|---|---:|---:|---:|---:|---|
| M1_LIGHTGBM_ALPHA158 | 0.019594 | 3/3 | 6/6 | 0.3790 | 通过 |
| M2_RETURN_LSTM | -0.029308 | 0/3 | 0/6 | 0.2402 | 未通过 |
| M3_GATED_DUAL_PATH_LSTM | 0.010683 | 3/3 | 6/6 | 0.4465 | 通过 |

A0 自编码器仅作诊断，其 validation-late mean RankIC 为 0.010839，不能单独授权 21C。

## Null 与稳健性诊断

M0 realized validation-full stationary-bootstrap 99% 双侧区间为 [-0.007663, 0.004112]。该区间按合同仅作诊断，不参与 hard gate。
已输出逐日 RankIC、full/early/late、月度与 LOMO、主板/创业板描述切片，以及 top-third 决策日/股票同时移除诊断。

## 解释边界

本次 gate 只回答冻结的简单基线是否展现方向一致且不过度集中于单月的信息；不构成统计显著性、交易可执行性、策略收益、组合优化或部署声明。
