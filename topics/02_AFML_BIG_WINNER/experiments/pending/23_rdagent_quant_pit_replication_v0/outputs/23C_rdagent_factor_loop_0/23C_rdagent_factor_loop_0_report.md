# EP23 23C RD-Agent Factor Loop 0

## 裁决

```text
loop_0 = complete
generated_factors = 4
implementation_checks = 4/4 passed
rdagent_replace_best = yes
claim_ceiling = rdagent_raw_loop0_config_confounded
```

第一次 RD-Agent factor experiment 已完成。新因子组合改善了基线的扣费后年化
超额收益和最大回撤，因此按 RD-Agent 的内置规则进入当前 SOTA factor library；
但事后配置审计发现 baseline 使用了 `RobustZScoreNorm + Fillna`，combined
experiment 没有任何 infer processor。因此两组结果不是只改变因子的受控比较，
不能据此确认增量来自四个新因子，也不能解释为已获得可部署 alpha。

## Agent hypothesis

Loop 0 同时测试四个彼此独立、只使用日内或历史可见数据的简单因子：

1. `close_momentum_20d`：`close_t / close_t-20 - 1`
2. `close_reversal_5d`：`-(close_t / close_t-5 - 1)`
3. `daily_close_location_value`：
   `(2 * close_t - high_t - low_t) / (high_t - low_t)`
4. `volume_surprise_20d`：
   `log((volume_t + 1) / (mean(volume_t-20:t-1) + 1))`

四个生成实现均成功执行、生成预期 HDF5、通过列名、MultiIndex、日频、
浮点类型和无无穷值检查。源代码快照保存在 `generated_factors/`。

## PIT protocol

| item | value |
|---|---|
| universe | `pit_largecap_main_chinext` |
| benchmark | `SH000300` |
| train | `2017-04-03` — `2021-12-29` |
| validation | `2022-01-04` — `2023-12-27` |
| historical test | `2024-01-02` — `2026-05-27` |
| model | Qlib `LGBModel` |
| strategy | Top50 / drop5 |
| costs | open 5 bp, close 15 bp, minimum 5 |

本轮 baseline 和 combined factor experiment 使用相同的 provider、split、模型、
组合规则与费用设定，但 preprocessing 不一致。原始 RD-Agent 裁决保留用于审计，
受控归因必须由 23C1 配置匹配复跑给出。

## Results

| metric | baseline | combined | delta |
|---|---:|---:|---:|
| IC | 0.008419 | 0.005211 | -0.003208 |
| ICIR | 0.088050 | 0.049792 | -0.038258 |
| Rank IC | 0.005548 | 0.005574 | +0.000026 |
| 扣费前年化超额 | -1.4083% | -0.6113% | +0.7970 pp |
| 扣费后年化超额 | -6.1473% | -5.3990% | +0.7484 pp |
| 扣费后信息比率 | -0.837241 | -0.706360 | +0.130881 |
| 扣费后最大回撤 | -23.1698% | -18.9978% | +4.1720 pp |

RD-Agent 的 `Replace Best Result = yes` 是原始流程输出，但由于 preprocessing
漂移，它不能作为受控的 factor-library 晋级依据。即使暂不考虑该漂移，扣费后
年化仍为 `-5.3990%`，IC 也从 `0.008419` 降至 `0.005211`。

## Interpretation and next experiment

- 当前结果只证明 RD-Agent 的端到端生成、实现和回测路径可运行；因子效果仍是
  `config_confounded`。
- 23C1 必须先匹配 preprocessing，再做四个因子的逐因子增量消融与联合复跑，
  判断应保留 momentum、reversal、close-location 还是 volume surprise。
- RD-Agent 提议的后续方向是 10 日 volume-confirmed close-location，以及
  20 日 downside-risk asymmetry；在进入该方向前，应先完成上述归因。
- historical test 已被本项目多次使用，证据类别仍是
  `design_contaminated_historical_real_market_evidence`，不能上调为 true OOS。

## Run provenance

- RD-Agent trace：`2026-07-27_09-00-04-495483`
- baseline recorder：`2f922a37a335441bbbe53aed0f186a19`
- combined recorder：`f7d877fdf1fb4997bdab433888bb254f`
- 当前 trace 的敏感信息扫描：`0` 个包含 OpenRouter key 前缀的文件
- CLI 默认无限循环；Loop 0 完成后，Loop 1 被主动中止以避免继续消耗 API
  额度。后续正式启动应显式传入 `--loop-n 1`。
