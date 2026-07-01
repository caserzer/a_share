# Payoff-state Feature Representation Diagnostic Report

## 一、结论

18D 的结论是：

```text
decision_state = 18D_feature_representation_refresh_supported
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
all_hard_gates_pass = true
recommended_refresh_family_ids = M1|M3|M5|M2
deferred_family_ids = M4
```

这不是一个“可以训练最终 payoff separability model”的结论。它只说明：在
18C 的 F1-F5 低容量 separability 失败之后，18D 找到了若干 PIT-valid、
t0-available、且在 train-prior residual readout 中仍含有 payoff 信息的表征族，
因此下一步应进入 18E 的 feature matrix refresh。

18D 不授权 entry / exit / holding policy，不授权 portfolio backtest，不授权模型部署、
production signal 或 live trading。

## 二、最重要发现

### 1. 18C 的问题更像“表征缺口”，但仍有 thin-margin caveat

18C 的主模型 `ridge_payoff_rank_h20_v1` 在 robustness split 上的 rank IC 是
`0.064398`，低于 materiality floor `0.080000`。18C 最强的辅助模型是
`shallow_tree_payoff_depth2_v1`，robustness rank IC 为 `0.076792`，距离 floor
只差 `0.003208`。

这意味着 18C 的容量/表征判断不能写成“容量完全排除”。18D 因此补跑了
depth<=4 的 train-only grouped-CV capacity probe：

| model_id | train grouped-CV rank IC | vs primary CV delta | capacity caveat |
|:--|--:|--:|:--|
| ridge_payoff_rank_h20_v1 | 0.013675 | 0.000000 | false |
| decision_tree_depth3_grouped_cv_probe_v1 | 0.008962 | -0.004714 | false |
| decision_tree_depth4_grouped_cv_probe_v1 | 0.007576 | -0.006099 | false |

结果很关键：中等容量的 depth-3 / depth-4 树没有把现有 23 个 F1-F5 特征救起来，
反而低于 primary ridge 的 train grouped-CV IC。因此 18D 的判断是：

```text
capacity_margin_status = thin_margin_caveat
capacity_conclusion_scope = low_capacity_representation_gap_with_capacity_caveat
capacity_bottleneck_flag = false
representation_bottleneck_flag = true
```

解释：18D 支持“低容量表征不足”这个方向，但报告必须保留 thin-margin 诚实性。
如果未来引入更强模型，仍需要单独 capacity accounting；本次不能把复杂模型直接
升级为主线。

### 2. 当前 F1-F5 缺的不是更多同类 level 特征，而是 episode 内形态、位置和不对称性

18D 的 feature gap decomposition 显示：

| current family | 已表达的信息 | 缺失的信息 | 对应候选族 |
|:--|:--|:--|:--|
| F1 | 短期收益、均线差、距 20/60 日高点 | episode 内修复路径质量、path entropy、range location | M1 |
| F2 | volume / money / turnover 的 level 或 z-score | signed inflow/outflow、参与度动态、压力变化 | M2 |
| F3 | board rank / market cap context | payoff asymmetry 与 path shape | M3 |
| F4 | 波动、回撤、intraday range | vol-adjusted repair quality，而不是单纯低波动 | M1/M3 |
| F5 | board dummy、market cap、tradability | 新 PIT regime context 才可能有增量 | M4 |

这解释了为什么 18C 的 ridge score 会卡在 `0.064398`：它已经捕捉到一些低波动、
参与度和短期修复信号，但没有表达 payoff-state 最核心的“路径形态”和“上行空间
/下行拥挤的不对称”。

### 3. M5 是最强 refresh 候选，M1/M3 提供核心形态和不对称补充，M2 有边际价值

18D 只允许 train rows 设置 `orthogonal_payoff_candidate = true`；robustness 和
validation 只作为 diagnostic readout。按 train-prior residual rank IC 排序，最强证据如下：

| family | feature | raw IC | residual IC | residual retention | 判断 |
|:--|:--|--:|--:|--:|:--|
| M5 | lifecycle progress to t0 | 0.166948 | 0.168810 | 1.011151 | 强，主推 |
| M3 | upside room to episode high | 0.067410 | 0.069110 | 1.025216 | 强，主推 |
| M5 | episode age to t0 | 0.059512 | 0.058699 | 0.986345 | 强，主推 |
| M1 | close location in episode range | -0.055572 | -0.051236 | 0.921982 | 强，主推 |
| M5 | bars since reclaim | 0.041452 | 0.028186 | 0.679968 | 有信号，但覆盖不足，appendix |
| M2 | money-flow persistence trailing20 | 0.014162 | 0.022856 | 1.613934 | 有增量 |
| M2 | turnover compression 20 vs 60 | -0.046154 | -0.021641 | 0.468879 | 有增量 |
| M2 | net signed money-flow trailing20 | -0.054852 | -0.021293 | 0.388198 | 有增量 |
| M1 | path transition entropy episode | 0.039028 | 0.020017 | 0.512887 | 有增量 |
| M2 | positive money-flow share trailing20 | -0.055115 | -0.018870 | 0.342373 | 有增量 |
| M5 | bars since episode low | 0.017869 | 0.014731 | 0.824385 | 有增量 |
| M1 | repair path efficiency episode | -0.021805 | -0.012967 | 0.594664 | 有增量 |

这里的 residual IC 是在 train split 上先对 `mr_volatility_20d` 和
`mr_volume_20d_zscore` 做线性残差化后的 rank IC；M2 还额外控制
`mr_turnover_rate_20d_zscore` 和 `mr_money_20d_zscore`。因此这些特征不是简单
重复 18C 已经看到的 volatility/participation ceiling。

## 三、候选族逐项解读

### M5 episode position and maturity：优先级最高

M5 的证据最强：

```text
candidate_feature_n = 4
primary_allowed_candidate_n = 3
orthogonal_payoff_candidate_n = 4
candidate_priority_score = 0.270425
recommended_for_refresh = true
```

最强特征是 `m5_lifecycle_progress_to_t0`，train residual IC = `0.168810`。它在
robustness 和 validation 也维持很强的 diagnostic readout：

| split | raw IC | residual IC | role |
|:--|--:|--:|:--|
| train | 0.166948 | 0.168810 | train_priority_prior |
| robustness | 0.246793 | 0.247604 | diagnostic only |
| validation | 0.255555 | 0.253393 | diagnostic only |

AFML 解释：episode 的位置/成熟度本身就是 payoff-state 的状态变量。当前样本不是
孤立 bar，而是 winner episode 内的 sequential step；同样的短期动量或低波动，
出现在 episode 早段、中段、末段，其后续 payoff 分布不同。18C 的 F1-F5 没有显式
表达这一点。

注意 `m5_bars_since_reclaim` 虽有 train residual IC `0.028186`，但因为 finite rate
只有 `0.795386`，低于 `candidate_min_finite_rate = 0.80`，被放入 appendix。它有
研究价值，但不应直接进入 18E 主矩阵，除非 18E 明确修复 reclaim 可得性或改变其
缺失处理契约。

### M3 payoff asymmetry context：直接补 payoff-state 核心缺口

M3 的 family 结果：

```text
candidate_feature_n = 3
primary_allowed_candidate_n = 3
orthogonal_payoff_candidate_n = 1
candidate_priority_score = 0.086515
recommended_for_refresh = true
```

唯一通过 train-prior orthogonality 的 M3 特征是
`m3_upside_room_to_episode_high`：

| split | raw IC | residual IC | role |
|:--|--:|--:|:--|
| train | 0.067410 | 0.069110 | train_priority_prior |
| robustness | 0.141261 | 0.155106 | diagnostic only |
| validation | 0.040571 | 0.044871 | diagnostic only |

这个结果符合 18D 的研究预期：payoff-state 的关键不是“当前看起来强不强”，而是
从 t0 看，结构性上行空间是否仍然存在。当前 F1-F5 没有直接表达 upside room，
因此 M3 应进入 18E refresh。

M3 里另外两个候选没有过 train-prior floor：

| feature | train residual IC | 判断 |
|:--|--:|:--|
| downside crowding to episode low | -0.009496 | 低于 0.010 floor，appendix/readout |
| vol-adjusted repair strength | -0.007908 | 低于 0.010 floor，appendix/readout |

含义：上行空间 proxy 比下行拥挤或简单 vol-adjusted repair strength 更接近当前
payoff-state 缺口。18E 应优先把 upside room 放入主矩阵，再考虑更精细的不对称组合。

### M1 episode-local morphology：有效，但不是所有 entropy 都有用

M1 的 family 结果：

```text
candidate_feature_n = 4
primary_allowed_candidate_n = 4
orthogonal_payoff_candidate_n = 3
candidate_priority_score = 0.087094
recommended_for_refresh = true
```

有效的 M1 特征包括：

| feature | train raw IC | train residual IC | 判断 |
|:--|--:|--:|:--|
| close location in episode range | -0.055572 | -0.051236 | 强，主推 |
| path transition entropy episode | 0.039028 | 0.020017 | 有增量 |
| repair path efficiency episode | -0.021805 | -0.012967 | 有增量 |

但 `m1_return_sign_entropy_trailing20` 没通过 orthogonality：

```text
raw IC = 0.014655
residual IC = 0.002874
residual_retention = 0.196097
orthogonal_payoff_candidate = false
```

这说明“加 entropy”本身不是答案。简单 trailing return sign entropy 大部分信息被
volatility/participation 控制项吸收；真正更有用的是 episode 内路径转换结构、
close 在 episode range 的位置，以及从 episode low 修复到 t0 的路径效率。

一个重要细节是 `close_location_episode_range` 的 residual IC 为负。这个方向不是
坏事，含义是：在当前 episode 定义下，t0 越靠近 episode 内高位，后续 h20 payoff
反而可能越受挤压；更靠近 range 中低位但已修复的状态可能保留更高的剩余 payoff
空间。这和 M3 的 upside room 结果一致。

### M2 supply and pressure dynamics：应作为次优先级进入 refresh

M2 的 family 结果：

```text
candidate_feature_n = 4
primary_allowed_candidate_n = 4
orthogonal_payoff_candidate_n = 4
candidate_priority_score = 0.084660
recommended_for_refresh = true
```

M2 的所有候选都通过了 train-prior orthogonality：

| feature | train raw IC | train residual IC | residual retention |
|:--|--:|--:|--:|
| money-flow persistence trailing20 | 0.014162 | 0.022856 | 1.613934 |
| turnover compression 20 vs 60 | -0.046154 | -0.021641 | 0.468879 |
| net signed money-flow trailing20 | -0.054852 | -0.021293 | 0.388198 |
| positive money-flow share trailing20 | -0.055115 | -0.018870 | 0.342373 |

但 M2 的解释要谨慎：它和 18C 当前唯一较有效的 F2 participation 家族同源，所以更
可能提供边际增量，而不是主导性新表征。18E 中 M2 应作为 secondary refresh family，
并继续保留 F2-extended residualization 检查，防止把旧的 volume/money z-score
重新包装成“新特征”。

### M4 regime and cross-sectional context：继续暂缓

M4 结果：

```text
candidate_feature_n = 1
primary_allowed_candidate_n = 0
orthogonal_payoff_candidate_n = 0
recommended_for_refresh = false
blocking_reason = no_orthogonal_train_prior_or_deferred
```

M4 没有被否定为永远无用；它只是没有在 18D 里证明有足够新 PIT context，可进入
18E 主矩阵。考虑到 18C 中 F5 基本没有贡献，除非后续能提供新的 PIT-valid
industry / breadth / regime 数据，否则 M4 的性价比低于 M1/M3/M5/M2。

## 四、输入覆盖和 lineage 质量

18D 的输入审计全部通过。关键数据源包括：

| source | evidence |
|:--|:--|
| 18B feature matrix | 23,405 rows，75 columns |
| 18C score panel | 23,405 rows，61 columns |
| qfq daily path source | 4,597 instrument CSVs |
| 16B label step panel | 504,580 rows |
| 16B materialized step panel | 504,580 rows |
| 16A episode interval panel | 2,867 rows |
| EP02 aligned context panels | 可用，但 M4 默认 appendix/deferred |

候选 feature panel 的 row denominator 仍是 18B/18C 的 `labelable_full`：

| split | row_n |
|:--|--:|
| train | 20,245 |
| robustness | 2,496 |
| validation | 664 |
| total | 23,405 |

qfq 路径覆盖：

| qfq_path_status | row_n | share |
|:--|--:|--:|
| pass | 22,508 | 96.17% |
| insufficient_pre_t0_path | 897 | 3.83% |

主要候选特征 finite rate：

| feature | finite_rate |
|:--|--:|
| close_location_episode_range | 0.961675 |
| upside_room_to_episode_high | 0.961675 |
| downside_crowding_to_episode_low | 0.961675 |
| lifecycle_progress_to_t0 | 0.961675 |
| money-flow trailing20 proxies | 0.961675 |
| path_transition_entropy_episode | 0.906174 |
| repair_path_efficiency_episode | 0.937877 |
| bars_since_reclaim | 0.795386 |

因此 18D 的 lineage 结论是：M1/M2/M3 的主要候选和 M5 的 3 个主候选都满足
PIT/t0 和 finite-rate 要求；`bars_since_reclaim` 因覆盖略低，保留为 appendix。

## 五、robustness / validation 只作为读数，不作为选择依据

18D 的 search accounting 全部通过：

```text
no_feature_selection_from_target_correlation_before_lineage = true
no_feature_selection_from_robustness = true
no_feature_selection_from_validation = true
no_final_model_training = true
binary_metric_not_primary_gate = true
neutral_rows_not_dropped = true
delayed_features_not_primary = true
```

这点很重要。报告中的 robustness / validation residual IC 可以帮助判断方向是否荒谬，
但不能反过来决定推荐。比如：

| feature | train residual IC | robustness residual IC | validation residual IC |
|:--|--:|--:|--:|
| lifecycle_progress_to_t0 | 0.168810 | 0.247604 | 0.253393 |
| upside_room_to_episode_high | 0.069110 | 0.155106 | 0.044871 |
| close_location_episode_range | -0.051236 | -0.058752 | 0.006834 |
| path_transition_entropy_episode | 0.020017 | 0.014680 | 0.087402 |
| money-flow persistence trailing20 | 0.022856 | 0.004974 | -0.037340 |
| net signed money-flow trailing20 | -0.021293 | 0.003457 | -0.071009 |

从解释上看，M5 和 M3 的部分特征在 robustness/validation 上也有方向性支持；
M2 的 OOS 表现更不稳定，因此更应作为 secondary family，而不是 primary thesis。
但最终推荐仍只基于 lineage + train-prior orthogonality。

## 六、对 18E 的具体建议

18E 应该刷新 feature matrix，而不是直接做 oracle-gap bridge。建议的 feature
优先级如下：

1. M5 episode position/maturity：优先加入 `lifecycle_progress_to_t0`、
   `episode_age_to_t0`、`bars_since_episode_low`。
2. M3 payoff asymmetry：优先加入 `upside_room_to_episode_high`。
3. M1 episode-local morphology：加入 `close_location_episode_range`、
   `path_transition_entropy_episode`、`repair_path_efficiency_episode`。
4. M2 supply/pressure dynamics：加入 money-flow persistence、turnover compression、
   net signed money-flow、positive money-flow share，但保持 F2-extended residualization
   审计。
5. M4 regime/context：暂缓，除非 18E 明确引入新的 PIT-valid regime / breadth /
   industry context，并证明不是 18B F5 的重复。

18E 的主矩阵不应纳入 `bars_since_reclaim`，除非先解决 reclaim 可得性问题；当前它的
finite rate 为 `0.795386`，略低于 18D 的 `0.80` floor。

## 七、AFML 解释

18D 的结果把 18C 的失败原因拆得更清楚：

当前 F1-F5 不是完全没有 payoff signal，而是 signal 表达得太粗。18C 的 ridge score
主要围绕短期修复、参与度、低波动和静态 context；这些可以产生弱排序，但无法稳定
表达 payoff-state 的结构性差异。

18D 找到的强证据集中在三类：

```text
episode 内位置：当前 step 在 winner episode 生命周期里的位置
结构性上行空间：t0 到 episode 高位/剩余空间的关系
修复路径形态：close 在 range 中的位置、路径转换熵、修复效率
```

这些更接近 AFML 里的 state representation，而不是单纯 predictor stacking。
因此下一步不是放宽 18C 门槛，也不是把 binary target 切回主线，而是构造一个新的
payoff-state feature matrix，再重新做 separability diagnostic。

## 八、边界

18D 只支持：

```text
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
```

18D 不支持：

```text
entry_policy
exit_policy
holding_policy
portfolio_backtest
model_deployment
production_signal
live_trading
oracle-gap bridge
```

只有当未来 refreshed feature matrix 在新的 separability diagnostic 中真正通过
rank IC、monotonicity、baseline、bootstrap 和 search-accounting gates，才可以重新
讨论 oracle-gap bridge。
