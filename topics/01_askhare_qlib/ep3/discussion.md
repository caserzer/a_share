# EP3 discussion：Winner Formation Anchor Discovery

> 生成日期：2026-05-09
> 状态：研究讨论记录，不是 requirement，不是策略冻结，不是 P1 validation。
> 与 EP2 的关系：EP3 是新的 sibling research，不是 EP2 R05 / R06 的自然延伸。EP2 的 R01-R05 结果用于解释为什么需要换问题，但 EP3 不继承 R02 threshold、R03 confirm-add pool 或 R05 holding policy 作为研究约束。

---

## 0. TL;DR

EP2 R04 / R05 已经给出一个很清楚的信号：

```text
EP2/R03 的 entry 更像短周期 launch event timing；
它不是已经被证明的 long-horizon winner formation entry。
```

R05-pre 中三条 deterministic holding / exit policy 都能把 validation strict big-winner capture 从 `2` 提高到 `5`，但同步带来：

```text
p05 return 恶化约 1.6-1.9pct；
capital occupancy 上升到 2.56-3.32 倍；
Track A / Track B / matched-random p95 全部失败。
```

这说明继续在 R03 confirmed pool 里做 continuation filter，可能只是在错误母体里切样本。更彻底的方向是把问题改成：

```text
真正的大 winner 在启动前、启动初期、加速前，
有没有稳定、可观察、可执行的 lifecycle anchor？
```

EP3 的目标不是训练策略，而是做 audit-first discovery：

```text
先找 winner formation anchor；
再用 matched baseline 和 instrument-year stability 判断它是否值得进入下一阶段。
```

P0 第一版必须足够窄：

```text
只实现 2 个 anchor family：
  A. launch 后回踩不破再转强
  C. 二次突破

其余 anchor family 只进入 P0.5 / P1 候选库，
不能在 P0 中实现或参与筛选。
```

---

## 1. 为什么不是继续做 EP2 filter

EP2 当前 entry 漏斗是：

```text
broad launch detector
  -> valid probe window filter
    -> R02 short-horizon hazard probe selector
      -> R03 bounded confirm-add
        -> H10 natural exit / 6% fast-fail
```

它已经证明了一个短周期事实：

```text
launch 后存在低频、可执行、低换手的 probe / confirm-add timing alpha。
```

但它没有证明：

```text
R03 confirm-add 后的 episode 已经进入 long-horizon winner formation 阶段。
```

R05 的失败形态更像：

```text
延长持有会多碰到几个 winner；
但这几个 winner 不是由当前 entry 精准识别出来的；
同时更多非 winner / bad continuation episode 会进入尾部风险。
```

所以，confirm-add continuation filter 不应该被视为解决方案。最多它是一个便宜的 falsification test：

```text
R03 confirmed pool 里是否存在稳定可分离的 long-hold 子集？
```

如果我们真心怀疑 filter 无法解决问题，那么更合理的是不要把下一阶段写成 R06 filter，而是另开 EP3。

---

## 2. EP3 的核心问题

EP3 不问：

```text
已经买了以后怎么多拿几天？
```

EP3 问：

```text
什么时候才真的进入了值得承担更长风险的 winner formation 阶段？
```

更机械的研究问题：

```text
在明确限定的 forward-audit 母体中，
是否存在可观察、next-open 可执行的 winner formation anchor，
能相对 matched baseline 同时改善：
  after-cost return,
  p05 / MAE,
  big-winner capture,
  instrument-year positive rate,
且不依赖单一年份、单一行业或少数股票？
```

这不是重新预测 120d winner，也不是重新调 R02 threshold。它是从 lifecycle anchor 的角度重建 entry discovery。

EP3 必须拆成两套母体：

```text
lifecycle profiling universe:
  全 PIT universe 中所有 50h120 / 100h240 winner；
  只做 retrospective lifecycle profiling；
  不计算 matched baseline lift；
  不做 promotion。

forward audit universe:
  EP2 launch pool
  + lifecycle profiling 发现的 winner_start 附近观察窗口中的 matched control stock-days；
  只在这一套母体上测试 observable anchor 的 next-open lift。
```

这样做的目的：

```text
不被 EP2 launch detector 完全锁死；
也不把全 PIT stock-day universe 直接变成新的 BaseRate 级别搜索。
```

---

## 3. 第一阶段应该做 retrospective lifecycle audit

第一步不是训练模型，而是把历史大 winner 的形成路径拆开。

对每个 50h120 / 100h240 winner，至少记录：

```text
winner_start_anchor:
  第一次出现可观察异动的日期。

pre_breakout_base:
  主升前是否有横盘、回踩、缩量、低波动区。

first_acceleration:
  第一次价格与成交额同步加速。

confirmation_anchor:
  第一次突破后是否回踩不破；
  是否出现第二次放量突破；
  是否行业同步扩散。

late_acceleration:
  已经明显上涨后的继续加速阶段。

failure_lookalikes:
  形态接近 winner anchor，但之后失败的样本。
```

这里必须分清两类字段：

```text
retrospective lifecycle stage:
  事后才知道的位置，只能用来解释路径和生成候选想法。

observable anchor:
  当时收盘后已经可见，可以进入未来候选 entry 测试。
```

EP3 最大的防泄漏边界就是：不能把 retrospective stage 直接当信号。

lifecycle profiling 阶段只回答：

```text
winner 中哪些 lifecycle stage 经常出现；
这些 stage 距离 first target / peak / observable start 有多远；
哪些 stage 可以被翻译成 signal_date close-derived anchor；
是否存在形态相近的 failure lookalikes。
```

它不回答：

```text
anchor 是否有交易 lift；
anchor 是否优于 matched baseline；
anchor 是否可以 promotion。
```

因此，winner-only 母体中不允许计算 `matched_delay_baseline` 或 `same_instrument_nonanchor_baseline` 的 lift。否则同一个 winner 上的非 anchor 日也可能处于上涨路径中，baseline 会被系统性污染。

---

## 4. Candidate observable anchors

EP3 第一版必须从少量预注册 anchor family 开始，不要做大规模 primitive search。

P0 只实现两个 primary anchor family：

```text
A. launch 后回踩不破再转强
   价格回撤但不跌破 launch reference / ATR floor；
   之后 next-open 可执行转强。

C. 二次突破
   第一次 launch 不是 entry；
   第二次放量突破或再加速才是 candidate entry。
```

选择 A / C 的理由：

```text
它们直接对应 lifecycle profiling 中最容易观察和最容易反证的阶段；
它们天然适合 failure-lookalike baseline；
它们不需要先引入复杂行业 breadth / regime / volatility primitive。
```

其余 anchor family 只进入候选库，P0 不实现：

```text
B. 首次放量突破后缩量整理
   first acceleration 后波动下降、成交缩量；
   整理后重新站上短期高点或关键均线。

D. 行业同步扩散
   个股启动同时行业 breadth / relative strength 改善；
   避免只买孤立异动。

E. market regime 配合后的强势延续
   市场宽度、趋势、风险偏好改善后，强势股再加速。

F. 高换手后的 volatility contraction
   高成交换手后波动收敛，随后再启动。

G. failed lookalike avoidance
   对看起来像 winner anchor 但随后快速失败的样本做对照。
```

这些 deferred families 不能参与 P0 selection、ranking 或 proceed gate。

这些 anchor 的共同要求：

```text
signal_date close-derived；
entry_price_reference = next open；
不能使用 entry execution date 的 high / low / close 作为 signal；
不能使用 future target date / future peak date 作为 feature。
```

---

## 5. EP3 不是直接预测 120d big-winner

不建议把 label 写成：

```text
未来 120 日是否涨 50%
```

原因：

```text
1. horizon 太长，噪声太大；
2. 容易回到 EP2 已经暴露的 horizon mismatch；
3. 只提高 winner capture 不够，还必须控制 p05 / MAE / capital occupancy；
4. 这会诱导模型学习事后 winner，而不是可执行 anchor。
```

更合适的是 anchor-level lift：

```text
anchor 后 H20 after-cost return；
anchor 后 p05 / MAE；
anchor 后 50h120 / 100h240 capture sensitivity；
anchor 相对 matched-delay baseline 的 lift；
anchor 的 instrument-year positive rate；
anchor 的 failure-lookalike rate。
```

P0 的 primary horizon 固定为：

```text
primary_horizon = H20
```

`H10` 和 `H60` 只能作为 sensitivity，不允许在 P0 中挑选最好的 horizon。否则 H10/H20/H60 同时报出后，很容易形成隐性 selection bias。

Big-winner label 可以作为 outcome audit，不应作为第一版主训练目标。

---

## 6. Matched baseline 是 EP3 的核心

EP3 最容易犯的错是看历史 winner 图，总结出漂亮形态。必须用 matched baseline 反杀，但 matched baseline 只能用于 forward audit，不能用于 winner-only lifecycle profiling。

forward audit 中，每个 candidate anchor 至少要对比：

```text
all_launch_direct_baseline:
  所有 launch 直接 next-open 买。

matched_delay_baseline:
  同一个 launch episode 中随机或固定延迟买。

same_instrument_nonanchor_baseline:
  同股票、相近时间、没有 anchor 的可执行日期。

industry_matched_baseline:
  同行业、同 regime、同 market state 的非 anchor 股票。

failed_lookalike_baseline:
  形态相似但没有后续 winner formation 的样本。
```

只有 anchor 相对这些 baseline 仍有 lift，才可能是真的。

两阶段评估边界：

```text
lifecycle profiling:
  winner-only；
  输出 stage 发生率、距 winner_start 的天数分布、可观察性、failure lookalike 是否存在；
  不输出 matched lift。

forward audit:
  bounded forward-audit universe；
  输出 next-open executable lift、matched baseline lift、risk metrics、coverage / concentration。
```

---

## 7. 评估不能停留在 event-level

大 winner 很容易被少数年份、少数股票、少数行业撑起来。因此 EP3 不能只看 event 胜率或平均收益。

必须至少输出：

```text
event_count
anchor_trigger_count
anchor_trigger_rate_per_launch_episode
anchor_trigger_count_per_instrument_year
unique_instrument_count
unique_instrument_year_count
instrument_year_positive_rate
year_positive_count
top1_instrument_year_pnl_share
top5_instrument_exposure_share
industry_concentration_share
regime_bucket_stability
failure_lookalike_rate
matched_baseline_lift_by_year
```

硬性判断：

```text
如果一个 anchor 只在一个年份、一个行业或几只股票上有效，
不能进入下一阶段。
```

P0 必须预注册触发频率预算：

```text
anchor_trigger_rate_per_launch_episode in [0.2, 1.5]
```

含义：

```text
低于 0.2：
  样本量太少，P0 audit 不稳定。

高于 1.5：
  anchor 太频繁，接近 daily / TopK 式搜索，不再是 winner formation anchor。
```

超出预算的 anchor family 直接 disqualify，不允许靠收益指标补救。

---

## 8. EP3 第一版产物

EP3 第一版建议只做 discovery audit，不做 strategy promotion。

建议产物：

```text
ep3_winner_lifecycle_profile.csv
ep3_winner_cross_year_audit.csv
ep3_observable_anchor_dictionary.csv
ep3_candidate_anchor_panel.parquet
ep3_anchor_vs_matched_baseline.csv
ep3_failure_lookalike_audit.csv
ep3_instrument_year_lift_audit.csv
ep3_regime_stability_audit.csv
ep3_preliminary_anchor_leads.csv
ep3_discussion_report.md
ep3_manifest.json
```

`ep3_winner_lifecycle_profile.csv` 的 schema 必须是：

```text
one row per winner-stage
primary_key = winner_episode_id + lifecycle_stage_id
```

不能写成一个 winner 一行后把多个 stage 塞进宽字段；否则 stage 距离、可观察性、anchor recall 和 failure lookalike 对照都不可重复。

其中 `ep3_preliminary_anchor_leads.csv` 只能表示：

```text
值得进入下一阶段验证的 anchor idea。
```

不能表示：

```text
策略候选；
P1 candidate；
可交易系统；
冻结版本。
```

---

## 9. 推荐的阶段拆分

### 9.1 EP3-P0：Winner lifecycle and anchor discovery

目标：

```text
只回答是否存在可观察 anchor idea。
```

允许：

```text
retrospective winner profiling；
observable anchor dictionary；
matched baseline audit；
failure lookalike audit；
instrument-year lift audit。
```

P0 只允许实现：

```text
primary_anchor_families:
  - pullback_hold_restrengthen
  - second_breakout

deferred_anchor_families:
  - post_breakout_contraction
  - industry_sync_expansion
  - market_regime_reacceleration
  - turnover_volatility_contraction
  - failed_lookalike_avoidance
```

禁止：

```text
训练交易模型；
输出策略；
P1 promotion；
full portfolio backtest；
使用 R02 threshold 或 R03 confirmed pool 作为主筛选约束。
实现 deferred anchor family；
在 H10/H20/H60 中选择最优 horizon。
```

### 9.2 EP3-P1：Anchor validation

只有 P0 形成稳定 lead 后才进入。

目标：

```text
对少量 anchor 做 validation-only selection；
robustness / future split 只 holdout；
验证 next-open executable entry 的 after-cost lift 和 risk profile。
```

### 9.3 EP3-P2：Schedule / portfolio integration

只有 P1 通过后才进入。

目标：

```text
研究 anchor entry 后的 schedule；
再讨论是否与 EP2 event sleeve 或 BaseRate 组合结合。
```

---

## 10. EP3 与 EP2 的边界

可复用 EP2 工程资产：

```text
PIT price / universe / industry；
calendar；
next-open execution；
blocked execution rules；
cost model；
launch detector as one reference anchor；
as-of discipline；
report / manifest / validator 风格。
```

不可继承为研究约束：

```text
R02 selected_threshold；
R02 selected_stop_risk_ceiling；
R03 confirm-add rule；
R05 deterministic holding policies；
H10 primary label；
R03 confirmed pool。
```

EP2 可以作为 reference lane：

```text
short-horizon event sleeve reference；
not winner formation source of truth。
```

---

## 11. 当前建议的 EP3 第一版问题

如果只选一个具体问题，建议写成：

```text
在 bounded forward-audit universe 中，
是否存在 P0 预注册的 pullback-hold-restrengthen 或 second-breakout anchor，
能在 next-open 可执行价格下，
相对 matched-delay baseline 同时提高：
  H20 after-cost return,
  big-winner capture sensitivity,
  instrument-year positive rate,
并且不显著恶化 p05 / MAE，
触发频率落在预注册预算内，
不依赖单一年份、单一行业或少数股票？
```

注意：P0 discussion 阶段不冻结 “launch 后 3-30 个交易日” 这种窗口。窗口应由 lifecycle profiling 的 `days_from_observable_start` / `days_to_winner_start` 分布先给出，再在 formal requirement 中预注册。讨论稿只能记录：

```text
anchor_window = to_be_frozen_after_lifecycle_profile
```

这个问题比 R03/R05 更接近 winner formation。

它不是问：

```text
已经买了以后怎么多拿几天？
```

而是问：

```text
什么时候才真的进入了值得承担更长风险的阶段？
```

---

## 12. Stop / continue 判断

EP3-P0 应该非常容易停止。

继续条件：

```text
至少一个 anchor family 在 validation-like period 中：
  相对 matched baseline 有 after-cost lift；
  p05 / MAE 不明显恶化；
  instrument-year positive rate 过线；
  anchor_trigger_rate_per_launch_episode in [0.2, 1.5]；
  lifecycle anchor recall >= 0.30；
  year / industry / regime concentration 可接受；
  failed lookalike rate 不过高。
```

停止条件：

```text
anchor lift 只来自少数股票或年份；
matched baseline 后 lift 消失；
p05 / MAE 明显恶化；
big-winner capture 只是由于更长 exposure；
observable anchor 不能从 retrospective lifecycle 中干净提取；
anchor 在 winner lifecycle 中召回率 < 0.30；
anchor_trigger_rate_per_launch_episode 不在 [0.2, 1.5]；
failure lookalikes 与 winners 无法区分。
```

如果停止，结论应是：

```text
当前数据和规则下，没有形成可执行 winner formation anchor；
EP2 保持 short-horizon event sleeve 定位；
不继续 long-horizon winner holding system。
```
