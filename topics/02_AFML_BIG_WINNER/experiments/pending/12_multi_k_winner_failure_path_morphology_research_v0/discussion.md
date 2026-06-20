# C0 Survival Episode 讨论

## 1. 当前观察

通过逐票绘图观察 C0 买点后，直观结论并不是“C0 买点很差”。相反，很多 C0 买点从价格路径上看并不差，只是它们没有落入既有 big-winner episode。当前评估把 C0 事件主要 reference 到稀有的 big-winner lifecycle，因此会把一批中右尾、可交易但不是超级右尾的机会算成 false positive。

这会弱化模型表现：

- big winner 在当前数据结构中本来就是稀有事件，base rate 低，event precision 自然会很低；
- C0 事件如果只用 big-winner episode 评估，会把“可交易 survival opportunity”和“真正无效买点”混在一起；
- 模型即使能识别可交易机会，也未必能把它们全部推到 120d +50% 的超级右尾，因此 raw big-winner precision 会低估模型价值。

已有 12A3/12A4/12A5A 结果也支持这个解释：

- C0 的优势是“少、早、重复低”，不是裸 precision 明显更高。
- 12A3 中，C0 event_n 为 28,691，低于 R-core 的 47,914；10d duplicate 为 7.25%，显著低于 R-core 的 57.83%；low 后首触发 median 为 9 sessions，早于 R-core 的 14 sessions。
- 但 C0 low-to-high event precision 只有 5.32%，低于 R-core 的 6.39%。这说明 C0 是更干净的状态变化事件源，不是天然高 precision 的 big-winner selector。
- 12A4 的 meta-labeling 有 uplift，robustness top bucket precision 从 C0 baseline 的 7.94% 提到 11.86%，但 bad-side 也从 28.12% 升到 40.59%。
- 12A5A 进一步显示，现有 PIT feature 能做局部风险尾部剔除，但没有证明 clean winner 与 bad-side 在当前特征空间稳定可分。

因此，当前问题不应被表述为“重新构建 big-winner episode”。更准确的表述是：

```text
为 C0 买点构建 survival episode / opportunity episode，
用它评估 C0 事件是否能产生可交易机会，
再单独检查 survival-selected C0 events 是否富集既有 big-winner lifecycle。
```

## 2. 为什么不是重构 Big Winner Episode

Big-winner episode 问的是：

```text
这个买点是否属于极少数超级右尾生命周期？
```

Survival episode 问的是：

```text
从这个 C0 买点进入后，是否能活下来，
并在合理窗口内给出足够 payoff？
```

两者不是同一个目标。

如果继续用 big-winner episode 作为唯一成功定义，会有两个问题：

1. 目标过窄。120d +50% 这类右尾事件天然稀有，会导致 event precision 被 base rate 压低。
2. 标签误伤。一些 60d 内能给出 +20% 或 +30% MFE、且没有先触发严重 MAE 的买点，在交易意义上是有效机会，但在 big-winner 标签下会被算成失败。

因此，big winner 应该保留为 enrichment diagnostic，而不是 C0 买点的 survival 主标签。

更合理的目标层级是：

```text
hard_fail:
  很快触发下障碍，说明买点或时点明显失败。

survive_no_payoff:
  没有快速失败，但在持有窗口内没有给出足够 MFE。

tradable_survivor:
  在合理窗口内先触发上障碍，且没有先触发下障碍。
```

Big winner 与 survival outcome 是两个不同目标。理论上，如果 survival episode 定义有效，那么 survival-selected C0 events 应该相对 all-C0 baseline 富集既有 big-winner lifecycle；但这个富集只用于诊断，不参与 survival 标签定义或阈值选择。

## 3. Survival Episode 的基本定义

建议使用 triple-barrier / first-hit 口径定义 C0-local survival episode。

### 3.0 分母口径：C0 event universe 自成分母

survival episode 必须以 **C0 event universe 自己**作为分母，不复用 06 episode registry（428）或 11A2 PIT rows（446）作为成功定义的分母：

```text
survival_denominator = C0 event universe（在本 audit 内独立重算的全部 C0 事件）
big_winner_enrichment = survival-selected C0 events 对既有 big-winner lifecycle 的富集诊断
```

这样做的原因：

```text
1. research_plan 已冻结 06=428 与 11A2=446 两个分母必须分离；
   任何混用都会重建 06-08-11 drift。
2. C0 buy-point 的评估问题是“C0 进入后能否活下来并给出 payoff”，
   分母天然应是 C0 事件本身，而不是稀有 big-winner lifecycle。
3. 06 / 11A2 数值只作 cross-check，不作 ground truth。
```

基础锚点：

```text
anchor = C0 event_t0
entry = next executable open after event_t0
upper barrier = MFE threshold
lower barrier = MAE threshold
vertical barrier = holding horizon
same-bar priority = lower barrier first
```

标签状态：

```text
upper_first:
  入场后先触发上障碍，定义为 survival opportunity 成功。

lower_first:
  入场后先触发下障碍，定义为 hard fail / bad survival。

neutral:
  到 vertical barrier 既没有触发上障碍，也没有触发下障碍。

censored:
  数据不足，无法完整观察 vertical barrier。
```

### 3.1 A 股粒度与可成交性约束（必须显式处理）

以下约束不处理会系统性高估 survival rate，必须在 audit 中显式落地：

```text
entry executability:
  next executable open 必须排除停牌、一字涨停开盘无法买入的情形；
  big winner 启动初期常见连板 / 一字板，next open 未必可成交，
  不可成交样本单独标注（entry_blocked），不计入 upper_first 成功分子。

same-bar 日线粒度局限:
  日线无法分辨同一根 bar 内 high 与 low 的先后；
  同一 bar 同时穿越上下障碍时强制判 lower_first（保守）；
  必须统计 same_bar_conflict 发生频率并单独输出。

barrier 价口径:
  上 / 下障碍用 high / low 触障属于乐观上界；
  实际可成交价受 close 与涨跌停约束；
  high / low 仅作 diagnostic，需在表内标注为乐观上界。

censored 分母:
  所有 rate 的分母必须显式声明是否剔除 censored；
  近端样本（数据不足 horizon）必须从对应 horizon 的 rate 分母剔除或单列，
  避免长 horizon positive rate 的时间端点偏差。
```

第一版可以从这些候选标签开始，而不是只定一个点：

```text
tradable_survivor_20:
  upper = +20%
  lower = -10%
  horizon = 60 trading days

strong_survivor_30:
  upper = +30%
  lower = -10% or -15%
  horizon = 60 or 80 trading days
```

其中 `tradable_survivor_20` 更接近当前标签体系中的 `continuation_60`，`strong_survivor_30` 是中右尾目标。正式 12A6 requirement 中不应预先指定这两个点为最终标签，而应从完整 forward-path grid 统计中选择 upper / lower / horizon。

## 4. MAE / MFE / 时长不能拍脑袋

`MAE = -10%`、`MFE = +30%`、`horizon = 60d` 可以作为候选，但不应直接作为最终定义。合理做法是先统计 C0 买点后的 forward path，再从统计分布里选择阈值。

### 4.0 audit 内独立重算与审计

所有 forward-path 量必须在本 audit 内从原始行情独立重算，不得从报告文本或上游聚合表反推：

```text
recompute_rule:
  C0 event universe、entry、MFE / MAE / time-to-hit / pre_success_MAE
  全部在本 audit 内基于原始 PIT 行情重算；
  12A4 / 06 / 11A2 数值只作 sanity cross-check，不作 ground truth。

input_artifact_audit:
  每个被读取的输入 artifact 必须进入 input_artifact_audit.csv，
  记录 resolved path、row count、sha256、schema status、read status。

fail_closed:
  必需输入缺失、schema 不匹配、PIT 时间戳不可证明时 fail closed；
  不得从聚合表反推事件、标签或特征。
```

对每个 C0 买点，从 next executable open 开始，计算：

```text
MFE_H = H 日内最高价 / 入场价 - 1
MAE_H = H 日内最低价 / 入场价 - 1
T_up(x) = 第一次触达 +x 的交易日
T_down(y) = 第一次触达 -y 的交易日
pre_success_MAE(x) = 成功触达 +x 前经历过的最大不利波动
```

建议网格：

```text
horizon H:
  10, 20, 40, 60, 80, 120 trading days

upper barrier:
  +10%, +15%, +20%, +25%, +30%, +40%

lower barrier:
  -6%, -8%, -10%, -12%, -15%, -20%
```

每个组合都要输出：

```text
event_n
upper_first_n / rate
lower_first_n / rate
neutral_n / rate
censored_n / rate
median_time_to_upper
median_time_to_lower
pre_success_MAE p50 / p75 / p90
positive rate by split
positive rate by board
positive rate by primary_family_id
```

### 4.1 阈值选择的预注册与多重比较防护

网格为 `6 horizon × 5 upper × 6 lower = 180 组合`，再叠加 split / board / family 切片，会产生上千个 frontier 读数。必须防止从大量读数里回头挑“看起来最好”的阈值：

```text
pre_registered_rule:
  阈值选择规则在跑 robustness / OOS 前预先写定，
  例如固定的边际收益拐点准则（horizon 每加 20d 新增 upper_first rate < 2%-3% 即停）。

single_candidate_in_sample:
  先只在 train / in-sample 用预注册规则确定单一候选阈值。

oos_validate_only:
  robustness / OOS 切片只做验证，不做调参；
  禁止用 OOS 切片回头挑更好看的 threshold / horizon / family。
```

## 5. MFE 上障碍如何选

MFE 上障碍要同时满足三个条件：

```text
1. positive rate 足够建模，不能像 big winner 一样过稀。
2. payoff 有交易意义，不能只是普通噪声反弹。
3. 跨 split、board、family 稳定，不能只由少数切片支撑。
```

判断方式：

- 如果 `+30% / 60d` 的 upper_first rate 只有 5%-8%，它可能仍然太稀有，会重复 big-winner precision 过低的问题。
- 如果 `+20% / 60d` 有 15%-25% 的 positive rate，且 split 稳定，它更适合作为 primary survival 标签。
- 如果 `+30% / 60d` 样本足够，但主要集中在某些 board 或某些年份，需要把它定义为 strong survival diagnostic，而不是唯一 primary 标签。

因此建议不要在 `+20%` 和 `+30%` 之间二选一，而是分层：

```text
primary survival:
  +20% / horizon

strong survival:
  +30% / horizon

big-winner enrichment:
  selected survival events vs all-C0 baseline 的 big-winner overlap 富集率
```

这样可以先定义 survival opportunity，再独立观察它是否富集 big winner，而不是把 big winner 当作 survival outcome 的一部分。

## 6. MAE 下障碍如何选

MAE 下障碍不能只由风险偏好决定。关键统计是：

```text
在最终触达 +20% / +30% 的成功样本里，
触达上障碍之前的 pre_success_MAE 分布是多少？
```

例子：

- 如果 80% 的 `+30% survivor` 在成功前 MAE 不超过 -10%，那么 -10% 是合理止损。
- 如果 40% 的 `+30% survivor` 成功前都曾跌到 -12% 到 -15%，那么 -10% 太紧，会杀掉大量真机会。
- 如果坏样本很早触发 -8%，而好样本很少跌破 -8%，那么 -8% 比 -10% 更好。

因此 MAE 选择应当看：

```text
pre_success_MAE p75 / p90
lower_first_rate
upper_first_after_lower_conflict rate
bad-side reduction
true survivor killed by stop rate
```

一个实用选择原则：

```text
选择能过滤明显失败，
但不会杀掉超过 20%-25% true survivor 的下障碍。
```

如果 -10% 会杀掉过多 `+30% survivor`，应测试 -12% 或 -15%。如果 -15% 才合理，则说明 C0 买点本身波动很大，后续模型应把 position sizing / volatility normalization 纳入讨论。

## 7. 持有时长如何选

持有时长要看 time-to-hit 曲线，而不是直接拍 60d。

需要统计：

```text
P(MFE >= +20% by 20d / 40d / 60d / 80d / 120d)
P(MFE >= +30% by 20d / 40d / 60d / 80d / 120d)
P(MAE <= -10% by 10d / 20d / 40d / 60d)
```

合理 horizon 应该在累计成功率曲线出现边际收益下降的位置。

简单规则：

```text
当 horizon 每增加 20d，
新增 upper_first rate < 2%-3%，
且新增样本的 MAE 或 bad-side 更差，
就不应继续延长 horizon。
```

如果大部分 `+20%` 或 `+30%` 机会在 40-60d 内完成，60d 合理。如果很多机会要到 80-120d 才完成，则 60d 只能定义为 medium survival，不应作为完整 survival 标签。

## 8. Meta-labeling 的角色

主升浪后期出现 C0 买点容易失败，这个观察可能成立，但不应直接跳到 meta-labeling。

更合适的顺序是：

```text
step 1:
  先用 C0-local survival episode 把 C0 事件分成
  upper_first / lower_first / neutral / censored。

step 2:
  再检查主升浪后期特征是否集中出现在 lower_first 或 neutral。

step 3:
  如果后期买点主要对应 lower_first，再训练 meta-label rejector。

step 4:
  如果后期买点大量只是 not_big_winner_but_survivor，
  那问题是 big-winner 标签太窄，不是买点失败。
```

当前 12A4/12A5A 的经验说明，直接用现有 big-winner / bad-side 标签做 meta-labeling，会遇到 precision 和 bad-side 同时上升的问题。模型可能学到的是更拥挤、更活跃、更高波动的状态，而不是稳定的 clean survivor 形态。

因此，meta-labeling 的目标应改成：

```text
primary:
  reject lower_first / hard_fail。

secondary:
  rank upper_first survival probability。

diagnostic:
  observe bigwinner enrichment ratio。
```

不要让模型一开始就承担“预测稀有 big winner”的任务。

注意：`lower_first` / `upper_first` 是用未来路径定义的标签，只能作为训练目标，不得作为 rejector 特征。继承 12A5A 非目标：

```text
no_future_feature:
  不用 episode low / high / first_50pct / MFE / future return 生成 rejector feature；
  不用 bad-side / winner / target / inside-window 标签作为 rejector 输入特征。
```

## 9. 建议的下一步实验

建议新增一个小型 audit，而不是直接建模：

```text
12A6_c0_local_survival_episode_audit
```

12A6 是纯 audit 阶段，不训练任何模型（与 12A5A 把 probe 与 modeling 分阶段的纪律一致）。第 8 节的 meta-labeling 全部推迟到 audit 通过后的独立 requirement。

核心研究问题：

```text
C0 买点是否能形成稳定的 survival opportunity？
MAE / MFE / horizon 的合理阈值在哪里？
survival-selected C0 events 是否相对 all-C0 baseline 富集既有 big-winner lifecycle？
主升浪后期买点到底是 hard fail，还是 not-big-winner-but-survivor？
```

必需输出：

```text
input_artifact_audit.csv
c0_forward_path_distribution.csv
c0_triple_barrier_grid_frontier.csv
c0_pre_success_mae_distribution.csv
c0_time_to_hit_curve.csv
c0_bigwinner_enrichment_crosstab.csv
c0_late_stage_failure_diagnostics.csv
c0_entry_executability_audit.csv
c0_same_bar_conflict_audit.csv
```

决策读数（阈值为占位占位，需在 12A6 spec 里预注册最终数值）：

```text
primary_survival_candidate:
  upper_first rate >= P_MIN（例 15%）；
  lower_first rate <= L_MAX（例 35%）；
  split 间 upper_first rate 相对差 <= S_MAX（例 25%），board / family 同口径；
  true survivor killed by stop rate <= K_MAX（例 25%）；
  horizon 每加 20d 新增 upper_first rate < M_MIN（例 2%-3%）的拐点存在。

strong_survival_candidate:
  payoff 更高（upper = +30%）；
  upper_first rate >= P_STRONG_MIN（例 8%），不至于重复 big-winner base-rate 问题；
  作为 secondary rank target。

bigwinner_enrichment_diagnostic:
  只观察 survival-selected C0 events 是否富集既有 big-winner lifecycle；
  不参与 survival threshold selection。
```

上述阈值字母（P_MIN / L_MAX / S_MAX / K_MAX / M_MIN / P_STRONG_MIN）是占位，括号内为参考起点；必须在 12A6 spec 里预注册为单一固定数值，不得事后调整。

## 10. 当前结论

当前更合理的研究表述是：

```text
C0 买点不是要直接预测 rare big winner。
先验证 C0 是否能产生可交易 survival opportunity；
再单独观察 survival-selected C0 events 是否富集既有 big-winner lifecycle。
```

MAE / MFE / 时长应由 forward path 统计决定，而不是主观设定。第一轮可以把 `+20% / -10% / 60d`、`+30% / -10% 或 -15% / 60d 或 80d` 等作为候选读数，但正式 requirement 应从完整 grid 的 train 统计中选择 upper / lower / horizon。Big winner 只作为 enrichment diagnostic。

如果统计显示 `+30% / -10% / 60d` 的 positive rate 足够、pre-success MAE 不超过 -10% 的比例足够高、time-to-hit 在 60d 前出现明显拐点，那么它可以升级为主标签。否则不应强行使用这个阈值。
