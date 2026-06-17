# 需求：11A2 Post-t0 Archetype Path Divergence Diagnostic

## 0. 本需求要回答的问题

11A1 已经在 `risk_on ∩ PIT-valid` 完整候选分母上证明：**t0 snapshot 的预注册 proxy 无法把 big winner 从失败暴露中稳健分离**。关键事实是「纠缠」，不是「无信息」：

- `P4_early_momentum_proxy`：winner delta **+6.11pp**，但 big_failure delta **+10.34pp**。
- `P6_clean_repair_proxy`：winner delta **+5.80pp**，但 big_failure delta **+7.34pp**。

也就是说，能在 t0 把 winner 概率抬上去的特征，**同样把 failure 概率抬上去**。能区分 winner 与 failure 的信息不在 t0 这个时间切片里，而是（可能）在 t0 之后的路径里展开。

11A2 只回答一个纯统计问题：

> 在 `risk_on` 下，固定到 t0，沿着 t0 之后的早期路径（t0+1 / t0+3 / t0+5 / t0+10 / t0+15 / t0+20）观察，不同 outcome archetype 类别（big winner / big failure / false repair / neutral）的早期路径分布**是否、以及从哪一天开始**出现统计显著的分离；并且在出现分离的那一天，最终行情**是否还没走完**（tradability lag）。

11A2 是 **diagnostic-only**。它不输出交易策略、不授权 routing/entry/exit、不放宽 10C rejector、不 claim 任何策略 EV，也不新增任何可上线特征。它的唯一产物是「t0 之后分离何时发生、有多强、是否在收益兑现之前、是否由幸存者偏差造成」的统计读数。

本轮范围固定为 `analysis_regime_bucket == risk_on`，沿用 11A1 的 strict PIT evaluated denominator。`risk_off`、`transition` 只作 out-of-scope 计数，不进入任何分离判定。

> 本需求在 framing 上取代 `next_step_discussion.md` §6 中原列的 `11A2_shakeout_proxy_pit_causality_audit`：把「区分 t0 / early-path / retrospective 特征 + category-B false_repair 削减」重述为一个更前置的 **path divergence / tradability-lag 诊断**。false_repair 削减问题作为 §5.2 子对照 `C2_winner_vs_false_repair_only` 保留；primary contrast `C1` 的负类口径与 11A1 `big_failure_proxy`（`fast_fail_10 OR false_repair_20`）严格一致。

## 1. 实验名称与状态

- experiment_id: `11_archetype_proxy_validation_system_v0`
- primary_run_id: `11A2_post_t0_archetype_path_divergence_diagnostic`
- parent_experiment_id: `10_riskon_layered_rejector_system_v0`
- upstream_run_id: `11A1_archetype_proxy_robust_payoff_risk_audit`
- status: `spec_frozen_pending_run`
- expected_entrypoint: `src/run_11a2_post_t0_archetype_path_divergence_diagnostic.py`
- expected_config: `configs/config_11a2_post_t0_archetype_path_divergence_diagnostic.yaml`
- expected_test_file: `tests/test_post_t0_archetype_path_divergence_diagnostic.py`

## 2. 核心原则

### 2.1 把结论精确化：t0 不是「无信息」，而是「纠缠」

11A2 不得把 11A1 的结果叙述为「t0 无信息」。正确表述是：

```
在 t0：winner 信号与 failure 信号共线（entangled）
=> t0 不存在稳定的 winner/failure 决策边界
=> 若信息存在，它在 t0 之后随路径解耦（decouple over trajectory）
```

11A2 的任务就是检验「解耦」是否真实发生、何时发生、以及解耦发生时收益是否已经走完。

### 2.2 diagnostic-only：11A2 不做的事

11A2 明确不做以下事项：

- 不输出 routing 决策、risk bucket 分配、仓位、entry/exit 规则。
- 不训练任何可上线的 winner/failure classifier；任何多变量 separability 估计只能 cross-fit，且仅用于度量「可分性强度」，绝不作为模型产出。
- 不把早期路径特征宣布为 entry feature。
- 不把「出现分离」等价于「存在可交易 edge」；可交易性只能在 11C 评估。
- 不修改 10A/10B/10C/10D/11A1 的输入、输出或既有结论。
- 不用本轮结果放宽 10C rejector。
- 不比较或解释 `risk_off`、`transition`；这些只作 out-of-scope count。

### 2.3 三条必须预注册的诚实条款（运行前写死）

11A2 的失败模式与 11A1 不同（11A1 怕假阳；11A2 怕「机械分离 / 幸存者分离 / 收益已走完」被误读成成功）。运行前必须冻结：

1. **幸存者条款（survivorship）**：早期路径特征条件在「存活到 t0+K」上。任何分离都必须**同时**在两种口径下报告：
   - (a) survivors-only：t0+K 仍 active 的样本；
   - (b) full-cohort：包含在 t0+K 之前已 fast-fail / 退市 / 停牌的样本，并对退市 / 停牌导致的不可成交路径用 §6.4 预注册 fill contract 赋值（退市按 `delist_haircut` 参数；停牌 carry-forward 停牌前最后收盘）。**fast-fail label touch 本身不得作为 primary full-cohort 的终止性 fill 事件**：若 touch 后仍有真实 qfq bar，EP1–EP7、`ep_mfe/ep_mae`、onset 与 tradability 一律继续使用真实价格路径；`selected_fast_fail_*` touch / barrier 字段只能进入 EP8B label-overlap audit。
   `separation_detected_*` 状态必须以 full-cohort confirmed K* 为准（见 §7.3 / §9）；survivors-only 仅作对照。若分离仅在 survivors-only 口径成立，而在 full-cohort 口径塌缩，则该分离必须标记 `survivorship_induced_separation`，最终状态不得为 `separation_detected_tradable`。

2. **可交易性条款（tradability lag）**：若分离只在「最终行情已实现大部分」之后才出现，则预注册结论是 `separation_detected_late`，不是成功。判据见 §7.4：在 full-cohort confirmed onset day `K*`，big winner 组 `median(ep_mfe_to_K* / mfe_120_recomputed)`（同源同锚点重算，见 §7.4）超过 `tradability_realized_fraction_ceiling`（默认 0.50）即判为 late。

3. **同义反复条款（tautology）**：早期路径特征与 outcome 在机械上重叠（例如「t0→t0+5 累计收益」必然与 forward_return 相关）。因此**单独的分离强度（AUC/KS）不是结论**；结论是 (onset day, tradability lag, survivorship-robustness) 的联合体。raw 多变量 AUC 仅 secondary readout。

### 2.4 本轮 regime scope

- evaluated denominator 必须满足 11A1 同款条件：10A post-dedup R-core primary denominator → `analysis_regime_bucket == risk_on` → strict PIT inner join（`is_listed=true ∧ is_st=false ∧ is_suspended=false`）。
- 非 `risk_on` / PIT-invalid 行只进入 scope 审计表，不进入分离统计。
- 本轮不得把 `risk_on` 结论外推到 `risk_off` / `transition` / 非 PIT universe。

## 3. 上游输入

### 3.1 讨论与需求输入（解释来源，非可变数据）

- `../10_riskon_layered_rejector_system_v0/next_step_discussion.md`
- `requirement_11a1_archetype_proxy_robust_payoff_risk_audit.md`
- `outputs/publishable/reports/11A1_archetype_proxy_robust_payoff_risk_audit_report.md`

runner 必须在 `input_artifact_audit.csv` 记录 path、sha256、mtime。

### 3.2 11A1 frozen scope 对账输入（必需）

11A2 必须复现 11A1 的 evaluated denominator，并与 11A1 已发布的 scope 审计表对账，确保两轮分母一致：

- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/risk_on_scope_filter_audit.csv`
- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/pit_universe_scope_filter_audit.csv`
- `outputs/publishable/tables/11A1_archetype_proxy_robust_payoff_risk_audit/acceptance_summary.csv`

若 11A1 local_cache `proxy_scored_denominator.parquet` 存在（11A1 spec §12.2 允许但不强制），优先直接消费它作为 frozen evaluated denominator；否则按 §4 从相同上游 contract 重建，并对账 row count。

### 3.3 10A / 09B / 08 / 09A 上游 contract（必需）

与 11A1 §3.2–§3.6 完全相同的输入集合，用于重建 evaluated denominator、regime 回填、horizon 完整性与 outcome 标签：

- 10A：`10A_density_rule_system_manifest.json`、`post_dedup_event_bindings.parquet`、`post_dedup_population_contract.csv`
- 09B：`feature_contract.csv`、`feature_transform_contract.json`、`feature_matrix.parquet`、`sample_uniqueness_weights.parquet`
- 08：`candidate_family_event_labels.parquet`、`run_manifest.json`
- 09A：`selected_label_event_bindings.parquet`、`topics/02_AFML_BIG_WINNER/configs/labels.yaml`

primary denominator 固定取值与 11A1 §3.2 一致：

| 字段 | 固定取值 |
| --- | --- |
| `population_id` | `10A__same_instrument_cooldown_10d` |
| `denominator_id` | `post_dedup_risk_on_r_core` |
| `admission_status` | `admitted` |
| `readout_only_flag` | `false` |

regime 回填规则与 11A1 §3.5 一致：

```text
analysis_regime_bucket =
  coalesce_non_empty(
    09A.episode_regime_bucket,
    10A.event_regime_bucket,
    09A.event_regime_bucket
  )
```

### 3.4 价格、PIT universe 与状态数据（必需，用于早期路径构造）

11A2 的早期路径特征必须从 daily bar 构造，因此价格数据是一等输入，不只是完整性审计：

- PIT executable universe: `topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv`
- qfq primary dir: `topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq`
- qfq fallback dir: `topics/02_AFML_BIG_WINNER/data/interim/qlib_csv/day`
- board metadata: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/instrument_metadata_target_universe.csv`
- SH name history dir: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/sh_name_history`
- SZ name history: `topics/02_AFML_BIG_WINNER/data/raw/akshare/status/stock_info_sz_change_name_short.csv`

qfq primary daily bar 至少包含：`instrument`, `date`, `open`, `high`, `low`, `close`, `volume`, `money`。若使用 qfq fallback dir，允许从文件名派生 `instrument`，但必须在 `early_path_feature_coverage_audit.csv` / manifest 中标记 `instrument_source = filename_derived_fallback`。

PIT/status 数据必须能在 t0 之后逐日判断退市 / 停牌，用于 §2.3 幸存者条款的 full-cohort fill。`ST` 仅用于 t0 strict PIT eligibility（`event_t0_date` 当天 `is_st=false`），**本轮不做 post-t0 / future-ST 状态处理**：t0 之后进入 ST 不作为 full-cohort fill、剔除、终止或 final-status ceiling 条件。

> 早期路径特征只允许使用 t0 之后**实际发生**的 daily bar；不得使用任何超出 `[t0, t0+K]` 窗口的未来信息构造 t0+K 的特征值（例如 t0+K 的特征不得引用 t0+20 的价格）。

## 4. Evaluated denominator 与对账

### 4.1 重建规则

按 11A1 §3.2 / §3.5 / §3.7 的口径重建 evaluated denominator：

```text
10A post_dedup_risk_on_r_core (admitted, readout_only=false)
  -> analysis_regime_bucket == risk_on
  -> strict PIT inner join on (instrument, event_t0_date) = (instrument, membership_date)
     WHERE is_listed=true AND is_st=false AND is_suspended=false
```

join key 与 canonical id policy 沿用 11A1 §4.1（优先用 10A 物化 join key；`binding_canonical_event_id` 优先来自 10C join；pipe split 仅作 fallback/cross-check）。

### 4.2 scope 对账

必须输出 `scope_reconciliation_vs_11a1.csv`，按 split 比较 11A2 重建结果与 11A1 已发布审计表：

- `split`
- `a2_risk_on_pre_pit_row_n`
- `a1_risk_on_pre_pit_row_n`
- `a2_pit_valid_evaluated_row_n`
- `a1_pit_valid_evaluated_row_n`
- `pre_pit_row_n_match_flag`
- `pit_valid_row_n_match_flag`
- `reconciliation_status`

若任一 split 的 `pit_valid_evaluated_row_n` 与 11A1 差异 `> 0.5%`，最终状态不得高于 `11A2_post_t0_archetype_path_divergence_statistics_incomplete`，并记录 `denominator_drift_vs_11a1`。

`pit_valid_evaluated_row_n` 是 11A2 后续所有分离统计的唯一分母。若为空，最终状态为 `11A2_post_t0_archetype_path_divergence_input_blocked`。

## 5. Outcome archetype 类别定义（被分离的对象）

### 5.1 类别

所有类别使用 11A1 frozen 标签（来自 10A / 08），不引入新标签。`big_failure_proxy` 必须与 11A1 §5.2 完全一致，即 `fast_fail_10 == true OR false_repair_20 == true`，不得在 11A2 重新窄化，否则 primary contrast 会偏离 11A1 纠缠结论。类别在 evaluated denominator 内划分如下：

| class_id | 定义 | 含义 |
| --- | --- | --- |
| `class_big_winner` | `winner_120 == true` | 右尾 big winner |
| `class_big_failure_proxy_nonwinner` | `winner_120 == false AND (fast_fail_10 == true OR false_repair_20 == true)` | 与 11A1 `big_failure_proxy` 对齐的非 winner 失败暴露并集 |
| `class_neutral_chop` | `winner_120 == false AND fast_fail_10 == false AND false_repair_20 == false`，且 horizon 完整 | 中性 / 震荡未兑现 |

`class_big_failure_proxy_nonwinner` 内部再做两个**互斥子划分**，仅用于 §5.2 子对照诊断，不改变 primary contrast 的并集口径：

| subclass_id | 定义 | 含义 |
| --- | --- | --- |
| `subclass_fast_fail` | `fast_fail_10 == true`（可同时 false_repair） | 破坏型快速失败 |
| `subclass_false_repair_only` | `false_repair_20 == true AND fast_fail_10 == false` | 反弹/修复失败（非快速破坏） |

两个 subclass 对 `class_big_failure_proxy_nonwinner` 构成完备且互斥的划分。

horizon 完整性：类别判定要求对应 horizon 标签可得；`winner_120` 需 `horizon_complete_120d`，`false_repair_20` 需 `horizon_complete_20d`，`fast_fail_10` 需 `horizon_complete_10d`。任一所需 horizon 不完整的样本不得归入任何已 resolved 类别，必须进入 `class_unresolved`，只计数、不参与分离统计。

### 5.2 主对照与子对照

| contrast_id | 正类 | 负类 | tier | 主要回答的问题 |
| --- | --- | --- | --- | --- |
| `C1_winner_vs_big_failure_proxy` | `class_big_winner` | `class_big_failure_proxy_nonwinner` | primary | 11A1 纠缠的那一对（winner vs `fast_fail OR false_repair` 并集）：早期路径能否解耦 |
| `C2_winner_vs_false_repair_only` | `class_big_winner` | `subclass_false_repair_only` | sub | constructive shakeout vs destructive false repair 能否区分 |
| `C3_winner_vs_fast_fail` | `class_big_winner` | `subclass_fast_fail` | sub | winner vs 破坏型快速失败能否区分 |
| `C4_winner_vs_neutral` | `class_big_winner` | `class_neutral_chop` | sub | 右尾相对中性背景的分离 |
| `C5_winner_vs_all_nonwinner` | `class_big_winner` | 其余全部已 resolved 类别 | sub | 总体右尾可分性 |

`C1` 为唯一 primary contrast，且其负类口径必须等于 11A1 `big_failure_proxy` 的非 winner 并集。最终 `separation_detected_*` 状态只由 `C1` 决定；`C2`/`C3` 把并集拆成 fast_fail 与 false_repair_only 两路子诊断，用于解释分离来自哪一支，但不单独决定 final status。所有 contrast 必须在 all/train/validation/robustness 四个 split 上各自输出。

### 5.3 类别计数审计

必须输出 `outcome_class_count_audit.csv`，`class_id` 必须同时覆盖 §5.1 的三个父类与两个 subclass：

- `split`
- `class_id`（`class_big_winner` / `class_big_failure_proxy_nonwinner` / `class_neutral_chop` / `subclass_fast_fail` / `subclass_false_repair_only` / `class_unresolved`）
- `row_n`
- `weight_sum`（`final_sample_weight`，缺失记 1 并标 `weight_missing_fallback`）
- `unique_instrument_n`
- `class_rate`

任一 contrast 在 train 或 robustness 上，若任一侧 `row_n < 60` 或 `unique_instrument_n < 30`，该 contrast 在该 split 标记 `contrast_underpowered`，不得给出该 split 的 `separation_detected`。

## 6. 早期路径特征空间（category B，readout-only）

### 6.1 观察窗口

预注册早期窗口：

```text
K ∈ {1, 3, 5, 10, 15, 20}  （交易日，相对 t0）
```

每个特征在每个 K 上计算一次，得到一条随 K 演化的分离曲线。

### 6.2 价格锚点 policy（运行前冻结）

所有 return / drawdown / reclaim / MFE / MAE 必须使用统一锚点，且锚点定义必须与 10A label 的交易约定对账，否则 K=1/3 的读数无法复现。预注册锚点：

| anchor | 定义 | 用途 |
| --- | --- | --- |
| `event_t0_close` | `event_t0_date` 当日 qfq 收盘价 | 事件结构参考（t0 高/低点收复、close-vs-t0 形态） |
| `entry_anchor_price` | `t0+1` 交易日 qfq 开盘价（即可执行建仓价） | 所有 `ep_ret_*`、`ep_*_drawdown`、`ep_mfe_*`、`ep_mae_*` 的**唯一收益基准** |

硬约束：

- 所有「收益型」early-path 量（`ep_ret_t0_to_K`、`ep_max_drawdown_to_K`、`ep_recovery_from_min_to_K`、`ep_mfe_to_K`、`ep_mae_to_K`）一律以 `entry_anchor_price` 为分母，模拟「t0 收盘看到事件、t0+1 开盘可建仓」的可执行口径，避免把 t0 当日不可成交的涨跌幅算进收益。
- 「结构型」量（`ep_close_vs_t0_close`、`ep_breach_t0_low_through_K_flag`、`ep_close_above_t0_high_at_K_flag`）以 `event_t0_close` / t0 当日 high/low 为参考。
- 窗口区间统一为 `(t0, t0+K]`，即从 `t0+1` 到 `t0+K`（含），不含 t0 当日。`ep_mfe_to_K`、`ep_mae_to_K` 在该区间内用 daily high/low 相对 `entry_anchor_price` 计算。
- runner 必须输出 `price_anchor_reconciliation.csv`，把 `entry_anchor_price` 与 10A/11A1 物化的 executable anchor 逐行对账：优先使用 `event_window_anchor_date` / `event_window_anchor_pos`，并把 09A `trade_time` 视作同义 trade-open date cross-check；若上游另有 `trade_open_date` / `trade_open_price`（例如 08 label artifact）则作为补充 price check。字段至少包括 `anchor_date_match_rate`、`anchor_price_rel_diff_p95`、`anchor_source`、`anchor_status`。`entry_anchor_price` 必须从 qfq 在 `event_window_anchor_date`（通常为 t0+1 可执行开盘日）的 `open` 重算；若只存在 `event_t0_date` 而无法解析 executable anchor，则回退为 `session_after(event_t0_date)` qfq 开盘价并标 `anchor_fallback_t0p1_open`；若开盘缺失（停牌等），按 §6.4 full-cohort fill 处理并标 `anchor_unavailable_filled`。
- 锚点对账失败率（`1 - anchor_date_match_rate`）超过 config 阈值（默认 0.5%）时，最终状态不得高于 `11A2_post_t0_archetype_path_divergence_statistics_incomplete`。

### 6.3 特征族（全部 category B early-path readout）

所有特征仅用 `(t0, t0+K]` 窗口内 daily bar 计算（§6.2 锚点），全部标注 `category = B_early_path_readout_only`，不得进入任何可上线特征集合。t0+K 的特征值不得引用任何 `> t0+K` 的未来 bar。

| feature_family | 字段示例 | 说明 | onset/separability 资格 |
| --- | --- | --- | --- |
| `EP1_cum_return_path` | `ep_ret_t0_to_K`, `ep_close_vs_t0_close` | t0 后累计收益形态 | **primary return channel 来源** |
| `EP2_path_drawdown` | `ep_max_drawdown_to_K`, `ep_min_close_ret_to_K` | 窗口内最深回撤 / 下行结构 | **primary structure channel 来源** |
| `EP3_recovery_shape` | `ep_recovery_from_min_to_K`, `ep_close_in_range_K` | 自窗口低点的修复幅度 | separability 可用 |
| `EP4_ema_reclaim` | `ep_close_above_ema20_at_K_flag`, `ep_days_above_ema20_through_K` | 均线收复结构 | separability 可用 |
| `EP5_event_level_reclaim` | `ep_breach_t0_low_through_K_flag`, `ep_close_above_t0_high_at_K_flag` | 事件 t0 高/低点的收复或跌破 | separability 可用 |
| `EP6_volume_structure` | `ep_down_day_vol_contraction_K`, `ep_up_day_vol_expansion_K`, `ep_vol_decay_ratio_K` | 放量下跌后缩量等量价结构 | separability 可用 |
| `EP7_volatility_sequence` | `ep_atr_change_t0_to_K`, `ep_range_contraction_K` | 波动收缩/扩张序列 | separability 可用 |
| `EP8A_structural_failure_price_action` | `ep_structural_drawdown_8pct_by_K_flag`, `ep_structural_drawdown_10pct_by_K_flag`, `ep_days_to_first_structural_drawdown` | 仅由本轮 qfq price path 重算的结构性下破 / drawdown 触达 | secondary stress-test only |
| `EP8B_label_aligned_fail_timing` | `ep_fast_fail_barrier_touched_by_K_flag`, `ep_days_to_first_fast_fail` | 09A/10A fast-fail label 对齐的 barrier / touch timing | **禁止**：label-overlap audit only |

`EP8A` 与 `EP8B` 必须拆开，防止把 label definition echo 误读为 path divergence：

- `EP8A_structural_failure_price_action` 只能用本轮 §6.2 qfq path、`entry_anchor_price` 与预注册 drawdown 阈值重算；不得读取 09A/10A 的 `selected_fast_fail_*` label 字段、barrier id 或 touch_pos。`EP8A` 可进入 §7.1 单变量 secondary stress-test readout，用于观察「纯 price-action 下破」是否与 outcome 同步，但不得进入 primary dual-channel onset、不得进入 final status，且默认不进入 §7.2 multivariate cross-fit separability。
- `EP8B_label_aligned_fail_timing` 是 label-aligned audit family。`C1`/`C3` 的负类由 `fast_fail_10` 定义，而 `EP8B` 的 `ep_fast_fail_barrier_touched_by_K_flag` / `ep_days_to_first_fast_fail` 与该标签在构造上直接重叠，尤其 K<=10 会机械抬高 separability。因此 `EP8B`：
  - 不得进入 §7.1 单变量 onset 主曲线；
  - 不得进入 §7.2 multivariate cross-fit separability 的特征集合；
  - 不得进入任何 `divergence_onset_day` / `separation_detected_*` 判定；
  - 仅作为 `label_overlap_tautology_audit.csv` 输出：报告 `ep_fast_fail_barrier_touched_by_K_flag` 与 `fast_fail_10` 在各 K 的 overlap（命中率、Jaccard、lead-lag），用于量化「分离里有多少其实是 fast_fail 标签的同义反复」，从而校准 §7/§9 结论。

`ep_mfe_to_K`、`ep_mae_to_K`（窗口内 MFE/MAE，§6.2 锚点）必须额外计算，专用于 §7.4 tradability lag；它们是上界路径读数，不得作为「分离特征」纳入 onset 主曲线或 multivariate separability，避免 §2.3 同义反复。

### 6.4 缺失与 full-cohort fill contract（运行前冻结）

survivors-only 与 full-cohort 两口径的 fill 规则必须写成可执行 config contract，否则 survivorship audit 方向不可复现。

survivors-only 口径：要求样本在 `(t0, t0+K]` 内有完整 daily bar 且 `entry_anchor_price` 可得；否则该样本在该 K 的 survivors-only 统计中剔除并计数。

full-cohort 口径：在 `(t0, t0+K]` 内发生退市 / 停牌导致不可成交的样本不得剔除，按下列**优先级顺序**（先命中先适用）赋值，并记录 `fill_reason`。fast-fail label touch 不是 primary full-cohort 的终止性事件，不能改写 EP1–EP7 / `ep_mfe` / `ep_mae` 的真实价格路径。

| 优先级 | fill_reason | 状态源 | 触发条件 | 填充价 / 赋值 |
| --- | --- | --- | --- | --- |
| 1 | `delisted` | board metadata + SH/SZ name history delist date | 在 `(t0, t0+K]` 内退市 | 退市生效日起，价格序列填 `delist_fill_price`；config 预注册为 `last_tradable_close * (1 - delist_haircut)`，默认 `delist_haircut = 1.0`（即归零）；同时输出 `delist_haircut` 取值，便于敏感性 |
| 2 | `suspended` | PIT universe `is_suspended` + qfq 缺 bar | 在 `(t0, t0+K]` 内停牌且无成交 | 停牌期价格 carry-forward 停牌前最后收盘 `last_pre_suspend_close`；复牌后恢复真实 bar |
| 3 | `complete_path` | qfq | 窗口内完整可成交，或 fast-fail touch 后仍有真实 qfq bar | 使用真实 daily bar |

约束：

- 退市 / 停牌终止性事件的判定与赋值只用 `<= t0+K` 的信息。post-t0 ST 不参与本轮 fill / exclusion / ceiling。
- **fast-fail touch 坐标系（防 off-by-one）**：`selected_fast_fail_*` 只允许用于 EP8B `label_overlap_tautology_audit.csv` 与 `touch_pos_coordinate_policy.csv`，不得用于 primary full-cohort fill、EP1–EP7、`ep_mfe/ep_mae`、onset、tradability 或 final status。09A/10A 的 `selected_fast_fail_touch_pos` 可能是绝对 session index，不得直接拿 `selected_fast_fail_touch_pos <= K` 比较。实现必须优先使用 `selected_fast_fail_touch_date` 或 `selected_fast_fail_touch_offset_sessions` 转换成 actual session date `fast_fail_touch_date`，再判断 `fast_fail_touch_date <= session_date(t0 + K)`。runner 必须输出 `touch_pos_coordinate_policy`（字段：`touch_pos_origin`、`touch_pos_origin_offset_vs_t0`、`converted_via`、`coordinate_status`），并对 10A/11A1 `event_window_anchor_date`、09A `trade_time` 与 t0 的相对偏移做一致性校验；偏移不可解析率超 config 阈值时，最终状态不得高于 `11A2_post_t0_archetype_path_divergence_statistics_incomplete`。
- 若报告需要额外展示 label-aligned barrier-stop sensitivity，必须单独输出为 `label_aligned_barrier_stop_sensitivity`，且不得进入 `separation_curve_readout.csv` 的 primary rows、`divergence_onset_readout.csv`、`tradability_lag_readout.csv` 或任何 `separation_detected_*` final status。`break_swing_low_20` 的 barrier price 若需重构，必须按 09A frozen contract 从 qfq 在 trade-open 前一交易日的 `prior_swing_low_20 = low.shift(1).rolling(20, min_periods=20).min()` 计算；不可得时只允许标记 `barrier_price_unavailable`，不得用触达日收盘价替代 primary path。
- `delist_haircut` 是预注册敏感性参数。final status 的 primary 口径使用 config 中的 `delist_haircut`（默认 `1.0`，即归零）；report 必须同时给出 `delist_haircut = 1.0` 与 `delist_haircut = 0`（最后可成交价）两个端点下的 survivorship audit。若 `delist_haircut = 0` 端点会推翻 primary 口径下的 `separation_detected_tradable`（例如变成 `survivorship_induced_separation`、`survivorship_direction_flip`、`separation_absent` 或 `late_most_move_realized`），必须标记 `delist_haircut_sensitivity_conflict`，最终状态不得高于 `11A2_post_t0_archetype_path_divergence_statistics_incomplete`。
- 每个 (feature, K, split) 必须输出 survivors-only 与 full-cohort 两套 `eligible_row_n` 与缺失率。
- 必须输出 `full_cohort_fill_audit.csv`：`split`、`K`、`delist_haircut`、`fill_reason`、`row_n`、`weight_sum`、`unique_instrument_n`，给出 fill_reason 分布，并能复核 `delist_haircut = 1.0 / 0.0` 两端点。

## 7. 分离度量

### 7.1 单变量分离曲线

对每个 (contrast, feature, K, split, cohort) 输出：

- weighted KS statistic（正负类经验分布最大差）
- one-feature AUC（正类为 1）
- robust effect size：Cliff's delta 与标准化均值差（winsorized 1%/99% 后计算）
- 正类与负类的 median、p25、p75
- `eligible_positive_n`, `eligible_negative_n`
- bootstrap 95% CI（instrument-block，见 §8.1）

### 7.2 多变量可分性（cross-fit，secondary）

为度量「早期路径整体可分性强度」，允许在每个 (contrast, K, split) 上做 cross-fit separability 估计：

- 仅用 §6.3 的 category-B 特征 `EP1`–`EP7`，**必须排除 `EP8A` / `EP8B`**（structural-failure stress-test 与 label-overlap，见 §6.3）与 `ep_mfe/ep_mae`。
- 5-fold cross-fit，fold 切分按 `instrument` group（同一 instrument 不跨 fold），避免泄漏。
- 估计器固定为 L2 logistic，超参数预注册，不调参。
- 输出 cross-fit AUC 的均值与 95% CI。
- 该读数标注 `multivariate_separability_secondary`，仅描述可分性强度，**不得**作为模型产出或 onset 主判据。

### 7.3 divergence onset day

`divergence_onset_day` 必须拆成「channel」与「tier」两个维度，避免单纯用 EP1 累计收益把 outcome proxy 提前映射成 pseudo-separability。

#### 7.3.1 primary dual-channel metric

本轮预注册两个 primary channel，均使用 winsorized 1%/99% 后的 weighted Cliff's delta：

| channel_id | metric | family | 用途 |
| --- | --- | --- | --- |
| `return_channel` | Cliff's delta of `EP1.ep_ret_t0_to_K` | EP1 | 收益路径分离 |
| `structure_channel` | Cliff's delta of `EP2.ep_max_drawdown_to_K` | EP2 | 下行结构 / drawdown 路径分离 |

`EP2.ep_max_drawdown_to_K` 必须以 `entry_anchor_price` 为基准，并以有符号收益表示：窗口内最低 low 相对 entry 的收益，通常为 `<= 0`。因此 `structure_channel` 的 `winner_higher` 表示 winner drawdown 更浅，`winner_lower` 表示 winner 更深回踩 / shakeout。两个 channel 的方向**不要求相同**；每个 channel 只要求 train 与 robustness 在自身方向上稳定。

primary final status 不再允许由 `return_channel` 单独决定。`return_channel` confirmed 但 `structure_channel` 不支持时，必须标 `return_only_pseudo_separability_risk`，只能作为 readout，不能写任何 `separation_detected_*` 状态。

#### 7.3.1a dual-channel collinearity readout（corroboration vs echo）

`return_channel`（终点收益）与 `structure_channel`（窗口内最差点收益）都以 `entry_anchor_price` 为基准，对动量型 winner 可能是同一现象的两个投影。若两通道高度同向，则「dual-channel 双双通过」是 echo 而非独立佐证，会让 `separation_detected_tradable` 的说服力被高估。因此必须显式量化二者的相关性，并把高共线作为一个 readout caveat：

对每个 (contrast, K, split, cohort) 计算并写入 `divergence_onset_readout.csv`：

- `channel_rank_corr`：在该 cell 的 evaluated 样本上，`ep_ret_t0_to_K` 与 `ep_max_drawdown_to_K` 的 weighted Spearman 秩相关。
- `channel_direction_agreement_rate`：bootstrap（§8.1，instrument-block）中两通道 `separation_direction` 同号（在「更利好 winner」方向上一致）的迭代比例。
- `dual_channel_collinearity_flag`：若 `abs(channel_rank_corr) >= dual_channel_collinearity_corr_ceiling`（§8.5，默认 0.85）或 `channel_direction_agreement_rate >= dual_channel_direction_agreement_ceiling`（默认 0.95），标 `dual_channel_collinear_readout`。

`dual_channel_collinear_readout` 不改变 final status 判定门（dual-channel Tier3 仍按 §7.3.4），但报告 §10.3 必须前置标注该 flag：当 C1 full-cohort confirmed onset 所在 K* 被标 `dual_channel_collinear_readout` 时，必须说明「双通道确认更接近 corroboration-by-echo，而非正交独立证据」，并把它与 §7.4 tradability-late 风险一并解读。鼓励（非强制）追加一个非收益族（EP4/EP5 reclaim flag 或 EP6 volume）作为 tie-break 第三通道 readout，但本轮不进入 final status 门。

#### 7.3.2 signed metric 与方向

所有 onset 判据对有符号 metric 使用绝对值判断强度，同时保留方向：

```text
separation_direction(channel, contrast, K, split, cohort) =
  sign(channel_separation_metric) ∈ {winner_higher, winner_lower, undetermined}
```

若真实分离是「winner 先回踩、failure 短暂反弹」，delta 可能显著为负，但仍是真实分离；不得把反向分离误判为 absent。任一 channel 的 train/robustness 方向冲突时，该 channel 在该 K 标 `onset_direction_conflict`，不得进入 Tier3 confirmed。

#### 7.3.3 三层 onset 定义

`divergence_onset_day` 必须输出三层，防止把「没有通过最强确认」误读为「没有结构」：

```text
channel_tier1_train_onset_day(channel, contrast, cohort) =
  train split 中最小的 K，使得：
    abs(channel_separation_metric) >= onset_threshold
    AND bootstrap 95% CI 不跨 0
    AND min(abs(ci_low), abs(ci_high)) > null_band_upper
  否则 = none

channel_tier2_stability_adjusted_onset_day(channel, contrast, cohort) =
  最小的 K，使得：
    train 在该 K 满足 tier1 条件
    AND robustness 在该 K 的 separation_direction 与 train 一致
    AND abs(robustness channel_separation_metric) > null_band_upper
    AND robustness directional bootstrap probability >= tier2_directional_prob_floor
  否则 = none

channel_tier3_confirmed_onset_day(channel, contrast, cohort) =
  最小的 K，使得：
    train 与 robustness 在该 K 上均满足 tier1 条件
    AND 两 split 的 separation_direction 一致
  否则 = none
```

Tier 解释：

| tier | 字段 | 解释 | 是否可进 final status |
| --- | --- | --- | --- |
| Tier 1 | `tier1_train_onset_day` | train-only structure readout | 否 |
| Tier 2 | `tier2_stability_adjusted_onset_day` | train 显著，robustness 方向和最小强度支持，但未必 CI 显著 | 否 |
| Tier 3 | `tier3_confirmed_onset_day` | train 与 robustness 同一 K 严格确认 | 是，但必须再通过 dual-channel |

#### 7.3.4 dual-channel onset

对每个 (contrast, cohort, tier) 计算 `dual_channel_*_onset_day`：

```text
dual_channel_tierX_onset_day(contrast, cohort) =
  最小的 K，使得 return_channel 与 structure_channel 各自的 tierX onset 均已发生在 <= K，
  且在该 K 满足对应 tier 的一致性检查：
    Tier1: train 中两个 channel 的 separation_direction 均非 undetermined，
           且两个 channel 的 abs(train metric) 均 > null_band_upper；
    Tier2: train/robustness 对两个 channel 均满足 Tier2 方向与最小强度要求；
    Tier3: train/robustness 对两个 channel 均满足 Tier3 confirmed 要求；
  否则 = none
```

其中 X ∈ {1, 2, 3}。`confirmed_divergence_onset_day` 是兼容旧字段名的别名，定义为：

```text
confirmed_divergence_onset_day(contrast, cohort)
  = dual_channel_tier3_confirmed_onset_day(contrast, cohort)
```

若 `return_channel` 出现 Tier3 confirmed 但 `structure_channel` 没有达到 Tier2，必须在 `divergence_onset_readout.csv` 标 `return_only_pseudo_separability_risk`。若 `structure_channel` 达到 Tier2/Tier3 但 `return_channel` 不支持，标 `structure_only_instability_readout`。这些状态只解释 path structure，不进入 final status。

#### 7.3.5 feature selection 纪律

- 不做任何跨特征 max/选择；primary 只使用 `return_channel` 与 `structure_channel` 两个预注册 channel。
- `EP3`–`EP7` 的单变量曲线只作 secondary readout，不参与 onset 判定。
- `EP8A` 只能作 secondary stress-test；`EP8B` 只能作 label-overlap audit；二者都不得进入 onset 判定。
- `onset_threshold`、`null_band_upper`、`tier2_directional_prob_floor` 在 §8.5 config 预注册，运行前冻结并入 manifest hash。`onset_threshold` 与 `null_band_upper` 均为 Cliff's delta effect-size 单位，不是收益百分点。
- 若研究者仍希望报告「最强单特征 onset」，必须把「跨 `EP1`–`EP7` 选最强」这一步纳入 §8.4 null simulation 的同一选择流程（null 下也重复选最强），并在 report 中标为 `selection_adjusted_secondary_readout`，绝不作为 primary onset 或 final status 依据。

所有 channel-level 与 dual-channel onset 字段均必须分 cohort（survivors-only / full-cohort）各算一次。

### 7.4 tradability lag（中心诚实指标）

tradability lag 必须以 **`C1` + full-cohort + dual-channel Tier3 `confirmed_divergence_onset_day`** 计算，即 `K* = confirmed_divergence_onset_day(C1, full_cohort)`；survivors-only K* 只作对照输出，不决定 final status。若 `K*` 为 none，则取 full-cohort 下 `dual_channel_tier1_train_onset_day` 的最小 K 作为 provisional，并标注 `provisional_train_only_not_status_eligible`；若 Tier1 也不存在，则 tradability lag 状态为 `onset_absent`。对 `class_big_winner` 输出。

**basis 对账（防复权/基准口径错配）**：`ep_mfe_to_K*` 来自本轮 qfq path（§6.2 锚点），而 frozen `mfe_120d` 来自 08/09A aggregate，二者基准价与复权口径可能不同；若直接相除，basis mismatch 会被误读成 late/early。因此必须先重算并对账：

- `mfe_120_recomputed` = 用本轮同一 qfq 源、同一 `entry_anchor_price`、在 `(t0, t0+120]` 内重算的 MFE。
- 输出 `mfe_basis_reconciliation.csv`：`instrument`、`event_t0_date`、`mfe_120d_frozen`、`mfe_120_recomputed`、`mfe_120_rel_diff`、`basis_status`。
- 若 `abs(mfe_120_rel_diff) > mfe_basis_rel_diff_ceiling`（config 预注册，默认 0.05），该行标 `mfe_basis_mismatch`，**不参与** tradability status 计算，只进 basis audit。
- tradability lag 的分母统一使用 `mfe_120_recomputed`（同源同锚点），不使用 frozen `mfe_120d`，以保证分子分母 basis 一致。

对 basis 一致（`basis_status == ok`）的 `class_big_winner` 样本输出：

- `winner_median_ep_mfe_to_Kstar_over_mfe120` = `median(ep_mfe_to_K* / mfe_120_recomputed)`（**primary tradability metric**）
- `winner_median_ep_ret_to_Kstar_over_fwd120` = `median(ep_ret_t0_to_K* / forward_return_120d)`，标 `secondary_basis_unchecked`：分子 `ep_ret_t0_to_K*` 来自本轮 qfq，分母 `forward_return_120d` 是 08/09A frozen aggregate，basis 未对账。该字段只作 secondary readout，**不进入** `winner_realized_fraction_status` 或任何 final status。若实现方选择重算 `forward_return_120_recomputed`（同源同锚点），可改标 `basis_checked` 并作为补充对照，但 primary tradability 判据仍只用 MFE 比值。
- `tradability_basis_eligible_n` 与 `tradability_basis_excluded_n`
- `winner_realized_fraction_status`：

| status | 条件 |
| --- | --- |
| `tradable_window_open` | `winner_median_ep_mfe_to_Kstar_over_mfe120 <= tradability_realized_fraction_ceiling`（默认 0.50） |
| `late_most_move_realized` | 超过 ceiling |
| `onset_absent` | `confirmed_divergence_onset_day(C1, full_cohort) == none` |

tradability lag 是把「统计上能分」翻译成「分得早不早」的唯一桥梁，必须在报告结论中前置呈现。

## 8. 稳健性审计

### 8.1 bootstrap

- bootstrap_n: 1000
- random_seed: 20260617
- primary block level: `instrument`
- secondary block level: `binding_canonical_event_id`（仅 sensitivity）
- 每次 bootstrap 重算 §7.1 channel-level separation metric 与 §7.3 tiered onset。
- 对每个 channel 输出 separation metric 的 median、5%/95% CI、`probability(abs(metric) > null_band_upper AND sign(metric) == confirmed_direction)`；若该 split/K 未形成 confirmed direction，则输出方向分层概率（`winner_higher` / `winner_lower` / `undetermined`）而不是单侧 `metric > null_band_upper`。
- 若 secondary event-block 与 primary instrument-block 的 onset 方向冲突，标记 `episode_block_onset_conflict`。

#### 8.1.1 跨 split（Tier2 / Tier3）bootstrap 方案

Tier2 / Tier3 与 dual-channel confirmed onset 是**跨 split**量（依赖 train 与 robustness 联合判定），单 split bootstrap 不可复现这些字段的稳定性。重采样方案固定为：

- 每个 bootstrap 迭代 `b`，对 `train` 与 `robustness` **各自独立**做 instrument-block 重采样；两 split 使用从 `bootstrap_seed` 派生的、可复现的 per-split 子种子（例如 `derive_seed(bootstrap_seed, split_name, b)`），即同一迭代内两 split 用不同但确定的子种子，互不共享被采样的 instrument 集合。
- 在迭代 `b` 内，先在两 split 各自重采样样本上重算 §7.1 channel metric 与 §7.3.3 的 Tier1 条件，再做 §7.3.3 / §7.3.4 的跨 split 一致性判定（Tier2 方向 + 最小强度、Tier3 同 K confirmed、dual-channel 两通道同时满足），得到该迭代的 channel-level 与 dual-channel onset day。
- `validation` 不参与 Tier2/Tier3 bootstrap（仅按 §8.2 power guard 作 readout）。

#### 8.1.2 Tier3 / confirmed onset 的 bootstrap 输出

Tier3 confirmed onset 与 dual-channel confirmed onset 是「最小满足 K」型离散量，不是连续 effect size，因此**不输出单点 CI**，而输出分布型读数到 `bootstrap_separation_readout.csv`：

- `confirmed_onset_hit_rate`：bootstrap 迭代中 `confirmed_divergence_onset_day != none` 的比例（dual-channel Tier3，按 contrast × cohort）。
- `confirmed_onset_day_distribution`：命中迭代中 confirmed onset day 的分布（至少 p25 / median / p75 与各 K 的命中频次）。
- `tier2_onset_hit_rate` 与 `tier2_onset_day_distribution`：对 Tier2 同样输出。
- `channel_confirmed_onset_hit_rate`：分 channel 的 Tier3 命中率（用于区分是哪个 channel 不稳定）。
- bootstrap-stable 的判定（§9 final status 使用）定义为：`confirmed_onset_hit_rate >= confirmed_onset_hit_rate_floor`（§8.5，默认 0.60）且 median bootstrap confirmed onset day 与 point-estimate confirmed onset day 的差 `<= onset_day_bootstrap_drift_ceiling` 个观察窗格（§8.5，默认 1）。

### 8.2 split 一致性

所有 contrast 必须在 `all` / `train` / `validation` / `robustness` 上各输出完整分离曲线：

- `train`：输出 Tier1 train-only onset，并与 robustness 联合计算 Tier2 / Tier3；primary channel 已在 §7.3 预注册为 `return_channel` + `structure_channel`，本步不做 outcome-driven feature selection。
- `robustness`：onset 稳定性 / 确认 split，与 train 联合决定 Tier2 / Tier3 与 dual-channel `confirmed_divergence_onset_day`。
- `validation`：out-of-sample readout，**带 power guard**。11A1 strict PIT 后 validation winner 极少（量级约 16 个），任何 validation onset 或冲突都极易是低功率噪声。因此：
  - 仅当 validation 的 primary contrast `C1` 满足 `class_big_winner` 与 `class_big_failure_proxy_nonwinner` 两侧均 `row_n >= validation_min_class_n`（config 预注册，默认 30）且各侧 `unique_instrument_n >= validation_min_instrument_n`（默认 20）时，才允许写 `validation_onset_conflict`。
  - 否则 validation 标 `validation_low_power`，validation onset 只作 readout，不得写 conflict，也不得据此修改 train/robustness 的 onset 结论或 final status。
  - `validation_low_power` 不是负面结论，但报告不得把 validation 的方向当作独立证据。
- `all`：仅展示，不作判定依据。

必须输出 `split_onset_consistency.csv`：`contrast_id`、`cohort`、`channel_id`、`split`、`channel_tier1_train_onset_day`、`channel_tier2_stability_adjusted_onset_day`、`channel_tier3_confirmed_onset_day`、`dual_channel_tier1_train_onset_day`、`dual_channel_tier2_stability_adjusted_onset_day`、`dual_channel_tier3_confirmed_onset_day`、`separation_direction`、`onset_metric_value`、`split_class_min_row_n`、`split_power_status`、`onset_status`。

### 8.3 幸存者审计（survivorship）

必须输出 `survivorship_separation_audit.csv`，对每个 (contrast, channel_id, K, split) 对比两 cohort；至少覆盖 `return_channel` 与 `structure_channel`，secondary feature 可按相同 schema 追加：

- `channel_id`
- `survivors_only_separation_metric`
- `full_cohort_separation_metric`
- `survivors_only_eligible_n`
- `full_cohort_eligible_n`
- `pre_K_path_unavailable_dropout_n`（survivors-only 相对 full-cohort 因 t0+K 前退市 / 停牌 / qfq 缺 bar 而少掉的样本；fast-fail touch 不计入 dropout）
- `pre_K_path_unavailable_dropout_rate`
- `survivorship_strength_gap = abs(survivors_only_separation_metric) - abs(full_cohort_separation_metric)`
- `survivorship_direction_status`：`same_direction` / `direction_flip` / `undetermined`
- `delist_haircut`
- `delist_haircut_sensitivity_status`：`primary` / `endpoint_check` / `sensitivity_conflict`
- `survivorship_flag`：
  - 若 `survivorship_direction_status == same_direction` 且 `survivorship_strength_gap > survivorship_gap_ceiling`（默认 0.10 in effect-size 单位），标 `survivorship_induced_separation`；
  - 若 `survivorship_direction_status == direction_flip`，标 `survivorship_direction_flip`；
  - 两者均不得进入 `separation_detected_tradable`。

### 8.4 multiple-comparison audit

11A2 在 feature × K × contrast 上做多次比较，必须显式审计。输出 `multiple_comparison_audit.csv`：

- `total_tested_cells`（feature × K × contrast × split）
- `significant_cells_n`
- `null_simulation_n`（>= 500，seed `20260617`）
- `null_expected_significant_cells_n`
- `null_significant_cells_p95`
- `actual_exceeds_null_p95_flag`
- `multiple_comparison_status`

null simulation：在每个 `split + event_year_quarter + source_family_id` cell 内随机置换 class 标签，保持各 class 的 marginal count 不变，重算 §7.1 metric。该审计用于解释「观察到的分离是否强于同分布随机标签」，不得用于事后增删 feature/contrast。

### 8.5 Config Contract（运行前冻结，入 manifest hash）

所有阈值与参数必须在 `configs/config_11a2_post_t0_archetype_path_divergence_diagnostic.yaml` 预注册，运行前冻结，并在 manifest 中记录 `config_sha256`；否则「运行前冻结」不可验证。预注册项至少包含：

| config key | 默认 | 用途 |
| --- | --- | --- |
| `observation_windows_K` | `[1, 3, 5, 10, 15, 20]` | 早期观察窗口 |
| `primary_onset_channels` | `["return_channel", "structure_channel"]` | dual-channel primary onset gate；不得运行后增删 |
| `onset_threshold` | `0.147` | `abs(channel_separation_metric)` onset 阈值，适用于 `return_channel` 与 `structure_channel`；Cliff's delta small-effect 下界 |
| `null_band_upper` | `0.05` | onset CI 距离 0 最近边界必须超过的 null 带，即 `min(abs(ci_low), abs(ci_high)) > 0.05`；Cliff's delta 不可忽略区间边界 |
| `tier2_directional_prob_floor` | `0.60` | Tier2 中 robustness 方向 bootstrap probability 的最低要求 |
| `confirmed_onset_hit_rate_floor` | `0.60` | §8.1.2 dual-channel Tier3 confirmed onset 的 bootstrap 命中率下限（bootstrap-stable 判定） |
| `onset_day_bootstrap_drift_ceiling` | `1` | §8.1.2 bootstrap median confirmed onset day 与 point estimate 的最大偏差（观察窗格数） |
| `dual_channel_collinearity_corr_ceiling` | `0.85` | §7.3.1a 两通道 weighted Spearman 秩相关上限，超过标 collinear |
| `dual_channel_direction_agreement_ceiling` | `0.95` | §7.3.1a 两通道方向一致率上限，超过标 collinear |
| `ep8a_structural_drawdown_pct_levels` | `[0.08, 0.10]` | EP8A price-action-only structural drawdown stress-test 阈值；不得读取 label barrier |
| `survivorship_gap_ceiling` | `0.10` | survivors-only 与 full-cohort effect-size 差上限 |
| `delist_haircut` | `1.0` | final status primary 口径的退市填充 haircut |
| `delist_haircut_sensitivity_values` | `[1.0, 0.0]` | survivorship sensitivity 端点；若 `0.0` 推翻 tradable 结论则 ceiling 到 statistics_incomplete |
| `tradability_realized_fraction_ceiling` | `0.50` | tradable vs late 门槛 |
| `mfe_basis_rel_diff_ceiling` | `0.05` | MFE basis 对账允许偏差 |
| `validation_min_class_n` | `30` | validation power guard 最小单侧 row_n |
| `validation_min_instrument_n` | `20` | validation power guard 最小单侧 unique_instrument_n |
| `contrast_min_class_n` | `60` | §5.3 contrast underpowered 门槛 |
| `contrast_min_instrument_n` | `30` | §5.3 contrast underpowered 门槛 |
| `eligible_row_n_floor_ratio` | `0.70` | §9.2 qfq 早期路径最低 eligible 比 |
| `class_unresolved_ceiling` | `0.30` | §9.2 unresolved 占比上限 |
| `denominator_drift_ceiling` | `0.005` | 与 11A1 scope drift 上限 |
| `anchor_recon_fail_ceiling` | `0.005` | §6.2 锚点对账失败率上限 |
| `mfe_basis_mismatch_ceiling` | `0.20` | §9.2 winner 中 basis mismatch 占比上限 |
| `touch_pos_offset_unresolved_ceiling` | `0.005` | §6.4 touch_pos 坐标偏移不可解析率上限 |
| `bootstrap_n` | `1000` | block bootstrap 次数 |
| `bootstrap_seed` | `20260617` | bootstrap seed |
| `null_simulation_n` | `500` | multiple-comparison null 次数 |
| `null_simulation_seed` | `20260617` | null simulation seed |

任何 config 项缺失，或与预注册默认不一致但未在 manifest 记录时，最终状态不得高于 `11A2_post_t0_archetype_path_divergence_statistics_incomplete`。

## 9. Diagnostic status 分类

11A2 不授权任何东西，最终 `diagnostic_summary.csv` 给出唯一 `final_status`，是描述性结论而非 pass/fail。final status 只能由 **`C1` + full-cohort + dual-channel Tier3 `confirmed_divergence_onset_day`** 决定：

| status | 条件 |
| --- | --- |
| `11A2_post_t0_archetype_path_divergence_separation_detected_tradable` | scope/对账/horizon/power 完整；primary contrast `C1` 的 full-cohort dual-channel Tier3 `confirmed_divergence_onset_day != none` 且 bootstrap-stable（§8.1.2：`confirmed_onset_hit_rate >= confirmed_onset_hit_rate_floor` 且 onset day drift `<= onset_day_bootstrap_drift_ceiling`，`return_channel` 与 `structure_channel` 均通过 train/robustness confirmed，且各 channel 方向稳定）；不存在 `return_only_pseudo_separability_risk`；不被 `survivorship_induced_separation` / `survivorship_direction_flip` 推翻；无 `delist_haircut_sensitivity_conflict`；且在该 full-cohort K* 上 `winner_realized_fraction_status == tradable_window_open`。`dual_channel_collinearity_flag == dual_channel_collinear_readout` 不阻断该状态，但报告必须按 §7.3.1a 前置标注「双通道确认接近 corroboration-by-echo」 |
| `11A2_post_t0_archetype_path_divergence_separation_detected_late` | 同上但 `winner_realized_fraction_status == late_most_move_realized`，即分离出现时收益已大部分兑现 |
| `11A2_post_t0_archetype_path_divergence_separation_survivorship_only` | survivors-only 存在 dual-channel Tier3 confirmed onset，但 full-cohort 口径塌缩（`survivorship_induced_separation` 或 `survivorship_direction_flip`） |
| `11A2_post_t0_archetype_path_divergence_separation_absent` | 统计完整，但 `C1` full-cohort 无 bootstrap-stable dual-channel Tier3 `confirmed_divergence_onset_day`；若 Tier1/Tier2 存在，报告必须表述为 `weak_or_unconfirmed_structure`，不得写成“完全无结构” |
| `11A2_post_t0_archetype_path_divergence_statistics_incomplete` | 输入可读，但 scope 对账、horizon、survivorship、锚点/basis 或 power 审计不完整，无法定性 |
| `11A2_post_t0_archetype_path_divergence_input_blocked` | global input gates 失败 |

### 9.1 global input gates（任一失败 -> input_blocked）

- 主输入文件缺失（10A / 09B / 08 / qfq / PIT universe / 11A1 scope 审计表）。
- evaluated denominator 为空。
- `risk_on ∩ PIT-valid` 重建与 11A1 无法对账（无任何 split 可比）。
- 所有 contrast 在 train 与 robustness 均 `contrast_underpowered`。

### 9.2 不得 input_blocked、但 ceiling 到 statistics_incomplete

- 与 11A1 denominator drift `> 0.5%`。
- primary contrast `C1` 在 train 或 robustness 任一 split 任一侧 `contrast_underpowered`；由于 final status 只能由 C1 决定，此时不得落入 `separation_absent`，必须 ceiling 到 `statistics_incomplete`。
- horizon 完整性导致 `class_unresolved` 占比过高（config 阈值，默认 `> 0.30`）。
- survivorship 两 cohort 任一不可计算。
- qfq 早期路径缺失率过高（config 阈值，默认任一 K 的 `eligible_row_n / pit_valid_evaluated_row_n < 0.70`）。
- §6.2 价格锚点对账失败率 `> 0.5%`（`price_anchor_reconciliation.csv` 的 `anchor_status` 不为 ok）。
- §7.4 `mfe_basis_reconciliation.csv` 中 `mfe_basis_mismatch` 比例过高（config 阈值，默认 winner 样本中 `> 0.20`），导致 tradability status 不可靠。
- §6.4 fast-fail `touch_pos` 坐标偏移不可解析率超阈（`touch_pos_coordinate_policy.csv` 的 `coordinate_status` 不为 ok）。
- `delist_haircut_sensitivity_conflict`：`delist_haircut = 0` 端点推翻 primary `delist_haircut = 1.0` 口径下的 `separation_detected_tradable`。

### 9.3 预注册否定结论

- 若 `separation_absent`：预注册结论为「t0 之后的早期路径在当前 `risk_on ∩ PIT-valid` 数据下没有形成 dual-channel Tier3 稳健分离，trajectory routing 方向在此数据上不成立，回到单层 rejector / readout-only」。若 Tier1/Tier2 有读数，必须解释为 `weak_or_unconfirmed_structure` / `statistical_instability`，不得事后放宽阈值救活。
- 若 `separation_detected_late` 或 `survivorship_only`：预注册结论为「分离存在但不可交易 / 由幸存者偏差造成，不构成 routing 依据」，需在 11C 之前另行论证可成交性，11A2 本身不授权 routing。

## 10. 输出文件

### 10.1 publishable tables

输出目录：

```text
outputs/publishable/tables/11A2_post_t0_archetype_path_divergence_diagnostic/
```

必须生成：

- `input_artifact_audit.csv`
- `scope_reconciliation_vs_11a1.csv`
- `denominator_contract_audit.csv`
- `price_anchor_reconciliation.csv`
- `outcome_class_count_audit.csv`
- `early_path_feature_registry.csv`
- `early_path_feature_coverage_audit.csv`
- `full_cohort_fill_audit.csv`
- `touch_pos_coordinate_policy.csv`
- `label_overlap_tautology_audit.csv`
- `separation_curve_readout.csv`（contrast × feature × K × split × cohort，含 `separation_direction`）
- `multivariate_separability_readout.csv`
- `divergence_onset_readout.csv`（含 channel-level Tier1/Tier2/Tier3、dual-channel Tier1/Tier2/Tier3、`confirmed_divergence_onset_day`、§7.3.1a 的 `channel_rank_corr` / `channel_direction_agreement_rate` / `dual_channel_collinearity_flag`，分 cohort）
- `mfe_basis_reconciliation.csv`
- `tradability_lag_readout.csv`
- `split_onset_consistency.csv`
- `survivorship_separation_audit.csv`
- `bootstrap_separation_readout.csv`（含 §8.1.2 的 `confirmed_onset_hit_rate` / `confirmed_onset_day_distribution` / `tier2_onset_hit_rate` / `channel_confirmed_onset_hit_rate`）
- `multiple_comparison_audit.csv`
- `diagnostic_summary.csv`

### 10.2 local cache

输出目录：

```text
outputs/local_cache/11A2_post_t0_archetype_path_divergence_diagnostic/
```

允许生成（只能包含 strict PIT 后的 `risk_on ∩ PIT-valid` evaluated rows）：

- `early_path_feature_matrix.parquet`
- `bootstrap_samples.parquet`

manifest 必须记录每个 cache 的 path、sha256、row_count、schema。

### 10.3 report 与 manifest

必须生成：

- `outputs/publishable/reports/11A2_post_t0_archetype_path_divergence_diagnostic_report.md`
- `outputs/publishable/manifest_11A2_post_t0_archetype_path_divergence_diagnostic.json`

报告必须包含：

1. 数据来源、与 11A1 的 scope 对账结果。
2. evaluated denominator row count 与三类主 outcome class（`class_big_winner` / `class_big_failure_proxy_nonwinner` / `class_neutral_chop`）及两个子划分计数（分 split）。
3. 价格锚点 policy 与 `price_anchor_reconciliation` 结果。
4. 每个 contrast 的分离曲线随 K 演化（all/train/validation/robustness 四 split，validation 需标 power guard 状态）。
5. `confirmed_divergence_onset_day`（C1 + full-cohort + dual-channel Tier3）、`return_channel` / `structure_channel` 各自 Tier1/Tier2/Tier3、`separation_direction`、两通道 `(return_direction, structure_direction)` 方向组合、§7.3.1a 的 `channel_rank_corr` / `channel_direction_agreement_rate` / `dual_channel_collinearity_flag`（高共线时显式标注「corroboration vs echo」），与 tradability lag（前置呈现，分母为 `mfe_120_recomputed`）。
6. survivorship 两 cohort 对比、full-cohort fill_reason 分布、`delist_haircut = 1.0 / 0.0` sensitivity 与 `survivorship_flag`。
7. `EP8A` price-action-only structural stress-test 与 `EP8B` label-overlap tautology audit（分离中有多少其实是 fast_fail 标签）。
8. bootstrap 解释，含 §8.1.2 dual-channel Tier3 `confirmed_onset_hit_rate` / onset day 分布与 bootstrap-stable 判定，以及 multiple-comparison 解释。
9. `final_status` 与 §9.3 预注册结论。
10. 明确边界声明：11A2 仅诊断，不授权 routing/entry/exit，不 claim 策略 EV。

## 11. 验证要求

### 11.1 单元测试

`tests/test_post_t0_archetype_path_divergence_diagnostic.py` 至少覆盖：

- evaluated denominator 重建与 11A1 scope 对账（drift 阈值触发 statistics_incomplete）。
- `observation_windows_K == [1, 3, 5, 10, 15, 20]`，且所有 early-path / onset / coverage 输出均包含 K=15。
- outcome class 互斥划分：`class_big_failure_proxy_nonwinner == winner_120=false AND (fast_fail_10 OR false_repair_20)`，与 11A1 `big_failure_proxy` 口径一致；`subclass_fast_fail` 与 `subclass_false_repair_only` 互斥且并集等于父类。
- primary contrast `C1` 负类口径等于 11A1 `big_failure_proxy` 非 winner 并集，不被窄化为 fast_fail-only。
- horizon 完整性 -> `class_unresolved`。
- 价格锚点：收益型量以 `entry_anchor_price`（t0+1 开盘）为分母，结构型量以 `event_t0_close` 为参考；`price_anchor_reconciliation` 与 10A/11A1 executable anchor（`event_window_anchor_date` / `event_window_anchor_pos`，09A `trade_time` cross-check）对账，失败率超阈值触发 statistics_incomplete。
- 早期路径特征只用 `(t0, t0+K]` 窗口，不引用窗口外未来 bar。
- survivors-only 与 full-cohort 两 cohort 的 eligible 计数与 §6.4 fill contract（delist/suspend/complete_path 优先级与 fill_reason），并验证 post-t0 ST 不触发 fill / exclusion / ceiling。
- `EP8A` 与 `EP8B` 拆分：`EP8A` 只能用 qfq price path 与预注册 drawdown 阈值重算，不读取 09A/10A `selected_fast_fail_*` 字段；`EP8B` 被排除在 onset 主曲线与 multivariate separability 之外，仅进入 `label_overlap_tautology_audit`。
- `ep_mfe/ep_mae` 不进入 onset 主曲线，只进入 tradability lag。
- divergence onset 使用预注册 dual-channel：`return_channel = EP1.ep_ret_t0_to_K` 的 Cliff's delta，`structure_channel = EP2.ep_max_drawdown_to_K` 的 Cliff's delta；不做跨特征 max 选择。
- onset 判定使用 `abs(channel_separation_metric)` 并输出每个 channel 的 `separation_direction`；反向分离（winner_lower）不被误判为 absent。
- Tier1/Tier2/Tier3 onset 分离：Tier1 为 train-only，Tier2 为 train 显著 + robustness 方向/最小强度支持，Tier3 为 train 与 robustness 同一 K 严格确认。
- dual-channel confirmed onset：final status 只用 `C1 + full-cohort + dual_channel_tier3_confirmed_onset_day`；若 `return_channel` Tier3 confirmed 但 `structure_channel` 未达 Tier2，必须标 `return_only_pseudo_separability_risk` 且不得进入任何 `separation_detected_*` 状态。
- 若 return channel 最早 K=5、structure channel 最早 K=10，且 return channel 在 K=10 仍满足 Tier3 confirmed 条件、structure channel 在 K=10 首次满足 Tier3 confirmed 条件，则 dual-channel confirmed onset 可为 K=10。
- dual-channel collinearity readout：输出 `channel_rank_corr` 与 `channel_direction_agreement_rate`，超过 §8.5 阈值时标 `dual_channel_collinear_readout`；该 flag 不阻断 final status，但报告必须前置标注 corroboration-vs-echo。
- 跨 split bootstrap：Tier2/Tier3 每次迭代对 train 与 robustness 各自独立 instrument-block 重采样（per-split 派生子种子），再做跨 split 一致性判定；Tier3 输出 `confirmed_onset_hit_rate` / onset day 分布而非单点 CI；bootstrap-stable 判定使用 `confirmed_onset_hit_rate_floor` 与 `onset_day_bootstrap_drift_ceiling`。
- tradability lag 以 full-cohort confirmed K* 计算；survivors-only K* 不决定 final status。
- tradability lag basis 对账：分母用 `mfe_120_recomputed`，`mfe_basis_mismatch` 行被排除出 tradability status；`ep_ret/forward_return_120d` 比值标 `secondary_basis_unchecked` 不进 status。
- fast-fail `touch_pos` 坐标转换仅用于 EP8B / label-overlap audit：先转 session date 再判 `<= t0+K`，输出 `touch_pos_coordinate_policy`，偏移不可解析超阈触发 statistics_incomplete；并验证 `selected_fast_fail_*` 不得改写 primary full-cohort price path 或进入 final status。
- tradability lag 状态分类（tradable_window_open / late_most_move_realized / onset_absent）。
- survivorship_flag 触发逻辑：基于绝对分离强度差与方向一致性，覆盖 `survivorship_induced_separation` / `survivorship_direction_flip`，并验证 `delist_haircut` 两端点冲突会 ceiling 到 statistics_incomplete。
- validation power guard：样本不足时标 `validation_low_power`，不得写 `validation_onset_conflict`。
- config contract：所有 §8.5 阈值入 manifest `config_sha256`；`onset_threshold == 0.147`、`null_band_upper == 0.05`；缺失或未记录时 ceiling 到 statistics_incomplete。
- multiple-comparison null simulation 输出。
- 四 split 全部产出分离曲线。
- final status precedence（含 input_blocked / statistics_incomplete / 三种 detected / absent）。

### 11.2 运行验证

实现后至少运行：

```bash
uv run python -m pytest tests/test_post_t0_archetype_path_divergence_diagnostic.py
uv run python src/run_11a2_post_t0_archetype_path_divergence_diagnostic.py --config configs/config_11a2_post_t0_archetype_path_divergence_diagnostic.yaml
```

若无 `uv` 环境，允许使用项目既有 Python runner，但必须在 report 中记录实际命令。

### 11.3 artifact validation

- publishable CSV 均非空，除非 final_status 是 input_blocked。
- manifest 中所有 publishable artifact sha256 可复算。
- `diagnostic_summary.csv` 只有一个 final_status。
- report 引用的核心数值能在 CSV 中定位。

## 12. 报告措辞约束

报告不得使用以下措辞：

- “早期路径特征是 entry 信号”
- “11A2 证明 routing 有效”
- “可以据此 override 10C”
- “MFE 收益”

允许使用：

- “early-path 分离 / divergence onset”
- “tradability lag”
- “survivorship-induced separation”
- “diagnostic-only readout”
- “separation 存在但不可交易 / 由幸存者偏差造成”

## 13. 后续依赖

11A2 的唯一合法下游用途：

- 若 `separation_detected_tradable`：进入 11C 的 two-stage policy 设计，把「t0 小仓试探 → t0+K* 再决策」作为**待验证**结构，由 11C 计算带成本、可成交性与组合容量的策略 EV。11A2 本身不给 EV。
- 若 `separation_detected_late` / `survivorship_only`：不进入 routing；如继续，必须先单独论证「在收益走完之前可成交地捕捉分离」，否则回到单层 rejector / readout-only。
- 若 `separation_absent`：停止 trajectory routing 方向，回到单层 rejector / readout-only，不放宽阈值。
- 若 `statistics_incomplete` / `input_blocked`：先补数据完整性 / scope 对账，不做策略化解释。

> 最关键的一句话：**11A1 证明 t0 处 winner 与 failure 纠缠；11A2 只回答这种纠缠是否、以及多早在 t0 之后解耦，并且只有当「解耦发生在收益兑现之前、且不是幸存者偏差」时，trajectory routing 才值得在 11C 付费验证。**
