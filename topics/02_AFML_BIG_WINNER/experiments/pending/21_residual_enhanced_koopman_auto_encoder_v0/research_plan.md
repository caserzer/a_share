# Episode 21 Research Plan：在 PIT Universe 中近似复现 Residual-Enhanced Adaptive Koopman Autoencoder

> 文档状态：`draft_research_plan`
>
> 生成日期：2026-07-13
>
> Episode ID：`21_residual_enhanced_koopman_auto_encoder_v0`
>
> 论文：Liao et al. (2026), *Residual-Enhanced Adaptive Koopman Autoencoder: A Deep Latent Dynamics Model for Stock Prediction*
>
> 论文版本：ICASSP 2026 version of record，DOI `10.1109/ICASSP55912.2026.11465125`
>
> 本地论文：`paper/Residual-Enhanced_Adaptive_Koopman_Autoencoder_A_Deep_Latent_Dynamics_Model_for_Stock_Prediction.pdf`
>
> 上游数据契约：EP19 PIT universe / tradability contract；EP20A paper/data contract
>
> 启动性质：`topic_level_human_restart_for_architecture_diagnostic`
>
> 自动授权：`upstream_automatic_authorization = false`
>
> 本 Episode 第一份预期需求：`requirement_21a_paper_lineage_pit_data_and_architecture_contract.md`

## 0. 一页结论

EP21 的目标不是把论文表 1–3 的数字搬到本地，也不是用一个更复杂的模型挽救 EP20 已失败的 gate。核心问题是：

> **在本项目 close-observed、next-session executable 的 PIT top-400 主板 + top-100 创业板 universe 中，论文提出的
> “双路 LSTM 编码 + 多 Koopman operator 自适应选择 + diffusion latent residual correction”是否比共享样本、共享特征、
> 共享训练预算的简单模型提供稳定的增量横截面收益排序信息；如果有，这个增量能否桥接为成本后可执行的 Top-30
> long-only exposure？**

研究对象固定为三个彼此分开的 estimand：

```text
E_representation:
    REAKA 对下一期横截面收益排序的增量信息

E_dynamics:
    multiple adaptive Koopman operators 相对 single operator / direct LSTM 的增量

E_execution:
    同一 score 在 next-open、blocked-fill、成本、现金和连续 NAV 约束下的 Top-30 价值
```

这三个 estimand 不得相互替代：reconstruction loss 低不等于 RankIC 高，RankIC 高不等于可交易，TopK gross return 高也不等于
diffusion 模块真的有增量。

Primary horizon 固定为论文一致的一步预测：

```text
decision close t -> predict close(t+1)/close(t)-1
Qlib close(t+1)-to-close(t+2) label -> frozen-score timing sensitivity only
next-open(t+1)-to-next-open(t+2) -> executable bridge only
```

论文只给出 5 页会议正文，没有披露 operator 数量、latent dimension、扩散步数与 noise schedule、优化器、batch size、
normalization、随机种子、TopK 调仓频率、交易成本或完整代码。因此 EP21 只能声明：

```text
paper_architecture_grounded_project_adaptation
```

不得声明：

```text
exact_replication
paper_result_reproduced
CSI300_result_reproduced
REAKA_profitability_confirmed
```

论文可冻结的核心是：

1. `T = 10` 个交易日的 return / Alpha158 sequence；
2. return-LSTM 与 feature-LSTM 双路编码；
3. sigmoid gate 融合两路 latent；
4. 多个可学习 Koopman matrix，通过 Gumbel-Softmax selector 选择；
5. latent residual `R = Z+ - K_s Z`；
6. conditional DDPM 学习 residual distribution；
7. decoder 重构并预测 return；
8. `L_total = L_rec + L_koop + L_diff`；
9. primary predictive readout 为 daily RankIC / RankICIR，TopK 只作下游经济桥接。

本地适配固定使用项目 PIT universe，而不是事后 CSI300 constituents。所有特征只到 decision close `t`，买入最早发生于
next executable open。历史 2017-01 至 2026-05 已被本 topic 反复观察，只能作为
`design_contaminated_historical`；即使 historical design holdout 很强，也只能冻结候选，不能成为可信 support。可信证据必须来自历史阶段结束、
最终 checkpoint / ensemble / execution contract 密封之后真实形成的 forward cohort。

EP21 按以下顺序执行：

```text
21A  paper lineage + local data/timing + architecture/search freeze
  -> 21B  Alpha158/label pipeline + simple baseline benchmark
  -> 21C  single/adaptive Koopman nested ablation
  -> 21D  MLP residual vs diffusion residual attribution
  -> 21E  Top-30 next-open executable bridge
  -> 21F  frozen true-forward confirmation
```

每一阶段都需要人工批准下一阶段 requirement。EP21 本身不授权 policy training、portfolio optimization 或 deployment。

---

## 1. 研究动机与上游边界

### 1.1 为什么单独建立 EP21

EP20 研究的是论文约束下的 OHLCV 正 beta exposure，并已证明当前历史对 TrendPV / residual momentum 的有效月份不足；
这不等于所有非线性时序表征都失败，也不授权用深度模型绕过 EP20 的样本门。

EP21 是一次由人明确发起的 architecture diagnostic，问题从“某个手工因子是否形成正 beta”切换为：

```text
same PIT rows + same Alpha158 + same label
    -> direct nonlinear sequence model
    -> latent linear dynamics
    -> state-adaptive latent dynamics
    -> probabilistic nonlinear residual correction
```

只有逐层 nested ablation 后仍存在增量，才能把结果归因于论文提出的结构。直接训练 full REAKA 并与一个弱 baseline 比较，
不足以回答研究问题。

### 1.2 继承的上游事实

EP21 继承但不重新解释以下冻结事实：

- EP19 已建立 close-observed、next-session usable 的 PIT universe 和 tradability lineage；
- `pit_topn_400_100_membership_daily.csv` 提供 `membership_date -> usable_trade_date` 映射；
- `pit_topn_400_100_executable_daily.csv` 是 execution-side universe，不是 signal-time hindsight universe；
- qfq 股票日线当前约覆盖 2017-01 至 2026-05，底层文件约 4,597 只；
- benchmark daily 包含 CSI300、创业板指和全 A 指数的本地序列；
- EP19 成本、涨跌停、停牌、blocked exit 与 next-open 规则可以作为 21E 的默认 lineage；
- EP20A 已判定 project adaptation reachable、exact paper replication unreachable；
- 所有 freeze 前本地历史都属于 design-contaminated evidence。

21A 必须重新 hash 实际输入并审计当前覆盖；上述数字只是计划时 inventory，不可代替运行时证据。

### 1.3 不继承的结论

EP21 不继承：

- 论文在 CSI300 / S&P500 上报告的 RankIC、RankICIR、AR 或 Sharpe；
- 论文 TopK=30 的收益规模；
- EP20 任一 signal 的正负方向；
- “多 operator 一定对应真实市场 regime”的解释；
- “diffusion 一定改善极端收益预测”的结论；
- “深度模型是生产策略”的授权。

论文报告值只用于验收表结构和数量级异常检查，不能成为本地 pass threshold。

---

## 2. 论文方法档案与可复制边界

### 2.1 原论文问题与数据

论文对每只资产 `i` 使用 feature sequence `X_i` 和 return sequence `y_i`，预测下一期收益：

```text
y_hat(i,t+1) = M(X_i,1:t, y_i,1:t)
```

论文实验：

| 项目 | 论文设定 |
|---|---|
| markets | CSI300、S&P500 |
| sample | 2010-01-01 至 2020-12-31 |
| train | 2010-01-01 至 2017-12-31 |
| validation | 2018-01-01 至 2018-12-31 |
| test | 2019-01-01 至 2020-12-31 |
| features | Qlib Alpha158 |
| lookback | 10 trading days |
| primary metrics | RankIC、RankICIR |
| portfolio | TopK，`K=30` |

EP21 的 universe、样本期和执行语义都不同，因此只能做 architecture-grounded adaptation。

### 2.2 Latent encoder

论文将 return sequence 分成重叠片段：

```text
y_1:T-1 = [y_1, ..., y_T-1]
y_2:T   = [y_2, ..., y_T]

H_y  = LSTM_y(y_1:T-1)
H_y+ = LSTM_y(y_2:T)
H_x  = LSTM_x(x_1:T-1)
H_x+ = LSTM_x(x_2:T)
```

feature path 生成 sigmoid gate：

```text
G  = GateNet(H_x)
G+ = GateNet(H_x+)

Z  = H_y  * G  + H_x  * (1-G)
Z+ = H_y+ * G+ + H_x+ * (1-G+)
```

`*` 为 element-wise multiplication。EP21 必须保存 tensor-shape contract，禁止依靠 broadcasting 隐式改变语义。

### 2.3 Adaptive Koopman Selector

论文使用 operator codebook：

```text
K = {K_1, ..., K_N}
a = LeakyReLU(W [Z, H_y])
alpha = GumbelSoftmax(a, tau)
K_s = sum_i alpha_i K_i
Z_hat+ = K_s Z
```

训练时使用 differentiable Gumbel-Softmax；推理公式使用 selector argmax。EP21 必须分别记录 train-soft、train-hard 和
inference-hard 语义，primary 不允许在 historical-holdout outcome 后切换。

### 2.4 Dynamic Residual Corrector

Koopman residual：

```text
R = Z+ - Z_hat+
```

条件 DDPM 对 residual 加噪并学习：

```text
x_s = sqrt(alpha_bar_s) R + sqrt(1-alpha_bar_s) epsilon
L_diff = E || epsilon_theta(x_s, s, Z) - epsilon||^2
```

推理从 Gaussian noise 反向采样 residual `R_hat`，再得到：

```text
Z_tilde+ = Z_hat+ + R_hat
```

因为论文没有说明 point prediction 使用一次采样、固定 seed、采样均值还是 deterministic sampler，EP21 必须在 21A
冻结。Primary 使用固定数量 residual draws 的预测均值；单次 draw 只能作 uncertainty sensitivity。

### 2.5 Decoder 与 loss

论文 decoder 只重构 return path：

```text
y_hat_1:T-1 = Decoder(Z)
y_hat_2:T   = Decoder(Z_tilde+)

L_total = L_rec + L_koop + L_diff
```

EP21 primary 保持论文未加权的 `1:1:1` loss。任何 loss reweighting 只能作为预注册 sensitivity，且不得替代 primary。

为把该 snapshot-pair 公式映射到 decision-date sample，EP21 训练样本使用长度 T 的 source dates 和向前平移一日的长度 T
teacher dates，即训练时覆盖 T 个 `Z_j -> Z+_j` transitions；只有 teacher 最后一行属于 `t+1` future target。Inference 仍只输入
截至 `t` 的 T 行，并只读取最后一个 transition 的 decoded score。该 indexing adaptation 必须在 formula registry 中显式标记，
不能把只训练最后一个 transition 的实现写成同一 primary。

### 2.6 论文未披露项与本地处理

| 未披露或不清楚项目 | EP21 处理 |
|---|---|
| Alpha158 精确表达式/version | 绑定本地 `pyqlib==0.9.7` 的 158 expressions，并输出逐项 registry/hash |
| target label | paper one-step primary、Qlib gap sensitivity 与 project-executable label 分开冻结/报告 |
| normalization / missing | 21A preoutcome 冻结，所有模型共享 |
| latent dimension / LSTM depth | 21A 冻结一个 primary，不按 historical-holdout outcome 选择 |
| operator count `N` | 21A 冻结 primary；最多两个 diagnostic sensitivities |
| Gumbel temperature path | 21A 冻结初值、终值与 annealing schedule |
| DDPM steps / beta schedule | 21A 冻结；不做 outcome-driven grid |
| inference residual sampling | 固定 draw count、seed mapping 和 aggregation |
| snapshot indexing / loss reduction | primary 使用 T 个 shifted transitions；batch/time/latent 全部 mean reduction |
| teacher encoder gradient | primary 使用 shared encoder end-to-end gradient；stop-gradient 仅作 adaptation sensitivity |
| optimizer / batch / epochs | 21A 按 12GB GPU budget 冻结 |
| random seeds | 至少 3 个预注册 seeds，全部发布 |
| RankICIR formula | 使用 `mean(daily RankIC) / std(daily RankIC)`；论文正文疑似排版错误 |
| TopK rebalance / cost | paper-proxy 与 project-executable 两套语义分开 |
| source code | 若 21A 未找到官方代码，保持 `official_code_unavailable`，不得补写成 exact |

推荐的 primary architecture budget 是 `T=10`、latent width 64、1-layer dual LSTM、4 operators、linear beta schedule、20
diffusion steps、8 inference residual draws、3 training seeds。它们是待 21A 冻结的 project choices，不是论文事实。

---

## 3. Research Questions 与可证伪假设

### Q1. Alpha158 + return sequence 在 PIT universe 中是否有基本可学信息？

比较 `M1_LIGHTGBM_ALPHA158`、`M2_RETURN_LSTM`、`M3_GATED_DUAL_PATH_LSTM`。若这些模型在 validation 上均不能产生
正且稳定的 daily RankIC，则复杂 Koopman 结构没有合理入口；historical design holdout 只在全部 mandatory arms 密封后共同
readout，不参与该阶段授权。

```text
H1_null: same-sample Alpha158 / return history contains no stable next-period rank information
```

### Q2. Koopman latent propagation 是否优于 direct sequence model？

比较 single Koopman AE 与 gated dual-path LSTM。必须同时检查 RankIC 和 latent consistency；仅 reconstruction 改善不算。

```text
H2: K1_SINGLE_KOOPMAN_AE - M3_GATED_DUAL_PATH_LSTM > 0 in paired daily RankIC
```

### Q3. 多 operator 自适应选择是否有增量？

先按论文 ablation 比较 `K2_ADAPTIVE_KOOPMAN_AE` 与 `K1_SINGLE_KOOPMAN_AE`，再与
`K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL` 做 parameter-matched comparison。后者保留相同 operator codebook 和
selector-sized parameters，但混合权重是跨样本固定的 global logits，不依赖当前 latent state。

```text
H3a: K2 - K1 > 0
H3b: K2 - K1C > 0
    and selector uses more than one effective operator
    and operator assignment is stable enough across seeds/time folds
```

只有 H3a 与 H3b 均通过，才能声称 state-conditioned adaptive selection 有增量。如果只通过 H3a，结果可能只是 codebook
容量增量；如果 selector 永远选择同一个 operator，结论只能是额外参数或训练噪声增量，不能叫 adaptive regime benefit。

### Q4. Residual path 是否有增量，diffusion 是否优于 MLP residual？

```text
H4a: R1_AKS_MLP_RESIDUAL - K2 > 0
H4b: R2_REAKA_DIFFUSION - R1_AKS_MLP_RESIDUAL > 0
H4c: R2_REAKA_DIFFUSION - K2 > 0
```

H4a 判断 generic residual path，H4b 判断 diffusion-specific increment，H4c 判断完整 residual stack。H4b 必须同时在
全样本和预冻结 shock/high-vol slice 中评估。只有 tail slice 改善、全样本不改善时，结论是
`diffusion_tail_specialist_diagnostic`，不是 full-model superiority。

### Q5. Predictive gain 是否能转化为可执行 Top-30 utility？

在相同 Top-30、相同 next-open、相同资金和成本规则下比较 R2、M3、M1 和 equal-weight PIT universe。

```text
H5: REAKA full-capital net utility exceeds the frozen comparator margin
    without violating turnover, drawdown, ES10, concentration or capacity budgets
```

若 RankIC 增量成立但 TopK 成本后失败，保留 representation result，终止 deployment bridge。

### Q6. 增量能否在 seal 后真实 forward 中复现？

所有 historical result 都只是设计证据。最终问题是冻结模型/feature/normalization/seed ensemble 后，在新 decision dates 上能否
保持 paired RankIC delta 和可执行 utility。

---

## 4. PIT Universe、特征与 timing contract

### 4.1 Primary universe

Primary denominator：

```text
U_t = rows in pit_topn_400_100_membership_daily.csv
      where membership_date = decision_date t
      and usable_trade_date = next exchange session t+1
      and is_listed = true
      and is_st = false
      and is_suspended = false
      and history_ready_240d_flag = true
```

`U_t` 是 close `t` 后可知、计划在 `t+1` 使用的 universe。不得用 `t+1` close 才形成的 membership 决定 `t` 的样本。

必须保留：

```text
decision_date
membership_date
membership_available_time
usable_trade_date
instrument
board_bucket
board_rank_by_market_cap
total_market_cap_cny
history_ready_240d_flag
```

CSI300 仅作为 benchmark/regime context，不作为事后 constituent filter。不得用今天的 CSI300 constituents 回填历史。

### 4.2 Price / volume lineage

Primary price history：

```text
data/raw/akshare/day/qfq/{instrument}.csv
```

至少需要：

```text
date, open, high, low, close, volume, money, turnover_rate, factor
```

21A 必须验证：

- `(instrument, date)` 唯一；
- OHLC 数值与 high/low ordering；
- volume/money unit；
- qfq factor continuity；
- corporate-action jumps；
- raw-share volume 在 factor jump window 内的可比性；
- calendar alignment；
- missing / zero volume；
- universe row 对应 bar availability。

### 4.3 Alpha158 与 VWAP 单位边界

Primary feature family 是本地 `pyqlib==0.9.7` 的 Alpha158 expressions，不能凭名称手写“差不多的 158 因子”。21A 输出：

```text
alpha158_expression_registry.csv
alpha158_local_field_mapping.csv
alpha158_expression_hash.txt
```

当前 provider 的明确语义是 `qfq OHLC + raw share volume + raw money`。Alpha158 的多组 `VOLUME/CORR/CORD/VMA/VSTD/
WVMA/VSUMP/VSUMN/VSUMD` expressions 会直接消费 `$volume`，所以 21A 必须先冻结：

```text
volume_primary_semantics = raw shares after hands-to-shares normalization
volume_factor_adjustment = forbidden unless source lineage proves the exact transform
material_factor_jump_window = preoutcome-frozen audit/quarantine sensitivity
```

Primary 保持本地 Qlib-compatible raw-share volume，但必须逐 expression 披露跨 material factor jump window 的 row count、
feature distortion 和 quarantine sensitivity。若 corporate-action window 主导结果，只能得到
`alpha158_volume_corporate_action_sensitive_diagnostic`，不能支持 architecture claim。

qfq OHLC 与原始 transaction money / raw share volume 不在同一价格尺度，因此：

```text
money / volume
```

不得直接当 qfq VWAP。21A 必须从数据准备 contract 验证 adjustment factor 方向，冻结类似：

```text
vwap_qfq_candidate = money / volume * qfq_factor
```

或由审计证明的等价公式，并验证绝大多数非异常 bar 满足：

```text
low_qfq - tolerance <= vwap_qfq <= high_qfq + tolerance
```

`vwap_qfq` 必须在 EP21-local feature cache 中以 expression substitution 或显式 derived field 物化；不得静默修改共享 Qlib
provider。两种路径只能冻结一种 primary，并必须产生相同 key 上的等价性 audit。

若 VWAP lineage 失败：

```text
alpha158_exact_local_materialization = false
```

此时可运行删除 VWAP-dependent expressions 的 registered adaptation，但不得继续称 Alpha158-158。

### 4.4 Sequence construction

每个 `(instrument, decision_date=t)` 构造长度 `T=10` 的 sequence：

```text
y_seq = close returns ending at t
x_seq = Alpha158 feature rows ending at t
```

最大 rolling feature warm-up、10-day sequence、PIT history-ready 和 label horizon 必须共同满足。不得用未来行填补 sequence；
不得把缺失交易日当 0 return。停牌行的处理由 21A 冻结为 carry/invalid，并在所有模型间一致。

### 4.5 Primary prediction label

论文 architecture 是从 close `t` 可见状态推进一个 latent step，预测 `t+1` return。因此 paper-architecture primary 固定为：

```text
Y_rank_primary(t) = qfq_close(t+1) / qfq_close(t) - 1
```

它是一步 prediction target 和 representation readout，不是可执行 PnL；signal 在 close `t` 后才形成，不能假设成交在
close `t`。

本地 Qlib Alpha158 handler 的 canonical label 只作为冻结 score 上的 timing sensitivity，不重新训练、不参与 model selection：

```text
Y_qlib_gap_diagnostic(t) = qfq_close(t+2) / qfq_close(t+1) - 1
expression = Ref($close,-2)/Ref($close,-1)-1
```

经济桥接使用：

```text
Y_exec_1d(t) = qfq_open(next_session_after_entry) / qfq_open(entry_session) - 1
entry_session = usable_trade_date = t+1
```

三者必须在不同列和表中，禁止把 close proxy 收益写成 next-open executable return。

#### 4.5.1 Decision-time denominator 与 label outcome resolution

Primary denominator 先于 outcome 固定：

```text
U_t_decision = PIT member at decision close t
               AND history/feature ready using information <= t
               AND eligible for the frozen model score contract
```

`U_t_decision` 不得因 `t+1` 是否有 bar、是否停牌、是否退市或 label 大小而逐股改变。21A 必须冻结并测试以下
`label_resolution_status`：

```text
NORMAL_NEXT_SESSION_CLOSE
LISTED_SUSPENDED_CARRY
CONFIRMED_TERMINAL_PRICE
UNKNOWN_DATA_GAP
RIGHT_CENSORED_DATA_CUTOFF
```

- `NORMAL_NEXT_SESSION_CLOSE`：使用下一 exchange session 的 qfq close；
- `LISTED_SUSPENDED_CARRY`：证券仍上市但下一 exchange session 无成交，使用 close `t` carry，return 为 0；
- `CONFIRMED_TERMINAL_PRICE`：只有存在可审计的官方终止/结算价格时才解析该 outcome；
- `UNKNOWN_DATA_GAP`：不得逐股静默删除，primary 的整个 decision day 标记为 `not_evaluable_data_integrity`；
- `RIGHT_CENSORED_DATA_CUTOFF`：下一 exchange session 尚未完整落库时，整个 decision day 右删失。

全部 mandatory arms 必须对同一个 `U_t_decision` 产出 score；任一 arm 缺 score 是 coverage/pipeline failure，不得通过取各模型
score/label intersection 改变 paired denominator。RankIC 的 `U_t_resolved` 只能由前三种已解析状态组成，并且必须等于当天完整
`U_t_decision`；否则整日不进入 primary RankIC。Economic replay 仍从同一 `U_t_decision` 发单，停牌/涨跌停通过 blocked-fill 和
carry-marking 处理，而不是从候选 universe 删除。

### 4.6 Training graph、teacher target 与 inference graph

每个 sample 的 forecast origin 固定为 decision close `t`：

```text
source_dates          = [t-T+1, ..., t]
teacher_shifted_dates = [t-T+2, ..., t+1]       # train only
x_obs, y_obs          = source tensors using bars/features <= t only
forecast_target       = Y_rank_primary(t) = close(t+1)/close(t)-1
score                 = last scalar of decoded shifted prediction
```

Primary train graph：

```text
x_obs, y_obs
  -> dual encoder / gate
  -> Z_source[1:T]
  -> selector[1:T] and K_s[1:T]
  -> Z_hat_shifted[1:T]
  -> residual corrector conditioned only on Z_source[1:T] and sampled noise
  -> Z_tilde_shifted[1:T]
  -> decoder
  -> y_hat_shifted[1:T]
  -> score = y_hat_shifted[T]
```

训练时允许一个严格隔离的 `target_only_teacher_branch` 使用 shifted target sequence `[t-T+2, ..., t+1]` 编码
`Z_teacher_shifted[1:T]`；其中前 `T-1` rows 来自 observed tail，只有末行 `y_(t+1), x_(t+1)` 是 target-only future
row。对每个 `j in [1,T]`，该 branch 仅用于构造：

```text
R_shifted[j] = Z_teacher_shifted[j] - Z_hat_shifted[j]
```

Teacher tensors：

- 不得 concat、skip-connect 或 condition 到 forecast path；
- 不得进入 selector、GateNet input 或 residual conditioning context；
- validation/test inference graph 必须完全删除 teacher branch；
- primary 按论文式 end-to-end Koopman loss 允许梯度从 `L_koop` 回传 shared target encoder；这不等于把 teacher value 输入 inference；
- stop-gradient 只能登记为独立 adaptation sensitivity，不得替换 primary；
- train 与 inference 必须对同一 source sample 输出同 shape、同 score index。

Primary 的 return encoder/decoder 和 teacher return rows 一律使用 raw one-step qfq close return；不得把 decision-date
cross-sectional target normalization 混入 return sequence。所有 squared loss 都先对有效 latent/return element 做 mean，再对有效
batch/time cell 做 mean，禁止用 time-axis sum 令 loss 随 T 放大。精确归约固定为：

```text
L_source_rec = MeanValid((Decoder(Z_source) - y_source_raw)^2)
L_shifted_observed_rec = MeanValid_j<T((y_hat_shifted[j] - y_teacher_shifted_raw[j])^2)
L_history_reconstruction = 0.5 * (L_source_rec + L_shifted_observed_rec)
L_forecast = MeanBatch((y_hat_shifted[T] - Y_rank_primary_raw(t))^2)
L_rec = L_history_reconstruction + L_forecast

L_koop = MeanValid_B,T,D((Z_teacher_shifted - Z_hat_shifted)^2)
L_diff = MeanValid_B,T,D,noise((epsilon_hat - epsilon)^2)
L_total_REAKA = L_rec + L_koop + L_diff
```

`L_forecast` 是 `L_rec` 的 final-step supervised component，不是额外绕过论文 loss 的第四项。全部可学习 arms 必须共享同一
forecast target：M1 使用 regression objective；M2/M3 使用 `L_forecast`；A0 使用 `L_rec`；K1/K1C/K2 使用
`L_rec + L_koop`；R1 使用 `L_rec + L_koop + L_residual_mlp`；R2 使用论文的 `L_rec + L_koop + L_diff`。

Primary 不使用 target cross-sectional normalization。预注册 sensitivity 如使用该 normalization，必须对整条 return
source/teacher/forecast target 使用同一变换语义，单列 `target_transform_id`，不得替换 primary；target statistic 不得进入
Alpha158 feature transform、sample selection、score 后处理或 inference。Primary evaluation 始终使用 raw
`Y_rank_primary` 的 cross-sectional rank。

### 4.7 Feature normalization 与 missingness

21A 在 outcome access 前冻结以下 primary policy：

1. expression 只使用 `<= t` 的 bar；
2. historical evaluation 的 primary winsor / center / scale 参数只在 original training period 拟合；
3. validation、historical holdout 只 apply frozen original-training transform；
4. 21F final deterministic refit 可在 final refit window 重新拟合一次 transform，随后整个 forward cohort 静态 apply；
5. feature missing indicator 是否加入必须预注册；
6. label/target-only normalization 不得进入 feature normalization、sample selection 或 inference；
7. 同一阶段、同一 fit window 的 transform 供全部 arms 使用；
8. 每日 feature coverage、极值、constant-column 和 inf replacement 全量审计。

Primary 固定为 phase-specific fit-window-fitted robust center/scale、clip 到固定范围、invalid 后填 fit-window median。Decision-date CS rank
normalization 只能使用当日 PIT denominator，必须有独立 `transform_id`，只作预注册 sensitivity；它不受第 2 条的
fit-window-fitted 参数规则约束，也不能替换 primary。

---

## 5. Model Arms 与 nested attribution

### 5.1 Mandatory arms

| arm_id | 模型 | 研究角色 |
|---|---|---|
| `M0_HASH_NULL_SCORE` | 由 frozen hash(`instrument`,`decision_date`) 生成、与 outcome 独立的伪随机 score | pipeline/null sanity check |
| `M1_LIGHTGBM_ALPHA158` | 当日 Alpha158 LightGBM | 非时序强基线 |
| `M2_RETURN_LSTM` | 仅 return sequence 的 LSTM | 论文 w/o gating 对应基线 |
| `M3_GATED_DUAL_PATH_LSTM` | return + Alpha158 双路 LSTM/gate，direct head | primary direct-sequence comparator |
| `A0_VANILLA_AUTOENCODER` | 双路 encoder/decoder，无 Koopman/residual | 论文 vanilla AE ablation |
| `K1_SINGLE_KOOPMAN_AE` | 单 Koopman operator | fixed latent dynamics comparator |
| `K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL` | 与 K2 相同 codebook/selector-sized 参数，但使用跨样本固定 global mixture | capacity-matched non-adaptive control |
| `K2_ADAPTIVE_KOOPMAN_AE` | 多 operator + AKS，无 residual | adaptive dynamics test |
| `R1_AKS_MLP_RESIDUAL` | K2 + parameter-matched MLP residual | diffusion-specific comparator |
| `R2_REAKA_DIFFUSION` | K2 + conditional DDPM residual | full paper-grounded adaptation |

GRU、TCN、ADGATs、FactorVAE、MASTER 不属于 minimum gate。只有本地已有经过验证的 implementation 且不扩大 outcome-driven
search 时，才可作为 `registered_external_comparator`；缺失不能被写成论文 replication 完成。

### 5.2 Fair-comparison rules

全部 arms 必须共享：

- identical PIT rows and splits；
- identical Alpha158 tensor where applicable；
- identical primary label；
- identical normalization/missing policy；
- identical early-stopping metric and patience；
- identical maximum epochs/data passes；
- identical seed list；
- identical score-to-TopK mapping；
- identical cost/execution replay。

每个 arm 输出 parameter count、GPU time、peak memory、epochs、data passes 和 inference latency。`K1C` 与 K2、`R1`
residual MLP 与 diffusion denoiser 的参数量分别应在可行范围内匹配；若无法在 ±10% 内匹配，必须披露 parameter-count delta，
且相应 mechanism attribution 自动降级。

### 5.3 Primary shape contract

21A 必须冻结并由 unit test 验证：

```text
y_source:          [batch, T, 1]
x_source:          [batch, T, 158]
H_y_source:        [batch, T, latent_dim]
H_x_source:        [batch, T, latent_dim]
Z_source:          [batch, T, latent_dim]
Z_t:               [batch, latent_dim]                    # Z_source[:, -1, :]

y_teacher_shifted: [batch, T, 1]                          # train teacher branch only
x_teacher_shifted: [batch, T, 158]                        # train teacher branch only
Z_teacher_shifted: [batch, T, latent_dim]                 # train-only, gradient-enabled primary

selector_source:   [batch, T, N_operator]
K_codebook:        [N_operator, latent_dim, latent_dim]
K_selected:        [batch, T, latent_dim, latent_dim]
Z_hat_shifted:     [batch, T, latent_dim]
residual_shifted:  [batch, T, latent_dim]
Z_tilde_shifted:   [batch, T, latent_dim]
decoded_source:    [batch, T]
decoded_shifted:   [batch, T]
score_next:        [batch]                                # decoded_shifted[:, -1]
```

Primary 必须对全部 `T` 个 source-to-shifted transitions 应用共享 codebook、逐时点 selector、Koopman consistency 和 residual
loss；primary score 只取最后可见 `Z_t` 的一次推进结果。`last_transition_only_adaptation` 只能作为单独注册的 sensitivity，使用
独立 `arm_id/config_hash`，不得替代 primary、不得进入 C0–C4 gates，也不得与 full shifted-sequence approximation 混名。

### 5.4 Primary training choices

21A 应在不读取 outcome 的前提下冻结一个 primary config。建议：

```text
lookback_T = 10
latent_dim = 64
lstm_layers = 1
n_operator = 4
selector_activation = leaky_relu
gumbel_tau_start = 1.0
gumbel_tau_end = 0.1
gumbel_inference = hard_argmax
diffusion_steps = 20
beta_schedule = linear(1e-4, 2e-2)
inference_residual_draws = 8
loss_weights_REAKA = {rec_including_forecast: 1.0, koop: 1.0, diff: 1.0}
optimizer = AdamW
learning_rate = 1e-3
weight_decay = 1e-5
max_epochs = 100
early_stopping_patience = 10
seed_count = 3
```

这些值是受本地 RTX 4070 SUPER 12GB 计算预算约束的 project defaults，不是论文参数。21A 需要以 dry-run memory audit
确认 batch size；OOM 后允许机械减 batch，不允许改变 architecture 后继续用同一 run_id。

### 5.5 Search budget

Primary result 只来自一个 frozen config。允许的 sensitivity 最多为：

```text
n_operator in {2, 8}          # primary 4 不重复搜索
latent_dim in {32, 128}       # 只作 capacity sensitivity
diffusion_steps in {10, 50}   # 只作 compute/quality sensitivity
```

Sensitivity 不能用于替换失败的 primary，也不能从 historical holdout 选 winner。所有尝试、失败、OOM、NaN 和
early-stop run 都进入
`model_search_accounting_manifest.csv`。

---

## 6. Historical split、训练与复现治理

### 6.1 Split 原则

禁止 random row split。Primary 使用连续时间段，初始建议：

```text
train:               2018-01-02 .. 2022-12-30
validation:          2023-01-03 .. 2023-12-29
historical_design_holdout: 2024-01-02 .. 2026-05-29 complete decision dates only
```

`complete decision date` 按 4.5.1 的整日 resolution contract 判断；不得在一个保留日期内逐股删除 incomplete future labels。

Validation stability halves 固定为：

```text
validation_early = first eligible 2023 session .. 2023-06-30
validation_late  = first eligible session after 2023-06-30 .. 2023-12-29
```

21A 可根据实际 first fully eligible date 对 train start 做机械顺延，但不得查看 label 分组结果。边界至少 purge：

```text
T input sessions + maximum registered label/execution horizon = 12 sessions
```

并输出实际 dropped rows。Historical design holdout 再固定分为：

```text
holdout_early = 2024 calendar year
holdout_late  = 2025-01 through data cutoff
```

不得因某段表现差而重新切分。该 holdout 不是可信 OOS support，但在全部 mandatory arms 训练和 checkpoint freeze 前仍必须
保持 sealed，避免不同阶段顺序读取后再修改 architecture。

### 6.2 Model selection

允许 validation 决定：

- early stopping epoch；
- 同一 frozen arm 内的 checkpoint；
- 若 21A 预注册多个 training learning rates，则按 validation 选一个，但所有 cell 计入 multiplicity。

禁止 validation/historical holdout 决定：

- feature deletion；
- label timing；
- operator count primary；
- residual module类型；
- TopK；
- cost assumption；
- regime slice；
- terminal state definition。

21B–21D 的训练、early stopping 和 validation futility 只能读取 train/validation。`historical_design_holdout` 的任何
label summary、RankIC、PnL 或 score-outcome join，必须等全部 M/K/R mandatory arms 与 primary sensitivities 训练完毕、
checkpoint/hash 固定后一次性解封。解封后禁止重新训练、替换 primary config 或增加 arm；如发现真正 pipeline defect，只能以
新 run version 全量重启并保留旧 bundle。

### 6.3 Randomness

至少 3 个固定 seeds。每个 seed 固定并保存：

```text
python / numpy / torch seed
dataloader order seed
gumbel noise seed
diffusion train-noise seed
diffusion inference-draw seed
weight initialization seed
```

Primary model score 为 frozen seed ensemble mean；单个最佳 seed 不得作为主结果。必须报告 seed dispersion、worst seed 和
seed-rank stability。

### 6.4 Reproducible runtime

21A 必须冻结：

- Python / PyTorch / CUDA / Qlib versions；
- exact lockfile/hash；
- deterministic flags 与已知 nondeterministic kernels；
- GPU model / memory；
- feature cache hash；
- split hash；
- config hash；
- checkpoint hash；
- score file hash。

当前项目没有 PyTorch dependency；21A 必须先给出 dependency/lock change contract。不得在 21B runner 中静默安装 latest torch。

---

## 7. Staged Research Architecture

### Stage 21A：论文血缘、PIT 数据与 architecture freeze

目标：在读取 outcome summary 前回答“本地到底能近似到哪一层、tensor/label/timing 如何定义、计算预算是否足够”。

必做：

1. PDF metadata、页码/公式/表格 registry 与 SHA256；
2. 官方 code / appendix availability audit；
3. 论文未披露项和 project choices registry；
4. installed Qlib Alpha158 158 expressions/hash；
5. VWAP adjustment/unit audit 与 raw-volume corporate-action semantics；
6. PIT membership `t -> t+1 usable` audit；
7. label 三语义、`U_t_decision` 与整日 outcome-resolution freeze；
8. feature/sequence coverage，不读取 label outcome distribution；
9. historical split、purge、seed、search budget freeze；
10. source/teacher/inference graph、tensor shape、per-arm loss 与 inference sampling contract；
11. PyTorch/CUDA dependency plan 与 12GB GPU dry-run；
12. metrics、multiple testing、economic margins、terminal states、21F comparators/refit protocol freeze；
13. preoutcome access log 和 freeze bundle hash。

21A 不训练 outcome model。输出后需人工批准才生成/执行 21B。

### Stage 21B：Alpha158 pipeline 与 simple baselines

运行：

```text
M0_HASH_NULL_SCORE
M1_LIGHTGBM_ALPHA158
M2_RETURN_LSTM
M3_GATED_DUAL_PATH_LSTM
A0_VANILLA_AUTOENCODER
```

目标是验证：

- label/score date alignment；
- RankIC implementation；
- feature coverage；
- baseline learning support；
- seed/runtime reproducibility；
- M3 是否在 validation 提供进入 Koopman test 的最低信息基础。

常数同分 score 只能另作 tie-handling unit test，因为 Spearman 对常数 score 未定义。

若 M1/M2/M3 在 validation 上均无稳定正方向，21B 可按预注册 futility rule 终止复杂模型主线。21B 不得读取
historical design holdout；不得因为 validation baseline 弱而跳过 gate 后直接运行 full REAKA 寻找幸运结果。

### Stage 21C：Single vs Adaptive Koopman nested ablation

运行：

```text
K1_SINGLE_KOOPMAN_AE
K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL
K2_ADAPTIVE_KOOPMAN_AE
```

除 predictive metrics 外，必须检查：

- Koopman consistency loss out-of-time；
- operator selection share；
- effective operator count；
- selector entropy；
- switching rate / transition matrix；
- spectral radius / unstable latent propagation；
- assignment stability across seeds；
- 与 frozen market regime 的描述性关系。

`K1C` 必须使用与 K2 相同的 codebook 和 selector-sized network，但 selector input 固定为 learned constant context，从而产生
跨 instrument/date 相同的 global mixture；不得读取 `Z/H_y`。K2 必须同时优于 K1 和 K1C，且 operator assignment 不 collapse，
才支持 adaptive selection。Operator assignment 只可称 latent state partition，不能直接命名为 bull/bear 或宏观 regime，
除非后续独立验证。

### Stage 21D：Residual MLP vs conditional diffusion

运行：

```text
R1_AKS_MLP_RESIDUAL
R2_REAKA_DIFFUSION
```

21D 完成所有 mandatory checkpoints 和预注册 sensitivity 后，才允许一次性解封 historical design holdout。除 RankIC 外，
必须报告：

- residual MSE / MAE；
- residual tail error；
- sample mean/variance stability；
- CRPS 或等价 distributional score；
- calibration / interval coverage diagnostics；
- frozen high-vol / large-index-move / limit-heavy slices；
- inference draws 与 latency；
- `R2-R1` paired daily RankIC delta。

若 R2 只靠更多参数或更多 compute 获胜，而 matched MLP 不弱，则不得声称 diffusion-specific benefit。

### Stage 21E：Top-30 executable bridge

只在 R2 通过 historical representation gate 后执行。两套 portfolio 必须分开：

```text
paper_one_step_top30:
    daily top-30 equal weight
    paper one-step close(t)-to-close(t+1) return proxy
    gross, diagnostic only

project_executable_top30:
    score after close t
    target rebalance next executable open t+1
    equal-weight Top-30
    one continuous no-injection NAV ledger
    blocked buy -> cash
    blocked exit -> keep marked position and consume capital
    explicit commission, stamp tax, slippage and capacity
```

比较 R2、M3、M1 与 full PIT equal-weight baseline。不得只展示 cumulative return；必须展示 turnover、cash drag、blocked
fills、drawdown、ES10、name/month concentration 和 break-even cost。

### Stage 21F：Frozen true-forward confirmation

21A 在 historical holdout 解封前即固定 21F comparator 身份为 `M1_LIGHTGBM_ALPHA158` 和
`M3_GATED_DUAL_PATH_LSTM`；不得根据 historical readout 只选择较弱者。21D/21E 完成且人工批准 21F 后，使用以下一次性
deterministic refit protocol：

1. 只 refit `R2`、`M1`、`M3`，architecture、features、loss、TopK、cost、seed list 与原 historical contract 完全不变；
2. `final_refit_cutoff` 固定为 candidate seal 前最后一个 outcome 已完整解析的 decision date；
3. refit window 使用从 original train start 到 `final_refit_cutoff` 的全部已解析 pre-forward rows；
4. 每个 seed/arm 的训练 data-pass/epoch/boosting-iteration 数使用 pre-holdout validation 已冻结的
   `selected_train_steps(seed, arm)`，refit 不再 early-stop；
5. feature/return transform 只在 final refit window 重新拟合一次，并在 R2/M1/M3 间共享适用语义；
6. refit 完成后只允许 shape、finite-value、hash 和 score-coverage integrity tests，不得读取任何 post-seal outcome；
7. 生成独立 final candidate freeze bundle，冻结一个 primary R2 seed ensemble、M1 ensemble、M3 ensemble 及 execution contract。

该 refit 后的模型是 forward estimand；historical readout 评价的是 pre-holdout checkpoint，不得把其数值写成 final-refit model 的
历史 OOS 表现。Forward 起点：

```text
first exchange session strictly after final 21F candidate seal
```

21A seal 负责阻止 preoutcome contract 漂移，但不能替代训练结束后的 checkpoint seal。如果 final candidate seal 之后修改
feature、architecture、normalization、checkpoint、seed aggregation、score calibration 或 TopK，则必须重新 seal，forward clock
重新开始。

首个 forward cohort 内三组模型全部静态：在达到 252 个 complete decision days 前禁止 rolling retrain、增量更新、normalizer
refresh 或 comparator 替换。预先安排的任何更新都必须另建 model version 和 forward cohort，不能拼接进本 cohort。

21F primary forward representation family 为 `R2-M3` 与 `R2-M1` 的 paired daily RankIC delta，使用 Holm correction；forward
economic family 为 R2 相对 M3、M1 的 paired net-utility delta，另作 Holm correction，并继续满足 cash hurdle、full-PIT
equal-weight baseline、risk、cost、capacity 与 concentration 的 conjunctive gates。K1/K1C/K2/R1 不进入 minimum 21F；因此
21F 不重新确认 module attribution，21C/21D 的 module flags 永远保持 `historical_design_diagnostic`。如需 forward mechanism
attribution，必须另立 requirement 并冻结全部 nested arms。

建议证据阶梯：

```text
< 60 complete decision days:     not evaluable
60-125 days:                     forward interim only
126-251 days:                    directional, non-confirmatory
>= 252 days and ex-ante power:   confirmatory-evaluable
```

最终下限由 21A 使用 daily-block dependence、frozen MDE 和 power 计算；不能把 500 stocks × days 当独立样本夸大 power。

---

## 8. Metrics、统计设计与 multiple testing

### 8.1 Primary predictive metric

每日只在 4.5.1 定义的完整 `U_t_resolved == U_t_decision` cross-section 计算：

```text
RankIC_d = Spearman(score_i,d, Y_rank_primary_i,d)
```

每日最低有效股票数由 21A 冻结，建议 `N >= 100`；但该阈值只判断预先形成的 `U_t_decision` 是否有足够研究支持，不能用于
事后删除 label/score 缺失股票后保留当天。Primary summary：

```text
mean_daily_RankIC
std_daily_RankIC
RankICIR = mean_daily_RankIC / std_daily_RankIC
positive_RankIC_day_rate
```

论文正文的 RankICIR denominator 疑似排版为 mean；EP21 使用标准 deviation，并在 registry 中记录解释。

### 8.2 Primary incremental contrasts

预注册 family：

```text
C0 = K1_SINGLE_KOOPMAN_AE - M3_GATED_DUAL_PATH_LSTM
C1 = R2_REAKA_DIFFUSION - M3_GATED_DUAL_PATH_LSTM
C2a = K2_ADAPTIVE_KOOPMAN_AE - K1_SINGLE_KOOPMAN_AE
C2b = K2_ADAPTIVE_KOOPMAN_AE - K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL
C3a = R1_AKS_MLP_RESIDUAL - K2_ADAPTIVE_KOOPMAN_AE
C3b = R2_REAKA_DIFFUSION - K2_ADAPTIVE_KOOPMAN_AE
C4 = R2_REAKA_DIFFUSION - R1_AKS_MLP_RESIDUAL
```

`C0` 是 fixed Koopman latent-dynamics gate；`C1` 是 full architecture predictive gate；`C2a` 是 paper-style
single-operator ablation；`C2b` 才是 capacity-controlled
adaptive-selection attribution；`C3a` 是 generic MLP residual path；`C3b` 是 full residual stack；`C4` 是
diffusion-specific attribution。不能用 C1 通过推导任何 module contrast 通过。

### 8.3 Inference unit

Primary inference unit 是 decision day，而不是 stock-day row。使用 paired daily deltas并采用：

- stationary/block bootstrap，block length 在 21A 冻结；
- 或 HAC/Newey-West sensitivity；
- calendar-month cluster sensitivity；
- early/late fold；
- leave-one-month-out；
- top 1/3/5 extreme days removed；
- board bucket 和 market regime slices。

同日横截面 500 只股票不能当 500 个独立时间证据。

### 8.4 Multiple testing

七个 primary contrasts 用 Holm correction。Search sensitivities、三个 seeds、多个 horizons 和 regime slices 都必须登记，但
不允许从中选择新 primary。Regime/tail slice 除预注册的 diffusion attribution 外均为 descriptive diagnostics。

### 8.5 Secondary predictive diagnostics

```text
Pearson IC
MSE / MAE
top30 mean label
top30-minus-universe
top30-minus-bottom30
quintile/decile monotonicity
score turnover
score autocorrelation
coverage / missingness
```

MSE 改善不能替代 RankIC gate；单一 top30 return 也不能替代 cross-sectional ranking stability。

### 8.6 Concentration and fragility

必须披露：

- top 1/3 instruments removed；
- top 1/3 decision days removed；
- max instrument contribution；
- max month contribution；
- main-board vs ChiNext；
- high/low volatility；
- benchmark up/down；
- limit-heavy days；
- seed dispersion；
- prediction magnitude and clipping sensitivity。

---

## 9. Gates 与 terminal states

### 9.1 21A readiness gate

全部通过才可训练：

```text
paper_source_lineage_gate
alpha158_expression_gate
vwap_qfq_unit_gate
volume_corporate_action_semantics_gate
pit_membership_timing_gate
feature_label_alignment_gate
train_teacher_inference_graph_gate
split_purge_gate
architecture_shape_gate
dependency_lock_gate
gpu_dry_run_gate
search_budget_gate
outcome_firewall_gate
freeze_bundle_hash_gate
```

### 9.2 Baseline information gate

21B 至少一个非 null baseline 必须在 validation 同时满足：

- validation learning pipeline 正常；
- validation mean RankIC positive；
- validation_early / validation_late 不出现机械相反且由单月支配；
- 至少两个 seeds 正方向；
- score coverage 达冻结门。

该 gate 只允许继续训练预注册 architecture，不得读取 historical design holdout，也不形成 support。

### 9.3 Full REAKA representation gate

R2 必须：

1. mean RankIC 为正；
2. C1 paired delta 的 corrected lower confidence bound 高于 21A frozen margin；
3. holdout_early / holdout_late 方向一致或通过预注册 stability rule；
4. worst-seed 不出现灾难性反向；
5. concentration/coverage/NaN gates 通过；
6. 没有 historical-holdout-driven config replacement。

### 9.4 Module attribution gates

```text
koopman_latent_dynamics_supported:
    C0 passes

adaptive_operator_supported:
    C2a passes + C2b passes
    + effective operator count / stability gates pass

mlp_residual_path_supported:
    C3a passes

full_residual_stack_supported:
    C3b passes

diffusion_specific_supported:
    C4 passes + residual distribution/tail diagnostics pass
```

`C2a` 通过而 `C2b` 失败只能得到 codebook-capacity diagnostic；`C3a` 失败不自动否定 diffusion，但 `C3b` 失败会关闭
full residual-stack claim。某个模块 attribution 失败不一定否定 R2 的 prediction，但会降低结论为
`complex_model_gain_not_mechanistically_attributed`。

### 9.5 Economic bridge gate

21E 必须同时满足：

- cash-inclusive full-capital net return 超过 frozen cash hurdle；
- R2 相对 full-PIT equal-weight baseline 的 paired net utility 超过预注册 margin；
- 在同一 complete decision-day denominator 上，R2 相对 M3 与 M1 的两个 paired net-utility contrasts 均超过冻结 margin；
- ES10 / max drawdown 在预算内；
- turnover/cost/capacity 通过；
- blocked-fill/cash drag 不吞噬 gross edge；
- result 不由少数股票或月份主导。

RankIC gate 通过但 economic gate 失败时，终态是 representation-only，不得部署。

Economic comparator rule 固定为 conjunctive，不得在 holdout 后只保留较弱 comparator。两个 paired economic contrasts 构成
独立 Holm family；absolute net return 还必须超过 frozen cash hurdle 和 full-PIT equal-weight baseline 的预注册 margin。

### 9.6 互斥 primary terminal state 与非互斥 diagnostic flags

每个已经关闭、不再继续推进的 run/version 只允许一个 `primary_terminal_state`。仍在运行或等待人工批准的阶段使用独立
`stage_decision in {continue_eligible, pending_human_approval}`，不得提前填 terminal state。关闭时按以下顺序 first-match：

```text
1. 21_paper_lineage_or_data_contract_blocked
   -> 论文/Alpha158/VWAP/PIT timing/label denominator contract 无法建立；停止训练。

2. 21_compute_or_dependency_contract_blocked
   -> PyTorch/CUDA/12GB memory/reproducible lock 不满足；停止 full run。

3. 21_baseline_information_not_supported
   -> simple baselines 无稳定正 validation RankIC；关闭复杂 architecture mainline。

4. 21_historical_representation_not_supported
   -> R2 historical representation gate 不通过；不进入 21E/21F。

5. 21_historical_representation_candidate_only
   -> historical representation gate 通过，但 21E 尚未完成或尚未获人工批准。

6. 21_representation_supported_execution_failed
   -> historical RankIC 增量成立，但已完成的 21E 成本后 Top-30 utility gate 失败；不可进入 21F。

7. 21_historical_executable_candidate_only
   -> historical representation + economic gates 通过，但 complete forward decision days < 60；仍非可信 support。

8. 21_forward_interim_not_support
   -> 60-125 个 complete forward decision days；仅 interim monitoring。

9. 21_forward_directional_not_confirmatory
   -> 126-251 天，或 >=252 天但尚未达到 frozen ex-ante power；只能报告方向。

10. 21_forward_confirmation_not_supported
    -> 已达到 252 天与 frozen power，但 forward representation family 不通过或出现预注册灾难性稳定性失败。

11. 21_forward_representation_supported_execution_unresolved
    -> confirmatory-evaluable 的 forward representation family 通过，但 executable bridge 因完整性/coverage 原因尚不可评价。

12. 21_forward_representation_supported_execution_failed
    -> confirmatory-evaluable 的 forward representation family 通过，但 executable utility/risk/cost/capacity 任一 conjunctive gate 失败。

13. 21_forward_executable_reaka_candidate_supported
    -> 至少 252 天且达到 frozen power，forward R2 对 M3/M1 的 representation 与 execution families、risk、cost、capacity、
       concentration、stability 全部通过；只允许人工发起新 policy requirement，不代表 forward module attribution 已确认。
```

Module attribution 不再占用 `primary_terminal_state`，而写入允许同时为真的 boolean `diagnostic_flags`：

```text
koopman_latent_dynamics_not_incremental          = C0_evaluable AND NOT C0_pass
adaptive_operator_not_incremental                = C2_evaluable AND NOT(C2a_pass AND C2b_pass AND selector_stable)
operator_codebook_capacity_only_diagnostic       = C2_evaluable AND C2a_pass AND NOT C2b_pass
mlp_residual_not_incremental                     = C3a_evaluable AND NOT C3a_pass
residual_stack_not_incremental                   = C3b_evaluable AND NOT C3b_pass
diffusion_not_incremental_vs_mlp                 = C4_evaluable AND NOT C4_pass
diffusion_tail_specialist_diagnostic             = C4_evaluable AND NOT C4_pass AND frozen_tail_slice_pass
complex_model_gain_not_mechanistically_attributed = C1_pass AND any critical module flag above is true
```

尚未评价的 contrast 对应 flag 必须为 null/`not_evaluable`，禁止把 missing 当 `false pass` 或 `true failure`。

`terminal_state_decision.csv` 必须包含唯一 primary state、全部 diagnostic flags、触发 contrast/gate、evidence stage 和 first-match
priority；report 可以同时解释多个 module flags，但不得把它们并列写成多个终态。

---

## 10. Requirement 路线图

### 21A：论文血缘、PIT 数据与 architecture contract

```text
requirement_21a_paper_lineage_pit_data_and_architecture_contract.md
```

这是当前 research plan 唯一直接授权生成的 requirement。只做 preoutcome audit、shape/config/search freeze 和 compute dry-run。

### 21B：Alpha158 baseline benchmark

```text
requirement_21b_alpha158_sequence_baseline_benchmark.md
```

只有 21A 人工批准后生成/执行。

### 21C：Adaptive Koopman nested ablation

```text
requirement_21c_single_vs_adaptive_koopman_nested_ablation.md
```

只有 21B validation-only baseline futility gate 通过后生成；不得读取 historical design holdout。

### 21D：Residual MLP vs diffusion attribution

```text
requirement_21d_residual_mlp_vs_diffusion_corrector_attribution.md
```

只有 21C 在 train/validation 上 Koopman pipeline evaluable 后生成。21D 全部 checkpoint 密封前不得读取 historical design
holdout；21D 末尾只允许一次性共同 readout。

### 21E：Top-30 next-open executable bridge

```text
requirement_21e_top30_next_open_executable_bridge.md
```

只有 full REAKA historical representation gate 通过后生成。

### 21F：Frozen true-forward confirmation

```text
requirement_21f_frozen_reaka_true_forward_confirmation.md
```

只允许按 Stage 21F 的 deterministic refit protocol 冻结一个 R2 ensemble、一个 M1 ensemble 和一个 M3 ensemble。M1/M3
身份在 historical holdout 解封前固定；任何 material change 都必须另建 cohort 并重启 forward clock。21F 不授权 forward nested
module attribution。

---

## 11. Minimum publishable artifacts

### 11.1 21A contract artifacts

```text
paper_source_registry.csv
paper_formula_and_architecture_registry.csv
paper_reproducibility_gap_registry.csv
official_code_availability_audit.csv
alpha158_expression_registry.csv
alpha158_local_field_mapping.csv
alpha158_expression_hash.txt
vwap_qfq_unit_and_range_audit.csv
alpha158_volume_corporate_action_audit.csv
alpha158_factor_jump_window_quarantine_sensitivity.csv
pit_membership_signal_execution_timing_audit.csv
feature_sequence_support_audit.csv
label_semantics_freeze.csv
decision_universe_and_label_resolution_contract.csv
train_teacher_inference_graph_contract.csv
per_arm_loss_and_score_index_contract.csv
split_purge_embargo_freeze.csv
model_arm_registry.csv
tensor_shape_contract.csv
hyperparameter_and_search_budget_freeze.csv
seed_and_randomness_freeze.csv
runtime_dependency_gpu_audit.csv
metric_margin_power_freeze.csv
forward_refit_and_comparator_freeze.csv
preoutcome_access_log.csv
freeze_bundle_manifest.json
21A_contract_decision.csv
```

### 11.2 Model/run artifacts

```text
feature_panel_manifest.json
decision_universe_and_label_resolution_audit.parquet
training_run_registry.csv
model_search_accounting_manifest.csv
checkpoint_manifest.json
pre_holdout_checkpoint_bundle_manifest.json
historical_design_holdout_access_audit.csv
seed_level_training_curves.csv
daily_prediction_scores.parquet
daily_rankic_readout.csv
paired_rankic_contrast_readout.csv
rankic_stability_and_concentration_audit.csv
model_parameter_compute_latency_audit.csv
koopman_consistency_readout.csv
operator_usage_entropy_and_transition_audit.csv
operator_spectral_stability_audit.csv
operator_assignment_seed_stability.csv
operator_capacity_matched_control_audit.csv
residual_point_and_distributional_readout.csv
residual_tail_regime_readout.csv
terminal_state_decision.csv
```

### 11.3 Economic artifacts

```text
paper_one_step_top30_readout.csv
qlib_gap_label_timing_sensitivity.csv
project_executable_top30_orders.csv.gz
project_executable_top30_positions.csv.gz
project_executable_top30_daily_nav.csv
turnover_cost_capacity_readout.csv
blocked_fill_and_cash_drag_audit.csv
drawdown_es10_concentration_readout.csv
economic_bridge_decision.csv
```

### 11.4 Final refit 与 forward artifacts

```text
final_refit_protocol.json
final_refit_data_cutoff_and_row_manifest.json
final_refit_transform_manifest.json
final_refit_checkpoint_manifest.json
forward_candidate_freeze_manifest.json
forward_daily_prediction_and_label_resolution.parquet
forward_paired_rankic_readout.csv
forward_executable_daily_nav_and_utility.csv
forward_gate_and_terminal_state_decision.csv
```

每一阶段必须有 report、decision CSV、manifest 和 output hashes。大型逐行 scores/orders 可以 gzip/parquet 保存，但 publishable
summary 不能只给 aggregate 而缺少可复算 lineage。

---

## 12. Quality-control checklist

### 12.1 PIT / timing

- [ ] feature bar date `<= decision_date`
- [ ] membership 由 `membership_date=t` 在 close t 后可知
- [ ] trade 最早 `usable_trade_date=t+1`
- [ ] 无 current constituent backfill
- [ ] 无 future normalization
- [ ] label 不参与 feature/row selection
- [ ] split boundary purge 覆盖 T 与 label horizon
- [ ] `U_t_decision` 在 outcome 前固定且全部 arms 共享
- [ ] suspension carry、terminal price、unknown gap、right censor 状态逐行可审计
- [ ] unknown/data-cutoff outcome 触发整日 not-evaluable，而不是逐股静默删除
- [ ] qfq price 与 money/volume adjustment 一致
- [ ] raw-share volume 与 factor-jump window 语义已冻结并有 sensitivity
- [ ] teacher target tensors 不进入 forecast/inference path
- [ ] primary score 明确来自 `Z_t -> Z_(t+1)` 的 decoder final scalar

### 12.2 Paper fidelity

- [ ] T=10 primary
- [ ] return/feature dual LSTM
- [ ] sigmoid gate 公式一致
- [ ] single vs adaptive operator 分开
- [ ] Gumbel train / argmax inference 语义明确
- [ ] residual target 为 `Z+ - K_s Z`
- [ ] DDPM condition 包含 current Z
- [ ] decoder/loss shape 有 unit tests
- [ ] primary 对全部 T 个 shifted transitions 计算 Koopman/residual loss
- [ ] loss 的 batch/time/latent reduction 使用冻结的 mean semantics
- [ ] `L_rec` 明确包含 final-step supervised `L_forecast`
- [ ] K1C capacity-matched non-adaptive control 已物化
- [ ] unreported choices 标记 project choice
- [ ] 不使用论文结果作本地 pass threshold

### 12.3 Statistical / ML governance

- [ ] chronological split only
- [ ] one primary config
- [ ] all trials counted
- [ ] historical design holdout 在全部 mandatory checkpoints 密封前未读取
- [ ] pre-holdout checkpoint bundle 与一次性 access audit 可双向复核
- [ ] M1/M3 forward comparator 身份在 historical holdout 前冻结
- [ ] deterministic final-refit protocol 在 historical holdout 前冻结
- [ ] final refit epoch/data window/transform/checkpoint 可由 manifest 复算
- [ ] 首个 252-day forward cohort 无 rolling retrain 或 normalizer refresh
- [ ] at least 3 seeds
- [ ] ensemble aggregation pre-frozen
- [ ] paired daily inference
- [ ] daily rather than stock-day evidence unit
- [ ] Holm correction for primary contrasts
- [ ] early/late, seed, concentration diagnostics
- [ ] best seed / best sensitivity 不替代 primary

### 12.4 Execution

- [ ] close proxy 与 executable PnL 分表
- [ ] TopK=30 固定
- [ ] continuous no-injection NAV
- [ ] blocked buy 留现金
- [ ] blocked exit 占用资本
- [ ] commission/stamp/slippage 生效日期正确
- [ ] turnover/capacity/break-even cost 披露
- [ ] 不把 long-short spread 当 long-only 可执行收益

### 12.5 Engineering

- [ ] dependency lock reproducible
- [ ] no silent runtime install
- [ ] shape/gradient/NaN tests
- [ ] deterministic seed mapping
- [ ] transactional output publication
- [ ] no partial `.building` promoted as final
- [ ] manifest file-set bidirectional audit
- [ ] output hashes verified
- [ ] `git diff --check`

---

## 13. Paper claims 的解释边界

论文提供的是一个值得检验的 architecture hypothesis：市场状态可能需要多个 latent linear operators，而有限维 Koopman
近似未解释的 residual 可能包含 state-dependent、non-Gaussian 和 shock-prone 结构。它没有证明：

- operator selector 学到经济上真实且稳定的 regime；
- diffusion 在相同参数和 compute budget 下优于普通 residual network；
- CSI300 当前成分或任意 A 股 PIT universe 都能复现论文数字；
- daily Top-30 在 A 股 next-open、涨跌停和成本后仍有收益；
- historical design holdout 结果可以直接部署。

EP21 的贡献应是建立一条可审计的证据链：

```text
paper architecture lineage
    -> PIT Alpha158/timing contract
    -> shared-data simple baselines
    -> single vs adaptive Koopman attribution
    -> MLP vs diffusion residual attribution
    -> executable Top-30 bridge
    -> true-forward confirmation
```

如果 full REAKA 只在 reconstruction/MSE 上改善而 RankIC 不改善，应关闭 prediction claim；如果 RankIC 改善但 nested ablation
不能定位来源，应把它降级为复杂模型增量而不是 Koopman/diffusion 机制证据；如果 RankIC 改善但成本后失败，应保留为
representation-only diagnostic。只有 seal 后 forward 中 R2 相对预冻结 M1/M3 的预测、执行与风险门全部通过，才允许人工发起
下一阶段策略研究；21C/21D 的模块归因仍须明确标记为 historical diagnostic，不能被 21F 自动升级为 forward mechanism support。
