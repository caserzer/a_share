# Discussion 3: Close Episode 12 and Reopen Event Discovery as Episode 13

## 0. 结论

12A7g 之后，不应继续在 Episode 12 下新增 `12A7h` / `12A8` requirement 来推进 event mining。

Episode 12 的问题已经回答清楚：

```text
C0 不是一个稳定的 winner selector。
Vol-scaled label form 本身可用。
Post-hoc survivor 的改善主要是 precision / recall tradeoff。
Deployable stage-2 没有留下稳健可排序的 winner signal。
Full PIT universe 存在可排序 path morphology，但这还不是 event-family 证据。
```

因此，Episode 12 应收敛为：

```text
12-series final state =
  C0 降级为 defense / participation context;
  不再继续围绕 C0 做 winner selector 小修小补;
  不在 12 目录下继续创建 event-mining requirement。
```

下一阶段应重开 Episode 13，主题不是 “修复 C0”，而是：

```text
Episode 13 =
  full-PIT native opportunity universe 上的 event-agnostic discovery;
  用 12A7g 选出的 vol-scaled winner label 作为冻结 outcome;
  用 train-frozen token cartography / event mining 寻找新 event family。
```

## 1. 12A7g 对 discussion2 的裁决

`12A7g_vol_scaled_label_panel_c0_separability_triage` 的最终裁决是：

```text
decision_state = 12A7g_baserate_only_not_separable_stop_winner_selection
next_allowed_requirement = defense_overlay_plus_rule_based_participation_summary
```

这个结果支持 discussion2 的核心怀疑：C0 有弱右尾富集，但不是干净 winner event。更重要的是，C0 的 post-hoc survivor 条件率改善不能等同于可部署 edge。

关键证据：

```text
selected_label = vol20d_kup2p0_kdn1p0_H20
train winner base rate = 0.1488
train positive n = 34,621
label stability score = 0.9003

c0_entry_t0 winner base rate = 0.1527
c0_posthoc_no_fast_fail_survivor winner base rate = 0.2347
c0_deployable_stage2_reference winner base rate = 0.1579

c0_deployable_stage2_reference recall_vs_entry = 0.2474
c0_deployable_stage2_reference utility_per_20d = -0.009238
```

Interpretation:

```text
1. Vol-scaled label 成立，不是失败点。
2. C0 entry 有弱信号，但 robustness 不稳。
3. post-hoc survivor 看起来更干净，但无法变成可部署 selector。
4. deployable stage-2 的 recall cost 太高，且 utility 为负。
5. C0 适合降级为 defense / participation context，而不是继续当 winner discovery engine。
```

## 2. 为什么不应在 12 下继续做 requirement

Episode 12 的主线是：

```text
multi-K winner / failure path morphology
-> C0 state-change backbone
-> fast-fail defense
-> stage-2 continuation
-> C0 separability / winner-label triage
```

这条线已经给出负面裁决：C0 的 winner-selection ceiling 已经被测出来了。继续在 12 下追加 requirement 有两个问题：

```text
1. 名义上仍像是在修 C0 体系，容易把问题继续限定在旧 event family 内。
2. event mining 的对象已经不应是 C0 的扩展，而应是 full PIT native universe 的重新发现。
```

所以 12 目录下只保留讨论和结果归档，不再继续产生新 requirement。

如果未来需要引用 12 的产物，引用边界应是：

```text
12A7g provides:
  selected vol-scaled label;
  C0 negative selector evidence;
  defense / participation interpretation;
  full raw universe primitive diagnostic signal.

12A7g does not provide:
  validated C0-comparable event-family cartography gate;
  deployable winner selector;
  permission to interpret raw full-universe separability as event support.
```

## 3. 跳出 C0 后，不需要先修 C0 active band

如果目标仍是回答：

```text
full universe 是否比 C0 更值得做？
```

那就必须修 `full_pit_c0_comparable_active_band`，因为这是 C0-vs-full 的公平 denominator。

但 Episode 13 的目标不是 “证明比 C0 好”，而是重启一个 C0-free event discovery episode。因此不需要先修：

```text
full_pit_c0_comparable_active_band
volatility_reconciliation_fail
```

前提是必须换一个新的 denominator：

```text
full_pit_native_opportunity_universe
```

这个 universe 不能从 C0 阈值派生，而要从 full PIT universe train split 自己冻结。

这里的 `full PIT universe` 不是重新发明一套分母。Episode 13 应复用 12A7g 已经构造和审计过的 full PIT vol-scaled universe 作为底座：

```text
reuse from 12A7g:
  record_unit = instrument x reference_date
  PIT executable daily universe
  reference_date / reference_pos
  entry_date / entry_pos / entry_price
  qfq primitive rebuild
  regime_calendar_available 与 missing regime date bypass
  supported board filter
  next-open executable assertion
  required pre-vol lookback complete
  selected label = vol20d_kup2p0_kdn1p0_H20
```

但 Episode 13 不能直接复用 12A7g 的所有 denominator：

```text
do not reuse:
  full_pit_c0_comparable_active_band
  C0-derived active-band thresholds
  C0 entry denominator as the opportunity universe
  raw full-universe separability as event-family evidence
```

正确关系是：

```text
12A7g full PIT vol-scaled universe
  -> Episode 13 full_pit_native_opportunity_universe
     -> len-1 token cartography / event mining
```

也就是说，12A7g 提供 outcome layer 与 PIT primitive base；Episode 13 在其上再冻结一个 C0-free native opportunity band。

建议基础口径：

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date
entry = next executable open

native opportunity filters:
  regime_calendar_available == true
  board_bucket in supported boards
  listed / non-ST / non-suspended where available
  next-open entry executable
  required volatility lookback complete
  basic liquidity floor, train-only
  trading continuity floor, train-only
  volatility sanity floor / cap, train-only
```

注意：跳出 C0 不代表可以使用 raw full universe。raw full universe 的 `max_drawdown_20d` separability 很强，但它可能混入 inactive / low-liquidity / low-motion hard negatives。Episode 13 必须有 native opportunity band，只是不再需要 C0-comparable active band。

### 3.1 放弃 C0-comparable 的代价必须显式记账

放弃 `full_pit_c0_comparable_active_band` 不是免费的。它换来了不必修 `volatility_reconciliation_fail`，但同时永久放弃了一个命题：

```text
Episode 13 永远无法主张 "比 C0 更值得做"。
它只能主张 "在 native opportunity universe 上独立可分且净值为正"。
两者不是同一件事，不允许在结论里偷换。
```

更危险的是：放弃可比 denominator 之后，**无法直接回答"新发现的 event family 是不是又一个 C0-like 双尾 morphology"**。discussion2 §17.6 已警告"换个名字重新发现一个 C0-like 双尾事件"的风险，在 C0-free 设定下反而更难被识别，因为没有可比基准来做对照。

因此，作为对这一代价的补偿，Episode 13 的 bad-side veto（见 §6.3）必须**额外**包含一项 morphology 共线诊断。它不是为了限制 Episode 13 只能找非反转事件，而是为了防止把 broad reversal / C0-like 双尾形态误命名为全新 event family：

```text
morphology_collinearity_check:
  胜出的 len-1 token 与 max_drawdown_20d / distance_to_20d_low /
    rebound_from_20d_low 等 reversal / drawdown / C0-like morphology anchors
    的 rank 相关性必须被报告;
  若胜出 token 与这些 anchors 高度共线(预注册阈值,如 |rank-corr| >= 0.7),
    则标记为 "morphology_rediscovery_suspect";
  高共线本身不构成否决,也不自动禁止解释为可用 event;
  只有当 fast_fail_uplift / lower_first_rate / utility_proxy 同时显示双尾恶化或
    净效用不足时,才降级为 "C0-like two-tailed rediscovery";
  若高共线 token 仍通过 bad-side veto 与 utility gate,
    可以作为 "native morphology event",但不得声称它证明 C0 体系正确。
```

没有这项诊断，Episode 13 可能换了一个 universe 又把 broad drawdown / reversal morphology 重新挖出来一遍，却误以为发现了与既有双尾结构完全无关的新东西。

## 4. 不限定反转效应，但要限定搜索层级

12A7g 发现：

```text
full raw universe selected primitive = max_drawdown_20d
train AUC = 0.6045
validation AUC = 0.6121
robustness AUC = 0.6301
```

这说明 full PIT universe 中存在可排序 path morphology。但 Episode 13 不应预设它一定是反转效应。`max_drawdown_20d` 是一个诊断发现，不是下一阶段的先验结论。

Episode 13 应开放 token family：

```text
reversal / drawdown:
  max_drawdown_20d
  distance_to_20d_low
  rebound_from_20d_low

breakout / trend:
  distance_to_20d_high
  ret_5d / ret_20d buckets
  trend_ma_5_20_spread
  trend_ma_20_60_spread

volatility / range:
  volatility_20d / volatility_60d
  vol compression / expansion
  recent_range_activity_20d
  intraday_range_mean_20d

liquidity / attention:
  turnover_rate_median_20d
  turnover_zscore_20d
  money_median_20d

relative strength:
  stock_vs_board_20d
  board_return_20d
```

但开放 token family 不等于无边界 mining。第一阶段只应做：

```text
len-1 token cartography
```

先回答哪个 token family 在 train 中有 winner uplift，并能在 validation / robustness 中保持方向。只有 len-1 通过后，再考虑 len-2 event sequence。不要一开始做 len-2 / len-3 sequence mining。

## 5. Episode 13 的第一份 requirement 应该是什么

建议新开目录：

```text
topics/02_AFML_BIG_WINNER/experiments/pending/13_full_pit_native_event_discovery_v0/
```

第一份 requirement 不应叫 event mining full run，而应叫 preflight / cartography：

```text
requirement_13a_full_pit_native_token_cartography_preflight.md
```

目标：

```text
Build a C0-free, full-PIT native opportunity universe.
Freeze the selected vol-scaled winner label from 12A7g.
Run train-frozen len-1 token cartography across broad PIT-safe token families.
Evaluate winner uplift, fast-fail uplift, lower-first risk, utility proxy, and stability.
Decide whether sequence mining is justified.
```

非目标：

```text
Do not continue C0 selector repair.
Do not mine len-2 / len-3 sequences yet.
Do not retune winner label.
Do not call raw full-universe separability an event-family result.
Do not use C0-derived thresholds for the native opportunity band.
```

### 5.1 native universe 的 floor / cap 必须预注册并审计

§3 的 native filters 含三个 train-only 阈值：`basic liquidity floor`、`trading continuity floor`、`volatility sanity floor / cap`。这些阈值本身就是参数，且直接决定 denominator 形状、base rate 和所有下游 uplift。它们与 discussion2 §17.5 警告的 tokenization 阈值是同类过拟合入口；更重要的是，12A7g 的 active band 正是死在 universe 定义层的 `volatility_reconciliation_fail`——**universe 定义不稳，则下游一切 separability 都不可信**。

因此 13A preflight 必须：

```text
1. requirement 只冻结 liquidity / continuity / volatility floor 与 cap 的
   计算规则、候选分位点、tie-breaking 和审计字段;
   实际 frozen threshold values 由 train split 一次性计算,
   写入 native_universe_frozen_thresholds.csv / universe_definition_audit.csv,
   后续 validation / robustness 不得重调。
2. 对 native full-PIT volatility 做自洽性检查:
   qfq close-return definition、lookback completeness、reference_pos、entry_pos、
   missing/duplicate qfq rows、finite OHLCV 状态必须逐行可证明;
   不要求与 12A6c / C0 feature_matrix 做 reconciliation,
   也不把 12A7g 的 C0-side volatility_reconciliation_fail 偷渡为 Episode 13 blocker。
   若 native volatility 自身不可复现或不 PIT-safe,preflight 才判 input gate fail。
3. 产出 universe_definition_stability_audit:
   denominator 行数 / instrument 数 / instrument-month block 数 by year / board;
   floor 邻域敏感性(轻微抖动阈值时 denominator 与 base rate 的漂移幅度);
   要求漂移在预注册容差内,类似 12A7g 对 label 做的 dispersion 检查。
```

### 5.2 冻结 label 必须在 native universe 上复核可移植性

12A7g 选出的 `vol20d_kup2p0_kdn1p0_H20`（stability score 0.9003、base rate 14.88%）是在 12A7g 的 primary scope（含 regime bypass 后 431,239 行）上测的。native opportunity universe 的 denominator 与该 scope **不是同一集合**，因此 label 的 base-rate dispersion 在新分母上是否仍 eligible 是个未验证假设。

13A preflight 必须做一步廉价复核：

```text
在 native universe train split 上重算 selected label 的
  base rate 与 base-rate dispersion;
确认仍在 12A7g eligible 阈值内;
若 dispersion 在新分母上超阈,说明 "冻结 label" 已漂移,
  必须在 preflight 阶段暴露,而不是带着隐性漂移进入 cartography。
```

注意：这是**复核**，不是 retune。允许的结果只有"仍 eligible / 已漂移并 flag"，不允许借此重新挑 label。

## 6. Episode 13 的 gate

13A 不应以 “找到最高 winner rate token” 为成功。它必须用 train-frozen gate：

```text
1. input / PIT gate:
   native opportunity universe 可复现;
   selected label 可复现;
   token availability time <= reference_date close;
   next-open entry 可证明。

2. winner uplift gate:
   train selected token 在 validation / robustness 方向一致;
   winner uplift vs matched control 为正;
   AUC / rank-IC / top-decile lift 达到预注册阈值。

3. bad-side veto:
   fast_fail_uplift 不同步放大;
   lower_first_rate 不恶化;
   utility proxy after cost buffer 为正或至少显著优于 native baseline;
   morphology_collinearity_check 有明确标注(见 §3.1):
     胜出 token 若与 reversal / drawdown / C0-like morphology anchors 高度共线,
     标记为 morphology_rediscovery_suspect 并强制双尾复核;
     是否降级由 fast_fail_uplift / lower_first_rate / utility_proxy 决定,
     不由共线性单独决定。

4. stability gate:
   by year / board / regime 不集中在单一切片;
   instrument-month block bootstrap 后仍站得住。

5. search-control gate:
   真实 token grid size 进入 FDR / deflated metric;
   validation / robustness readout-only。

6. deployability gate (吸收 12A7g 真正卡死 C0 的教训,但不照搬 stage-2 recall floor):
   12A7g 的教训是 C0 不死在 entry 可分性,而死在 deployable stage-2:
   可部署决策点上 separability 消失、utility 转负、recall 塌缩到 0.2474。
   §6.2-§6.4 的 uplift 全在 cartography 发现层,不足以证明可部署。因此:

   token 必须在 next-open executable 决策点上重测,uplift 不得塌缩;
   min_support / captured_positive_n 必须达到预注册 floor,
     防止 niche token 只有高条件率但捕获正例太少;
   不用单一 recall_vs_native_baseline floor 否决 token,
     因为 event mining 本来就是筛选子集,高质量 niche event 可以低 recall;
   必须报告 precision-recall frontier vs native baseline:
     coverage_share, captured_positive_n, captured_positive_share,
     winner_rate, lift, utility_proxy_per_entry, utility_proxy_total_indexed;
   utility per horizon after cost buffer 或 total indexed utility 必须为正,
     或在预注册置信区间下显著优于 native baseline(不得只报条件率);
   precision / recall / coverage tradeoff 必须显式报告,
     禁止用 post-hoc / survivor-conditional 条件率冒充可部署 edge。

   deployability gate 不过,则 token 仅作 diagnostic,不得进入 §6 后续 sequence 授权。
```

说明：第 6 条是把 discussion2 §13 / §15.2 的 recall 记账和 12A7g 最贵的失败教训正式写进 Episode 13 的预注册闸门，但它不要求 Episode 13 复刻 C0 defense / stage-2 的 recall floor。Episode 13 可以发现低 coverage、高效用的 niche event；前提是它必须清楚报告捕获正例数、coverage、utility total，以及 bad-side 是否同步放大。

只有 13A 通过（含 deployability gate），才启动：

```text
requirement_13b_train_frozen_event_sequence_mining.md
```

## 7. 对 12 的最终定位

Episode 12 的价值不是失败，而是把错误路线裁掉：

```text
1. C0 不是主 winner selector。
2. Defense / participation 仍有研究价值，但不是 winner discovery engine。
3. Vol-scaled label panel 是后续 episode 可复用的 outcome layer。
4. Full PIT native event discovery 应该作为新 episode 重开，而不是在 C0 体系里继续修。
```

因此，后续文档命名和目录应明确切断：

```text
Do:
  Episode 13 / full-PIT native event discovery

Do not:
  12A7h C0 event cartography
  12A8 C0 selector repair
  12-series reverse mining continuation
```

这能避免把 Episode 13 的全 universe 发现任务继续背上 C0 的历史假设。
