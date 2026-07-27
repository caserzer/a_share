# EP23 23F PIT Execution and Big Winner Bridge

## 裁决

```text
frozen_model = last_state_gru
primary_seed = 20260725
seed_selection = validation_paper_proxy_ic max, seed ascending tie-break
decision = model_branch_only_supported
evidence = design_contaminated_historical_real_market_evidence
deployment_authorized = false
```

主 seed 只由 23D2 validation IC 选择；23F 没有用 test ARR、执行收益或
Big Winner 结果挑 seed。完整五 seed 都通过同一执行器，用于检查结论是否依赖
单个随机种子。

## PAPER_PROXY 与 next-open 执行

| lane | gross ARR | net ARR | IR | MDD | one-way turnover |
|---|---:|---:|---:|---:|---:|
| PAPER_PROXY Top50/drop5 | 16.67% | 10.60% | 0.685 | -15.58% | 0.1064 |
| EXECUTABLE_BRIDGE Top50/drop5 | 14.83% | 9.10% | 0.549 | -15.82% | 0.1007 |
| EXECUTABLE_BRIDGE Top30/drop5 | 10.89% | 1.84% | 0.188 | -19.48% | 0.1674 |

EXECUTABLE_BRIDGE 在 decision close 后的下一交易日开盘成交；使用 raw price
判断涨跌停、qfq price 连续计值，并逐单处理停牌/缺 bar、整手、佣金最低额、
卖出印花税、过户费、5bps 单边滑点、未成交现金和延迟退出。它不是把
`open-to-open` label 直接当作可成交收益。

## 同期基准

| comparator | ARR | IR | MDD |
|---|---:|---:|---:|
| last_state_gru_executable_net | 9.10% | 0.549 | -15.82% |
| SH000300 | 17.97% | 0.884 | -19.15% |
| all_A_SH000985 | 18.81% | 0.817 | -17.27% |
| PIT_universe_equal_weight | 22.21% | 0.956 | -20.47% |

## Big Winner utility

- eligible up50 episode：545；
- captured episode：291，recall `53.39%`；
- right-tail exposure days：14017；
- false-positive exposure days：14919；
- right-tail exposure enrichment：`0.872x`；
- severe-left-tail exposure：策略 `1.13%`，
  eligible universe `4.59%`。

right-tail exposure 是实际持仓日落在 EP15 path-defined up50 episode interval
内；false-positive exposure 是其补集。二者是 ex-post utility attribution，
不能回灌为交易时标签。左尾以持仓开盘后 20 个交易日内最低 qfq low 相对当前
qfq open 不高于 -20% 定义。

## Morphology independence

| morphology | eligible episodes | captured | recall |
|---|---:|---:|---:|
| jump_repricing_winner | 42 | 19 | 45.24% |
| late_rescue_winner | 193 | 70 | 36.27% |
| slow_grind_winner | 104 | 85 | 81.73% |
| smooth_trend_winner | 33 | 17 | 51.52% |
| stair_step_winner | 7 | 6 | 85.71% |
| unclassified_mixed_path | 155 | 94 | 60.65% |
| unclassified_short_path | 11 | 0 | 0.00% |

independence gate 要求：material morphology（至少 10 episodes）中至少 80%
有捕获，且任一 morphology 不得占全部 captured episodes 的 70% 以上。这只
排除“收益完全由单一路径形态驱动”的解释，不声称各形态收益同质。

## Gates

| gate | result | observed |
|---|---|---|
| paper_proxy_positive_gate | PASS | net_arr=0.106033 |
| executable_no_sign_reversal_gate | PASS | paper_net_arr=0.106033;executable_net_arr=0.091005 |
| five_seed_executable_direction_gate | PASS | positive_seeds=5/5 |
| universe_equal_weight_increment_gate | FAIL | strategy_net_arr=0.091005;universe_arr=0.222087 |
| blocked_fill_materialization_gate | PASS | primary_blocked_orders=46;reasons=limit_down_blocked;limit_up_blocked;suspended_missing_daily_bar |
| right_tail_enrichment_gate | FAIL | enrichment=0.872020 |
| left_tail_burden_gate | PASS | excess=-0.034625 |
| episode_capture_gate | PASS | captured=291/545 |
| morphology_coverage_gate | PASS | material_capture_share=0.833333 |
| morphology_concentration_gate | PASS | largest_captured_share=0.323024 |

## 解释边界

- historical test 已反复观察，是 design-contaminated historical evidence；
- 正 ARR 本身不授权策略，必须同时通过 executable sign、seed、Big Winner
  utility 与 morphology gates；
- SH000985 使用项目冻结的全 A 指数日线；universe equal-weight 只对当日
  frozen score 可用股票计算；
- 本阶段不包含容量冲击、盘口排队、分钟级涨跌停打开概率或 live forward；
- `deployment_authorized=false`，即使达到 historical freeze candidate，
  也只能进入独立 true-forward freeze。
