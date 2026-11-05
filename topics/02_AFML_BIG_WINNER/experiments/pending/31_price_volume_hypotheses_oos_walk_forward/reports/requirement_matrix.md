# EP31 逐项验收与证据

| GOAL_section | requirement | status | evidence |
| --- | --- | --- | --- |
| 1,9 | 八项独立裁决；七项日线检验与 H09 数据准入 | DELIVERED | metrics/hypothesis_verdicts.csv; audits/data_gate.json |
| 1 | 价格/风险/规模以外的行业/PIT 完整独立性 | BLOCKED_DATA | audits/feature_field_lineage.csv; industry and independent shares unavailable |
| 2 | exact EP30 release / manifest / 全文件 SHA | PASS | audits/ep30_release_verification.json |
| 2 | OHLCV/换手来源、逐字段质量、标签不倒填特征 | PASS_PROXY_ONLY | audits/security_source_lineage.csv; feature_field_lineage.csv; tests/test_no_future_leakage.py |
| 2 | price/total/executable 同值别名只使用一次 | PASS | audits/alias_deduplication.json |
| 2 | 公司行动、身份、更名、ST/停牌、终值缺口 | DELIVERED_WITH_LIMITS | reports/data_quality.md; audits/feature_replay.json; tests/test_adjustment_corporate_actions.py |
| 2,3 | H09 逐笔真实准入 | BLOCKED_DATA | No attested trade-size/count source; tests/test_microstructure_h09_gate.py |
| 3 | 唯一主端点、方向、反向解释、固定窗口/阈值 | PASS | GOAL.md; manifests/preregistration.json; configs/*.yaml |
| 3 | H01/H02 连续回归、分位/IC、换手重算 | DELIVERED | metrics/pooled_oos_metrics.csv; secondary_endpoints.csv; H02_turnover_sensitivity.csv |
| 3 | H03 交互项、双重排序 | DELIVERED | metrics/H03_double_sort.csv; hypothesis_scorecard.md |
| 3 | H07 未来 RV、历史 RV/HAR 基线、MSE/QLIKE | DELIVERED | metrics/required_baseline_ablations.csv; pooled_oos_metrics.csv |
| 3 | H10 高换手/小实体消融与校准 | DELIVERED | metrics/required_baseline_ablations.csv; H10_calibration.csv |
| 3 | H11 不含当日前高、突破/趋势基线、冷却 | PASS | tests/test_breakout_no_current_bar.py; metrics/required_baseline_ablations.csv |
| 3 | H12 对 H01/H02 共线性与额外增量 | DELIVERED | audits/H12_train_collinearity.csv; metrics/H12_after_H01_H02.csv |
| 4 | 周末历史身份分母、warmup、事件日/episode | DELIVERED | audits/population_by_year_board.csv; daily_event_and_episode_coverage.csv; security_coverage.csv |
| 4 | t0 / known_at / feature_start / next open / t1 / mature_at | PASS_PROXY_ONLY | audits/data_gate.json private data_timeline; data.json and label partition hashes |
| 4 | 5/20/60/120D、6月、MFE/MAE、UNKNOWN/CENSORED | DELIVERED | metrics/secondary_endpoints.csv; maturity_coverage.csv; audits/label_coverage.csv |
| 4 | 同面板强基线、无因子基线 | DELIVERED | metrics/constant_baseline.csv; required_baseline_ablations.csv; frozen prediction indexes |
| 4 | EP28 M_R/L2 与原 Big Winner 队列比较 | BLOCKED_NOT_COMPARABLE | reports/big_winner_incremental_value.md; no mixed-cohort metrics |
| 5.1,5.2 | 两段递进 inner CV、精确24月、逐事件t1 purge | PASS_WITH_TWO_BLOCKED_FOLDS | audits/fold_admission.json; per-H fold timelines; manifests/revision_01.json |
| 5.2 | 自2021Q1逐季度；扩展窗与36月滚动 | DELIVERED | fold_predictions/index.csv; 334 admitted folds; H02 2021Q1 two schemes blocked |
| 5.2 | 先封存全量预测/模型，再读取外层评分 | PASS | audits/scoring_start.json; manifests/*; private model/prediction hashes |
| 5.2 | 期限独立成熟；部分季度单列；不补未来 | PASS | metrics/maturity_coverage.csv; complete_quarter flags |
| 5.3 | 历史OOS诚实命名、禁止当独立最终测试 | DELIVERED | reports/oos_walk_forward.md; final_conclusion.md |
| 5.3 | 代码冻结后真实新时间 forward shadow | BLOCKED_NEW_T0_DATA_FORWARD_PENDING | forward_shadow/status.json; zero forward predictions and independently mature labels |
| 5.4 | 未来行情/因子、池、ST、上市、代码、除权对抗 | PASS | audits/tests.json; tests/test_no_future_leakage.py and corporate action / breakout tests |
| 5.4 | 不成熟标签、全样本拟合、同收盘成交、重复episode、别名负控制 | PASS | tests/; audits/delivery_check.json; alias_deduplication.json |
| 5.4 | 20D滞后、同日板块置乱、训练标签置乱 | DELIVERED | metrics/placebo.csv; reports/diagnostic_cases.md |
| 6 | 日期横截面关联、时间块CI、七项BH-FDR | DELIVERED | metrics/pooled_oos_metrics.csv; *_monthly.csv; audits/label_concurrency.csv |
| 6,7 | 每折95%时间块区间 | INSUFFICIENT_TEMPORAL_BLOCKS | outer_fold_metrics.csv: only three monthly observations per quarter; CI unavailable, not invented |
| 6 | 70%折同向、留一年、板块/规模/流动性/市场状态 | DELIVERED | metrics/outer_fold_metrics.csv; robustness.csv; hypothesis_verdicts.csv |
| 6 | 月等权、证券等权、偏度、最差5%、分位曲线 | DELIVERED | metrics/robustness.csv; secondary_endpoints.csv; pooled_oos_metrics.csv |
| 6,7 | Big Winner 同分母、单因子/组合、右尾召回/误杀/失败/机会成本 | DELIVERED | metrics/big_winner_incremental.csv; big_winner_coverage.csv |
| 4,6 | 单一long-only规则、0/20/50/100bps费用诊断 | DELIVERED_HYPOTHETICAL_COHORT | metrics/cost_scenarios.csv; no compounding or executable P&L claim |
| 1,4 | 实盘、实际含息权益、成交与重叠资金策略盈利 | TRADING_NOT_AUTHORIZED_UNCERTIFIED | reports/data_quality.md; big_winner_incremental_value.md |
| 7 | 表面有效但不能支持的诊断案例/或明确无该案例 | DELIVERED | reports/diagnostic_cases.md |
| 8,9 | P0至P4、负/反向/阻断结果、原计划不改写 | DELIVERED | notes/round_log.md; reports/; immutable GOAL/P0 and R01 |
| 9 | 独立重放全数据、模型序列化回放 | PASS | audits/independent_data_replay.json: 408 byte-identical files; model replay receipts |
| 9 | EP01—EP30 文件/缓存保持不变 | FINAL_AUDIT_PASS | audits/predecessor_snapshot.json; delivery_check.json; EP30 release verification |
| 9,10 | 代码/配置/清单/报告、小文件公开范围 | DELIVERED | README.md; requirements.txt; outputs/manifests/publication.json; private payload indexes |

受阻和不可比条目保留原合同的公开限制；它们不是统计支持，也不计作已完成真实前瞻或交易认证。原 GOAL.md 的勾选框不改写，由本表逐项映射实际证据。
