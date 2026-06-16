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

> **先对 PIT executable universe 内的完整可评估 winner 数据做统计，观察 path 度量在全量与 split 间的分布形态；是否需要冻结 archetype、边界画在哪，留给后续基于这些统计的独立 requirement 决定。**

本阶段只做只读统计 profiling：在 **PIT executable universe 内的 winner population** 上计算 path 度量分布，并在 `train` / `validation` / `robustness` 上分别计算**同一套统计**，用来观察不同时间 / regime split 下是否存在 path 风格迁移。草案里的规则被降级为 **Appendix A 的 seed 假设（non-binding）**，仅用于对照统计，绝不作为冻结判据。

### 1.3 本 requirement 不做什么

1. 不冻结任何 archetype 阈值为生产定义；本阶段只产出全量、split 分层、regime 分层与 split × regime 联合视图的经验分布、seed 假设对照与 style / regime migration readout。
2. 不把 path archetype 作为 t0 entry rejector 的 predictor（path 用未来信息，leakage 红线）。
3. 不选择阈值、聚类数、划分规则；本阶段不产出冻结 `winner_path_archetype_v1`。
4. 不替换 `winner_120` 作为主 KPI / retention 分母。
5. 不重训 10A/10B/10C，不回改上游冻结结论。
6. 不声称任何 supported gate；本 requirement 的最高产出是 `statistics_complete`，不是 model-supported 或 archetype-supported。
7. 不使用 PIT executable universe 之外的 winner rows 生成主统计、injury concentration 或 E1/bridge alignment。非 PIT rows 只能进入 universe exclusion audit，不能混入 `all / train / validation / robustness` 主分母。

## 2. 目标

在 PIT executable universe 内尽可能完整的 winner population 上，用**只读统计**方式回答四个问题：

```text
Q1  PIT executable universe 内，big winner 的 forward path 在哪些可观测维度上分散？
    （day-to-target、early drawdown、回撤深度、跳空/涨停强度、点火时间等）

Q2  全量统计与 train / validation / robustness 分层统计是否一致？
    是否存在明显 path 风格迁移（style migration）？

Q3  10C / 10D 被拒的 winner 是否集中在某些 path 度量区间或 seed 假设 bucket？
    这些 bucket 与 E1-missed / bridge winner 的重合度有多高？

Q4  injury 集中度、E1 对齐关系、path 分布差异在 split 与 risk regime 间是否同向？
    哪些统计因为 power 不足只能作为观察，不能解释为结构结论？
```

统计完成结论（`statistics_complete`）必须同时满足：

1. PIT executable universe 过滤已成功执行，且 PIT-filtered 主分母 forward-path 覆盖率达到 `min_path_coverage`（见 §10），input audit 无 blocking failure；
2. 所有核心 path 度量在 split-only、regime-only、split × regime 三类 reporting view 上均输出同口径分布；
3. seed 假设 bucket、10C rejected-winner concentration、E1-missed / bridge 对齐表均按 split 与 `path_regime_state` 输出；
4. report 明确区分"统计观察"与"待后续冻结的 archetype 定义"。

若输入可读但 PIT universe 覆盖、forward-path coverage、power、split 或 regime 覆盖不足，输出 `statistics_incomplete`，并把结论导向"补 PIT universe join / 补 forward-path 数据 / 补 regime taxonomy / 后续再做更粗或更稳的 archetype 定义"，而不是强行冻结多类 archetype。

## 3. Scope 与判定纪律

### 3.1 Universe filter + 两个分析 scope

本 requirement 用一个 PIT universe 硬过滤层和两个分析 population，分别服务"全量统计"与"injury 归因"：

```text
universe_scope（所有主统计的硬过滤层）
    = topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv
    = point-in-time、close-observed、可执行股票池
    = membership_date = D 的信息在 D close 后可见，
      可执行日期为 usable_trade_date（下一交易 session）
    = join key: instrument | usable_trade_date

profiling_scope（最大化 power，用于 Q1/Q2）
    = 09A selected_label_event_bindings 中
      event_big_winner_120d_label == true
      and horizon_complete_120d == true
      and (instrument, trade_open_date) ∈ PIT executable universe
    = trade_open_date = 09A.trade_time
    = PIT join key: 09A.instrument | 09A.trade_time
      == pit_universe.instrument | pit_universe.usable_trade_date
    = 不强制收缩到 10A post-dedup；但必须收缩到 PIT executable universe

injury_scope（与 10C 对齐，用于 Q3/Q4）
    = 10A default supported scope:
      population_id = 10A__same_instrument_cooldown_10d
      denominator_id = post_dedup_risk_on_r_core
      admission_status = admitted
    = 再通过 injury_to_09a_join_key 回连到 PIT-filtered 09A profiling rows
    = 只有成功匹配 PIT profiling_scope 的 injury winners 才能进入
      injury concentration / E1 / bridge alignment 主表
```

`profiling_scope` 与 `injury_scope` 的样本数差异、PIT universe 过滤前后 winner 数、非 PIT rows 的排除原因、winner 重合关系必须在 coverage audit 中显式报告。injury crosstab 只能在 PIT-filtered `injury_scope` 上做。所有 distribution / concentration / alignment 表必须按 `split` 与 `path_regime_state` 两个 reporting axis 输出，至少覆盖：

```text
split = all
split = train
split = validation
split = robustness

path_regime_state = all
path_regime_state = risk_on
path_regime_state = risk_off
path_regime_state = transition
```

实现必须输出 split-only（`path_regime_state = all`）、regime-only（`split = all`）与 split × regime 联合视图。低样本 joint cell 必须带 `low_power` 标记，不得因为 regime 维度样本不足而强行写成结构结论。

`path_regime_state` 的主 reporting levels 必须是 `risk_on / risk_off / transition`。若 09A `episode_regime_bucket` 缺失但 `event_regime_bucket` 存在，必须使用 `event_regime_bucket` 回填 `path_regime_state`，否则会把可分类 winner 错误挪入 missing bucket，改变不同 regime 下的 big winner 分布。回填必须显式审计，不能静默发生。

PIT universe 过滤是硬约束，不是 optional coverage caveat。`instrument_metadata_target_universe.csv` 只能作为 listing / board metadata 使用，不能替代 `pit_largecap_main_chinext_executable_daily.csv` 定义 universe membership。若 PIT executable universe artifact 缺失、schema 不满足、或 `(instrument, trade_open_date)` join 无法执行，decision 必须为 `big_winner_archetype_profiling_input_blocked`。

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
| `topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv` | yes | PIT executable universe 硬过滤层；必须按 `instrument + usable_trade_date` 过滤 profiling / injury 主分母；`membership_date` / `available_time` / `membership_rule_version` 写入 audit |
| `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet` | yes | PIT 过滤前 winner 候选全集、`event_big_winner_120d_label`、horizon-complete flags、split、regime、join keys；`trade_time` canonicalized as `trade_open_date`，`event_split` canonicalized as `split` |
| `outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet` | yes | injury_scope 过滤、`E1_missed_winner_flag`、admission_status、input_event_key |
| `outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet` | yes | 10C `full / keep_9000` candidate_rejected_flag、`bridge_positive_flag`，用于 injury crosstab / bridge 对齐 |
| `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv` | yes | `board_bucket` / listing metadata，用于 board-specific limit proxy；不得用于 universe membership 过滤 |
| `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/sh_name_history/{instrument}.csv`、`topics/02_AFML_BIG_WINNER/data/raw/akshare/status/stock_info_sz_change_name_short.csv` | optional | historical ST name evidence；可用时用于 ST 0.048 limit proxy，缺失时输出 `st_status_source = not_evaluable_non_blocking` |
| `configs/labels.yaml`（`TOPIC_ROOT/configs/labels.yaml`） | yes | `labels.label_families.winner_120.right_tail_threshold_pct`、confirm/failure barrier，作为 seed 阈值的权威来源，禁止硬编码 |

PIT executable universe schema 必须至少包含：

```text
instrument
usable_trade_date
membership_date
available_time
board_bucket
is_listed
is_st
is_suspended
membership_rule_version
```

PIT universe join canonicalization 必须显式写入 input audit 与 manifest：

```text
pit_universe_name = pit_largecap_main_chinext
pit_universe_file = topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv
pit_universe_join_key = instrument | usable_trade_date
trade_open_date = selected_label_event_bindings.trade_time
pit_universe_filter_key =
  09A.instrument | 09A.trade_time
  == pit_universe.instrument | pit_universe.usable_trade_date
pit_membership_date = pit_universe.membership_date
pit_available_time = pit_universe.available_time
pit_membership_rule_version = pit_universe.membership_rule_version
```

09A 字段 canonicalization 必须显式写入 input audit 与 manifest：

```text
trade_open_date = selected_label_event_bindings.trade_time
split           = selected_label_event_bindings.event_split
event_regime_state = selected_label_event_bindings.event_regime_bucket
episode_regime_state_raw = selected_label_event_bindings.episode_regime_bucket
path_regime_state =
  if non-empty episode_regime_bucket:
      episode_regime_bucket
  else if non-empty event_regime_bucket:
      event_regime_bucket
  else:
      regime_missing
path_regime_source =
  episode_regime_bucket
  | event_regime_bucket_fallback
  | unresolved_missing
binding_canonical_event_id = selected_label_event_bindings.canonical_event_id
profiling_row_identity = sample_id | selected_target_id | denominator_id
injury_to_09a_join_key =
  10A.sample_id | 10A.selected_target_id | 10A.input_denominator_id
  == 09A.sample_id | 09A.selected_target_id | 09A.denominator_id
```

PIT universe 过滤顺序：

```text
09A_raw_winner_candidate =
  event_big_winner_120d_label == true
  and horizon_complete_120d == true

profiling_scope =
  09A_raw_winner_candidate
  inner join pit_largecap_main_chinext_executable_daily
    on instrument + trade_open_date == instrument + usable_trade_date

non_pit_winner_candidate =
  09A_raw_winner_candidate anti join pit universe

injury_scope_pit =
  10A default injury_scope winner rows
  inner join profiling_scope
    by injury_to_09a_join_key
```

`non_pit_winner_candidate` 不得进入任何 distribution / style migration / seed / injury / alignment 主表，只能进入 `pit_universe_scope_audit.csv` 和 manifest exclusion counts。若后续要研究非 PIT rows，必须另立 requirement。

`path_regime_state` 是本 requirement 的主 regime reporting axis，主取值为 `risk_on` / `risk_off` / `transition`。该字段优先使用 09A `episode_regime_bucket`，因为 episode-side regime 更贴近 winner path 所属 episode；但若 `episode_regime_bucket` 缺失或为空，必须用同一 09A row 的 `event_regime_bucket` 回填，而不是把该 row 放入主统计的 missing bucket。这样可以避免 08 membership 覆盖缺口扭曲不同 regime 下的 big winner 分布。

回填纪律：

```text
event_regime_state        = selected_label_event_bindings.event_regime_bucket
episode_regime_state_raw  = selected_label_event_bindings.episode_regime_bucket
path_regime_state         = coalesce_non_empty(episode_regime_state_raw, event_regime_state)
path_regime_source        = episode_regime_bucket | event_regime_bucket_fallback | unresolved_missing
```

`event_regime_bucket_fallback` 不是新的 regime，而是 `path_regime_state` 的 source provenance。只有当 `episode_regime_bucket` 与 `event_regime_bucket` 同时缺失 / 非法时，才允许 `path_regime_state = regime_missing`；该 residual bucket 必须进入 coverage audit 与 report caveat。若 residual `regime_missing` 非零，decision 至少降级为 `statistics_incomplete`，不得输出未说明的 `statistics_complete`。report 必须同时披露 `path_regime_source` 分布、fallback 行数、fallback 行在 split / regime 下的分布。

09A 中同一 `(instrument, trade_open_date)` 可能对应多个 denominator / target 行。implementation 不得因为 path key 重复而静默去重 profiling rows；forward path 可按 `(instrument, trade_open_date)` 复用，但统计分母与 row identity 必须保留到 `profiling_row_identity` 粒度。

injury_scope 回连 09A 时必须使用 `injury_to_09a_join_key`。禁止只按 `sample_id` 或 `sample_id + selected_target_id` 回连 09A，因为同一事件可在多个 denominator 中出现；若该 join 非唯一或有丢失，必须进入 `path_coverage_audit.csv` 并使 decision 降级为 `input_blocked`。

injury rows 回连 09A 后还必须满足 PIT universe filter。10A/10C 中存在但不在 PIT-filtered profiling_scope 的 winner rows 必须输出：

```text
injury_excluded_non_pit_universe_n
injury_excluded_non_pit_universe_rate
injury_excluded_unmatched_pit_profile_n
```

这些 rows 不得进入 `injury_concentration_by_bucket.csv` 或 `bucket_e1_alignment_2x2.csv` 的主分母。

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

| artifact | required | usage |
|---|---|---|
| `topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv` | yes | authoritative per-instrument qfq daily OHLC source；必须包含 `date/open/high/low/close` |
| `topics/02_AFML_BIG_WINNER/data/interim/qlib_csv/day/{instrument}.csv` | fallback | qfq daily OHLC fallback / reconciliation source；若使用，必须在 input audit 标明 fallback reason |
| `../02_big_winner_reverse_lifecycle_profile_v0/outputs/large_raw/anchor_aligned_daily_panel.parquet` | no | optional reference only；该 artifact 是 reverse-lifecycle aligned feature panel，不得作为 forward OHLC source |
| `../02_big_winner_reverse_lifecycle_profile_v0/outputs/local_cache/episode_aligned_daily_panel.parquet` | no | optional reference only；该 artifact 是 episode-aligned feature panel，不得作为 forward OHLC source |

forward-path 是本 requirement 的**运行时硬依赖**。现有 10C/08 label parquet 只有 aggregated `mfe_20d` 等标量、**没有逐日 OHLC 序列**；02 reverse-lifecycle 的 aligned panels 也没有可复核的 raw/qfq `open/high/low/close` 序列，因此不能满足本 requirement 的 OHLC source contract。implementation 必须从 qfq 日线 CSV 构造 event-aligned forward path：

1. 对每个 `instrument` 读取 qfq daily bar CSV，按 `date` 升序排序，并校验 `(instrument, date)` 唯一、`open/high/low/close` 非空且为正数；
2. 仅对 PIT-filtered `profiling_scope` 计算 forward path；qfq daily bar 的存在不能替代 PIT universe membership；
3. 对 PIT-filtered 09A winner base 使用 `trade_open_date = trade_time`，`trade_open_price = qfq_open` on `trade_open_date`；
4. `d = 1..120` 定义为 `trade_open_date` 之后的第 1 到第 120 个交易 session（strictly after `trade_open_date`），`qfq_close[0] = trade_open_price`；
5. 在 input audit 中确认每个 PIT profiling row 的 `(instrument, trade_open_date)` 能在 qfq daily bars 中定位，并覆盖完整 `d = 1..120`；
6. 校验对齐口径（`trade_open_price`、qfq adjustment、forward session 计数）与 09A `winner_120` label 约定一致；若使用 fallback source，必须同时输出 fallback source row count 与 mismatch readout；
7. 若不存在 qfq 日线 CSV、`trade_open_date` 不在该 instrument 的 qfq calendar 中、或 `d = 1..120` 不完整，则对应行 `winner_path_status = input_blocked_missing_forward_path`，并在 coverage audit 中计数；
8. 若 PIT-filtered forward-path 覆盖率低于 `min_path_coverage`，整份 decision 降级为 `input_blocked` 或 `statistics_incomplete`（按 §11）。

禁止用 aggregate 标量（`mfe_20d` / `mae_20d` / `mfe_60d` 等）反推逐日 path 形状；aggregate 标量只能作为 path 派生量的 sanity 对照。

禁止用 qfq CSV 文件清单、`instrument_metadata_target_universe.csv`、当前上市状态或任何 latest-only universe source 推断 PIT universe membership。唯一主分母过滤源是 `pit_largecap_main_chinext_executable_daily.csv` 的 `instrument + usable_trade_date`。

### 4.3 aggregate 标量 inputs（只读对照，禁止反推 path）

若 09A/10A binding 或 10C scores 提供 `mfe_20d` / `mae_20d` / `mfe_60d` / `mae_60d` / `mfe_120d` / `mae_120d`，implementation 必须：

1. 在 input audit 中确认这些字段的**符号约定**（mae 是负号还是正幅值），并写入 manifest；
2. 在 `path_basis_reconciliation_audit.csv` 中标明每个 aggregate scalar 的 source artifact、window basis 与 anchor basis；
3. 仅把它们用于校验逐日 path 重算结果（如 `recomputed_mfe_120 ≈ mfe_120d`）；只有当该 scalar 的 window basis 明确等同于 §4.2 的 `trade_open_date` strictly-after `d=1..120` 口径时，不一致率超 `agg_path_mismatch_tol` 才是 input-blocking；
4. 若 aggregate scalar 来自 10C 等下游 readout，且 basis 不同或不可复核，只能作为 non-blocking reconciliation readout，不得据此推翻 qfq daily bars 计算出的 path；
5. 不得用它们替代逐日 path 计算。

当前本地可用 artifact 中，10C reference scores 仅提供 `mfe_20d`；09A / 10A 未提供 `mfe_120d`、`mae_20d`、`mfe_60d`、`mae_60d`、`mae_120d` 等 aggregate scalar。因此 `path_basis_reconciliation_audit.csv` 在当前数据版本下预期只对可用的 `mfe_20d` 输出对账行，并对缺失 scalar 输出 `not_provided_non_blocking` 状态。缺失这些 aggregate scalar 不是 input-blocking，不影响 §4.2 qfq daily bars 的权威 forward-path 计算。

## 5. Join Contract

1. **raw winner candidate**：从 09A bindings 过滤 `event_big_winner_120d_label == true and horizon_complete_120d == true`，并 canonicalize `trade_open_date = trade_time`、`split = event_split`、`event_regime_state = event_regime_bucket`、`episode_regime_state_raw = episode_regime_bucket`、`path_regime_state = coalesce_non_empty(episode_regime_bucket, event_regime_bucket)`、`path_regime_source`、`binding_canonical_event_id = canonical_event_id`。
2. **PIT universe filter**：raw winner candidate 必须 inner join `pit_largecap_main_chinext_executable_daily.csv`：

```text
09A.instrument == pit_universe.instrument
09A.trade_open_date == pit_universe.usable_trade_date
```

join 后形成 `profiling_scope`。anti-join rows 进入 `pit_universe_scope_audit.csv`，不得进入 path metrics 或主统计表。PIT universe join key 若非唯一，decision = `input_blocked`。

3. **forward-path lookup**：PIT-filtered winner base 的 `(instrument, trade_open_date)` 对 qfq daily bars 定位 `trade_open_price` 与 `d=1..120` forward sessions。qfq price source 要求 `(instrument, date)` 唯一；winner base 允许多个 profiling rows 共享同一 `(instrument, trade_open_date)`，不得把这种合法复用计为 join duplicate。
4. **injury join**：`injury_scope` 的 `binding_canonical_event_id`（派生规则见 10C/10D join 契约，从 `input_event_key` pipe 切分）对 10C scores，过滤到 `model_id=regularized_logistic_false_repair_20d_l2_v1` / `ablation_id=full` / `capacity_id=keep_9000` / `threshold_id=keep_9000` / `population_id=10A__same_instrument_cooldown_10d` / `denominator_id=post_dedup_risk_on_r_core`，过滤后按 `(input_event_key, split)` 唯一，join 零行丢失、无重复。
5. **injury PIT carry-through**：injury readout 的 `path_regime_state` 与 PIT membership fields 必须来自 `10A.sample_id + 10A.selected_target_id + 10A.input_denominator_id == 09A.sample_id + 09A.selected_target_id + 09A.denominator_id` 的唯一 matched PIT-filtered 09A row。无法匹配 PIT-filtered 09A 的 injury winners 只能进入 exclusion audit，不得进入 injury concentration / alignment 主表。
6. **E1 / bridge join**：从 10A `post_dedup_event_bindings` 携带 `E1_missed_winner_flag` / `split`；从 10C reference scores 携带 `bridge_positive_flag`，并 canonicalize 为 output field `bridge_winner`。二者均与 PIT-filtered winner base 按 exact injury join key 对齐。
7. **injury regime carry-through**：10A `event_regime_bucket` 可输出为 `injury_event_regime_state` 供审计，但不得替代 PIT-filtered 09A 的 `path_regime_state`。injury readout 的 `path_regime_state` 必须继承 PIT-filtered 09A 的 episode-priority / event-fallback 结果与 `path_regime_source`。

所有 join 的行数、丢失数、重复数、PIT universe include/exclude counts 必须进 coverage audit。`split` 的权威来源是 10A binding（injury_scope）与 09A binding（profiling_scope），不得从 PIT universe 或 forward-path 面板推断。

## 6. Phase 1：原始 path 度量计算（无阈值）

在 `profiling_scope` 上，对每个有完整 forward-path 的 winner 计算一组**连续**path 度量。本阶段**不打任何 archetype 标签、不施加任何阈值**，只产出可供分布分析的连续量。度量以 `trade_open_price` 为基准、qfq forward OHLC 计算：

```text
trade_open_date  = 09A trade_time
trade_open_price = qfq_open on trade_open_date
qfq_open[d] / qfq_high[d] / qfq_low[d] / qfq_close[d]
    = d-th trading session strictly after trade_open_date, d in [1,120]

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
  elif any required qfq OHLC / trade_open_price is non-finite or <= 0:
    winner_path_status = input_blocked_metric_inconsistency
  elif mfe_120_recomputed < winner_mfe_threshold or day_to_target is null:
    winner_path_status = winner_basis_mismatch
  else:
    winner_path_status = ok

# 点火 / 确认时间
day_to_confirm = min d in [1,120] where ret_high[d] >= confirm_upper_barrier  else null

# 到达阈值之前的早期回撤结构（窗口随 day_to_target 浮动，避免 run 后回吐污染）
pre_target_window = [1, day_to_target)

empty pre_target_window handling:
  if day_to_target == 1:
    pre_target_window_status = empty_pre_target_window
    deepest_pre_target_ret_low = null
    day_to_deepest_pre_target_low = null
    max_drawdown_to_target = null
    pre_target_touch_failure_lower_flag = false
    pre_target_close_drawdown_failure_proxy_flag = false
  else:
    pre_target_window_status = ok
    deepest_pre_target_ret_low   = min ret_low[d]   over pre_target_window
    day_to_deepest_pre_target_low = argmin ret_low[d] over pre_target_window
    max_drawdown_to_target = min over pre_target_window of qfq_low[d]/running_high[d] - 1
    pre_target_touch_failure_lower_flag =
        deepest_pre_target_ret_low <= failure_lower_barrier
    close_drawdown_proxy[d] =
        qfq_close[d] / max(trade_open_price, max(qfq_close[1..d])) - 1
    pre_target_close_drawdown_failure_proxy_flag =
        min close_drawdown_proxy[d] over pre_target_window <= failure_max_drawdown

# 固定短窗早期回撤（与 confirm_20 同窗，便于和现有 label 对照）
deepest_ret_low_20 = min ret_low[d] over [1, min(20, day_to_target)]
day_to_deepest_low_20 = argmin ret_low[d] over [1, min(20, day_to_target)]

# 跳空 / 涨停强度（窗口到 target）
max_single_day_close_return_to_target = max over [1,day_to_target] of qfq_close[d]/qfq_close[d-1]-1
max_gap_open_return_to_target         = max over [1,day_to_target] of qfq_open[d]/qfq_close[d-1]-1
limit_like_up_day_count_to_target     = count d in [1,day_to_target] where qfq_close[d]/qfq_close[d-1]-1 >= board_limit_proxy
    where qfq_close[0] = trade_open_price

# 形态汇总
mfe_20_recomputed / mfe_60_recomputed / mfe_120_recomputed
mae_20_recomputed / mae_60_recomputed / mae_120_recomputed   # 用于和 aggregate 标量对账
```

`board_limit_proxy` 必须按 instrument board 分档（主板/中小板 ~0.095，创业板/科创 ~0.195，ST ~0.048；具体档值入 config，见 §9），不得用单一 0.095。board bucket 的权威来源是 `instrument_metadata_target_universe.csv.board_bucket`；若该字段缺失，可用 01 data-prep 的 code-prefix `board_bucket()` helper 作为 fallback，并记 `board_bucket_source = code_prefix_fallback`。若仍无法判定 board，记 `limit_proxy_status = board_unknown` 并在该行用 `unknown_fallback` 档，同时计数。

ST limit proxy 只在 historical name evidence 能证明该 instrument 在对应 trading session 处于 ST / *ST / 退市整理等 ST-like 名称状态时使用 `st` 档。可用 evidence source 包括 `sh_name_history/{instrument}.csv`、`stock_info_sz_change_name_short.csv` 与 `instrument_metadata_target_universe.csv.name`；若无法按 date 复核 ST 状态，不得静默套用 0.048，必须输出 `st_status_source = not_evaluable_non_blocking` 并使用 board bucket 档。`limit_proxy_status` 至少包含 `ok` / `board_unknown` / `st_status_not_evaluable`。

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

### 7.1 Phase 2 全量 + split / regime 单变量 / 多变量统计

对 §6 的连续度量，必须按同一套口径输出 `split` 与 `path_regime_state` 两个 reporting axis 的统计：

```text
split_levels = all / train / validation / robustness
path_regime_levels = all / risk_on / risk_off / transition
required_views:
  split-only: split_levels x path_regime_state=all
  regime-only: split=all x path_regime_levels
  split-regime: split_levels x path_regime_levels
```

`all` 是主统计层级；三个 split 用于观察时间 / OOS 风格迁移，`path_regime_state` 用于观察 risk-on / risk-off / transition 市场状态下的 path 风格差异。任何一个维度都不得用于选择阈值或冻结 archetype。`path_regime_source` 必须随统计输出或 audit 输出，确保 episode-source rows 与 event-fallback rows 可审计。

```text
- 每个度量的分位数（p01/p05/p10/p25/p50/p75/p90/p95/p99）、mean、std、缺失率
- 度量两两之间的 Spearman 相关矩阵
- 关键度量的直方图分箱计数（bin 边界写入 config，确定性）
```

目的：在画任何边界之前，先看清每个维度的天然分布形状（单峰/多峰/长尾）、维度间冗余，以及不同 split / 不同 risk regime 下 path 风格是否迁移。

### 7.2 Phase 3 style migration readout

对每个核心 path 度量，必须分别比较 split migration 与 regime migration：

```text
quantile_delta[split, metric, q] =
    quantile(metric | split) - quantile(metric | all)

standardized_mean_delta[split, metric] =
    (mean(metric | split) - mean(metric | all)) / std(metric | all)

ks_statistic[split, metric] =
    two-sample KS statistic between split and all

psi[split, metric] =
    population stability index using fixed bins from config

quantile_delta[path_regime_state, metric, q] =
    quantile(metric | path_regime_state) - quantile(metric | all)

standardized_mean_delta[path_regime_state, metric] =
    (mean(metric | path_regime_state) - mean(metric | all)) / std(metric | all)

ks_statistic[path_regime_state, metric] =
    two-sample KS statistic between path_regime_state and all

psi[path_regime_state, metric] =
    population stability index using fixed bins from config
```

同时输出 pairwise split comparison（`train_vs_validation`、`train_vs_robustness`、`validation_vs_robustness`）与 pairwise regime comparison（`risk_on_vs_risk_off`、`risk_on_vs_transition`、`risk_off_vs_transition`）的 KS / PSI / mean delta，用来直接观察不同样本段与不同市场状态之间的 path 风格迁移。若 joint split × regime cell 样本数不足，输出 `low_power`，但不得丢弃该行。

PSI / histogram 类统计必须带 power 标记：

```text
min_bin_count = config.style_migration.min_bin_count
if any compared bin count < min_bin_count:
  psi_bin_power_flag = low_power
  exclude that bin contribution from psi_total
```

KS / PSI / quantile delta 输出必须携带对应 split、`path_regime_state`、joint cell 的 `winner_n` / non-null metric n。report 对 validation 与 transition / risk_off 的迁移解读必须附样本量，且低 power bucket 只能写作观察，不能写作结构性迁移结论。

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
count / rate by split and path_regime_state
flag overlap matrix by split and path_regime_state
10C rejected-winner concentration by flag, split, and path_regime_state
E1 / bridge alignment by flag, split, and path_regime_state
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

在 PIT-filtered `injury_scope` 上：

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

必须按 `split` 与 `path_regime_state` 两个 reporting axis 分别计算，至少包含 split-only、regime-only 与 split × regime 联合视图。`injury_concentration_lift` 只作统计 readout；本阶段不得因为某个 lift 过阈值而 claim archetype supported。10A injury scope 的 event regime 可能高度集中于 risk-on，report 必须区分 `injury_event_regime_state` 与 09A carry-through 的 `path_regime_state`。

### 8.1.1 hard-failure 条件化与 winner basis 校准

必须输出独立校准表，避免把 winner 定义条件化误读成 path 事实：

```text
by split = all / train / validation / robustness
and path_regime_state = all / risk_on / risk_off / transition:
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

    报告：Jaccard、phi 系数、P(E1|s)、P(s|E1)，按 split 与 path_regime_state
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
  profiling_population: pit_universe_winner_120_horizon_complete
  pit_universe_name: pit_largecap_main_chinext
  pit_universe_join_key: [instrument, usable_trade_date]
  pit_universe_date_key: usable_trade_date
  pit_universe_filter_policy: require_instrument_trade_open_date_in_executable_universe
  injury_population_id: 10A__same_instrument_cooldown_10d
  injury_denominator_id: post_dedup_risk_on_r_core
  injury_non_pit_policy: exclude_from_main_readout_and_audit

paths:
  pit_executable_universe: "topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv"
  upstream_09a_bindings: "../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet"
  upstream_10a_bindings: "outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet"
  upstream_10c_scores: "outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet"
  labels_config: "topics/02_AFML_BIG_WINNER/configs/labels.yaml"
  qfq_dir: "topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq"
  qfq_fallback_dir: "topics/02_AFML_BIG_WINNER/data/interim/qlib_csv/day"
  board_metadata: "topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv"
  sh_name_history_dir: "topics/02_AFML_BIG_WINNER/data/raw/akshare/status/sh_name_history"
  sz_name_history: "topics/02_AFML_BIG_WINNER/data/raw/akshare/status/stock_info_sz_change_name_short.csv"

forward_path:
  forward_sessions: 120
  min_path_coverage: 0.90
  agg_path_mismatch_tol: 0.02

board_limit_proxy:
  main_board: 0.095
  chinext_star: 0.195
  st: 0.048
  unknown_fallback: 0.095
  board_bucket_source: "topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv:board_bucket"
  board_bucket_fallback: "01_data_prepare_pit_largecap_akshare_qlib_v0 board_bucket code-prefix helper"
  st_status_sources:
    - "topics/02_AFML_BIG_WINNER/data/raw/akshare/status/sh_name_history/{instrument}.csv"
    - "topics/02_AFML_BIG_WINNER/data/raw/akshare/status/stock_info_sz_change_name_short.csv"
    - "topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv:name"
  st_not_evaluable_policy: use_board_bucket_proxy_and_mark_st_status_not_evaluable

distribution_audit:
  quantiles: [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
  split_levels: [all, train, validation, robustness]
  path_regime_levels: [all, risk_on, risk_off, transition]
  required_reporting_views: [split_only, regime_only, split_regime]
  regime_state_source: "coalesce_non_empty(09A selected_label_event_bindings.episode_regime_bucket, 09A selected_label_event_bindings.event_regime_bucket)"
  regime_source_precedence: ["episode_regime_bucket", "event_regime_bucket"]
  episode_regime_missing_policy: "fallback_to_event_regime_bucket_and_audit_path_regime_source"
  residual_regime_missing_policy: "only_if_episode_and_event_regime_both_missing_or_invalid; decision_statistics_incomplete_if_nonzero"
  histogram_bins:
    day_to_target: [0, 20, 40, 60, 90, 120]
    deepest_pre_target_ret_low: [-1.00, -0.30, -0.20, -0.12, -0.08, -0.04, 0.00, 0.50]
    max_drawdown_to_target: [-1.00, -0.30, -0.20, -0.12, -0.08, -0.04, 0.00]

style_migration:
  compute_ks: true
  compute_psi: true
  compute_quantile_delta: true
  compute_regime_pairwise: true
  min_bin_count: 5
  min_split_n_for_commentary: 100
  min_regime_n_for_commentary: 100

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

`pit_executable_universe`、`pit_universe_filter_policy`、`pit_universe_date_key`、`injury_non_pit_policy`、`regime_source_precedence`、`episode_regime_missing_policy` 与 `residual_regime_missing_policy` 也必须入 manifest hash。若实现没有读取并应用这些 config 字段，不得输出 `statistics_complete`。

## 10. Required Outputs

所有 publishable 表 UTF-8 CSV、稳定列序、确定性排序、无 wall-clock 时间戳。

```text
outputs/publishable/tables/big_winner_archetype_profiling/input_artifact_audit.csv
outputs/publishable/tables/big_winner_archetype_profiling/pit_universe_scope_audit.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_coverage_audit.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_basis_reconciliation_audit.csv
outputs/publishable/tables/big_winner_archetype_profiling/hard_failure_conditioning_calibration.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_metric_distribution.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_metric_correlation.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_metric_histogram.csv
outputs/publishable/tables/big_winner_archetype_profiling/path_style_migration_readout.csv
outputs/publishable/tables/big_winner_archetype_profiling/seed_hypothesis_readout.csv
outputs/publishable/tables/big_winner_archetype_profiling/seed_flag_overlap_by_reporting_view.csv
outputs/publishable/tables/big_winner_archetype_profiling/injury_concentration_by_bucket.csv
outputs/publishable/tables/big_winner_archetype_profiling/bucket_e1_alignment_2x2.csv
outputs/publishable/tables/big_winner_archetype_profiling/seed_hypothesis_comparison.csv
outputs/local_cache/big_winner_archetype_profiling/winner_path_metrics.parquet
outputs/manifests/big_winner_archetype_profiling_manifest.json
outputs/publishable/reports/big_winner_archetype_profiling_report.md
```

所有 distribution / histogram / correlation / style migration / seed / injury / E1 alignment publishable tables 必须包含以下 reporting columns，确保 split 与 regime 维度可审计：

```text
reporting_view       # split_only | regime_only | split_regime
split                # all | train | validation | robustness
path_regime_state    # all | risk_on | risk_off | transition
winner_n
non_null_metric_n    # metric tables only
power_flag           # ok | low_power
```

### 10.0 `pit_universe_scope_audit.csv`（至少）

```text
audit_section                  # profiling_scope | injury_scope | pit_universe_schema | pit_universe_key
population_stage               # raw_09a_winner_candidate | pit_filtered_profiling_scope | excluded_non_pit | raw_injury_scope | pit_filtered_injury_scope | excluded_injury_non_pit
row_count
winner_n
unique_instrument_n
unique_trade_open_date_n
pit_universe_row_n
pit_universe_unique_key_n
pit_universe_duplicate_key_n
pit_universe_missing_key_n
pit_universe_joined_n
pit_universe_excluded_n
pit_universe_excluded_rate
split
path_regime_state
path_regime_source
episode_regime_missing_event_fallback_n
path_regime_unresolved_missing_n
exclusion_reason               # not_in_pit_executable_universe | pit_universe_duplicate_key | pit_universe_missing_required_field | none
pit_universe_name
pit_universe_date_key
pit_membership_rule_version
audit_status                   # pass | warning_low_power | input_blocked
```

`pit_universe_scope_audit.csv` 是主分母审计表。它必须能回答：09A raw winner 候选有多少、PIT 过滤后剩多少、哪些 split / regime 被排除最多、10A/10C injury winner 中有多少不在 PIT-filtered profiling scope。

### 10.1 `winner_path_metrics.parquet`（至少）

```text
instrument
profiling_row_identity
pit_universe_name
pit_universe_member_flag
pit_membership_date
pit_usable_trade_date
pit_available_time
pit_membership_rule_version
pit_board_bucket
pit_status_source
trade_open_date
trade_open_price
binding_canonical_event_id
source_denominator_id      # 09A denominator_id
injury_input_denominator_id # 10A input_denominator_id; injury_scope rows only
input_event_key            # injury_scope 行有，profiling-only 行可空
split
event_regime_state
episode_regime_state_raw
path_regime_state
path_regime_source          # episode_regime_bucket | event_regime_bucket_fallback | unresolved_missing
injury_event_regime_state  # injury_scope rows only; from 10A event_regime_bucket when available
winner_120
horizon_complete_120d
E1_missed_winner_flag
bridge_winner              # canonicalized from 10C bridge_positive_flag when available
winner_path_status         # ok | input_blocked_missing_forward_path | winner_basis_mismatch | input_blocked_metric_inconsistency | input_blocked
winner_mfe_threshold
confirm_upper_barrier
failure_lower_barrier
failure_max_drawdown
close_based_drawdown_policy
hard_failure_first_blocks_winner
day_to_target
day_to_confirm
pre_target_window_status   # ok | empty_pre_target_window
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
board_bucket_used
board_bucket_source
limit_proxy_status
st_status_source
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

`winner_path_metrics.parquet` 只能包含 PIT-filtered profiling rows。若为了 debug 保留非 PIT rows，必须另写 local-only exclusion cache，不能混进该主宽表。

### 10.2 Manifest（至少）

```text
decision
pit_universe_name
pit_universe_source_path
pit_universe_hash
pit_universe_date_key
pit_universe_filter_policy
raw_09a_winner_candidate_n
pit_filtered_profiling_scope_winner_n
excluded_non_pit_winner_candidate_n
excluded_non_pit_winner_candidate_rate
profiling_scope_winner_n
raw_injury_scope_winner_n
pit_filtered_injury_scope_winner_n
excluded_injury_non_pit_winner_n
injury_scope_winner_n
path_coverage_rate
split_levels
path_regime_levels
regime_source_precedence
episode_regime_missing_policy
episode_regime_missing_event_fallback_n
episode_regime_missing_event_fallback_rate
path_regime_source_counts
path_regime_unresolved_missing_n
style_migration_summary
regime_migration_summary
winner_basis_mismatch_rate
hard_failure_conditioning_summary
injury_scope_day_to_target_parsed_rate
top_injury_concentration_buckets
injury_concentration_lift_by_split
injury_concentration_lift_by_regime
bucket_e1_jaccard_by_split
bucket_e1_jaccard_by_regime
winner_mfe_threshold
forward_path_source_dir
forward_session_alignment
fallback_forward_path_source_dir
board_metadata_source
st_status_source_summary
board_limit_proxy
input_hashes
config_hash
publishable_table_hashes
local_cache_hashes
input_failures
decision_block_reasons
```

Report 必须为中文，含数据表、findings、insight，并明确：
- PIT executable universe 内 big winner 的 path 分布形态；
- train / validation / robustness 与 all 的 path 分布差异，是否出现风格迁移；
- risk_on / risk_off / transition 与 all 的 path 分布差异，以及 split × regime joint cell 的样本量与 low-power 标记；
- PIT executable universe 过滤前后 winner 数、非 PIT rows 的排除比例，以及该过滤如何改变 split / regime / injury 分母；
- winner population 已被 `hard_failure_first_blocks_winner` 条件化，early-shakeout / seed shakeout 占比必须在该条件下解释；
- `winner_basis_mismatch`、`day_to_target_parsed_rate` 与 hard-failure conditioning calibration 的数字；
- seed 假设 bucket 仅作为 non-binding 对照，不能作为冻结 archetype；
- injury 是否集中、集中在哪些 metric bin / seed bucket / regime state、与 E1-missed 的 2×2 一致性数字；
- validation / transition / risk_off / low-power bucket 的迁移或 injury 结论必须附样本量，不得把低 power readout 写成结构性结论；
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
| `..._statistics_complete` | PIT executable universe 过滤成功；非 PIT rows 已从主分母排除并审计；PIT-filtered path 覆盖率达标；`episode_regime_bucket` missing rows 已按 `event_regime_bucket` 回填并审计；residual `path_regime_state = regime_missing` 为 0；split-only / regime-only / split × regime 统计、style / regime migration readout、seed bucket readout、injury concentration、E1/bridge alignment 均完整输出 |
| `..._statistics_incomplete` | PIT universe 输入可读且过滤可执行、部分表可产出，但 PIT 过滤后 coverage / power / split / regime 缺失导致部分统计只能降级；或 `episode_regime_bucket` 与 `event_regime_bucket` 同时缺失 / 非法导致 residual `path_regime_state = regime_missing` 非零；报告必须列明缺口 |
| `..._input_blocked` | PIT universe artifact 缺失或 schema/key 不可用；PIT universe join 非唯一；forward-path 缺失超容忍；join loss；label/符号校验失败；winner 阈值不可解析；或 PIT-filtered 覆盖率低于 `min_path_coverage` |

本 requirement 没有 supported-model 或 archetype-supported 状态：最高 `statistics_complete` 只表示"统计表完整产出"，不等于任何可部署模型、gate 或冻结 archetype 定义。

## 12. Determinism 与 Validation

确定性要求：固定 `PYTHONHASHSEED` 或无 hash-order 依赖；分位/分箱边界确定性；CSV 输出前稳定排序；publishable 表无 wall-clock 时间戳；manifest `generated_at` 排除在 table hash 之外。

最少 validation 断言：

1. input audit 对 forward-path 与 winner label 无 blocking failure；
2. PIT executable universe artifact 来自 `topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv`，schema 包含 §4.1 要求字段；
3. PIT universe key `(instrument, usable_trade_date)` 唯一；若重复，decision = `input_blocked`；
4. `profiling_scope` 中每一行均满足 `instrument + trade_open_date == pit_universe.instrument + pit_universe.usable_trade_date`；`winner_path_metrics.parquet` 不含非 PIT rows；
5. `pit_universe_scope_audit.csv` 输出 raw 09A winner candidate、PIT-filtered profiling scope、excluded non-PIT rows、raw injury scope、PIT-filtered injury scope、excluded injury non-PIT rows；
6. `instrument_metadata_target_universe.csv` 仅用于 board/listing metadata，不得用于 universe membership 过滤；
7. winner / confirm / failure 阈值、hard-failure-first / close-based-drawdown policy 来自 `configs/labels.yaml` nested keys，未硬编码；
8. 09A field mapping 固定为 `trade_open_date = trade_time`、`split = event_split`、`event_regime_state = event_regime_bucket`、`episode_regime_state_raw = episode_regime_bucket`、`path_regime_state = coalesce_non_empty(episode_regime_bucket, event_regime_bucket)`、`path_regime_source = episode_regime_bucket | event_regime_bucket_fallback | unresolved_missing`，并保留 `profiling_row_identity = sample_id | selected_target_id | denominator_id`；
8a. `episode_regime_bucket` 缺失但 `event_regime_bucket` 存在的 rows 必须回填到 `risk_on / risk_off / transition` 主 reporting levels，并在 `path_regime_source = event_regime_bucket_fallback`、`episode_regime_missing_event_fallback_n` 中审计；不得把这些 rows 放入主统计 missing bucket；
8b. `path_regime_state = regime_missing` 只允许在 episode 与 event regime 同时缺失 / 非法时出现；若 residual missing 非零，decision 至少为 `statistics_incomplete`，report 必须披露 row count、split 分布与原因；
9. forward path source 来自 qfq daily bar CSV，且 `d=1` 是 `trade_open_date` 之后的第一个交易 session；02 reverse-lifecycle aligned panels 不得被接受为 OHLC source，除非未来 artifact schema 明确提供 raw/qfq `open/high/low/close` 且通过本节所有校验；
10. injury readout 回连 09A 仅使用 `10A.sample_id + 10A.selected_target_id + 10A.input_denominator_id == 09A.sample_id + 09A.selected_target_id + 09A.denominator_id`，且必须匹配到 PIT-filtered profiling scope；禁止 sample-only 或 sample+target-only join；
11. 非 PIT injury rows 不得进入 `injury_concentration_by_bucket.csv` 或 `bucket_e1_alignment_2x2.csv` 主分母；
12. 所有 early-drawdown 度量窗口上界 == `day_to_target`（杜绝 run 后回吐污染），且 `day_to_target == 1` 时输出 `pre_target_window_status = empty_pre_target_window` 并按 §6 空窗规则置值；
13. board limit proxy 按 board / ST 分档，未用单一常数；board bucket 与 ST status provenance 写入 output / manifest，ST 不可复核时使用 board bucket 档并标 `st_status_not_evaluable`；
14. `path_metric_distribution.csv` / `path_metric_histogram.csv` / `path_style_migration_readout.csv` 均包含 split-only、regime-only、split × regime 三类 reporting view；
15. `day_to_target == null` 被区分为 path missing / winner basis mismatch / metric inconsistency，三类不混算；
16. PSI bin 低于 `min_bin_count` 时标 `low_power` 且不计入 `psi_total`；
17. seed flags 使用 §6 recomputed path metrics，不直接使用 aggregate scalar columns；
18. `seed_flag_overlap_n` 等于 5 个 seed flag 中为 true 的个数；
19. seed bucket、`winner_path_archetype_v0` 诊断标签及任何 path 派生量未进入任何 t0 模型设计矩阵；
20. injury crosstab 仅在 PIT-filtered injury_scope、仅对 10C `full / keep_9000`；
21. bucket × E1 的 2×2 四格数与边际一致；
22. hard-failure conditioning calibration 与 PIT-filtered injury_scope `day_to_target_parsed_rate` 已输出；
23. 每张 publishable 表 hash 均在 manifest 中。

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
