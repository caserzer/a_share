# R05 Preflight 快速可行性最终报告

R05 Preflight 是低成本方向筛查，只判断 fixed primitive 是否值得进入完整 R05a 协议；本报告不批准任何可交易规则。

Final decision: `r05_preflight_stop_no_absolute_floor`

本次 validation 已通过 validator，`failed_checks=[]`，`warning_checks=[]`。workflow 层结论是：三个 canonical candidate 中没有任何一个满足 preflight pass，`candidate_pass_count=0`，`allowed_next_requirement=sleeve_allocator_direction_requirement`。

## 1. Executive Summary

R05 Preflight 的核心问题是：

```text
新的 low-overlap / non-R02 primitive 是否至少存在 validation absolute positive floor？
```

当前答案是否定的。

三类候选 primitive 的 validation 结果分别是：

| candidate_id | validation events | complete share | hold20 net mean | median | p10 | loss<=-5 | gate status |
|---|---:|---:|---:|---:|---:|---:|---|
| `low_vol_uptrend_preflight` | 574 | 96.86% | -0.72% | -1.36% | -9.46% | 26.26% | `preflight_fail_no_absolute_floor` |
| `base_breakout_vcp_preflight` | 73 | 95.89% | +1.00% | -1.47% | -7.61% | 20.00% | `preflight_fail_insufficient_sample` |
| `cross_sectional_low_beta_low_vol_preflight` | 810 | 96.05% | -1.52% | -1.83% | -9.24% | 27.63% | `preflight_fail_no_absolute_floor` |

这说明当前失败不是由 execution availability 造成的。三个 candidate 的 validation complete share 都高于 95%，execution audit 全部为 `passed`。主要问题是 validation split 的 after-cost return floor 不成立，尤其是两个样本充足的 candidate 都是负均值、负中位数和较深左尾。

## 2. Gate Result

| candidate_id | family | validation_events | complete_share | mean | median | p10 | status | blocking_reason |
|---|---|---:|---:|---:|---:|---:|---|---|
| `low_vol_uptrend_preflight` | low_vol_uptrend | 574 | 96.86% | -0.72% | -1.36% | -9.46% | `preflight_fail_no_absolute_floor` | `validation_absolute_floor_failed` |
| `base_breakout_vcp_preflight` | base_breakout_vcp | 73 | 95.89% | +1.00% | -1.47% | -7.61% | `preflight_fail_insufficient_sample` | `validation_event_count_below_min` |
| `cross_sectional_low_beta_low_vol_preflight` | cross_sectional_low_beta_low_vol | 810 | 96.05% | -1.52% | -1.83% | -9.24% | `preflight_fail_no_absolute_floor` | `validation_absolute_floor_failed` |

preflight pass 需要 validation event count 至少 300，complete share 至少 95%，并且 hold20 net mean > 0、median > -0.50%、p10 > -8.00%。当前没有 candidate 同时满足这些条件。

`base_breakout_vcp_preflight` 是唯一 validation mean 为正的候选，但 validation 只有 73 个事件，远低于 300 的最低样本门槛；同时 median 为 -1.47%，说明 +1.00% 的均值更可能来自少数右尾样本，而不是稳定的事件级优势。

## 3. Split Return Summary

| candidate_id | split | events | raw triggers | suppressed | complete | complete share | mean | median | p10 | loss<=-5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `low_vol_uptrend_preflight` | train | 1,116 | 13,967 | 12,851 | 1,095 | 98.12% | +0.08% | -1.02% | -9.87% | 26.48% |
| `low_vol_uptrend_preflight` | validation | 574 | 7,390 | 6,816 | 556 | 96.86% | -0.72% | -1.36% | -9.46% | 26.26% |
| `low_vol_uptrend_preflight` | robustness | 976 | 13,678 | 12,702 | 950 | 97.34% | +0.81% | +0.33% | -6.83% | 18.74% |
| `base_breakout_vcp_preflight` | train | 99 | 121 | 22 | 95 | 95.96% | +1.37% | +0.02% | -8.97% | 16.84% |
| `base_breakout_vcp_preflight` | validation | 73 | 91 | 18 | 70 | 95.89% | +1.00% | -1.47% | -7.61% | 20.00% |
| `base_breakout_vcp_preflight` | robustness | 123 | 164 | 41 | 120 | 97.56% | +1.90% | +1.06% | -8.04% | 17.50% |
| `cross_sectional_low_beta_low_vol_preflight` | train | 1,444 | 19,212 | 17,768 | 1,412 | 97.78% | +0.08% | -0.92% | -9.20% | 25.35% |
| `cross_sectional_low_beta_low_vol_preflight` | validation | 810 | 10,930 | 10,120 | 778 | 96.05% | -1.52% | -1.83% | -9.24% | 27.63% |
| `cross_sectional_low_beta_low_vol_preflight` | robustness | 1,238 | 18,052 | 16,814 | 1,198 | 96.77% | +0.88% | +0.24% | -7.03% | 17.70% |

这张表有两个重要信号：

1. `low_vol_uptrend` 和 `cross_sectional_low_beta_low_vol` 都呈现 train 接近 0、validation 转负、robustness 转正的形态。这和 R04e 中“validation split 拒绝、robustness 转好”的现象一致，支持 validation regime / exposure pressure 是关键问题，而不是单一公式实现错误。
2. `base_breakout_vcp` 在三个 split 的均值都为正，但事件数过少，validation 只有 73 个 collapse 后事件。它不能支持进入完整 R05a，因为完整协议会更严格，样本不足会放大偶然右尾的影响。

## 4. Execution Audit

| candidate_id | split | events | entry_unavailable | exit_unavailable | split_boundary | complete | complete share | status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `low_vol_uptrend_preflight` | train | 1,116 | 0 | 2 | 19 | 1,095 | 98.12% | `passed` |
| `low_vol_uptrend_preflight` | validation | 574 | 0 | 0 | 18 | 556 | 96.86% | `passed` |
| `low_vol_uptrend_preflight` | robustness | 976 | 0 | 3 | 23 | 950 | 97.34% | `passed` |
| `base_breakout_vcp_preflight` | train | 99 | 0 | 0 | 4 | 95 | 95.96% | `passed` |
| `base_breakout_vcp_preflight` | validation | 73 | 0 | 0 | 3 | 70 | 95.89% | `passed` |
| `base_breakout_vcp_preflight` | robustness | 123 | 0 | 0 | 3 | 120 | 97.56% | `passed` |
| `cross_sectional_low_beta_low_vol_preflight` | train | 1,444 | 0 | 0 | 32 | 1,412 | 97.78% | `passed` |
| `cross_sectional_low_beta_low_vol_preflight` | validation | 810 | 0 | 0 | 32 | 778 | 96.05% | `passed` |
| `cross_sectional_low_beta_low_vol_preflight` | robustness | 1,238 | 0 | 1 | 39 | 1,198 | 96.77% | `passed` |

Execution 层没有形成阻断。entry unavailable 全部为 0，exit unavailable 也很少；主要 censor 来自 split-boundary，同一 split 内的 hold20 path 被严格截断。这说明负收益不是因为无法执行或大量路径缺失导致，而是完整路径样本自身的 after-cost 表现不足。

## 5. Event Collapse Readout

三类 candidate 都存在大量连续 raw trigger，因此 event collapse 是必要的：

| candidate_id | split | raw triggers | kept events | suppressed | suppressed share |
|---|---:|---:|---:|---:|---:|
| `low_vol_uptrend_preflight` | train | 13,967 | 1,116 | 12,851 | 92.01% |
| `low_vol_uptrend_preflight` | validation | 7,390 | 574 | 6,816 | 92.23% |
| `low_vol_uptrend_preflight` | robustness | 13,678 | 976 | 12,702 | 92.86% |
| `base_breakout_vcp_preflight` | train | 121 | 99 | 22 | 18.18% |
| `base_breakout_vcp_preflight` | validation | 91 | 73 | 18 | 19.78% |
| `base_breakout_vcp_preflight` | robustness | 164 | 123 | 41 | 25.00% |
| `cross_sectional_low_beta_low_vol_preflight` | train | 19,212 | 1,444 | 17,768 | 92.48% |
| `cross_sectional_low_beta_low_vol_preflight` | validation | 10,930 | 810 | 10,120 | 92.59% |
| `cross_sectional_low_beta_low_vol_preflight` | robustness | 18,052 | 1,238 | 16,814 | 93.14% |

`low_vol_uptrend` 和 `cross_sectional_low_beta_low_vol` 本质上是状态型信号，不是稀疏事件信号。超过 92% 的 raw triggers 被 20 trading-day collapse 压掉，说明如果不做 collapse，event count 会被连续状态重复触发严重放大。当前结果已经是 collapse 后的保守口径，因此 validation 负均值更有解释力。

`base_breakout_vcp` 更像稀疏事件，suppressed share 只有约 20%，但这也导致样本不足。它的形态有观察价值，但不能单独支撑完整协议投入。

## 6. Findings

### Finding 1: 两个样本充足 candidate 都没有 validation absolute floor

`low_vol_uptrend_preflight` validation 有 574 个事件，hold20 net mean 为 -0.72%，median 为 -1.36%，p10 为 -9.46%。`cross_sectional_low_beta_low_vol_preflight` validation 有 810 个事件，hold20 net mean 为 -1.52%，median 为 -1.83%，p10 为 -9.24%。这两个 candidate 都满足样本和 execution 门槛，但不满足收益 floor。

这比“没有找到强 alpha”更严格：当前证据显示，即使只要求最小正均值，validation 也没有过。

### Finding 2: low beta / low vol 没有解决 validation 年份的长多压力

`cross_sectional_low_beta_low_vol` 原本是为了加入一个机制上不同于纯 momentum continuation 的 defensive primitive。但它在 validation 的表现比 `low_vol_uptrend` 更差：mean -1.52% vs -0.72%，loss<=-5 rate 27.63% vs 26.26%。

这说明仅靠 cross-sectional low beta / low vol 约束，并没有把 validation split 的主要风险拿掉。它可能降低波动形态，但没有把 after-cost hold20 期望转正。

### Finding 3: base breakout / VCP 是唯一有正均值的候选，但样本太少且中位数仍为负

`base_breakout_vcp` validation mean 为 +1.00%，但只有 73 个事件，低于 300 的最低样本要求；median 为 -1.47%，说明典型事件仍亏损，均值依赖少数右尾样本。

这类信号可以作为后续“稀疏事件 family”的探索线索，但不应在当前 R05a v1 中作为通过 preflight 的 standalone candidate 使用。

### Finding 4: robustness 转正不能救回 validation

三个 candidate 的 robustness mean 都为正：

| candidate_id | validation mean | robustness mean | delta |
|---|---:|---:|---:|
| `low_vol_uptrend_preflight` | -0.72% | +0.81% | +1.53% |
| `base_breakout_vcp_preflight` | +1.00% | +1.90% | +0.90% |
| `cross_sectional_low_beta_low_vol_preflight` | -1.52% | +0.88% | +2.39% |

但 EP4 lifecycle 明确 validation 是 go/no-go split，robustness 只能作为读数，不能反向改变 validation gate。这个 pattern 与 R04e 的结论相互印证：当前问题更像 split/regime 层面的长多候选池压力，而不是某个固定 primitive 在全周期稳定有效。

### Finding 5: 当前失败不是 implementation/execution failure

Validator 已通过，execution audit 全部 passed，complete share 均高于 95%。因此 final decision 的含义不是“实验没跑起来”，而是“实验按合同跑完后，没有找到值得进入完整 R05a 的 candidate”。

## 7. Insights

### Insight 1: R05a 不应继续作为默认下一步

Preflight 的目的就是避免在没有 validation floor 的 primitive 上投入完整 R05a 工程量。当前两个样本充足 candidate 都失败，第三个正均值 candidate 又样本不足。因此，按当前证据直接执行完整 R05a，大概率只会把失败边界测得更精确，而不是改变结论。

更合理的执行结论是：冻结当前 R05a full protocol，不启动完整 matched comparator / bootstrap / capacity stress / structural audit。

### Insight 2: EP4 的问题继续指向 sleeve / exposure，而不是 entry primitive

R04e 已经显示 union pool 在 validation 中无法形成组合层正期望；R05 Preflight 又显示换成新的 low-vol / low-beta / breakout primitive 后，validation floor 仍不成立。两个实验从不同角度给出相同方向：当前主要瓶颈不像是“缺一个更细的 entry formula”，而像是 validation regime 下 long-only inventory 的收益压力。

因此，`sleeve_allocator_direction_requirement` 比继续扩展 R05a primitive grid 更符合当前证据。

### Insight 3: 如果还要保留 alpha discovery，应该优先研究稀疏事件而不是状态型信号

`low_vol_uptrend` 和 `cross_sectional_low_beta_low_vol` raw trigger 中超过 92% 被 collapse，说明它们更像长期状态暴露，而不是独立 entry event。状态型暴露在 validation 年份容易继承相同 regime 压力。

`base_breakout_vcp` 虽然样本不足，但 raw-to-kept ratio 更健康，且三段均值为正。若未来继续做 alpha discovery，应优先把它作为“稀疏事件 family”的设计线索，而不是简单放宽阈值把样本堆到 300。放宽阈值可能会把它重新变成状态型或噪声型信号。

### Insight 4: 当前结果支持 stop，而不是参数再搜索

本需求明确禁止 grid search、threshold search 和 validation 后重跑。这个约束是必要的：如果在当前结果后对 `base_breakout_vcp` 放宽/收紧阈值寻找 300 个 validation 事件，容易变成 validation-mining。

后续若要继续研究，应新开需求，并把搜索空间、train-only selection、validation freeze 和 stop rule 写清楚，而不是在本 preflight 内继续调参。

## 8. Final Interpretation

R05 Preflight 已完成它的设计目标：用低成本方式验证 R05a full protocol 是否值得启动。当前结果没有找到通过 validation floor 的 candidate。

最终执行判断：

```text
final_decision = r05_preflight_stop_no_absolute_floor
candidate_pass_count = 0
allowed_next_requirement = sleeve_allocator_direction_requirement
```

这不是一个实现失败，而是一个有效的方向否决。当前证据不支持继续投入完整 R05a；更合理的下一步是把问题从 standalone alpha pool discovery 转向 sleeve allocator / exposure composition。
