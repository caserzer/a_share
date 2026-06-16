# 需求：Big Winner Path-Archetype 只读统计 Profiling（v0）

## 0. 路径基准

本 requirement 同时引用 repo-root 路径与实验目录相对路径，必须按以下规则解析：

1. `REPO_ROOT` 是当前 Git repository root。
2. `TOPIC_ROOT` 是 `topics/02_AFML_BIG_WINNER`。
3. `EXPERIMENT_ROOT` 是 `TOPIC_ROOT/experiments/pending/10_riskon_layered_rejector_system_v0`。
4. 以 `topics/` 开头的路径一律按 repo-root-relative 解析。
5. 以 `../` 开头的路径一律按 `EXPERIMENT_ROOT` 相对路径解析。
6. 其他相对路径（`outputs/`、`configs/`、`src/`、`tests/`）一律按 `EXPERIMENT_ROOT` 相对路径解析。
7. manifest 必须记录每个 input/output 的 resolved absolute path、relative path、file size、mtime UTC 与 content hash。

## 1. 背景

### 1.1 直接动因：10C 的失败不是均匀地打击 winner

10A–10C rejector 系统的诊断链（见 `discussion.md`）已经把 10C false-repair rejector 的失败根因锁定为：

> **拒绝"量"不漂、拒绝"方向"漂。** 同一个 10% 拒绝预算，train 上能避开 winner，OOS 上系统性地把一类特定 winner —— E1-missed / early-shakeout（先假摔、回踩、再走出的大赢家）—— 误判成 false-repair 拒掉。被 10C `full / keep_9000` 杀掉的 winner 中约 **70–82% 是 E1-missed**（train 82% / validation 69% / robustness 79%）。

这说明一个被现有 label 体系掩盖的事实：

> 当前 `winner_120` 是一个纯 endpoint label（120d 内 MFE 触及 right-tail 阈值即为 winner），它把**路径完全不同的大赢家塞进同一个保护池**。直拉型、先假摔再起、震荡走高、晚点火型，在 endpoint 上同为 winner，但它们对 t0 entry rejector 的**可保护性完全不同**：
> - 直拉型在 t0 起步即走，rejector 物理上碰不到，天然 winner-safe；
> - early-shakeout 型在 t0 之后先回踩（正好落进 20d false-repair 判定窗口），与真 false-repair 在 t0 特征空间物理同形 —— 这是 injury 的集中来源。

因此，要解释并最终解决 10C/10D 的 winner injury，必须先有一个**按 path 划分 winner** 的能力，而不是停留在 endpoint 同质假设上。

### 1.2 本 requirement 与既有 archetype 草案的关系

`EXPERIMENT_ROOT` 下曾有一份 `big_winner_archetype_diagnostic.md` 草案，给出了一组带固定阈值的 archetype 规则（`gap_or_event_driven` / `shakeout_reversal` / `volatile_chop` / `early_momentum` / `late_bloomer`，阈值如 `mae_20d <= -0.08`、`max_drawdown <= -0.15`、`limit proxy 0.095` 等）。

**本 requirement 明确不采用那组固定阈值作为冻结定义。** 那些阈值只是先验假设，存在已知问题（优先级把 shakeout 喂给 gap、mae 窗口被 run 后回吐掩盖、limit proxy 不分板块、shakeout floor 未与 winner 自身 failure barrier 对齐等）。本 requirement 的核心立场是：

> **先对完整数据集做统计，观察 path 度量在全量与 split 间的分布形态；是否需要冻结 archetype、边界画在哪，留给后续基于这些统计的独立 requirement 决定。**

本阶段只做只读统计 profiling：在全量 winner population 上计算 path 度量分布，并在 `train` / `validation` / `robustness` 上分别计算**同一套统计**，用来观察不同时间 / regime split 下是否存在 path 风格迁移。草案里的规则被降级为 **Appendix A 的 seed 假设（non-binding）**，仅用于对照统计，绝不作为冻结判据。

### 1.3 本 requirement 不做什么

1. 不冻结任何 archetype 阈值为生产定义；本阶段只产出全量与 split 分层的经验分布、seed 假设对照与 style migration readout。
2. 不把 path archetype 作为 t0 entry rejector 的 predictor（path 用未来信息，leakage 红线）。
3. 不选择阈值、聚类数、划分规则；本阶段不产出冻结 `winner_path_archetype_v1`。
4. 不替换 `winner_120` 作为主 KPI / retention 分母。
5. 不重训 10A/10B/10C，不回改上游冻结结论。
6. 不声称任何 supported gate；本 requirement 的最高产出是 `statistics_complete`，不是 model-supported 或 archetype-supported。

## 2. 目标

在尽可能完整的 winner population 上，用**只读统计**方式回答四个问题：

```text
Q1  完整数据集里，big winner 的 forward path 在哪些可观测维度上分散？
    （day-to-target、early drawdown、回撤深度、跳空/涨停强度、点火时间等）

Q2  全量统计与 train / validation / robustness 分层统计是否一致？
    是否存在明显 path 风格迁移（style migration）？

Q3  10C / 10D 被拒的 winner 是否集中在某些 path 度量区间或 seed 假设 bucket？
    这些 bucket 与 E1-missed / bridge winner 的重合度有多高？

Q4  injury 集中度、E1 对齐关系、path 分布差异在 split 间是否同向？
    哪些统计因为 power 不足只能作为观察，不能解释为结构结论？
```

统计完成结论（`statistics_complete`）必须同时满足：

1. 完整数据集 forward-path 覆盖率达到 `min_path_coverage`（见 §10），且 input audit 无 blocking failure；
2. 所有核心 path 度量在 `all` / `train` / `validation` / `robustness` 四个统计层级上均输出同口径分布；
3. seed 假设 bucket、10C rejected-winner concentration、E1-missed / bridge 对齐表均按 split 输出；
4. report 明确区分"统计观察"与"待后续冻结的 archetype 定义"。

若输入可读但 coverage / power 不足，输出 `statistics_incomplete`，并把结论导向"扩大 winner universe / 补 forward-path 数据 / 后续再做更粗或更稳的 archetype 定义"，而不是强行冻结多类 archetype。

## 3. Scope 与判定纪律

### 3.1 两层 scope

本 requirement 用两个 population，分别服务"全量统计"与"injury 归因"：

```text
profiling_scope（最大化 power，用于 Q1/Q2）
    = 当前实验可获得的全部 winner_120 == true 且 horizon_complete_120d == true 的事件
    = 优先使用 09A selected_label_event_bindings 的 winner 全集，
      不强制收缩到 10A post-dedup；目的是让统计有最大样本量

injury_scope（与 10C 对齐，用于 Q3/Q4）
    = 10A default supported scope:
      population_id = 10A__same_instrument_cooldown_10d
      denominator_id = post_dedup_risk_on_r_core
      admission_status = admitted
```

`profiling_scope` 与 `injury_scope` 的样本数差异、winner 重合关系必须在 coverage audit 中显式报告。injury crosstab 只能在 `injury_scope` 上做。所有 distribution / concentration / alignment 表必须至少输出四个层级：

```text
split = all
split = train
split = validation
split = robustness
```

### 3.2 path = 未来信息，只读不可作 predictor（红线）

所有 forward-path 派生量（day-to-target、drawdown、gap、limit count、archetype label 等）**使用 t0 之后的价格路径**，因此：

```text
Allowed:
    分布 profiling / 分位统计
    winner retention by seed bucket / metric bin
    10C / 10D rejected-winner concentration crosstab
    winner-safe label engineering 讨论
    exit / continuation policy 设计（t+k path 信息可见之后）

Forbidden:
    作为 t0 entry / rejector 的 predictor 或 feature
    在任一 split 或全量上选择并冻结阈值 / 聚类数 / 划分
    仅凭 path readout 声称 supported gate
    替换 winner_120 作为主 endpoint KPI
```

implementation 必须在 validation 中 assert：seed bucket、`winner_path_archetype_v0` 诊断标签及任何中间派生量都未进入任何 t0 模型设计矩阵（本实验不训练模型，但要为后续阶段固化这条边界）。

## 4. Required Inputs

### 4.1 winner / label / split inputs

| artifact | required | usage |
|---|---|---|
| `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet` | yes | winner 全集、`event_big_winner_120d_label`、horizon-complete flags、split、join keys |
| `outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet` | yes | injury_scope 过滤、E1/bridge flags、admission_status、input_event_key |
| `outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet` | yes | 10C `full / keep_9000` candidate_rejected_flag，用于 injury crosstab |
| `configs/labels.yaml`（`TOPIC_ROOT/configs/labels.yaml`） | yes | `labels.label_families.winner_120.right_tail_threshold_pct`、confirm/failure barrier，作为 seed 阈值的权威来源，禁止硬编码 |

winner 阈值必须从 `configs/labels.yaml` 的 `labels.label_families.winner_120.right_tail_threshold_pct` 读取（当前为 `0.50`），并写入 manifest；不得在代码里硬编码 `0.50`。所有 "to-target" 窗口以该阈值定义，记为 `winner_mfe_threshold`。

以下 label-family config 也必须读取并写入 manifest hash，禁止硬编码：

```text
confirm_upper_barrier =
  labels.label_families.confirm_20.upper_barrier_pct
  # current config value: 0.12

failure_lower_barrier =
  labels.label_families.failure_10.lower_barrier_pct
  # current config value: -0.08

failure_max_drawdown =
  labels.label_families.failure_10.max_drawdown_pct
  # current config value: -0.10

close_based_drawdown_policy =
  labels.barrier_observation.close_based_drawdown
  # current config value: true

hard_failure_first_blocks_winner =
  labels.label_families.winner_120.hard_failure_first_blocks_winner
  # current config value: true
```

当前 `hard_failure_first_blocks_winner == true`，因此 `winner_120` population 已经被"hard-failure 先触发则不算 winner"条件化。所有 early-drawdown / seed shakeout 统计都必须在这个条件下解释：`shakeout` 占比偏低可能来自 winner 定义本身先验裁掉了一部分 hard-failure-first path，而不等价于"E1-missed 不是 shakeout"。

### 4.2 forward-path OHLC inputs

| candidate artifact | usage |
|---|---|
| `../02_big_winner_reverse_lifecycle_profile_v0/outputs/large_raw/anchor_aligned_daily_panel.parquet` | 候选 forward OHLC 来源 |
| `../02_big_winner_reverse_lifecycle_profile_v0/outputs/local_cache/episode_aligned_daily_panel.parquet` | 候选 forward OHLC 来源 |

forward-path 是本 requirement 的**运行时硬依赖**，预期可位于服务器 local cache；当前本地 workspace 不要求预先验证这些路径。现有 10C/08 label parquet 只有 aggregated `mfe_20d` 等标量、**没有逐日 OHLC 序列**。implementation 必须：

1. 在 input audit 中确认存在一个能按 `(instrument, trade_open_date)` 对齐、覆盖 `d = 1..120` forward sessions 的 qfq OHLC 面板；
2. 校验对齐口径（`trade_open_price`、qfq adjustment、forward session 计数）与 04/02 label 约定一致；
3. 若不存在 trade_open 对齐的逐日面板，或对齐口径不可复核，则对应行 `winner_path_status = input_blocked_missing_forward_path`，并在 coverage audit 中计数；
4. 若 forward-path 覆盖率低于 `min_path_coverage`，整份 decision 降级为 `input_blocked` 或 `statistics_incomplete`（按 §11）。

禁止用 aggregate 标量（`mfe_20d` / `mae_20d` / `mfe_60d` 等）反推逐日 path 形状；aggregate 标量只能作为 path 派生量的 sanity 对照。

### 4.3 aggregate 标量 inputs（只读对照，禁止反推 path）

若 09A/10A binding 提供 `mfe_20d` / `mae_20d` / `mfe_60d` / `mae_60d` / `mfe_120d` / `mae_120d`，implementation 必须：

1. 在 input audit 中确认这些字段的**符号约定**（mae 是负号还是正幅值），并写入 manifest；
2. 仅把它们用于校验逐日 path 重算结果（如 `recomputed_mfe_120 ≈ mfe_120d`，不一致率超 `agg_path_mismatch_tol` 即 input-blocking）；
3. 不得用它们替代逐日 path 计算。

## 5. Join Contract

1. **winner base**：`profiling_scope` 从 09A bindings 过滤 `event_big_winner_120d_label == true and horizon_complete_120d == true`。
2. **forward-path join**：winner base 的 `(instrument, trade_open_date)` 对 forward OHLC 面板，要求 one-to-one、覆盖 `d=1..120`；缺失行单独计数为 `input_blocked_missing_forward_path`，不静默丢弃。
3. **injury join**：`injury_scope` 的 `binding_canonical_event_id`（派生规则见 10C/10D join 契约，从 `input_event_key` pipe 切分）对 10C scores，过滤到 `model_id=regularized_logistic_false_repair_20d_l2_v1` / `ablation_id=full` / `capacity_id=keep_9000` / `threshold_id=keep_9000` / `population_id=10A__same_instrument_cooldown_10d` / `denominator_id=post_dedup_risk_on_r_core`，过滤后按 `(input_event_key, split)` 唯一，join 零行丢失、无重复。
4. **E1 / bridge join**：从 10A `post_dedup_event_bindings` 携带 `E1_missed_winner_flag` / `bridge_winner` / `split`，与 winner base 按 canonical id 对齐。

所有 join 的行数、丢失数、重复数必须进 coverage audit。`split` 的权威来源是 10A binding（injury_scope）与 09A binding（profiling_scope），不得从 forward-path 面板推断。

## 6. Phase 1：原始 path 度量计算（无阈值）

在 `profiling_scope` 上，对每个有完整 forward-path 的 winner 计算一组**连续**path 度量。本阶段**不打任何 archetype 标签、不施加任何阈值**，只产出可供分布分析的连续量。度量以 `trade_open_price` 为基准、qfq forward OHLC 计算：

```text
ret_high[d]  = qfq_high[d]  / trade_open_price - 1
ret_low[d]   = qfq_low[d]   / trade_open_price - 1
ret_close[d] = qfq_close[d] / trade_open_price - 1
running_high[d] = max(qfq_high[1..d])

# 到达 winner 阈值的时间（窗口锚点）
day_to_target = min d in [1,120] where ret_high[d] >= winner_mfe_threshold
mfe_120_recomputed = max ret_high[d] over [1,120]

day_to_target null handling:
  if forward path OHLC missing:
    winner_path_status = input_blocked_missing_forward_path
  elif mfe_120_recomputed < winner_mfe_threshold:
    winner_path_status = winner_basis_mismatch
  else:
    winner_path_status = input_blocked_metric_inconsistency

# 点火 / 确认时间
day_to_confirm = min d in [1,120] where ret_high[d] >= confirm_upper_barrier  else null

# 到达阈值之前的早期回撤结构（窗口随 day_to_target 浮动，避免 run 后回吐污染）
pre_target_window = [1, day_to_target)
deepest_pre_target_ret_low   = min ret_low[d]   over pre_target_window
day_to_deepest_pre_target_low = argmin ret_low[d] over pre_target_window
max_drawdown_to_target = min over pre_target_window of qfq_low[d]/running_high[d] - 1

# 固定短窗早期回撤（与 confirm_20 同窗，便于和现有 label 对照）
deepest_ret_low_20 = min ret_low[d] over [1, min(20, day_to_target)]
day_to_deepest_low_20 = argmin ret_low[d] over [1, min(20, day_to_target)]

# hard-failure-first 条件化校准
pre_target_touch_failure_lower_flag =
    deepest_pre_target_ret_low <= failure_lower_barrier

close_drawdown_proxy[d] =
    qfq_close[d] / max(trade_open_price, max(qfq_close[1..d])) - 1

pre_target_close_drawdown_failure_proxy_flag =
    min close_drawdown_proxy[d] over pre_target_window <= failure_max_drawdown

# 跳空 / 涨停强度（窗口到 target）
max_single_day_close_return_to_target = max over [1,day_to_target] of qfq_close[d]/qfq_close[d-1]-1
max_gap_open_return_to_target         = max over [1,day_to_target] of qfq_open[d]/qfq_close[d-1]-1
limit_like_up_day_count_to_target     = count d in [1,day_to_target] where qfq_close[d]/qfq_close[d-1]-1 >= board_limit_proxy
    where qfq_close[0] = trade_open_price

# 形态汇总
mfe_20_recomputed / mfe_60_recomputed / mfe_120_recomputed
mae_20_recomputed / mae_60_recomputed / mae_120_recomputed   # 用于和 aggregate 标量对账
```

`board_limit_proxy` 必须按 instrument board 分档（主板/中小板 ~0.095，创业板/科创 ~0.195，ST ~0.048；具体档值入 config，见 §9），不得用单一 0.095。若无法判定 board，记 `limit_proxy_status = board_unknown` 并在该行用保守档，同时计数。

`day_to_target == null` 不得一律归为 path 缺失。`winner_basis_mismatch` 表示 aggregate winner label 与 trade-open forward OHLC 重算口径不一致，应进入 §4.3 对账与 `path_basis_reconciliation_audit.csv`，不计入 forward-path missing。coverage audit 必须分别报告 missing-path、basis-mismatch、metric-inconsistency。

由于 winner population 已被 `hard_failure_first_blocks_winner` 条件化，必须额外报告：

```text
pre_target_touch_failure_lower_n
pre_target_touch_failure_lower_rate
pre_target_close_drawdown_failure_proxy_n
pre_target_close_drawdown_failure_proxy_rate
```

这些计数用于校准"触及 failure lower barrier 但仍进入 winner population"的样本规模，帮助解释 seed shakeout bucket 的有效域被 winner 定义先验裁剪的问题。`pre_target_close_drawdown_failure_proxy_flag` 是 close-based drawdown proxy，用于解释 `failure_max_drawdown` 口径影响；若上游 label helper 可暴露 exact hard-failure-first 判定顺序，report 应同时输出 exact count，否则必须标明该列为 proxy。

**关键纪律：所有"早期回撤"度量的搜索窗口必须以 `day_to_target` 为上界**（`pre_target_window = [1, day_to_target)`），杜绝草案里"run 后获利回吐被误计为 early shakeout"的 B6 类 bug。固定 20d 窗口度量仅作对照，不作为冻结分型依据。

## 7. Phase 2–3：全量统计 + split 风格迁移 readout（核心）

### 7.1 Phase 2 全量 + split 单变量 / 多变量统计

对 §6 的连续度量，必须按同一套口径输出 `all` / `train` / `validation` / `robustness` 四层统计。`all` 是主统计层级；三个 split 用于观察风格迁移，不用于选择阈值或冻结 archetype。

```text
- 每个度量的分位数（p01/p05/p10/p25/p50/p75/p90/p95/p99）、mean、std、缺失率
- 度量两两之间的 Spearman 相关矩阵
- 关键度量的直方图分箱计数（bin 边界写入 config，确定性）
```

目的：在画任何边界之前，先看清每个维度的天然分布形状（单峰/多峰/长尾）、维度间冗余，以及不同 split 下 path 风格是否迁移。

### 7.2 Phase 3 style migration readout

对每个核心 path 度量，比较 `train` / `validation` / `robustness` 相对 `all` 的分布差异：

```text
quantile_delta[split, metric, q] =
    quantile(metric | split) - quantile(metric | all)

standardized_mean_delta[split, metric] =
    (mean(metric | split) - mean(metric | all)) / std(metric | all)

ks_statistic[split, metric] =
    two-sample KS statistic between split and all

psi[split, metric] =
    population stability index using fixed bins from config
```

同时输出 pairwise split comparison（`train_vs_validation`、`train_vs_robustness`、`validation_vs_robustness`）的 KS / PSI / mean delta，用来直接观察不同样本段之间的 path 风格迁移。

PSI / histogram 类统计必须带 power 标记：

```text
min_bin_count = config.style_migration.min_bin_count
if any compared bin count < min_bin_count:
  psi_bin_power_flag = low_power
  exclude that bin contribution from psi_total
```

KS / PSI / quantile delta 输出必须携带对应 split 的 `winner_n` / non-null metric n。report 对 validation 的迁移解读必须附样本量，且低 power bucket 只能写作观察，不能写作结构性迁移结论。

这些值只作 readout，不设置 pass/fail gate。report 必须把明显迁移的维度列出来，并说明可能影响后续 archetype freezing 的风险。

### 7.3 Phase 3 seed hypothesis readout（non-binding）

Appendix A 的 seed 假设可以被实现为 deterministic multi-hot flags，用于生成只读 crosstab：

```text
seed_gap_or_event_driven_flag
seed_shakeout_reversal_flag
seed_volatile_chop_flag
seed_early_momentum_flag
seed_late_bloomer_flag
```

这些 flag 只用于统计：

```text
count / rate by split
flag overlap matrix by split
10C rejected-winner concentration by flag and split
E1 / bridge alignment by flag and split
```

seed flags 一律使用 §6 的 recomputed path 度量实现，不得直接使用 aggregate `mfe_20d` / `mae_20d` / `mfe_60d` / `mae_60d` 列。Appendix A 中的 `mae_20d` / `mfe_60d` 等字样只是历史草案记法，在实现中必须映射到 `deepest_ret_low_20`、`mfe_60_recomputed`、`mae_60_recomputed` 等重算字段。

```text
seed_flag_overlap_n =
  count of true values among:
    seed_gap_or_event_driven_flag
    seed_shakeout_reversal_flag
    seed_volatile_chop_flag
    seed_early_momentum_flag
    seed_late_bloomer_flag
```

禁止把 seed flags 命名为冻结 archetype，禁止输出唯一主标签 `winner_path_archetype_v1`。如需输出 `winner_path_archetype_v0`，只能表示 Appendix A seed precedence 的诊断标签，并必须标 `archetype_status = seed_non_binding`。

## 8. Phase 4：Injury 集中度 + E1 一致性统计

在 `injury_scope` 上：

### 8.1 Injury 集中度

```text
对每个 reporting bucket b:
    injured_winner_n[b]   = count(winner in b and 10C full/keep_9000 rejected)
    winner_n[b]           = count(winner in b)
    injury_rate[b]        = injured_winner_n[b] / winner_n[b]
    share_of_injury[b]    = injured_winner_n[b] / total_injured_winner_n
    share_of_winner[b]    = winner_n[b] / total_winner_n
    injury_concentration_lift[b] = share_of_injury[b] - share_of_winner[b]
```

`reporting bucket` 包括：

```text
seed hypothesis flags from Appendix A
fixed histogram bins for core path metrics
optional 2D bins: deepest_pre_target_ret_low x day_to_target
```

必须按 `all` / `train` / `validation` / `robustness` 分别计算。`injury_concentration_lift` 只作统计 readout；本阶段不得因为某个 lift 过阈值而 claim archetype supported。

### 8.1.1 hard-failure 条件化与 winner basis 校准

必须输出独立校准表，避免把 winner 定义条件化误读成 path 事实：

```text
by split = all / train / validation / robustness:
  winner_n
  path_available_winner_n
  day_to_target_parsed_n
  day_to_target_parsed_rate
  winner_basis_mismatch_n
  winner_basis_mismatch_rate
  pre_target_touch_failure_lower_n
  pre_target_touch_failure_lower_rate
  pre_target_close_drawdown_failure_proxy_n
  pre_target_close_drawdown_failure_proxy_rate
```

其中 `pre_target_touch_failure_lower_n` 表示 winner 中曾在 target 前触及 `failure_lower_barrier` 但未被 hard-failure-first 阻断的样本量。若该数很低，不能直接解释为"没有 shakeout winner"；必须同时说明 winner population 已被 `hard_failure_first_blocks_winner` 条件化。

`injury_scope` 也必须报告同样的 `day_to_target_parsed_rate`。这用于检查 10A/10C 的 aggregate `winner_120` 口径与本 profiling 的 trade-open forward OHLC 重算口径是否一致。

### 8.2 Bucket × E1-missed 2×2 一致性（必须显式量化）

这是本 requirement 区别于"自说自话分型"的核心审计：forward-path seed bucket / metric bin 与 `E1_missed_winner_flag`（来自 episode membership）是**两套独立的 path 概念**，其重合是待验证假设，不是恒等式。

```text
对候选 shakeout-like bucket s：
                      E1_missed=true   E1_missed=false
    bucket=s             n11              n10
    bucket!=s            n01             n00

    报告：Jaccard、phi 系数、P(E1|s)、P(s|E1)，按 split
```

无论重合度高低都必须给出数字与解读：
- 高重合 → §1.1 的 injury 故事获得独立 path 佐证，支持后续优先研究"winner 保护下沉 exit 层"；
- 低重合 → injury 有多个来源，seed bucket 与 E1 需分别处理，报告必须明说。

## 9. Config Contract

implementation 必须创建 `configs/config_winner_archetype_profiling.yaml`，最少包含：

```yaml
run:
  experiment_id: big_winner_archetype_profiling_v0
  random_seed: 20260615
  winner_label_column: event_big_winner_120d_label
  winner_mfe_threshold_source: "topics/02_AFML_BIG_WINNER/configs/labels.yaml:labels.label_families.winner_120.right_tail_threshold_pct"
  confirm_upper_barrier_source: "topics/02_AFML_BIG_WINNER/configs/labels.yaml:labels.label_families.confirm_20.upper_barrier_pct"
  failure_lower_barrier_source: "topics/02_AFML_BIG_WINNER/configs/labels.yaml:labels.label_families.failure_10.lower_barrier_pct"
  failure_max_drawdown_source: "topics/02_AFML_BIG_WINNER/configs/labels.yaml:labels.label_families.failure_10.max_drawdown_pct"
  close_based_drawdown_policy_source: "topics/02_AFML_BIG_WINNER/configs/labels.yaml:labels.barrier_observation.close_based_drawdown"
  hard_failure_first_blocks_winner_source: "topics/02_AFML_BIG_WINNER/configs/labels.yaml:labels.label_families.winner_120.hard_failure_first_blocks_winner"

scope:
  profiling_population: all_winner_120_horizon_complete
  injury_population_id: 10A__same_instrument_cooldown_10d
  injury_denominator_id: post_dedup_risk_on_r_core

forward_path:
  forward_sessions: 120
  min_path_coverage: 0.90
  agg_path_mismatch_tol: 0.02

board_limit_proxy:
  main_board: 0.095
  chinext_star: 0.195
  st: 0.048
  unknown_fallback: 0.095

distribution_audit:
  quantiles: [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
  split_levels: [all, train, validation, robustness]
  histogram_bins:
    day_to_target: [0, 20, 40, 60, 90, 120]
    deepest_pre_target_ret_low: [-1.00, -0.30, -0.20, -0.12, -0.08, -0.04, 0.00, 0.50]
    max_drawdown_to_target: [-1.00, -0.30, -0.20, -0.12, -0.08, -0.04, 0.00]

style_migration:
  compute_ks: true
  compute_psi: true
  compute_quantile_delta: true
  min_bin_count: 5
  min_split_n_for_commentary: 100

injury:
  reference_10c_model_id: regularized_logistic_false_repair_20d_l2_v1
  reference_10c_ablation_id: full
  reference_10c_capacity_id: keep_9000
  reference_10c_threshold_id: keep_9000
  report_lift_alert_floor: 0.05

seed_hypothesis:
  use_appendix_a_as_binding: false   # 仅对照，永不冻结
```

修改任一 config 值必须产生新的 manifest hash 与 report note。winner / confirm / failure 阈值、hard-failure-first / close-based-drawdown policy、board limit 档、分位列表、直方图 bins、style migration 统计开关、seed 假设开关全部入 manifest hash。

## 10. Required Outputs

所有 publishable 表 UTF-8 CSV、稳定列序、确定性排序、无 wall-clock 时间戳。

```text
outputs/publishable/tables/big_winner_archetype_profiling/input_artifact_audit.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_coverage_audit.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_basis_reconciliation_audit.csv
outputs/publishable/tables/big_winner_archetype_profiling/hard_failure_conditioning_calibration.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_metric_distribution.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_metric_correlation.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_metric_histogram.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_style_migration_readout.csv
outputs/publishable/tables/big_winner_archetype_profiling/seed_hypothesis_readout.csv
outputs/publishable/tables/big_winner_archetype_profiling/seed_flag_overlap_by_split.csv
outputs/publishable/tables/big_winner_archetype_profiling/injury_concentration_by_bucket.csv
outputs/publishable/tables/big_winner_archetype_profiling/bucket_e1_alignment_2x2.csv
outputs/publishable/tables/big_winner_archetype_profiling/seed_hypothesis_comparison.csv
outputs/local_cache/big_winner_archetype_profiling/winner_path_metrics.parquet
outputs/manifests/big_winner_archetype_profiling_manifest.json
outputs/publishable/reports/big_winner_archetype_profiling_report.md
```

### 10.1 `winner_path_metrics.parquet`（至少）

```text
instrument
trade_open_date
trade_open_price
binding_canonical_event_id
input_event_key            # injury_scope 行有，profiling-only 行可空
split
winner_120
horizon_complete_120d
E1_missed_winner_flag
bridge_winner
winner_path_status         # ok | input_blocked_missing_forward_path | winner_basis_mismatch | input_blocked_metric_inconsistency | input_blocked
winner_mfe_threshold
confirm_upper_barrier
failure_lower_barrier
failure_max_drawdown
close_based_drawdown_policy
hard_failure_first_blocks_winner
day_to_target
day_to_confirm
deepest_pre_target_ret_low
day_to_deepest_pre_target_low
max_drawdown_to_target
deepest_ret_low_20
pre_target_touch_failure_lower_flag
pre_target_close_drawdown_failure_proxy_flag
max_single_day_close_return_to_target
max_gap_open_return_to_target
limit_like_up_day_count_to_target
board_limit_proxy_used
mfe_20_recomputed / mfe_60_recomputed / mfe_120_recomputed
mae_20_recomputed / mae_60_recomputed / mae_120_recomputed
seed_gap_or_event_driven_flag
seed_shakeout_reversal_flag
seed_volatile_chop_flag
seed_early_momentum_flag
seed_late_bloomer_flag
seed_flag_overlap_n
winner_path_archetype_v0   # only Appendix A seed precedence diagnostic; nullable
archetype_status           # seed_non_binding | not_assigned
tenc_full_keep9000_rejected_flag
```

### 10.2 Manifest（至少）

```text
decision
profiling_scope_winner_n
injury_scope_winner_n
path_coverage_rate
split_levels
style_migration_summary
winner_basis_mismatch_rate
hard_failure_conditioning_summary
injury_scope_day_to_target_parsed_rate
top_injury_concentration_buckets
injury_concentration_lift_by_split
bucket_e1_jaccard_by_split
winner_mfe_threshold
board_limit_proxy
input_hashes
config_hash
publishable_table_hashes
local_cache_hashes
input_failures
decision_block_reasons
```

Report 必须为中文，含数据表、findings、insight，并明确：
- 完整数据集上 big winner 的 path 分布形态；
- train / validation / robustness 与 all 的 path 分布差异，是否出现风格迁移；
- winner population 已被 `hard_failure_first_blocks_winner` 条件化，early-shakeout / seed shakeout 占比必须在该条件下解释；
- `winner_basis_mismatch`、`day_to_target_parsed_rate` 与 hard-failure conditioning calibration 的数字；
- seed 假设 bucket 仅作为 non-binding 对照，不能作为冻结 archetype；
- injury 是否集中、集中在哪些 metric bin / seed bucket、与 E1-missed 的 2×2 一致性数字；
- validation / low-power bucket 的迁移或 injury 结论必须附样本量，不得把低 power readout 写成结构性结论；
- 对 10D / Gate-0 与 exit-layer 方向的具体含义；
- decision 落入哪个状态及下一步建议。

## 11. Decision States

decision 必须恰为以下之一：

```text
big_winner_archetype_profiling_statistics_complete
big_winner_archetype_profiling_statistics_incomplete
big_winner_archetype_profiling_input_blocked
```

| decision | condition |
|---|---|
| `..._statistics_complete` | path 覆盖率达标，`all/train/validation/robustness` 四层统计、style migration readout、seed bucket readout、injury concentration、E1/bridge alignment 均完整输出 |
| `..._statistics_incomplete` | 输入可读、部分表可产出，但 coverage / power / split 缺失导致部分统计只能降级；报告必须列明缺口 |
| `..._input_blocked` | forward-path 缺失超容忍、join loss、label/符号校验失败、winner 阈值不可解析，或覆盖率低于 `min_path_coverage` |

本 requirement 没有 supported-model 或 archetype-supported 状态：最高 `statistics_complete` 只表示"统计表完整产出"，不等于任何可部署模型、gate 或冻结 archetype 定义。

## 12. Determinism 与 Validation

确定性要求：固定 `PYTHONHASHSEED` 或无 hash-order 依赖；分位/分箱边界确定性；CSV 输出前稳定排序；publishable 表无 wall-clock 时间戳；manifest `generated_at` 排除在 table hash 之外。

最少 validation 断言：

1. input audit 对 forward-path 与 winner label 无 blocking failure；
2. winner / confirm / failure 阈值、hard-failure-first / close-based-drawdown policy 来自 `configs/labels.yaml` nested keys，未硬编码；
3. 所有 early-drawdown 度量窗口上界 == `day_to_target`（杜绝 run 后回吐污染）；
4. board limit proxy 按 board 分档，未用单一常数；
5. `path_metric_distribution.csv` / `path_metric_histogram.csv` / `path_style_migration_readout.csv` 均包含 `all/train/validation/robustness` 四层统计；
6. `day_to_target == null` 被区分为 path missing / winner basis mismatch / metric inconsistency，三类不混算；
7. PSI bin 低于 `min_bin_count` 时标 `low_power` 且不计入 `psi_total`；
8. seed flags 使用 §6 recomputed path metrics，不直接使用 aggregate scalar columns；
9. `seed_flag_overlap_n` 等于 5 个 seed flag 中为 true 的个数；
10. seed bucket、`winner_path_archetype_v0` 诊断标签及任何 path 派生量未进入任何 t0 模型设计矩阵；
11. injury crosstab 仅在 injury_scope、仅对 10C `full / keep_9000`；
12. bucket × E1 的 2×2 四格数与边际一致；
13. hard-failure conditioning calibration 与 injury_scope `day_to_target_parsed_rate` 已输出；
14. 每张 publishable 表 hash 均在 manifest 中。

## 13. Implementation Notes

推荐实现位置：`src/run_winner_archetype_profiling.py`，可复用 10C/10D 的 `experiment_paths.py` / `io_contracts.py` / `metrics.py` / `reporting.py`。模块名是建议，不是契约；publishable artifact 名、schema、决策状态机、scope 定义、join 契约、统计 profiling 流程、leakage 边界才是契约。

---

## Appendix A：Seed 假设（non-binding，仅供 profiling 后对照）

以下来自早期 `big_winner_archetype_diagnostic.md` 草案，**不作为冻结定义、不作为判据**。仅用于 `seed_hypothesis_comparison.csv` 的 non-binding 对照统计。已知问题（必须在对照时一并记录）：优先级把 shakeout 喂给 gap、固定 20d mae 窗口被 run 后回吐掩盖、limit proxy 不分板块、shakeout floor 未与 winner failure barrier 对齐。

历史草案里的 `mae_20d` / `mfe_60d` / `max_drawdown` 字样不得解释为 aggregate scalar input。实现时必须使用 §6 的 recomputed path fields：

```text
mae_20d       -> deepest_ret_low_20
mfe_60d       -> mfe_60_recomputed
mae_60d       -> mae_60_recomputed
max_drawdown  -> max_drawdown_to_target
limit_count   -> limit_like_up_day_count_to_target
```

```text
# 阈值均为先验假设，仅用于 non-binding readout；profiling 只报告经验分布/分位，后续 requirement 再决定是否替换或冻结。
seed_gap_or_event_driven:
  limit_like_up_day_count_to_target >= 2
  OR max_gap_open_return_to_target >= 0.08
  OR max_single_day_close_return_to_target >= 0.18

seed_shakeout_reversal:
  deepest_ret_low_20 <= failure_lower_barrier
  AND day_to_deepest_low_20 < day_to_target

seed_volatile_chop:
  max_drawdown_to_target <= -0.15
  AND mfe_60_recomputed >= labels.label_families.continuation_60.min_mfe_pct
  AND mae_60_recomputed <= -0.12

seed_early_momentum:
  day_to_confirm <= labels.label_families.confirm_20.horizon_days
  AND day_to_target <= 60
  AND deepest_ret_low_20 > failure_lower_barrier
  AND max_drawdown_to_target > -0.12

seed_late_bloomer:
  day_to_target > 60
  AND mfe_20_recomputed < confirm_upper_barrier

# 先验阈值来源（对照用）
0.50  = winner endpoint threshold（实际从 configs/labels.yaml 读）
0.12  = confirm_20 upper barrier（从 config 核实）
-0.08 = confirm_20 lower barrier（从 config 核实）
-0.12 / -0.15 = 先验 deeper drawdown，无数据依据
0.095 = 先验 limit proxy，应按 board 分档替换
```
