# AFML Big Winner 下一轮研究方向讨论

## 0. 定位

本文基于 2026-06-14 的研究方向讨论、`README.md` 的项目约束，以及 08 全实验最终报告形成下一轮研究路线。它不是新的实验结果，也不是 requirement；它用于把 08 之后的工作从多条平行想法收敛成一条可执行研究链路。

当前最重要的判断是：下一轮不要再把后续实验拆成“regime、primary model、feature engineering”三条平行线，而应收敛为一条顺序明确的链路：

```text
fast-fail label 重定义
    ↓
feature / stationary / importance 基础建设
    ↓
risk_on cost-rejector / failure primary model uplift
    ↓
risk_off E1 failure model baseline
    ↓
transition 暂停，只做诊断
```

这与 08 总报告的综合判断一致：`risk_on` 已经有足够 recall source，真正瓶颈是 cost / fast-fail / false-repair 排序质量；`transition` 在当前 residual label 下不应继续 family rediscovery。

## 1. 从 08 继承的边界

08 的最终结论不是“找不到信号”，而是把问题拆清楚了：

1. E1 继续是 sparse backbone，不应被移除。
2. R-core / R6 是 `risk_on` cost rejector 的主要 recall source。
3. T4 / T7 降级为 negative control / context tag，不是 transition recall backbone。
4. R-series deterministic compression 已被证伪为主线。
5. `risk_on` 的当前问题是 cost sorting 还差一点，不是 recall source 不足。
6. `transition` 的当前问题是 residual bucket / state stability，不是缺少一个新的 event family。

Experiment E/H 已证明 `risk_on` cost rejector 有稳定 OOS signal，但尚未过 research-entry。H 的关键边界非常窄：

```text
keep_0800:
    train any recall = 90.0452%，通过 90% gate
    train cost reduction = 14.1389%，距离 15% 差 0.8611pp

keep_0775:
    train cost reduction = 15.3452%，通过 15% gate
    train any recall = 89.1403%，距离 90% 差 0.8597pp
```

这说明下一步不是继续调 keep fraction、放宽 gate 或复用 robustness-best threshold，而是提升 `0.775-0.800` 附近的局部排序质量，或者重新构造 `cost_bad_10_20` target，使同一个 train-only threshold 同时保留 recall 与降低 cost。

这里必须加一个前置 caveat：H 的 `0.775-0.800` frontier 是旧 `cost_bad_10_20` target 下的锚点。如果 R09 重新定义 `failure_10` 或 `cost_bad_10_20`，H 的 cost reduction / recall tradeoff 不能被直接当成新 target 下的 research-entry gate。R09 必须输出新旧 cost target 的桥接表，R11 的 gate 必须基于选定的新 target 重新预声明。

## 2. 直接吸收的建议

### 2.1 三个想法应串联，不应并行

原来的三个想法：

```text
1. regime 分工
2. primary model / failure_10
3. feature sets / stationary / PCA
```

不应拆成三条实验线。更合理的关系是：

```text
regime 决定实验对象
feature / target construction 决定 primary model 能否提升
primary model 是最终交付
```

因此下一轮主线不应写成：

```text
做 regime
做 feature
做 primary model
```

而应写成：

```text
做 risk_on fast-fail primary model 的 feature / target uplift
```

`regime` 在这里不是独立研究主线，而是决定先做 `risk_on`，暂缓 `risk_off`，冻结 `transition`。

### 2.2 先重定义 fast-fail label，再训练模型

当前 `failure_10 = -10% drawdown barrier` 可能过硬，更像 severe failure，不一定是 10D fast-fail 的最佳定义。README 对 `failure_10` 的定义本来就不是固定 -10%，而是：

```text
failure_10 = 1 if, within 10 trading days after trade_time,
    a configured lower barrier, drawdown barrier, episode-start low break,
    or structural support break is touched before any configured confirmation
    or upper barrier condition.
```

阈值必须在实验前配置冻结，不能从全样本事后推导。因此 R09 应先做纯 label diagnostic，不训练模型。

候选 label frontier 至少包括：

```text
fixed MAE10:
    -5%, -8%, -10%, -12%
    -6% 只作为 sensitivity，若与 -5% / -8% 高度重合则不进入 R11

vol-scaled barrier:
    -1.0 sigma, -1.5 sigma, -2.0 sigma

ATR-scaled barrier:
    -1.5 ATR, -2.0 ATR

structure barrier:
    break event low
    break recent swing low
    break EMA20
    break EMA60

hybrid:
    fast-fail_10d OR false-repair_20d
```

每个 label 至少评估以下指标：

```text
fast-fail rate
winner recall retention
kill-wrong rate = P(winner_120 = 1 | fast_fail = 1)
winner-injury rate = P(fast_fail = 1 | winner_120 = 1)
被杀 winner 的 t0 -> fast-fail touch drawdown / MAE 分布
与旧 cost_bad_10_20 的 overlap / confusion matrix
```

`wrong-kill` 不能只用一个比例概括。`winner_120` 是 120d right-tail readout，`failure_10` 是 10d path label；一个事件可以先触及 10d lower barrier，后续又成为 120d winner。这里不能简单把它判成“标签错”。必须同时看 `P(winner | fast_fail)` 和 `P(fast_fail | winner)`，并报告被杀 winner 在 fast-fail touch 点的 drawdown 深度，区分可接受洗盘与真实不可承受回撤。

`failure_10` 的目标不是单纯减少失败，因为不交易就没有失败。正确目标仍是 README 中的 failure filter 目标：

```text
minimize accepted failure_10 rate
subject to retaining enough big-winner recall
```

### 2.3 transition 先冻结

08 已经给出明确结论：当前 `transition` 不是稳定第三态。它是 risk_on / risk_off 以外的 residual bucket，继续找 T6/T8/VCP/volatility family，容易把 regime composition、短 transition segment 和 future outcome 混成伪 alpha。

因此当前不要做：

```text
transition primary model
transition-specific family rediscovery
transition ranker compression
previous-regime context 直接并入 risk_on cost rejector
```

transition 只保留为 diagnostic 和 regime label redesign notes。若未来要重启，必须先扩展样本跨度，或者重定义一个正向、PIT、跨 split 可复现的 regime label。

同样要注意：即使本轮主线只做 `risk_on`，也不能假设 regime label 本身天然可靠。08 G 已经暴露 published / reconstructed transition 有明显漂移；R09 必须先做 `regime_label_pit_audit`，确认 `risk_on` 标注在 t0 完全可见、可重构，并且 train / validation / robustness 的重构一致率达标。否则所有 regime-specific readout 都会建立在不稳的分组上。

### 2.4 不再调 keep fraction，而是提升排序质量

Experiment E/H 的信息含量在于：模型不是没有 OOS signal，而是同一个 train-only threshold 不能同时过 cost 与 recall。

H 修补工程契约后仍得到稳定排序读数：

```text
robustness ROC-AUC ≈ 0.6858
robustness PR-AUC ≈ 0.5239
robustness top-decile lift ≈ 2.0307
```

失败点不是 feature leakage、label join、as-of join 或 denominator 对账，而是 `keep_0800` 与 `keep_0775` 之间的局部 frontier。下一步必须提升该局部区域的排序质量，而不是继续在阈值上做文章。

## 3. 吸收但需要修正的建议

### 3.1 “不同 regime 不同 primary model”先降级

“不同 regime 对应不同 primary model”方向上可以理解，但现在直接做三套模型风险太高。更稳妥的拆法是：

```text
risk_on:
    主线模型，R-core / R6 source

risk_off:
    E1 baseline + failure audit
    暂不重投入

transition:
    diagnostic only
```

阶段顺序：

```text
第一阶段：
    不做三套模型，先做 risk_on cost-rejector uplift

第二阶段：
    risk_off 单独做 E1 failure_10 baseline

第三阶段：
    transition 等 regime label 重定义后再说
```

原因是 08 已经证明 `risk_on` 和 `transition` 不是同一种问题。`risk_on` 是 recall source 充分但 cost sorting 还差一点；`transition` 是 label / state stability 问题。

### 3.2 fracdiff 是增强项，不是第一主线

README 中 fracdiff 的定位很清楚：只用于 selected memory-bearing continuous series，例如：

```text
log(close / industry_index)
log(close / market_index)
log(industry / market)
log(amount)
VWAP-related series
```

不要盲目应用到：

```text
returns
ranks
event dummies
labels
```

对于 10D fast-fail model，更优先的 feature hygiene 是：

```text
rolling z-score
rolling percentile
ATR normalization
sigma normalization
distance / range / volatility / flow / basis / stop-distance feature
```

因此 R10 的原则是：

```text
stationary hygiene 必做
rolling z / percentile / ATR normalization 是主流程
fracdiff 只用于 selected continuous series 的增强项
```

### 3.3 PCA 不作为主力 selector

PCA 可以做，但不应成为主降维方法。README 对 feature importance 的优先级是：

```text
feature family grouping
SFI
MDA
group MDA
clustered importance
avoid full-sample feature selection leakage
```

因此 R10 主线应采用：

```text
feature family ablation
group MDA
clustered feature importance
representative feature selection
```

PCA 只能作为 sanity check 或 family 内对照：

```text
family 内 PCA
train-fold fit
validation / robustness transform
和 raw / representative features 对照
```

不要做：

```text
全局 PCA
先 PCA 再解释模型
full-sample PCA / selection
```

## 4. 不建议吸收的部分

### 4.1 不要现在推进 transition 模型

当前 transition 不是“不够努力”，而是定义本身不稳。08 证据显示：

- transition taxonomy 不稳定。
- previous-regime context 不能稳定排序。
- transition robustness 有效独立 segment 太少。
- OOS 上 no-context cost rejector 强于 prev-context。

因此不要在下一轮做：

```text
transition primary model
transition cost rejector
transition feature uplift
```

除非先完成 regime label redesign。

### 4.2 不要先做 risk_off-heavy 主线

`risk_off` / E1 可以做 baseline，但不应抢主线资源。当前最值得投入的是 `risk_on` cost-rejector uplift，而不是新的 transition family search，也不是回到全局 E1 大模型。

`risk_off` 应作为第四步 R12，先建立 E1 failure baseline，后续再考虑和 `risk_on` 汇总到 regime-aware sizing framework。

### 4.3 不要把 feature set 实验做成大网格

下一轮要控制实验规模。不要做：

```text
多 targets × 多 feature sets × 多 stationary × PCA × 多模型 × 多阈值
```

这会变成新的 validation overfit。R09 只扫 label，不训练大模型；R10 做 feature foundation 和 importance；R11 才用冻结 label 与 feature set 训练少量模型。

## 5. 推荐实验排序

### R09：Fast-Fail Barrier Diagnostic

定位：第一步，纯 label diagnostic，不训练模型。

建议实验名：

```text
09A_fast_fail_label_frontier
```

目标：

```text
重定义 failure_10 / cost_bad_10_20
```

输入：

```text
risk_on R-core / R6
risk_off E1 作为辅助 baseline
```

核心输出：

```text
regime_label_pit_audit.md
fast_fail_label_frontier.md
fast_fail_label_contract.md
cost_target_bridge.csv
label_pairwise_agreement.csv
label_mechanism_contract.csv
```

核心表：

| label | prevalence | winner retention | kill-wrong | winner-injury | old target overlap | split stability |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |

`regime_label_pit_audit.md` 是 R09 的第一项前置检查。它必须确认 `risk_on` 标注在 t0 完全可见，并按 G 的思路报告 published / reconstructed regime 的一致率、drift cell、future-row join count 与 split-level consistency。若 `risk_on` 标注不可重构或 robustness 漂移过大，R09/R11 的 regime-specific 结论必须降级为 diagnostic。

`cost_target_bridge.csv` 是 R09 的硬产物。它必须在同一事件集上比较旧 `cost_bad_10_20` 与每个候选新 label，至少报告：

```text
old_positive / new_positive confusion matrix
Jaccard overlap
old-only / new-only share
winner_120 rate by bridge cell
fast-fail / false-repair component contribution
```

R11 不得把 H 的旧 target `14.1389% / 89.1403%` frontier 直接当作新 target 的 gate。选定新 target 后，R11 必须重新冻结 cost reduction、recall retention、E1-missed retention 与 robustness readout gate，并在报告中注明不可与 H 旧 target 逐点直接比较。

`label_pairwise_agreement.csv` 用来防止 R09 选择两个几乎等价的 label 进入 R11。至少报告 Jaccard、Cohen's kappa、positive-set overlap、winner-injury 差异。进入 R11 的 1-2 个 label 应来自不同机制族，例如一个 vol / ATR-scaled label 加一个 structural label；除非相邻 fixed percentage label 在 split stability 或 wrong-kill 上有明确差异，否则不应同时进入 R11。

`label_mechanism_contract.csv` 记录每个 structural label 使用的 series 和计算方式，例如 event low、swing low、EMA20、EMA60。这个产物要被 R10 读取，用于标记 feature-label mechanism overlap。若 R09 的 label 和 R10 的 feature 共享同一均线或同一 swing source，R11 必须单独报告这组特征的 leakage-aware ablation，不能把可分性直接解释成泛化 alpha。

候选 label：

```text
fixed MAE10: -5 / -8 / -10 / -12%，-6 只作为 sensitivity
vol-scaled: -1 sigma / -1.5 sigma / -2 sigma
ATR-scaled: -1.5 ATR / -2 ATR
structure fail: event low / swing low / EMA20 / EMA60 break
hybrid: fast-fail_10d OR false-repair_20d
```

R09 结束后必须冻结 label contract。每个后续实验消费 label 前，必须在 config 中冻结：

```text
t0
trade_time
t1
barrier definition
price field and adjustment policy
same-bar tie handling
censoring policy
label end timestamp for purged CV
旧 target 对账规则
false_repair horizon
```

### R10：Feature Foundation / Stationary / Importance

定位：第二步，构建 t0 可见、稳定、可审计的 feature set v1，不急着训练最终模型。

建议实验名：

```text
09B_feature_foundation_ablation
```

主要 feature family：

```text
FS0 baseline existing H features
FS1 event intrinsic / family flags / event score
FS2 basis / path quality
FS3 volatility / range / stop-distance SDF
FS4 amount / volume / VWAP / DIB
FS5 market / industry / risk_on quality
FS6 recurrence / local density up to t0
```

必须做：

```text
rolling z / percentile
ATR / sigma normalization
selected fracdiff only
10D label uniqueness / sample weights
feature family ablation
group MDA / clustered importance
label-mechanism overlap audit
```

禁止做：

```text
future features
post-event volume
label-derived features
full-sample feature selection
full-sample scaling / PCA / threshold tuning
```

R10 的交付不是“模型过 gate”，而是：

```text
feature_contract.md
feature_stationarity_audit.csv
sample_uniqueness_weights.parquet
feature_family_ablation.csv
group_mda_importance.csv
clustered_importance_report.md
label_mechanism_overlap_audit.csv
```

`sample_uniqueness_weights.parquet` 是 R10 的冻结产物，不是各模型临时重算的辅助文件。R10 的 feature importance、group MDA、clustered importance，以及 R11 的模型训练 / weighted loss / sequential bootstrap 必须引用同一份 sample weight。这样可以避免 R gated 事件在 episode 内密集重复触发时，importance 和模型训练使用两套不一致的样本权重。

`label_mechanism_overlap_audit.csv` 必须列出每个 feature family 与 R09 selected label 的机制重叠，例如：

```text
feature uses EMA60 distance
label uses EMA60 break
feature uses swing-low distance
label uses swing-low break
feature uses ATR / sigma
label uses ATR / sigma barrier
```

这些 overlap 不自动 forbidden，但 R11 必须在 ablation 和解释中单独标注。否则模型可能只是在学习 label 的同机制 proxy，而不是稳定的成本排序能力。

### R11：Risk-on Cost Rejector / Failure Primary Uplift v2

定位：第三步，才训练模型。

建议实验名：

```text
09C_riskon_cost_rejector_uplift
```

目标：

```text
用 R09 新 label + R10 新 feature
把 H 的 0.775-0.800 frontier 推过 research-entry
```

模型数量要控制：

```text
logistic / elastic net
random forest or bagging shallow trees
shallow LightGBM
```

除模型族外，R11 必须显式测试 train-fold calibration，而不是只换分类器：

```text
Platt / logistic calibration
isotonic calibration
calibration fit inside train fold only
calibration before/after frontier readout around keep_0800
```

对于有明确经济方向的特征，例如 drawdown、stop-distance、ATR-normalized distance、volatility shock，也可以设置 monotonic constraint 或 monotonic sanity check。单调约束不是为了追求更高 AUC，而是为了提升 `0.775-0.800` 附近的局部排序稳定性。

核心 gate：

```text
train-only threshold selection
validation / robustness only readout
cost before/after 使用同一 horizon-complete denominator
no future leakage
R10 frozen uniqueness weights reused
E1-missed retention
bridge retention
density / concentration cap predeclared
```

R11 的核心判定不是最高 AUC，而是同一 train-selected threshold 是否同时满足：

```text
train cost reduction >= frozen threshold
train any recall retention >= frozen threshold
train E1-missed retention >= frozen threshold
validation / robustness 不反转
density / concentration / leakage audit pass
```

R11 还应顺手跑一个 `risk_off` read-only 对照：使用同一 selected feature pipeline / model family / threshold policy，在 risk_off E1 或 risk_off available sample 上只输出 readout，不调参、不进 gate。这个对照用于回答 R11 的 uplift 是否真是 `risk_on` 特异，还是更通用的 feature / target construction 改善。它不改变 R11 的主结论，也不提前启动 R12。

### R12：Risk-off E1 Failure Model Baseline

定位：第四步，再做 risk_off。

建议实验名：

```text
12_riskoff_e1_failure_model_baseline
```

目标：

```text
确认 E1 sparse backbone 在 risk_off 下能否通过 failure_10 gate 降低 fast-fail，同时保留 winner recall
```

R12 不一定要马上 research-entry。它先建立：

```text
risk_off E1 failure baseline
```

后续如果 risk_on / risk_off 都有稳定 failure model，再考虑合并为：

```text
shared feature pipeline
regime-specific threshold / calibration
regime-aware sizing framework
```

### Transition：Frozen Diagnostic

transition 当前只保留：

```text
transition outcome diagnostic
transition label redesign notes
regime definition redesign
```

不进入 modeling，不作为 R09-R11 的训练 scope。

## 6. 三个拍板问题

### Q1：fast-fail 重定义扫哪些？

建议三类都扫：

```text
fixed percentage
vol / ATR-scaled
structural break
```

但只在 R09 label diagnostic 中扫，不要拿每个 label 都训练一轮大模型。通过：

```text
kill-wrong = P(winner_120 = 1 | fast_fail = 1)
winner-injury = P(fast_fail = 1 | winner_120 = 1)
winner recall retention
被杀 winner 的 fast-fail touch drawdown 深度
label pairwise agreement / split stability
```

选出 1-2 个 label 进入 R11。

### Q2：模型形态是两个独立模型，还是单模型 + regime condition？

当前建议：

```text
下一步只做 risk_on model
risk_off 先做 baseline
transition 不做
```

未来如果合并，优先采用：

```text
shared feature pipeline
regime-specific threshold / calibration
必要时再拆模型
```

不要从一开始就三套模型。

### Q3：PCA 要不要当降维选择器？

建议：

```text
不当主选择器
```

主线：

```text
stationary hygiene
feature family ablation
group MDA / clustered importance
representative features
```

PCA：

```text
只做 family-level sanity check
不做全局降维主流程
```

## 7. 下一轮主实验命名

建议把下一轮主实验命名为：

```text
09_riskon_fastfail_label_feature_uplift
```

它包含三个子阶段：

```text
09A_fast_fail_label_frontier
09B_feature_foundation_ablation
09C_riskon_cost_rejector_uplift
```

如果这条线过了，再考虑：

```text
12_riskoff_e1_failure_model_baseline
confirm_20 ranking
bet sizing
exit / synthetic path stress
```

现在最不该做的是：

```text
继续调 keep threshold
继续找 transition family
继续堆 PCA / feature 大网格
直接做 full entry backtest
```

这些都会把 08 已经拆开的几个问题重新揉在一起。

## 8. 一句话结论

下一轮不要再找新 source，也不要继续 transition；先重定义 fast-fail label，再构建稳定的 t0 feature foundation，最后集中把 `risk_on` R-core/R6 的 cost rejector 从“有 OOS 信号但没过 research-entry”推过那条很窄的 cost/recall frontier。
