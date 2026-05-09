# EP2 Requirement 02: Hazard Timing Model

Status: draft placeholder. Do not implement until `ep2/requirement_01_label_and_baseline_freeze.md` is reviewed and accepted.

This file intentionally copies the relevant discussion content only. Detailed implementation requirements will be expanded after Requirement 01 passes.

## EP2-3 Hazard timing model（条件开启）

仅当 EP2-2 gate 通过时启动。

不使用普通 binary LGBM。第一版限定为 **discrete-time three-class softmax**：每天预测 `target_first / stop_first / neither` 三类概率，输出：

```text
score_probe_day =
    P(target_before_stop_within_H)
  - lambda * P(stop_before_target_within_H)
  - mu * missed_upside_penalty
```

以 episode-level first valid day 作为主 probe 触发。

first valid day 必须有明确冲突优先级，避免模型用后段确认日"补票"：

```yaml
episode_primary_probe_day:
  search_window:
    start: launch_effective_date
    end: launch_effective_date + max_probe_window
  valid_if:
    - score_probe_day >= threshold
    - no_fast_fail_has_occurred
    - missed_gain_to_exposure <= max_missed_gain
  if_multiple: earliest_valid_day_only
  if_none: no_probe
```

如果同一天 `target_first / stop_first / neither` score 冲突，primary rule 使用 `score_probe_day` 排序，且 `P(stop_before_target_within_H)` 超过预注册风险阈值时强制判为 invalid day。`first valid day` 如果晚于 `max_probe_window` 或 `missed_gain_to_exposure` 超过阈值，则该 episode 记为 `no_probe`，不能用后段确认日补票。

明确禁止（避免 EP2-3 失控）：

- 不直接上 Cox / Fine-Gray competing-risk 模型（A 股 small-pool 下 censoring 独立性假设不成立）；
- 不做 path-to-primitive；
- 不做 leaf rule extraction；
- 不做行业专用 LGBM；
- 不做 20–40 个 CSV gate；
- 不做复杂 FDR / null family（保留 same-pool random / fixed-delay null 即可）；
- 不做 full strategy annual return（无 holding / exit 时无意义）。

## 三档判定与停止 / 重写规则

允许进入 EP2-4 当且仅当：

1. exposure / probe signal 相对 same-pool random exposure 有正 after-cost lift；
2. 相对 `buy_all_on_launch_hold_to_H` 与 `buy_all_on_launch_with_same_fast_fail` 不明显牺牲 big-winner coverage；
3. median `missed_gain_to_exposure` 不过高；
4. fast-fail 明显减少坏 exposure 的尾部损失；
5. signal frequency 明显低于 daily BaseRate；
6. episode-level concentration 不过高。

必须停止或重写 EP2 当出现：

1. exposure 成功主要来自同一年度 / 少数 instrument-year；
2. signal 太高频，退化成 daily alpha；
3. short-horizon expectancy 为正但 `missed_gain_to_exposure` 很大；
4. fast-fail 错杀大量后续 winner；
5. exposure timing 只跑赢 random，但跑不赢 `buy_all_on_launch_hold_to_H` 或 `buy_all_on_launch_with_same_fast_fail`；
6. 需要反复改 label threshold 才能成立。
