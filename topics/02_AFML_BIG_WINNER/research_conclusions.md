# 02_AFML_BIG_WINNER 研究结论

生成日期：2026-06-30

本文档是 `research_log.md` 的对应结论版。它不重复完整时间线，只沉淀截至 Episode 16 可以成立、不能成立、以及后续研究应遵守的边界。

完整时间线见 `research_log.md`。

## 1. 总裁决

截至 Episode 16：

```text
deployable_strategy_found = false
completed_experiment_count = 0
production_signal_authorized = false
live_trading_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
continuation_as_action_mainline_closed = true
```

最短结论：Big Winner 研究已经反复证明存在 lifecycle、repair、risk、survival 相关信号；但还没有证明这些信号能在 OOS、after-cost、full-denominator 口径下稳定转化为正 utility。当前不能部署交易策略，也不应继续在已关闭的 continuation-as-action 主线上补丁式推进。

## 2. 可以成立的结论

### C1. Big Winner 更像 episode lifecycle，不是稠密 stock-day 标签

02 的反向画像显示，大赢家不是低点日某个单因子的直接结果，而是 post-low repair、rank persistence、continuation 的路径现象。S3 `repair_rank_persistence` 与 S6 `continuation_discriminator` 是多次复现的强结构。

对应影响：研究应保留事件、episode、阶段标签和 path context，不应回退到简单的每日 winner classification。

### C2. "买低点" 不成立，repair/confirmation 才是合理入口语义

02/03 共同说明，low-day leading factors 弱，EMA60 reclaim 虽可观察但 false-repair 很高。03 的 observable anchor event contract 没能通过 false-repair-excluded match coverage 和 forward20 edge。

对应影响：任何未来 entry idea 都必须先处理 false repair，而不是只找 rebound/reclaim。

### C3. E1 是 repair candidate backbone，但只是候选生成器

07 证明 E1 单通道几乎覆盖 full union 的 before-first recall，且密度显著更低。E2/E6 的 incremental recall 不足，不能当主通道。

对应影响：E1 可以作为候选或上游上下文，但不能直接被称为 alpha 或 entry。

### C4. Risk_on recall source 存在，瓶颈是 cost/fast-fail/false-repair sorting

08 的 R-core/R6 在 risk_on 下提供了强 recall source，R-core risk_on post-replay recall 在 train/robustness 达到 98.2%/94.5%。但密度和成本过高，cost rejector 虽有 OOS AUC/lift，frontier 仍太窄。

对应影响：后续若回到 risk_on，应该研究 payoff/state 表征和 cost-safe retention，而不是继续扩 recall。

### C5. 10B fast-fail structural gate 是保留价值最高的防守组件

10B 的 `keep_9400` structural gate 捕捉 fast-fail，有 source-caveated 支持；validation/robustness 没有严重反转。它不是生产策略，但比 10C false-repair gate 更接近可用的 risk-defense building block。

对应影响：可把 10B 作为风险防守参考组件或 future baseline，不应把 10C 当成 winner-safe gate。

### C6. 简单低波/防守 backbone 比复杂 C0/stage 模型更稳

12A7/12A7b 证明复杂模型和两阶段链路没有战胜简单规则。`volatility_20d` ascending 的 simple backbone 在 fast-fail defense 上有稳健效果，X=0.30 对 downside 最优但会压制 winner participation，X=0.20 在 fast-fail penalty 下更保守。

对应影响：防守信号优先考虑简单、可迁移、rank-based operating point；复杂 stage-2 continuation 不应继续包装为可部署 selector。

### C7. Fixed 120d winner label 确实 censor slow winners

15A 证明 fixed 120d 对慢 winner path 有严重 right-censoring。up50 train path winner rate 60%，fixed120 仅 16.28%，大量 winner 超过 120d 才完成路径。

对应影响：旧 fixed horizon winner label 有明显标签偏差。未来研究若涉及终局 winner，必须处理 censoring。

### C8. Sequential sampling discipline 是必要且成功的

16A 证明 anchor row 严重高估有效样本数。h20 train anchor 57,524 最终只有 20,245 个完整 non-overlap labelable steps；robustness anchor-to-full-horizon ratio 达 4.5280。

对应影响：后续任何持有中/序贯研究都必须使用 non-overlap time-blocked steps 与 episode-cluster discipline，不能把 anchor 当独立样本。

### C9. 持有中 survival/drawdown-risk 可分性是真实的

16C 的 robustness AUC 0.672220，PR-AUC lift 0.099183；16D 的 robustness defense precision 49.37%，相对 negative base rate 28.10% 的 lift 为 +21.27pp。剔除 known-failed context 后 robustness AUC 仍有 0.688768。

对应影响：持有中状态确实包含 survival / negative-risk 信息。这个信号可以作为 diagnostic risk state，但不能直接等同于 action policy。

### C10. 16E 的失败不是因为没有规避 drawdown

16E 中 defended-negative drawdown avoided mean 在 robustness 为 0.164024，drawdown avoidance gate 通过。失败来自 payoff/return utility：robustness defended positive opportunity cost `-32.499665`，defended negative gain `+15.693211`，defended neutral gain `+3.005729`，全分母 net `-13.800725`。

对应影响：风险降低不等于 utility 为正。AFML 决策必须同时核算 positive sacrifice、negative avoidance、neutral distribution 和 continued-negative leakage。

### C11. Survival probability 与 realized payoff magnitude 在 OOS 上解耦

16E-postmortem 显示 robustness 中 survival base rate 随 score 从 D1 到 D10 上升，但 realized h20 return 不单调，score-decile payoff Spearman 只有 0.030303。D5 mean continue return 达峰，D10 反而回落。

对应影响：不能把 survival score 当成 payoff-maximizing continuation score。也不能通过调 threshold、加 overlay、改名 participation filter 来绕过这个断裂。

### C12. Payoff-aligned target 目前也没有足够 OOS rank separability

16X 给 payoff target 一次干净预检：feature contract、lineage、power、search accounting 全通过。但 robustness payoff rank IC 只有 0.051877，低于 0.06 floor；decile monotonicity Spearman 0.163636；payoff probe 没有优于 survival probe，margin 为 -0.000723。

对应影响：不能启动 16B2 payoff-aligned continuation label redesign。问题不在旧 target 名称，而在当前 t0 feature contract 对 payoff magnitude 的 OOS 表征不足。

## 3. 被否定或关闭的路径

### P1. 直接从 low/reclaim/anchor 入场

关闭依据：02 low-day factor 弱；03 observable anchor event contract sample blocked；04/07 candidate pools recall 尚可但 precision/false repair 未解决。

当前状态：不支持。

### P2. 用更多 recall source 解决问题

关闭依据：04、07、08、12A0/A1 多次显示 recall 可以提高，但密度、precision、cost 和 utility 不跟随改善。

当前状态：不应作为主攻方向。

### P3. Transition regime 主线

关闭依据：08 F/G/I 显示 transition residual label 不稳定，previous-regime context OOS 不增益。

当前状态：冻结。

### P4. False-repair feature rejector 作为 winner-safe gate

关闭依据：10C train 有 false-repair/exposure lift，但 E1-missed retention 低于 gate，validation retention collapse。

当前状态：10C 可作为 feature source，不作为 gate。

### P5. T0 archetype payoff/risk screen

关闭依据：11A1 的 8 个 t0 proxies 无一通过 robust payoff/risk screen；P4/P6 winner uplift 同时伴随 failure uplift。

当前状态：不支持。

### P6. C0 state-change backbone / winner selector

关闭依据：12A3 precision 低；12A4 meta-label 未达 gate；12A7g 判定 baserate only not separable。

当前状态：C0 只保留为 feature source 或 defense/participation context。

### P7. Full-PIT native token/event mining

关闭依据：13A/13A2/13A3/13C/13E/13F/13G 均没有产生 utility-positive or robust OOS deployable path。

当前状态：不支持继续在同一形态上扩挖。

### P8. Sparse state-change event utility

关闭依据：14A same-event 50bps utility gate fail，14C rank monotonicity stress not supported。

当前状态：不授权后续 confirmatory defense overlay。

### P9. Path-defined winner shape taxonomy

关闭依据：15B taxonomy 不稳定；15C PIT-observable phase 不优于 random；15C2 sharpness 不超过 cluster-blocked baseline。

当前状态：不支持用 t0 预测离散 winner shape。

### P10. Sequential continuation-as-action

关闭依据：16E utility fail；16E-postmortem directionality fail；16X payoff precheck fail。

当前状态：主线关闭，`next_allowed_requirement = none`。

## 4. 当前最可信的组件清单

这些组件有研究价值，但都不是 production signal。

| 组件 | 当前用途 | 边界 |
| --- | --- | --- |
| PIT largecap / top-N proxy 数据地基 | 后续研究分母 | top-N 有 available-source caveat |
| S3 repair rank persistence | lifecycle 结构证据 | 不是独立 entry |
| E1 repair candidate backbone | candidate generation / context | recall 高但 precision/utility 未过 |
| R-core/R6 risk_on recall source | recall benchmark / source pool | 密度和成本重 |
| 10B fast-fail structural gate | source-caveated defense baseline | 非 production，需重新验证部署口径 |
| `volatility_20d` simple defense backbone | fast-fail defense / participation throttle | downside 优先，不是 winner selector |
| 16C survival score | holding-state diagnostic risk signal | 不能直接作为 action score |
| 16D bottom-score defense bucket | negative-risk enrichment evidence | 16E 证明 action utility 不支持 |

## 5. 禁止外推的说法

以下说法不被当前研究支持：

- "已经找到了 big winner 交易策略。"
- "E1/R-core/C0 可以直接入场。"
- "risk_on 本身解释 winner，或者只要 risk_on 就能交易。"
- "10B/10C 是生产级风控或止损规则。"
- "低波规则可以选 winner。"
- "path-defined winner label 解决了 winner 预测问题。"
- "16C AUC 通过，所以 continuation policy 可用。"
- "16D 能捕捉 negative，所以 defend action 有正收益。"
- "16E 只是成本太高，0bps 就能过。"
- "16X bootstrap CI 排除 0，所以 payoff label 重做应启动。"

## 6. 研究失败的共同模式

01-16 中反复出现同一个结构：

```text
recall / probability / risk separability exists
-> threshold or policy can enrich some target class
-> OOS payoff magnitude or utility ordering does not hold
-> after-cost/full-denominator decision fails
```

这说明主问题已经不是 "能不能发现事件" 或 "能不能找到某种分类信号"，而是：

```text
当前 t0 或 event-time observable state 是否能稳定排序 future payoff magnitude / net utility?
```

截至 16X，答案仍是否定或不足。

## 7. 后续研究方向建议

后续不应继续沿 16 的 continuation-as-action 主线追加 16F、16B2 或 A/B/C 修补。更合理的 topic-level 方向是：

1. 回到更上游的 entry alpha，而不是在持有中 survival score 上寻找 payoff utility。
2. 重新定义 payoff-state 表征：特征需要解释收益幅度和厚尾 upside，而不只是 survival / drawdown 0/1。
3. 将 10B、`volatility_20d` 等防守组件作为 separate risk-control candidates，而不是混入 winner selector。
4. 用 non-overlap / episode-cluster discipline 作为默认统计单元，避免 anchor-level 功效幻觉。
5. 所有新方向必须预先声明 full-denominator utility、positive sacrifice、negative leakage、neutral handling、cost/delay stress、validation non-selection。

如果只允许一句研究方向：

```text
停止追加 recall 和 continuation threshold 搜索，转向可 OOS 迁移的 payoff magnitude state 表征；防守信号与 winner selection 分离评估。
```

## 8. 最终结论

02_AFML_BIG_WINNER 到 Episode 16 的价值不是找到一个可交易策略，而是把大量看似有希望的路径系统性排除，并收敛出一个更清晰的问题边界：

Big Winner 的 lifecycle、repair、survival 和 fast-fail 风险并非随机；但当前研究尚未找到能稳定捕捉 winner payoff magnitude、同时不牺牲过多 right-tail upside 的 OOS action surface。后续研究必须从 payoff/utility 排序问题重新出发，而不是把已有 probability/risk signal 包装成交易动作。
