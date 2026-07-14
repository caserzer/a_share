# Requirement 20B-P4-MLRANK：P4 Eligible Universe 多因子次月收益单调排序诊断

> 文档状态：`draft_requirement_execution_authorized_pending_implementation`
>
> 生成日期：2026-07-14
>
> Experiment ID：`20_ohlcv_positive_beta_exposure_research`
>
> Phase ID：`20B_P4_MLRANK`
>
> Run ID：`20B_P4_learned_monotonic_return_ranking_diagnostic_v1`
>
> Contract version：`20B_P4_MLRANK_v1`
>
> Claim ceiling：`design_contaminated_historical_ranking_diagnostic_only`

## 0. 一页执行结论与不可协商范围

本 requirement 只回答一个问题：

> 在当前 P4 market-only residual-momentum eligible 股票横截面上，使用 P0/P1/P4/P6 的严格 point-in-time signals 训练多因子 cross-signal reranker，能否形成一个 ex-ante score，使 score 从低到高形成的十个桶在**下一月横截面收益排序**上比原始 P4 score 更接近单调递增？

研究身份与 claim boundary 固定为：

```text
research_scope = cross_signal_learned_reranker_on_p4_eligible_universe
multi_factor_model_allowed = true
P4_single_factor_repair_claim_allowed = false
P4_raw_score_role = incumbent_paired_baseline_and_registered_feature
```

因此，若 full model 通过，只能声明“P4 eligible universe 上的冻结多因子 reranker 改善了排序形态”；不得声明 P4 residual momentum 单因子已被修复。A1/A2 只用于解释 P4 path 与其他 signals 的相对贡献。

目标是排序形态，不是绝对收益。Primary objective 固定为：

```text
D1 expected next-month cross-sectional return
    <= D2
    <= ...
    <= D10
```

本轮明确**不要求**：

```text
D1 < 0
D10 > 0
任何 middle bucket > 0
Top-N 绝对收益为正
Top-N 跑赢现金或国债
每一个实现月份都严格单调
```

对同一个 decision month 的十桶收益同时加上或减去同一常数，不得改变本轮任何 primary monotonicity metric 或 gate。市场共同涨跌、现金/国债 participation、long-only absolute-return regime 是另一问题，不得混入本轮模型选择。

本轮是在查看 20B v5 和后续63个月十桶 outcome 后提出的模型 follow-up，固定属于：

```text
historical_sample_role = design_contaminated_followup
historical_support_claim_allowed = false
true_out_of_sample_claim_allowed = false
exact_replication_claim_allowed = false
deployment_authorized = false
```

即使 robustness split 通过，也只能写成“在冻结的 historical pseudo-OOS split 上观察到排序形态改善”，不得写成真实 OOS 支持、可部署 alpha 或可盈利 long-only 策略。

### 0.1 禁止的捷径

Primary result 禁止：

- 用下一月实现收益直接排序股票；
- 对 robustness outcome 调参、选特征、选模型、改 split 或改变桶数；
- 股票行随机 train/test split；
- 把同一月份数百只股票当作数百个独立时间样本；
- 对实现桶收益做 isotonic regression 后把“校准曲线”冒充模型排序改善；
- 根据 full/robustness 结果事后改变损失权重、树深、正则强度、feature set 或缺失值规则；
- 以 D10 绝对正收益、D1 绝对负收益或 cash outperformance 作为本轮 gate；
- 读取或使用 P5 retrospective board proxy、未来 board membership、未来 universe membership 或未来 outcome-resolution 状态作为 feature；
- 把本轮 learned score 回写、覆盖或重新密封到 20B v5。

## 1. 身份、文件与授权边界

```text
experiment_id = 20_ohlcv_positive_beta_exposure_research
phase_id = 20B_P4_MLRANK
run_id = 20B_P4_learned_monotonic_return_ranking_diagnostic_v1
contract_version = 20B_P4_MLRANK_v1
requirement_file = requirement_20b_p4_learned_monotonic_return_ranking_diagnostic.md
config_file = configs/config_20b_p4_learned_monotonic_return_ranking_diagnostic.yaml
runner_file = src/run_20b_p4_learned_monotonic_return_ranking_diagnostic.py
test_file = tests/test_20b_p4_learned_monotonic_return_ranking_diagnostic.py
output_root = outputs/20B_P4_learned_monotonic_return_ranking_diagnostic_v1
```

本 requirement 的生成，以及后续实现、historical outcome 读取和模型训练，均由 workspace user 于 2026-07-14 的直接指令授权；不需要等待另一份人类审批文件：

```text
requirement_generation_authorized = true
separate_human_execution_authorization_required = false
requirement_execution_authorized = true
implementation_authorized = true
historical_outcome_execution_authorized = true
model_training_authorized = true
policy_training_authorized = false
portfolio_optimization_authorized = false
20C_requirement_generation_authorized = false
20C_execution_authorized = false
deployment_authorized = false
```

Runner 不得因为缺少 `execution_authorization.json` 而阻塞。执行仍必须依次通过 upstream integrity、outcome firewall、split integrity、dependency 和 deterministic gates；直接执行授权不豁免任何数据、时序或结果治理约束。

同一 `run_id + contract_version` 不得覆盖已有成功或失败 bundle。Feature、split、label、model、hyperparameter、bucket、metric、gate 或 unknown 规则发生 material change 时必须升级 contract version 和 output root。

### 1.1 Config 必须冻结的值

未来 config 至少必须 exact-match：

```text
identity: experiment_id, phase_id, run_id, contract_version
paths: requirement_file, upstream_v5_root, output_root,
       replay_a_scratch_root, replay_b_scratch_root
upstream: expected_contract_version, expected_final_output_hashes_sha256,
          expected_final_manifest_sha256, expected_decision_sha256,
          expected_preoutcome_bundle_hash, expected_historical_bundle_hash,
          expected_assignment_sha256, expected_outcome_audit_sha256,
          expected_fold_freeze_sha256, exact_report_waiver_path,
          expected_sealed_report_sha256
base_population: arm_id, semantic_track, source_bucket_count, signal_eligible
feature_arms: P0/P1/P4/P6 exact arm_id + semantic_track
splits: train/validation/robustness exact decision-date boundaries
labels: source column, known policy, percentile-rank formula, relevance-bin formula,
        paper_proxy_forbidden=true
features: exact ordered feature IDs, imputation constants, lag rules
models: exact model IDs and every hyperparameter
scoring_instances: validation/robustness scored_model_id + family + fit mapping
research_scope: multi_factor_model_allowed, P4_single_factor_repair_claim_allowed
sorting: bucket_count=10, score direction, tie breaker
inference: HAC lag, bootstrap block length, repetitions, seed
gates: every threshold and truth table in Section 11
serialization: float/CSV/Parquet/JSON/hash rules
```

Unknown config key、缺失 key、requirement/config mismatch 或 CLI 覆盖冻结参数必须 fail closed。

### 1.2 Direct execution authority

```text
execution_authority = workspace_user_direct_instruction_2026-07-14
execution_authority_mode = direct_no_separate_authorization_file
execution_authority_record_required = false
```

Preflight 的 `contract_snapshot.json` 必须记录上述三个常量以及 exact `requirement_sha256`、`contract_version` 和 upstream bundle hash。它们用于审计本次执行依据，不是等待后续签字的 gate。Runner、config、tests 和 output inventory 均不得要求、生成或引用独立 authorization file。

## 2. 只回答与不回答的问题

### 2.1 只回答

1. 原始 P4 score 在冻结 validation/robustness 月份上的 security-level Rank IC 和十桶单调形态是什么？
2. 固定的线性 rank regression 是否能比原始 P4 改善下一月横截面收益排序？
3. 固定的 LightGBM LambdaRank 是否能比原始 P4 改善下一月横截面收益排序？
4. 改善是否同时出现在 aggregate bucket curve、逐月 Rank IC 和 robustness 前后半段，而不是只由某一个月或某一相邻桶推动？
5. 若改善存在，它主要来自 P4 path，还是来自 P0/P1/P6 cross-signal ensemble？
6. 改善是否足以称为 `near_monotonic`，还是仅为弱改善/不稳定改善？

### 2.2 不回答

本 requirement 不回答：

- 哪一种 OHLCV feature family 在无限搜索下最好；
- 深度模型、Alpha158、自动编码器或 sequence architecture 是否更好；
- 是否应该持有现金/短债；
- 下一月 Top bucket 的绝对收益是否为正；
- 成本后 Top-N portfolio 是否可部署；
- learned score 是否提供独立于 P0/P1/P6 的 residual-momentum alpha；
- 未来新数据是否确认 historical pattern。

## 3. 上游 immutable 输入与完整性合同

路径别名：

```text
EXPERIMENT_ROOT = topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research
UPSTREAM_V5_ROOT = EXPERIMENT_ROOT/outputs/20B_trendpv_residual_momentum_design_and_replication_diagnostic_v5
ASSIGNMENT = UPSTREAM_V5_ROOT/historical/instrument_month_signal_bucket_assignment.parquet
OUTCOME_AUDIT = UPSTREAM_V5_ROOT/historical/outcome_resolution_audit.csv.gz
FOLD_FREEZE = UPSTREAM_V5_ROOT/preoutcome/statistical_and_fold_freeze.csv
V5_DECISION = UPSTREAM_V5_ROOT/20B_trendpv_residual_momentum_design_and_replication_diagnostic_decision.csv
V5_MANIFEST = UPSTREAM_V5_ROOT/manifest_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json
V5_OUTPUT_HASHES = UPSTREAM_V5_ROOT/output_hashes_20b_trendpv_residual_momentum_design_and_replication_diagnostic.json
V5_PREOUTCOME_OUTPUT_HASHES = UPSTREAM_V5_ROOT/preoutcome/preoutcome_output_hashes_20b.json
V5_HISTORICAL_MANIFEST = UPSTREAM_V5_ROOT/historical/historical_manifest_20b.json
V5_HISTORICAL_OUTPUT_HASHES = UPSTREAM_V5_ROOT/historical/historical_output_hashes_20b.json
```

冻结上游身份：

```text
upstream_contract_version = 20B_v5
upstream_final_output_hashes_sha256 = 51c74f44ec3157f0df39b724b818477907c69bc7e10490fafbc67cc2bf6ff6e4
upstream_final_manifest_sha256 = e99d797c81729ab6c51e6de027218d81cbd7d9244cb556989af62b8916f83e6b
upstream_decision_sha256 = 322aac8de0f5ccd456e9b90830644edcd2c473bfec48baf1cab348fee11e9992
upstream_preoutcome_bundle_hash = 4079813d74ce16344dd53886c6a986c356a17589dd5725c18622a807de1102d1
upstream_historical_bundle_hash = bac77bc13efcd7b75df5b18f44940bcc24e57589e62dde593bd0ef748705426f
upstream_historical_manifest_sha256 = 4080855f5a97ecfaba0d11dbf2ac0607a927086ef3e57cfd40dfbcdf89474bda
assignment_sha256 = 99f4d543318a343b9a1832b2e7f6c3b00ad841f80af68270c994054dd4e86721
outcome_audit_sha256 = 6231d9f6fc6828b0803b71b4a7a52ef199db6792b1ec9616b7e152495616bba6
fold_freeze_sha256 = 0930e56eaca91882b5f82b7ef0062ee924607a6a6847e9f00916e3816380b9e7
upstream_historical_sample_role = design_contaminated_historical
upstream_20C_requirement_generation_authorized = false
```

Preflight 的 exact verification algorithm：

1. 验证 `SHA256(V5_OUTPUT_HASHES bytes)`、`SHA256(V5_MANIFEST bytes)`、`SHA256(V5_DECISION bytes)` 分别等于上述冻结值；
2. 验证 final manifest 的 `contract_version/run_id/preoutcome_bundle_hash/historical_bundle_hash/immutable` exact-match；
3. 验证 `SHA256(V5_PREOUTCOME_OUTPUT_HASHES bytes)=upstream_preoutcome_bundle_hash`，并复算其中全部 entries；
4. 验证 `SHA256(V5_HISTORICAL_OUTPUT_HASHES bytes)=upstream_historical_bundle_hash`，并复算其中全部 entries，包括 `V5_HISTORICAL_MANIFEST`、`ASSIGNMENT` 与 `OUTCOME_AUDIT`；
5. 验证 final output-hashes registry 中 decision 与 manifest entries；
6. final registry 中 report 的 sealed hash `370904e7e69ab947f74c7e9cbfe98732ee9a3bcd53df5d39aa2623ea6ad66f26` 只记录为 `known_postseal_narrative_hash_waiver`，不得打开、读取或验证当前 report bytes，也不得把该 waiver 扩展到任何 machine artifact。

报告 Markdown 不是本轮输入 authority。除上述唯一 report path 外，任何 registry entry mismatch 都必须 fail closed；不得笼统跳过 top-level registry，也不得用报告叙事反向重建 machine decision。

### 3.1 P4 base population

从 `ASSIGNMENT` 只取：

```text
arm_id = P4_RESMOM_R2_MARKET_ONLY_ADAPTATION
semantic_track = project_sequential_market_residual_primary
bucket_count = 10
signal_eligible = true
```

`bucket_count=10` 只用于去除同一 signal 在 5/10 bucket materialization 中的重复行；不得继承 v5 原 bucket_id 作为 model feature 或 label。

冻结 base population audit expectation：

```text
decision_month_n = 63
decision_date_min = 2021-01-29
decision_date_max = 2026-03-31
instrument_month_n = 25,049
minimum_monthly_instrument_n = 295
maximum_monthly_instrument_n = 447
known_project_label_n = 25,020
unknown_project_label_n = 29
```

运行时必须从 sealed artifact 重算这些值。任一不一致进入 `upstream_input_integrity_blocked`，不得自动接受新的 row population。

同一 `(decision_date, instrument_id)` 必须唯一。`raw_signal` 必须 finite。Base population 不允许因 label unknown、模型缺失 feature 或 future universe 状态被删除；feature missing 只能按 Section 7 的冻结规则保留并显式标记。

### 3.2 Feature-arm 白名单

只允许从同一 sealed `ASSIGNMENT` 读取下列 signal：

| Feature alias | arm_id | semantic_track | 用途 |
|---|---|---|---|
| `p4` | `P4_RESMOM_R2_MARKET_ONLY_ADAPTATION` | `project_sequential_market_residual_primary` | incumbent residual-momentum path |
| `p0` | `P0_TOTAL_MOMENTUM_12_1` | `project_return_history_primary` | total-momentum comparator signal |
| `p1` | `P1_TRENDPV_RAW_ADAPTATION` | `project_strict_primary` | TrendPV signal |
| `p6` | `P6_LOWVOL_36M_COMPARATOR` | `project_monthly_volatility_primary` | Low Vol comparator signal |

所有 feature route 同样固定 `source bucket_count=10`，按 `(decision_date, instrument_id)` left join 到 P4 base population。

明确禁止：

```text
P5_RESMOM_R3_BOARD_ADAPTATION
full_history_retrospective_proxy
bucket_id / bucket_role / ex_ante weights
project/paper next-month return
outcome_resolution
project_bucket_month_evaluable
instrument_id hash/encoding as feature
calendar year/month trend feature
```

P5 被排除是因为其 static board route 含 retrospective proxy scope；本轮不得让模型通过 P5 吸收 board look-ahead。

### 3.3 Required upstream audit

`preflight/upstream_input_integrity_audit.csv` 最少字段：

```text
artifact_id
artifact_path
expected_sha256
observed_sha256
expected_value
observed_value
status
blocking_reason
```

任何必需 hash、schema、row key或 frozen value mismatch 必须在读取 outcome column 和 model fit 前终止。

## 4. Staged execution 与 outcome firewall

未来 runner 只能执行：

```text
parent orchestrator CLI = full
stage 1 = preflight
stage 2 = materialize
stage 3 = select-candidates
stage 4 = score-and-readout
stage 5 = finalize
```

`--stage full` 是唯一 publication-capable CLI：它按 Section 8.5 管理 replay A/B、逐一启动内部 stage workers、比较 registered core outputs，并只 finalize replay A。单 stage CLI 只允许 tests/debug scratch 执行，必须带 `--non-publishable-test-run`，不得写入正式 `output_root`、不得生成 final decision/report/manifest。

### 4.1 Preflight

只允许读取：requirement/config bytes、v5 manifest/hash/decision、Parquet schema/footer metadata 和 Section 3 的 integrity metadata。

不得读取：

```text
project_resolved_next_month_return
paper_proxy_next_month_return
outcome_resolution
任何 raw qfq outcome value
```

Preflight 必须输出并密封：

```text
preflight/contract_snapshot.json
preflight/upstream_input_integrity_audit.csv
preflight/split_registry.csv
preflight/feature_registry.csv
preflight/model_registry.csv
preflight/preflight_manifest.json
preflight/preflight_output_hashes.json
```

### 4.2 Materialize

仅在 preflight 已密封且 requirement/config/upstream identity exact-match 后运行；不等待额外的人类 authorization 文件。

Materialize 分成两个 fresh process：

```text
feature-worker:
    column-project only feature/source columns;
    build feature_panel without any outcome column;
    seal feature bundle and exit.

label-worker:
    start only after feature bundle seal;
    read frozen project label/outcome columns;
    build physically separate train_validation_label_panel
        and robustness_label_panel;
    seal both files and label-resolution audit;
    never modify feature_panel.
```

`feature-worker` 的 import/read audit 中 outcome field read count 必须为零。

两个 label files 不得只是同一 Parquet dataset 的 logical partition 或 symlink；必须是两个独立 regular files、分别 hash。Selection/refit workers 的 read whitelist 只允许 `train_validation_label_panel.parquet`；score worker 不得读取任何 label；三者均禁止打开 `robustness_label_panel.parquet`。

### 4.3 Select-candidates：独立 selection worker 与 pre-robustness seal

Controller 必须启动一个 fresh `selection-worker`；其 filesystem whitelist 只允许：

```text
sealed preflight bundle
sealed materialized/feature_panel.parquet
sealed materialized/train_validation_label_panel.parquet
```

明确禁止打开 `robustness_label_panel.parquet`、任何 robustness outcome proxy 或未注册 feature。Worker 内按顺序：

1. 只用 train rows 分别拟合 M1/M2 candidate；
2. 保存两个 candidate model artifacts；
3. 在 validation rows 上一次性打分；validation label 不得用于 fit、early stopping 或 model update；
4. 使用 validation labels 计算所有 registered selection metrics；
5. 按 Section 9.1 选择唯一 `selected_model_family_id`；
6. 写出全部 candidate fit audit、scores、outcome-free validation bucket assignments、metrics、selection record 与 access audit；
7. 正常退出，不得继续执行 refit 或 robustness scoring。

Worker 退出后，parent controller 才允许机械写入 `selection/selection_worker_exit.json`。只有同时满足：

```text
selection_worker_exit_code = 0
selection_worker_status = pass
robustness_label_open_count = 0
robustness_outcome_column_read_count = 0
candidate_n = 2
selection_row_n = 1
```

controller 才密封 `pre_robustness_selection_bundle`。Selection bundle hash 必须在任何 selected-family refit、robustness score 或 robustness label open 之前形成。Controller 不得导入/调用 model fit、score selection 或 metric implementation。

### 4.4 Score-and-readout：refit、score 与 metric 三进程边界

只有 pre-robustness selection bundle hash 验证通过，controller 才可启动 fresh `refit-worker`。该 worker 只允许读取：

```text
sealed feature_panel
sealed train_validation_label_panel
sealed pre_robustness_selection bundle
```

它必须：

1. 使用 frozen selected family 和 Section 8 exact hyperparameters 在 train+validation rows 上拟合 `selected_full_refit`；
2. 使用同一 family/hyperparameters 拟合 `A1_P4_PATH_ONLY_refit` 与 `A2_CROSS_SIGNALS_WITHOUT_P4_refit`；
3. 写出三个 exact fit artifacts、fit contracts、artifact registry、fit audit 与 frozen feature-importance readout；
4. 正常退出；不得读取 robustness features 或任何 robustness label。

Parent 在 worker 退出后写 `models/refit_worker_exit.json` 并密封 model bundle。要求：

```text
robustness_label_open_count = 0
robustness_rows_used_for_fit = 0
robustness_feature_row_read_count = 0
```

Model bundle hash 形成后，controller 才启动 fresh inference-only `score-worker`。该 worker：

- 只读 sealed model bundle、sealed feature panel 与 frozen P4 base keys；
- 不得打开 train/validation/robustness label files；
- 不得 import/call Ridge.fit、LightGBM train/refit/update 或 feature-transform fit；
- 载入三个 refit artifacts，对完整 robustness features 一次性打分；
- 机械生成 B0/N0 robustness scores；
- 只按 score 形成 outcome-free 十桶 membership；
- 写出 score access/call audit 后退出。

Parent 写 `scores/score_worker_exit.json`，验证 `fit_or_update_call_count=0`、`any_label_open_count=0` 后密封 score bundle。Score payload 可以记录已经存在的 `model_bundle_hash`，不得记录自身尚未形成的 score bundle hash。

Score bundle 密封后，controller 才可启动 fresh inference-only `metric-worker`。该 worker：

- 只读 sealed score bundle、sealed robustness label panel 和已冻结 metric config；
- 不得 import/call Ridge.fit、LightGBM train/refit/update、candidate selection 或 feature transform fit；
- 生成 robustness return join、monotonicity、paired delta、bootstrap、ablation 与 descriptive top-bucket turnover readout；
- 写出 access/call audit 后退出。

Parent 验证 `metric_worker_exit_code=0` 后密封 historical readout bundle。禁止 expanding refit 穿过 robustness，禁止先看 robustness 再改变 selection、feature 或 hyperparameter。

### 4.5 Finalize

只读 replay A 已密封的 preflight、materialized、selection、model、score、historical readout bundles，以及 parent-written determinism comparison artifacts，计算 gate/decision/report/final manifest。不得重新读取 upstream raw data、robustness label，不得重训或改写任何 stage artifact。

## 5. 冻结时间切分与统计单位

63个 decision months 固定切分：

| split | decision date | 月份数 | P4 rows | known labels | unknown labels | 角色 |
|---|---|---:|---:|---:|---:|---|
| `train` | `2021-01-29..2023-06-30` | 30 | 10,642 | 10,631 | 11 | model fit only |
| `validation` | `2023-07-31..2024-06-28` | 12 | 5,107 | 5,106 | 1 | candidate selection only |
| `robustness` | `2024-07-31..2026-03-31` | 21 | 9,300 | 9,283 | 17 | frozen final readout |

Split 只能按 `decision_date` 形成；禁止 `train_test_split`、股票行随机切分、instrument-stratified random split 或把同一个 decision month 分到多个 split。

所有 inference 的独立统计单位是 decision month，不是 instrument row。Instrument rows 只用于同月横截面 ranking loss 和 Rank IC。

Robustness 额外固定两个稳定性子段，仅用于 readout，不用于选择：

```text
robustness_early = first 10 robustness decision months
robustness_late  = remaining 11 robustness decision months
```

不得根据可评价月份重新切半。

## 6. Label、unknown 与 relevance contract

### 6.1 Primary outcome

唯一 primary label source：

```text
project_resolved_next_month_return
```

Key：

```text
(decision_date=t, instrument_id) -> label_month=t+1
```

`outcome_resolution=valid_mark` 且 return finite 才是 known label；`unknown_bridge_arm_month_not_evaluable` 为 unknown，不进入 model loss，但 base feature row 和 model score 必须保留。

不得用 `paper_proxy_next_month_return` 填补 primary unknown。本 requirement 删除 paper-proxy sensitivity：label-worker、selection/refit/score/metric workers 均不得 materialize 或读取该列，任何 label/readout artifact 出现该列或对应 semantics 必须 fail closed。这样避免为非核心 sensitivity 扩大 outcome firewall。

### 6.2 Cross-sectional rank label

对每个 decision month，在 known-label P4 base rows 内：

```text
y_return = project_resolved_next_month_return
y_rank_average = rank(y_return, ascending=true, method=average)
y_rank_pct = (y_rank_average - 1) / (known_label_n - 1)
```

若 `known_label_n < 250` 或 `< 10 * 10`，该月不可训练/评价并 fail sample integrity。Equal return 必须得到相同 `y_rank_pct`，不得用 instrument id 人为制造 target order。

LightGBM relevance 固定为：

```text
y_relevance = min(9, floor(10 * y_rank_pct))
```

因此 target 是 `0..9` 的 ordinal relevance；higher relevance 表示下一月横截面收益更高，不表示绝对收益为正。

### 6.3 Unknown readout

Primary bucket-return readout：

1. 分桶只使用 ex-ante model score，unknown 不改变 membership；
2. 桶内删除 unknown outcome；
3. 对剩余 known rows 等权；
4. 只有十个桶均满足 `known_n >= 10` 且 `known_coverage_rate >= 0.95`，该月才进入 primary monotonicity readout；
5. 每个 model 必须使用相同 common evaluable months 与相同 known instrument rows进行 paired comparison。

Secondary strict sensitivity：只有十桶所有成员全部 resolved 的月份才进入；不得替代 primary。

## 7. Frozen feature contract

### 7.1 当月横截面 rank

对 feature arm `a in {p0,p1,p4,p6}`，每个 decision month 仅在该 arm `raw_signal` finite rows 内计算：

```text
feature_rank_average = rank(raw_signal, ascending=true, method=average)
feature_rank_pct = (feature_rank_average - 1) / (finite_n - 1)
```

若 `finite_n < 100`，该 arm 当月全部 feature 记为 missing。Feature rank 不做 favorable-direction 翻转；模型自行学习正负方向。

### 7.2 P4 path feature

P4 lag 以 calendar decision-month sequence 定义，不按某股票最近一次出现记录定义：

```text
p4_rank_t
p4_rank_lag1 = same instrument at immediately previous scheduled P4 month
p4_rank_lag3 = same instrument at exactly 3 scheduled P4 months before t
p4_rank_mean3 = mean(p4_rank_t, lag1, lag2), only if all 3 finite
p4_rank_std3 = population_std(..., ddof=0), only if all 3 finite
p4_rank_delta1 = p4_rank_t - p4_rank_lag1
p4_rank_delta3 = p4_rank_t - p4_rank_lag3
```

不得跨缺失月份 forward-fill，不得把最近一次可得值冒充 exact lag。

### 7.3 Exact ordered feature list

Primary full feature set 顺序冻结为：

```text
01 p4_rank_t
02 p4_rank_lag1
03 p4_rank_lag3
04 p4_rank_mean3
05 p4_rank_std3
06 p4_rank_delta1
07 p4_rank_delta3
08 p0_rank_t
09 p1_rank_t
10 p6_rank_t
11 p4_lag1_missing
12 p4_lag3_missing
13 p4_mean3_missing
14 p0_missing
15 p1_missing
16 p6_missing
```

Missing/imputation 固定为：

```text
rank / rolling-mean missing -> 0.5
rolling-std missing -> 0.0
delta missing -> 0.0
corresponding missing indicator -> 1
otherwise missing indicator -> 0
```

不使用 validation/robustness 统计量拟合 imputer 或 scaler。不得 winsorize、z-score、PCA、feature selection 或 target encoding。

### 7.4 Feature timing audit

`materialized/feature_lineage_audit.csv` 每个 feature-month 至少记录：

```text
feature_id
decision_date
source_arm_id
source_semantic_track
source_max_decision_date
source_outcome_field_read_count
finite_n
missing_n
status
blocking_reason
```

必须满足：

```text
source_max_decision_date <= decision_date
source_outcome_field_read_count = 0
```

任一 feature 违反即 `feature_timing_or_outcome_firewall_blocked`。

## 8. Model registry 与 deterministic fit

### 8.1 Baselines

```text
scored_model_id = B0_P4_RAW_RANK
model_family_id = NONTRAINABLE_P4_BASELINE
fit_id = null
score = p4_rank_t
trainable = false
selection_eligible = false
role = incumbent paired baseline
```

```text
scored_model_id = N0_HASH_NULL
model_family_id = NONTRAINABLE_HASH_NULL
fit_id = null
score = uint64(first_16_hex(SHA256(run_id|decision_date|instrument_id))) / (2^64-1)
trainable = false
selection_eligible = false
role = pipeline null diagnostic
```

Hash null 不得进入 model selection 或 gate；它只检查分桶/metric pipeline 是否会机械制造强单调。

### 8.2 Candidate M1：Ridge rank regression

```text
model_family_id = M1_RIDGE_RANK_REGRESSION
validation_scored_model_id = M1_RIDGE_RANK_REGRESSION
library = scikit-learn==1.9.0
estimator = sklearn.linear_model.Ridge
target = y_rank_pct
alpha = 10.0
fit_intercept = true
solver = svd
tol = 1e-12
positive = false
feature_order = Section 7.3 exact order
```

每个训练月份的 row weight：

```text
sample_weight_i,t = 1 / known_label_n_t
```

因此每个月对 loss 的总权重相同。系数必须以可精确 replay 的 CSV 输出：intercept 与每个 feature coefficient 各一行，按 feature order 保存，数值使用 `%.17g`；不得只保存不可审计 pickle，也不得套用普通 readout CSV 的 `%.12g`。

### 8.3 Candidate M2：LightGBM LambdaRank

```text
model_family_id = M2_LIGHTGBM_LAMBDARANK
validation_scored_model_id = M2_LIGHTGBM_LAMBDARANK
library = lightgbm==4.6.0
estimator = lightgbm.LGBMRanker
objective = lambdarank
metric = ndcg
eval_at = [10, 20, 50]
lambdarank_truncation_level = 50
label_gain = [0, 1, 3, 7, 15, 31, 63, 127, 255, 511]
n_estimators = 200
learning_rate = 0.03
num_leaves = 7
max_depth = 3
min_child_samples = 100
min_split_gain = 0.0
subsample = 1.0
subsample_freq = 0
colsample_bytree = 1.0
reg_alpha = 1.0
reg_lambda = 10.0
random_state = 20260714
n_jobs = 1
deterministic = true
force_col_wise = true
verbosity = -1
```

训练 rows 必须按 `(decision_date ASC, instrument_id ASC)` 排序；`group` 必须是每个 decision month 的 known-label row count。Sample weight 同 M1，使每个月总权重相同。

禁止 early stopping、validation continuation、Bayesian/grid/random search 或改变 boosting round。Model 必须保存为 LightGBM text model，并输出 tree/feature importance audit。

### 8.4 Dependency gate

运行环境固定通过：

```bash
cd topics/02_AFML_BIG_WINNER
uv run python ...
```

Preflight 必须验证 exact runtime：

```text
pyproject_sha256 = cd2d0cff7728be686b59ca14b63c35d6050af6b5ff3a2305fa2e50e606d8dd66
uv_lock_sha256 = 95b1c429f48b9ef1e950d1639334cdcc8633cb1536213e4f236b15e7b00b4e60
numpy = 1.26.4
pandas = 2.3.3
scipy = 1.17.1
lightgbm = 4.6.0
scikit-learn = 1.9.0
pyarrow = 24.0.0
```

Runner 不得执行 `pip install`、`uv add`、`uv lock` 或修改 dependency files。Lock hash 或 exact dependency mismatch 进入 `dependency_blocked`，不得静默跳过 M2 后把 M1 当成完整 candidate pool。HAC 按 Section 10.7 直接使用 NumPy/SciPy 公式实现，不依赖 ambient `statsmodels`。

### 8.5 Determinism

同一 sealed input/config 必须在两个独立 scratch roots 中完整运行至 historical readout seal：

```text
replay_a_scratch_root = output_root + ".__replay_a__"
replay_b_scratch_root = output_root + ".__replay_b__"
```

执行前 `output_root` 与两个 scratch roots 必须都不存在；任一已存在均 fail closed，不得删除、复用或覆盖。这是 run 创建前的 invocation refusal，不生成或覆盖 decision bundle，也不进入 Section 11 research terminal truth table。Replay A/B 使用相同 `run_id/contract_version/config bytes`，但 filesystem root 和 process identity 独立；不得共享 Python/model state、memory cache、temporary model file 或 RNG object。

两个 replay 完成后，parent controller 必须在读取任何 final decision/report 之前比较下列 canonical core outputs：

```text
feature_panel content hash identical
train_validation_label_panel content hash identical
robustness_label_panel content hash identical
candidate selection identical
all score float64 values identical within atol=1e-12, rtol=0
bucket assignment identical
all primary metric float64 values identical within atol=1e-12, rtol=0
historical terminal inputs identical
```

PID、UTC timestamp、scratch absolute path 和 worker-exit bytes 属于 audit-only non-comparable fields；不得混入上述 core content hash。Parent 把逐项比较结果写入 replay A 的 `determinism/determinism_comparison.csv`，并把 replay B 的 core relative-path hashes 写入 `determinism/replay_b_core_hashes.json`。任一 core mismatch 令 `determinism_gate=false`，但仍使用 replay A 生成 immutable failure decision bundle。

Replay A 是唯一 publication candidate；只有 comparison artifacts 写入且 final output registry形成后，才允许将 replay A atomic rename 为 `output_root`。Replay B 绝不发布；成功或失败 final bundle 已收录其 core hashes 后才允许清理 replay B scratch。不得以第二次执行覆盖第一次已发布 bundle。

若任一 replay 因更早的 upstream/firewall/dependency/stage-seal blocker 未到达 historical readout，parent 仍须对已存在的 registered core artifacts 写 comparison rows，并对未到达项写 `status=not_evaluable_due_to_prior_blocker`；不得把未执行伪装成 replay mismatch。Truth-table 按 Section 11 precedence 采用更早 blocker，`determinism_gate=false` 仅在两次 replay 都到达可比较状态而 core comparison 失败时生效。

### 8.6 Exact fit identity 与 artifact path

Fit registry 固定为：

| fit_id | model family | feature_set_id | fit label scope | score scope | artifact root |
|---|---|---|---|---|---|
| `M1_candidate_train` | M1 | `FULL_16` | train | validation | `selection/models/M1_candidate_train/` |
| `M2_candidate_train` | M2 | `FULL_16` | train | validation | `selection/models/M2_candidate_train/` |
| `selected_full_refit` | selected M1 or M2 | `FULL_16` | train+validation | robustness | `models/selected_full_refit/` |
| `A1_p4_path_only_refit` | selected M1 or M2 | `P4_PATH_ONLY` | train+validation | robustness | `models/A1_p4_path_only_refit/` |
| `A2_cross_signals_without_p4_refit` | selected M1 or M2 | `CROSS_SIGNALS_WITHOUT_P4` | train+validation | robustness | `models/A2_cross_signals_without_p4_refit/` |

Scoring identity 与 model family/fit identity 必须分离。冻结映射：

| split | scored_model_id | model_family_id | fit_id |
|---|---|---|---|
| validation | `B0_P4_RAW_RANK` | `NONTRAINABLE_P4_BASELINE` | null |
| validation | `N0_HASH_NULL` | `NONTRAINABLE_HASH_NULL` | null |
| validation | `M1_RIDGE_RANK_REGRESSION` | `M1_RIDGE_RANK_REGRESSION` | `M1_candidate_train` |
| validation | `M2_LIGHTGBM_LAMBDARANK` | `M2_LIGHTGBM_LAMBDARANK` | `M2_candidate_train` |
| robustness | `B0_P4_RAW_RANK` | `NONTRAINABLE_P4_BASELINE` | null |
| robustness | `N0_HASH_NULL` | `NONTRAINABLE_HASH_NULL` | null |
| robustness | `S0_SELECTED_FULL` | frozen selected M1 or M2 | `selected_full_refit` |
| robustness | `A1_P4_PATH_ONLY` | frozen selected M1 or M2 | `A1_p4_path_only_refit` |
| robustness | `A2_CROSS_SIGNALS_WITHOUT_P4` | frozen selected M1 or M2 | `A2_cross_signals_without_p4_refit` |

`scored_model_id` 是 score、bucket、return、metric 与 paired-readout 的唯一模型主键；`model_family_id` 只表示算法 family；`fit_id` 只表示训练实例。三者不得互相代用。Nontrainable rows 的 `fit_id` 与 `model_artifact_sha256` 必须是 JSON/Parquet null，但不得出现在 stable key 中。

`preflight/model_registry.csv` stable key 为 `(split, scored_model_id)`，必须恰有上表9行，并至少记录 `model_family_id`、`fit_id`、`model_role`、`feature_set_id`、`trainable`、`selection_eligible` 和 `score_scope`。对 `S0/A1/A2`，preflight 中的 `model_family_id` exact写为 `SELECTED_FAMILY_PLACEHOLDER`；下游只可用 sealed `candidate_selection.csv` 在内存中解析为 M1 或 M2，并在 model/score artifacts 记录解析后的 actual family。Preflight registry 本身不得改变，且解析不得改变 `scored_model_id/fit_id`。

Artifact filename 由 family 固定：

```text
M1 -> coefficients.csv
M2 -> model.txt
```

每个 fit root 必须含 `fit_contract.json`，至少记录：

```text
fit_id
model_family_id
feature_set_id
fit_split_scope
fit_row_n
fit_month_n
fit_max_label_decision_date
fit_call_count
update_or_continuation_call_count
robustness_feature_row_read_count
robustness_label_open_count
robustness_outcome_column_read_count
fit_row_key_hash
feature_order_hash
hyperparameter_hash
model_artifact_sha256
```

禁止复用、覆盖或软链接另一个 fit artifact。Candidate fit contract 的 audit 字段必须由 selection worker 在 fit 时写入，后续 worker 不得推断或回填。

`models/model_artifact_registry.csv` stable key 为 `fit_id`，至少包含：

```text
fit_id
model_family_id
feature_set_id
fit_split_scope
score_split_scope
artifact_relative_path
artifact_sha256
fit_contract_sha256
fit_row_n
fit_month_n
fit_max_label_decision_date
selection_bundle_hash
status
blocking_reason
```

## 9. Candidate selection、refit 与 ablation

### 9.1 Validation selection

M1/M2 各自在 train 30个月拟合一次，并在完整 validation 12个月上打分。Candidate selection 不允许使用 robustness 数据。

Selection 的全部 bucket return、Rank IC 和排序 key 只允许 `return_semantics=project_known_only_primary`；strict sensitivity、paper proxy 或任何其他 return semantics 均不得参与 candidate eligibility、排序或 tie-break。

排序 key 固定为：

```text
validation_aggregate_bucket_mean_spearman DESC
validation_adjacent_order_rate DESC
validation_mean_security_rank_ic DESC
model_complexity_order ASC
```

```text
model_complexity_order:
M1 = 1
M2 = 2
```

不得删除表现较差 candidate row。若 metric exact tie，选择 M1。

Validation eligibility 固定为：

```text
all required metrics finite
aggregate_bucket_mean_spearman > 0
mean_security_rank_ic > 0
D10_minus_D1 > 0
```

即使两个 candidate 都不 eligible，也必须按排序 key 记录 `best_available_candidate` 并完成 robustness diagnostic；但 `validation_selection_gate=false`，最终不得进入 near-monotonic 或 improved state。

### 9.2 Frozen robustness refit

唯一 selected family 使用 train+validation 42个月的 known labels 重拟合一次，hyperparameters、feature order 和 preprocessing 完全不变；随后一次性 score 21个 robustness months。

Robustness label 只能在 score file 已密封后由 fresh metric process join。Model fit/import audit 必须显示：

```text
robustness_label_read_count_during_fit = 0
robustness_rows_used_for_fit = 0
```

### 9.3 Frozen attribution ablations

使用 selected model family 和相同 hyperparameters，额外重拟合两个 diagnostic-only ablations：

```text
A1_P4_PATH_ONLY:
    features = 01..07 + 11..13

A2_CROSS_SIGNALS_WITHOUT_P4:
    features = 08..10 + 14..16
```

Ablation 不参与 candidate selection 或 terminal gate。解释必须逐 metric 使用 Section 12.9 的 full/A1/A2 数值和相对 B0 delta，不得使用未冻结的“接近”“较弱”或 composite attribution threshold。若 A2 在某个 metric 上等于或超过 full，只允许写成“该 metric 的改善不依赖 P4 path”；无论 A1/A2 结果如何，都不得作因果声明或把 full success 写成 P4 单因子修复。

## 10. Sorting、bucket return 与 monotonicity metrics

### 10.1 Learned-score 分桶

每个 model × decision month 在完整 P4 base population上：

1. 要求 model score finite；
2. 按 `(model_score ASC, instrument_id ASC)` 稳定排序；
3. `rank = 1..N`；
4. `bucket_id = 1 + floor((rank-1) * 10 / N)`；
5. D1 是最低预测收益桶，D10 是最高预测收益桶；
6. 每桶 ex-ante membership 与权重不得受 next-month known/unknown 影响。

所有模型必须在相同 P4 base rows 上分桶。不得为了得到更单调曲线删除 score 中间区域、改为固定 Top-N、改 bucket edge 或合并相邻桶。

### 10.2 Bucket return

对 primary known-only readout：

```text
R_model,t,b = mean(project_resolved_next_month_return_i,t
                   over known rows assigned to bucket b)
```

每个月同时计算：

```text
common_return_t = mean(project return over all known P4 base rows)
centered_bucket_return_t,b = R_model,t,b - common_return_t
```

Raw 与 centered bucket 在同月的 ordering 必须完全相同。Primary monotonicity metrics 使用 centered return，以明确剥离不影响排序的共同状态；raw return 仍完整输出供审计。

### 10.3 Security-level Rank IC

对每个可评价月：

```text
security_rank_ic_t = Spearman(model_score_i,t, project_return_i,t+1)
```

只在 paired known rows 上计算，tie 使用 average rank。输出：

```text
mean
median
std
positive_month_rate
HAC mean t/p with lag=3
minimum / maximum
```

### 10.4 Aggregate bucket curve

先按月份等权计算每桶均值：

```text
mu_b = mean(centered_bucket_return_t,b over common evaluable months)
```

Primary metrics：

```text
aggregate_bucket_mean_spearman = Spearman([1..10], [mu_1..mu_10])
adjacent_order_count = count(mu_(b+1) > mu_b for b=1..9)
adjacent_order_rate = adjacent_order_count / 9
strict_monotonic_curve = all(mu_(b+1) > mu_b)
D10_minus_D1 = mu_10 - mu_1
D10_minus_middle = mu_10 - mean(mu_2..mu_9)
maximum_adjacent_inversion = max(mu_b - mu_(b+1), 0)
```

Equal adjacent means不算 ordered；必须记录 zero-difference pair。

### 10.5 Monthly bucket morphology

每月计算：

```text
monthly_bucket_spearman_t = Spearman([1..10], [R_t,1..R_t,10])
monthly_adjacent_order_rate_t
monthly_D10_minus_D1_t
```

输出 mean/median/positive rate 和前后半段。不得要求每个月 strict monotonic；该指标用于稳定性而不是逐月硬约束。

### 10.6 Invariance tests

实现必须证明：

1. 对同月十桶 return 加任意常数，所有 ordering metric 不变；
2. 一个所有桶均为负但 `D1 < ... < D10 < 0` 的 synthetic case 通过 monotonicity metric；
3. 一个所有桶均为正但顺序随机的 synthetic case不得通过；
4. isotonic/post-hoc curve 不进入 primary score、bucket 或 gate。

### 10.7 Paired model delta 与 uncertainty

Validation 的 M1/M2/B0 delta，以及 robustness 的 selected full/A1/A2/B0 delta，必须分别在相应 split 的 exact common months 和 exact common known rows上计算；未选 candidate 不允许用 train-only artifact 越级生成 robustness delta：

```text
delta_aggregate_bucket_mean_spearman
delta_adjacent_order_rate
delta_mean_security_rank_ic
delta_D10_minus_D1
```

Inference 只作为 design-only uncertainty。Moving-block bootstrap 精确实现：

```text
input_months = paired common evaluable months ascending
n = len(input_months)
block_length = 3
candidate_block_starts = 0..n-block_length
block = three consecutive positional month indices; non-circular
blocks_per_replicate = ceil(n / block_length)
rng = numpy.random.Generator(numpy.random.PCG64(20260714))
for each of 5000 replicates:
    sample block starts iid with replacement
    concatenate sampled blocks in draw order
    truncate to first n positional indices
    retain duplicate sampled months with multiplicity
    recompute challenger and B0 curves on identical sampled indices
    recompute each paired delta from scratch
quantile_method = numpy.quantile(method="linear")
reported_percentiles = [0.05, 0.50, 0.95]
CI_interpretation = two_sided_90pct_percentile_interval
```

`n < 3`、nonfinite replicate metric 或不足5000个 finite replicates 必须使对应 confidence field missing 并记录原因。Bootstrap unit 必须是 month block；禁止 instrument-row bootstrap，禁止对预先聚合的单一 delta 加噪声。

HAC 对按 decision month 升序的 `security_rank_ic_t` 和 paired `rank_ic_delta_t` 分别做 intercept-only mean test，不允许由 library default 决定：

```text
L = min(3, month_n - 1)
gamma_h = sum((x_t-mean_x)*(x_(t-h)-mean_x) for t=h+1..n) / month_n
Bartlett_weight_h = 1 - h/(L+1)
variance_of_mean = (gamma_0 + 2*sum(Bartlett_weight_h*gamma_h for h=1..L)) / month_n
finite_sample_correction = none
HAC_t_stat = mean_x / sqrt(variance_of_mean)
HAC_two_sided_p = 2 * scipy.stats.norm.sf(abs(HAC_t_stat))
month_n < 2 or variance_of_mean <= 0/nonfinite -> HAC fields missing with reason
```

## 11. Exact gates 与 decision truth table

### 11.1 Integrity gates

下列 upstream/firewall/split/model/score/stage-seal gates 必须在 replay A 与 replay B 分别计算后取 logical AND；任一 replay 失败即整体 gate=false。Metric point estimates 与最终报告数值只取 publication candidate replay A，但必须先通过 determinism comparison。

```text
upstream_integrity_gate =
    all required v5 hashes/schema/counts exact

outcome_firewall_gate =
    preflight outcome reads = 0
    and feature-worker outcome reads = 0
    and paper_proxy_next_month_return reads/materializations = 0 in every stage
    and selection-worker robustness label/outcome reads = 0
    and refit-worker robustness feature/label/outcome reads = 0
    and score-worker any label opens = 0
    and score-worker fit/update/transform-fit calls = 0
    and metric-worker robustness label opens only after score seal verified
    and metric-worker fit/update/selection/transform-fit calls = 0

split_integrity_gate =
    exact date boundaries/counts
    and no decision month crosses split
    and robustness rows used for fit = 0

model_registry_gate =
    B0/N0 nontrainable definitions registered
    and M1/M2 candidate artifacts materialized
    and selected_full/A1/A2 refit artifacts materialized
    and exact dependency/hyperparameters
    and no unregistered candidate/search
    and five registered fit IDs have unique artifact paths
    and selected/A1/A2 family equals frozen selected family

score_integrity_gate =
    validation scored_model_id set exact equals
        {B0_P4_RAW_RANK, N0_HASH_NULL,
         M1_RIDGE_RANK_REGRESSION, M2_LIGHTGBM_LAMBDARANK}
    and validation score row_n = 4 * 5,107 = 20,428
    and robustness scored_model_id set exact equals
        {B0_P4_RAW_RANK, N0_HASH_NULL, S0_SELECTED_FULL,
         A1_P4_PATH_ONLY, A2_CROSS_SIGNALS_WITHOUT_P4}
    and robustness score row_n = 5 * 9,300 = 46,500
    and each scored model key set exact equals its split P4 base key set
    and no missing/extra/duplicate score or bucket-assignment rows
    and every model_score finite
    and every row assigned to exactly one bucket in 1..10

stage_seal_integrity_gate =
    for each replay in {replay_a, replay_b},
    for every reached stage in
        {preflight, materialized, pre_robustness_selection,
         model, score, historical_readout}:
        parent-written worker exit status valid where applicable
        and manifest payload path/hash set exact
        and output-hashes registry path/hash set exact
        and bundle hash recomputes from exact registry bytes
        and prior-stage bundle hash chain exact
        and no current-stage self hash or self-exit hash reference
    and an unreached later stage caused by an earlier terminal blocker
        is not treated as a seal failure

determinism_gate = all Section 8.5 checks pass

sample_support_gate =
    train_month_n = 30
    and validation_scheduled_month_n = 12
    and validation_evaluable_month_n >= 10
    and robustness_scheduled_month_n = 21
    and robustness_evaluable_month_n >= 18
    and robustness_early_evaluable_month_n >= 8
    and robustness_late_evaluable_month_n >= 9

metric_materialization_gate =
    all registered B0/N0/M1/M2 validation metrics finite
    and B0/N0/S0/A1/A2 robustness full/early/late primary metrics finite
    and all paired primary delta metrics finite
    and every scheduled scored-model/split/return-semantics metric row
        either finite or carries an allowed outcome-coverage/sample exclusion
    and no score nonfinite/missing/duplicate condition is mapped to exclusion
```

### 11.2 Validation selection gate

```text
validation_selection_gate =
    selected candidate satisfies Section 9.1 validation eligibility
```

### 11.3 Robustness ordering-improvement gate

在 robustness 21个月 paired primary readout 上：

```text
ordering_improvement_gate =
    stage_seal_integrity_gate
    and upstream_integrity_gate
    and outcome_firewall_gate
    and split_integrity_gate
    and model_registry_gate
    and score_integrity_gate
    and determinism_gate
    and validation_selection_gate
    and sample_support_gate
    and metric_materialization_gate
    and selected.aggregate_bucket_mean_spearman > 0
    and selected.aggregate_bucket_mean_spearman
        > B0.aggregate_bucket_mean_spearman
    and selected.adjacent_order_rate
        > B0.adjacent_order_rate
    and selected.mean_security_rank_ic > 0
    and selected.mean_security_rank_ic
        > B0.mean_security_rank_ic
    and selected.D10_minus_D1 > 0
    and robustness_early.aggregate_bucket_mean_spearman > 0
    and robustness_late.aggregate_bucket_mean_spearman > 0
```

Gate 不含任何 absolute-return positivity condition。

### 11.4 Near-monotonic gate

```text
near_monotonic_gate =
    ordering_improvement_gate
    and robustness.aggregate_bucket_mean_spearman >= 0.80
    and robustness.adjacent_order_count >= 8
    and robustness.maximum_adjacent_inversion
        <= 0.25 * abs(robustness.D10_minus_D1)
```

`strict_monotonic_curve=true` 是更强的 descriptive flag，不是 near-monotonic 必要条件。

### 11.5 Confidence strength flag

不改变 terminal state，但必须输出：

```text
paired_rank_ic_delta_two_sided_90pct_CI_lower_gt_zero
paired_bucket_spearman_delta_two_sided_90pct_CI_lower_gt_zero
```

两者都 true 才允许写 `bootstrap_directionally_supported_within_contaminated_design`；否则不得声称 bootstrap 已共同支持两个 primary ordering deltas。

`bootstrap_confidence_strength_flag` exact mapping：

```text
confidence inputs missing/nonfinite
    -> confidence_not_evaluable
both registered CI lower-bound flags true
    -> bootstrap_directionally_supported_within_contaminated_design
otherwise
    -> point_estimate_not_jointly_bootstrap_supported
```

### 11.6 Terminal state

所有 gate 字段是 nullable boolean：已执行且通过为 `true`，已执行且失败为 `false`，因更早 blocker 未到达则为 null。Terminal precedence 选择第一个已执行的 false gate；不得把未执行/null 当作 false，也不得让 later-stage null 覆盖 earlier blocker。所有非 blocked success/weak/no-improvement states 要求其列出的 gates 全部显式为 true。

Truth-table precedence：

1. `20B_P4_MLRANK_stage_seal_integrity_blocked`
2. `20B_P4_MLRANK_upstream_input_integrity_blocked`
3. `20B_P4_MLRANK_outcome_firewall_or_split_blocked`
4. `20B_P4_MLRANK_dependency_training_or_score_pipeline_blocked`
5. `20B_P4_MLRANK_metric_materialization_blocked`
6. `20B_P4_MLRANK_sample_support_underpowered`
7. `20B_P4_MLRANK_near_monotonic_multifactor_historical_design_observed`
8. `20B_P4_MLRANK_multifactor_ordering_improved_not_near_monotonic`
9. `20B_P4_MLRANK_multifactor_weak_or_unstable_improvement`
10. `20B_P4_MLRANK_no_multifactor_ordering_improvement`

定义：

```text
stage_seal_integrity_blocked:
    any reached stage fails stage_seal_integrity_gate

upstream_input_integrity_blocked:
    stage_seal_integrity_gate=true for reached preflight artifacts
    and upstream_integrity_gate=false

outcome_firewall_or_split_blocked:
    stage-seal/upstream gates pass
    and (outcome_firewall_gate=false or split_integrity_gate=false)

dependency_training_or_score_pipeline_blocked:
    stage-seal/upstream/outcome-firewall/split gates pass
    and (model_registry_gate=false
         or score_integrity_gate=false
         or determinism_gate=false)

metric_materialization_blocked:
    stage-seal/upstream/outcome-firewall/split/model/score/determinism gates pass
    and metric_materialization_gate=false

sample_support_underpowered:
    stage-seal/upstream/outcome-firewall/split/model/score/determinism/metric gates pass
    and sample_support_gate=false

near_monotonic_multifactor_historical_design_observed:
    all stage-seal/upstream/outcome-firewall/split/model/score/
        determinism/metric/sample gates pass
    and near_monotonic_gate=true

multifactor_ordering_improved_not_near_monotonic:
    all stage-seal/upstream/outcome-firewall/split/model/score/
        determinism/metric/sample gates pass
    and ordering_improvement_gate=true
    and near_monotonic_gate=false

multifactor_weak_or_unstable_improvement:
    all stage-seal/upstream/outcome-firewall/split/model/score/
        determinism/metric/sample gates pass
    and ordering_improvement_gate=false
    and at least one paired robustness ordering delta > 0

no_multifactor_ordering_improvement:
    all stage-seal/upstream/outcome-firewall/split/model/score/
        determinism/metric/sample gates pass
    and ordering_improvement_gate=false
    and no primary paired robustness ordering delta > 0
```

无论 terminal state：

```text
historical_support_claim_allowed = false
true_forward_support_claim_allowed = false
cash_or_bond_gate_authorized = false
20C_requirement_generation_authorized = false
20C_execution_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
next_allowed_requirement = none
research_scope = cross_signal_learned_reranker_on_p4_eligible_universe
multi_factor_model_allowed = true
P4_single_factor_repair_claim_allowed = false
```

## 12. Required artifacts 与 schemas

### 12.1 Artifact inventory

至少生成：

```text
preflight/contract_snapshot.json
preflight/upstream_input_integrity_audit.csv
preflight/split_registry.csv
preflight/feature_registry.csv
preflight/model_registry.csv
preflight/preflight_manifest.json
preflight/preflight_output_hashes.json

materialized/feature_panel.parquet
materialized/feature_lineage_audit.csv
materialized/train_validation_label_panel.parquet
materialized/robustness_label_panel.parquet
materialized/label_resolution_audit.csv
materialized/materialized_manifest.json
materialized/materialized_output_hashes.json

selection/models/M1_candidate_train/coefficients.csv
selection/models/M1_candidate_train/fit_contract.json
selection/models/M2_candidate_train/model.txt
selection/models/M2_candidate_train/fit_contract.json
selection/candidate_validation_scores.parquet
selection/candidate_validation_bucket_assignment.parquet
selection/candidate_validation_metrics.csv
selection/candidate_selection.csv
selection/candidate_fit_audit.csv
selection/selection_access_audit.csv
selection/selection_worker_exit.json
selection/pre_robustness_selection_manifest.json
selection/pre_robustness_selection_output_hashes.json

models/selected_full_refit/{selected_artifact_filename}
models/selected_full_refit/fit_contract.json
models/A1_p4_path_only_refit/{selected_artifact_filename}
models/A1_p4_path_only_refit/fit_contract.json
models/A2_cross_signals_without_p4_refit/{selected_artifact_filename}
models/A2_cross_signals_without_p4_refit/fit_contract.json
models/model_artifact_registry.csv
models/model_fit_audit.csv
models/model_feature_importance.csv
models/refit_access_audit.csv
models/refit_worker_exit.json
models/model_bundle_manifest.json
models/model_bundle_output_hashes.json

scores/robustness_model_score_panel.parquet
scores/robustness_model_bucket_assignment.parquet
scores/score_worker_access_audit.csv
scores/score_worker_exit.json
scores/score_bundle_manifest.json
scores/score_bundle_output_hashes.json

historical/model_bucket_monthly_returns.csv.gz
historical/top_bucket_turnover_monthly.csv
historical/security_rank_ic_monthly.csv
historical/monotonicity_readout.csv
historical/paired_model_delta.csv
historical/block_bootstrap_readout.csv
historical/ablation_readout.csv
historical/metric_worker_access_audit.csv
historical/metric_worker_exit.json
historical/historical_manifest.json
historical/historical_output_hashes.json

determinism/determinism_comparison.csv
determinism/replay_b_core_hashes.json

20B_P4_learned_monotonic_return_ranking_diagnostic_decision.csv
20B_P4_learned_monotonic_return_ranking_diagnostic_report.md
manifest_20b_p4_mlrank.json
output_hashes_20b_p4_mlrank.json
```

`{selected_artifact_filename}` 是条件互斥占位符，不是 literal path：若 frozen selected family=M1，三个 refit root 必须各自只含 `coefficients.csv` 且禁止 `model.txt`；若 selected family=M2，必须各自只含 `model.txt` 且禁止 `coefficients.csv`。Manifest/output-hashes registry 只登记实际允许的 exact path；同时出现两种文件或缺失所选文件均 fail closed。

### 12.2 `feature_panel.parquet`

Stable key：`(decision_date, instrument_id)`。

必须包含：

```text
run_id
decision_date
label_month
instrument_id
split
p4_base_eligible
16 Section 7.3 feature columns in exact order
feature_max_source_decision_date
feature_outcome_read_count
upstream_input_snapshot_hash
```

禁止包含任何 return、outcome、bucket outcome evaluability 或 future membership field。

### 12.3 Label panels

下列两个独立文件使用相同 schema 和 stable key `(decision_date, instrument_id)`：

```text
materialized/train_validation_label_panel.parquet
materialized/robustness_label_panel.parquet
```

```text
decision_date
label_month
instrument_id
split
project_resolved_next_month_return
outcome_resolution
label_known
y_rank_pct
y_relevance
known_label_n_in_month
label_source_hash
```

Unknown rows必须存在且 `label_known=false`、rank/relevance missing。

`materialized/label_resolution_audit.csv` 必须记录 project label source path/hash、project outcome column read count，以及 `paper_proxy_column_read_count=0`、`paper_proxy_column_materialized_count=0`。任一非零即 outcome-firewall failure。

Split 内容 exact：

```text
train_validation_label_panel split in {train, validation}
robustness_label_panel split = robustness only
```

Candidate fit/selection/refit/score process 读取后者必须由 access audit 判定为 firewall violation；只有 score/model bundle seal 后启动的 fresh metric-worker 可读取。

### 12.4 Pre-robustness selection bundle schemas

`selection/candidate_validation_scores.parquet` stable key：`(scored_model_id, decision_date, instrument_id)`；只允许 `split=validation`，至少包含：

```text
scored_model_id
model_family_id
fit_id
model_role
feature_set_id
decision_date
label_month
instrument_id
model_score
score_finite
fit_max_label_decision_date
model_artifact_sha256
robustness_label_open_count
```

必须包含 B0/N0/M1/M2 全部 validation rows；B0/N0 的 `fit_id/model_artifact_sha256` 为 null 并标记 nontrainable。

`selection/candidate_validation_bucket_assignment.parquet` stable key 同样为 `(scored_model_id, decision_date, instrument_id)`，必须恰有20,428行；除 score-panel identity/key 字段外至少包含 `model_score_rank`、`bucket_id`、`nominal_bucket_n`，不得包含任何 return/outcome/resolution column。Validation metrics 只能由该 exact assignment content 与 validation labels join 后生成，并记录 assignment content hash；不得另算另一套 bucket membership。

`selection/candidate_validation_metrics.csv` stable key：`(scored_model_id, return_semantics)`，只允许 `return_semantics=project_known_only_primary`，至少包含 `validation_bucket_assignment_content_hash`、Section 9.1 三个 selection metrics、D10/D1 curve、evaluable month N、candidate eligibility、selection sort values 和 rank。Selection sort 只允许比较 M1/M2；B0/N0 必须完整输出但 `candidate_eligible=false`、`selection_rank=null`。

`selection/candidate_selection.csv` 必须唯一一行：

```text
run_id
contract_version
selection_split
candidate_n
selected_model_family_id
selected_robustness_scored_model_id
selected_candidate_fit_id
selected_candidate_artifact_sha256
selected_validation_bucket_spearman
selected_validation_adjacent_order_rate
selected_validation_mean_rank_ic
validation_selection_gate
selection_sort_key
robustness_label_open_count
selection_status
blocking_reason
```

`selected_robustness_scored_model_id` 固定为 `S0_SELECTED_FULL`；它不是 candidate family ID，也不是 candidate fit ID。

`candidate_selection.csv` 不得引用尚未形成的 `selection_worker_exit_sha256` 或本 selection bundle 自身 hash。Parent-written exit record 及其 hash 只能由后续 selection manifest/output-hashes registry 收录。

`selection/candidate_fit_audit.csv` stable key 为 `fit_id`，必须恰有 `M1_candidate_train` 与 `M2_candidate_train` 两行，并使用 Section 12.5 `model_fit_audit.csv` 的相同字段集合。每一行必须与对应 candidate `fit_contract.json` exact-match，且固定：

```text
fit_split_scope = train
fit_month_n = 30
fit_call_count = 1
update_or_continuation_call_count = 0
robustness_feature_row_read_count = 0
robustness_label_open_count = 0
robustness_outcome_column_read_count = 0
status = pass
```

`selection/selection_access_audit.csv` stable key：`(worker_id, path_role, path)`，至少包含：

```text
worker_id
process_pid
path_role
path
allowed
open_count
bytes_read
outcome_column_read_count
fit_call_count
score_call_count
status
blocking_reason
```

`selection/selection_worker_exit.json` 由 parent 在 child 已退出后写入，必须记录 pid、started/ended UTC、exit code、worker output hashes、robustness-label open/read count 和 parent observation timestamp。Selection worker 不得自行写自己的 exit record。

### 12.5 Model/refit audit schemas

`models/model_artifact_registry.csv` 使用 Section 8.6 exact schema，必须有5个 fit rows；`fit_id` 与 artifact path 必须各自唯一，每个 artifact 均记录并验证 SHA256。不同 fit bytes 偶然相同不是错误，但仍不得复用 path、软链接或覆盖。

`models/model_fit_audit.csv` stable key：`fit_id`，至少包含：

```text
fit_id
model_family_id
feature_set_id
fit_split_scope
fit_row_n
fit_month_n
fit_max_label_decision_date
fit_call_count
update_or_continuation_call_count
robustness_feature_row_read_count
robustness_label_open_count
robustness_outcome_column_read_count
fit_row_key_hash
feature_order_hash
hyperparameter_hash
artifact_sha256
status
blocking_reason
```

全部5个 fit identity 都必须可审计；candidate 两行必须从 sealed `selection/candidate_fit_audit.csv` 逐字段机械复制并重新验证对应 fit contract，三个 refit 行来自本 worker。对三个 refit 行，`fit_call_count=1`、`update_or_continuation_call_count=0`、`robustness_feature_row_read_count=0`、`robustness_label_open_count=0`、`robustness_outcome_column_read_count=0`。

`models/refit_access_audit.csv` 使用与 selection access audit 相同的 path-level schema，并额外记录 `pre_robustness_selection_bundle_hash_verified`。`models/refit_worker_exit.json` 只能由 parent 在 child 退出后写入；refit worker 不得自行写 exit record。

`models/model_feature_importance.csv` stable key 为 `(fit_id, feature_id, importance_type)`，只允许三个 refit fit IDs，至少包含：

```text
fit_id
model_family_id
feature_set_id
feature_id
feature_order
importance_type
importance_value
feature_present
artifact_sha256
status
blocking_reason
```

M1 对每个实际 feature 输出 `signed_coefficient` 与 `absolute_coefficient` 两行，intercept 使用独立 `feature_id=__INTERCEPT__` 且只输出 signed value；M2 对每个实际 feature 输出 `gain` 与 `split_count` 两行。未包含于 A1/A2 feature set 的 feature 不得伪造零 importance row。

### 12.6 `scores/robustness_model_score_panel.parquet`

Stable key：`(scored_model_id, decision_date, instrument_id)`。

```text
scored_model_id
model_family_id
fit_id
model_role
split
decision_date
label_month
instrument_id
model_score
score_finite
fit_max_label_decision_date
robustness_label_read_during_fit
feature_set_id
model_artifact_sha256
pre_robustness_selection_bundle_hash
model_bundle_hash
```

对 `selected_full_refit/A1/A2`，`fit_max_label_decision_date < minimum scored decision_date` 必须成立；B0/N0 的 fit date 必须为空且 `model_role` 标记为 nontrainable。未被选中的 M1/M2 candidate 不得在 robustness score panel 中伪装成 full refit。

`scores/robustness_model_bucket_assignment.parquet` 只能由 score 和 P4 base population形成，不得包含 outcome return/resolution；stable key 为 `(scored_model_id, decision_date, instrument_id)`，并至少保存 `model_family_id`、`fit_id`、`model_score_rank`、`bucket_id`、`nominal_bucket_n`、`pre_robustness_selection_bundle_hash` 和 `model_bundle_hash`。

任何 score payload 文件都不得包含本 score bundle 自身的 `score_bundle_hash`。Fresh metric-worker 必须先验证 `score_bundle_manifest.json` 与 `score_bundle_output_hashes.json`，再读取 robustness label。

`scores/score_worker_access_audit.csv` 使用 path-level stable key `(worker_id, path_role, path)`，除 Section 12.4 access 字段外至少增加：

```text
model_bundle_hash_verified
any_label_open_count
fit_call_count
update_or_continuation_call_count
feature_transform_fit_call_count
status
blocking_reason
```

必须满足 `model_bundle_hash_verified=true` 且所有 label-open/fit/update/transform-fit count 为0。`scores/score_worker_exit.json` 只能由 parent 在 child 退出后写入；score worker 不得自行写 exit record。

### 12.7 `model_bucket_monthly_returns.csv.gz`

Stable key：`(scored_model_id, split, decision_date, return_semantics, bucket_id)`。

```text
scored_model_id
model_family_id
fit_id
split
decision_date
label_month
return_semantics
bucket_id
nominal_n
known_n
unknown_n
known_coverage_rate
raw_bucket_return
common_return
centered_bucket_return
month_evaluable
exclusion_reason
```

`return_semantics` 只允许：

```text
project_known_only_primary
project_all_resolved_strict_sensitivity
```

`historical/top_bucket_turnover_monthly.csv` stable key 为 `(scored_model_id, split, decision_date)`，只允许 `split=robustness`，对 robustness 的五个 scored models × 21个月全量输出，固定105行。对相邻 scheduled robustness decision months，以各月 D10 等权权重定义：

```text
w_i,t = 1 / D10_member_n_t if instrument i in D10_t else 0
one_way_top_bucket_turnover_t =
    0.5 * sum(abs(w_i,t - w_i,t-1) over union of the two D10 sets)
```

至少包含 `prior_decision_date`、`D10_member_n`、`prior_D10_member_n`、`overlap_n`、`one_way_top_bucket_turnover`、`turnover_finite` 和 `exclusion_reason`。每个 scored model 的 robustness 首月保留一行、turnover missing、`exclusion_reason=no_prior_scheduled_month`；其余100行 turnover 必须 finite 且位于 `[0,1]`。不得跨缺失 scheduled month配对。Turnover 只作 descriptive capacity warning，不进入 selection 或 terminal gate。

### 12.8 `monotonicity_readout.csv`

Stable key：`(scored_model_id, split_scope, return_semantics)`。

```text
scored_model_id
model_family_id
fit_id
split_scope
return_semantics
scheduled_month_n
evaluable_month_n
mean_security_rank_ic
median_security_rank_ic
security_rank_ic_positive_month_rate
HAC_t_stat
HAC_p_value
aggregate_bucket_mean_spearman
adjacent_order_count
adjacent_order_rate
strict_monotonic_curve
D10_minus_D1
D10_minus_middle
maximum_adjacent_inversion
mean_monthly_bucket_spearman
monthly_bucket_spearman_positive_rate
absolute_return_positivity_used_in_gate
inference_role
```

`absolute_return_positivity_used_in_gate` 必须恒为 `false`。

`historical/security_rank_ic_monthly.csv` stable key 为 `(scored_model_id, split, decision_date, return_semantics)`，至少包含 `model_family_id`、`fit_id`、`label_month`、`paired_known_n`、`security_rank_ic`、`rank_ic_finite` 和 `exclusion_reason`；HAC 输入必须由该文件按 decision date 升序机械重放。

### 12.9 `paired_model_delta.csv`

```text
challenger_scored_model_id
baseline_scored_model_id
split_scope
common_month_n
common_instrument_month_n
metric_id
challenger_value
baseline_value
paired_delta
delta_direction_favorable
```

`historical/block_bootstrap_readout.csv` stable key 为 `(challenger_scored_model_id, baseline_scored_model_id, split_scope, metric_id)`，至少包含：

```text
challenger_scored_model_id
baseline_scored_model_id
split_scope
metric_id
common_month_n
block_length
candidate_block_start_n
blocks_per_replicate
seed
requested_replicate_n
finite_replicate_n
quantile_method
p05
p50
p95
two_sided_CI_level
CI_lower_gt_zero
status
exclusion_reason
```

固定 `block_length=3`、`seed=20260714`、`requested_replicate_n=5000`、`quantile_method=linear`、`two_sided_CI_level=0.90`；`p05/p95` 分别是 CI lower/upper，不得改称单侧95%界。

`historical/ablation_readout.csv` stable key 为 `(split_scope, return_semantics, metric_id)`，只允许 robustness `full/early/late`、两种 registered return semantics，以及以下 metric set：

```text
aggregate_bucket_mean_spearman
adjacent_order_rate
mean_security_rank_ic
D10_minus_D1
```

至少包含 `selected_model_family_id`、`baseline_scored_model_id=B0_P4_RAW_RANK`、`full_scored_model_id=S0_SELECTED_FULL`、`A1_scored_model_id=A1_P4_PATH_ONLY`、`A2_scored_model_id=A2_CROSS_SIGNALS_WITHOUT_P4`、`baseline_value`、`full_value`、`A1_value`、`A2_value`、`full_minus_baseline`、`A1_minus_baseline`、`A2_minus_baseline`、`A1_minus_full`、`A2_minus_full`、`favorable_direction` 和 `status`。不得输出未经阈值冻结的 composite attribution label。

上述四个 registered ablation metrics 的 `favorable_direction` 均固定为 `higher_is_better`；所有 delta 均按“左侧模型值减右侧模型值”计算。

`historical/metric_worker_access_audit.csv` stable key 为 `(worker_id, path_role, path)`，至少包含：

```text
worker_id
process_pid
path_role
path
allowed
open_count
bytes_read
score_bundle_manifest_verified
score_bundle_hash_verified
robustness_label_column_read_count
fit_call_count
update_or_continuation_call_count
candidate_selection_call_count
feature_transform_fit_call_count
status
blocking_reason
```

只有 `score_bundle_manifest_verified=true` 且 `score_bundle_hash_verified=true` 后，robustness label open/read count 才允许大于0；所有 mutation call count 必须为0。`historical/metric_worker_exit.json` 只能由 parent 在 child 退出后写入，并记录 pid、started/ended UTC、exit code、worker payload hashes 和 parent observation timestamp。

### 12.10 Determinism artifacts

`determinism/determinism_comparison.csv` stable key 为 `(artifact_role, comparison_id)`，至少包含：

```text
artifact_role
comparison_id
replay_a_relative_path
replay_b_relative_path
replay_a_content_hash
replay_b_content_hash
comparison_method
atol
rtol
row_n_a
row_n_b
key_set_equal
value_equal
status
blocking_reason
```

Hash-exact artifacts 使用 `comparison_method=sha256_exact`、`atol=rtol=0`；float score/metric artifacts 使用 stable-key sort 后的 `float64_allclose`，固定 `atol=1e-12, rtol=0`，并同时要求 schema、row count、key set 和 non-float columns exact。`determinism/replay_b_core_hashes.json` 是 relative POSIX path 到 lowercase SHA256 的 canonical flat mapping，只允许 Section 8.5 registered core artifacts。

### 12.11 Decision CSV

唯一一行，至少包含：

```text
run_id
contract_version
decision_state
research_scope
multi_factor_model_allowed
P4_single_factor_repair_claim_allowed
historical_sample_role
claim_ceiling
execution_authority
separate_human_execution_authorization_required
requirement_execution_authorized
implementation_authorized
historical_outcome_execution_authorized
model_training_authorized
stage_seal_integrity_gate
stage_seal_failure_replay
stage_seal_failure_stage
upstream_integrity_gate
outcome_firewall_gate
split_integrity_gate
model_registry_gate
score_integrity_gate
determinism_gate
sample_support_gate
metric_materialization_gate
validation_selection_gate
selected_model_family_id
selected_scored_model_id
baseline_scored_model_id
validation_selected_metric
robustness_evaluable_month_n
baseline_robustness_bucket_spearman
selected_robustness_bucket_spearman
delta_robustness_bucket_spearman
baseline_robustness_adjacent_order_rate
selected_robustness_adjacent_order_rate
delta_robustness_adjacent_order_rate
baseline_robustness_mean_rank_ic
selected_robustness_mean_rank_ic
delta_robustness_mean_rank_ic
selected_robustness_D10_minus_D1
ordering_improvement_gate
near_monotonic_gate
bootstrap_confidence_strength_flag
absolute_return_positivity_required
cash_or_bond_gate_authorized
pre_robustness_selection_bundle_hash
model_bundle_hash
score_bundle_hash
historical_readout_bundle_hash
historical_support_claim_allowed
20C_requirement_generation_authorized
deployment_authorized
next_allowed_requirement
blocking_reason
```

固定：

```text
research_scope = cross_signal_learned_reranker_on_p4_eligible_universe
multi_factor_model_allowed = true
P4_single_factor_repair_claim_allowed = false
execution_authority = workspace_user_direct_instruction_2026-07-14
separate_human_execution_authorization_required = false
requirement_execution_authorized = true
implementation_authorized = true
historical_outcome_execution_authorized = true
model_training_authorized = true
absolute_return_positivity_required = false
cash_or_bond_gate_authorized = false
historical_support_claim_allowed = false
20C_requirement_generation_authorized = false
deployment_authorized = false
```

`selected_scored_model_id` 在 pre-robustness selection/model/score chain 已形成时固定为 `S0_SELECTED_FULL`；`baseline_scored_model_id` 同期固定为 `B0_P4_RAW_RANK`；若更早 stage 阻塞则二者均为 null。`stage_seal_failure_replay` 只允许 `replay_a/replay_b`，`stage_seal_failure_stage` 只允许上述六个 seal stage ID；无 seal failure 时二者均为 null。

## 13. Report contract

中文报告必须至少包含：

1. 一页结论和 terminal state；
2. 明确写出本轮是 P4 eligible universe 上的 cross-signal 多因子 reranker，不是 P4 单因子修复，并写出“不要求中间桶或任何桶绝对为正”；
3. 当前 workspace 用户直接执行授权、不需要独立审批文件，以及仍然有效的 outcome-contaminated claim boundary；
4. 63个月和三段 split；
5. Validation 展示 B0/N0/M1/M2 全量表；robustness 展示 B0/N0/selected full/A1/A2 全量表，不得把未选 candidate 的 train-only artifact 伪装成 robustness model；
6. validation selection 与 robustness frozen readout 的分离；
7. 十桶 mean curve 图：B0 与 selected model 使用相同坐标轴；
8. robustness 逐月十桶热力图；
9. security Rank IC、bucket Spearman、adjacent inversion、D10-D1 的 paired delta；
10. robustness early/late 和 block-bootstrap uncertainty；
11. A1/A2 逐 metric 数值和相对 B0/full delta；不得生成 composite causal attribution；
12. unknown coverage 与 strict all-resolved sensitivity；
13. 模型复杂度、冻结 feature-importance schema 和 D10 one-way turnover 仅作 descriptive warning；
14. 明确说明 paper-proxy sensitivity 未执行且禁止进入本轮 artifacts；
15. 明确说明本轮没有现金、国债、成本后 NAV、执行成交或 deployment 结论。

报告不得：

- 用 train/validation 曲线替代 robustness 结论；
- 隐藏失败 candidate；
- 把 D10 正收益写成 gate；
- 把 aggregate curve 单调写成每月都单调；
- 把 A2 cross-signal ensemble 的成功写成 P4 单因子成功；
- 因为 full model 使用了 P0/P1/P6，就把成功归因于 residual momentum 本身；
- 把 historical pseudo-OOS 写成 true OOS。

## 14. Manifest、hash 与 publication

所有 JSON 必须 strict JSON：`allow_nan=false`。普通 readout CSV 固定 UTF-8、LF、header、`float_format="%.12g"`；M1 coefficient CSV 是唯一例外，按 Section 8.2 使用 `%.17g`。Parquet 固定 `pyarrow + zstd`。Gzip 固定 `compresslevel=9, mtime=0`。

### 14.1 无环 stage seal DAG

Stage seal 顺序固定为：

```text
preflight
-> materialized
-> pre_robustness_selection
-> model
-> score
-> historical_readout
-> replay_core_comparison
-> final_publication
```

Preflight 至 historical_readout 的 stage chain 必须在 replay A/B 各执行一次；`replay_core_comparison` 是 parent-only comparison step，不形成第三套 stage bundle，其两个 comparison artifacts 只进入 replay A 的 final publication registry。

每个 stage 必须遵守同一无环规则：

1. payload 文件不得包含本 stage 尚未形成的 bundle hash；
2. stage manifest 可以包含全部 prior-stage bundle hashes 和本 stage payload hashes，但不得包含本 stage bundle hash；
3. stage output-hashes registry 是 flat JSON object：key 为相对该 stage root 的 POSIX relative path，value 为对应 exact bytes 的 lowercase 64-hex SHA256；它覆盖本 stage payload 与 manifest，明确排除 registry 自身，key 集合不得缺失或增加；
4. registry keys 按字典序升序，使用 UTF-8 canonical JSON 序列化：`sort_keys=true`、`separators=(",", ":")`、`ensure_ascii=false`、`allow_nan=false`，并固定一个末尾 LF；
5. `stage_bundle_hash = SHA256(exact stage output-hashes registry bytes)`；
6. 只有后续 stage 可以把该 hash 写入自己的 payload/manifest；当前 stage 任何文件都不得自引用它。

因此：selection record 不含 selection bundle hash或 parent-written exit hash；model payload只可引用 selection bundle hash；score payload只可引用 selection/model bundle hash；historical payload只可引用 score 及更早 bundle hashes。Final manifest 可以记录全部已形成的 prior-stage hashes和 decision SHA，但不得记录 final publication bundle 自身 hash。

### 14.2 Final publication manifest

Manifest 必须记录：

```text
requirement_sha256
config_sha256
execution_authority
separate_human_execution_authorization_required
requirement_execution_authorized
implementation_authorized
historical_outcome_execution_authorized
model_training_authorized
research_scope
multi_factor_model_allowed
P4_single_factor_repair_claim_allowed
upstream_final_output_hashes_sha256
upstream_preoutcome_bundle_hash
upstream_historical_bundle_hash
preflight_bundle_hash
materialized_bundle_hash
pre_robustness_selection_bundle_hash
model_bundle_hash
score_bundle_hash
historical_readout_bundle_hash
determinism_comparison_sha256
replay_b_core_hashes_sha256
stage_seal_integrity_gate
score_integrity_gate
determinism_gate
runtime_dependency_versions
feature_order_hash
split_registry_hash
candidate_selection_hash
scored_model_identity_registry_hash
decision_sha256
```

`output_hashes_20b_p4_mlrank.json` 必须覆盖 output root 内除自身外全部 publishable files，其 exact bytes 定义 final publication bundle hash，但该 hash 不得回写同一 bundle。Finalize 采用 temporary directory + atomic rename。失败 bundle 同样必须 immutable，不得用后一次运行覆盖。

## 15. Tests 与 validation contract

### 15.1 单元测试

至少覆盖：

1. P4 base population exact filter 和5/10重复去除；
2. feature arm exact route，P5 明确拒绝；
3. final registry 中只有冻结 report path 可用 narrative waiver，任一 machine artifact mismatch fail closed；
4. pyproject/uv.lock hash 和每个 exact dependency version mismatch 均 fail closed；
5. feature-worker outcome column read count 恒为0；
6. paper proxy 列或 semantics 出现在任一 materialized/readout artifact 必须 fail closed；
7. P4 lag 使用 exact scheduled month，不跨缺失 forward-fill；
8. equal feature values使用 average rank；
9. equal outcome values得到相同 y rank/relevance；
10. unknown label 不进入 loss但保留 score/membership；
11. 同一月份不得跨 split，random row split helper 不得存在或被调用；
12. 每个训练月份 sample weight sum 为1；
13. LightGBM group count与月份 known rows完全一致，`label_gain` exact-match；
14. validation label不用于 fit/early stopping；
15. train/validation 与 robustness labels 是独立 regular files且分别 hash；
16. selection worker 只在 validation metrics materialize 后选择唯一 family，robustness 不得改变选择；
17. selection worker 退出后才由 parent 写 exit record并形成 pre-robustness selection seal；
18. candidate selection lexicographic exact tie 选择 M1；
19. candidate fit audit 与两个 fit contracts 逐字段一致，后续不得回填；
20. 五个 fit ID 的 artifact path 唯一且各自 hash 可复算，candidate/refit/ablation 不覆盖；
21. selected artifact filename 的 M1/M2 条件互斥规则 fail closed；
22. M1 coefficient `%.17g` round-trip 重放 score，普通 readout CSV 使用 `%.12g`；
23. refit worker robustness feature/label read count 恒为0；
24. score worker label-open、fit/update、transform-fit call count 恒为0；
25. score seal 前打开 robustness label file 必须 fail firewall；
26. metric worker 只有验证 score bundle 后可打开 robustness label，所有 mutation call count为0；
27. preflight scored-model registry 恰有9行且 placeholder resolution exact；validation/robustness family/fit mapping exact，Full/A1/A2 下游主键不碰撞；
28. validation score rows exact 20,428、robustness score rows exact 46,500，全部 finite 且 key set 等于 P4 base；
29. learned-score 十桶公式和稳定 tie-break；
30. score payload 不含自身 score bundle hash，任何 stage payload/manifest/registry 不形成自引用；
31. stage bundle hash 按 exact canonical registry bytes 复算一致，prior-stage hash链完整；
32. 任一 reached stage seal 失败 exact 落入 `stage_seal_integrity_blocked`；
33. 所有 scored models 使用 exact common row/month comparison；
34. 所有桶均负但严格递增的 synthetic curve 通过 near-monotonic morphology；
35. 所有桶均正但乱序的 curve 失败；
36. 同月加常数不改变任何 monotonicity metric；
37. adjacent equal 不计为 ordered；
38. isotonic calibration 不能进入 primary score/gate；
39. absolute-return positivity 不出现在 decision gate；
40. moving-block bootstrap 精确使用 non-circular overlapping 3-month blocks、PCG64 seed、5000次及 linear 5/50/95分位数；
41. HAC 精确复现 Section 10.7 Bartlett 公式，underpowered/nonfinite 路径输出 missing reason；
42. confidence flag 使用双侧90% percentile CI lower bound，不得误标为单侧95%；
43. A1/A2 不参与 model selection 或 terminal gate，ablation table 不生成 composite causal label；
44. D10 one-way turnover 公式、首月 exclusion 和不跨 scheduled gap 规则 exact；
45. replay A/B scratch roots 必须预先不存在、process state 隔离、registered core comparison exact；
46. replay mismatch 生成 replay A immutable failure bundle且不得发布/覆盖 replay B；
47. `research_scope/multi_factor_model_allowed/P4_single_factor_repair_claim_allowed` 在 config、decision、manifest exact一致；
48. stage-seal、score、sample 和 metric failure 分别进入冻结 terminal state；
49. JSON 不含 NaN/Infinity；
50. 缺少独立 authorization file 不得造成任一 stage blocked；
51. decision/manifest exact记录 direct execution authority 和 execution booleans；
52. blocked 或成功 state 均不得授权 20C/deployment。

### 15.2 Integration tests

Synthetic mini-bundle 必须覆盖：

```text
case A: full multifactor score改善排序 -> multifactor improved state
case B: near-monotonic 8/9 adjacent + rho>=0.8 -> near-monotonic multifactor state
case C: validation winner在 robustness 反转 -> weak/no-improvement state
case D: robustness outcome 被 fit 读取 -> firewall blocked
case E: P5 feature 注入 -> feature blocked
case F: one unknown middle row -> membership不变且known-only return重算
case G: all returns negative but ordered -> positivity-independent pass
case H: candidate/dependency缺失 -> dependency/training/score pipeline blocked
case I: robustness可评价月份不足但 metrics finite -> sample-support underpowered
case J: required paired metric nonfinite且 sample充足 -> metric-materialization blocked
case K: A2 在某 metric 等于/超过 full -> 仅披露该 metric，不允许 composite P4 repair claim
case L: selection/model/score/historical 任一当前 stage self-hash 注入 -> stage-seal-integrity blocked
case M: paper proxy 注入 label/readout -> outcome-firewall blocked
case N: 任一 scored model 缺一行或 score nonfinite -> dependency/training/score pipeline blocked
case O: Full/A1/A2 复用同一 scored_model_id -> dependency/training/score pipeline blocked且score_integrity_gate=false
case P: replay A/B core score mismatch -> deterministic pipeline blocked并发布 replay A failure bundle
```

### 15.3 未来实现后的 validation commands

```bash
cd topics/02_AFML_BIG_WINNER

uv run python -m pytest \
  experiments/pending/20_ohlcv_positive_beta_exposure_research/tests/test_20b_p4_learned_monotonic_return_ranking_diagnostic.py -q

uv run python \
  experiments/pending/20_ohlcv_positive_beta_exposure_research/src/run_20b_p4_learned_monotonic_return_ranking_diagnostic.py \
  --config experiments/pending/20_ohlcv_positive_beta_exposure_research/configs/config_20b_p4_learned_monotonic_return_ranking_diagnostic.yaml \
  --stage full
```

## 16. Definition of Done

只有同时满足以下条件，本 requirement 的未来实现才算完成：

- 上游 v5 machine bundle hash/schema/count全部验证；
- requirement/config exact binding，并记录 direct execution authority；
- feature 与 outcome fresh-process firewall 可审计；
- 63个月 exact split 和 row counts 复算一致；
- 16个冻结 features 全量 materialize，无额外 feature；
- paper proxy 不进入任何 label、selection、metric 或 readout artifact；
- B0/N0/M1/M2 全量运行，无隐藏 candidate/search；
- validation selection 由独立 worker 完成并在任何 refit/robustness read 前密封；
- candidate fit audit 可从 selection stage 原始记录逐字段复核；五个 fit artifacts 路径唯一且各自 hash 可复算；
- selected family 与两个 ablation 在不读取 robustness feature/label 的 fresh refit worker 中冻结，M1/M2 artifact filename 条件互斥；
- inference-only score worker 不打开任何 label或调用 fit/update，score seal 后 metric worker 才读取 robustness label；
- validation/robustness scored-model identities 唯一，score row counts/key sets/finite values 全部通过 score integrity gate；
- primary/strict sensitivity、security Rank IC、bucket monotonicity、paired delta、bootstrap、ablation、feature importance 和 D10 turnover 输出齐全；
- 结论身份固定为 P4 eligible universe 上的多因子 reranker，任何状态都不允许 P4 single-factor repair claim；
- positivity-independence synthetic tests 通过；
- stage seal、score、sample underpowered、metric materialization blocked 与其余 terminal truth table唯一确定；
- 报告完整披露 design contamination、非 true OOS、无现金/国债/成本后策略结论；
- replay A/B 使用独立 scratch roots，core comparison、无环 stage seal DAG、manifest/output hash 和 deterministic replay 全部通过；
- 20C、portfolio optimization 与 deployment 等 downstream authorization 保持 false。

## 17. Requirement review checklist

评审时逐项确认：

```text
[ ] 研究目标只要求次月横截面收益排序尽可能单调，不要求任何桶绝对为正。
[ ] 允许 P0/P1/P4/P6 多因子 reranker，但 claim 只属于 P4 eligible universe，不属于 P4 单因子修复。
[ ] P4 base population、63个月和 train/validation/robustness 日期完全冻结。
[ ] Feature 只来自 decision-time P0/P1/P4/P6；P5 retrospective route 被禁止。
[ ] Label 是 next-month project return 的同月横截面 rank，不是绝对正负标签。
[ ] Paper proxy sensitivity 已删除，任何 worker/materialized/readout artifact 均不得读取或输出该列。
[ ] 股票行随机切分、robustness refit 和 post-hoc isotonic 被禁止。
[ ] M1/M2 hyperparameters、selection key、refit和ablation完全冻结。
[ ] Selection、refit、score、metric 是四个可审计 fresh worker；robustness label 只在 score seal 后打开。
[ ] Scored model、model family 与 fit identity 分离；Full/A1/A2 的所有下游 stable keys 唯一。
[ ] Validation 20,428 行、robustness 46,500 行 score 全部 finite 且 exact覆盖 P4 base keys。
[ ] Primary metric 同时覆盖 security Rank IC、bucket curve Spearman 和 adjacent inversions。
[ ] Near-monotonic/improved truth table不包含 absolute-return positivity。
[ ] Unknown 不改变 ex-ante membership，paired readout 使用相同 common rows/months。
[ ] 输出 schema、tests、manifest、hash和blocked states 足以直接实现。
[ ] 所有 stage seal 无 self-hash/self-exit-hash 循环，五个 fit artifact 不覆盖。
[ ] Replay A/B scratch、comparison 与 single-publication arbitration 完全冻结。
[ ] 当前 workspace 用户指令已直接授权 implementation/outcome read/model training，不要求独立人类授权文件。
```
