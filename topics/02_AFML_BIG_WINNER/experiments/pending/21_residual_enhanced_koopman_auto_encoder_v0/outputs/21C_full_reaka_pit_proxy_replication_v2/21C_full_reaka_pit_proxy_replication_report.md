# 21C Full REAKA PIT Proxy Local Validation Sanity

## 决策与 claim ceiling

`21C_FULL_teacher_or_architecture_pipeline_not_evaluable`。本 bundle 为 P1 materialization failure profile。

## 独立 scope restart 与 corrected lineage

21B_v5 runtime-counter erratum、21A M2 lineage erratum及 execution pins均通过；失败发生在任何模型训练前。

## Teacher materialization failure

全体 train denominator 中有 `396` 个 source samples 不存在同 instrument 的严格 next approved feature-cache key。
按 v2 合同禁止 drop、forward-fill、借用跨 instrument offset或读取 raw feature source，因此 `teacher_materialization_gate=not_evaluable`。

前十个受影响 keys：`["SH600269|2018-02-09","SZ000501|2018-02-26","SZ000910|2018-02-26","SH600618|2018-03-15","SZ002102|2018-03-16","SH600622|2018-03-21","SZ000881|2018-03-21","SZ000600|2018-03-30","SH600172|2018-04-02","SZ002343|2018-04-02"]`。

## 未运行范围

Resource probe、三个 R2 jobs、validation-early selection、late readout、RankIC、paired comparison和Top30均未运行；historical holdout access为0。

## Claim boundary

本结果不支持 REAKA 方向、相对 comparator ordering、机制、盈利或部署结论。下一步必须新建 requirement解决 teacher feature availability estimand。
