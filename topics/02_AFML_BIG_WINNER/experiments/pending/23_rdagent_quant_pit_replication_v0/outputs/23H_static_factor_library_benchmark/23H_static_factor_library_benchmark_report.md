# EP23 23H 静态多因子库 Matched Benchmark

## 裁决

```text
terminal_state = static_library_benchmark_complete
selected_library_by_validation_median_ic = A20_RDAGENT_PINNED
evidence = design_contaminated_historical_real_market_evidence
deployment_authorized = false
```

## 五 seed 中位数

| library_id                              |   usable_feature_count |   validation_paper_proxy_ic |   validation_paper_proxy_rank_ic |   historical_test_paper_proxy_ic |   historical_test_paper_proxy_rank_ic |   historical_test_paper_proxy_net_arr |   historical_test_executable_bridge_net_arr |   historical_test_paper_proxy_mean_one_way_turnover |   effective_rank |
|:----------------------------------------|-----------------------:|----------------------------:|---------------------------------:|---------------------------------:|--------------------------------------:|--------------------------------------:|--------------------------------------------:|----------------------------------------------------:|-----------------:|
| A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION |                    157 |                    0.009337 |                         0.002972 |                         0.006361 |                              0.003966 |                              0.113934 |                                    0.171287 |                                            0.108235 |        20.517503 |
| A20_RDAGENT_PINNED                      |                     20 |                    0.009969 |                         0.008596 |                         0.007892 |                              0.008424 |                              0.131308 |                                    0.148394 |                                            0.106713 |        15.396235 |
| A300_QLIB_NO_VWAP_REGISTERED_ADAPTATION |                    298 |                    0.005457 |                        -0.004003 |                         0.003308 |                              0.003815 |                              0.206582 |                                    0.239860 |                                            0.107924 |         8.204985 |

## 关键解释

- 所有 headline 都是五 seed 中位数；没有用 historical test 选择 library。
- A157/A300 是显式 no-VWAP adaptation，不是完整 Alpha158/Alpha360。
- 完整 Alpha158/360、Alpha101 和 AutoAlpha 维持 23G blocked 裁决。
- 本阶段只说明静态信息集差异，不证明 RD-Agent 进化有效。
- Alpha20 与 23B 的最大绝对复现差为 `4.369e-09`。

运行耗时：`47.80` 秒。
