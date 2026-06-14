# 需求：09A Fast-Fail Label Frontier

## 0. 路径基准

本 requirement 同时引用 repo-root 路径与实验目录相对路径，必须按以下规则解析：

1. `REPO_ROOT` 是 `/home/xiaolv/code/a_share` 或当前 Git repository root。
2. `TOPIC_ROOT` 是 `topics/02_AFML_BIG_WINNER`。
3. `EXPERIMENT_ROOT` 是 `TOPIC_ROOT/experiments/pending/09_riskon_fastfail_label_feature_uplift`。
4. 以 `topics/` 开头的路径一律按 repo-root-relative 解析。
5. 以 `../` 开头的路径一律按 `EXPERIMENT_ROOT` 相对路径解析。
6. manifest 必须记录上述 resolved absolute path 与 hash，避免从 topic root 或 repo root 启动时误读上游。

## 1. 目标

09A 是纯 label diagnostic，不训练模型。它必须重定义或确认：

```text
selected_fast_fail_10_label
selected_cost_bad_10_20_target
```

09A 不得覆盖或改写上游既有 `failure_10_label`。现役 `failure_10_label` 必须作为 incumbent baseline 保留；09A 只能新增 selected label / target 列。

09A 必须回答：

1. 旧 `failure_10 = severe drawdown` 是否过硬。
2. 新 label 是否保留 enough winner recall。
3. 新 target 与旧 H target 的差异是否可解释。
4. 是否存在 1-2 个机制不同、split 稳定的 candidate label 可进入 09C。

只有 09A 输出 `09A_label_frontier_candidate_selected` 或 `09A_label_frontier_candidate_source_caveated_selected`，09C 才允许进入 supported gate。其他 09A 状态下，09B 仍可执行，但 09C 只能 diagnostic。

## 2. 输入与依赖

必须读取并记录 hash：

```text
topics/02_AFML_BIG_WINNER/README.md
topics/02_AFML_BIG_WINNER/research_direction_discussion_20260614.md
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/08_all_experiments_final_report.md
```

必须读取的 08 manifest：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/risk_on_post_filter_cost_rejector/risk_on_post_filter_cost_rejector_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/risk_on_cost_rejector_research_entry_hardening/risk_on_cost_rejector_research_entry_hardening_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/transition_subregime_taxonomy_audit/transition_subregime_taxonomy_audit_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/transition_previous_regime_outcome_audit/transition_previous_regime_outcome_audit_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/transition_previous_regime_context_cost_rejector_ablation/transition_previous_regime_context_cost_rejector_ablation_manifest.json
```

必须读取的事件、label 与 membership 源：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_canonical_events.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_event_instances.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_capture.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/cross_section_feature_panel.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
```

09A 候选 label 若要计算 ATR / sigma / EMA / swing-low / intraday high-low touch，必须读取并审计可回放的价格路径来源：

```text
topics/02_AFML_BIG_WINNER/experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/outputs/manifests/run_manifest.json
topics/02_AFML_BIG_WINNER/experiments/pending/01_data_prepare_pit_largecap_akshare_qlib_v0/outputs/manifests/cache_manifest.csv
topics/02_AFML_BIG_WINNER/data/interim/qlib_csv/day/*.csv
topics/02_AFML_BIG_WINNER/data/interim/index_qlib_csv/day/*.csv
```

价格路径来源必须至少支持以下字段或等价字段：

```text
instrument
date
$open / open
$high / high
$low / low
$close / close
$volume / volume
$money / money
adjustment_policy
```

如果某个候选 label 需要的字段不可重建，不能隐式丢样本，也不能用旧 `mae_10d` 近似替代。必须在 `candidate_label_evaluability_audit.csv` 中标记：

```text
candidate_label_status = not_evaluable_missing_price_path
```

并从 selected label 候选集中排除。

07 E1 baseline 只作 read-only denominator / future R12 reference：

```text
../07_topn_multichannel_repair_candidate_generator_v0/outputs/manifests/run_manifest.json
../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv
../07_topn_multichannel_repair_candidate_generator_v0/outputs/local_cache/topn_canonical_event_labels.parquet
```

如果 D / E / H manifest 缺失或 hash 不可读，09A 必须停止：

```text
decision = 09A_label_frontier_input_blocked
```

## 3. 非目标

09A 明确不做：

1. 不训练任何 classifier / ranker。
2. 不选择 keep threshold。
3. 不调 validation / robustness。
4. 不做 transition model 或 transition family rediscovery。
5. 不把 label 诊断结果解释为 entry signal。
6. 不因 target 变松就声称相对 H 旧 frontier 有 uplift。
7. 不用旧 `mae_10d` / `mfe_10d` 反推需要 path ordering 的 structural / vol-scaled label。
8. 不在 label frontier 后根据 09C 模型表现回头改 label。

## 4. Regime PIT Audit

09A 的第一步必须输出：

```text
outputs/publishable/tables/09A_fast_fail_label_frontier/regime_label_pit_audit.csv
outputs/publishable/reports/09A_fast_fail_label_frontier/regime_label_pit_audit.md
```

至少包含：

| field | required readout |
| --- | --- |
| `regime_source_artifact` | 事件与 membership 的 regime 来源 |
| `t0_visible_flag` | 是否只用 t0 及之前市场数据 |
| `future_join_count` | 必须为 0 |
| `published_reconstructed_consistency` | train / validation / robustness 分别报告 |
| `risk_on_reconstructed_not_published_share` | split-level |
| `published_risk_on_not_reconstructed_share` | split-level |
| `transition_drift_context` | 只作 caveat，不进入训练 |

Regime PIT 保证不能来自列名本身。`candidate_family_canonical_events.csv.gz` 中预期同时存在 `event_regime_bucket` 与 `market_regime_bucket`；两者可以完全一致，且这种一致是正常的 event-level alias，不代表已经完成 PIT 审计。PIT 保证唯一来自 `cross_section_feature_panel.parquet` 按 `event_t0_date` 的 as-of 重建，并与 canonical event-level regime 对账。

Regime 对象必须分清 event-level 与 episode-level grain，不得用 episode-level 字段回填 event training scope：

| regime object | source artifact | source column | semantic |
| --- | --- | --- | --- |
| `event_regime_bucket` | `candidate_family_canonical_events.csv.gz` | `event_regime_bucket` | event t0 可见 regime，用于 09A 主分母与 09C 训练 scope |
| `event_market_regime_alias` | `candidate_family_canonical_events.csv.gz` | `market_regime_bucket` | event-level alias/readout；若与 `event_regime_bucket` 相同是正常情况 |
| `event_regime_reconstruction` | `cross_section_feature_panel.parquet` | `market_regime_bucket` joined by `date = event_t0_date` | 唯一的 t0 as-of reconstruction / PIT audit source |
| `episode_regime_bucket` | `candidate_family_capture.parquet` or D membership | `market_regime_bucket` | episode readout regime，只用于 retention / bridge / E1-missed readout |

`event_regime_bucket` 预期存在。如果缺少该列，允许临时读取 canonical event 表中的 `market_regime_bucket` 作为 candidate event regime，但该状态必须标记为 backward-compatible diagnostic，且必须证明该列由 `event_t0_date` 及之前的 market data 固化，不是由 `candidate_family_capture.parquet` 的 episode-level `market_regime_bucket` 回填。若无法证明，只能输出 diagnostic。

`cross_section_feature_panel.parquet` 的 `market_regime_bucket` 必须先通过 market-wide audit：同一 `date` 上不得出现多个 regime 值；若同日多值，必须解释是否 instrument-level regime 合法，否则 regime PIT audit blocked。

`regime_label_pit_audit.csv` 必须额外包含：

| field | required readout |
| --- | --- |
| `event_regime_source_artifact` | 必须是 event-level artifact |
| `event_regime_source_column` | 默认 `event_regime_bucket` |
| `event_market_regime_alias_column` | canonical event 表中的 `market_regime_bucket` |
| `event_market_regime_alias_agreement` | `event_regime_bucket` 与 canonical `market_regime_bucket` 的一致率；一致率 1.0 是正常别名，不是 PIT 证明 |
| `episode_regime_source_artifact` | episode-level readout artifact |
| `episode_regime_source_column` | 默认 `market_regime_bucket` |
| `event_episode_regime_same_source_flag` | 若 event 与 episode 都来自 capture / membership，必须 blocked；canonical 内 alias 不触发该 flag |
| `event_regime_reconstruction_source` | `cross_section_feature_panel.parquet` |
| `event_regime_reconstruction_join_key` | `instrument`, `event_t0_date` 或 market-wide equivalent |
| `feature_panel_market_wide_regime_check` | 同日 regime 是否唯一 |
| `risk_off_reconstructed_consistency_readonly` | derived risk_off read-only scope 的 report-only 一致率 |

默认 pass/fail 下限：

| metric | default |
| --- | ---: |
| `future_join_count` | `0` |
| `min_train_published_reconstructed_consistency` | `0.995` |
| `min_validation_published_reconstructed_consistency` | `0.990` |
| `min_robustness_published_reconstructed_consistency` | `0.985` |
| `max_risk_on_reconstructed_not_published_share` | `0.015` |
| `max_published_risk_on_not_reconstructed_share` | `0.015` |
| `min_risk_off_readonly_reconstructed_consistency_report_only` | report-only, no hard gate |

如果 `risk_on` 无法按公开规则重建，或 robustness consistency 低于预声明下限，09A 必须输出：

```text
decision = 09A_regime_label_pit_blocked
```

## 5. Source Pool Reconstruction

09A 必须通过 08 A 的 scope mapping contract 重建 label frontier 的 contract source pool，不得用临时字符串匹配或手写 family list。

必须重建并审计的 contract source pool：

1. `08_R_core_event_regime_gated`
2. `08_R6_event_regime_gated`
3. `07_E1_only`

`risk_off_e1_horizon_complete_readonly` 不是 08 A scope mapping contract 中的 `candidate_scope_id`，不得在 contract 中查找。它是 09A 派生只读 scope：

```text
risk_off_e1_horizon_complete_readonly =
    07_E1_only
    ∩ event_regime_bucket == "risk_off"
    ∩ horizon_complete_10d == true
```

派生规则：

1. 基础 universe 必须来自已重建的 `07_E1_only`，不得手写 E1 family list。
2. `event_regime_bucket` 必须使用 §4 定义的 t0-visible event regime，不得使用 episode-level `market_regime_bucket`。
3. 该 scope 的 `scope_type` 必须记录为 `derived_readonly_scope`。
4. 该 scope 只用于 risk_off read-only denominator / R12 前置参考，不得进入 09A selected label 选择、09B feature selection 或 09C training gate。
5. 该派生 scope 豁免于"必须存在于 08 A scope mapping contract"的约束，但不豁免 hash、join、schema、regime PIT 与 denominator 对账。

重建要求：

1. `scope_status` 必须是 `reconstructable_event_membership` 或等价可审计状态。
2. aggregate-only R compression arms 不得进入 09A denominator。
3. R-core 继续接受 08 A / H 已审计的 `47914` vs published `47929` 的 `-15` 差异；但必须在 audit 中记录 accepted difference reason。
4. 如果 reconstructed event count 与 `source_row_count` 不一致，且该差异未被上游 audit 接受，必须停止。
5. 如果任一 contract source pool 或 `derived_readonly_scope` 无法重建，必须停止并输出：

```text
decision = 09A_source_pool_reconstruction_blocked
```

必须输出：

```text
outputs/publishable/tables/input_audit/source_pool_reconstruction_audit.csv
```

## 6. Label Frontier 分母

所有候选 label 必须在同一组可审计事件分母上比较，不能按 label 各自丢样本。09A 至少报告三个分母：

| denominator_id | 用途 |
| --- | --- |
| `risk_on_r_core_horizon_complete` | 09C 主训练目标分母 |
| `risk_on_r6_horizon_complete` | R6 source sensitivity |
| `risk_off_e1_horizon_complete_readonly` | risk_off read-only baseline / R12 前置参考 |

硬规则：

1. `risk_on_r_core_horizon_complete` 是 09A 选择 label 的主分母。
2. 所有候选 label 必须报告 raw event n、horizon-complete n、censored n、non-executable n。
3. 不能因为某个 label 缺少 ATR / sigma / EMA 字段就隐式改变主分母；必须标记 label-specific missing / not-evaluable count。
4. fast-fail / cost target 指标必须使用同一 denominator view。
5. winner 相关指标必须只在 `horizon_complete_120d = true` 的子集上计算；120d-incomplete 事件必须单独计数，不得静默当作 `event_big_winner_120d_label = 0`。
6. `kill_wrong_rate` 与 `winner_injury_rate` 是 event-level 指标，使用 event-level 120d-complete subset。
7. `winner_recall_retention` 是 episode-level 指标，必须通过 `target_episode_id` / capture membership 计算"仍有至少一个存活 event 的 target episode 占比"，不得与 event-level `1 - winner_injury_rate` 混同。
8. `winner_censoring_status` 必须从上游 `candidate_outcome_120d_status` 派生，不得另立一套不可对账的 120d censoring 口径。
9. 若 `risk_on_r_core_horizon_complete` 与 H 的 R-core source binding 无法对账，09A 只能 output blocked。
10. `risk_off_e1_horizon_complete_readonly` 是 derived read-only denominator，不得与 contract source pool 混同。

## 7. 候选 Label

### 7.1 Candidate evaluability audit

09A 必须先输出：

```text
outputs/publishable/tables/09A_fast_fail_label_frontier/candidate_label_evaluability_audit.csv
```

至少包含：

| column | meaning |
| --- | --- |
| `candidate_label_id` | 候选 label |
| `mechanism_family` | fixed / vol_scaled / atr_scaled / structural / hybrid |
| `required_source_artifacts` | 需要的输入来源 |
| `required_fields` | 需要字段 |
| `path_ordering_required` | 是否需要逐日路径顺序 |
| `price_path_coverage_rate` | 主分母上的路径覆盖率 |
| `field_missing_count` | 缺失字段数 |
| `not_evaluable_count` | 不可评价事件数 |
| `candidate_label_status` | evaluable / sensitivity_only / not_evaluable |
| `not_evaluable_reason` | 缺失原因 |

只有 `candidate_label_status in {evaluable, sensitivity_only}` 的 label 可以进入 `fast_fail_label_frontier.csv`。只有 `candidate_label_status = evaluable` 的 label 可以进入 `selected_label_contract.csv`。

### 7.2 Candidate label family

候选 label family：

```text
fixed MAE10:
    -5%, -8%, -10%, -12%
    -6% 默认只作为 sensitivity_only，不进入 selected label；若要提升为可选 label，必须在运行前 config 显式声明，并仍需通过 §10.1 的 pairwise duplicate / Pareto 规则

vol-scaled barrier:
    -1.0 sigma, -1.5 sigma, -2.0 sigma

ATR-scaled barrier:
    -1.5 ATR, -2.0 ATR

structure barrier:
    break event low
    break recent swing low
    break EMA20
    break EMA60

hybrid:
    fast-fail_10d OR false-repair_20d
```

其中：

1. fixed MAE10 可由 10d path low / trade price 计算；如果只存在旧 `mae_10d` 且无法确认 touch order / censoring / same-bar tie，不得进入 selected label，只能作为 sensitivity readout。
2. vol-scaled barrier 的 sigma 必须用 `trade_time` 前可见窗口计算，例如 trailing 20d / 60d realized volatility；窗口长度必须写入 contract。
3. ATR-scaled barrier 必须用 `trade_time` 前可见 OHLC 窗口计算，例如 trailing 14d ATR；窗口长度必须写入 contract。
4. `break recent swing low` 必须冻结 swing lookback、确认规则、是否允许同日 event low。
5. EMA20 / EMA60 break 必须冻结 EMA 计算窗口、warmup、price field 与 touch field。
6. hybrid label 不是新的独立 path label，而是 selected fast-fail label 与 frozen false-repair component 的组合 target。

每个 label 必须写入 `fast_fail_label_contract.md`，冻结：

1. `t0`
2. `trade_time`
3. `t1`
4. price field 与 adjustment policy
5. barrier threshold
6. same-bar tie handling
7. censoring policy
8. horizon completeness rule
9. label end timestamp for purged CV
10. false-repair horizon
11. 与旧 target 对账规则
12. winner readout label：主口径固定为 `event_big_winner_120d_label`，即 120d +50% winner；`event_super_winner_120d_label` 与 `event_near_winner_120d_label` 只能作为 sensitivity，不得替代主口径。
13. winner readout completeness：主 winner 指标必须要求 `horizon_complete_120d = true`；`winner_censoring_status` 必须从 `candidate_outcome_120d_status` 固定映射：
    - `not_missing` -> `complete`
    - `censored_incomplete_horizon` -> `incomplete_120d`
    - `non_executable_next_open` -> `non_executable`
    - missing / unknown status -> `not_evaluable`
14. `candidate_outcome_120d_status` 的上游计数必须与 09A 的 `winner_120_complete_n`、`winner_120_incomplete_n`、`winner_censoring_status` 对账。

### 7.3 `failure_10` 与 `cost_bad_10_20` 构造

09A 必须分开输出两个层级：

```text
selected_fast_fail_10_label
selected_cost_bad_10_20_target
```

默认规则：

```text
selected_cost_bad_10_20_target =
    selected_fast_fail_10_label OR frozen_event_false_repair_20d_label
```

硬要求：

1. `frozen_event_false_repair_20d_label` 默认沿用 08 H 使用的 `event_false_repair_20d_label` 定义。
2. 如果 09A 认为 false-repair component 也必须调整，只能输出 diagnostic，不得直接进入 09C supported gate。
3. `selected_label_contract.csv` 必须同时记录 fast-fail component 与 cost target component。
4. `cost_target_bridge.csv` 必须分别报告 fast-fail component overlap、false-repair component overlap、hybrid target overlap。
5. `selected_cost_bad_10_20_target` 的 `label_t1_date` 必须按 20d cost horizon 冻结，即 `max(selected_fast_fail_10_label_t1_date, frozen_false_repair_20d_t1_date, trade_time + 20 trading sessions when no earlier component touch exists)`。该时间用于 purged CV、embargo、sample uniqueness 与 concurrency。

### 7.4 Selected label contract schema

09A 必须输出：

```text
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_contract.csv
```

至少包含：

| column | meaning |
| --- | --- |
| `selected_target_id` | selected cost target id |
| `selected_fast_fail_label_id` | selected fast-fail component |
| `false_repair_component_id` | frozen false-repair component |
| `selection_rank` | 选择排序 |
| `selection_status` | selected / rejected / diagnostic_only |
| `selection_reason` | 选择或拒绝原因 |
| `mechanism_family` | selected fast-fail mechanism family |
| `primary_denominator_id` | 主分母 |
| `candidate_label_status` | evaluable / sensitivity_only / not_evaluable |
| `source_caveated` | 是否带 source caveat |
| `label_contract_hash` | `fast_fail_label_contract.md` hash |
| `event_binding_hash` | `selected_label_event_bindings.parquet` hash |
| `usable_for_09C_supported_gate` | 是否允许 09C supported gate |
| `winner_readout_label` | 必须是 `event_big_winner_120d_label` |
| `winner_readout_completeness_rule` | 必须要求 `horizon_complete_120d = true` |
| `winner_censoring_status_mapping` | `candidate_outcome_120d_status` -> `winner_censoring_status` 固定映射 |
| `cost_target_label_t1_rule` | 20d cost horizon rule |

## 8. Wrong-kill 双向口径

不得只报告一个 `wrong-kill rate`。必须拆成 event-level 指标：

```text
kill_wrong_rate = P(event_big_winner_120d_label = 1 | fast_fail = 1)
winner_injury_rate = P(fast_fail = 1 | event_big_winner_120d_label = 1)
```

二者都只能在 `horizon_complete_120d = true` 的 event 子集上计算。

计算 winner 指标前必须显式 drop `event_big_winner_120d_label is null` 的事件。每个 split / denominator 的 dropped row count 必须等于 `winner_120_incomplete_n`，且这些被 drop 的行必须满足：

```text
candidate_outcome_120d_status in {
    "censored_incomplete_horizon",
    "non_executable_next_open"
}
```

如果 null dropped count、`candidate_outcome_120d_status` 汇总、`horizon_complete_120d` 三者不能对账，09A 必须输出 diagnostic 或 blocked，不得报告 selected candidate。

`winner_recall_retention` 必须作为 episode-level 指标单独报告：

```text
winner_recall_retention =
    P(target_episode has >= 1 surviving event after candidate fast-fail filter)
```

其分母是 120d-complete、可桥接的 target episode，不是 event-level winner 事件数。

并额外报告：

1. killed winner 的 t0 -> fast-fail touch drawdown / MAE 分布。
2. killed winner 的 touch 后 MFE 分布。
3. killed winner 中是否先触及 lower barrier 再触及 120d winner threshold。
4. fast-fail touch 到 first 50% / first 120d winner touch 的间隔。

解释规则：

```text
event_big_winner_120d_label = 1 且 fast_fail = 1 不自动说明 label 错；
它可能说明该 winner 路径需要承受不可接受的早期 drawdown。
```

## 9. 新旧 Target Bridge

09A 必须输出：

```text
outputs/publishable/tables/09A_fast_fail_label_frontier/cost_target_bridge.csv
```

在同一事件集上比较旧 `cost_bad_10_20` 与每个候选新 target，至少包含：

| column | meaning |
| --- | --- |
| `candidate_label_id` | 候选 label |
| `old_target_positive_n` | 旧 target positive |
| `new_target_positive_n` | 新 target positive |
| `old_new_both_positive_n` | 交集 |
| `old_only_positive_n` | 旧正新负 |
| `new_only_positive_n` | 新正旧负 |
| `both_negative_n` | 都为负 |
| `jaccard_overlap` | 正例 Jaccard |
| `old_only_n` | 旧正新负样本数，同 `old_only_positive_n` |
| `new_only_n` | 新正旧负样本数，同 `new_only_positive_n` |
| `old_only_winner_rate` | old-only cell `event_big_winner_120d_label` rate |
| `new_only_winner_rate` | new-only cell `event_big_winner_120d_label` rate |
| `old_only_power_caveat` | 当 old-only n < 30 时必须为 true |
| `new_only_power_caveat` | 当 new-only n < 30 时必须为 true |
| `component_failure_10_share` | fast-fail component share |
| `component_false_repair_20d_share` | false-repair component share |

如果 `old_only_n < 30` 或 `new_only_n < 30`，对应 winner-rate cell 只能作为 diagnostic text 使用，不得进入 label selection policy 或 Pareto 排序。

09C 的 uplift 不能直接和 H 旧 target frontier 逐点比较。选定新 target 后，必须重新冻结 09C gate。

`fast_fail_label_frontier.csv` 至少包含：

| column | meaning |
| --- | --- |
| `candidate_label_id` | 候选 label |
| `is_incumbent_baseline` | 现役 `failure_10_label` / -10% baseline 标记 |
| `denominator_id` | denominator view |
| `split` | train / validation / robustness / all |
| `raw_event_n` | raw event count |
| `horizon_complete_10d_n` | 10d fast-fail horizon-complete count |
| `horizon_complete_20d_n` | 20d cost / false-repair horizon-complete count |
| `censored_n` | censored count |
| `non_executable_n` | non-executable count |
| `not_evaluable_n` | not-evaluable count |
| `not_evaluable_share` | not-evaluable share |
| `coverage_asymmetry_caveat` | split-level coverage 不对称 caveat |
| `winner_120_complete_n` | 120d winner readout complete event count |
| `winner_120_incomplete_n` | 120d winner readout incomplete event count |
| `winner_120_incomplete_non_executable_n` | `candidate_outcome_120d_status = non_executable_next_open` count |
| `winner_120_incomplete_censored_n` | `candidate_outcome_120d_status = censored_incomplete_horizon` count |
| `winner_120_complete_share` | 120d complete share |
| `winner_120_completeness_caveat` | 120d complete share 偏低或 split 不对称 caveat |
| `positive_n` | candidate positive count |
| `positive_rate` | candidate positive rate |
| `episode_winner_recall_retention` | episode-level winner recall retention |
| `kill_wrong_rate` | `P(event_big_winner_120d_label = 1 | fast_fail = 1)` |
| `winner_injury_rate` | `P(fast_fail = 1 | event_big_winner_120d_label = 1)` |
| `old_target_jaccard` | 与旧 target positive set 的 Jaccard |
| `incumbent_delta_kill_wrong` | 相对 incumbent 的 kill-wrong 变化 |
| `incumbent_delta_winner_injury` | 相对 incumbent 的 winner-injury 变化 |
| `selection_gate_status` | pass / fail / diagnostic |

### 9.1 Selected label event binding

09A 必须输出事件级 selected label binding：

```text
outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_event_binding_summary.csv
```

`selected_label_event_bindings.parquet` 至少包含：

| column | meaning |
| --- | --- |
| `sample_id` | 稳定样本 id |
| `canonical_event_id` | canonical event id |
| `instrument` | 股票代码 |
| `event_t0_date` | t0 |
| `trade_time` | 可执行 trade time |
| `event_split` | train / validation / robustness |
| `source_pool_id` | 单一 source pool id；若同一事件属于多个 denominator，必须按 event x denominator 输出多行 |
| `event_regime_bucket` | t0 可见 regime |
| `episode_regime_bucket` | episode readout regime |
| `denominator_id` | denominator view |
| `horizon_complete_10d` | 10d complete flag |
| `horizon_complete_20d` | 20d complete flag |
| `horizon_complete_120d` | 120d winner readout complete flag |
| `candidate_outcome_120d_status` | 上游 120d outcome status 原字段 |
| `selected_fast_fail_10_label` | selected fast-fail component |
| `selected_fast_fail_touch_date` | first touch date |
| `selected_fast_fail_touch_pos` | first touch position |
| `selected_fast_fail_barrier_id` | touched barrier id |
| `frozen_false_repair_20d_label` | 08 false-repair component |
| `selected_cost_bad_10_20_target` | selected cost target |
| `event_big_winner_120d_label` | 主 winner readout label |
| `event_super_winner_120d_label` | sensitivity readout，不参与主选择 |
| `event_near_winner_120d_label` | sensitivity readout，不参与主选择 |
| `winner_censoring_status` | derived from `candidate_outcome_120d_status`: complete / incomplete_120d / non_executable / not_evaluable |
| `label_t1_date` | label end timestamp for purged CV / uniqueness |
| `censoring_status` | complete / censored / non_executable / not_evaluable |

`sample_id` 必须是 `canonical_event_id` 的确定性函数。若 `canonical_event_id` 缺失，必须用 `(instrument, event_t0_date, trade_time, source_event_id)` 的稳定 hash 生成，并在 manifest 记录生成规则。`selected_label_event_bindings.parquet` 的唯一键是 `(sample_id, denominator_id)`。

如果一个事件同时属于 R-core 与 R6，`selected_label_event_bindings.parquet` 必须按 `(sample_id, denominator_id)` 粒度输出多行，并提供 `canonical_event_id` 去重 readout。所有 frontier / bridge 表必须声明 denominator，跨 denominator 去重 readout 一律以 `canonical_event_id` 为准，避免重复计数。

09B / 09C 不得从 aggregate frontier 表重建 label。必须读取这份 event-level binding。

## 10. Label Agreement 与机制去重

09A 必须输出：

```text
outputs/publishable/tables/09A_fast_fail_label_frontier/label_pairwise_agreement.csv
```

至少报告：

1. Jaccard overlap。
2. Cohen's kappa。
3. positive-set overlap。
4. train / validation / robustness positive rate difference。
5. winner-injury difference。
6. cost target positive-rate difference。
7. 09C 主分母上的 not-evaluable share。

进入 09C 的 1-2 个 label 必须来自不同机制族，除非相邻 fixed percentage label 在 split stability 或 winner-injury 上有明确差异。

### 10.1 Label selection policy

09A 必须在读取 validation / robustness readout 之前冻结 label selection policy。默认 train-only selection gate 如下，config 可以更严格但不得更宽松：

| gate | default |
| --- | ---: |
| 主分母 `risk_on_r_core_horizon_complete` 上 `candidate_label_status` | `evaluable` |
| train 主分母 not-evaluable share | `<= 0.5%` |
| train positive rate | `5% - 45%` |
| train winner 120d complete share | report and non-collapse |
| train winner recall retention under candidate label | `>= 85%` |
| train winner-injury rate | report, and must not dominate selected winners without explanation |
| old/new target Jaccard | report, no hard pass |
| label pairwise duplicate threshold | Jaccard `>= 0.90` or kappa `>= 0.85` |

Validation / robustness 只做 selected-label readout：

| readout | default interpretation |
| --- | --- |
| validation / robustness positive rate | report; severe non-replication can downgrade selected label |
| validation / robustness winner 120d complete share | report; low completeness triggers caveat |
| max split positive-rate spread | if above predeclared threshold, force diagnostic downgrade |
| max split winner 120d completeness spread | report; severe spread triggers caveat or diagnostic downgrade |

Train-only 纪律：

1. label 选择、pairwise duplicate 剔除、Pareto 支配排序只能使用 train split 指标。
2. validation / robustness 只允许在 selected label 冻结后做 readout、caveat 或降级，不得用于在多个候选 label 之间挑选。
3. 如果 train-selected label 在 validation / robustness 上出现严重 non-replication，可以降级为 diagnostic，但不能回头选择 validation / robustness 上更好看的 label。
4. 默认 `oos_positive_rate_spread_force_diagnostic_threshold = 15pp`。如果 train-selected label 在 validation / robustness 上的 positive-rate spread 超过该阈值，必须强制输出 `09A_label_frontier_diagnostic_only_no_candidate`，不得仅记录 caveat 后进入 09C。

选择顺序：

1. 先排除 not-evaluable / sensitivity-only label。
2. 再排除 split positive-rate 不稳定 label；如果某 label 的 split-level not-evaluable share 明显不对称，必须先加 `coverage_asymmetry_caveat`，不得直接拿其 split spread 与全覆盖 fixed-% label 比较。
3. 再排除与更稳定同族 label 高度重复的 label；`-6%` fixed MAE10 与其他 fixed percentage label 的去重也只按本规则处理。
4. 在通过 bound gate 的 label 中，按 `(kill_wrong_rate ↓, winner_injury_rate ↓)` 做 Pareto 支配排序。被同族 label 同时支配的候选必须剔除。
5. 若跨族 label 不存在严格支配关系，优先选择不同机制族的 1-2 个 label，并报告与 incumbent baseline 的 `incumbent_delta_kill_wrong`、`incumbent_delta_winner_injury`。
6. 如果所有 label 都不通过，输出 `09A_label_frontier_diagnostic_only_no_candidate`，不得为了推进 09C 放宽门槛。

## 11. Structural Label Mechanism Contract

09A 必须输出：

```text
outputs/publishable/tables/09A_fast_fail_label_frontier/label_mechanism_contract.csv
```

至少记录：

1. `label_id`
2. `mechanism_family`
3. `series_used`
4. `lookback_window`
5. `as_of_rule`
6. `touch_price_field`
7. `feature_overlap_risk`
8. `selected_fast_fail_component_flag`
9. `selected_cost_target_component_flag`
10. `not_evaluable_policy`

如果 label 使用 EMA20 / EMA60 / swing low / ATR / sigma，后续 09B / 09C 必须把同机制 feature 单独做 overlap audit。

## 12. 输出

09A 必须输出：

```text
outputs/manifests/09A_fast_fail_label_frontier_manifest.json
outputs/publishable/reports/09A_fast_fail_label_frontier_report.md
outputs/publishable/reports/09A_fast_fail_label_frontier/fast_fail_label_contract.md
outputs/publishable/tables/09A_fast_fail_label_frontier/regime_label_pit_audit.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/candidate_label_evaluability_audit.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/fast_fail_label_frontier.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/cost_target_bridge.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/label_pairwise_agreement.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/label_mechanism_contract.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_contract.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_event_binding_summary.csv
outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
```

manifest 至少包含：

```text
experiment_id
run_timestamp
git_commit
decision
source_caveated
input_hashes
output_hashes
config_hash
source_pool_reconstruction_status
regime_label_pit_status
event_regime_source_status
episode_regime_source_status
derived_readonly_scope_status
selected_target_label
selected_target_contract_hash
selected_label_event_bindings_hash
sample_id_generation_status
label_bridge_status
bridge_power_caveat_status
candidate_label_evaluability_status
incumbent_baseline_status
coverage_asymmetry_status
winner_120_completeness_status
candidate_outcome_120d_status_reconciliation_status
label_selection_policy_hash
price_path_source_status
```

## 13. 09A 决策

允许的 09A 决策：

```text
09A_label_frontier_candidate_selected
09A_label_frontier_candidate_source_caveated_selected
09A_label_frontier_diagnostic_only_no_candidate
09A_label_frontier_input_blocked
09A_source_pool_reconstruction_blocked
09A_regime_label_pit_blocked
```

只有 `09A_label_frontier_candidate_selected` 或 `09A_label_frontier_candidate_source_caveated_selected` 允许进入 09C supported gate。若使用 source-caveated variant，09C 的 supported 决策也必须使用 source-caveated variant。其他状态仍可进入 09B 做 feature foundation，但 09C 只能 diagnostic。
