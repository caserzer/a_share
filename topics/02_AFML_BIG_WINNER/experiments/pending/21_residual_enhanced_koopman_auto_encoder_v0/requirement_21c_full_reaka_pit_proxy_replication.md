# Requirement 21C：Full REAKA PIT Proxy Local Validation Sanity

> 文档状态：`frozen_requirement_execution_authorized`
>
> 生成日期：2026-07-14
>
> Experiment ID：`21_residual_enhanced_koopman_auto_encoder_v0`
>
> Phase ID：`21C_FULL_VALIDATION_SANITY`
>
> Run ID：`21C_full_reaka_pit_proxy_replication`
>
> Requirement version：`21C_FULL_v4`
>
> 上游研究计划：`research_plan.md`
>
> 上游阶段：successful corrected successor of `21B_alpha158_sequence_baseline_benchmark`
>
> 当前执行状态：`pending_v4_performance_successor_authorization`
>
> Claim ceiling：`validation_only_full_architecture_local_sanity_and_point_ordering`

## 0. 一页执行结论

本 requirement 响应 2026-07-14 workspace 用户提出的研究范围变更意向：暂不做 K1/K1C/K2/R1 的 nested ablation，只回答：

> 在 21A/21B 已冻结的本地 PIT universe、157-feature registered Alpha158 adaptation、T=10 raw return sequence 和一步
> close-to-close label 上，完整 `R2_REAKA_DIFFUSION` 能否产生正且稳定的 validation-late daily RankIC，并在同日 paired readout
> 中呈现高于冻结 M1/M3 comparator 的论文方向性排序。

本阶段只新增并训练：

```text
R2_REAKA_DIFFUSION
```

比较对象只读取成功且合格的 21B successor 中已经冻结的：

```text
M1_LIGHTGBM_ALPHA158
M3_GATED_DUAL_PATH_LSTM
```

本阶段明确不训练、不重训、不替换：

```text
M0_HASH_NULL_SCORE
M1_LIGHTGBM_ALPHA158
M2_RETURN_LSTM
M3_GATED_DUAL_PATH_LSTM
A0_VANILLA_AUTOENCODER
K1_SINGLE_KOOPMAN_AE
K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL
K2_ADAPTIVE_KOOPMAN_AE
R1_AKS_MLP_RESIDUAL
```

`M2_RETURN_LSTM` 只允许作为 21B 已有的 project-defined return-only diagnostic 被引用；不得继续称为论文 `w/o GM`
ablation，也不进入本阶段 gate。论文 `w/o GM` 仍未实现，因为它应保留 AKS、Koopman、diffusion residual、decoder 和完整 loss。

生成本 requirement 只记录该意向，不等于 scope override 已获执行批准。执行前必须存在独立、不可变、由人类签署并被 execution
authorization 绑定的 `scope_restart_decision.json`；runner 不得用本文件自证其有权偏离原 research plan/21B decision。该 restart 不回写或
改造已密封 21A/21B bundle，且必须发生在任何 21C 模型训练、validation-late readout 或 historical-design-holdout outcome access 之前。

本阶段只使用 train、validation_early、validation_late：

```text
provisional_candidate_selection_fold = validation_early
replication_gate_fold = validation_late
validation_full_role = diagnostic_only
historical_design_holdout_readout_authorized = false
```

本阶段不读取 2024+ historical design holdout，不计算 next-open executable PnL，不做成本/容量/部署结论。即使 R2 通过，也只能得到：

```text
paper_architecture_grounded_project_adaptation
full_reaka_local_validation_point_ordering_observed
```

禁止声明：

```text
exact_replication
paper_result_reproduced
CSI300_result_reproduced
S&P500_result_reproduced
koopman_mechanism_supported
adaptive_operator_supported
diffusion_increment_supported
REAKA_profitability_confirmed
deployment_ready
```

### 0.1 当前 21B_v4 只作 observed candidate，不是自动合格 successor

当前 workspace 的 21B_v4 observed bundle 显示：

```text
stage_decision = 21B_baseline_information_supported_pending_human_approval
baseline_information_gate = pass
eligible_baseline_ids = M1_LIGHTGBM_ALPHA158|M3_GATED_DUAL_PATH_LSTM
next_requirement_generation_authorized = true
next_requirement_execution_authorized = false
```

但代码审查已发现 qfq cutoff 后首行 materialization/access-counter 语义与 21B strict contract 不一致。当前 v4 可用于本 requirement
的 schema/路径设计，不能被 21C runner 自动视为执行合格输入。21C execution 只能绑定一个新的 immutable corrected 21B successor，且：

```text
post_cutoff_value_token_materialization_count = 0
post_cutoff_outcome_value_decode_count = 0
process_access_counters_are_runtime_derived = true
upstream_21b_contract_erratum_gate = pass
```

禁止直接修改已密封 v4 输出或用人工文字说明替代 corrected rerun/hash closure。

## 1. 身份、目录与 stage

### 0.2 v2 teacher-cache availability correction

`21C_FULL_v1` 在已授权 materialization 中 fail closed：396 个 train source samples 的 decision-date feature cache offset 已是对应
instrument 的最后一个 approved cache key，因此 `last_offset+1` 跨 instrument，不能作为 t+1 teacher feature。v1 只留下 unsealed building
cleanup evidence，未进入训练、late readout 或 finalize。

`21C_FULL_v2` 禁止物理相邻 offset 假设。Materializer 必须按 approved feature-key registry 的 `(instrument, feature_date)` 顺序解析每个
sample 的严格 next key；若任一 train sample 不存在同 instrument 的 t+1 approved feature key，则不得 drop row、缩 denominator、forward-fill、
借用其他 instrument offset 或读取 raw feature source，必须写 P1 materialization failure bundle，并以
`teacher_materialization_gate=not_evaluable`、state 4 终止。只有全体 train rows 都存在 exact t+1 key时才允许生成 teacher artifacts并进入训练。

### 0.3 v3 PIT-universe exclusion successor

`21C_FULL_v2` 已 immutable 封存为 `P1_MATERIALIZATION_BLOCKED`。其 396 条 missing-teacher source samples 对应 396 个互不重复的
instrument。2026-07-16 workspace 用户显式授权把完整受影响集合从本实验 PIT universe 移除并继续执行。

`21C_FULL_v3` 将以下 registry 作为新的 material input：

```text
registry_path = references/21c_full_v3/pit_universe_exclusion_registry.csv
registry_sha256 = 3c3d903821ee56a49f1ea0d83327606b58f87826ae317d6f95e5a5d4236aef11
registry_instrument_n = 396
derivation_scope = train_teacher_t_plus_1_key_availability_only
exclusion_scope = all_folds_entire_instrument_history
```

Runner 必须重放 v2 缺失条件，证明 registry 与 396 个 `(instrument, trigger_decision_date, source_sample_row_idx)` exact 一致；不得只使用报告
展示的前十个样例。每个 registry instrument 必须从 train、validation_early、validation_late 的整个历史中统一移除，M1/M3 comparator readout
也必须应用同一 exclusion set。禁止只删除 396 条失败行、按日期恢复 instrument、对 retained rows 再做 availability drop，或利用
validation outcome 决定 exclusion。

该授权显式改变 estimand 为 `v2_missing_teacher_instrument_excluded_pit_universe`。v3 结果只对缩减后的 PIT universe 有效，不得包装成原始
full PIT universe 结果，也不得与 v2 的未训练终态作性能比较。Preflight 必须写出完整
`pit_universe_exclusion_audit.csv` 和逐 fold 的 `pit_universe_exclusion_impact.csv`，并把 registry SHA256、source/removed/retained row counts及
retained row-key hashes纳入 resolved config、teacher manifest、checkpoint/semantic/final manifests与最终报告。

### 0.4 v4 performance successor

`21C_FULL_v3` 已通过 preflight 和 teacher materialization，但首个 seed 在约 32 分钟内尚未完成，随后由 workspace 用户显式要求“提升性能”。
v3 training worker 被有序终止；其 `.building` 目录作为 unsealed interruption evidence保留，不得当作结果或继续追加。

`21C_FULL_v4` 完整继承 v3 的 396-instrument exclusion、335,393-row train denominator、模型/损失/optimizer/seed/epoch/patience、training batch
resource probe与 validation gates，只允许以下 performance changes：

```text
feature_cache_residency = shared_process_ram_copy
inference_batch_size = 1024
inference_noise_device = cpu_row_seeded_batched_schedule
row_draw_seed_formula = unchanged
reverse_noise_tensor_shape = [row,20,10,64]
```

每个 `(instrument,decision_date,model_seed,draw_id)` 仍使用独立 SHA256-derived seed。CPU generator 一次生成 initial residual 加 19 个 reverse-step
noise，固定 index 0 为 initial residual、index `20-step+1` 为 step>1 noise，然后每 draw只做一次 device transfer。该 v4 RNG route 与未完成 v3 的
CUDA generator route 数值不等价，因此必须更新 requirement/config/runner/test/authorization pins并使用新 root；不得声称 byte-identical continuation。
模型训练 batch semantics、loss reductions和 optimizer-step count均不得为加速而改变。

预期实现文件：

```text
requirement_file = requirement_21c_full_reaka_pit_proxy_replication.md
config_file = configs/config_21c_full_reaka_pit_proxy_replication.yaml
runner_file = src/run_21c_full_reaka_pit_proxy_replication.py
test_file = tests/test_21c_full_reaka_pit_proxy_replication.py
authorization_file = references/21c_full_v4/execution_authorization.json
scope_restart_decision_file = references/21c_full_v4/scope_restart_decision.json
canonical_output_root = outputs/21C_full_reaka_pit_proxy_replication_v4
preauthorization_audit_root = outputs/21C_full_reaka_pit_proxy_replication_v4_preauthorization_audits
```

工作目录固定为：

```bash
cd topics/02_AFML_BIG_WINNER
```

Canonical output root 必须带 requirement version。Material requirement、approved upstream、feature route、模型 config、seed、split、
gate、scope 或 claim boundary 任一改变必须创建新 version/root；旧失败或成功 root 永不覆盖。
例外只限当前未授权 draft：在不存在 execution authorization、canonical root 或 preauthorization audit 的前提下，可原地修订当前 version；一旦任一
authorization bytes 绑定 requirement SHA256 或任一 audit/root 已生成，后续 material change 必须升级 requirement/root version。

Runner 顶层 stage 只有：

```text
preflight
materialize-r2-teacher
train-r2
late-readout
finalize
```

- `preflight`：只验证人类执行授权、scope override、corrected 21B successor、21A lineage、依赖、hash、artifact profile 和访问白名单；
  不得读取 feature/qfq value、label、score outcome 或模型 checkpoint tensor；
- `materialize-r2-teacher`：只基于已验证的 21B source panel、sequence index 和 feature cache，为 train rows 生成 shifted teacher
  index/return panel；不得生成 validation teacher tensor、RankIC、TopK 或任何 summary；
- `train-r2`：parent controller 启动 fresh `r2-selection-worker`；worker 只读 train 与 validation_early，训练三个 primary R2 seeds、
  选择 provisional checkpoint 并退出；parent 验证文件后密封 pre-gate bundle；
- `late-readout`：parent 只在 pre-gate bundle 密封后启动 fresh inference-only worker。该 worker 才能打开 validation_late，并输出
  R2 seed/ensemble score；禁止 fit、backward、optimizer step、checkpoint/config replacement；
- `finalize`：只读已密封 artifacts 和 approved 21B comparator scores，计算 paired RankIC、稳定性、paper-proxy Top30、decision、报告、
  manifest 和 hashes；不得导入训练入口或修改 checkpoint；
- stage 不得调用 package manager；环境 bootstrap 必须在 stage 外显式完成。

缺失/无效 authorization 的 preflight 只允许写 content-addressed P0 audit，不能占用 canonical output root。路径规则继承 21B：

```text
authorization_observation = "MISSING" if file absent else lowercase_sha256(full authorization bytes)
preauthorization_audit_id = first_16_hex(SHA256(requirement_sha256 + "|" + authorization_observation))
```

## 2. 授权、scope restart 与上游 successor

### 2.1 生成授权与执行授权分离

```text
requirement_generation_authority = workspace_user_request_2026-07-14
requirement_generation_authorized = true
requirement_execution_authorized = false
scope_restart_decision_authorized = false
scope_override_execution_authorized = false
historical_holdout_readout_authorized = false
top30_close_proxy_authorized = true_after_pre_gate_seal
next_open_execution_replay_authorized = false
policy_training_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

生成本文件不构成执行授权。`references/21c_full/execution_authorization.json` 必须由后续人类动作生成，字段集合 exact 为：

```json
{
  "requirement_sha256": "<exact sha256>",
  "approved_21c_runner_sha256": "<exact sha256>",
  "approved_21c_config_sha256": "<exact sha256>",
  "approved_21c_test_sha256": "<exact sha256>",
  "scope_restart_decision_path": "references/21c_full/scope_restart_decision.json",
  "scope_restart_decision_sha256": "<exact sha256>",
  "approved_21b_output_root": "<explicit corrected versioned relative path>",
  "approved_21b_requirement_version": "<exact version>",
  "approved_21b_requirement_sha256": "<exact sha256>",
  "approved_21b_runner_sha256": "<exact sha256>",
  "approved_21b_config_sha256": "<exact sha256>",
  "approved_21b_test_sha256": "<exact sha256>",
  "approved_21b_decision_sha256": "<exact sha256>",
  "approved_21b_manifest_sha256": "<exact sha256>",
  "approved_21b_output_hashes_sha256": "<exact sha256>",
  "approved_21b_gate_evidence_sha256": "<exact sha256>",
  "approved_21b_pre_holdout_bundle_hash": "<exact sha256>",
  "approved_21b_semantic_payload_bundle_hash": "<exact sha256>",
  "approved_21b_contract_erratum_id": "<non-empty immutable id>",
  "approved_21b_contract_erratum_path": "<exact versioned relative path under approved 21B root>",
  "approved_21b_contract_erratum_sha256": "<exact sha256>",
  "approved_21a_paper_lineage_erratum_path": "<exact versioned relative path under approved 21B root>",
  "approved_21a_paper_lineage_erratum_sha256": "<exact sha256>",
  "scope_override": "full_reaka_local_validation_sanity_without_module_ablation",
  "historical_holdout_readout_authorized": false,
  "reviewer_role": "human",
  "reviewed_at_utc": "<RFC3339 UTC>",
  "authorization_status": "approved"
}
```

任何 extra/missing key、非 64-hex hash、unversioned/latest/glob path、非人类 reviewer、scope override 不一致、holdout authorization
不为 false，均使 authorization 无效。所有 `*_path` 必须是 workspace-relative canonical path，禁止 symlink；其 full bytes SHA256 必须与
相邻 pin exact-match。三个 `approved_21c_*_sha256` 必须分别等于 Section 1 固定 runner/config/test 文件在 authorization full bytes
落盘前、reviewer 审阅时的 full-byte SHA256；preflight 必须在任何 value/checkpoint open 前重新计算并 exact-match，后续 stage 也必须把它们
纳入 resolved config、pre-gate seal、semantic manifest 与 final manifest。Runner 不得生成或修改 authorization、scope restart 或
upstream erratum 文件，也不得在 authorization 后替换自身 runner/config/test bytes。

### 2.2 合格 corrected 21B successor

Source config 是 authorization 前由 reviewer 审阅并被 `approved_21c_config_sha256` 绑定的静态输入，不得嵌入自身 hash 或尚未存在的
authorization bytes/pins；否则形成 self-hash cycle。只有 preflight 生成的 `resolved_config.yaml` 必须复制 authorization 中的 exact pins。
合格 successor 必须同时满足：

1. canonical output root 尚未被修改，manifest/output-hashes/file-set 双向验证通过；
2. decision 唯一一行，`stage_decision=21B_baseline_information_supported_pending_human_approval`；
3. `baseline_information_gate=pass`；
4. `M1_LIGHTGBM_ALPHA158` 与 `M3_GATED_DUAL_PATH_LSTM` 各三个 checkpoint 均为 `eligible_frozen`；
5. M1/M3 validation_early、validation_late seed/ensemble score 完整且 coverage=1；
6. approved pre-holdout bundle hash、semantic payload hash 与 authorization exact-match；
7. 21B 全部 causal gates 与 output manifest meta-gate pass；
8. corrected implementation/tests 证明 cutoff 后 value token materialization/decode 为 0，访问计数来自真实 wrapper/log；
9. 21B historical holdout outcome/label/score-join/metric count 均为 0；
10. 21B config、decision、manifest 均显式记录 exact `upstream_21b_contract_erratum_gate=pass`；不得用名称或语义未冻结的“等价 gate”替代。

当前 observed v4 若未满足第 8/10 条必须 fail closed。21C 不得以“数值看起来没变”、人工确认或重新计算单个 hash绕过。

Corrected 21B root 内必须包含 authorization 所 pin 的 `contract_erratum`，exact JSON keys：

```text
erratum_id,source_requirement_version,corrected_requirement_version,
defect_id,defect_description,affected_artifacts,corrected_runner_sha256,
corrected_config_sha256,corrected_test_sha256,runtime_counter_evidence_path,
runtime_counter_evidence_sha256,runtime_access_event_log_path,
runtime_access_event_log_sha256,runtime_counter_aggregation_contract_id,
post_cutoff_value_token_materialization_count,
post_cutoff_outcome_value_decode_count,counter_collection_mode,
historical_holdout_outcome_open_count,historical_holdout_label_open_count,
historical_holdout_score_join_count,historical_holdout_metric_count,status
```

其中两个 post-cutoff count 与四个 historical-holdout count 必须为 0；`counter_collection_mode=runtime_wrapper_and_append_only_log`、
`runtime_counter_aggregation_contract_id=QFQ_RUNTIME_ACCESS_EVENT_AGGREGATION_V1`、`status=corrected_rerun_sealed`。
`runtime_counter_evidence_path` 与 `runtime_access_event_log_path` 必须是同一 corrected root 下两个不同的 canonical paths，均被 output
manifest/hash closure、semantic payload closure 和 `affected_artifacts` 覆盖。Raw append-only event log 的 CSV schema exact 为：

```text
event_seq,process_id,stage,access_scope,operation,path,path_class,
value_token_requested,value_decoded,decision_date,status,reason
```

`event_seq` 从 0 连续递增；`process_id` 是由 stage/worker role 派生的 stable logical ID，禁止使用 OS PID；`path` 必须是
workspace-relative canonical path，禁止绝对路径、symlink resolution alias 或临时 root。每次 wrapper allow/deny attempt 在返回 value或抛出
异常前先 append、flush、fsync 一行。跨 fresh processes 的 append 必须使用 process-safe exclusive lock，锁内分配下一 event_seq并完成整行
append+flush+fsync，禁止各 process 自行从 0 计数后事后去重。`status` 只允许
`allowed|denied`；`allowed` 时 reason 为空，`denied` 时 reason 非空。`decision_date` 不适用时为空，否则必须是 wrapper 在本次 access request
开始前持有的 routing date；禁止先实例化整行或 value token 再回填。Event log canonical sort 等于 append order，即 `event_seq` ASC，禁止
聚合、去重或事后重排。

`runtime_counter_evidence_path` 的聚合 CSV schema exact 为：

```text
process_id,stage,access_scope,operation,path_class,value_token_requested,value_decoded,
decision_date_min,decision_date_max,event_count,source_log_path,source_log_sha256,status,reason
```

Canonical sort：`process_id,stage,access_scope,operation,path_class,value_token_requested,value_decoded`。每行 `source_log_path/hash` 必须 exact
等于 erratum pins。Evidence 只能由 sealed raw log 逐行聚合：group key 等于上述 sort key，`event_count` 为 raw row count，date min/max 忽略空值；
`status` 只允许 `pass|fail`，pass reason 为空、fail reason 非空。禁止由 config 常量、预置零值、测试 fixture 或报告文字生成。Erratum 的两个
post-cutoff count 必须分别从 raw log 重算为：

```text
post_cutoff_value_token_materialization_count =
    count(event where decision_date > max_allowed_outcome_source_date
          and value_token_requested=true)

post_cutoff_outcome_value_decode_count =
    count(event where decision_date > max_allowed_outcome_source_date
          and value_decoded=true)
```

四个 historical-holdout counts 也必须按各自 operation/access_scope 从同一 raw log 机械重算；erratum、aggregate evidence 与 raw-log recomputation
三方任一不一致即 fail。Exact mapping 为：

```text
historical_holdout_outcome_open_count =
    count(event where access_scope=historical_design_holdout and operation=outcome_open)
historical_holdout_label_open_count =
    count(event where access_scope=historical_design_holdout and operation=label_open)
historical_holdout_score_join_count =
    count(event where access_scope=historical_design_holdout and operation=score_outcome_join)
historical_holdout_metric_count =
    count(event where access_scope=historical_design_holdout and operation=metric_compute)
```

Counter verifier 必须先验证 raw log full-byte hash、event_seq 连续性、schema 与 output closure，再允许读取 aggregate evidence。Raw log 不含
timestamp/latency 等 volatile 字段；full-byte 与 semantic hash 均覆盖同一 canonical bytes。
`defect_id=QFQ_POST_CUTOFF_VALUE_TOKEN_AND_RUNTIME_COUNTER_SEMANTICS`；erratum 的 corrected version/runner/config/test hashes 必须与
authorization pins exact-match，`affected_artifacts` 为 path ASC canonical JSON array且每个 path 均在 corrected output manifest 中。

### 2.3 独立 scope restart 与 successor route override

原 research plan/21B decision 将 next requirement 写为 planned nested-ablation 文件。`scope_restart_decision.json` 必须在 execution
authorization 之前由人类创建，字段集合 exact 为：

```json
{
  "decision_id": "<non-empty immutable id>",
  "superseded_route": "requirement_21c_single_vs_adaptive_koopman_nested_ablation.md",
  "approved_route": "requirement_21c_full_reaka_pit_proxy_replication.md",
  "superseded_estimand": "nested_module_attribution",
  "approved_estimand": "full_architecture_local_validation_sanity",
  "requirement_sha256": "<exact sha256>",
  "historical_holdout_readout_authorized": false,
  "execution_authorized": false,
  "reviewer_role": "human",
  "reviewed_at_utc": "<RFC3339 UTC>",
  "decision_status": "approved_scope_restart_only"
}
```

任何 extra/missing key、原/新 route 或 estimand 不一致、requirement hash 不匹配、非人类 reviewer、holdout=true、
`execution_authorized=true` 均 fail。只有 execution authorization exact 绑定该 decision hash、当前本文件 hash、corrected 21B hashes，且 corrected
21B historical holdout access count 为 0，才允许 alternate successor：

```text
requirement_21c_full_reaka_pit_proxy_replication.md
```

该 restart 只改变尚未执行的 21C 研究范围，不把原 research plan/21B decision/file 改写为其他值，也不授权 21C execution、holdout、
经济 replay 或后续阶段；execution 仍只由 Section 2.1 的独立 authorization 授予。

### 2.4 继承 21A contract

21C 必须从 corrected 21B manifest 反向验证其唯一 approved 21A successor，并继承：

```text
paper source/hash and formula registry
paper-lineage erratum path/hash
feature route/expression/cache/order hashes
normalization/missingness contract
PIT universe and denominator contract
label semantics
T=10 sequence and 12-session purge
R2 tensor/teacher/inference graph
primary architecture/search/randomness freeze
dependency/runtime/GPU contract
```

由于已密封 21A registry/research plan 将 M2 标成 paper baseline/w-o-gating，而本 requirement 已确认该映射不成立，corrected 21B 必须附带
authorization 所 pin 的 `approved_21a_paper_lineage_erratum_path`。该 immutable JSON keys exact 为：

```text
erratum_id,upstream_21a_version,upstream_model_arm_registry_sha256,
affected_arm_id,original_role,corrected_role,paper_w_o_gm_equivalent,
paper_lstm_equivalent,gate_eligible_in_21c,reason,reviewer_role,
reviewed_at_utc,status
```

固定值：`affected_arm_id=M2_RETURN_LSTM`、`corrected_role=project_return_only_diagnostic`、两个 equivalent 均为 false、
`gate_eligible_in_21c=false`、`reviewer_role=human`、`status=approved_lineage_erratum`。Erratum 不重写 21A bytes；21C 的 lineage audit 必须同时
记录原 registry hash 与 erratum hash，并以 erratum 后语义解释 M2。缺失、未被 corrected 21B manifest/hash closure 覆盖或 hash 不匹配均 fail。

任一 21A/21B inherited hash 链断裂时，21C 在读取 value/checkpoint 前 block。

## 3. Research estimand 与 claim boundary

### 3.1 唯一 primary estimand

```text
E_full_architecture_validation_proxy:
    frozen full R2 ensemble validation_late daily RankIC
    and paired point-estimate ordering versus frozen M1/M3
```

本阶段不估计：

```text
E_single_koopman_increment
E_adaptive_operator_increment
E_diffusion_specific_increment
E_gating_increment
E_executable_net_utility
E_forward_confirmation
```

### 3.2 论文与本地差异必须显式报告

| 维度 | 论文 | 本 requirement |
|---|---|---|
| market | CSI300 / S&P500 | PIT top-400 main board + top-100 ChiNext |
| period | 2010-2020 | train 2018-2022，validation 2023 |
| feature | Alpha158 | `ALPHA158_NO_VWAP_REGISTERED_ADAPTATION`，D=157 |
| lookback | T=10 | T=10 |
| model details | 多项未披露 | 21A project-frozen choices |
| primary readout | RankIC / RankICIR | 同口径本地 validation proxy |
| TopK | K=30，执行细节未披露 | daily close-to-close gross proxy only |

`paper_reference_comparison.csv` 可以抄录论文 Table 1/3 的静态参考值，但必须设置：

```text
threshold_role = reference_only
local_pass_threshold_source = none
cross_market_numeric_match_claim_allowed = false
```

### 3.3 允许的结论

- R2 pipeline/architecture 是否 evaluable；
- R2 validation-late 方向是否正且跨 seed/月稳定；
- R2 相对本地冻结 M1/M3 的 paired point-estimate ordering；
- paper-proxy Top30 close-to-close gross morphology；
- 是否值得由人另行发起更严格 historical/forward requirement。

不得把 validation、gross Top30 或 reconstruction improvement 写成可信 OOS、机制归因、可执行 alpha 或论文数值复现。

## 4. 数据、feature route、split 与访问边界

### 4.1 唯一输入 route

本 requirement 不重新选择 feature。必须 exact 继承 corrected 21B：

```text
feature_route_id = ALPHA158_NO_VWAP_REGISTERED_ADAPTATION
feature_dim = 157
lookback_T = 10
label_id = Y_rank_primary
label_formula = qfq_close(t+1)/qfq_close(t)-1
normalization = train median / (IQR/1.349), clip [-10,10]
invalid_fill = train median
missing_indicator_direct_input = false
```

若 corrected 21B 使用其他 route、feature count/order/expression hash，本 version fail；不得动态适配到 158 或其他 feature count。

### 4.2 Exact effective splits

```text
train = 2018-01-02 .. 2022-12-14
validation_early = 2023-01-03 .. 2023-06-30 eligible rows
validation_late = first eligible session after 2023-06-30 .. 2023-12-13
validation_full = validation_early union validation_late
historical_design_holdout = forbidden
```

实际 eligible dates/rows、purge hash、row-key hash 必须 exact-match corrected 21B manifests；禁止重新筛 row、缩 denominator 或依据 R2
coverage 取 intersection。

### 4.3 Source panel reuse

21C 不重新读取 raw qfq、membership、calendar 或 feature-expression source。只允许打开 manifest 显式列出的：

```text
materialized/sequence_sample_index.parquet
materialized/panels/train/return_and_label_panel.f32.memmap
materialized/panels/validation_early/return_and_label_panel.f32.memmap
materialized/panels/validation_late/return_and_label_panel.f32.memmap
approved 21A feature cache key/index/memmap components
```

每次 open 前验证 path、full-byte SHA256、semantic hash、byte size、dtype、shape、sort/key hash。禁止 symlink、glob、mtime/latest resolution。

### 4.4 R2 train-only shifted teacher materialization

对每个 train source sample：

```text
source_dates          = [t-9, ..., t]
teacher_shifted_dates = [t-8, ..., t+1]

y_teacher_shifted[0:9] = y_source[1:10]
y_teacher_shifted[9]   = forecast_y(t+1)

x_teacher_shifted[0:9] = x_source[1:10]
x_teacher_shifted[9]   = feature_cache(instrument,t+1)
```

最后一个 feature row 是 train-only teacher target row。每个 teacher date/key/cache offset 必须显式记录。只允许 train rows；validation
teacher count 必须为 0。所有 teacher tensors：

- 只能进入 train-only shared-parameter teacher encoder/gate path，构造 `Z_teacher_shifted`；
- 允许 `x_teacher_shifted` 进入 teacher branch 的 shared `feature_encoder` 与 shared `gate_linear`，允许 `y_teacher_shifted` 进入 teacher
  branch 的 shared `return_encoder`；这些 module 与 source branch 共享同一组 parameter objects，不复制权重、不 stop-gradient；
- 不得进入 source-branch encoder/GateNet input、selector context、DDPM condition、decoder skip/concat 或 inference signature；
- 不得写入 validation score artifact；
- inference graph 必须完全不接受 teacher 参数。

Teacher latent exact 为：

```text
H_y_teacher = LSTM_y(y_teacher_shifted)                         # [B,T,64], zero h0/c0
H_x_teacher = LSTM_x(x_teacher_shifted)                         # [B,T,64], zero h0/c0
G_teacher = sigmoid(Linear_gate(H_x_teacher))                   # [B,T,64]
Z_teacher_shifted = H_y_teacher*G_teacher + H_x_teacher*(1-G_teacher)
```

Teacher 与 source 两次调用均从 per-sample zero hidden/cell state 开始，禁止把 source final state传给 teacher、跨 branch carry state或把两个
sequence concat 后一次编码。`L_koop/L_diff/L_rec` 对 teacher branch 的梯度必须回到同一 shared return/feature encoder 与 gate parameters；
teacher branch 不调用 selector，也不生成第二套 `K_selected`。这里禁止的是 teacher value 进入 **source** GateNet 或 inference graph，不是禁止
teacher branch 使用 shared gate parameters。

Materializer 禁止计算 train/validation label summary、RankIC、loss、score、TopK 或访问 validation_late panel。

### 4.5 Access audit scopes

所有 value access 必须记录：

```text
stage,process_role,path,artifact_sha256,access_scope,row_scope,value_scope,
allowed,row_n,first_key,last_key,reason
```

Hard counters：

```text
raw_qfq_open_count = 0
raw_membership_open_count = 0
raw_calendar_open_count = 0
historical_holdout_feature_value_read_count = 0
historical_holdout_outcome_value_read_count = 0
historical_holdout_label_materialization_count = 0
historical_holdout_score_join_count = 0
historical_holdout_metric_count = 0
selection_worker_validation_late_open_count = 0
```

任一非零/`allowed=false` 为 access firewall failure，优先于模型结果。

## 5. Full R2 architecture contract

### 5.1 Mandatory arm registry

本阶段 registry 只有一条 trainable mandatory row：

| arm_id | mandatory | role | claim ceiling |
|---|---:|---|---|
| `R2_REAKA_DIFFUSION` | true | full paper-grounded project adaptation | full-architecture validation proxy only |

M1/M3 是 `inherited_frozen_comparator=true,trainable_in_21c=false`，不得进入 job count。M2 若出现在 lineage note，必须：

```text
role = project_return_only_diagnostic
paper_w_o_gm_equivalent = false
gate_eligible_in_21c = false
```

### 5.2 Canonical encoder、gate、selector 与 Koopman propagation

```text
H_y = LSTM_y(y_source)                                      # [B,T,64]
H_x = LSTM_x(x_source)                                      # [B,T,64]
G = sigmoid(Linear_gate(H_x))                               # [B,T,64]
Z_source = H_y * G + H_x * (1-G)                           # [B,T,64]

selector_logits = LeakyReLU(Linear_selector(concat[Z_source,H_y]), 0.01)
selector_train = softmax((selector_logits + gumbel_noise)/tau, dim=operator)
selector_inference = one_hot(argmax(selector_logits), tie=smallest_operator_index)

K_selected[b,t] = sum_n selector[b,t,n] * K_codebook[n]    # [B,T,64,64]
Z_hat_shifted[b,t,i] = sum_j K_selected[b,t,i,j] * Z_source[b,t,j]
```

禁止 implicit broadcasting、row-vector right multiply、K transpose、hard/straight-through primary training、inference sampling selector。

Exact module topology：

```text
return_encoder  = LSTM(input=1,   hidden=64,layers=1,unidirectional,batch_first=true,dropout=0)
feature_encoder = LSTM(input=157, hidden=64,layers=1,unidirectional,batch_first=true,dropout=0)
gate_linear     = Linear(64,64)
selector_linear = Linear(128,4)
K_codebook      = 4 x [64,64]
decoder         = Linear(64,1)
```

### 5.3 DDPM residual corrector

```text
R_target_shifted = Z_teacher_shifted - Z_hat_shifted
x_s = sqrt(alpha_bar_s)*R_target_shifted + sqrt(1-alpha_bar_s)*epsilon
epsilon_hat = epsilon_theta(x_s,s,Z_source)
R_hat_train = (x_s - sqrt(1-alpha_bar_s)*epsilon_hat)/sqrt(alpha_bar_s)
Z_tilde_train = Z_hat_shifted + R_hat_train
```

Frozen denoiser：

```text
timestep_embedding = fixed sinusoidal dim 32
denoiser_input = concat[x_s(64),Z_source(64),time_embedding(32)]
denoiser = Linear(160,128) -> SiLU -> Linear(128,128) -> SiLU -> Linear(128,64)
```

Schedule：

```text
S = 20
beta_s = linspace(1e-4,2e-2,20)
alpha_s = 1-beta_s
alpha_bar_s = product(alpha_1..alpha_s)
training s ~ UniformInteger(1,20) independently per valid batch/time cell
epsilon ~ Normal(0,I)
```

Inference 必须运行 exact 20-step DDPM reverse chain，不得改用 DDIM、eta、clipping、dynamic threshold、learned variance 或单步 x0。

### 5.4 Decoder、loss 与 score

```text
decoded_source = Decoder(Z_source)
decoded_shifted_train = Decoder(Z_tilde_train)

L_source_rec = MeanValid((decoded_source-y_source_raw)^2)
L_shifted_observed_rec = MeanValid_j=0..T-2((decoded_shifted_train[:,j,0]-y_teacher_shifted_raw[:,j,0])^2)
L_history_reconstruction = 0.5*(L_source_rec+L_shifted_observed_rec)
L_forecast = MeanBatch((decoded_shifted_train[:,T-1,0]-forecast_y)^2)
L_rec = L_history_reconstruction+L_forecast
L_koop = MeanValid_B,T,D((Z_teacher_shifted-Z_hat_shifted)^2)
L_diff = MeanValid_B,T,D((epsilon_hat-epsilon)^2)
L_total_R2 = L_rec+L_koop+L_diff
```

其中 `forecast_y=Y_rank_primary_raw(t)`，T=10 的 forecast index 固定 9；shifted observed reconstruction 只覆盖 index 0..8。
`L_forecast` 只能在 `L_rec` 中出现一次。MeanValid 是 element/latent mean 后 valid batch/time-cell mean；不得 time sum 或按长度加权。

Inference 每个 row/seed 使用 8 个独立 residual draws：

```text
score_draw[draw_id] = Decoder(Z_hat_shifted + R_hat_draw)[:,T-1]
seed_score = arithmetic_mean(score_draw[0..7])
ensemble_score = arithmetic_mean(seed_score_20260713..20260715)
```

Draw seed：

```text
uint64_prefix(SHA256(run_id|R2_REAKA_DIFFUSION|model_seed|instrument|decision_date|draw_id)) mod 2^63
```

每个 row-key 独立 generator；score 必须对 batch/order 完全不变。

### 5.5 Shape、initialization 与 finite contract

必须 exact 继承 21A `tensor_shape_contract.csv`、`train_teacher_inference_graph_contract.csv` 和初始化 contract。最低 shapes：

```text
y_source [B,10,1]
x_source [B,10,157]
H_y,H_x,Z_source,Z_teacher,Z_hat,R_target [B,10,64]
selector [B,10,4]
K_codebook [4,64,64]
K_selected [B,10,64,64]
inference residual draws [B,8,10,64]
decoded draws [B,8,10]
score [B]
```

Constructor default initialization 必须全部覆盖。每个 seed 使用唯一 CPU `weight_init_generator=model_seed+53`，注册、显式重初始化与 RNG
draw 顺序 exact 为：

```text
1. return_encoder
2. feature_encoder
3. gate_linear
4. selector_linear
5. K_codebook
6. decoder
7. denoiser_linear_1
8. denoiser_linear_2
9. denoiser_linear_3
```

两个 LSTM 均按 PyTorch `input|forget|cell|output` gate order：`weight_ih_l0` 用一次 full-tensor Xavier-uniform draw；
`weight_hh_l0[gH:(g+1)H,:]` 按 `g=0,1,2,3` 各作一次 orthogonal draw；两个 bias 先清零，只设置
`bias_ih_l0[H:2H]=1`。每个 Linear 按上述顺序先 Xavier-uniform weight、后 bias 清零。`K_codebook` 以一次 shape `[4,64,64]`
full-tensor `Normal(0,0.01)` draw 后加 broadcast identity；operator index 固定 `0,1,2,3`。禁止逐 operator 改变 draw 顺序。

Model attribute/optimizer parameter registration order必须与上表一致；optimizer 接收该 registration order 的 trainable parameters，不得使用
set、name sort 或动态 module discovery 重排。Resolved config、checkpoint manifest 与 synthetic fixture 必须绑定 canonical
`initialization_contract_sha256` 和 exact ordered parameter-name list hash。所有 tensor/model construction 先在 CPU 完成，再迁移 CUDA。

任一 NaN/Inf、shape mismatch、implicit broadcast、teacher leakage 或 nondeterministic reordered inference 均 fail closed。

## 6. Training、checkpoint selection 与 search budget

### 6.1 Exact primary jobs

```text
planned_primary_job_n = 3
arm_id = R2_REAKA_DIFFUSION
model_seeds = [20260713,20260714,20260715]
primary_config_n = 1
sensitivity_job_n = 0
hyperparameter_search_allowed = false
best_seed_primary_allowed = false
```

不得运行 21A 的 S01-S06 sensitivities，不得在 OOM/NaN/弱 RankIC 后改变 latent width、operator count、diffusion steps、loss weight、
learning rate、feature route、target transform 或 draw count。

### 6.2 Frozen optimizer/config

```yaml
architecture:
  lookback_T: 10
  feature_dim: 157
  latent_dim: 64
  lstm_layers: 1
  n_operator: 4
  gumbel_tau_start: 1.0
  gumbel_tau_end: 0.1
  gumbel_anneal: linear_by_optimizer_step
  gumbel_train_mode: soft
  gumbel_inference_mode: hard_argmax
  diffusion_steps: 20
  beta_start: 0.0001
  beta_end: 0.02
  inference_residual_draws: 8
loss:
  rec_weight: 1.0
  koop_weight: 1.0
  diff_weight: 1.0
training:
  precision: fp32
  amp: false
  optimizer: AdamW
  learning_rate: 0.001
  weight_decay: 0.00001
  adam_betas: [0.9,0.999]
  adam_eps: 0.00000001
  adam_amsgrad: false
  adam_foreach: false
  adam_fused: false
  adam_capturable: false
  adam_maximize: false
  adam_differentiable: false
  scheduler: none
  gradient_clip_global_l2: 1.0
  gradient_clip_foreach: false
  gradient_clip_error_if_nonfinite: true
  zero_grad_set_to_none: true
  max_epochs: 100
  early_stopping_patience: 10
  evaluate_every_epochs: 1
  checkpoint_tie_break: earliest_epoch
  train_shuffle_each_epoch: true
  dataloader_drop_last: false
  dataloader_num_workers: 0
  dataloader_pin_memory: false
  dataloader_persistent_workers: false
  dataloader_prefetch_factor: null
  device_transfer_non_blocking: false
  validation_inference_batch_size: selected_batch_size
  late_inference_batch_size: selected_batch_size
  sample_weight: 1.0
  day_balanced_loss: false
```

Optimizer 使用一个且仅一个 parameter group，成员为 Section 5.5 ordered trainable parameter list，包含 bias、LSTM、K 和 denoiser，全部共享
同一 learning rate/weight decay；禁止 no-decay bias/norm 特例、name sort、set 或多 group。Exact step：

```text
optimizer.zero_grad(set_to_none=True)
L_total_R2.float().backward()
torch.nn.utils.clip_grad_norm_(ordered_parameters,max_norm=1.0,norm_type=2.0,
                               error_if_nonfinite=True,foreach=False)
optimizer.step()   # no closure
```

AdamW constructor 必须显式传入上述 betas/eps/weight_decay/amsgrad/foreach/fused/capturable/maximize/differentiable；禁止依赖 PyTorch default。
AMP/scaler、gradient accumulation、closure、scheduler 和 post-step clipping 均禁止。Resource probe 与 production 使用同一 constructor、single-group
和 step order。

每个 job 固定：

```text
steps_per_epoch = ceil(train_n/selected_batch_size)
planned_total_steps = max_epochs * steps_per_epoch
optimizer_step_index = k, k in [0, planned_total_steps-1]
tau(k) = 1.0 - (1.0-0.1) * k/(planned_total_steps-1)
```

`tau(k)` 在第 `k` 次 forward 前计算并 clip 到 `[0.1,1.0]`；本阶段 `planned_total_steps>1`，否则 config fail。Early stop 不重定义
denominator，resume/retry 不重置 `k`。每个实际 optimizer step 只递增一次；validation 不递增。

### 6.3 Mechanical GPU batch ladder

```text
batch_size_candidates = [256,128,64,32,16]
selected_batch_size = largest candidate passing full R2 forward+backward+optimizer-state+8-draw inference dry-run
peak_reserved_memory <= 0.90*device_total_memory
minimum_batch_size = 16
```

Resource probe 在任何 production job 前只运行一次：使用独立 `resource_probe_seed=21000053`、synthetic finite zero tensors、exact target
device/runtime、候选 batch 的完整 shape，不读取 label/score/RankIC。每个候选在 fresh execve process 中从清空的 CUDA peak counters 开始；必须
同时覆盖一轮 forward、backward、AdamW state allocation/step 和 8-draw 20-step inference。选出的单一 `selected_batch_size` 被写入
`resource_probe_audit.csv`，并由三个 primary seeds 共享。只允许因 OOM/peak cap 按 256→128→64→32→16 下降；不能依据 loss/RankIC
选择 batch。若 16 不通过，stage not evaluable；不得按 seed 分别选择 batch。

Probe 将 `resource_probe_seed` 当作 synthetic model seed，并派生 numpy/torch/weight/gumbel/diffusion streams 分别为 `seed+11,+23,+53,+71,+89`；
module/init/draw/optimizer order与 production exact。Synthetic row `i` 固定
`instrument=__R2_RESOURCE_PROBE_{i:06d},decision_date=1970-01-02`，inference draw seed继续使用 Section 5.4 hash公式但
`run_id=21C_R2_RESOURCE_PROBE`。Memory gate只比较未舍入 raw bytes：

```text
peak_reserved_memory_bytes * 100 <= device_total_memory_bytes * 90
```

MiB/peak fraction只报告，不参与边界判定。

### 6.4 Randomness

Exact 继承 21A `seed_and_randomness_freeze.csv`：

```text
python_seed = model_seed
numpy_seed = model_seed+11
torch_seed = model_seed+23
dataloader_seed = model_seed+37
weight_init_seed = model_seed+53
gumbel_seed = model_seed+71
diffusion_train_noise_seed = model_seed+89
```

Train shuffle seed 按 `dataloader_seed+epoch_index` 派生。Deterministic algorithms、cuDNN deterministic、TF32/cublas workspace 等 runtime
flags 必须与 approved 21A/21B fingerprint exact-match。

每个 stream 使用独立 CPU generator，禁止共享/跳 draw。Epoch `e` 从 0 开始，以 `dataloader_seed+e` 生成一次 train-row `randperm`；最后
不足 batch 保留。每个 optimizer step 对实际 batch size `B_actual`，按以下顺序生成并 transfer 到 model device：

```text
1. gumbel U = Uniform(0,1), one full tensor draw [B_actual,T,4]
2. gumbel_noise = -log(-log(clamp(U,1e-10,1-1e-10)))
3. diffusion s = UniformInteger(1,20), one full tensor draw [B_actual,T]
4. epsilon = Normal(0,1), one full tensor draw [B_actual,T,64]
```

步骤 1 使用 gumbel generator；步骤 3/4 顺序共享 diffusion-train generator。Validation 不消费这些 generators，failed/retried batch 禁止静默
继续旧 stream；整个 production run 必须作废并以新 version/root 重跑。Inference 只使用 Section 5.4 的 row-key/draw-id generator。

### 6.5 Selection-only early fold

每 epoch 结束只对 validation_early 运行 inference graph并计算 mean daily RankIC：

```text
selection_metric = validation_early_mean_daily_RankIC
strict_improvement = current > best
tie = earliest epoch
patience = 10 consecutive non-improvements
```

初始化 `best_metric=-inf,best_epoch=null,non_improvement_count=0`。每个 epoch metric finite 且严格大于 best 时更新 in-memory CPU best-state
copy并将 counter 清零；否则 counter 加一。禁止写 intermediate checkpoint file；job 结束后只把最终 best-state close/reopen/hash-verify 一次。
完成当前 epoch audit 后，counter 首次等于 10 即停止，禁止运行下一 epoch。Epoch 1 metric
非 finite 直接 fail，不得由 `-inf` 吸收。达到 epoch 100 时保留此前 best；best_epoch 仍为 null 时 job fail。

selection worker 不得打开 validation_late path、读取 M1/M3 late outcome、计算 paper table或 Top30。任何 attempt 必须被 filesystem/access
wrapper 拒绝并使 worker fail。

Checkpoint 在 late readout 前仅为 `provisional_selected`。三个 checkpoint 全部存在、hash/semantic state/eligibility 前置条件通过后，parent
才写 `pre_gate_r2_checkpoint_bundle_manifest.json`。

## 7. Fresh-process boundary、checkpoint seal 与 late readout

### 7.1 Selection worker

必须通过 fresh `execve` interpreter 启动，不能 fork 继承 controller/model state。Parent 在 child exit 后写 exit record，验证：

```text
exit_code = 0
status = pass
validation_late_open_count = 0
historical_holdout_open_count = 0
produced_checkpoint_n = 3
training_job_count = 3
fit_entrypoint_call_count = 3
optimizer_step_count = sum(actual_optimizer_steps_across_three_jobs) > 0
```

Worker 不得自己写 parent-success record。

### 7.2 Pre-gate immutable seal

Seal 必须绑定：

```text
requirement/config/upstream hashes
feature/split/normalizer/panel hashes
teacher extension manifest/hash
three R2 checkpoint byte+semantic hashes
training registry/curves/search accounting
selection validation_early scores
selection worker parent exit record
selection late-open count=0
historical holdout all outcome counts=0
```

Seal 后禁止重训、换 epoch、换 seed/config、删除失败记录、修改 checkpoint 或 normalizer。

### 7.3 Late readout worker

必须是新 interpreter、inference-only module whitelist。只允许：

```text
load three sealed R2 state_dicts
open validation_late source panel/cache
run hard selector + 8-draw DDPM inference
write seed/ensemble scores and access audit
exit
```

禁止 import/call optimizer、loss.backward、train mode、fit/update、checkpoint save、selection function。Parent exit record要求：

```text
fit_or_update_call_count = 0
backward_call_count = 0
optimizer_step_count = 0
checkpoint_write_count = 0
validation_late_open_count >= 1
historical_holdout_open_count = 0
```

### 7.4 Checkpoint eligibility

Late worker 正常退出且 score bytes/hash 验证后，parent 才能生成 exact 3-row `checkpoint_eligibility_manifest.json`。每个 seed 必须同时满足：

```text
candidate_status_before_late = provisional_selected
selection_fold = validation_early
checkpoint_hash_and_semantic_hash_verified = true
selection_worker_status = pass
late_readout_worker_status = pass
validation_early_complete_day_n >= 80
validation_late_complete_day_n >= 80
validation_full_complete_day_n >= 200
validation_early_score_coverage = 1.0
validation_late_score_coverage = 1.0
nonfinite_score_n = 0
duplicate_or_missing_row_key_n = 0
historical_holdout_all_access_count = 0
```

全部 conjunct 成立时 `checkpoint_eligibility_status=eligible_frozen`；否则为 `provisional_not_evaluable`，并将所有失败 conjunct 的 gate ID
按 ASCII 排序写入 `eligibility_blocking_reasons` JSON array。只有三个 seeds 全部 `eligible_frozen`，`checkpoint_eligibility_gate=pass`；否则
进入 training/late-readout not-evaluable state，不得计算 direction/ordering gate。Eligibility 只判断 coverage/integrity，不依据 RankIC 正负。

### 7.5 Comparator freeze

M1/M3 late scores必须从 corrected 21B sealed artifacts读取；不得 reload 后重新推断、重新 ensemble、改 score scale 或挑较弱 comparator。
Paired metrics 使用 R2/M1/M3 对同一 `U_t_decision` 的完整 score rows。

## 8. Metrics、stability 与 paper-proxy Top30

### 8.1 Daily RankIC

对 complete decision day：

```text
score_rank = average_rank(score,ascending=true)
label_rank = average_rank(Y_rank_primary,ascending=true)
RankIC_d = Pearson_float64(score_rank,label_rank)
```

完整日要求：

```text
U_t_resolved_n = U_t_decision_n >= 100
all R2/M1/M3 ensemble scores finite and nonconstant
label finite and nonconstant
score coverage = 1.0 for every required arm
```

任一失败整日 `not_evaluable`；不得删 row、填 0、jitter ties 或取 arm intersection。

Summary：

```text
mean_daily_RankIC = arithmetic mean over complete days
std_daily_RankIC = sample std ddof=1
RankICIR = mean/std
positive_day_rate = count(RankIC_d>0)/complete_day_n
max_abs_day_contribution = max_d(abs(RankIC_d/complete_day_n))
```

### 8.2 R2 direction/stability gate

R2 ensemble 必须同时满足：

```text
validation_full_complete_day_n >= 200
validation_early_complete_day_n >= 80
validation_late_complete_day_n >= 80
validation_late_ensemble_score_coverage_rate = 1.0
ensemble_mean_RankIC_late > 0
positive_late_seed_n >= 2 of 3
positive_leave_one_late_month_out_n >= 5 of 6
max_late_month_abs_contribution_share <= 0.50
NaN_or_inf_count = 0
```

Late month IDs 固定 `2023-07..2023-12`。对每个 month `m`：

```text
LOMO_mean_m = mean(RankIC_d for complete late days with month(d) != m)
positive_leave_one_late_month_out_n = count_m(LOMO_mean_m > 0)
late_month_contribution_m = sum(RankIC_d for complete late days in m) /
                            validation_late_complete_day_n
max_late_month_abs_contribution_share = max_m(abs(late_month_contribution_m)) /
                                        sum_m(abs(late_month_contribution_m))
```

LOMO 分母无剩余日、任一月无 complete day 或 contribution 绝对值和为 0 时 gate fail。Validation full/early 只报告，不替代 late gate。

### 8.3 Paired comparator readout

Primary local ordering contrasts：

```text
P1 = R2_REAKA_DIFFUSION - M1_LIGHTGBM_ALPHA158
P2 = R2_REAKA_DIFFUSION - M3_GATED_DUAL_PATH_LSTM
unit = paired complete decision-day RankIC delta
scope = validation_late
```

Hard ordering flag只使用同日 point estimate：

```text
relative_advantage_point_ordering_observed = Mean(P1)>0 AND Mean(P2)>0
```

另输出 `m=2` one-sided stationary-bootstrap/Holm diagnostic。对按 decision date ASC 的 paired delta `x[0..n-1]`，使用 Politis-Romano
circular stationary bootstrap：restart probability `p=1/20`；每个 replicate 的首 index 与每次 restart index 均从 `[0,n)` 均匀抽取，
不 restart 时 index=`(index+1) mod n`，直到长度 n。RNG 固定 `numpy.random.Generator(PCG64(20260715))`，先完整生成 P1 的 5000
replicates，再生成 P2。Null-centered `x0=x-mean(x)`，one-sided p 固定为：

```text
p_raw = (1 + count(mean(x0_bootstrap) >= observed_mean(x))) / 5001
```

Holm 按 raw p ASC、tie `contrast_id` ASC，adjusted p 使用 step-down cumulative maximum并 clip 1。该 diagnostic 不成为 validation hard
gate，不得写成 confirmatory inference。

### 8.4 Paper-proxy Top30 gross diagnostic

对 R2/M1/M3 ensemble，在每个 complete validation_late day：

```text
rank raw score DESC, tie canonical instrument ASC
select exact TopK=30
daily_top30_gross_return = arithmetic_mean(Y_rank_primary of selected 30)
daily_equal_weight_gross_return = arithmetic_mean(Y_rank_primary over U_t_decision)
```

Summary：

```text
cumulative_gross = product(1+r_d)-1
annualized_gross = product(1+r_d)^(252/n)-1
annualized_sharpe = sqrt(252)*mean(r_d)/std(r_d,ddof=1)
mean_top30_minus_equal_weight
positive_day_rate
```

该 proxy 不含 next-open、涨跌停 fill、成本、现金、turnover constraint 或连续 executable NAV；名称和报告中必须含 `paper_proxy` 与
`gross_close_to_close`。不得写为 PnL、AR reproduction 或 executable return。Top30 不进入 hard gate。

### 8.5 Paper reference table

静态参考至少包含论文 Table 1：

| paper market | model | RankIC | RankICIR |
|---|---|---:|---:|
| CSI300 | LightGBM | 0.016 | 0.148 |
| CSI300 | LSTM | 0.027 | 0.221 |
| CSI300 | REAKA | 0.064 | 0.568 |
| S&P500 | LightGBM | 0.013 | 0.110 |
| S&P500 | LSTM | 0.018 | 0.201 |
| S&P500 | REAKA | 0.061 | 0.541 |

Local mapping：M1 可标 `closest_local_lightgbm_proxy`；R2 可标 `paper_architecture_grounded_project_adaptation`；M3 是 project direct
comparator；M2 不得映射 paper LSTM 或 `w/o GM`。跨市场/时期数值只并排，不计算 pass/fail、百分比复现率或误差阈值。

## 9. Gates、decision state 与后续边界

### 9.1 Causal gates

```text
execution_authorization_gate
scope_restart_gate
scope_override_gate
upstream_21b_success_gate
upstream_21b_contract_erratum_gate
upstream_paper_lineage_erratum_gate
upstream_hash_and_file_set_gate
dependency_runtime_gate
input_panel_integrity_gate
train_validation_firewall_gate
historical_holdout_zero_access_gate
teacher_materialization_gate
architecture_shape_gate
teacher_isolation_gate
loss_and_score_index_gate
seed_determinism_gate
gpu_memory_gate
training_completion_gate
pre_gate_bundle_hash_gate
late_readout_process_gate
checkpoint_eligibility_gate
score_coverage_gate
rankic_implementation_gate
finalize_transaction_gate
r2_direction_stability_gate
```

两个 seal meta-gate 不覆盖 causal decision precedence：

```text
output_manifest_hash_gate       = P5 success-candidate bundle integrity
failure_bundle_integrity_gate   = P0..P4 blocked/failure bundle integrity
```

P5 固定 `output_manifest_hash_gate=pass,failure_bundle_integrity_gate=not_run`。P0-P3 固定
`output_manifest_hash_gate=not_run,failure_bundle_integrity_gate=pass`。P4 若因 metric/report transaction 在 success-candidate seal 前失败，则
output gate=`not_run`；若因 success-candidate manifest/hash verification 失败，则 output gate=`fail`；两种 P4 都必须
`failure_bundle_integrity_gate=pass` 才能发布。若 failure-bundle 自身 integrity fail，禁止声称任何 sealed profile/state，只允许 stderr/parent
process error 和未发布 `.building` cleanup evidence。
`finalize_transaction_gate` 在 P0-P3 为 `not_run`、P5 为 `pass`；P4 metric/report transaction failure 时为 `fail`，仅 success-candidate
manifest/hash verification failure时可为 `pass`。

### 9.2 Local validation sanity classification

```text
r2_direction_supported = r2_direction_stability_gate == pass
relative_advantage_point_ordering_observed = Mean(P1)>0 AND Mean(P2)>0

full_reaka_local_validation_point_ordering_observed =
    r2_direction_supported
    AND relative_advantage_point_ordering_observed
```

### 9.3 Unique stage decision

按 first-match：

```text
1. 21C_FULL_blocked_by_missing_or_invalid_human_authorization
2. 21C_FULL_blocked_by_upstream_contract_or_runtime
3. 21C_FULL_input_or_access_firewall_blocked
4. 21C_FULL_teacher_or_architecture_pipeline_not_evaluable
5. 21C_FULL_training_or_late_readout_not_evaluable
6. 21C_FULL_finalize_or_manifest_integrity_blocked
7. 21C_FULL_r2_direction_not_supported
8. 21C_FULL_r2_direction_supported_without_local_baseline_ordering
9. 21C_FULL_local_validation_point_ordering_observed
```

Exact first-match gate mapping：

```text
state 1 iff fail(any execution_authorization,scope_restart,scope_override)
state 2 iff fail(any upstream_21b_success,upstream_21b_contract_erratum,
                    upstream_paper_lineage_erratum,upstream_hash_and_file_set,dependency_runtime)
state 3 iff fail(any input_panel_integrity,train_validation_firewall,historical_holdout_zero_access)
state 4 iff fail(any teacher_materialization,architecture_shape,teacher_isolation,
                    loss_and_score_index,seed_determinism)
state 5 iff fail(any gpu_memory,training_completion,pre_gate_bundle_hash,
                    late_readout_process,checkpoint_eligibility,score_coverage)
state 6 iff fail(any rankic_implementation,finalize_transaction) or fail(output_manifest_hash)
state 7 iff all prior gates pass and r2_direction_stability_gate=fail
state 8 iff r2_direction_stability_gate=pass and relative_advantage_point_ordering_observed=false
state 9 iff full_reaka_local_validation_point_ordering_observed=true
```

上述 `fail(any ...)` 只把 `status in {fail,not_evaluable}` 视为实际 blocking failure；`not_run` 不触发任何后续或更早 state。一旦按 causal
gate order 找到首个实际 blocking failure，所有因它而未执行的 downstream gates 保留 `not_run`，并通过 reason 精确记录
`not_run_due_to_prior_gate:<gate_id>`，不得伪造 pass。`not_run` 只能出现在首个实际 blocking gate 之后；若任一 gate 在首个 failure 之前为
`not_run`，或不存在实际 failure 却仍有 causal gate=`not_run`，则 artifact profile/state 不可发布，`failure_bundle_integrity_gate=fail`，只能保留
未密封 `.building` cleanup evidence。Section 9.1、gate evidence 与 first-match group 的 gate order 必须完全按 state 1→6 的 precedence 排列；
`r2_direction_stability_gate` 最后。

State 8/9 都只是 validation-only architecture sanity。State 9 仅表示本地 point ordering，不得命名为论文结果复现；它不支持任何
individual module claim。State 8 说明完整架构有正方向但未观察到本地 comparator ordering；State 7 说明本地 validation 方向不支持。
State 6 只表示 finalize/hash closure 失败，禁止复用已计算但未密封的 metric。

所有 state：

```text
historical_holdout_readout_authorized = false
next_requirement_generation_authorized = false
next_requirement_execution_authorized = false
policy_training_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

任何后续 historical test、nested ablation、execution bridge 或 forward confirmation 都必须由人新建 requirement，不能由本 runner 自动触发。

## 10. Required artifacts 与 schemas

### 10.1 Artifact superset

```text
preflight/preflight_access_audit.csv
preflight/upstream_21b_authorization_and_hash_audit.csv
preflight/scope_override_audit.csv
preflight/scope_restart_decision_audit.csv
preflight/paper_lineage_erratum_audit.csv
preflight/resolved_config.yaml
materialized/r2_train_teacher_sequence_index.parquet
materialized/r2_train_teacher_return_panel.f32.memmap
materialized/r2_input_extension_manifest.json
materialized/materialization_access_audit.csv
materialized/materialization_failure_evidence.csv
training/model_search_accounting_manifest.csv
training/resource_probe_audit.csv
training/training_run_registry.csv
training/seed_level_training_curves.csv
training/training_failure_evidence.csv
training/checkpoints/R2_REAKA_DIFFUSION/seed_20260713/state_dict.pt
training/checkpoints/R2_REAKA_DIFFUSION/seed_20260714/state_dict.pt
training/checkpoints/R2_REAKA_DIFFUSION/seed_20260715/state_dict.pt
training/checkpoint_manifest.json
training/selection_worker_exit_record.json
training/selection/validation_early_prediction_scores.parquet
training/pre_gate_r2_checkpoint_bundle_manifest.json
training/readout/validation_late_prediction_scores.parquet
training/late_readout_worker_exit_record.json
training/late_readout_failure_evidence.csv
training/checkpoint_eligibility_manifest.json
training/model_parameter_compute_latency_audit.csv
training/training_access_audit.csv
historical_design_holdout_access_audit.csv
daily_rankic_readout.csv
rankic_stability_and_concentration_audit.csv
paired_rankic_comparison.csv
stationary_bootstrap_pair_diagnostic.csv
paper_proxy_top30_daily.csv
paper_proxy_top30_summary.csv
paper_reference_comparison.csv
artifact_profile_registry.csv
stage_status_registry.csv
finalize_failure_evidence.csv
gate_evidence_21c_full.csv
21C_full_reaka_pit_proxy_replication_decision.csv
21C_full_reaka_pit_proxy_replication_report.md
semantic_reproducibility_manifest.json
manifest_21c_full_reaka_pit_proxy_replication.json
output_hashes_21c_full_reaka_pit_proxy_replication.json
```

### 10.2 Core exact schemas

除 Parquet/memmap/JSON 另有声明外，CSV 使用 UTF-8、LF、逗号分隔、header exact、无 index；null token 固定为空字符串，boolean
固定 lowercase `true|false`，float 使用 round-trip decimal，日期 `YYYY-MM-DD`，timestamp RFC3339 UTC。禁止 extra columns。除非某个 schema
对同名或 domain-specific status 字段另行给出 exact 枚举，CSV check/audit 的通用 `status` 只允许
`pass|fail|not_run|not_evaluable`；仅当 schema 同时包含 `reason` 时，pass 的 reason 为空、其他状态 reason 非空。JSON manifest 的
`status`、CSV 的 `job_status/run_status/selection_status/metric_day_status/checkpoint_eligibility_status` 等均服从各自显式枚举，不受通用
check-status 枚举覆盖；因此 pre-gate manifest 的 `status=sealed` 是合法且唯一的 success 值。

`preflight/resolved_config.yaml` top-level keys exact 为：

```text
schema_version,run_id,requirement_version,requirement_sha256,
execution_authorization_path,authorization_observation,authorization_schema_status,
execution_authorization_sha256,
scope_restart_decision_path,scope_restart_decision_sha256,
approved_21c_implementation,approved_21b,approved_21a_lineage,paths,feature_route,splits,
architecture,loss,training,randomness,resource_probe,metrics,gates,artifact_profiles
```

`authorization_observation` exact 使用 Section 1 的 `MISSING|lowercase_sha256(bytes)`；`authorization_schema_status` 只允许
`missing|invalid|pass`。状态规则：

```text
authorization missing:
  execution_authorization_sha256 = null
  scope_restart_decision_path/hash = null
  approved_21c_implementation = null
  approved_21b = null
  approved_21a_lineage = null

authorization present but schema/hash invalid:
  execution_authorization_sha256 = actual full-byte SHA256
  scope_restart_decision_path/hash = null
  approved_21c_implementation = null
  approved_21b = null
  approved_21a_lineage = null

authorization schema pass:
  execution_authorization_sha256 = actual full-byte SHA256
  scope_restart_decision_path/hash = exact authorization pins
  approved_21c_implementation = exact object copied from approved_21c_runner/config/test_sha256 pins
  approved_21b = exact object copied from all approved_21b_* authorization pins
  approved_21a_lineage = non-null iff upstream_21b_success_gate=pass, else null
```

Non-null `approved_21c_implementation` object keys exact 为：

```text
runner_path,runner_sha256,config_path,config_sha256,test_path,test_sha256
```

三个 path 分别固定为 Section 1 的 `runner_file/config_file/test_file`，三个 hash 分别复制 authorization 的
`approved_21c_runner_sha256/approved_21c_config_sha256/approved_21c_test_sha256`；禁止把 execution authorization hash 写回 source config。

Non-null `approved_21a_lineage` exact 包含 approved 21A root/version、原 registry hash 和 paper-lineage erratum path/hash；其余 mapping 的 leaf
keys/values exact 来自 Sections 1、4、5、6、8、9、11。YAML null 必须写 canonical `null`；禁止空字符串代替 null、YAML anchors、aliases、
自定义 tag、environment interpolation、extra key 或运行时默认补值。Resolved bytes 在任何 model/value open 前冻结。

以下 check-audit 文件共享 exact schema：

```text
preflight/upstream_21b_authorization_and_hash_audit.csv
preflight/scope_override_audit.csv
preflight/scope_restart_decision_audit.csv
preflight/paper_lineage_erratum_audit.csv

check_id,stage,artifact_path,expected_value,observed_value,status,reason
```

Sort：`check_id` ASC；check-id registry exact 为：

```text
upstream_21b_authorization_and_hash_audit = [
  authorization_observation_recorded,
  authorization_schema_exact,
  authorization_reviewer_human,
  authorization_requirement_sha256_match,
  approved_21c_runner_sha256_match,
  approved_21c_config_sha256_match,
  approved_21c_test_sha256_match,
  approved_21b_root_canonical_versioned,
  approved_21b_requirement_version_match,
  approved_21b_requirement_sha256_match,
  approved_21b_runner_sha256_match,
  approved_21b_config_sha256_match,
  approved_21b_test_sha256_match,
  approved_21b_decision_sha256_match,
  approved_21b_manifest_sha256_match,
  approved_21b_output_hashes_sha256_match,
  approved_21b_gate_evidence_sha256_match,
  approved_21b_pre_holdout_bundle_hash_match,
  approved_21b_semantic_payload_bundle_hash_match,
  approved_21b_contract_erratum_id_match,
  approved_21b_contract_erratum_path_match,
  approved_21b_contract_erratum_sha256_match,
  approved_21b_contract_erratum_schema_exact,
  runtime_access_event_log_path_canonical,
  runtime_access_event_log_sha256_match,
  runtime_access_event_log_manifest_covered,
  runtime_access_event_log_schema_exact,
  runtime_access_event_seq_contiguous,
  runtime_counter_evidence_sha256_match,
  runtime_counter_evidence_source_log_pin_match,
  runtime_counter_aggregation_contract_exact,
  runtime_counter_recomputed_from_raw_log,
  post_cutoff_value_token_materialization_zero,
  post_cutoff_outcome_value_decode_zero,
  runtime_counter_collection_mode_exact,
  historical_holdout_all_counters_zero,
  corrected_21b_output_file_set_exact
]

scope_override_audit = [
  authorization_scope_override_exact,
  approved_route_filename_exact,
  sealed_upstream_files_not_rewritten
]

scope_restart_decision_audit = [
  scope_restart_file_present,
  scope_restart_path_canonical,
  scope_restart_sha256_match,
  scope_restart_schema_exact,
  scope_restart_requirement_sha256_match,
  scope_restart_routes_exact,
  scope_restart_estimands_exact,
  scope_restart_reviewer_human,
  scope_restart_holdout_false,
  scope_restart_execution_false,
  scope_restart_status_exact
]

paper_lineage_erratum_audit = [
  upstream_21a_registry_sha256_match,
  paper_lineage_erratum_path_canonical,
  paper_lineage_erratum_sha256_match,
  paper_lineage_erratum_schema_exact,
  paper_lineage_erratum_manifest_covered,
  paper_lineage_affected_arm_m2_exact,
  paper_lineage_corrected_role_exact,
  paper_lineage_paper_equivalence_flags_false,
  paper_lineage_gate_eligible_false,
  paper_lineage_reviewer_and_status_exact
]
```

Resolved config 必须逐数组 exact 复制；CSV row set必须与对应数组相等，不允许运行时增删、合并或改名。某个较早 check fail 后，其余仍保留
row但 `status=not_run`。Section 4.5 的四个 access-audit 文件统一 exact schema：

```text
stage,process_role,path,artifact_sha256,access_scope,row_scope,value_scope,
allowed,row_n,first_key,last_key,reason
```

Sort：`stage,process_role,path,access_scope,row_scope,value_scope`；拒绝访问也必须记录，`allowed=false,row_n=0`。

`materialized/r2_train_teacher_sequence_index.parquet` exact schema：

```text
sample_row_id:int64
instrument:string
decision_date:date32
teacher_position:int8
teacher_date:date32
return_source_kind:string          # source_shift|forecast_label
return_source_position:int8 nullable
return_panel_offset:int64 nullable
feature_source_kind:string         # source_shift|approved_feature_cache
feature_source_position:int8 nullable
feature_cache_row_offset:int64
```

Sort：`sample_row_id,teacher_position`；每个 train sample exact 10 rows，position exact `0..9`；position 9 的 return source 必须是
`forecast_label`、feature source 必须是 `approved_feature_cache`。`r2_train_teacher_return_panel.f32.memmap` 为 C-contiguous little-endian
float32、shape `[train_row_n,10,1]`，无 header。两者均禁止 validation rows。

`materialized/r2_input_extension_manifest.json` exact keys：

```text
schema_version,run_id,upstream_21b_output_root,upstream_21b_semantic_payload_bundle_hash,
source_sequence_index_path,source_sequence_index_sha256,source_return_panel_path,
source_return_panel_sha256,approved_feature_cache_manifest_sha256,train_row_n,
teacher_sequence_index_path,teacher_sequence_index_sha256,teacher_return_panel_path,
teacher_return_panel_sha256,teacher_return_panel_dtype,teacher_return_panel_shape,
teacher_row_key_hash,teacher_date_key_hash,feature_cache_offset_hash,
validation_teacher_row_n,materialization_access_audit_sha256,status
```

固定：`schema_version=21c_r2_input_extension_v1`、dtype=`little_endian_float32`、shape=`[train_row_n,10,1]`、
`validation_teacher_row_n=0`、`status=pass`。Canonical JSON 继承 21B：UTF-8、key sort、compact separators、无 NaN/Inf、LF 结尾。

四个 failure evidence CSV 共享 exact schema：

```text
check_id,failed_stage,failed_gate_id,attempt_id,worker_mode,worker_process_start_attempted,
artifact_path,error_class,
expected_value,observed_value,first_observed_at_utc,status,reason
```

适用路径为 `materialized/materialization_failure_evidence.csv`、`training/training_failure_evidence.csv`、
`training/late_readout_failure_evidence.csv`、`finalize_failure_evidence.csv`；sort `check_id,attempt_id,artifact_path`，至少一行且全部 status=fail。
`worker_mode` 只允许 `none|r2_selection|r2_late_readout`；非 worker failure 固定 `none,false`。

`training/model_search_accounting_manifest.csv` exact 3 rows：

```text
arm_id,model_seed,config_id,planned,primary_or_sensitivity,attempt_n,
selected_batch_size,job_status,checkpoint_produced,failure_reason
```

Sort：`arm_id,model_seed`；固定一个 arm、三个 seeds、`config_id=R2_PRIMARY_FROZEN`、`planned=true`、
`primary_or_sensitivity=primary`。`job_status` 只允许
`completed|early_stopped|failed_oom_at_min_batch|failed_nan_inf|failed_runtime|not_run_due_prior_job_failure|not_run_due_upstream_block`。

`training/resource_probe_audit.csv` exact 5 rows：

```text
candidate_order,batch_size,resource_probe_seed,device_fingerprint_sha256,
forward_pass,backward_pass,optimizer_state_step_pass,eight_draw_inference_pass,
oom_observed,peak_reserved_memory_bytes,device_total_memory_bytes,
peak_reserved_memory_mib,device_total_memory_mib,peak_fraction,
selection_status,reason
```

Sort `candidate_order=0..4` 对应 `256,128,64,32,16`；一旦出现第一条 `selection_status=selected`，后续候选必须
`selection_status=not_run`，之前均为 `rejected_oom_or_peak_cap`。`resource_probe_seed=21000053`。
`not_run` rows 的 pass/oom/memory fields 为 null、reason=`skipped_after_larger_batch_selected`；selected/rejected rows 的 raw-byte memory fields
必须 non-null。若五个均 rejected，则不存在 selected row并触发 P2。

`training/seed_level_training_curves.csv` exact schema：

```text
arm_id,model_seed,epoch,optimizer_step_end,train_loss_total,train_loss_rec,
train_loss_koop,train_loss_diff,validation_early_mean_rankic,
validation_early_complete_day_n,validation_early_score_coverage,
gumbel_tau_last_step,elapsed_seconds,peak_gpu_memory_mib,status,reason
```

Sort：`arm_id,model_seed,epoch`；每个已启动 job 从 epoch 1 连续递增，不允许跳号或 post-selection epoch。P2 若没有 production job 启动，
文件必须只有 header、0 data rows；否则 row set exact 等于每个已启动 seed 的实际完整 epoch range。P3-P5 每个 seed 至少一行且最大 epoch
exact 等于 training registry 的 final evaluated epoch。

`training_run_registry.csv`：

```text
run_id,arm_id,model_seed,config_sha256,feature_route_id,feature_dim,
train_row_n,validation_early_row_n,validation_late_row_n,selected_batch_size,
started_at_utc,ended_at_utc,final_evaluated_epoch,selected_epoch,selection_metric,
checkpoint_path,checkpoint_sha256,model_state_semantic_sha256,
parameter_count,initialization_contract_sha256,ordered_parameter_name_list_sha256,
actual_optimizer_step_n,peak_cpu_rss_mib,peak_gpu_memory_mib,training_wall_seconds,
data_pass_n,run_status,failure_reason
```

Canonical sort：`arm_id,model_seed`；P2-P5 exact 3 rows。未启动 job 仍保留 planned seed row，时间、epoch、checkpoint 与计数为空/0，
resource/preflight block 使用 `run_status=not_run_due_upstream_block`，较早 production seed failure 后的剩余 seeds 使用
`not_run_due_prior_job_failure`，failure reason 非空。`run_status` 枚举与 search accounting 的 `job_status` 一致。
Successful job 必须 `1 <= selected_epoch <= final_evaluated_epoch <= 100`；`run_status=early_stopped` iff final epoch<100且 patience counter=10，
否则正常跑满为 `completed`。

`checkpoint_manifest.json` 是 exact keys `schema_version,records` 的 JSON object；records 按 `arm_id,model_seed`，P2 为 0..3 条、P3/P4/P5
exact 3 条。每条 record：

```text
arm_id,model_seed,checkpoint_path,serialization_format,serialization_version,
selected_epoch,selection_fold,validation_early_metric_at_selection,
config_sha256,upstream_21b_semantic_payload_bundle_hash,
feature_cache_content_hash,split_hash,normalization_contract_hash,
train_row_key_hash,validation_early_row_key_hash,teacher_extension_hash,
parameter_count,initialization_contract_sha256,ordered_parameter_name_list_sha256,checkpoint_sha256,
model_state_semantic_sha256,runtime_fingerprint_sha256
```

State dict 只含 model parameters/buffers，不含 optimizer、epoch 或 dataloader。Semantic hash 按 parameter name ASC 和 CPU contiguous
little-endian `(name,dtype,shape,raw-bytes)`。

两个 worker exit record 由 parent 在 child 退出后写，exact JSON keys：

```text
schema_version,worker_mode,process_start_contract,worker_pid,command_argv_sha256,
resolved_config_sha256,started_at_utc,ended_at_utc,exit_code,
filesystem_whitelist_sha256,forbidden_import_or_call_count,
validation_late_open_count,historical_holdout_open_count,training_job_count,
fit_entrypoint_call_count,fit_or_update_call_count,backward_call_count,
optimizer_step_count,checkpoint_write_count,produced_checkpoint_n,
produced_artifact_paths,produced_artifact_hashes,status,reason
```

`process_start_contract` 只允许 `fresh_execve_interpreter|launch_failed_before_execve`。`launch_failed_before_execve` 时 `worker_pid,exit_code` 为
JSON null，全部 call/open/checkpoint count 为 0，produced arrays=`[]`，`status=fail,reason` 非空；该 record 是 parent-written launch disposition，
不是 child 自报 exit。

Selection success record 固定 `worker_mode=r2_selection,status=pass`，training/fit-entrypoint/checkpoint n 均为 3，
`fit_or_update_call_count=fit_entrypoint_call_count=3`（top-level fit entrypoint 次数，不是 optimizer step），late/holdout open 为 0。
`checkpoint_write_count=produced_checkpoint_n=3`，`backward_call_count=optimizer_step_count` 且等于 registry 三行 optimizer steps 之和。
P2 failed selection record 固定 `status=fail`，允许：

```text
0 <= training_job_count <= 3
fit_entrypoint_call_count = training_job_count
fit_or_update_call_count = fit_entrypoint_call_count
0 <= produced_checkpoint_n <= training_job_count
produced_checkpoint_n = len(checkpoint_manifest.records) = |Ck|
optimizer_step_count = sum(training_run_registry.actual_optimizer_step_n)
optimizer_step_count <= backward_call_count <= optimizer_step_count + 1
checkpoint_write_count = produced_checkpoint_n
```

Late success record 固定 `worker_mode=r2_late_readout,status=pass`，training-job/fit-entrypoint/fit-update/backward/optimizer/checkpoint-write count
全部为 0，late open>=1、
holdout open=0。P3 failed late record 固定 `status=fail`；禁止动作的 count 仍必须为 0，late open 允许 0..N 并记录实际值。两个 mode 的
`produced_artifact_paths` 均按 path ASC，其 hash array 同位置对应；禁止 extra keys。
`checkpoint_write_count` 定义为已 close、parent reopen并 hash-verified 的成功 checkpoint writes；失败/临时 write attempt 只进入 failure evidence。

`training/pre_gate_r2_checkpoint_bundle_manifest.json` exact keys：

```text
schema_version,run_id,requirement_sha256,resolved_config_sha256,
approved_21c_runner_sha256,approved_21c_config_sha256,approved_21c_test_sha256,
upstream_21b_semantic_payload_bundle_hash,feature_cache_content_hash,split_hash,
normalization_contract_hash,teacher_extension_hash,checkpoint_manifest_sha256,
checkpoint_paths,checkpoint_sha256s,model_state_semantic_sha256s,
training_run_registry_sha256,training_curves_sha256,search_accounting_sha256,
resource_probe_audit_sha256,validation_early_prediction_scores_sha256,
selection_worker_exit_record_sha256,selection_validation_late_open_count,
historical_holdout_all_access_count,bundle_hash,status
```

三个 checkpoint-related arrays 按 model seed ASC 对齐，exact 3 项；两个 access count 均为 0，`status=sealed`。`bundle_hash` 是除自身外
其余 key/value canonical JSON bytes 的 SHA256。

`training/checkpoint_eligibility_manifest.json` exact 3 rows encoded as JSON object with keys `schema_version,records`；每条 record keys：

```text
arm_id,model_seed,checkpoint_sha256,candidate_status_before_late,selection_fold,
checkpoint_hash_and_semantic_hash_verified,selection_worker_status,
late_readout_worker_status,validation_full_complete_day_n,
validation_early_complete_day_n,validation_late_complete_day_n,
validation_early_score_coverage,validation_late_score_coverage,nonfinite_score_n,
duplicate_or_missing_row_key_n,historical_holdout_all_access_count,
checkpoint_eligibility_status,eligibility_blocking_reasons
```

Records 按 `arm_id,model_seed`，枚举和 conjunct exact 遵循 Section 7.4；`eligibility_blocking_reasons` 为 JSON array，不使用拼接字符串。

Prediction parquet：

```text
arm_id:string
score_role:string          # seed|ensemble
model_seed:int64 nullable
fold:string                # validation_early|validation_late
decision_date:date32
instrument:string
score:float64
checkpoint_bundle_hash:string
row_key_hash:string
```

Sort：`fold,decision_date,instrument,score_role,model_seed`。R2 ensemble 只能有一条/row；seed exact 3 条/row。

`daily_rankic_readout.csv`：

```text
arm_id,score_role,model_seed,fold,decision_date,U_t_decision_n,U_t_resolved_n,
score_row_n,label_row_n,RankIC,metric_day_status,reason
```

Sort：`arm_id,score_role,model_seed,fold,decision_date`；`metric_day_status=evaluable` 时 RankIC finite，否则 RankIC 为空且 reason 非空。
P5 exact key universe 为：R2 的三个 seed+ensemble分别覆盖 validation_early、validation_late、由两者 byte-preserving union 得到的
validation_full；M1/M3 只含 inherited ensemble validation_late。每个 key 对对应 fold 的每个 decision date exact 一行，包括
not-evaluable day；禁止只输出 complete days。

`paired_rankic_comparison.csv`：

```text
contrast_id,left_arm,right_arm,fold,complete_day_n,left_mean_rankic,right_mean_rankic,
paired_mean_delta,positive_delta_day_rate,relative_advantage_point_ordering_observed,status
```

Sort：`contrast_id`；exact P1、P2 两行且 fold=`validation_late`。

`paper_proxy_top30_daily.csv`：

```text
arm_id,decision_date,U_t_decision_n,topk_n,topk_instrument_list_json,
top30_gross_close_to_close_return,equal_weight_gross_close_to_close_return,
top30_minus_equal_weight,score_coverage_rate,status
```

Sort：`arm_id,decision_date`；成功 profile 对每个 M1/M3/R2 complete day exact 一行，`topk_n=30`。

其余 readout/audit CSV exact schemas：

```text
training/model_parameter_compute_latency_audit.csv
arm_id,model_seed,parameter_count,trainable_parameter_count,checkpoint_bytes,
training_wall_seconds,inference_row_n,inference_wall_seconds,rows_per_second,
peak_cpu_rss_mib,peak_gpu_memory_mib,status,reason

rankic_stability_and_concentration_audit.csv
arm_id,score_role,model_seed,fold,audit_type,period_id,complete_day_n,
mean_rankic,rankic_std,rankicir,positive_day_rate,max_abs_day_contribution,
max_abs_month_contribution_share,status,reason

stationary_bootstrap_pair_diagnostic.csv
contrast_id,left_arm,right_arm,fold,complete_day_n,observed_paired_mean_delta,
bootstrap_replicate_n,mean_block_length,bootstrap_seed,one_sided_p_value,
holm_family_size,holm_order,holm_adjusted_p_value,status,reason

paper_proxy_top30_summary.csv
arm_id,fold,complete_day_n,topk_n,cumulative_gross_close_to_close_return,
annualized_gross_close_to_close_return,annualized_sharpe_no_risk_free,
mean_top30_minus_equal_weight,positive_day_rate,status,reason

paper_reference_comparison.csv
market,model,paper_rankic,paper_rankicir,local_arm_id,local_mapping_role,
local_fold,local_mean_rankic,local_rankicir,numerically_comparable,
gate_eligible,threshold_role,local_pass_threshold_source,
cross_market_numeric_match_claim_allowed,status,reason
```

Canonical sort 分别为 `arm_id,model_seed`、`arm_id,score_role,model_seed,fold,audit_type,period_id`、`contrast_id`、`arm_id,fold`、
`market,model`，exact 6 rows（CSI300/S&P500 × LightGBM/LSTM/REAKA）。Paper rows 固定
`numerically_comparable=false,gate_eligible=false,threshold_role=reference_only,`
`local_pass_threshold_source=none,cross_market_numeric_match_claim_allowed=false`；只允许 M1 映射 `closest_local_lightgbm_proxy`、R2 映射
`paper_architecture_grounded_project_adaptation`；paper LSTM 两行的 local fields 必须为空。M2/M3 均不得映射 paper row，M3 只在 paired
comparison 中标记 `project_direct_comparator`。

`model_parameter_compute_latency_audit.csv` 在 P2-P5 exact 3 rows，按 seed ASC；未启动 seed 的 parameter counts 仍由 frozen topology
机械计算，latency/memory fields 为 null/0、`status=not_run`。`rankic_stability_and_concentration_audit.csv` 在 P5 exact 48 rows：

```text
fold_summary:
  (R2 seed_20260713|seed_20260714|seed_20260715|ensemble) x
  (validation_early|validation_late|validation_full) = 12
calendar_month:
  R2 ensemble x (12 validation_full months + 6 validation_late months) = 18
leave_one_month_out:
  R2 ensemble x (12 validation_full omissions + 6 validation_late omissions) = 18
```

Month/omission `period_id` 固定 `YYYY-MM`，full 为 `2023-01..2023-12`、late 为 `2023-07..2023-12`；fold-summary period_id等于 fold。
Calendar/LOMO rows 的两个 concentration fields 为 null；fold-summary rows 的 `max_abs_day_contribution` non-null，且 late ensemble 的
`max_abs_month_contribution_share` non-null并 exact 等于 Section 8.2 gate value。其他 fold-summary month-share field 可计算时 non-null，否则
null并在 reason说明。零 complete-day 的预注册 month/omission row 保留并标 `not_evaluable`，不得删行缩 cardinality。

`stage_status_registry.csv` exact schema：

```text
stage_order,stage_id,started_at_utc,ended_at_utc,stage_status,
input_bundle_hash,output_bundle_hash,failed_gate_ids,reason
```

Exact 5 rows，order/stage id 对应 Section 1；未运行 stage 的 timestamp/hash 为空、`stage_status=not_run`。

`gate_evidence_21c_full.csv` exact schema：

```text
gate_order,gate_id,gate_class,evidence_artifact_path,evidence_field,
expected_value,observed_value,status,blocking,reason
```

Gate rows exact 等于 Section 9.1 causal gates，再依次追加 `output_manifest_hash_gate,failure_bundle_integrity_gate`；causal gate 顺序与
decision precedence 一致，两个 meta-gates 最后。`blocking` 固定 true，禁止只在 report 中补 gate。

`artifact_profile_registry.csv` exact schema：

```text
profile_order,profile_id,required_paths_json,forbidden_paths_json,
conditional_path_rules_json,registry_contract_sha256
```

Exact 6 rows P0..P5；三个 JSON fields 均为 canonical JSON arrays/objects，path ASC，内容必须由 Section 11 的集合机械生成。
`registry_contract_sha256` 六行相同，定义为 canonical JSON `{U,base_sets,profile_equations,conditional_rules}` 的 SHA256，不包含 registry CSV
bytes 或该 hash 字段自身。

`semantic_reproducibility_manifest.json` exact keys：

```text
schema_version,run_id,requirement_sha256,resolved_config_sha256,
approved_21c_runner_sha256,approved_21c_config_sha256,approved_21c_test_sha256,
scope_restart_decision_sha256,upstream_21b_semantic_payload_bundle_hash,
upstream_21b_pre_holdout_bundle_hash,upstream_paper_lineage_erratum_sha256,
feature_route_hash,split_hash,normalization_contract_hash,source_row_key_hash,
teacher_extension_hash,initialization_contract_sha256,ordered_parameter_name_list_sha256,
model_state_semantic_hashes,early_score_semantic_hash,late_score_semantic_hash,
metric_semantic_hashes,semantic_payload_bundle_hash
```

`model_state_semantic_hashes` 按 seed ASC，`metric_semantic_hashes` 按 artifact path ASC；P0/P1 对尚未产生的 payload 使用空 array/null，禁止
placeholder hash。`semantic_payload_bundle_hash` 对除自身外的 semantic keys canonical JSON 计算。

`manifest_21c_full_reaka_pit_proxy_replication.json` exact keys：

```text
schema_version,run_id,requirement_version,artifact_profile_id,
artifact_profile_registry_sha256,requirement_sha256,resolved_config_sha256,
approved_21c_runner_sha256,approved_21c_config_sha256,approved_21c_test_sha256,
scope_restart_decision_sha256,approved_21b_output_root,
approved_21b_output_hashes_sha256,approved_21b_contract_erratum_sha256,
approved_21a_paper_lineage_erratum_sha256,pre_gate_r2_checkpoint_bundle_hash,
upstream_21b_pre_holdout_bundle_hash,semantic_payload_bundle_hash,
gate_evidence_sha256,decision_sha256,report_sha256,files
```

`files` 为除 output-hashes 文件和 final manifest 自身外，当前 profile exact paths 的 path ASC objects：
`{path,byte_size,sha256}`。`output_hashes_21c_full_reaka_pit_proxy_replication.json` exact keys 为
`schema_version,manifest_sha256,file_count,files`；其 `files` 覆盖 final manifest 和其余所有 profile artifacts，但排除 output-hashes 自身。
禁止 symlink、额外文件或自引用。

`21C_full_reaka_pit_proxy_replication_decision.csv` unique row exact header：

```text
run_id,requirement_version,artifact_profile_id,artifact_profile_registry_sha256,stage_decision,
execution_authorization_gate,scope_restart_gate,scope_override_gate,upstream_21b_success_gate,
upstream_21b_contract_erratum_gate,upstream_paper_lineage_erratum_gate,
upstream_hash_and_file_set_gate,
dependency_runtime_gate,input_panel_integrity_gate,train_validation_firewall_gate,
historical_holdout_zero_access_gate,teacher_materialization_gate,
architecture_shape_gate,teacher_isolation_gate,loss_and_score_index_gate,
seed_determinism_gate,gpu_memory_gate,training_completion_gate,
pre_gate_bundle_hash_gate,late_readout_process_gate,checkpoint_eligibility_gate,
score_coverage_gate,rankic_implementation_gate,finalize_transaction_gate,r2_direction_stability_gate,
output_manifest_hash_gate,failure_bundle_integrity_gate,r2_validation_late_mean_rankic,
positive_late_seed_n,positive_lomo_n,lomo_total_n,
r2_minus_m1_paired_mean_delta,r2_minus_m3_paired_mean_delta,
relative_advantage_point_ordering_observed,
full_reaka_local_validation_point_ordering_observed,
historical_holdout_readout_authorized,next_requirement_generation_authorized,
next_requirement_execution_authorized,policy_training_authorized,
portfolio_optimization_authorized,deployment_authorized,
scope_restart_decision_sha256,approved_21b_contract_erratum_sha256,
approved_21a_paper_lineage_erratum_sha256,
pre_gate_r2_checkpoint_bundle_hash,upstream_21b_pre_holdout_bundle_hash,
semantic_payload_bundle_hash,blocking_reasons
```

Profile-specific nullability exact 为：

```text
IMPLEMENTATION_PIN_FIELDS = {
  approved_21c_runner_sha256,
  approved_21c_config_sha256,
  approved_21c_test_sha256
}

AUTH_PIN_FIELDS = {
  scope_restart_decision_sha256,
  approved_21b_contract_erratum_sha256,
  approved_21a_paper_lineage_erratum_sha256,
  upstream_21b_pre_holdout_bundle_hash
}

R2_RESULT_FIELDS = {
  r2_validation_late_mean_rankic,positive_late_seed_n,positive_lomo_n,lomo_total_n,
  r2_minus_m1_paired_mean_delta,r2_minus_m3_paired_mean_delta,
  relative_advantage_point_ordering_observed,
  full_reaka_local_validation_point_ordering_observed
}

P0 with authorization_schema_status in {missing,invalid}: IMPLEMENTATION_PIN_FIELDS and AUTH_PIN_FIELDS = null
P0 with authorization_schema_status=pass: IMPLEMENTATION_PIN_FIELDS and AUTH_PIN_FIELDS = exact authorization pins
P1..P5: IMPLEMENTATION_PIN_FIELDS and AUTH_PIN_FIELDS = non-null exact authorization pins
P0..P2: pre_gate_r2_checkpoint_bundle_hash = null
P3..P5: pre_gate_r2_checkpoint_bundle_hash = non-null verified hash
P0..P4: every R2_RESULT_FIELDS value = null
P5: every R2_RESULT_FIELDS value = non-null; booleans remain explicit true|false
P0..P5: semantic_payload_bundle_hash = non-null SHA256, including an empty-payload semantic hash where applicable
```

Final manifest 与 semantic manifest 中的 `approved_21c_runner_sha256,approved_21c_config_sha256,approved_21c_test_sha256`，以及 final manifest 中的
`scope_restart_decision_sha256,approved_21b_output_root,approved_21b_output_hashes_sha256,`
`approved_21b_contract_erratum_sha256,approved_21a_paper_lineage_erratum_sha256,upstream_21b_pre_holdout_bundle_hash` 使用同一 authorization-schema
规则：missing/invalid 时全部 canonical JSON null；schema pass 时 exact 复制 pins，即使后续 pinned artifact verification fail。其
`pre_gate_r2_checkpoint_bundle_hash` 使用上述 profile rule。Semantic manifest 的 upstream/teacher/model/score/metric fields 按最早成功 stage
填值；未产生字段为 JSON null，hash arrays 为 `[]`，不得使用空字符串、`NA` 或 placeholder hash。

`blocking_reasons` 是 failed causal gate IDs 加 failed `output_manifest_hash_gate` 的 canonical JSON array，按 decision precedence 后 gate_id
ASC；无 failure 为 `[]`。`failure_bundle_integrity_gate` 不进入数组，因为它不通过时 bundle/decision 不得发布。

### 10.3 Report mandatory sections

中文报告必须依次包含：

1. 决策与 claim ceiling；
2. 独立 scope restart：为什么跳过消融、它不授权 execution；
3. corrected 21B/21A lineage、两个 errata 与 hashes；
4. paper-vs-local setup differences；
5. full R2 architecture/config/search accounting 与 approved 21C runner/config/test hashes；
6. validation early selection 与 late seal boundary；
7. R2 seed/ensemble RankIC 和稳定性；
8. R2 vs M1/M3 paired comparison；
9. paper reference table 与不可比较说明；
10. paper-proxy Top30 gross diagnostic；
11. 不支持的机制/盈利/部署结论；
12. access/hash/reproducibility audit；
13. 下一步必须重新人工授权。

不得把 M2 写为 paper w/o GM，不得把 validation-late 写为 test/forward，不得把 gross close proxy 写为 executable PnL，也不得把
state 9 写为 paper result reproduced、preliminary replication success 或统计显著优势。

## 11. Artifact profiles、transactional seal 与 hash closure

Section 10.1 全部路径构成唯一 universe `U`。以下集合中的字符串均为 exact relative paths：

```text
C_COMMON_FINAL = {
  artifact_profile_registry.csv,
  stage_status_registry.csv,
  gate_evidence_21c_full.csv,
  21C_full_reaka_pit_proxy_replication_decision.csv,
  21C_full_reaka_pit_proxy_replication_report.md,
  semantic_reproducibility_manifest.json,
  manifest_21c_full_reaka_pit_proxy_replication.json,
  output_hashes_21c_full_reaka_pit_proxy_replication.json,
  historical_design_holdout_access_audit.csv
}

A_PREFLIGHT = {
  preflight/preflight_access_audit.csv,
  preflight/upstream_21b_authorization_and_hash_audit.csv,
  preflight/scope_override_audit.csv,
  preflight/scope_restart_decision_audit.csv,
  preflight/paper_lineage_erratum_audit.csv,
  preflight/resolved_config.yaml
}

M_SUCCESS = {
  materialized/r2_train_teacher_sequence_index.parquet,
  materialized/r2_train_teacher_return_panel.f32.memmap,
  materialized/r2_input_extension_manifest.json,
  materialized/materialization_access_audit.csv
}

M_FAILURE = {
  materialized/materialization_access_audit.csv,
  materialized/materialization_failure_evidence.csv
}

T_CORE = {
  training/model_search_accounting_manifest.csv,
  training/resource_probe_audit.csv,
  training/training_run_registry.csv,
  training/seed_level_training_curves.csv,
  training/checkpoint_manifest.json,
  training/model_parameter_compute_latency_audit.csv,
  training/training_access_audit.csv
}

T_SUCCESS_ONLY = {
  training/checkpoints/R2_REAKA_DIFFUSION/seed_20260713/state_dict.pt,
  training/checkpoints/R2_REAKA_DIFFUSION/seed_20260714/state_dict.pt,
  training/checkpoints/R2_REAKA_DIFFUSION/seed_20260715/state_dict.pt,
  training/selection_worker_exit_record.json,
  training/selection/validation_early_prediction_scores.parquet,
  training/pre_gate_r2_checkpoint_bundle_manifest.json
}

T_FAILURE = {training/training_failure_evidence.csv}

L_SUCCESS = {
  training/readout/validation_late_prediction_scores.parquet,
  training/late_readout_worker_exit_record.json,
  training/checkpoint_eligibility_manifest.json
}

L_FAILURE = {
  training/late_readout_worker_exit_record.json,
  training/late_readout_failure_evidence.csv
}

F_METRICS = {
  daily_rankic_readout.csv,
  rankic_stability_and_concentration_audit.csv,
  paired_rankic_comparison.csv,
  stationary_bootstrap_pair_diagnostic.csv,
  paper_proxy_top30_daily.csv,
  paper_proxy_top30_summary.csv,
  paper_reference_comparison.csv
}

F_FAILURE = {finalize_failure_evidence.csv}
```

Exact profile equations：

```text
Required(P0_PREFLIGHT_BLOCKED)      = C_COMMON_FINAL ∪ A_PREFLIGHT
Required(P1_MATERIALIZATION_BLOCKED)= C_COMMON_FINAL ∪ A_PREFLIGHT ∪ M_FAILURE
Required(P2_TRAINING_BLOCKED)       = C_COMMON_FINAL ∪ A_PREFLIGHT ∪ M_SUCCESS ∪ T_CORE ∪ T_FAILURE ∪ Ck ∪ Ws
Required(P3_LATE_READOUT_BLOCKED)   = C_COMMON_FINAL ∪ A_PREFLIGHT ∪ M_SUCCESS ∪ T_CORE ∪ T_SUCCESS_ONLY ∪ L_FAILURE
Required(P4_FINALIZE_BLOCKED)       = C_COMMON_FINAL ∪ A_PREFLIGHT ∪ M_SUCCESS ∪ T_CORE ∪ T_SUCCESS_ONLY ∪ L_SUCCESS ∪ F_FAILURE
Required(P5_FULL_FINALIZED)         = C_COMMON_FINAL ∪ A_PREFLIGHT ∪ M_SUCCESS ∪ T_CORE ∪ T_SUCCESS_ONLY ∪ L_SUCCESS ∪ F_METRICS
Forbidden(P)                        = U - Required(P)
```

P2 的 `Ck` exact 等于 `checkpoint_manifest.records[*].checkpoint_path` 的 path set，cardinality 只能 0..3；checkpoint manifest record
存在 iff 同 seed search-accounting row 的 `checkpoint_produced=true`，两个 artifact 的 seed set/cardinality 必须一致。每个 path/hash 必须与
manifest 双向匹配，root 中禁止任何其他 checkpoint。`Ws={training/selection_worker_exit_record.json}` iff training failure evidence 含
`worker_mode=r2_selection,worker_process_start_attempted=true`，否则 `Ws={}`；一旦 launch 被尝试，无论 execve/worker 成功或失败，parent 都必须写
record。P2 checkpoint manifest 即使 `Ck={}` 也必须存在且 records 为空。P0/P1 禁止 checkpoint manifest；P3/P4/P5 的三个 checkpoint
path exact。除 P2 的 `Ck`、`Ws` 外不允许可选路径。
P2 failure evidence 的 worker fields 描述该 stage 是否曾启动 selection worker，而非仅描述最终失败发生在哪个 process；因此即使 worker
成功退出、随后 parent pre-gate seal 失败，也必须写 `r2_selection,true` 并包含 `Ws`。只有 resource probe/parent failure 发生在任何 selection
launch 前才写 `none,false`。

触发 first-match：preflight fail→P0；materialization fail→P1；resource/training/selection/pre-gate-seal fail→P2；late worker/readout fail→P3；
late success 后 metric/report/final seal fail→P4；全部 causal readout 和 final seal 成功→P5。Failure evidence 只能出现在对应 profile；P5 禁止
全部 failure evidence。Canonical root 下出现 `U` 外任何 leaf file、symlink、profile-forbidden path 或非 required-path ancestor 的目录均使 seal
fail；required file path 的机械 parent directories（如 `preflight/`、`training/checkpoints/.../`）允许存在但不作为 `U` 中独立 artifact，且禁止
额外空目录、临时目录或目录内非 profile 文件。
P3 的 late failure evidence 必须为 `worker_mode=r2_late_readout,worker_process_start_attempted=true`；execve 前 launch failure 使用 Section 10.2
定义的 parent disposition record，因此 L_FAILURE 的 exit-record path 仍然 required。

所有 stage先写 sibling `.building`，fsync/close 后从磁盘重开验证，最终 atomic rename。存在 canonical root、sealed audit root 或 partial root
时不得覆盖。

Hash domain：

- full-byte output hash 覆盖全部 artifact bytes；
- semantic payload hash 覆盖输入 rows、teacher extension、model state、scores、metrics，不含 timestamp/latency；
- final manifest 记录 exact file set但不记录自身或 output-hashes hash；output-hashes 单向记录 final-manifest SHA256，避免循环；
- P0-P4 的 manifest/output-hashes 只密封 failure bundle，并由 `failure_bundle_integrity_gate` 验证；它们不得反向把失败的
  success-candidate `output_manifest_hash_gate` 改写为 pass；
- semantic manifest 不得把 decision/report 顶层 hash嵌入 payload DAG 形成循环；
- CSV/JSON/Parquet/memmap canonicalization 规则继承 21B，所有 sort/header/dtype/null semantics exact。

## 12. Implementation acceptance tests

最低测试集合：

1. 缺失/错误/extra-key/non-human execution authorization、scope restart、21C runner/config/test pin 或任一 upstream pin 在任何
   value/checkpoint open 前 fail；authorization 后修改 21C runner/config/test 任一 byte 必须 fail；P0 missing/invalid authorization 的
   resolved-config/decision/semantic-manifest/final-manifest canonical null bytes exact；
2. current uncorrected 21B_v4 fixture 因 contract erratum gate fail，且 model/value open count=0；
3. corrected 21B successor 的 requirement/runner/config/test、两个 errata、raw append-only runtime access event log、聚合 counter evidence、
   decision/manifest/output hashes/file set/semantic payload/pre-holdout bundle 全部 exact-match 才通过；raw event log 缺失、hash/schema/
   event_seq 异常、source-log pin不一致、aggregate/erratum count不能从 raw log exact重算或以预置零常量生成均 fail；
4. 独立 scope restart 缺失、自授权 execution、scope override 非 exact、holdout authorization=true 或原 nested filename 静默替换均 fail；
5. M1/M3 各 3 个 frozen checkpoint/early+late scores缺失或 coverage不足 fail；
6. raw qfq/membership/calendar open attempt fail；
7. source panels/cache/index 任一 path/hash/shape/dtype/key mismatch fail；
8. teacher dates exact source shift一格，末行为 t+1；validation teacher count exact 0；
9. y teacher exact 等于 `y_source[1:] + forecast_y`；x teacher末 row exact命中同股 t+1 cache；
10. teacher branch exact复用 shared return/feature encoder与 gate parameter objects、从独立 zero h0/c0 计算 `Z_teacher_shifted`，且
    `L_koop/L_diff/L_rec` gradient 回到 shared parameters；teacher tensor尝试进入 source encoder/source GateNet/selector/DDPM condition/
    inference signature，或绕过 teacher shared gate、carry source state、复制 teacher-only weights均 fail；
11. teacher perturbation不改变 fixed-source inference score；
12. D_x 非157、T非10、latent非64、operator非4、draw非8均 fail；
13. K orientation/einsum fixture exact，transpose/right-multiply/broadcast fail；
14. soft Gumbel train、U clamp exact `[1e-10,1-1e-10]`、hard argmax inference/tie-smallest exact；`2^-24` clamp fixture必须 fail；
15. beta/alpha/alpha_bar/posterior variance与20步 reverse fixture exact；
16. training R_hat 使用 sampled-timestep x0 estimate，不运行 full reverse chain；
17. inference运行20步8 draws，row-key seed对 batch/order exact；
18. loss reduction/batch duplication invariant，L_forecast只计一次；
19. initialization fixture验证 exact module/draw/parameter traversal、module tensors、gate-slice orthogonal、单一 forget bias与K full-tensor
    identity-noise；任意 registration reorder 必须改变 fixture hash并 fail；AdamW explicit flags、single parameter group、zero-grad/backward/
    clip/step order逐项 exact；
20. exactly 3 primary jobs，任何 K1/K1C/K2/R1/M2/M3 training attempt fail；
21. resource probe只运行一次且三个 seeds共享 batch；OOM ladder只按256→128→64→32→16，raw-byte 90% boundary、probe stream/row-key exact，
    不能读取 outcome 或改变模型 config；tau 0-based closed-form、early-stop denominator与 optimizer-step counter fixture exact；
22. selection只读 validation_early，改变 late labels不改变 selected epoch/checkpoint hash；
23. selection fresh execve/parent exit record/late zero-open exact；success counts=3；P2 partial counts=0..3并与 registry/Ck exact；selection/late
    launch-before-execve failure均生成 parent disposition，optimizer-step count不与 fit-entrypoint count混用；
24. pre-gate seal前 late worker启动必须 fail；seal后任何 checkpoint/config mutation fail；
25. late worker import train/optimizer/backward/save checkpoint均 fail；
26. ensemble exact为三 seed arithmetic mean，best seed不能替代；
27. RankIC average-rank/float64 Pearson与 fixture一致，constant/NaN返回 not_evaluable；
28. score coverage/denominator不得取 arm intersection；
29. R2 direction gate每个 conjunct boundary均有 pass/fail fixture；
30. M1/M3 comparator scores必须复用上游 bytes，重新 inference/scale/选择 comparator fail；
31. paired P1/P2同日 delta与m=2 bootstrap diagnostic exact；
32. Top30 exact 30、score DESC/tie instrument ASC、gross/equal-weight公式 exact；
33. Top30不得进入 hard gate；report中出现 executable/PnL claim fixture fail；
34. M2 映射 paper LSTM/w-o-GM 的 registry/report fixture fail；
35. historical holdout任一 feature/outcome/label/join/metric count非0 fail并优先落 state 3；
36. nine decision states first-match、P4 映射 finalize-integrity state、success-candidate/failure-bundle 两个 integrity gates互不覆盖、blocking
    reasons与authorization booleans exact；`fail|not_evaluable` 才触发 state，合法 downstream `not_run_due_to_prior_gate:*` 不得抢占或改写
    earlier state，首个 failure 前出现 not_run 或无 failure 却存在 not_run 时 failure-bundle integrity fail且禁止发布 profile；
37. P0-P5 集合方程、P2 `Ck=checkpoint_manifest paths` 且与 search-accounting `checkpoint_produced` 双向一致、required/forbidden exact
    file-set，blocked profile不补造成功 artifact；
38. `.building`、existing sealed root、post-build reopen/hash failure均不得 seal；
39. semantic payload/top-level DAG无环，同输入同环境重复 run semantic hashes exact；
40. 四组 check-ID registry、48-row stability、3-row model audit，以及所有 required CSV/JSON/Parquet/memmap
    header/key/dtype/sort/null/cardinality exact；report、decision、gate evidence、manifest/output hashes双向可复算。

## 13. Validation commands

实现后至少执行：

```bash
.venv/bin/python -m pytest -q \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21c_full_reaka_pit_proxy_replication.py

.venv/bin/ruff check \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21c_full_reaka_pit_proxy_replication.py \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21c_full_reaka_pit_proxy_replication.py

.venv/bin/python -m py_compile \
  experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21c_full_reaka_pit_proxy_replication.py

uv lock --check
git diff --check
```

实现完成但执行授权缺失时，只运行 unit/synthetic/negative-preflight tests；不得创建 canonical output root 或读取真实 model panel/checkpoint。

## 14. Completion checklist

- [ ] 新 requirement 只新增本文件，不改写 sealed 21A/21B outputs
- [ ] 独立人工 scope restart、执行授权与当前 requirement hash 三者分离并互相绑定
- [ ] authorization exact pin 21C runner/config/test，resolved/pre-gate/semantic/final manifests 全链记录且任一 byte drift fail
- [ ] corrected 21B successor/version/code/config/test/hash/runtime-counter erratum gate exact pinned
- [ ] corrected 21B raw append-only event log 与 aggregate evidence 均被 manifest/semantic closure 覆盖，全部零计数可从 raw log重算
- [ ] 21A M2 paper-lineage erratum path/hash exact pinned，未改写 sealed 21A bytes
- [ ] current uncorrected v4 fail closed，不被自动接受
- [ ] P0 missing/invalid authorization 的 resolved config、decision、semantic/final manifests canonical null rules exact
- [ ] historical holdout全程零访问
- [ ] feature route exact为157-feature registered adaptation，未冒充 Alpha158 exact
- [ ] source rows/splits/normalizer/label exact继承 corrected 21B
- [ ] train-only teacher shift/index/value/hash闭合，validation teacher为0；teacher branch exact复用 shared encoder/gate parameters且不进入 source/inference graph
- [ ] full R2 dual LSTM/gate/AKS/Koopman/DDPM/decoder/loss与21A一致
- [ ] R2 module registration/init/RNG draw/optimizer traversal、Gumbel clamp=`1e-10`、AdamW explicit flags/step、tau公式与contract hash exact
- [ ] 只运行3个R2 primary jobs，无消融/sensitivity/search
- [ ] batch OOM ladder只 probe 一次并由三 seeds 共享，是机械资源选择而非 outcome search
- [ ] validation_early选 checkpoint，pre-gate seal后 fresh worker读取 late
- [ ] worker success/partial/launch-failure disposition闭合，fit-entrypoint/optimizer-step counter不混用，三个 checkpoint eligibility conjunct exact
- [ ] M1/M3 comparator从21B冻结 score读取，不重训/重推断
- [ ] M2标为project diagnostic，未映射 paper LSTM/w-o-GM
- [ ] R2 seed/ensemble RankIC、month/LOMO/concentration/coverage完整
- [ ] R2-M1/R2-M3 paired point ordering和bootstrap diagnostic完整
- [ ] paper-proxy Top30只作gross close diagnostic，不进入gate
- [ ] paper静态数值只作reference，不作为threshold
- [ ] decision 只到 validation-only architecture sanity / point ordering，不声称论文结果复现、不授权后续
- [ ] decision first-match 只由实际 `fail|not_evaluable` 触发，合法 downstream not_run 不抢占 earlier state
- [ ] P0-P5 profiles、fresh process、access audit、transactional seal闭合
- [ ] success-candidate output integrity 与 blocked failure-bundle integrity 分离，后者失败不发布 profile
- [ ] 46-path artifact universe、check-ID registry、全部 schema/sort/null/cardinality 与 P2 conditional paths exact
- [ ] full-byte/semantic hashes与manifest file set双向验证
- [ ] tests、ruff、py_compile、lock、diff checks通过

---

本 requirement 的完成只表示 alternate 21C full-architecture local-validation-sanity 规格已生成。当前用户请求未授权执行、未授权读取
historical design holdout，也未授权跳过 corrected 21B successor。只有后续人类 authorization 与本文件 exact hash、corrected upstream
hashes 和 scope override 全部绑定后，runner 才可进入真实 preflight。
