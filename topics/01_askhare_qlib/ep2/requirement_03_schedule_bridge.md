# EP2 Requirement 03: Exposure Schedule Bridge

Status: draft placeholder. Do not implement until `ep2/requirement_01_label_and_baseline_freeze.md` and `ep2/requirement_02_hazard_timing_model.md` are reviewed and accepted.

This file intentionally copies the relevant discussion content only. Detailed implementation requirements will be expanded after Requirement 02 passes.

## EP2-4 Exposure schedule + BaseRate-overlap bridge（条件开启）

仅当 EP2-3 hazard score 相对 EP2-2 schedule baseline 有可验证 lift 时启动。

任务：

- 把 hazard score 装配成 probe / confirm_add / fast_fail_exit 完整 schedule；
- 输出与 EP2-2 schedule baseline 同口径的对比；
- 完成 BaseRate-overlap bridge audit（仅前 3 个问题）：
  1. EP2 launch pool 中有多少事件也被 BaseRate TopK 命中？
  2. EP2 exposure signal 是否出现在 BaseRate 高分区域？
  3. EP2 exposure schedule 是否提供 BaseRate 没覆盖的低频机会？

剩余两个组合层归因问题（fast-fail 解释 BaseRate 亏损 / 是否重复加仓）推迟到 EP2 之后的完整 holding / exit 阶段。

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
