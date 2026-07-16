# Requirement 21B：Alpha158 Sequence Baseline Benchmark

> 文档状态：`draft_requirement_pending_execution_approval`
>
> 生成日期：2026-07-13；修订日期：2026-07-14
>
> Experiment ID：`21_residual_enhanced_koopman_auto_encoder_v0`
>
> Phase ID：`21B`
>
> Run ID：`21B_alpha158_sequence_baseline_benchmark`
>
> Requirement version：`21B_v6`
>
> 上游研究计划：`research_plan.md`
>
> 当前执行状态：`pending_separate_21B_execution_approval`
>
> Claim ceiling：`validation_only_baseline_information_diagnostic`

## 0. 一页执行结论

21B 只回答一个问题：

> 在完全相同的 PIT decision rows、157-feature registered Alpha158 adaptation、raw return sequence 和一步 close-to-close label 下，
> `M1_LIGHTGBM_ALPHA158`、`M2_RETURN_LSTM`、`M3_GATED_DUAL_PATH_LSTM` 是否至少有一个在 validation 中提供稳定的正方向
> 横截面排序信息，从而值得继续进入 21C Koopman nested ablation？

21B 运行且仅运行：

```text
M0_HASH_NULL_SCORE
M1_LIGHTGBM_ALPHA158
M2_RETURN_LSTM
M3_GATED_DUAL_PATH_LSTM
A0_VANILLA_AUTOENCODER
```

21B 不运行 K1/K1C/K2/R1/R2，不读取 historical design holdout，不计算策略 PnL，不执行 Top-30 replay，不选择 feature、label、
operator、residual module、TopK 或成本参数。Validation 结果只是复杂架构的 futility screen，不是历史支持、可信 OOS support 或
deployment evidence。

为避免把同一 validation 信息同时用于 checkpoint 选择和 continuation gate，21B_v6 固定：

```text
provisional_candidate_selection_fold = validation_early
baseline_gate_fold = validation_late
validation_full_role = diagnostic_only
```

`validation_late` panel 只能在 12 个 learned provisional candidates 的 pre-gate bundle 已不可变密封后，由 fresh inference-only
gate-readout process 打开并生成 score-outcome join/metric；selection process 永远不得打开。此后不得重训、改 checkpoint 或替换 config。Materialization worker
可预先写入该独立 panel，但必须在写完、密封后退出，不能参与 provisional candidate selection。

当前已密封的 `21A_v1` **不是合格输入**：

```text
decision_state = 21A_pit_timing_or_denominator_contract_blocked
blocking_gate = pit_membership_timing_gate
failed_checks = U02|U03
freeze_bundle_hash = b13636af7716da6dcb31832782e123fb0a56d4edab4626f6c6e073cc5fd8ec99
```

v1 的失败是 runner 将终端数据截止右删失误判为 U02/U03 failure 的 false negative，不是应补造 2026-06-01 可交易结果。
该 bundle 继续保留为失败证据，禁止覆盖或作为 21B 输入。

已密封的 `21A_v2` 是本 requirement 唯一批准的 successor：

```text
approved_21a_output_root = outputs/21A_paper_lineage_pit_data_and_architecture_contract_v2
approved_21a_contract_version = 21A_v2
approved_21a_decision_state = 21A_preoutcome_architecture_contract_ready
approved_21a_critical_gates = 28/28 pass
approved_21a_gate_checks = 142/142 pass
approved_21a_freeze_bundle_hash = 0c6fb85a08315a5b1bd0b7621a4a7e4d36790d201eb83f8cca35f50d460cac16
approved_21a_decision_sha256 = 2dad2db00fca650f2b602331e15a783d8982daf272f59c717589a7c1096e9338
approved_21a_manifest_sha256 = 98f24dad24ca73b27edf58c0469db20182daab50b047da5556884fdd9df3c934
approved_21a_output_hashes_sha256 = edb5aaee713342169d84ddf78bcd1b5423f2bb9e4c4b8b20eed9308c4a29c961
approved_feature_cache_content_hash = 95839cfcbb28c7b83620936ec6beab38ff14adb182c8ce8dba4eaaebdcbfdee2
approved_feature_expression_sha256 = da50206946efd49cf7103a56561b7a5702503c18f70b4d8c5f48e8c1e9592188
approved_split_hash = ecff4e1b86c0383d593cef355770e14a6f54305006da33c0b789699064c067fa
approved_normalization_contract_hash = b924004891f52ab38329221d34f006ef31ea77b59f01b8187e62d894ceeb9be4
```

本 requirement 的生成来自 2026-07-13 workspace 用户显式请求；成功的 21A_v2 已授权生成/评审本 spec，但 21A decision 明确
`next_requirement_execution_authorized=false`，因此仍需单独的人类 21B execution approval。

21B runner 必须在任何 label、qfq outcome、feature cache 或 GPU 访问前验证上述不可变 21A_v2 successor。只有同时满足：

```text
approved_21a_decision_state = 21A_preoutcome_architecture_contract_ready
all_approved_21a_critical_gates = pass
approved_21a_next_requirement = requirement_21b_alpha158_sequence_baseline_benchmark.md
approved_21a_freeze_bundle_hash = exact runtime-configured SHA256
approved_21a_decision_sha256 = exact runtime-configured SHA256
separate_21b_execution_authorization.status = approved
separate_21b_execution_authorization.reviewer_role = human
```

才允许从 `preflight` 进入 `materialize-labels`。任一条件不满足必须 fail closed，输出 blocked preflight audit，并保持
`outcome_read_count=0`、`model_fit_count=0`。

## 1. 身份、目录与 stage

预期实现文件：

```text
requirement_file = requirement_21b_alpha158_sequence_baseline_benchmark.md
config_file = configs/config_21b_alpha158_sequence_baseline_benchmark.yaml
runner_file = src/run_21b_alpha158_sequence_baseline_benchmark.py
test_file = tests/test_21b_alpha158_sequence_baseline_benchmark.py
authorization_file = references/21b/execution_authorization.json
canonical_output_root = outputs/21B_alpha158_sequence_baseline_benchmark_v6
preauthorization_audit_root = outputs/21B_alpha158_sequence_baseline_benchmark_v6_preauthorization_audits
```

Canonical output root 必须显式包含 requirement version；禁止把 v4 写入未版本化 root、v1/v2/v3 root 或 `latest` alias。未来任何
material requirement change 必须使用新的 versioned root，旧 root 永不覆盖。

缺失或无效 human authorization 的 preflight 失败不得占用 canonical output root。该类 P0 audit 的落盘位置固定为：

```text
authorization_observation = "MISSING" if authorization path does not exist
                            else lowercase_sha256(full authorization file bytes)
preauthorization_audit_id = first_16_hex(
  SHA256(UTF8(requirement_sha256 + "|" + authorization_observation))
)
preauthorization_audit_path = preauthorization_audit_root + "/" + preauthorization_audit_id
```

该 path 仍是 immutable P0 sealed bundle；同一 observation 重试只能验证已有 bundle，禁止覆盖。授权文件随后变为合格时，正式 run
写入尚未创建的 canonical output root，不受既有 preauthorization audit 阻断。若 authorization 已 pass 后再因 upstream/hash/compute
问题形成 P0-P4，则该 version 已被消费；修复 material input 或 contract 后必须升级 version，不能覆盖失败证据。

工作目录固定为：

```bash
cd topics/02_AFML_BIG_WINNER
```

Runner 只允许四个 stage：

```text
preflight
materialize-labels
train-baselines
finalize
```

- `preflight`：只验证 21A successor、执行授权、dependency lock、上游 artifact hash、允许日期和 holdout firewall；不得读取 qfq bar
  value、feature cache value 或任何 label；
- `materialize-labels`：先以 byte-integrity-only 方式核对 live qfq/cache/source hashes；通过后只为 train/validation 的预冻结
  `U_t_decision` 解析 source return/label，生成逐样本 sequence index、`return+label` memmap、label-resolution audit 和 composite
  model-input-panel manifest；
- `train-baselines`：controller 必须依次启动两个不共享进程状态的 child workers。`selection-worker` 只读 train +
  `validation_early`，运行 13 个 jobs并写 provisional candidates；它成功退出后 controller 才能密封 pre-gate bundle。
  `gate-readout-worker` 是 fresh inference-only process，只在 seal 后读取 `validation_late` 并生成 score/readout；不得导入或调用 fit、
  optimizer、backward、boosting continuation；
- `finalize`：只读本 run 已密封的 artifacts，计算 validation readout、gates、decision、中文报告和 output hashes；不得重训；
- stage 不得隐式执行 `pip install`、`uv add`、`uv lock`、`uv sync`；环境 bootstrap 只能在 stage 外显式执行；
- 同一 canonical `run_id + requirement_version` 的 sealed stage 不得覆盖；同一 preauthorization audit path 也不得覆盖。Material input 或
  requirement 改变必须升级版本并保留旧 bundle。

## 2. 授权、前置条件与 claim boundary

### 2.1 生成授权与执行授权分离

```text
requirement_generation_authority = workspace_user_request_2026-07-13
requirement_generation_authorized = true
requirement_execution_authorized = false
historical_holdout_readout_authorized = false
21c_requirement_generation_authorized = false_before_21b_gate
21c_execution_authorized = false
policy_training_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

`references/21b/execution_authorization.json` 必须由后续人类批准动作生成，schema 固定为：

```json
{
  "requirement_sha256": "<exact sha256>",
  "approved_21a_contract_version": "<successful successor version>",
  "approved_21a_freeze_bundle_hash": "<exact sha256>",
  "approved_21a_decision_sha256": "<exact sha256>",
  "reviewer_role": "human",
  "reviewed_at_utc": "<RFC3339 UTC>",
  "authorization_status": "approved"
}
```

字段集合必须 exact-match；hash 或 version 不一致时授权失效。Runner 不得自行生成或修改该文件。

### 2.2 合格 21A successor

Config 必须显式提供并 exact-match Section 0 已冻结的值：

```text
approved_21a_output_root
approved_21a_contract_version
approved_21a_freeze_bundle_hash
approved_21a_decision_sha256
approved_21a_manifest_sha256
approved_21a_output_hashes_sha256
approved_feature_cache_content_hash
approved_feature_expression_sha256
approved_split_hash
approved_normalization_contract_hash
```

所有值必须是 non-empty 64-hex SHA256 或明确 version。禁止使用 `latest`、glob-first、mtime-newest、任意 hash 接受或从当前目录
自动猜测 successor。合格 successor 必须：

1. final manifest 与 output hashes 双向文件集验证通过；
2. freeze manifest/hash JSON canonical 且全部 artifacts 可复算；
3. decision 唯一一行，state 为 `21A_preoutcome_architecture_contract_ready`；
4. 28 个 critical gates 全部 pass，142 个 checks 全部 pass；
5. `next_allowed_requirement` 与本文件名一致；
6. `outcome_model_training_authorized=false`，证明 21A 本身未训练 outcome model；
7. primary feature route、cache hash、split hash、normalizer hash 与 21B config exact-match；
8. current blocked `21A_v1` 的上述 freeze hash 必须列入 explicit denylist。

### 2.3 允许声明

通过 21B 最多允许声明：

```text
validation_baseline_information_supported_under_frozen_project_adaptation
```

不得声明：

```text
historical_out_of_sample_support
Alpha158_exact_replication
paper_result_reproduced
Koopman_supported
diffusion_supported
REAKA_profitable
executable_strategy
production_ready
```

若 baseline gate 失败，只能声明“预冻结 config 下的 validation baseline information 不受支持”，不能推广为“Alpha158 永久无效”或
“所有非线性模型均无效”。

## 3. 输入白名单与访问防火墙

### 3.1 Preflight-only 输入

```text
research_plan.md
requirement_21b_alpha158_sequence_baseline_benchmark.md
config_21b_alpha158_sequence_baseline_benchmark.yaml
references/21b/execution_authorization.json
approved 21A final manifest/output hashes/decision
approved 21A freeze manifest/output hashes/contract_freeze_21a.json
approved 21A feature_cache_manifest.json
approved 21A feature_sequence_support_audit.csv
approved 21A model_arm_registry.csv
approved 21A per_arm_loss_and_score_index_contract.csv
approved 21A tensor_shape_contract.csv
approved 21A train_teacher_inference_graph_contract.csv
approved 21A split_purge_embargo_freeze.csv
approved 21A seed_and_randomness_freeze.csv
approved 21A hyperparameter_and_search_budget_freeze.csv
approved 21A metric_margin_power_freeze.csv
approved 21A label_semantics_freeze.csv
approved 21A decision_universe_and_label_resolution_contract.csv
approved 21A feature_normalization_and_missingness_contract.csv
pyproject.toml
requirements.txt
uv.lock
locked runtime package metadata
```

### 3.2 Materialization-only 输入

Preflight seal 通过后只允许：

```text
approved feature-only cache root
data/processed/universe/pit_topn_400_100_membership_daily.csv
data/raw/akshare/day/qfq/
data/raw/akshare/status/trading_calendar.csv
data/raw/akshare/status/instrument_metadata_target_universe.csv
data/raw/akshare/status/sh_name_history/
```

禁止读取 raw money/volume、benchmark、executable universe、EP19/EP20 outcome outputs、论文 PDF、互联网或任何
historical-design-holdout label/score artifact。

`train-baselines` 不得再次读取 raw qfq、calendar、metadata、name history 或 membership CSV。其唯一数值输入是已密封的 composite
model-input panel：批准的 feature-only cache、`sequence_sample_index.parquet`、三个 fold-isolated
`panels/<fold>/return_and_label_panel.f32.memmap` 和 `model_input_panel_manifest.json`。Runner 必须按 manifest 中的 exact path、
shape、dtype、byte size 与 SHA256 打开这些组件；不能按 glob、mtime 或目录顺序发现输入。

### 3.3 日期防火墙

允许 outcome 日期只来自合格 21A successor 的 effective split：

```text
train decision dates:      2018-01-02 .. 2022-12-14
validation decision dates: 2023-01-03 .. 2023-12-13
validation_early:           eligible dates <= 2023-06-30
validation_late:            eligible dates > 2023-06-30
```

上述日期是 21A_v2 已冻结的 semantic expectation；21B 必须以 successful successor artifact 为唯一机器真值。
若 successor 的 train/validation effective bounds 不一致，21B preflight fail，而不是自动接受新日期。

允许读取 outcome value 的最大 source date 必须由 successor effective validation end 经交易日历机械推导，并 exact-match：

```text
max_validation_decision_date = 2023-12-13
max_allowed_outcome_source_date = next_session(2023-12-13) = 2023-12-14
```

以下访问一律禁止：

```text
decision_date >= 2024-01-02 的 label、score-outcome join 或 metric
source_date > 2023-12-14 的 qfq close/return value decode、join、summary 或 materialization
historical_design_holdout summary/readout
t+2 Qlib-gap diagnostic label
next-open executable label
portfolio outcome
```

由于 qfq CSV 按 instrument 存放且单文件可能跨越 train、validation 与 holdout，访问语义固定如下：

- `byte_integrity_hash`：只顺序读取 raw bytes 计算 SHA256，不解码 CSV 字段；不计为 outcome access，但必须单独计数；
- `routing_date_only`：流式读取时只解析 date token 以决定是否停止；不得解码同一行 close/OHLC value；
- `outcome_value_row`：任何 qfq value column 被解码、进入内存、参与 return/label/join/summary 即计一次 semantic outcome row read；
- qfq permitted prefix 在流式 routing 中必须严格日期升序；在首次 `date > max_allowed_outcome_source_date` 的 routing-only 行立即
  停止，禁止解码该行及之后的 value columns；不得用一次性全文件 DataFrame parse 后再 filter；
- `historical_holdout_zero_access_gate` 约束的是 `outcome_value_row`、label、score-outcome join 和 metric count 全为 0；允许非零的
  byte-integrity 与 routing-only count 不能被写成 outcome read，也不能掩盖 value decode。

每次文件/partition read 必须记录：

```text
access_seq,stage,phase,path_or_resource,dataset_role,access_kind,requested_columns,
parsed_value_columns,date_min,date_max,max_allowed_source_date,content_sha256,allowed,status,purpose
```

`date_min/date_max` 对 `byte_integrity_hash` 固定为 `NA`；`parsed_value_columns` 对 byte/routing-only 访问固定为 `NA`。任何 forbidden
read 发生时，当前 run 失去 21B 资格，只能废弃并升级 version 重跑。

## 4. Frozen feature、universe 与 sequence contract

### 4.1 Primary feature route

21B 继承成功 21A successor 的唯一 primary route，预期为：

```text
feature_route_id = ALPHA158_NO_VWAP_REGISTERED_ADAPTATION
feature_count = 157
feature_expression_sha256 = successor-frozen exact hash
feature_cache_content_hash = successor-frozen exact hash
cache_role = feature_only_coverage_cache
label_columns_present = false
```

不得补造 VWAP feature，不得把 157 features 写成 Alpha158-158 exact materialization，不得重新拟合或修改 cache。21B 必须验证：

- cache file-set、byte sizes、row-key order 和 content hash；
- key 唯一且排序为 `instrument,feature_date`；
- normalization 只由 original train 拟合；
- center=`median`，scale=`IQR/1.349`，scale floor=`1e-12`，clip=`[-10,10]`；
- invalid fill=`train_median`，constant column output=`0`，missing indicator 不直接输入；
- 全部输出为 finite float32；
- feature cache 不含 label/outcome columns。

### 4.2 Decision universe

```text
U_t_decision = PIT membership at close t
               AND listed
               AND non-ST
               AND usable_trade_date is exactly next exchange session
               AND history_ready_240d_flag
               AND T=10 source rows ready
               AND feature warm-up/normalization ready
```

`U_t_decision` 必须直接继承 21A successor 的 `feature_sequence_support_audit.csv`，不得因 label、score、模型或 next-bar availability
逐股缩小。每天至少 100 rows；全部 arms 必须对同一日完整 denominator 出 score。

### 4.3 Sequence tensors

对每个 `(instrument, decision_date=t)`：

```text
source_dates = last 10 exchange sessions ending at t
x_source     = normalized feature rows [T=10,F=157]
y_source     = raw one-step qfq close returns [T=10,1]
forecast_y   = Y_rank_primary_raw(t)
```

不得把停牌缺交易日静默当成零 return。只允许使用 successor 的 suspension/missing policy。不得使用 `t+1` feature 或 return 作为
source input；21B 五个 arms 均不需要 target-only teacher branch。

M1 只使用 `x_source[-1,:]`；M2 使用完整 `y_source`；M3/A0 使用完整 `x_source,y_source`；M0 不读取 feature 或 return value，
只读取 row key。

### 4.4 Sealed composite model-input panel

`materialize-labels` 必须实际生成训练可读的数据组件，不能只写 lineage manifest。Composite panel 固定由以下四部分组成：

```text
approved feature cache/normalized_features.f32.memmap             # immutable [cache_row_n,157]
approved feature cache/keys.csv                                   # immutable row-index truth
materialized/sequence_sample_index.parquet                        # one row per retained decision sample
materialized/panels/<fold>/return_and_label_panel.f32.memmap      # [fold_sample_n,11]
```

三个 `<fold>` 必须 exact 为 `train|validation_early|validation_late`，各 panel 的列顺序 exact 为：

```text
[y_source(t-9),...,y_source(t),forecast_y(t+1)]
```

其 dtype 固定 little-endian float32；所有 value 必须 finite。`sequence_sample_index` 通过 10 个 exact cache row offsets 组装
`x_source`，并用同一行的 `fold_panel_row_idx` 在该行 `fold` 对应的 panel 中组装 `y_source/forecast_y`。任何 offset 越界、source
date 不匹配、row-key
不唯一、panel row 不连续或 hash 不一致均使 materialization fail；训练不得回退到 raw input。

三个 panel 必须物理分离，不能是同一 memmap 的 views/slices/symlinks。Materialization 完成后 worker 退出；新的 training selection
process 在 pre-gate seal 前的 whitelist 只允许打开 `train` 与 `validation_early` panel，访问 wrapper 对 late path 的 open/mmap
attempt 必须 fail closed 并记审计；含 `label_value` 的 label-resolution audit 同样禁止 selection process 打开。只有 whole-day
evaluable 的完整日期进入 panel；所有未进入 panel 的 `U_t_decision` rows 必须仍在
label-resolution audit 中按 whole day 记录，禁止逐股删除。`model_input_panel_manifest.json` 必须密封上述 component hash、shape、
dtype、column semantics、row-key hash、offset contract、process-phase whitelist 和访问上限。

## 5. Label materialization 与 denominator resolution

Primary label 唯一为：

```text
Y_rank_primary(t) = qfq_close(t+1) / qfq_close(t) - 1
```

这是 representation label，不是 executable PnL。Label outcome resolution 必须逐行映射：

| status_id | valuation | day action |
|---|---|---|
| `NORMAL_NEXT_SESSION_CLOSE` | observed next-session qfq close | retain full day |
| `LISTED_SUSPENDED_CARRY` | carry close(t), return=0 | retain full day |
| `CONFIRMED_TERMINAL_PRICE` | audited official terminal/settlement price | retain full day |
| `UNKNOWN_DATA_GAP` | none | whole day not evaluable |
| `RIGHT_CENSORED_DATA_CUTOFF` | none | whole day not evaluable |

规则：

1. `U_t_decision_n` 在 outcome read 前固定；
2. `U_t_resolved_n` 必须等于 `U_t_decision_n`，否则整日不进入 loss/evaluation；
3. 禁止按各 arm 的 score/label intersection 形成 denominator；
4. label 解析失败不得逐股 drop；
5. train/validation 每个 whole-day exclusion 必须记录原因和全部 row keys；
6. 任何 outcome row 的 session 必须严格等于 calendar 的 `next_session(t)`；
7. train label 只可用于 fit；`validation_early` label 只可用于 checkpoint/round selection；materialization worker 可写入但不得报告
   late summary，training process 只能在 pre-gate checkpoint bundle 密封后打开 `validation_late` panel并用于 baseline gate；
   `validation_full` 只作事后 diagnostic；
8. 禁止物化 `Y_qlib_gap_diagnostic` 和 `Y_exec_1d`。

## 6. Mandatory arm contract

### 6.1 Shared training settings

```text
precision = fp32
AMP = false
device = CUDA RTX 4070 SUPER
batch_size = 256
optimizer = AdamW
learning_rate = 1e-3
weight_decay = 1e-5
gradient_clip_norm = 1.0
max_epochs = 100
early_stopping_patience = 10
early_stopping_min_delta = 0.0
early_stopping_metric = validation_early_mean_daily_RankIC
provisional_candidate_selection_fold = validation_early
baseline_gate_fold = validation_late
checkpoint_tie_break = earliest_epoch
latent_dim = 64
lstm_layers = 1
lstm_dropout = 0.0
model_seeds = [20260713,20260714,20260715]
seed_ensemble = arithmetic_mean_of_three_seed_scores
best_seed_primary_allowed = false
```

M1 使用其独立 frozen LightGBM config。M2/M3/A0 必须共享 optimizer、batch、epoch/patience、seed 和 direct-head training budget。
不允许 learning-rate search、hidden-dim search、feature sensitivity、target normalization 或 failed-primary replacement。

Planned jobs 必须 exact 为 13：

```text
M0: 1 deterministic hash job
M1: 3 model-seed jobs
M2: 3 model-seed jobs
M3: 3 model-seed jobs
A0: 3 model-seed jobs
```

OOM 只允许沿 21A ladder `256->128->64->32->16` 机械减 batch，并对 M2/M3/A0 一致应用；低于 16、修改 architecture 或
切 CPU 均为 compute failure。M1 `num_threads=1`。

### 6.2 M0_HASH_NULL_SCORE

```text
canonical_key = "M0_HASH_NULL_SCORE|" + canonical_instrument + "|" + YYYY-MM-DD(decision_date)
u64 = unsigned_big_endian_integer(SHA256(UTF8(canonical_key))[0:8])
score = u64 / 2^64
```

该映射必须与 21A_v2 frozen contract exact-match。Score 必须 row-order、batch、process 和平台不变，不得读取 outcome、feature value
或 return value。M0 只做 pipeline/null sanity，不计入 baseline information gate。

### 6.3 M1_LIGHTGBM_ALPHA158

Input 为 `[B,157] = x_source[:,-1,:]`。Frozen config：

```text
objective = regression_l2
learning_rate = 0.05
num_leaves = 31
max_depth = -1
min_data_in_leaf = 20
feature_fraction = 1.0
bagging_fraction = 1.0
lambda_l1 = 0.0
lambda_l2 = 0.0
max_boosting_rounds = 100
early_stopping_rounds = 10
deterministic = true
force_col_wise = true
num_threads = 1
verbosity = -1
seed|bagging_seed|feature_fraction_seed|data_random_seed = current_model_seed
resolved_bin_construct_sample_cnt = 200000
resolved_max_bin = 255
```

每轮 checkpoint metric 只使用 `validation_early` daily RankIC 的等权日均值，不得用 stock-row MSE 或 `validation_late/full`
选择 checkpoint。若 LightGBM callback 不能安全实现该 metric，必须预先训练全部 100 rounds、逐 round 生成
`validation_early` score，再以相同 tie-break 离线选择；所有 rounds 计入 data-pass accounting。

`resolved_bin_construct_sample_cnt/max_bin` 是 LightGBM 4.6.0 的锁定默认值，只显式记录 resolved runtime，不是新 search knob。
由于实际 train rows 可超过 200,000，`data_random_seed=current_model_seed` 会影响 bin-construction row sample；因此三个 M1 jobs 是
**三个真实 seeded runs**，不得要求跨 seed 的 selected round、tree 或 prediction 完全相同。同一 seed、同一输入、同一 runtime 重跑必须
exact deterministic；跨 seed 允许不同，并与 M2/M3 一样使用 `positive_late_seed_n>=2/3` 和三-seed arithmetic ensemble。

每个 M1 seed job 必须从同一 canonical train row order 独立构造 LightGBM Dataset，并把当前 `data_random_seed`、resolved
`bin_construct_sample_cnt=200000`、`max_bin=255` 传入 Dataset construction；禁止跨 seed 复用首个 seed 已完成 binning 的 Dataset、
reference Dataset 或 shared binary Dataset。Dataset construction hash/row-key hash 必须写入 checkpoint record。

### 6.4 M2_RETURN_LSTM

```text
H_y = LSTM_y(y_source)                      # [B,T,64]
score = Linear(H_y[:,-1,:])                 # [B]
L_M2 = MeanBatch((score - forecast_y)^2)
```

只允许一个单层 unidirectional LSTM；禁止 feature input、bidirectional、attention、teacher forcing 或 future sequence。

### 6.5 M3_GATED_DUAL_PATH_LSTM

```text
H_y = LSTM_y(y_source)                    # [B,T,64]
H_x = LSTM_x(x_source)                    # [B,T,64]
G   = sigmoid(Linear_64_to_64(H_x))        # [B,T,64]
Z   = H_y * G + H_x * (1-G)               # [B,T,64]
score = Linear(Z[:,-1,:])                 # [B]
L_M3 = MeanBatch((score - forecast_y)^2)
```

GateNet 固定为单 affine + sigmoid，逐时点应用。禁止把 teacher/label 输入 GateNet，禁止 concat 替代 elementwise fusion，禁止隐式
broadcast。M3 是 21C/21F 的预冻结 direct-sequence comparator；不得因 validation 表现选择其他 comparator。

### 6.6 A0_VANILLA_AUTOENCODER

A0 与 M3 使用相同 dual encoder、GateNet 和 `Z`，增加共享 scalar return decoder：

```text
decoded_source = Linear_64_to_1(Z).squeeze(-1)          # [B,T]
score = Linear_64_to_1_direct(Z[:,-1,:]).squeeze(-1)   # [B]
L_source_rec = MeanValid((decoded_source-y_source.squeeze(-1))^2)
L_forecast_direct = MeanBatch((score-forecast_y)^2)
L_A0 = L_source_rec + L_forecast_direct
```

Decoder 与 direct score head 参数不共享。A0 不得构造 shifted teacher branch、Koopman operator 或 residual。A0 只作 vanilla-AE
diagnostic，不计入 baseline information gate。

### 6.7 Parameter initialization 与 determinism

所有 PyTorch arm 必须在 CPU 上完成构造和下述显式 re-initialization，再迁移到 CUDA；不得保留 constructor default initialization。
每个 `(arm_id,model_seed)` 创建独立 CPU `torch.Generator` 并以 `weight_init_seed=model_seed+53` 初始化。Module 初始化顺序 exact 为：

```text
M2: lstm_y -> score_head
M3: lstm_y -> lstm_x -> gate_linear -> score_head
A0: lstm_y -> lstm_x -> gate_linear -> source_decoder -> score_head
```

每个 LSTM 固定 `hidden_size=64,num_layers=1,bidirectional=false,proj_size=0,bias=true`，PyTorch gate order 固定为
`input|forget|cell|output`。其 tensor 初始化 exact 为：

```text
weight_ih_l0[0:4H,:]       = Xavier uniform(gain=1.0, generator=weight_init_generator)  # one full tensor draw
weight_hh_l0[gH:(g+1)H,:]  = orthogonal(gain=1.0, generator=weight_init_generator)      # g=0,1,2,3 in order
bias_ih_l0[:]              = 0
bias_hh_l0[:]              = 0
bias_ih_l0[H:2H]           = 1.0                                                        # forget gate only
bias_hh_l0[H:2H]           = 0.0                                                        # remains zero
```

因此 effective forget bias exact 为 1.0，不允许同时把 `bias_ih` 与 `bias_hh` 的 forget slice 设为 1。每个 Linear 按上述 module
顺序执行 `weight=Xavier uniform(gain=1.0,same generator stream)`、`bias=0`。任何额外 trainable parameter、不同 module traversal、整块
`weight_hh_l0` 一次性 orthogonal 或 CUDA generator 初始化均使 `seed_determinism_gate=fail`。Resolved config、checkpoint manifest 和
synthetic fixture 必须共同绑定 `parameter_initialization_contract_sha256`。

Seed streams 必须继承 21A：python/model seed、numpy=`seed+11`、torch=`seed+23`、dataloader=`seed+37`、
weight-init=`seed+53`。Dataloader 只在 train shuffle；validation 排序固定 `decision_date,instrument`。同一 checkpoint 重复 inference
的 score max-abs delta 必须为 0；batch reorder 后按 row key 重排的 delta 必须为 0。

21B 必须在创建 CUDA context 或 model 前 exact 继承并验证 21A deterministic runtime：

```text
CUBLAS_WORKSPACE_CONFIG = :4096:8
torch.use_deterministic_algorithms(True)
torch.set_deterministic_debug_mode("error")
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
```

Runtime audit 必须记录 observed values、CUDA/cuDNN/driver/device 和 known nondeterministic ops；任一 flag 不一致或 required op 抛出
nondeterministic error 时 `seed_determinism_gate=fail`，不得降为 warning。PyTorch same-seed full retrain 的 canonical model-state、
selected candidate 和 score semantic hashes 必须在 small synthetic acceptance fixture 中 exact；LightGBM 同样只要求 synthetic fixture
内的**同一** model seed 重跑 exact，不要求跨 seed identical。上述 deterministic duplicate 是 test fixture，不计入 13 个 production jobs；
production 只要求同一 sealed candidate 重复/重排 inference exact。

## 7. Training、checkpoint 与 search accounting

### 7.1 Training-only fit

- Feature normalizer 不在 21B 重拟合；
- model fit 只使用 effective train rows/labels；
- `validation_early` 只用于 provisional candidate epoch/round early stopping；在 pre-gate checkpoint bundle 密封前，selection worker 不得打开
  `validation_late` 的 label column、score-outcome join 或 metric；
- selection worker 必须先正常退出；controller 验证其 exit record、checkpoint bytes 和 early scores 后才可密封 pre-gate bundle；
- pre-gate bundle 密封后才允许 fresh gate-readout worker 一次性读取 `validation_late` 做 eligibility/futility readout；任何重训、
  继续 boosting、恢复 optimizer、修改 candidate checkpoint 或重新启动 selection worker 都使 run 作废；
- `validation_full` 只能由已密封 checkpoint 的 early+late readout 合成，且为 diagnostic-only；
- historical holdout 不得用于 fit、checkpoint、threshold 或 report；
- deep-arm epoch loss 以 sample 等权，最后不足 batch 不丢弃；
- every epoch/round 必须记录 train loss、`validation_early` mean RankIC、coverage、elapsed time、peak GPU memory 和 data passes；
- NaN/Inf、zero-row batch、missing-score day 立即 fail closed，不得跳过后继续。

### 7.2 Provisional candidate、process boundary 与 checkpoint eligibility

每个 `(arm_id,model_seed)` 只用 `validation_early` mean daily RankIC 选择最大 provisional candidate；tie 取最早 epoch/round。该动作
不是 21A 所称的 full-validation-eligible checkpoint selection。Primary arm score 为三个已密封 seed candidates 的等权 score 均值，
不得选 best seed。Candidate 写入临时目录后，其 manifest record 必须包含：

```text
arm_id
model_seed
config_sha256
feature_cache_content_hash
split_hash
normalization_contract_hash
train_row_key_hash
validation_early_row_key_hash
selection_fold
provisional_selected_epoch_or_round
validation_early_metric_at_selection
parameter_count
complexity_definition
model_specific_complexity
model_input_construction_sha256
parameter_initialization_contract_sha256
checkpoint_path
model_type
serialization_format
serialization_version
checkpoint_sha256
model_state_semantic_sha256
runtime_fingerprint_sha256
```

`selection_fold` 必须恒等于 `validation_early`。Selection worker 还必须输出只含 early rows 的
`selection/validation_early_prediction_scores.parquet`，随后终止；controller 不得与该 worker 共享 Python interpreter、model、optimizer
或 LightGBM Booster object。所有 12 learned candidates 完成并验证后，必须先密封 `pre_gate_checkpoint_bundle_manifest.json`；该
manifest 绑定 checkpoint、config、train/early row hashes、early scores 与 selection-worker exit record，并记录：

```text
selection_process_validation_late_panel_open_count_before_seal = 0
selection_process_label_resolution_audit_open_count_before_seal = 0
validation_late_score_outcome_join_count_before_seal = 0
selection_worker_exit_code = 0
selection_worker_terminated_before_seal = true
pre_gate_sealed_after_worker_exit = true
```

只有 pre-gate bundle hash 验证通过，controller 才能启动 fresh `gate-readout-worker`。该 worker 的 filesystem whitelist 只允许 feature
cache、sequence index、late panel、pre-gate manifest 和已密封 checkpoint；Python import/call guard 必须拒绝 optimizer、autograd
backward、LightGBM train/update 及 runner 的 selection entrypoint。Worker 只输出
`readout/validation_late_prediction_scores.parquet` 后终止；controller 验证 exit code、forbidden-call count 与 score hash 后写入
`gate_readout_worker_exit_record.json`。

Controller 随后合并 early/late score 并逐 `(arm_id,model_seed)` 计算 full/early/late complete metric days，生成不可变
`checkpoint_eligibility_manifest.json`：

```text
candidate_status_before_late = provisional_pending_full_coverage
eligible_checkpoint iff full>=200 AND early>=80 AND late>=80
eligible status = eligible_frozen
otherwise status = provisional_not_evaluable
```

只有 `eligible_frozen` 才是本 requirement 和 21A 语义下的 selected checkpoint；`provisional_not_evaluable` 不得进入 baseline gate，
不得被称为 selected/eligible checkpoint。全部 eligibility、scores/readouts 完成后再密封
`pre_holdout_checkpoint_bundle_manifest.json`。21B 本身仍不得解封 historical holdout。

### 7.3 Search accounting

`model_search_accounting_manifest.csv` 必须预先写入 13 个 planned jobs；每个 job 最终状态只能是：

```text
completed
early_stopped
oom_mechanical_batch_retry
failed_nan_inf
failed_runtime
not_run_due_upstream_block
```

每次 batch retry 是原 job 的 attempt，不增加可选择 config；attempt 全部保留。计划外 config/job 出现时 search-budget gate 失败。

## 8. Score、RankIC 与 stability readout

### 8.1 Score table

每个 mandatory arm 必须对每个可评价 validation `U_t_decision` row 输出：

```text
run_id,requirement_version,split,fold,decision_date,instrument,
arm_id,score_role,model_seed,score,U_t_decision_n,row_key_hash,
feature_route_id,checkpoint_sha256,checkpoint_bundle_sha256
```

Null semantics exact 为：

| `score_role` | `model_seed` | `checkpoint_sha256` | `checkpoint_bundle_sha256` |
|---|---:|---|---|
| `seed` | non-null int64 | non-null checkpoint hash | null |
| `ensemble` | null | null | non-null pre-gate bundle hash |
| `null` | null | null | null |

M0 仅输出 `score_role=null`；learned arms 同时保存 3 条 seed scores 与一条 ensemble score。Parquet 使用原生 null，不允许空字符串、
`0`、`ENSEMBLE` 等混合 sentinel；`score` 是唯一 score value column，不得另设 `ensemble_score`。任何 arm/day/score-role 覆盖小于
`U_t_decision_n` 时整日标记 pipeline failure；不得按共同 score intersection 继续算 RankIC。

上述完整 role/coverage contract 适用于 final `daily_prediction_scores.parquet`。为消除 pre-gate hash cycle，内部 precursor 文件固定：

- `selection/validation_early_prediction_scores.parquet` 只含 M1/M2/M3/A0 的 `score_role=seed` rows；每行绑定 individual
  `checkpoint_sha256`，`checkpoint_bundle_sha256=null`；不得包含 ensemble 或 M0；
- pre-gate bundle 密封后，controller 才可从上述三个 seed rows机械计算 early ensemble，并填入已知 pre-gate bundle hash；
- `readout/validation_late_prediction_scores.parquet` 可包含 late seed/ensemble/M0 rows，ensemble 绑定已存在的 pre-gate bundle hash；
- controller 合并 early seed、机械生成的 early ensemble/M0 与 late file，形成 final score table。Pre-gate manifest 只绑定 early
  seed-only precursor，不绑定任何含自身 hash 的 artifact。

### 8.2 RankIC implementation

对完整日：

```text
score_rank = average_rank(score, ascending=true)
label_rank = average_rank(Y_rank_primary, ascending=true)
RankIC_d = float64 Pearson(score_rank,label_rank)
```

若 `N<100`、score/label 非 finite、score constant、label constant 或 `U_t_resolved_n != U_t_decision_n`，当日 RankIC 为
`not_evaluable` 并记录 reason。不能把 undefined 写为 0。

Summary：

```text
mean_daily_RankIC = arithmetic mean across complete days
std_daily_RankIC = sample std, ddof=1
RankICIR = mean/std
positive_day_rate = count(RankIC_d>0)/complete_day_n
```

统计单位是 decision day，不是 stock-day。Continuation gate 只使用 `validation_late` ensemble；validation early/full、seed rows、M0、
Pearson IC、MSE/MAE、top30 label 均为 diagnostics。

### 8.3 Required folds/fragility

必须输出：

```text
validation_full                           # diagnostic_only
validation_early                          # checkpoint_selection_diagnostic
validation_late                           # baseline_gate
calendar_month_full                       # 12 diagnostic months
leave_one_month_out_full                  # 12 diagnostic omissions
calendar_month_late                       # 6 gate months: 2023-07 .. 2023-12
leave_one_month_out_late                  # 6 gate omissions
each model seed
top 1/3 decision days removed
top 1/3 instruments removed
main-board / ChiNext descriptive slices
```

`top 1/3 removed` 只对 `validation_full` 的 learned-arm ensemble 与 M0 null role 计算，不能进入 Section 9.3 gate。对每个
`(arm_id,score_role)`，base day set 是其原始 complete validation-full days，`base_mean` 是这些日 RankIC 的等权均值。Unit-level
contribution exact 定义为：

```text
decision-day unit d:
  removed_mean_d = mean(RankIC on base day set excluding d)
  signed_contribution_d = base_mean - removed_mean_d

instrument unit i:
  remove i from every base day on which it appears
  rerank both score and label within each affected remaining cross-section
  removed_mean_i = equal-day mean of recomputed RankIC over the same base day set
  signed_contribution_i = base_mean - removed_mean_i
```

Instrument hypothetical removal 不重新应用 primary `N>=100` coverage gate；只要 remaining `N>=2` 且 score/label 均非 constant/finite 即可
计算。任一 base day 在 removal 后不满足该 hypothetical evaluability 时，该 instrument unit 标记 `not_evaluable` 且不得进入 top-third
排序，不能静默 drop 该日。对每类 unit：

```text
evaluable_unit_n = count(unit_status == evaluable)
k = ceil(evaluable_unit_n / 3)
selection order = abs(signed_contribution) DESC, signed_contribution DESC, unit_id ASC
selected_in_top_third = first k units
```

Decision-day `unit_id=YYYY-MM-DD`；instrument `unit_id=canonical_instrument`。选出 top third 后必须一次性同时删除全部 selected units并
重新计算最终 diagnostic；禁止逐步删除后重排 selection。Tie 不得依赖 input row order。全部 unit contribution、rank 和 selection flag
写入 `fragility_unit_contribution_audit.csv`；summary 写入 `rankic_stability_and_concentration_audit.csv`，scope exact 为
`top_third_decision_days_removed_full|top_third_instruments_removed_full`。若 `evaluable_unit_n=0` 或 simultaneous removal 后任一 required
base day undefined，summary status=`not_evaluable` 并记录原因；这仍是 diagnostic，不改变 baseline information gate。

## 9. Exact gates

### 9.1 Upstream and firewall gates

```text
upstream_21a_success_gate
execution_authorization_gate
input_hash_gate
dependency_lock_gate
train_validation_date_firewall_gate
historical_holdout_zero_access_gate
```

全部 pass 才能 materialize labels。Current blocked 21A_v1 必须使 `upstream_21a_success_gate=fail` 且在 outcome read 前退出。

### 9.2 Pipeline gates

```text
feature_cache_integrity_gate
materialization_source_hash_gate
model_input_panel_integrity_gate
decision_universe_denominator_gate
label_resolution_gate
split_purge_gate
arm_registry_gate
architecture_shape_gate
loss_and_score_index_gate
seed_determinism_gate
training_completion_gate
pre_gate_checkpoint_bundle_hash_gate
checkpoint_eligibility_gate
checkpoint_bundle_hash_gate
candidate_selection_gate_firewall_gate
score_coverage_gate
rankic_implementation_gate
null_score_sanity_gate
output_manifest_hash_gate
```

除 `output_manifest_hash_gate` 外，上述 gate 都是 decision-phase causal gates，必须进入 decision exact schema 并参与 Section 10
first-match。`output_manifest_hash_gate` 是 seal meta-gate：builder 在 `.building` 中先写固定内容的 pass assertion，再生成 output hashes 与
final manifest，随后从磁盘重新打开完整 bundle 验证 exact profile/file-set/hash；只有验证 pass 才允许 atomic rename 为 sealed root。因此任何
已 sealed profile 的该 gate 必须为 `pass`。若 post-build 验证失败，`.building` 保持未密封并以 non-zero exit 结束，不得生成一个把
`output_manifest_hash_gate=fail` 写入 sealed decision 的自相矛盾 bundle。该 gate 的 evidence row 只能记录固定 selector
`post_build_full_disk_reopen_verification` 和 status，不得嵌入 final-manifest/output-hashes 的 hash value以制造控制文件环。

Exact checks：

1. feature/cache/split/normalizer hashes equal successful 21A successor；live qfq/source roots 必须在任何 outcome-value decode 前以
   byte-integrity hash exact-match successor；
2. every eligible day has `U_t_resolved_n=U_t_decision_n>=100`；
3. validation full/early/late complete days respectively at least `200/80/80`；
4. five mandatory arms exact，planned jobs exact 13，provisional learned candidates exact 12；P5 evaluable baseline 要求 eligibility
   manifest exact 12 records 且全部 `eligible_frozen`；
5. all learned-arm ensemble scores and M0 null-role scores have 100% row coverage on every retained day；
6. finite score/loss/gradient and exact tensor shapes；
7. repeated and reordered inference delta equal 0；
8. M0 exact hash fixture、key-only access lineage、100% coverage 和 reordered inference exact；
9. no historical holdout outcome-value/label/score-join/metric read；
10. artifact file set and every SHA256 bidirectionally verify。

`null_score_sanity_gate` 的 hard checks 只包括上述结构性 M0 条件，以及 deterministic synthetic null fixture：对 `N=100` 的 fixed ranks
枚举全部 100 个 cyclic shifts，mean daily RankIC 的绝对值必须 `<=1e-12`。真实 validation M0 的 stationary-bootstrap 99% two-sided
CI 必须报告，但只作 diagnostic，不能成为随机 hard gate。其参数固定为 10,000 replicates、expected block length=20 decision days、
percentile `[0.5%,99.5%]`、seed=`uint64_prefix(SHA256("21B_v6|M0_REALIZED_CI")) mod 2^63`。CI 不含 0 时标记
`realized_m0_null_diagnostic_warning` 并调查，不能仅凭一次 1% tail event 阻断或通过 pipeline。

### 9.3 Baseline information gate

Eligible non-null baselines 只包括 `M1/M2/M3`。某一 arm 必须同时满足：

```text
learning_pipeline_status = pass
all_three_seed_checkpoint_eligibility_status = eligible_frozen
validation_full_complete_day_n >= 200
validation_early_complete_day_n >= 80
validation_late_complete_day_n >= 80
provisional_candidate_selection_fold = validation_early
baseline_gate_fold = validation_late
validation_early_metric_at_selection is finite
ensemble_mean_RankIC_late > 0
positive_leave_one_late_month_out_n >= 5 of 6
max_late_month_abs_contribution_share <= 0.50
validation_late_ensemble_score_coverage_rate = 1.0
NaN_or_inf_count = 0
```

M1/M2/M3 都必须满足：

```text
positive_late_seed_n >= 2 of 3
```

M1 的三个 seeded runs 因 `data_random_seed` 影响大样本 bin construction，属于 seed-direction evidence；不得压缩成一个副本或要求
跨 seed prediction exact。
`validation_full` point estimate、12-month full LOMO 和 early point estimate 只报告，不得替代 late gate。

其中：

```text
late_month_contribution_m = sum_{d in late month m}(RankIC_d) / validation_late_complete_day_n
max_late_month_abs_contribution_share = max_m(abs(late_month_contribution_m)) /
                                        sum_m(abs(late_month_contribution_m))
```

若分母为 0，arm 不通过。Gate 为：

```text
baseline_information_gate = any(eligible(M1),eligible(M2),eligible(M3))
```

这是 direction/stability futility gate，不做“显著预测能力”声明，不使用 p-value 或 confidence lower bound 替代上述 conjunctive rule。
A0/M0 表现不能单独授权 21C。

## 10. Decision state 与后续授权

Decision 必须按 first-match 顺序产生唯一 `stage_decision`：

```text
1. 21B_blocked_by_21A_or_missing_human_authorization
   -> upstream/authorization gate fail；outcome/model counts 必须为 0。

2. 21B_input_hash_or_holdout_firewall_blocked
   -> hash/date/forbidden access failure；无论发生在 materialization、selection、gate readout 或 finalize，都优先落入 state 2；run 作废，
      不能解释 baseline。

3. 21B_label_or_denominator_pipeline_blocked
   -> model-input panel、label resolution、U_t denominator 或 split/purge contract 不完整；不能解释 baseline。

4. 21B_training_or_compute_not_evaluable
   -> dependency、arm/architecture/loss contract、mandatory jobs、provisional candidates、checkpoint eligibility、determinism、score/RankIC/null
      pipeline 或 GPU 未完成；不能解释 baseline。

5. 21B_baseline_information_not_supported
   -> pipeline evaluable，但 M1/M2/M3 均不通过 Section 9.3；关闭 EP21 complex-architecture mainline。

6. 21B_baseline_information_supported_pending_human_approval
   -> 至少一个 M1/M2/M3 通过；允许生成并评审 21C requirement，不授权执行 21C。
```

Gate-to-state first-match bucket exact 为：

```text
state 1: upstream_21a_success_gate, execution_authorization_gate
state 2: input_hash_gate, train_validation_date_firewall_gate, historical_holdout_zero_access_gate,
         feature_cache_integrity_gate, materialization_source_hash_gate,
         candidate_selection_gate_firewall_gate, or any access_audit.allowed=false
state 3: model_input_panel_integrity_gate, decision_universe_denominator_gate,
         label_resolution_gate, split_purge_gate
state 4: dependency_lock_gate, arm_registry_gate, architecture_shape_gate,
         loss_and_score_index_gate, seed_determinism_gate, training_completion_gate,
         pre_gate_checkpoint_bundle_hash_gate, checkpoint_eligibility_gate,
         checkpoint_bundle_hash_gate, score_coverage_gate, rankic_implementation_gate,
         null_score_sanity_gate
state 5/6: all causal gates pass; baseline_information_gate fail/pass respectively
seal meta-gate: output_manifest_hash_gate must pass and does not create a sealed failure state
```

同一 run 多个 gate fail 时先取最小 state number；同一 bucket 全部 failed gate 仍须进入 canonical `blocking_reasons`，不能只保留首个。

Artifact profile 与 decision state 的允许映射 exact 为：

```text
P0_PREFLIGHT_BLOCKED       -> state 1, 2, 3 or 4 according to failed preflight causal gate
P1_MATERIALIZATION_BLOCKED -> state 2 or 3
P2_SELECTION_BLOCKED       -> state 2 or 4
P3_GATE_READOUT_BLOCKED    -> state 2 or 4
P4_FINALIZE_BLOCKED        -> state 2 or 4
P5_FULL_FINALIZED          -> state 4, 5 or 6
```

Profile 只描述最后完成的 artifact phase，不覆盖 decision precedence。尤其 selection worker 打开 late panel、gate-readout worker 调用 fit、
任一 training/finalize phase 读取 historical holdout，均必须以当时可验证的 P2/P3/P4 artifacts 封存并落 state 2，不能因为失败发生较晚而
降级成 state 4。State 5/6 的前提是除 seal meta-gate 外全部 upstream/firewall/pipeline causal gates pass；任何 causal gate fail 时不得计算或
解释 `baseline_information_gate`。

P5 中任一 provisional candidate 未获 `eligible_frozen` 必须 state 4；不得把完整 artifact file set 误写成 baseline evaluable。

只有 state 6：

```text
next_requirement = requirement_21c_single_vs_adaptive_koopman_nested_ablation.md
next_requirement_generation_authorized = true
next_requirement_execution_authorized = false
```

其他 state 均为 false。所有 state 下：

```text
historical_holdout_readout_authorized = false
policy_training_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

## 11. Required artifacts 与 exact schemas

### 11.1 Stage artifacts

```text
preflight/preflight_access_audit.csv
preflight/upstream_21a_authorization_and_hash_audit.csv
preflight/resolved_config.yaml
materialized/decision_universe_and_label_resolution_audit.parquet
materialized/sequence_sample_index.parquet
materialized/panels/train/return_and_label_panel.f32.memmap
materialized/panels/validation_early/return_and_label_panel.f32.memmap
materialized/panels/validation_late/return_and_label_panel.f32.memmap
materialized/model_input_panel_manifest.json
materialized/materialization_access_audit.csv
materialized/materialization_failure_evidence.csv
training/training_run_registry.csv
training/model_search_accounting_manifest.csv
training/seed_level_training_curves.csv
training/checkpoints/M1_LIGHTGBM_ALPHA158/seed_20260713/model.txt
training/checkpoints/M1_LIGHTGBM_ALPHA158/seed_20260714/model.txt
training/checkpoints/M1_LIGHTGBM_ALPHA158/seed_20260715/model.txt
training/checkpoints/M2_RETURN_LSTM/seed_20260713/state_dict.pt
training/checkpoints/M2_RETURN_LSTM/seed_20260714/state_dict.pt
training/checkpoints/M2_RETURN_LSTM/seed_20260715/state_dict.pt
training/checkpoints/M3_GATED_DUAL_PATH_LSTM/seed_20260713/state_dict.pt
training/checkpoints/M3_GATED_DUAL_PATH_LSTM/seed_20260714/state_dict.pt
training/checkpoints/M3_GATED_DUAL_PATH_LSTM/seed_20260715/state_dict.pt
training/checkpoints/A0_VANILLA_AUTOENCODER/seed_20260713/state_dict.pt
training/checkpoints/A0_VANILLA_AUTOENCODER/seed_20260714/state_dict.pt
training/checkpoints/A0_VANILLA_AUTOENCODER/seed_20260715/state_dict.pt
training/checkpoint_manifest.json
training/selection_worker_exit_record.json
training/selection/validation_early_prediction_scores.parquet
training/pre_gate_checkpoint_bundle_manifest.json
training/readout/validation_late_prediction_scores.parquet
training/gate_readout_worker_exit_record.json
training/checkpoint_eligibility_manifest.json
training/pre_holdout_checkpoint_bundle_manifest.json
training/daily_prediction_scores.parquet
training/model_parameter_compute_latency_audit.csv
training/training_access_audit.csv
historical_design_holdout_access_audit.csv
stage_status_registry.csv
daily_rankic_readout.csv
rankic_stability_and_concentration_audit.csv
fragility_unit_contribution_audit.csv
finalize_failure_evidence.csv
gate_evidence_21b.csv
21B_baseline_benchmark_decision.csv
21B_alpha158_sequence_baseline_benchmark_report.md
semantic_reproducibility_manifest.json
manifest_21b_alpha158_sequence_baseline_benchmark.json
output_hashes_21b_alpha158_sequence_baseline_benchmark.json
```

上述是 superset，不是所有 decision state 的无条件 file set。Final manifest 必须选择且只选择一个 `artifact_profile_id`：

| profile | 触发条件 | required stage artifacts | forbidden sealed artifacts |
|---|---|---|---|
| `P0_PREFLIGHT_BLOCKED` | 任一 preflight causal gate fail | common-final + 三个 preflight artifacts + 13-row search manifest（全 `not_run_due_upstream_block`） | 全部 materialized panel、checkpoint、score/readout |
| `P1_MATERIALIZATION_BLOCKED` | source hash/firewall/label/denominator/materialization fail | P0 required + materialization access audit + materialization failure evidence | sealed panel components、全部 checkpoint、score/readout |
| `P2_SELECTION_BLOCKED` | selection worker/job 未完成或 selection firewall breach | common-final + successful preflight/materialization artifacts + training registry/search/curves/access/compute + 0..12 个 completed candidate files及同数 manifest records | selection exit success record、pre-gate bundle、late score、eligibility、pre-holdout bundle |
| `P3_GATE_READOUT_BLOCKED` | 12 candidates 与 pre-gate seal成功，但 inference-only readout 未完成 | common-final + successful preflight/materialization + 全部 12 candidate files/manifest + selection exit + early score + pre-gate bundle + training audits | sealed late score、eligibility、pre-holdout bundle、combined score |
| `P4_FINALIZE_BLOCKED` | late readout、eligibility、pre-holdout seal 与 combined score 已完成，但 finalize causal gate/readout 失败 | common-final + successful P3 artifacts + gate-readout exit + late score + eligibility + pre-holdout bundle + combined score + finalize failure evidence | daily RankIC、stability/fragility audits、materialization failure evidence |
| `P5_FULL_FINALIZED` | 全部 finalize causal gates/readout 完成，无论最终 information gate pass/fail | Section 11.1 全部 superset，但两个 failure-evidence files forbidden | 无 |

P0 若因 execution authorization 缺失或无效触发，bundle root 必须是 Section 1 的 `preauthorization_audit_path`；其他 P0 及 P1-P5 使用
canonical output root。`successful materialization artifacts` exact 指 Section 11.1 全部 `materialized/` paths但排除
`materialized/materialization_failure_evidence.csv`。上表 `successful P3 artifacts` exact 指 successful preflight/materialization、12 个
checkpoint/files manifest、selection exit、early score、pre-gate bundle 及全部 training audits。P0-P4 禁止 `daily_rankic_readout.csv`、
两个 stability/fragility audit；P5 必须包含三者。

`common-final` exact 为：

```text
historical_design_holdout_access_audit.csv
stage_status_registry.csv
gate_evidence_21b.csv
21B_baseline_benchmark_decision.csv
21B_alpha158_sequence_baseline_benchmark_report.md
semantic_reproducibility_manifest.json
manifest_21b_alpha158_sequence_baseline_benchmark.json
output_hashes_21b_alpha158_sequence_baseline_benchmark.json
```

`P2_SELECTION_BLOCKED` 中 candidate file count 可为 0..12，必须等于 `checkpoint_manifest.json` record count，并等于 registry 中
已完成/early-stopped learned job count；12 个 candidate 但 child exit/firewall check 未通过时仍是 P2，这些 candidate 只作失败证据，
eligibility 恒为未建立。所有 profile 下，未成功 stage 的临时内容只能留在 selected bundle root 之外的
`<selected_bundle_root>.building/<stage>/`，finalize 前必须删除；sealed root 禁止 `.building`、partial memmap 或未列入 profile 的额外文件。

Finalize 必须先验证 training/finalize access audits、historical firewall、score coverage 与输入完整性，再计算 RankIC/stability/fragility；
因此任何 late firewall breach 或 finalize causal failure 都能删除 partial metric files并合法封存为 P4。`output_manifest_hash_gate` 必须针对
selected profile 的 required/forbidden rules 验证 exact file set，不能要求 blocked run 补造成功
artifact 或空 checkpoint。Runner 在任何 stage fail 后只能进入只读 `finalize`，后续未运行 stage 在 `stage_status_registry.csv` 标记
`not_run_due_upstream_block`。

Config/resolved config 必须把上表展开为 ordered `artifact_profiles` records，字段 exact 为
`profile_id,required_paths,forbidden_paths,conditional_path_rules`（profile order P0..P5，path 使用 Section 11.1 exact relative path）。P2
唯一允许的 conditional rule 为 `completed_learned_job_exact_checkpoint_subset`，其 allowed universe 是 12 个 explicit checkpoint paths，
且 cardinality 允许 0..12、record/status reconciliation 使用上文规则；其他 optional file 一律禁止。
`artifact_profile_registry_sha256 = SHA256(canonical_json_bytes(resolved_config.artifact_profiles))`。Final manifest、decision 和 gate evidence
必须绑定该 hash，禁止运行时从现有文件反推/放宽 profile。

### 11.2 Core CSV schemas

所有 CSV 的 missing token 固定为字面量 `NA`，禁止空字符串、`null`、`None`、`0` 或混合 sentinel。M0 job/readout 的
`model_seed` 与 `checkpoint_sha256` 为 `NA`；learned seed row 使用整数 seed；ensemble readout 的 `model_seed` 为 `NA`。

`upstream_21a_authorization_and_hash_audit.csv`：

```text
check_id,artifact_path,expected_value,observed_value,status,blocking_reason
```

Access audit 三表统一：

```text
access_seq,stage,phase,path_or_resource,dataset_role,access_kind,requested_columns,
parsed_value_columns,date_min,date_max,max_allowed_source_date,content_sha256,allowed,status,purpose
```

`materialization_failure_evidence.csv`（仅 P1）：

```text
check_id,evidence_metric,observed_value,required_value,status,blocking_reason
```

禁止包含逐股 outcome values；只允许 source-hash、日期、row/day counts、denominator reconciliation 和 blocking reason。

`stage_status_registry.csv` 必须 exact 7 行并按下列 ordinal 排序：

```text
1 preflight
2 materialize-labels
3 train-baselines.selection-worker
4 train-baselines.pre-gate-seal
5 train-baselines.gate-readout-worker
6 train-baselines.eligibility
7 finalize
```

Schema：

```text
stage_ordinal,stage_or_subphase,attempt_id,bundle_root_class,bundle_root_relative_path,preauthorization_audit_id,
artifact_profile_id,status,worker_exit_code,started_at_utc,ended_at_utc,
sealed_artifact_count,stage_manifest_sha256,blocking_reason
```

Status 只允许 `sealed|blocked|not_run_due_upstream_block`；blocked 后的后续非-finalize rows 必须 `not_run_due_upstream_block`，finalize
仍必须 `sealed`。七行的 root/profile fields 必须相同并与 decision/final/semantic manifests exact-match。非-finalize sealed row 的
`stage_manifest_sha256` 定义为该 subphase produced artifacts 的
`SHA256(canonical_json_bytes({relative_path:full_byte_sha256}))`，path 排序；blocked/not-run row 为 `NA`。为避免 self-reference，
finalize row 的 `stage_manifest_sha256` 固定为 `NA`；final manifest 与 output-hashes 的 cycle-breaking 规则由 Section 11.5 单独验证。

Stage `attempt_id` 固定为 `stage_<stage_ordinal two digits>_attempt_01`；sealed stage 不允许第二次 attempt。Training registry 的
`attempt_id` 固定为 `<job_id>_attempt_<attempt ordinal two digits>`，ordinal 从 01 开始且只允许 OOM ladder 机械递增。不得使用 UUID、PID、
timestamp 或随机 nonce 作为 attempt id，以保证 semantic rerun 可比。

`training_run_registry.csv`：

```text
run_id,requirement_version,arm_id,model_seed,attempt_id,config_sha256,batch_size,
device,started_at_utc,ended_at_utc,provisional_selected_epoch_or_round,job_status,checkpoint_sha256,
train_row_n,validation_early_row_n,validation_late_score_row_n,
train_day_n,validation_early_day_n,validation_late_day_n
```

`model_search_accounting_manifest.csv`：

```text
job_id,arm_id,model_seed,planned,config_id,attempt_count,attempt_batch_sizes,
final_status,promotion_allowed,blocking_reason
```

`seed_level_training_curves.csv`：

```text
arm_id,model_seed,epoch_or_round,train_loss,validation_early_mean_RankIC,
validation_early_complete_day_n,validation_early_score_coverage_rate,elapsed_seconds,
peak_memory_mib,data_pass_n,status
```

`model_parameter_compute_latency_audit.csv`：

```text
arm_id,model_seed,parameter_count,train_seconds,inference_seconds,inference_row_n,
latency_ms_per_1000_rows,peak_cpu_rss_mib,peak_gpu_memory_mib,data_pass_n,status
```

`historical_design_holdout_access_audit.csv`：

```text
scope,date_min,date_max,byte_integrity_read_count,routing_date_only_read_count,
outcome_value_row_read_count,label_read_count,score_outcome_join_count,metric_read_count,
required_outcome_counts_zero,status
```

必须恰好一行 summary；`outcome_value_row_read_count`、`label_read_count`、`score_outcome_join_count`、`metric_read_count` 全为 0。
前两个 lineage/routing count 允许非零但不得与 outcome count 合并。

`daily_rankic_readout.csv`：

```text
arm_id,score_role,model_seed,fold,decision_date,U_t_decision_n,U_t_resolved_n,score_n,label_n,
RankIC,PearsonIC,MSE,MAE,rankic_status,not_evaluable_reason
```

`rankic_stability_and_concentration_audit.csv`：

```text
arm_id,score_role,model_seed,scope,evidence_role,slice_id,complete_day_n,mean_RankIC,
std_RankIC,RankICIR,positive_day_rate,positive_late_seed_n,
positive_lomo_n,lomo_total_n,max_month_abs_contribution_share,score_coverage_rate,status
```

`fragility_unit_contribution_audit.csv`（仅 P5）：

```text
arm_id,score_role,model_seed,fold,unit_type,unit_id,base_complete_day_n,base_mean_RankIC,
removed_complete_day_n,removed_mean_RankIC,signed_contribution,abs_contribution,
selection_rank,selected_in_top_third,unit_status,not_evaluable_reason
```

`unit_type` 只允许 `decision_day|instrument`；`fold=validation_full`；learned rows 只允许 `score_role=ensemble,model_seed=NA`，M0
只允许 `score_role=null,model_seed=NA`。Not-evaluable unit 的四个 removal/contribution/rank 字段为 `NA`，selection flag=false。

`finalize_failure_evidence.csv`（仅 P4）：

```text
check_id,evidence_metric,observed_value,required_value,status,blocking_reason
```

只允许记录 access/firewall、score coverage、RankIC implementation fixture 或 finalize runtime 的聚合 check；禁止逐股 outcome/score/label
value。P5 禁止该文件。

`gate_evidence_21b.csv`：

```text
gate_id,check_id,evidence_artifact,evidence_selector,observed_value,required_value,status,blocking_reason
```

`21B_baseline_benchmark_decision.csv`：

```text
run_id,requirement_version,bundle_root_class,bundle_root_relative_path,preauthorization_audit_id,
artifact_profile_id,artifact_profile_registry_sha256,stage_decision,upstream_21a_success_gate,
execution_authorization_gate,input_hash_gate,dependency_lock_gate,train_validation_date_firewall_gate,
historical_holdout_zero_access_gate,feature_cache_integrity_gate,
materialization_source_hash_gate,model_input_panel_integrity_gate,
decision_universe_denominator_gate,label_resolution_gate,split_purge_gate,arm_registry_gate,
architecture_shape_gate,loss_and_score_index_gate,seed_determinism_gate,
training_completion_gate,pre_gate_checkpoint_bundle_hash_gate,checkpoint_eligibility_gate,checkpoint_bundle_hash_gate,
candidate_selection_gate_firewall_gate,score_coverage_gate,rankic_implementation_gate,
null_score_sanity_gate,output_manifest_hash_gate,baseline_information_gate,eligible_baseline_ids,
best_validation_arm_diagnostic_only,next_requirement,next_requirement_generation_authorized,
next_requirement_execution_authorized,historical_holdout_readout_authorized,
policy_training_authorized,portfolio_optimization_authorized,deployment_authorized,
pre_gate_checkpoint_bundle_hash,pre_holdout_checkpoint_bundle_hash,
semantic_payload_bundle_hash,gate_evidence_sha256,blocking_reasons
```

`bundle_root_class` 只允许 `canonical|preauthorization_audit`；后者只允许 P0/state 1 且 `preauthorization_audit_id` non-null，前者的该字段
必须为 `NA`。Decision 必须显式携带 Section 9 的全部 gate；`output_manifest_hash_gate` 对任何 sealed row 恒为 `pass`。Causal gate status 只允许
`pass|fail|not_run_due_upstream_block`；`baseline_information_gate` 只允许 `pass|fail|not_evaluable`。`eligible_baseline_ids` 按
`M1_LIGHTGBM_ALPHA158|M2_RETURN_LSTM|M3_GATED_DUAL_PATH_LSTM` 固定顺序筛选并以 `|` 连接，无 eligible arm 时为 `NA`。
`blocking_reasons` 是 failed causal `gate_id` 的 canonical JSON array，先按 Section 10 state precedence、同 state 内按 `gate_id ASC`
排序；无 failure 时为 `[]`。`best_validation_arm_diagnostic_only` 只用于描述，不得成为 21C arm/config selector。

### 11.3 Parquet schemas

`decision_universe_and_label_resolution_audit.parquet`：

```text
split,fold,decision_date,instrument,usable_trade_date,U_t_decision,
history_ready,sequence_ready,feature_ready,label_resolution_status,
label_source_date,label_value,U_t_decision_n,U_t_resolved_n,whole_day_evaluable,
whole_day_not_evaluable_reason,row_key_hash
```

`sequence_sample_index.parquet` exact logical schema：

```text
sample_row_idx:int64
split:string
fold:string
decision_date:date32
instrument:string
U_t_decision_n:int32
x_cache_row_indices:fixed_size_list<int64>[10]
source_dates:fixed_size_list<date32>[10]
fold_panel_row_idx:int64
row_key_hash:string
```

`sample_row_idx` 必须在全表从 0 连续递增；`fold_panel_row_idx` 必须在每个 fold 内从 0 连续递增。`x_cache_row_indices` 的 key 必须
逐项等于 `(instrument,source_dates[j])`。`fold` 只允许 `train|validation_early|validation_late`。

三个 prediction-score Parquet 都使用 Section 8.1 exact columns/order，并遵守 Section 8.1 的 precursor role restrictions。Parquet
metadata 必须记录 schema version、row count、min/max date、sort key、content hash；sort key 固定为：

```text
split,decision_date,instrument,arm_id,score_role,model_seed
```

Null sort 固定为 last；`score_role` 顺序固定 `seed,ensemble,null`。

### 11.4 JSON manifests

`model_input_panel_manifest.json` 至少 exact 包含：

```text
schema_version,run_id,requirement_version,approved_21a_contract_version,
approved_21a_freeze_bundle_hash,feature_route_id,feature_count,
feature_expression_sha256,feature_cache_content_hash,normalization_contract_hash,
split_hash,feature_cache_keys_path,feature_cache_keys_sha256,
feature_cache_memmap_path,feature_cache_memmap_sha256,feature_cache_shape,feature_cache_dtype,
sequence_sample_index_path,sequence_sample_index_sha256,sequence_sample_n,sequence_sort_key,
panel_partitions,
train_row_key_hash,validation_early_row_key_hash,validation_late_row_key_hash,
train_row_n,validation_early_row_n,validation_late_row_n,
train_day_n,validation_early_day_n,validation_late_day_n,
label_id,label_materialization_hash,max_allowed_outcome_source_date,
materialization_worker_validation_late_summary_count,
materialization_worker_validation_late_metric_count,
historical_holdout_row_materialized_n,outcome_access_scope,status
```

两个 materialization-worker late readout count 必须为 0；允许写入逐行 late label，但不得在 checkpoint seal 前计算 late label summary、
与任何 score join 或产生 metric。

`panel_partitions` 必须是按 `train,validation_early,validation_late` 排序的 exact 三条 canonical records；每条字段为：

```text
fold,path,sha256,byte_size,shape,dtype,column_semantics,row_key_hash,open_phase_whitelist
```

每条必须验证 `byte_size = shape[0] * 11 * 4`，且三条 `shape[0]` 之和等于 `sequence_sample_n`。Component path 必须为 explicit
relative path，禁止 glob/symlink；late record 的 whitelist 只能是 `post_pre_gate_seal_readout`。

`selection_worker_exit_record.json` 与 `gate_readout_worker_exit_record.json` 必须由 parent controller 在 child process 已退出后写入，
child 不得自报成功。共同 exact schema：

```text
schema_version,worker_mode,process_start_contract,worker_pid,command_argv_sha256,
resolved_config_sha256,started_at_utc,ended_at_utc,exit_code,
filesystem_whitelist_sha256,forbidden_import_or_call_count,
late_panel_open_count,fit_or_update_call_count,
produced_artifact_paths,produced_artifact_hashes,status
```

`process_start_contract=fresh_execve_interpreter`，禁止 `fork` 继承 model/optimizer/Booster state。Selection record 要求
`late_panel_open_count=0`；gate-readout record 要求 `fit_or_update_call_count=0`。两个 record 的 `exit_code=0,status=pass` 才能推进；
controller 必须验证 produced paths/hashes，不能只信 child JSON/stdout。

`checkpoint_manifest.json` 按 `arm_id,model_seed` canonical 排序：P2 必须含 0..12 个已完成 learned provisional candidates，P3/P4/P5
必须 exact 12，P0/P1 禁止存在。每条共有：

```text
arm_id,model_seed,checkpoint_path,model_type,serialization_format,serialization_version,
provisional_selected_epoch_or_round,selection_fold,validation_early_metric_at_selection,
config_sha256,feature_cache_content_hash,split_hash,normalization_contract_hash,
train_row_key_hash,validation_early_row_key_hash,parameter_count,complexity_definition,model_specific_complexity,
model_input_construction_sha256,parameter_initialization_contract_sha256,
checkpoint_sha256,model_state_semantic_sha256,runtime_fingerprint_sha256
```

Model-specific seal：

- M1 `model_type=lightgbm_booster`，`serialization_format=lightgbm_text_model`，
  `serialization_version=lightgbm_4.6.0_text_v1`，使用 LightGBM 4.6.0
  `Booster.save_model(num_iteration=provisional_selected_round)` 写入 exact `model.txt`；full bytes 计算 `checkpoint_sha256`。Semantic state
  使用同一文件 reload 后 `Booster.dump_model(num_iteration=...)` 的完整返回对象加 resolved training params，按 `canonical_json_bytes`
  计算 hash；不得套用 tensor hash。M1 `parameter_count=total_leaf_n`，`complexity_definition=lightgbm_total_leaf_n`，同时在 record 的
  `model_specific_complexity={tree_n,split_n,leaf_n}`；`model_input_construction_sha256` 绑定 Dataset row-key/feature-order hash、
  current seed 和 resolved bin params；`parameter_initialization_contract_sha256=null`；
- M2/M3/A0 `model_type=pytorch_state_dict`，`serialization_format=torch_state_dict_zip`，
  `serialization_version=torch_2.8.0_state_dict_zip_v1`，文件只含 model state_dict，不含 optimizer、dataloader 或 epoch metadata。
  Semantic state 按参数名排序，每个 tensor 转 CPU contiguous little-endian bytes，并串联
  `(name,dtype,shape,raw-bytes)` 后计算 hash；`parameter_count` 是 trainable scalar 总数，
  `complexity_definition=pytorch_trainable_scalar_n`，`model_specific_complexity=null`；`model_input_construction_sha256` 绑定 sequence index、panel hashes、sampler seed、
  batch size 和 drop-last=false；`parameter_initialization_contract_sha256` 必须绑定 Section 6.7 exact contract 的 canonical SHA256。

P3/P4/P5 manifest 中的 12 个 `checkpoint_path` 必须与 Section 11.1 的 12 个 explicit relative paths exact-match；P2 必须是这些路径的
completed-job exact subset。禁止 glob、symlink、额外 checkpoint 或 best-seed alias。

`checkpoint_eligibility_manifest.json` 必须按 `arm_id,model_seed` exact 12 条记录：

```text
arm_id,model_seed,checkpoint_sha256,candidate_status_before_late,
validation_full_complete_day_n,validation_early_complete_day_n,validation_late_complete_day_n,
checkpoint_eligibility_status,eligibility_blocking_reason
```

`pre_gate_checkpoint_bundle_manifest.json` 绑定全部 provisional candidates、config、feature/split/normalizer hashes、train/early row
hashes、early scores、selection-worker exit record 以及 selection-process late-panel-before-seal zero-open counters；
`pre_holdout_checkpoint_bundle_manifest.json` 再绑定 pre-gate bundle、gate-readout-worker exit record、eligibility manifest、全部
scores/readouts 与
`historical_holdout outcome/label/join/metric count=0`。

### 11.5 Byte seal 与 semantic reproducibility

完整 seal 与可复现性是两个不同 hash domain：

- `output_hashes_*.json` 对除自身及 final manifest 外的每个 artifact 计算**完整 bytes SHA256**，包括时间、latency 和 memory；
- final manifest 记录 exact root file set 与 `output_hashes_*.json` 的 SHA256；验证时 file-set 必须与
  `artifact hashes + final manifest + output hashes` 的并集 exact-match；final manifest self-hash 不在 bundle 内自引用；
- `semantic_reproducibility_manifest.json` 按下述无环 DAG 对确定性字段、模型 tensor、score/readout 做 canonical hash；不能拿
  full-byte bundle hash 作为“两次运行必须相同”的断言。

Final manifest 还必须记录 `bundle_root_class,bundle_root_relative_path,preauthorization_audit_id`、`artifact_profile_id`、profile
required/forbidden registry hash 和 selected profile 验证结果；root fields/profile id 必须与 decision、semantic manifest、stage status
exact-match。

Semantic seal 生成顺序和 hash domain exact 为：

```text
control_paths = {
  gate_evidence_21b.csv,
  21B_baseline_benchmark_decision.csv,
  21B_alpha158_sequence_baseline_benchmark_report.md,
  semantic_reproducibility_manifest.json,
  manifest_21b_alpha158_sequence_baseline_benchmark.json,
  output_hashes_21b_alpha158_sequence_baseline_benchmark.json
}

semantic_payload_paths = selected_profile_required_paths - control_paths
semantic_payload_artifact_hashes = semantic hashes of semantic_payload_paths, keyed by relative path ASC
semantic_payload_bundle_hash = SHA256(canonical_json_bytes({
  canonicalization_version,
  artifact_profile_id,
  semantic_payload_artifact_hashes,
  model_state_semantic_hashes
}))

# Only after payload hash is frozen:
write gate evidence
write decision embedding semantic_payload_bundle_hash
write report; report may embed semantic_payload_bundle_hash

semantic_artifact_paths = selected_profile_required_paths - {
  semantic_reproducibility_manifest.json,
  manifest_21b_alpha158_sequence_baseline_benchmark.json,
  output_hashes_21b_alpha158_sequence_baseline_benchmark.json
}
semantic_artifact_hashes = semantic hashes of semantic_artifact_paths, keyed by relative path ASC
semantic_bundle_hash = SHA256(canonical_json_bytes({
  canonicalization_version,
  artifact_profile_id,
  semantic_payload_bundle_hash,
  semantic_artifact_hashes,
  model_state_semantic_hashes
}))
```

因此 decision、gate evidence 和 report 全部受顶层 `semantic_bundle_hash` 保护，但它们只允许嵌入 payload hash，禁止嵌入顶层
`semantic_bundle_hash`。顶层 hash 只写入 `semantic_reproducibility_manifest.json` 和被 semantic domain 排除的 final manifest；任何其他
artifact 出现该值均使 `output_manifest_hash_gate=fail`。该 DAG 不允许 fixed-point、自身 placeholder、写后回填或迭代求 hash。

Semantic canonicalization version 固定为 `21B_semantic_v6`。本 requirement 中 `canonical_json_bytes` exact 定义为：object key 按
UTF-8 bytes 升序；array 保持已注册 record order；UTF-8、`ensure_ascii=false`、无空白 separator；boolean/null 为小写 JSON token；integer
使用无前导零十进制；finite JSON number 在 semantic form 中转换成字符串 `f64le:<IEEE-754-little-endian-8-byte-lowerhex>` 后再序列化；
NaN/Inf 禁止。CSV/Parquet 的 float 继续按 schema dtype 的 little-endian bytes hash，不先转 JSON。YAML parsed object 和 LightGBM
`dump_model()` object 同样使用此 canonicalizer；不得依赖 Python dict insertion order、默认 `json.dumps` float 文本或 locale。

只允许排除以下 volatile fields：

```text
training_run_registry.csv: started_at_utc,ended_at_utc
seed_level_training_curves.csv: elapsed_seconds,peak_memory_mib
model_parameter_compute_latency_audit.csv: train_seconds,inference_seconds,
  latency_ms_per_1000_rows,peak_cpu_rss_mib,peak_gpu_memory_mib
stage_status_registry.csv: started_at_utc,ended_at_utc
JSON: generated_at_utc,worker_pid,started_at_utc,ended_at_utc
report: exact single line beginning "generated_at_utc:"
```

Semantic CSV/Parquet sort-key registry exact 为（missing/`NA` sort last）：

```text
preflight_access_audit.csv = access_seq
upstream_21a_authorization_and_hash_audit.csv = check_id,artifact_path
materialization_access_audit.csv = access_seq
materialization_failure_evidence.csv = check_id
training_run_registry.csv = arm_id,model_seed,attempt_id
model_search_accounting_manifest.csv = job_id
seed_level_training_curves.csv = arm_id,model_seed,epoch_or_round
model_parameter_compute_latency_audit.csv = arm_id,model_seed
training_access_audit.csv = access_seq
historical_design_holdout_access_audit.csv = scope
stage_status_registry.csv = stage_ordinal
daily_rankic_readout.csv = arm_id,score_role,model_seed,fold,decision_date
rankic_stability_and_concentration_audit.csv = arm_id,score_role,model_seed,scope,slice_id
fragility_unit_contribution_audit.csv = arm_id,score_role,model_seed,fold,unit_type,unit_id
finalize_failure_evidence.csv = check_id
gate_evidence_21b.csv = gate_id,check_id
21B_baseline_benchmark_decision.csv = run_id
decision_universe_and_label_resolution_audit.parquet = split,fold,decision_date,instrument
sequence_sample_index.parquet = sample_row_idx
selection/validation_early_prediction_scores.parquet = split,decision_date,instrument,arm_id,score_role,model_seed
readout/validation_late_prediction_scores.parquet = split,decision_date,instrument,arm_id,score_role,model_seed
daily_prediction_scores.parquet = split,decision_date,instrument,arm_id,score_role,model_seed
```

YAML 的 semantic hash 必须基于 parsed object 的 `canonical_json_bytes`，不基于注释/空白；JSON record arrays 使用各自已注册的
canonical record order，worker `produced_artifact_paths/hashes` 按 path 排序。

Payload/control path 分层只用于解除 DAG 依赖，不是 volatile exclusion；顶层 semantic domain 不得排除 config、row keys、access decisions、
selected epoch/round、loss/RankIC、model tensor、score、gate、decision、report 或 file membership。CSV 以 exact schema 顺序和 sort key
序列化，float 使用 IEEE-754 little-endian bytes；JSON 使用上述 `canonical_json_bytes`；
Parquet 的 semantic hash 基于 schema + canonical column buffers，不基于可能变化的 footer bytes。Manifest 必须包含：

```text
schema_version,canonicalization_version,volatile_field_exclusions,
bundle_root_class,bundle_root_relative_path,preauthorization_audit_id,
artifact_profile_id,control_paths,semantic_payload_artifact_hashes,semantic_payload_bundle_hash,
semantic_artifact_hashes,model_state_semantic_hashes,semantic_bundle_hash,status
```

`model_state_semantic_hashes` 在 P0/P1 必须为空，P2 与 completed candidate count 相等，P3/P4/P5 必须 exact 12；不能用 placeholder hash
补齐 blocked profile。

所有 volatile fields 仍受 full-byte output hash 保护；semantic exclusion 只用于同输入/同环境重复运行的确定性比较。

## 12. Implementation acceptance tests

最低测试集合：

1. current blocked `21A_v1` 使 preflight fail，且 qfq/cache/outcome read count 为 0；
2. mock successful successor 的 28 gates/142 checks/hash chain 全通过才可进入 materialization；
3. execution authorization 缺失、extra key、wrong hash、non-human 或 non-approved 均 fail；
4. 任一 upstream artifact/hash/file-set mismatch fail；
5. date-range firewall 拒绝 `decision_date>=2024-01-02` 的 label/metric，以及 `source_date>2023-12-14` 的 outcome value decode；
6. live qfq/source hash mismatch 必须在 value decode 前失败；unpartitioned qfq fixture 允许 full-file byte hash 和 routing-date peek，
   但禁止 cutoff 后 value parse；先全表 DataFrame parse 再 filter 必须被 access wrapper 拒绝；
7. feature cache label/outcome column、wrong feature count、wrong order/hash fail；
8. composite panel 的 missing component、wrong byte size/hash/dtype/shape、non-contiguous row index、bad cache offset 或 key/date mismatch fail；
9. source sequence 恰为 T=10 且所有 feature dates `<=t`，memmap 第 11 列 exact 为 `forecast_y(t+1)`；
10. `train-baselines` 尝试回读 raw qfq/calendar/membership 必须 fail；
11. M1 只读取最后 feature row；M2 不读取 feature；M3/A0 shape 与公式 exact；
12. M3 GateNet 不读取 teacher/label，A0 不构造 teacher/Koopman/residual；
13. label 五状态 synthetic cases 与 whole-day fail-closed 行为正确；
14. denominator 不允许 per-arm intersection，score 缺一行使整日 pipeline fail；
15. M0 hash score 与 21A fixture exact，且对 row/batch order 不变；100-shift synthetic null fixture 在 `1e-12` tolerance 内；
16. realized M0 CI 不含 0 只产生 diagnostic warning，不使 hard gate fail；
17. average-rank Spearman 与 scipy fixture 一致；constant score/label 返回 not-evaluable 而非 0；
18. RankICIR 使用 `ddof=1`；
19. 13 planned jobs、12 provisional candidate files、3 seeds、explicit checkpoint paths/model types/serialization formats exact；
20. provisional candidate selection 只使用 `validation_early` 且 tie 取最早 epoch；改变 late labels 不得改变 candidate/hash；
21. selection worker 必须 fresh execve process；其 late panel/audit open attempt fail，且 controller 只能在 child exit 后 seal；
22. gate-readout worker 必须是新的 inference-only process；optimizer/backward/LightGBM train-update/selection import-call 全部 fail；
23. full/early/late complete-day thresholds 通过前 candidate 只能是 provisional；12 records 全部 `eligible_frozen` 才通过
    `checkpoint_eligibility_gate`；
24. M1 tree-model semantic hash 与 M2/M3/A0 tensor semantic hash 分别按 model-type fixture exact；
25. ensemble 为三 seed arithmetic mean；score-role/null schema 和 checkpoint/bundle hash semantics exact；
26. M1 每 seed 独立 Dataset construction；跨 seed shared/reference Dataset 被拒绝；same-seed synthetic rerun exact、跨 seed允许不同，
    ensemble exact 为三 seed arithmetic mean，gate 使用 `positive_late_seed_n>=2/3`；
27. PyTorch initialization fixture 验证 exact module order、CPU generator、四个 recurrent gate-slice orthogonal、仅
    `bias_ih_l0[H:2H]=1`；双 forget bias、whole-matrix recurrent orthogonal 或参数顺序变化均 fail；
28. deterministic runtime flags mismatch fail；repeated/reordered inference max delta 为 0；
29. NaN/Inf/OOM ladder 和最低 batch fail-closed；
30. late-only baseline gate pass/fail boundary fixtures 覆盖每个 conjunct，M1/M2/M3 均覆盖 `positive_late_seed_n`；
31. M0/A0 单独正向不能通过 baseline information gate；
32. `historical_design_holdout_access_audit` 四个 outcome counts exact 0，byte/routing counts 不混入；
33. selection late-panel breach 在 0..12 candidate 的边界均产生 P2/state 2；gate-readout/late holdout breach 产生 P3 或 P4/state 2；
34. P0-P5 每个 artifact profile 均测试 required/forbidden/exact file-set；blocked profile 不补造成功 artifacts；
35. 缺失/无效 authorization 的 P0 只写 deterministic preauthorization audit path，随后合格 authorization 可创建 canonical v4 root；
36. transactional `.building` 不得作为 sealed output；post-build full-disk reopen 失败不得 atomic seal；任何 sealed profile 的
    `output_manifest_hash_gate` 必须为 pass；
37. decision exact header 包含全部 causal gates和 seal meta-gate；任一 omitted/duplicate gate、错误 first-match 或非 canonical
    `blocking_reasons` 均 fail；
38. leave-one-day/instrument contribution、`ceil(n/3)`、absolute-contribution order、tie-break 与 simultaneous removal fixture exact；
39. manifest file-set、CSV exact header/sort registry、Parquet schema/sort/null、`canonical_json_bytes` 的 float/Unicode/key-order fixture 全部验证；
40. canonical output root 必须为 versioned v4 root；unversioned/v1/v2/v3/existing sealed root 均拒绝；
41. sealed output 与 sealed preauthorization audit 重跑均拒绝覆盖；
42. full small synthetic integration 两次运行的 `semantic_payload_bundle_hash` 和顶层 `semantic_bundle_hash` 均 exact 一致；decision/gate/report
    改变只改变顶层 hash，payload artifact 改变同时改变两层；除 semantic manifest/final manifest 外任何 artifact 嵌入顶层 hash均 fail；
    timestamp/latency 改变时 full-byte output hash 允许且应变化，非 volatile score/model/gate/decision 改变时顶层 semantic hash 必须变化。

## 13. Validation commands

实现后至少执行：

```bash
.venv/bin/python -m pytest -q \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21b_alpha158_sequence_baseline_benchmark.py

.venv/bin/ruff check \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21b_alpha158_sequence_baseline_benchmark.py \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21b_alpha158_sequence_baseline_benchmark.py

.venv/bin/python -m py_compile \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21b_alpha158_sequence_baseline_benchmark.py

uv lock --check
git diff --check
```

Blocked 21A_v1 的 mandatory negative preflight 必须使用独立 test fixture/override，不能改写 production config 中已固定的 v2 hashes：

```bash
.venv/bin/python -m pytest -q \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21b_alpha158_sequence_baseline_benchmark.py \
  -k blocked_21a_v1_fails_before_outcome_access
```

Fixture 必须返回 block state，且 access audit 证明没有 outcome read。Production 21A_v2-bound 21B_v6 preflight 仍须等待单独
execution authorization；
不得为了通过测试把 authorization gate 改成可选。

## 14. Completion checklist

- [ ] Current blocked 21A_v1 被 explicit deny，且 preflight 在 outcome access 前失败
- [ ] Successful 21A successor version/hash 全部 exact pinned
- [ ] 21B human execution authorization 与 requirement/upstream hashes 绑定
- [ ] 只物化 train/validation `Y_rank_primary`
- [ ] composite model-input panel 的 sequence index、return/label memmap、shape/offset/hash 全部密封
- [ ] live qfq/cache/source hashes 在 outcome value decode 前 exact-match 21A successor
- [ ] qfq byte/routing access 与 semantic outcome row access 分离，cutoff 后 value decode 为 0
- [ ] historical design holdout outcome/label/score-join/metric read count 为 0
- [ ] 157-feature route、cache、normalizer、split hashes 继承成功 21A
- [ ] canonical output root/version exact 为 21B_v6；缺失/无效授权只写 content-addressed preauthorization audit path
- [ ] 五个 mandatory arms、13 jobs、12 provisional candidates 与 actual checkpoint files exact
- [ ] M1 tree checkpoint 与 M2/M3/A0 tensor checkpoint 的格式、byte hash、semantic hash 可复算
- [ ] M1/M2/M3/A0 formulas、loss、score index 和 tensor shapes exact
- [ ] M2/M3/A0 parameter initialization 的 module order、gate-slice、单一 forget bias 与 contract hash exact
- [ ] 三 seeds 与 ensemble mean，不允许 best-seed primary；M1/M2/M3 均使用 `positive_late_seed_n>=2/3`
- [ ] 所有 retained days 完整 denominator 与 100% score coverage
- [ ] daily RankIC 使用 average ranks、float64 Pearson、decision-day inference unit
- [ ] validation early 只选 provisional candidate，full/early/late coverage 后才授予 `eligible_frozen`
- [ ] selection worker 退出后才 seal；fresh inference-only worker 才能打开 validation late
- [ ] validation full/early/late、full/late LOMO 与 month concentration 完整
- [ ] top-third day/instrument fragility 的 unit contribution、rounding、tie-break、selection ledger 与 simultaneous removal exact
- [ ] baseline information gate 为 M1/M2/M3 的 late-only conjunctive any-pass
- [ ] A0/M0 不得单独授权 21C
- [ ] realized M0 CI 仅为 diagnostic，结构性 hash/synthetic null checks 才是 hard gate
- [ ] 不读取 historical holdout，不运行 Koopman/residual/economic replay
- [ ] pre-gate checkpoint bundle 在 late readout 前密封，pre-holdout bundle 在任何未来 holdout readout 前密封
- [ ] P0-P5 artifact profile required/forbidden file set 与 blocked finalize 行为 exact
- [ ] late-stage forbidden access 可由 P2/P3/P4 合法封存为 state 2，不得误降级 state 4
- [ ] decision 唯一、全部 causal/meta gate columns、canonical blocking reasons 与后续授权字段 fail closed
- [ ] score role/null/checkpoint schema 唯一，无重复 `ensemble_score`
- [ ] full-byte seal、semantic payload hash 与顶层 semantic hash 按无环 DAG 分离且可复算
- [ ] deterministic runtime flags 与 CSV/Parquet/JSON/YAML semantic order exact
- [ ] report、decision、gate evidence、manifest、output hashes 可双向复算
- [ ] tests、ruff、py_compile、lock check、diff check 全通过

---

## 15. 21B_v5 QFQ runtime-counter correction successor

`21B_v5` 是 sealed `21B_v4` 的 immutable corrected successor。它不覆盖 v4，不重训或挑选模型，只针对
`QFQ_POST_CUTOFF_VALUE_TOKEN_AND_RUNTIME_COUNTER_SEMANTICS` 缺陷执行真实的 cutoff-prefix access replay，并把每次 wrapper access
在返回 value 或异常前写入 append-only raw log。v5 必须新增并密封：

```text
audits/qfq_runtime_access_event_log.csv
audits/qfq_runtime_counter_evidence.csv
contract_erratum_21b_v5.json
paper_lineage_erratum_21a_for_21b_v5.json
```

Raw log、aggregate evidence、erratum 的 schema、计数公式与 hash closure exact 继承
`requirement_21c_full_reaka_pit_proxy_replication.md` Section 2.2。两个 post-cutoff count 与四个 historical-holdout count必须均从 raw
log 重算为 0；禁止用 config 常量或空报告声明代替。`counter_collection_mode=runtime_wrapper_and_append_only_log`、
`runtime_counter_aggregation_contract_id=QFQ_RUNTIME_ACCESS_EVENT_AGGREGATION_V1`、`status=corrected_rerun_sealed`。

v5 source config、decision 与 final manifest 必须显式包含：

```text
upstream_21b_contract_erratum_gate = pass
```

v4 model checkpoints、panels、prediction scores和 metrics 只允许 byte-preserving 继承；v5 manifest 必须重新密封 exact file set、semantic
payload 和 output hashes，并记录 v4 source root/hash lineage。M2 lineage 同时由 human-approved
`paper_lineage_erratum_21a_for_21b_v5.json` 修正为 `project_return_only_diagnostic`，不得映射 paper LSTM 或 `w/o GM`。

### 15.1 21B_v6 gate-registry compatibility successor

`21B_v6` byte-preserving 继承 sealed v5 的 corrected runtime log、aggregate evidence、model/panel/score/metric payload。唯一 material change是
把 integration acceptance 固化为 27-row gate registry：原 26-row 21B registry 加一条
`upstream_21b_contract_erratum_gate=pass`。v6 必须更新 requirement/config/runner/test pins、decision/root/version、semantic manifest 与 final
hash closure；不得重训、重选 checkpoint 或访问 historical holdout。

本 requirement 的完成只表示 21B 规格已生成，并已绑定成功的 21A_v2 successor。执行仍须单独 human authorization；本文件不得被
用作绕过 execution authorization，或把已密封 `21A_v1` false-negative bundle 改写为 pass 的依据。
