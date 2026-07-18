# 21D REAKA 论文差距因果诊断报告

## 结论

- 工程执行完整，终态为 `21D_gap_mechanisms_mixed_no_repair_candidate`，artifact profile 为 `P6_FULL_DIAGNOSTIC_FINALIZED`。
- 本轮全部 2018–2023 结果仍是设计污染后的机制诊断，不构成论文复现或独立 OOS 支持。
- D4@64 validation_late ensemble RankIC = `0.037315`。
- repair candidate gate = `research_candidate_fail`；其逐项结果为 `{"C04D_delta_at_least_0_005":true,"C04E_delta_at_least_0_005":true,"C08_delta_positive":true,"C09_delta_positive":true,"adjacent_turnover_at_most_0_80":false,"late_ensemble_rankic_positive":true,"mean_cross_seed_rho_at_least_0_25":false,"mean_cross_seed_top30_at_least_6":false,"median_prefix64_ref256_at_least_0_95":false,"no_H01_zero_solution_collapse":false,"positive_late_seed_n_at_least_2":true,"positive_lomo_n_at_least_5":true}`。

## 机制诊断

| hypothesis_id                             | support_level                          |
|:------------------------------------------|:---------------------------------------|
| H01_RAW_RETURN_ZERO_SOLUTION              | strongly_mechanism_consistent          |
| H02_DIFFUSION_GRADIENT_DOMINANCE          | mechanism_consistent                   |
| H03_SELECTOR_SOFT_HARD_MISMATCH           | not_supported                          |
| H04_DDPM_MONTE_CARLO_RANK_NOISE           | mechanism_consistent                   |
| H05_RETURN_PATH_PREPROCESSING_MISMATCH    | mechanism_consistent                   |
| H06_UNDISCLOSED_IMPLEMENTATION_AND_SEARCH | unresolved_external_implementation_gap |
| H07_PERIOD_REGIME_SHIFT                   | descriptive_only                       |
| H08_EARLY_SELECTION_ADAPTATION            | descriptive_only                       |

## 关键配对差异（validation_late）

| contrast_id   |   mean_rankic_delta | material_improvement   |
|:--------------|--------------------:|:-----------------------|
| C01           |         0.0198893   | True                   |
| C02           |        -0.00155107  | False                  |
| C03           |        -7.39724e-05 | False                  |
| C04A          |         0.0211394   | True                   |
| C04B          |         0.0184796   |                        |
| C04C          |         0.00572302  |                        |
| C04D          |         0.033896    | False                  |
| C04E          |         0.039619    | True                   |
| C05           |        -0.0185      |                        |
| C06           |        -0.0038625   |                        |
| C07           |        -0.0146375   |                        |
| C08           |         0.017721    |                        |
| C09           |         0.0266325   |                        |

## 污染边界与下一步

本实验没有读取 historical design holdout，没有改变 v4 retained universe，也没有使用 late 结果重新选择 arm、seed、checkpoint 或阈值。即使候选通过，也只能在最终密封后的新 exchange sessions 上另立 21F forward requirement；本报告不授权下一阶段执行。
