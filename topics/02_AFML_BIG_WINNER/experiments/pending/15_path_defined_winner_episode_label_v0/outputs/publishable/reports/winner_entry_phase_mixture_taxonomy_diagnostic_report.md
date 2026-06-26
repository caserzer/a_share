# 15C Winner Entry Phase and Mixture Taxonomy Diagnostic

## 1. 单行裁决

`decision_state = 15C_entry_phase_reduces_heterogeneity_but_coverage_insufficient`；`next_allowed_requirement = none`。

15C 的结论是：entry-phase 切分确实揭示了一部分 winner path 的结构，尤其是 outcome-relative phase；但 PIT-observable phase 没有显著优于随机切分，且 single-subtype coverage 太低、mixed share 太高，所以不能进入 15D separability。无论本报告如何解读，当前实验仍不授权 label deployment、signal search、entry policy、model training 或 separability search。

| item | value |
|---|---:|
| selected_threshold_id | `up50pct` |
| eligible_train_phase_subgroup_n_pit | 1340 |
| eligible_train_phase_subgroup_n_outcome | 1081 |
| pit_scheme_supported_for_15d | false |
| outcome_scheme_descriptive_supported | false |
| next_allowed_requirement | `none` |

## 2. 输入、lineage 与 adapter 证据

15C 没有从报告文本或图表反推逐行标签。所有逐行 anchor path type 来自 15B anchor-level taxonomy，并重新用 15B frozen deterministic rule 做复现检查。

| artifact | rows | gate |
|---|---:|---|
| 15B decision | 1 | pass |
| 15B path-shape rule audit | 30 | pass |
| 15B taxonomy assignment panel | 419998 | pass |
| 15B winner episode cluster membership | 417131 | pass |
| 15B representative audit | 2867 | pass |
| 15B split overlap audit | 2867 | pass |
| 15B upstream lineage audit | 6 | pass |
| 15B price path completeness audit | 1449 | pass |
| 13A native universe panel | 431239 | pass |

Adapter gate 的关键证据：

| item | value |
|---|---:|
| adapter_source_priority | 1 |
| adapter_row_count | 417131 |
| adapter_duplicate_source_row_key_n | 0 |
| adapter_required_columns_present | true |
| adapter_anchor_path_type_reproducible | true |
| adapter_cluster_interval_backfilled | true |
| adapter_status | pass |
| rebuild_status | not_required_pass |

这意味着本次 15C 的 path-quality 来源是逐行 anchor segment 上的 15B `path_type`，不是 episode medoid，也不是 report readout。`taxonomy_assignment_panel` 成功通过复现检查，因此无需 priority 2 feature-panel fallback 或 priority 3 raw-qfq rebuild。

## 3. 方法边界

15C 把 winner 拆成四层：outcome、threshold、entry phase、path-quality。顺序不能反过来：先确定 entry phase，再引用 anchor 自己 segment 上的 path-quality，最后做 cluster-level mixture。这样做的目的不是找入场信号，而是验证 “winner 这个 label 是否需要按 entry phase 拆成更细的 label primitive”。

Primary support decision 只使用 `threshold_id = up50pct`、`split = train`、`anchor_weighted` 指标。Validation 和 robustness 只做 frozen-rule confirmation，不参与 quantile fit、threshold selection 或 phase scheme selection。`up100pct` / `up150pct` 是 sensitivity readout，不能改变 primary decision。

## 4. Entry Phase 规则

PIT-observable phase 使用 t0 可见的 13A morphology 字段，并在 up50 train eligible anchor 上冻结 quantile。fit population 为 56987，missing feature count 为 0。

| rule | quantile |
|---|---:|
| q_ret60d_30 | -0.004994 |
| q_ret60d_50 | 0.101266 |
| q_ret60d_70 | 0.229017 |
| q_distance_to_60d_high_70 | -0.054945 |
| q_distance_to_60d_high_90 | -0.021546 |
| q_distance_to_20d_low_30 | 0.061969 |
| q_distance_to_20d_low_70 | 0.163508 |
| q_trend_ma_20_60_spread_50 | 0.034567 |

Outcome-relative phase 使用 `cluster_progress = (entry_pos - cluster_start_pos) / max(cluster_end_pos - cluster_start_pos, 1)`。它明显更贴近 realized path 的位置结构，但它使用未来 cluster interval，因此永远只能是 diagnostic descriptor，不能升级为 t0 feature。

## 5. Primary Up50 Train 结果

### 5.1 Representative disagreement

| scheme | baseline disagreement | phased disagreement | reduction | baseline entropy median | phased entropy median |
|---|---:|---:|---:|---:|---:|
| pit | 0.9384 | 0.8444 | 0.0940 | 0.6990 | 0.6970 |
| outcome | 0.9334 | 0.7445 | 0.1889 | 0.7219 | 0.6257 |

PIT phase 的 disagreement reduction 只有 0.0940，低于 support gate 所需的 0.15；phased disagreement 仍高达 0.8444，远高于 support gate 的 0.50 上限。Outcome phase 的 reduction 达到 0.1889，说明同一段 winner cluster 内 “从行情哪个阶段进入” 确实会影响 path-type 混合；但 outcome phase 不能作为 t0 feature。

### 5.2 Random baseline

| scheme | phase dominant | random dominant | uplift | phase entropy | random entropy | entropy reduction | real |
|---|---:|---:|---:|---:|---:|---:|---|
| pit | 0.6573 | 0.6125 | 0.0448 | 0.6436 | 0.6888 | 0.0451 | false |
| outcome | 0.7272 | 0.6139 | 0.1133 | 0.5765 | 0.6809 | 0.1044 | true |

PIT phase 没有通过 “优于同大小随机切分” 的真实性判据：dominant uplift 和 entropy reduction 都只有约 0.045，明显低于 0.10。也就是说，PIT morphology 当前的 phase 切分带来的纯度提升，大部分不能排除 “子组变小后自然更纯” 的机械效应。

Outcome phase 通过了真实性判据，dominant uplift = 0.1133，entropy reduction = 0.1044。这是一个重要 finding：winner path 的异质性有真实的 entry-zone 结构，只是这个结构主要由事后位置解释，而不是当前 PIT 规则捕获。

### 5.3 Coverage

| scheme | baseline unresolved | single subtype coverage | mixed share | sparse share | capture-friendly share | coverage improvement |
|---|---:|---:|---:|---:|---:|---:|
| pit | 0.3962 | 0.1188 | 0.8223 | 0.0589 | 0.0454 | -0.4850 |
| outcome | 0.3962 | 0.2851 | 0.6799 | 0.0349 | 0.1197 | -0.3187 |

Coverage 是最强的否定证据。PIT phase 切分后，只有 11.88% 的 up50 train anchor 能进入 single subtype，82.23% 仍是 mixed。Capture-friendly subtype 只有 4.54%。Outcome phase 虽然更好，但 single-subtype coverage 也只有 28.51%，mixed share 仍有 67.99%。两者都远低于 support gate：single coverage >= 0.50、mixed share <= 0.45。

## 6. PIT Phase 内部结构

up50 train 的 PIT phase 分解显示，最大的问题不是 sparse，而是 t0 morphology 规则无法把大多数 anchor 分成可用 subtype。

| PIT phase | anchors | dominant residual / subtype | share in phase | interpretation |
|---|---:|---|---:|---|
| undetermined_pit | 22041 | mixed_episode_winner | 0.9701 | 最大的 PIT bucket，几乎全是 mixed；它不能计入 single coverage |
| mid_trend_pit | 13305 | mixed_episode_winner | 0.7737 | 中段趋势状态仍无法稳定指向某个 path type |
| late_chase_pit | 9907 | mixed_episode_winner | 0.7644 | 追高并不等于单一路径；late_rescue / stair_step / smooth 混在一起 |
| early_base_pit | 8368 | mixed_episode_winner | 0.6656 | base 状态有一些 late_rescue，但纯度仍不足 |
| breakout_pit | 3366 | mixed_episode_winner | 0.6061 | breakout 更稀疏，sparse share 达 0.2377 |

关键 insight：当前 PIT phase 的主轴是 t0 截面状态，但 realized winner path quality 更多由后续路径中的回撤、跳涨集中度、趋势持续性和阶段位置共同决定。PIT phase 可以解释一部分状态差异，但还没有形成可部署的 label primitive。

## 7. Outcome Phase 内部结构

Outcome-relative phase 更能解释 path-type mixture，但它是未来可见 descriptor。

| outcome phase | anchors | dominant residual / subtype | share in phase | secondary subtype signal |
|---|---:|---|---:|---|
| mid_cluster_entry | 20538 | mixed_episode_winner | 0.7683 | stair_step 0.0958，late_rescue 0.0892 |
| early_cluster_entry | 17763 | mixed_episode_winner | 0.4861 | late_rescue 0.3732，是最清晰的 outcome-zone signal |
| breakout_cluster_entry | 11065 | mixed_episode_winner | 0.8091 | stair_step 0.0766，smooth 0.0723 |
| late_cluster_entry | 7621 | mixed_episode_winner | 0.7061 | smooth 0.1849，jump 0.0530 |

这里的结构有经济含义：早进 cluster 的 anchor 更容易经历 late_rescue 型路径；晚进 cluster 的 anchor 更容易看到 smooth 或 jump-like 的最后阶段。但这种分解使用了 cluster interval，因此不能直接变成 entry feature。它只能说明 label-form 层面确实存在 “同一 winner cluster 内不同 entry zone 体验不同”。

## 8. Split Confirmation

### 8.1 Random baseline 与 disagreement across splits

| split | scheme | real | uplift | entropy reduction | disagreement phased | disagreement reduction |
|---|---|---:|---:|---:|---:|---:|
| train | pit | false | 0.0448 | 0.0451 | 0.8444 | 0.0940 |
| validation | pit | false | 0.0134 | 0.0064 | 0.5096 | 0.1451 |
| robustness | pit | false | 0.0570 | 0.0544 | 0.8192 | 0.1320 |
| train | outcome | true | 0.1133 | 0.1044 | 0.7445 | 0.1889 |
| validation | outcome | false | 0.0748 | 0.0796 | 0.3974 | 0.2249 |
| robustness | outcome | true | 0.1135 | 0.1452 | 0.6639 | 0.2823 |

PIT scheme 在三个 split 都没有通过 random baseline 判据。Outcome scheme 在 train 和 robustness 通过，但 validation 不通过，而且 validation phase subgroup 数只有 36，样本较小。因此 outcome 结构更像 “强 descriptive clue”，不是可直接推进 separability 的稳定 feature。

### 8.2 Coverage across splits

| split | scheme | single coverage | mixed share | sparse share | capture-friendly share |
|---|---|---:|---:|---:|---:|
| train | pit | 0.1188 | 0.8223 | 0.0589 | 0.0454 |
| validation | pit | 0.2347 | 0.5484 | 0.2169 | 0.0347 |
| robustness | pit | 0.0880 | 0.8234 | 0.0886 | 0.0695 |
| train | outcome | 0.2851 | 0.6799 | 0.0349 | 0.1197 |
| validation | outcome | 0.4516 | 0.4085 | 0.1399 | 0.0704 |
| robustness | outcome | 0.2259 | 0.7112 | 0.0629 | 0.1709 |

Validation outcome 看起来 coverage 接近 gate，但 train 和 robustness 没有同步确认。AFML 上不能把 validation 的偶然改善拿来反选 phase scheme；15C 的冻结规则要求 train primary、validation/robustness no-fit confirmation。

## 9. Threshold Sensitivity

不同 threshold 的 mixture composition 不可外推。up50 的 PIT/outcome 都以 mixed 为主；threshold 越高，outcome phase 下 stair_step 的占比明显上升。

| threshold | scheme | top subtype | share | second subtype | share |
|---|---|---|---:|---|---:|
| up50pct | pit | mixed_episode_winner | 0.8183 | sparse_phase_subgroup | 0.0662 |
| up50pct | outcome | mixed_episode_winner | 0.6808 | late_rescue_winner | 0.1271 |
| up100pct | pit | mixed_episode_winner | 0.6512 | stair_step_winner | 0.1911 |
| up100pct | outcome | mixed_episode_winner | 0.3981 | stair_step_winner | 0.3533 |
| up150pct | pit | mixed_episode_winner | 0.5655 | stair_step_winner | 0.2776 |
| up150pct | outcome | stair_step_winner | 0.4615 | mixed_episode_winner | 0.3179 |

Insight：高阈值 winner 的路径更偏 stair-step，尤其在 outcome phase 下更明显。这不代表 up50 可以用 up150 的 subtype 结构训练；它反而说明 threshold layer 必须冻结分开。up50 的 primary support 失败不能被 up100/up150 的 descriptive pattern 覆盖。

## 10. Up50 Split 内 Subtype 结构

| split | scheme | top subtype | share | important secondary readout |
|---|---|---:|---:|---|
| train | pit | mixed_episode_winner | 0.8223 | late_rescue 0.0678，sparse 0.0589 |
| validation | pit | mixed_episode_winner | 0.5484 | sparse 0.2169，late_rescue 0.1502 |
| robustness | pit | mixed_episode_winner | 0.8234 | sparse 0.0886，stair_step 0.0427 |
| train | outcome | mixed_episode_winner | 0.6799 | late_rescue 0.1485，stair_step 0.0682 |
| validation | outcome | mixed_episode_winner | 0.4085 | late_rescue 0.3164，sparse 0.1399 |
| robustness | outcome | mixed_episode_winner | 0.7112 | stair_step 0.1152，smooth 0.0556，jump 0.0444 |

第 81 行附近的 `robustness / outcome / jump_repricing_winner: share=0.0444, n=496` 应该这样读：它是 outcome-relative descriptor 下的 robustness split 读数，说明 late / breakout zone 的一部分 winner anchor 可能表现为 jump-like repricing；但它没有达到 material subtype 的 primary 角色，也不能作为 t0 feature。更重要的是，train outcome 的 jump share 只有 0.0146，validation outcome 为 0.0648，split 间差异较大，不能把 jump_repricing 当成稳定 candidate。

## 11. PIT vs Outcome 对比

| metric | PIT | outcome | better |
|---|---:|---:|---|
| dominant_share_uplift_vs_random | 0.0448 | 0.1133 | outcome |
| internal_entropy_reduction_vs_random | 0.0451 | 0.1044 | outcome |
| phased representative disagreement | 0.8444 | 0.7445 | outcome |
| single_subtype_coverage | 0.1188 | 0.2851 | outcome |
| mixed_share | 0.8223 | 0.6799 | outcome |

Outcome phase 在每个核心指标上都优于 PIT phase，但它的优势不能转化为 15D authorization，因为 outcome phase 用了未来 cluster interval。PIT phase 是唯一可升级为 t0 feature 的 scheme，但它没有通过 real-over-random，也没有 coverage。

## 12. Findings

1. 15B 的核心问题不是 “path shape 完全没有结构”，而是 “cluster medoid 单元太粗”。15C 进一步证明，结构确实存在，但主要被 outcome-relative entry zone 捕捉，而不是当前 PIT morphology phase 捕捉。

2. PIT-observable entry phase 当前不能作为 separability label primitive。它没有显著优于随机切分，up50 train single coverage 只有 0.1188，mixed share 高达 0.8223，material subtype count 只有 train=1、validation=1、robustness=0。

3. Outcome-relative phase 是有解释力的 descriptor。up50 train outcome 的 dominant uplift = 0.1133、entropy reduction = 0.1044，robustness 也通过 real-over-random；但它仍然 coverage 不足，且不能升级为 t0 feature。

4. 高阈值 winner 与低阈值 winner 的形态结构明显不同。up150 outcome 里 stair_step share 达 0.4615，而 up50 outcome 仍以 mixed 为主。这强化了 threshold layer 必须分开，而不是把 up150 的清晰结构外推回 up50。

5. Capture-friendly subtype 仍然太少。up50 train PIT capture-friendly share 只有 0.0454，outcome 也只有 0.1197。即使只关心 smooth / stair_step / slow_grind，目前也没有足够覆盖率支持后续 separability。

## 13. Insight

AFML 视角下，15C 给出的答案是：winner 目前仍应保持 outcome label，而不是立即拆成可交易的 path-shape subtype label。Path shape 可以作为 post-hoc diagnostic，帮助解释为什么同一个 +50% winner 体验差异很大；但 current PIT phase 还不能把这种差异转成 t0 可预测的 label primitive。

更具体地说，后续如果继续推进，不应该直接做 15D separability。更合理的方向是先重新设计 PIT-observable phase：当前 `ret_60d / distance_to_high_low / trend spread` 这组 t0 morphology 太粗，无法捕捉 “entry zone in episode” 这种事后结构。可能需要更贴近 episode onset、compression-release、volume/turnover regime、relative-to-recent-breakout timing 的 PIT features；但这已经是新的 requirement，不属于 15C 授权范围。

## 14. 最终执行边界

15C 不授权：

- label deployment；
- signal search；
- entry / exit / holding policy；
- model training；
- separability search；
- 用 outcome-relative phase 构造 t0 feature；
- 用 up100/up150 的 descriptive pattern 覆盖 up50 primary decision。

最终 next step 仍为 `none`。当前证据支持的研究判断是：entry-phase 切分能帮助解释 winner path 的异质性，但还不能把 winner label 改造成可部署的 capture-friendly taxonomy。
