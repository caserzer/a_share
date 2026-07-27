# EP23 23G 因子库与运行时预检

## 裁决

```text
terminal_state = ready_for_primary_static_benchmark
ready_for_primary_static_benchmark = true
A101 = A101_REPLICATION_BLOCKED
AutoAlpha = AUTOALPHA_DEFINITION_BLOCKED
Alpha158 exact = replication_blocked_by_missing_vwap
Alpha360 exact = replication_blocked_by_missing_vwap
A157/A300 no-VWAP = registered_primary_route_adaptation
```

Alpha101/AutoAlpha 的定义阻塞不会被近似实现掩盖。完整 Alpha158/360 因当前
PIT provider 缺少经过审计的 `$vwap` 而阻塞；23H 使用显式命名的 A157/A300
no-VWAP adaptation，不把它们冒充完整 Alpha158/360。

## Primary library materialization

| library_id                              |   feature_count |   rows |   dates |   instruments | date_start   | date_end   |   finite_ratio |   minimum_feature_finite_ratio |   median_feature_finite_ratio |   constant_or_empty_features | unique_index   | status   | error   |
|:----------------------------------------|----------------:|-------:|--------:|--------------:|:-------------|:-----------|---------------:|-------------------------------:|------------------------------:|-----------------------------:|:---------------|:---------|:--------|
| A20_RDAGENT_PINNED                      |              20 |  11093 |      58 |           235 | 2021-01-04   | 2021-03-31 |       0.999725 |                       0.995943 |                      0.99991  |                            0 | True           | passed   |         |
| A158_QLIB_PINNED                        |             158 |  11093 |      58 |           235 | 2021-01-04   | 2021-03-31 |       0.993569 |                       0        |                      0.99991  |                            1 | True           | passed   |         |
| A360_QLIB_PINNED                        |             360 |  11093 |      58 |           235 | 2021-01-04   | 2021-03-31 |       0.831995 |                       0        |                      0.998287 |                           62 | True           | passed   |         |
| A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION |             157 |  11093 |      58 |           235 | 2021-01-04   | 2021-03-31 |       0.999897 |                       0.995943 |                      0.99991  |                            0 | True           | passed   |         |
| A300_QLIB_NO_VWAP_REGISTERED_ADAPTATION |             300 |  11093 |      58 |           235 | 2021-01-04   | 2021-03-31 |       0.998394 |                       0.996124 |                      0.998422 |                            2 | True           | passed   |         |

## Runtime

```text
effective chat     = openrouter/openai/gpt-5.6-sol-pro
effective embedding= openrouter/openai/text-embedding-3-small
chat smoke         = passed
embedding smoke    = passed
secret scan hits   = 0
```

## 解释边界

- 这里只做短窗口物化，不是因子有效性检验。
- Alpha101 需要 101/101 公式、实现和参考数值对拍；当前不满足。
- AutoAlpha 缺少完整动态 artifact 和 PIT 多模态数据快照；当前不满足。
- historical test 和 Big Winner 标签没有进入本阶段。
