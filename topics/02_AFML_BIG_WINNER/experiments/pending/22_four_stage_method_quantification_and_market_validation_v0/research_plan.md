# Episode 22 Research Plan：四阶段交易方法的可量化拆解与真实市场验证

> 文档状态：`draft_research_plan`
>
> 生成日期：2026-07-23
>
> Episode ID：`22_four_stage_method_quantification_and_market_validation_v0`
>
> 方法来源：仓库内直接来源 artifact [`【音频】投资高手白云居士李永顺：盈利1 4亿的交易心路.srt`](./【音频】投资高手白云居士李永顺：盈利1 4亿的交易心路.srt)
>
> 来源角色：`practitioner_narrative_design_hypothesis`
>
> 来源 SHA256：`a539fc184f0386e5365a7e3fc60f9bbf56d23923a73f613636cfa5c9d83232e2`
>
> 业绩声明：不独立核验“14 亿元盈利/收入”的真实性、归属、时间范围或统计口径
>
> 数据基线：EP19 PIT universe / tradability contract；项目 benchmark 与 qfq OHLCV 数据；它们是 baseline，不是 EP22 数据上限
>
> 启动性质：`topic_level_exploratory_data_discovery_for_component_quantification_and_market_validation`
>
> 探索治理：`routine_local_exploration_requires_manual_stage_authorization = false`
>
> 正式边界：`formal_forward_freeze_or_deployment_requires_separate_explicit_authorization = true`
>
> 本 Episode 第一份预期需求：`requirement_22a_source_data_availability_and_validation_contract.md`

## 0. 一页结论

EP22 不建设完整决策路由器，不训练一个把所有叙事揉在一起的“大模型”，也不尝试直接复制原交易者的完整操作体系。

EP22 只回答：

> **字幕分析中每一部分究竟能否被定义成可观测、PIT-valid、可证伪的量化命题；这些命题放到真实 A 股市场数据中后，
> 是稳定成立、仅有弱代理意义、被历史证伪，还是因为数据不足而不可验证？**

原方法按四个阶段叙述，但可量化内容拆成六个相互独立的验证模块：

| 模块 | 对应原方法 | EP22 验证对象 |
|---|---|---|
| M1 事件反应 | 短线强弱 | 市场共同价格冲击、板块/行业特异 residual 冲击，以及板块/行业“实际反应－应有反应”的异常强弱 |
| M2 情绪与持仓代理 | 情绪脉络＋博弈脉络 | 市场广度、波动、换手、拥挤等能否形成稳定的过滤状态 |
| M3 股权供给与资金需求 | 资金中脉 | IPO、增发、解禁、减持、回购、融资、ETF/基金流等真实可得数据的市场关系 |
| M4 风格价格冲击效率 | 资金流向与大小盘跷跷板 | 不同风格的收益、成交、广度、流动性和价格响应差异 |
| M5 长期价值质量 | 长期价值势能 | ROIC、现金流、盈利质量、杠杆、回购/稀释等长期变量 |
| M6 风险预算与对冲原件 | 情景＋对冲 | 波动/流动性/尾部约束是否校准；市场 beta、风格 beta 与个股残差能否被区分 |

这六个模块不是一条必须串行通过的 pipeline。22A 提供共同的数据、时点、统计和 claim contract；M1–M6 可以在同一探索
工作区内分别实现、分别迭代、分别运行、分别失败，不需要逐阶段等待人工批准：

```text
22A  source + data availability + PIT timing + estimand + validation protocol
  ├─ 22B  M1 observable-shock abnormal-reaction validation
  ├─ 22C  M2 sentiment / positioning-proxy state validation
  ├─ 22D-A/B  M3 issuer-capital-action / aggregate-demand validation
  ├─ 22E  M4 style price-impact-efficiency validation
  ├─ 22F  M5 long-horizon quality / value-potential validation
  └─ 22G-A/B  M6 risk primitives / beta decomposition / hedge-effectiveness validation
          ↓
       22H component quantifiability and market-validation atlas
```

22H 的最终产物不是仓位动作，而是一张研究地图：

```text
directly_measurable_and_historically_stable
proxy_only_but_historically_informative
measurable_but_historically_unstable_or_falsified
data_blocked
construct_invalid
forward_freeze_candidate
```

任何模块的历史正结果都不自动升级为：

```text
cross-module combination
decision router
cross-module or production position sizing
portfolio optimization
policy replay
production signal
deployment
live trading
```

本地 2017-01 至 2026-05 的历史已经被本 topic 多次观察，全部标记为
`design_contaminated_historical_real_market_evidence`。它仍然是真实市场数据，可用于：

- 判断变量能否构造；
- 证伪叙事；
- 估计效应量、稳定性、成本和统计功效；
- 冻结少量后续候选。

但它不能提供可信的最终正向 support。探索阶段允许继续改写公式、数据源、阈值、方向、horizon 和统计口径，只要每次尝试保留
可复现 checkpoint，并诚实记录 search path。只有准备把某个候选升级为正式 forward confirmation 时，才必须建立不可变 freeze，
再等待 freeze 后真实形成的 forward cohort。

因此 EP22 当前交付范围更精确地说是：

```text
historical_real_market_component_diagnosis
+ forward_freeze_preflight
```

不是 `confirmatory_forward_validation_complete`。

### 0.1 EP22 探索治理规则

EP22 固定使用项目原则 `9.8 EP22 Uses Exploratory Data-Discovery Mode`：

```text
routine_requirement_revision_allowed = true
routine_local_implementation_allowed = true
routine_historical_diagnostic_run_allowed = true
routine_ablation_and_variant_iteration_allowed = true
per_stage_human_authorization_required = false
mandatory_intermediate_seal = false
```

探索流程为：

```text
working
  -> checkpointed
  -> diagnostic_complete
  -> validated_working_result
  -> optional_formal_freeze
```

manifest、hash、stage log 和 config snapshot 用于重现与比较尝试，不是人工批准门槛。working artifact 可在 lineage 清楚、变更有记录的
情况下原位修复或重跑。PIT、防泄漏、train-only selection、denominator、multiplicity、稳定性与 claim ceiling 仍是科学约束，
不能因探索模式而取消。

本文后续的 `freeze/frozen` 默认指“在单个 attempt 内固定，避免 outcome 后改口径”，不等于 immutable seal，也不触发人工批准。
只有明确写成 `formal forward freeze` 时才表示跨 attempt 不可变的确认性合同。

探索结果允许明确裁决为 `historically_supported_in_exploration`、`historically_falsified`、`unstable`、`low_power` 或
`data_blocked`。这里的“证真”只表示冻结口径下的历史数据支持，不表示因果真理、true OOS 或 forward confirmation。

只有以下动作需要另行明确授权：正式 forward-confirmation freeze、生产部署、live trading、外部副作用或付费凭据数据获取、
破坏性修改既有 sealed bundle，以及把 EP22 扩展成跨模块决策路由或生产仓位系统。

### 0.2 数据发现是横跨所有模块的一等研究方向

EP22 不能把“当前本地没有数据”直接当作研究终点。现有 `U_project`、benchmark 与 OHLCV 只定义可复现 baseline；数据缺口本身、
哪里可以补、能否 PIT 重建、补充后是否真的有研究增量，都是本 Episode 的核心问题。

数据探索横向层：

```text
D0 gap registry
  -> D1 candidate-source discovery and public read-only acquisition
  -> D2 PIT/timestamp/revision/coverage audit
  -> D3 construct and effective-support gain
  -> D4 module-specific incremental empirical value
```

需要主动搜索的候选数据面至少包括：

- 更宽的历史 PIT eligible A 股 universe、daily tradability 与历史权重；
- genuine industry/sector index history、PIT constituent membership 与 taxonomy revisions；
- 公告/新闻精确发布时间、事件类型、修订与可用时点；
- IPO、增发、配股、解禁、减持、回购等 announcement/eligibility/execution/completion；
- ETF/基金申赎或份额、融资融券、北向/其他资金代理及其口径变化；
- as-reported 财务报表、首次公告时间、restatement lineage 与 analyst revision；
- official free float、total/listed-circulating shares 的语义与历史；
- 可交易 ETF/期货、合约、基差、换月、保证金、费率、成交与流动性；
- 集合竞价、分钟或其他可证明 first-executable timing 的数据。

数据价值必须分两层裁决：

```text
contract_usefulness:
    source 可访问、PIT 可重建、coverage 足够、construct 更接近原命题、
    effective support 增加、维护与许可可接受

empirical_usefulness:
    在模块专属 versioned attempt 中，
    相对 existing-data baseline 是否增加稳定、非泄漏、非机械的历史证据
```

可能的合法结论：

```text
source_not_found
source_available_but_not_PIT_reconstructable
source_PIT_usable_but_coverage_insufficient
source_redundant_with_existing_proxy
source_improves_construct_or_support_only
source_adds_incremental_historical_evidence
source_changes_or_falsifies_prior_interpretation
```

公开、read-only、无需新凭据或付费的数据发现、下载、缓存和 profiling 属于常规 EP22 探索。需要新凭据、付费、许可承诺或修改外部
系统时才另行请求授权。

本文后续未加限定的 `data_blocked` 默认表示“当前 source/arm 被阻断”。只有完成预注册的 public-source search budget，或确认
需要尚未批准的凭据、付费、许可后，才可把它升级为 module-level `component_data_blocked`。

---

## 1. 来源边界与研究身份

### 1.1 来源能提供什么

EP22 的直接方法来源是仓库内的
[`【音频】投资高手白云居士李永顺：盈利1 4亿的交易心路.srt`](./【音频】投资高手白云居士李永顺：盈利1 4亿的交易心路.srt)。
该文件是音频节目的文字转录 artifact，而不是二次方法还原；研究中的方法拆解、变量映射与待检验假设必须能够回溯到该字幕的
原始表述和时间戳。22A 的 `source_claim_registry` 至少必须记录以下固定身份：

```text
source_artifact_id = ep22_baiyun_lijuyshi_liyongshun_trading_journey_srt
source_artifact_path = topics/02_AFML_BIG_WINNER/experiments/pending/22_four_stage_method_quantification_and_market_validation_v0/【音频】投资高手白云居士李永顺：盈利1 4亿的交易心路.srt
source_artifact_sha256 = a539fc184f0386e5365a7e3fc60f9bbf56d23923a73f613636cfa5c9d83232e2
source_artifact_role = practitioner_narrative_design_hypothesis
```

该来源可以提供：

- 可检验的 practitioner hypothesis；
- 候选变量和作用机制；
- 需要被市场证伪的方向性判断；
- 风险与边界提醒；
- 模块拆分的研究起点。

该来源不能提供：

- 已核验的业绩；
- 完整交易记录；
- 精确仓位、成本、资金规模和 benchmark；
- 可复现的公式、参数或数据口径；
- 因果识别；
- 已被验证的交易规律。

因此 EP22 的方法身份固定为：

```text
practitioner_narrative_grounded_component_validation
```

不得写成：

```text
exact_replication
verified_14_billion_performance
verified_master_strategy
causal_investor_behavior_identification
capital_flow_accounting_identity
deployable_decision_system
```

原叙事中以下操作层内容不在六个 component validation 内，22A 的 source registry 必须逐项登记为：

```text
deferred_policy_construct_not_tested_in_EP22
```

- 短线/波段/趋势仓的具体权重；
- `t+1/t+3/t+5` 观察后的真实加减仓动作；
- 情景树概率更新与主导变量切换；
- 现金余量规则；
- 综合 risk budget；
- 个股失效退出与 hedge 的动态选择；
- 跨模块决策路由。

其中多周期只能按 Section 2.6 做 horizon association；landmark 只能按 Section 4.5 做无动作 predictive diagnostic。不得因
这两项被量化，就声称完整四阶段操作过程已覆盖。

### 1.2 “真实市场验证”的定义

EP22 中的真实市场验证必须满足：

1. 使用真实 A 股历史或 forward 市场数据，不用合成价格证明有效；
2. universe、特征、事件和状态均有 point-in-time 边界；
3. close `t` 才完整的变量，最早只能作用于下一可执行交易时点；
4. 价格、成交、公告、财务、资金或对冲数据都必须保留真实来源和时间戳；
5. 数据缺失时输出 `data_blocked`，不得用叙事或价格形态伪造数据；
6. historical association 与 true-forward support 分开；
7. 统计显著、经济显著、稳定性和可解释边界分别报告。

“真实市场验证”不等于“完成实盘回测”。M1–M6 的第一目标是检验命题本身，不是拼接交易策略。

### 1.3 与现有 Episode 的关系

EP22 是用户明确发起的 topic-level exploratory restart，不是任何现有 Episode 的机械延续；在本计划范围内的后续本地探索不需要
逐项人工批准。

允许继承：

- EP19 的 PIT top-400 主板 + top-100 创业板 universe lineage；
- close-observed、next-session usable 的时间语义；
- next-open、停牌、涨跌停、blocked fill、成本和现金审计方法；
- 项目的 train-only selection、purge、embargo、episode 去重和可审计 checkpoint 原则；
- 本地真实 qfq OHLCV 与 benchmark 数据作为待重新 hash 的输入。

不得继承：

- realized-winner 条件化 universe；
- winner episode 的未来边界、未来 phase 或未来 path；
- EP16/EP18 已观察的 survival/payoff score 作为正向先验；
- EP20/EP21 任一候选的正收益或模型有效性；
- EP21 尚处于 `.building` 的产物或暂定 readout；
- EP13/EP14 的事件公式作为已支持信号；
- EP8 的 regime 标签作为未经重审的真实市场状态。

### 1.4 与既有失败研究的区别

EP20B-SRC 已经检验过：

```text
trailing 5D/10D market-residual continuation
```

其历史终态为 `20B_SRC_not_identified_design_only`，residualization value 未通过，也没有 participation/meta-label 或下一 requirement
授权。

因此 22B 不是把 trailing residual momentum 改名重跑。22B 的第一层新 estimand 是：

```text
pre-registered common shock at t
+ contemporaneous board/industry reaction relative to causal expected group response
+ forward group price/path outcome from after the information cutoff
```

`EP20B-SRC-like group trailing residual continuation` 必须作为 incumbent comparator；它必须在本次受支持 group universe 上
重新按 group 口径因果构造，不能把 EP20B-SRC 的 stock-level 输出直接当作同口径 comparator。若 22B 最终只是把 trailing
residual momentum 聚合到 group 后重跑，应直接判为 `duplicate_research_closed`。

个股相对板块/行业的 residual 只属于第二层 decomposition。第一层板块/行业关系未通过前，不得用密集 stock-row 结果把 M1
解释成个股选股信号。

EP16 已证明 survival / drawdown-risk separability 不等于 action utility。因此 EP22 中：

- AUC、状态可分性、MAE 改善或风险分类不能自动授权策略；
- 任何“模块有效”结论必须限定在该模块自己的 estimand；
- EP22 不做 score-to-action mapping；
- 对冲诊断不能替代个股逻辑失效退出。

---

## 2. 共同研究原则

### 2.1 每个模块都必须有独立 estimand

六个模块分别回答六类问题，不允许用一个模块的指标替代另一个：

```text
M1: market/group shock 后的 group abnormal reaction 是否含有增量的 forward group price/path information?
M2: observable state 是否稳定对应不同的 forward market distribution?
M3: observable supply/demand event 是否对应可复现的 market response?
M4: style return/turnover/liquidity relation 是否稳定且不同于会计式“资金消耗”?
M5: PIT fundamental quality/value 是否对应长期收益与风险差异?
M6: 单项 risk-budget primitive 是否校准；
    shadow hedge 是否只在归因层隔离目标 exposure；
    executable hedge 是否在完整摩擦后仍有效?
```

模块之间不得共享“通过”：

- M1 有效不代表 M2 有效；
- M2 能描述状态不代表能预测；
- M3 的某类供给事件有效不代表可以把不同资金项相加；
- M4 的价格响应差异不证明资金被“消耗”；
- M5 的长期关系不提供短线择时；
- M6 某个 sizing primitive 或 hedge 降低波动，不证明原个股逻辑正确。

### 2.2 先验证 construct，再看 outcome

每个模块固定三层 gate：

```text
G_construct:
    变量是否真的测量所声称的对象？

G_pit_data:
    数据是否真实、PIT、覆盖足够且可复现？

G_market_validation:
    在真实市场中是否有方向、效应量、稳定性与增量价值？
```

任何前层失败，后层不得通过。

### 2.3 不用 OHLCV 识别投资者身份

OHLCV 可以测量：

- 实际价格反应；
- 相对强弱；
- gap、收盘位置、影线；
- 成交异常；
- 波动、广度、离散度；
- 流动性和价格冲击 proxy；
- 状态转移。

OHLCV 不能可靠识别：

- 主力吸筹或出货；
- 机构、散户、保险、社保或外资的真实身份；
- 资金净流入的完整来源；
- 公告的经济含义；
- 股权供给的实际执行；
- 投资者未来一定会买入或卖出。

所有相关字段必须使用 `proxy`、`observable_response` 或 `association` 命名，不得写成身份或因果事实。

### 2.4 历史数据的证据角色

所有 freeze 前历史：

```text
sample_role = design_contaminated_historical_real_market_evidence
support = false
allowed_use = construct_validation / falsification / effect_sizing / stability / candidate_freeze
```

历史弱或负结果可以关闭候选；历史强结果最多得到：

```text
historically_supported_design_candidate
```

只有 post-freeze forward cohort 才可能得到：

```text
forward_supported_component
```

### 2.5 模块独立与防止叙事膨胀

22B–22G 在任何 outcome 被读取前分别冻结：

- 一个 primary claim；
- 一个 primary outcome；
- 一个 primary horizon；
- 一个 incumbent baseline；
- 一个 primary statistical unit；
- 一个主要稳定性要求；
- secondary tests 的数量和 multiplicity family。

不得因某模块失败而把另一个模块临时加入模型“救结果”。22H 只汇总，不重新拟合、不组合分数、不选择最佳跨模块公式。

### 2.6 多周期假设单独验证

原方法区分短线、波段和趋势仓位，但没有给出可复现比例。EP22 不猜测三类仓位权重，只验证不同 component 的信息周期：

| Component | 候选观察周期 |
|---|---|
| M1 event reaction | H1/H3/H5/H10/H20 |
| M2 market state | days to several weeks |
| M3 supply/demand event | event-time to several months |
| M4 style response | days to several months |
| M5 quality/value | 6/12/24/36 months |
| M6 risk/hedge primitive | daily risk calibration to monthly stability |

每个模块只冻结一个 primary horizon，其余属于 multiplicity-controlled secondary。若同一变量只在某个 horizon 有效，应报告
`horizon_specific_association`，不得升级成适用于短线、波段和趋势的通用规律。

“短期判断失败不自动推翻长期命题”只作为 estimand separation 原则，不是允许亏损头寸继续持有的理由。

---

## 3. 共同数据、时点与统计合同

### 3.1 当前本地 baseline 与主动补数

22A 必须重新审计，不得把计划时 inventory 当运行时证据。当前已知本地输入包括：

- PIT top-400 主板 + top-100 创业板 membership / executable daily；
- qfq stock OHLCV；
- CSI300、创业板指、全 A 指数 benchmark OHLCV；
- 约 2017-01 至 2026-05 的历史覆盖；
- 既有 regime、event、execution 和 cost 审计产物。
- raw share-history cache 中的 total/listed-circulating share 候选字段；它们尚未成为 processed contract，
  且 `listed circulating A shares` 不自动等于指数方法意义的 official free float。

当前不预设已可靠可用、但必须进入 D0–D3 source exploration 的数据：

- genuine PIT industry membership；
- 公告级语义新闻及精确发布时间；
- IPO/增发/解禁/减持/回购的完整 PIT 执行数据；
- 基金发行、申赎、ETF creation/redemption 的完整历史；
- 融资融券可比口径历史；
- PIT free-float shares；
- as-reported 财务数据及首次公开时间；
- 分析师预测修正；
- 指数期货/ETF 的连续合约、基差、换月、保证金和真实成本。

缺失项必须在 22A 标记并进入 candidate-source registry，不得静默替代，也不得因为 baseline 中没有就直接关闭研究。每个缺口至少
记录候选 provider/API/file、访问条件、可用字段、时间范围、PIT timestamp、revision、许可/成本、预期解锁 module 与试采结果。

新增 source 不自动替换 baseline。必须建立成对 arm：

```text
B0_existing_local_baseline
B1_candidate_source_augmented
```

先审计 B1 是否改善 construct/coverage/effective support，再在 module-specific attempt 中检验 B1 相对 B0 是否有 empirical increment。
只有数据更多但无增量，正确结论是 `source_redundant_or_low_value`。

existing-data baseline 的 universe claim ceiling：

```text
stock_cross_section_scope = within_U_project
market_shock_source = official benchmark series
project_breadth != full_A_breadth
within_U_project_relative_small != A_share_small_cap
market_wide_supply_or_flow_claim = data_blocked_without_separate_broad_source
```

因此 baseline arm 中，M2 的上涨家数/新高/成交广度是项目池广度，M3 issuer panel 是项目池发行人，M4 size spread 是项目池内
相对 size。22A 应主动寻找并审计宽截面 PIT eligible universe、历史权重和相关数据；通过后新增 expanded-universe arm，而不是
回写或伪装 baseline。只有 expanded arm 的 coverage/PIT/denominator audit 通过，才可形成更宽市场范围的 source-specific 结论。

### 3.2 Industry 边界

EP19 已确认本 topic 的 historical PIT industry classification 不足以支持 primary industry RS / breadth。

因此默认：

```text
M1 primary market-shock source = official market benchmark
M1 primary reaction unit = supported board/style portfolio
M1 genuine-industry return arm = conditional_on_22A_source_audit
M1 genuine-industry internal-structure arm = conditional_on_22A_pit_membership_audit
M2 primary state = within-U_project breadth + official market benchmark + supported board/style only
M4 primary style = PIT-observable board/size/liquidity/volatility/momentum buckets
historical_current_industry_backfill = forbidden
```

M1 的行业层可以通过两条不同数据路径获准，且 claim ceiling 不同：

1. 有完整、时间语义明确的官方行业指数 OHLCV 时，可以运行 `industry_return_only_arm`，但不能据此声称掌握成分股 breadth、
   dispersion 或内部集中度；
2. 有逐时点有效的 industry membership、instrument mapping 与 `t-1` 权重时，才可以自建行业组合并运行
   `industry_internal_structure_arm`。

仓库其他 topic 中若存在覆盖较窄的 PIT industry 表，只能在通过以下审计后进入上述第二条路径：

- universe overlap；
- date coverage；
- instrument mapping；
- membership timestamp；
- taxonomy stability；
- cross-topic hash lineage；
- leave-one-out bucket construction。

覆盖不足或 mapping 不一致时输出：

```text
industry_return_only_arm = not_run_due_to_unsupported_historical_industry_index
industry_internal_structure_arm = not_run_due_to_unsupported_pit_industry
```

不得把 current industry、2025 taxonomy 或 concept/theme snapshot 回填为 historical PIT industry。
概念/主题板块在没有可证明的历史成分变更时间前不进入 M1 primary；交易板、行业、风格和概念不得混写为同一个 `board`。

### 3.3 通用时点

所有模块必须逐字段记录：

```text
observation_time
availability_time
decision_information_cutoff
first_usable_time
outcome_start
outcome_end
```

通用价格模块语义：

```text
feature_cutoff = close t
first_forward_price = next executable open after t
outcome starts after first_forward_price
```

如果某项数据在 `t+1` 才发布，不能回填到 `t`。

公告/财务模块必须区分：

```text
event_effective_date
announcement_timestamp
exchange_publication_timestamp
provider_ingestion_timestamp
first_market_usable_time
revision_timestamp
```

只有 `first_market_usable_time` 可决定样本时点。

### 3.4 qfq 与 corporate-action 审计

以下情况必须 fail closed 或单列：

- qfq factor discontinuity 伪造 overnight gap；
- raw 与 qfq open/close 无法对齐；
- 停牌后复牌 gap；
- 涨跌停导致不可成交；
- volume/amount 单位不一致；
- qfq `money / volume` 被错误称为 VWAP；
- delisting、ST 或 membership 状态缺失；
- benchmark 与 stock calendar 错位。

M1 的 gap、M3 的回购/稀释、M4 的 turnover 和 M6 的 hedge 尤其依赖这些审计。

### 3.5 Episode 与统计单位

禁止把密集 stock-day 当作独立证据。

M1/M3 的事件必须在线聚合：

```text
episode_start = first causal trigger
episode_end = fixed pre-registered cooldown or max_age
future recovery / future high / first winner hit cannot define episode boundary
```

同一 episode 的所有 rows 必须进入同一 fold。

统计单位按模块冻结：

| 模块 | primary inference unit 候选 |
|---|---|
| M1 | distinct market shock-date / online market or group shock episode；group rows nested within shock-date |
| M2 | non-overlapping calendar block / state segment |
| M3A | issuer-event episode + issuer/calendar block |
| M3B | non-overlapping aggregate-flow calendar block |
| M4 | style-date block |
| M5 | firm-report cohort + calendar vintage |
| M6A | instrument/date or reference-book/date risk-forecast block |
| M6B | portfolio-date / hedge-roll block |

误差与 bootstrap 至少处理：

- 日期横截面相关；
- 同一 instrument 重复；
- event episode 聚类；
- overlapping horizon；
- market regime persistence。

### 3.6 Train-only 与 multiplicity

以下全部只能在 train / expanding past 内完成：

- beta 与 expected-response 模型；
- rolling moments；
- shock cutoff；
- winsorization；
- quantile edge；
- scaler；
- state model；
- state label mapping；
- style bucket；
- lag kernel；
- half-life；
- model selection；
- threshold；
- hedge beta；
- candidate selection。

每个模块必须指定 primary family，并使用预注册的 Holm、FDR 或更严格 correction。不能从几十个 horizon、状态、供给项或风格中
挑最好一个后只报告 nominal p-value。

---

## 4. M1：可观测冲击后的异常反应

### 4.1 要验证的 practitioner claim

原命题是：

```text
实际反应 - 应有反应 = 信息
```

在没有可靠新闻语义、当时市场共识和 PIT 时间戳时，EP22 不称“利好/利空事件”，也不把价格波动归因于某条事后找到的
新闻。Primary 只研究：

```text
observable market-wide common price shock
+ observable group-specific residual price shock
+ contemporaneous board/industry reaction relative to causal expected group response
```

M1 的第一层 primary reaction unit 是受支持的交易板、行业或其他预注册 group portfolio，不是个股。研究顺序固定为：

```text
L0 market common shock
    -> L1 board/industry abnormal reaction
    -> L2 group internal breadth/dispersion/liquidity structure
    -> L3 stock relative-to-group reaction, deferred
```

第一层板块/行业结果未通过前，L3 不得成为 M1 primary，不得用巨大 stock-row N 替代有效 shock-date / episode 证据。
M1 的 event-conditioned group reaction 与 M4 的 unconditional / state-conditioned style price-impact relation 是两个 estimand；
不得用其中一个结果替代另一个。

公告/新闻语义只能作为单独的 secondary module extension，并且必须先证明精确发布时间、修订、停复牌与 first-market-usable
时点。若该数据合同未通过：

```text
semantic_good_bad_news_arm = not_run_due_to_timestamped_source_unavailable
```

不得用 gap 的正负反推“利好/利空”标签。

Construct ceiling 固定为：

```text
semantic_event_surprise = data_blocked_without_timestamped_event_polarity_and_expected_magnitude
market_or_group_price_shock_causal_origin = unidentified_without_timestamped_semantic_source
group_shock_reaction_residual = proxy_only
```

因此只运行 price-shock arm 时，M1 不得进入 `component_directly_measurable_historically_stable`；最高只能进入
`component_proxy_only_historically_informative`。

### 4.2 Group taxonomy 与数据授权

`group` 必须逐类明确，不得混用：

```text
exchange_board:
    main board / ChiNext / other PIT-observable trading board

genuine_industry:
    pre-registered official taxonomy with historical return series
    or auditable PIT membership

style_group:
    PIT-observable size / liquidity / volatility / momentum group

concept_or_theme:
    not eligible without historical membership and revision timestamps
```

22A 必须分别裁决：

```text
group_return_arm:
    需要可信的官方历史 group index OHLCV，
    或由 PIT membership + t-1 frozen weights 自建

group_internal_structure_arm:
    需要 PIT membership，才能计算 breadth / dispersion /
    leader concentration / limit / suspension structure
```

只有官方行业指数 OHLCV 而没有 PIT 成分时，可以研究行业收益 residual，但不得输出行业内部 breadth、dispersion 或“多数成分股
确认”等结论。若 genuine PIT industry 未通过，则行业 arm 必须显式 `data_blocked`，不得用 current industry 回填；M1 可以先运行
受支持的 exchange-board/style group，但结论不得升级为行业结论。

### 4.3 Primary clock 与可执行时点

日频 primary 固定从收盘冲击开始：

```text
shock_observation_time = close(t)
feature_cutoff = close(t)
first_usable_time = next executable open after t
outcome_start = first_usable_time
```

close `t` 才能确认的市场、板块/行业收益和内部结构，不得假设在同一 close 成交。

Overnight/open shock 只能作为独立 secondary arm。若只有 daily open，不能在观察 opening gap 后仍按同一个 daily open 假设成交；
必须有开盘集合竞价/分钟数据与明确的 first executable price，或者输出：

```text
open_shock_arm = not_run_due_to_non_executable_same_open_timing
```

### 4.4 市场共同冲击定义

市场冲击不能只由单个市值加权指数越线定义。否则大权重行业可能把指数拖动，并伪装成全市场共同冲击。22A/22B 必须在 outcome
前冻结具体 benchmark、lookback、最小样本、shock cutoff 和 breadth confirmation。

公式骨架为：

```text
market_return_t =
    official_benchmark_close_t / official_benchmark_close_t-1 - 1

market_center_t-1 =
    causal rolling center fit only through t-1

market_scale_t-1 =
    causal robust volatility fit only through t-1

market_shock_z_t =
    (market_return_t - market_center_t-1) / market_scale_t-1

market_magnitude_pass_t =
    market_shock_z_t crosses pre-registered directional cutoff

market_breadth_pass_t =
    pre-registered supported-group breadth
    and/or eligible-instrument breadth confirms the shock direction

market_common_shock_t =
    market_magnitude_pass_t AND market_breadth_pass_t
```

22A 必须在 outcome 前冻结究竟使用 group breadth、eligible-instrument breadth，还是二者的明确布尔组合；不能运行后任选。
若数据只支持项目池 breadth，字段和 claim 必须写成 `within_U_project_group_breadth` 或
`within_U_project_instrument_breadth`，不得称 full-A breadth。等权 group return、上涨/下跌 group 占比、成交或涨跌停广度
可以作为预注册 confirmation，但不得在 outcome 后挑选最有利的一项。若可用 group 数不足以形成有意义的 breadth，
`market_wide_scope_status` 必须降级或阻断，而不是把两三个 group 的同向波动称为全市场确认。

固定 `1%` 只能作为市场 benchmark 的候选 absolute magnitude floor，不能单独定义 primary shock。22A 可以在不读取未来 outcome
的前提下比较候选 absolute floor、robust-z 或 causal tail-quantile policy，并只根据以下 support 冻结：

- 正负方向 distinct shock-date / episode 数；
- 每年和各时间 fold 覆盖；
- 是否被少数极端年份支配；
- supported group 覆盖；
- missing、停牌、涨跌停和不可执行比例；
- market/board/industry overlap；
- 有效独立 block 与功效。

不得根据哪个阈值的未来收益最好选择 shock cutoff。

当 benchmark magnitude 越线但 breadth 不通过时，状态必须为：

```text
index_concentrated_or_group_led_move
```

不得归入 pure market common shock。

### 4.5 板块/行业特异冲击与预期反应

板块/行业的原始涨跌不能直接定义 group shock。必须先剥离市场共同反应。对于 group `g`：

```text
rest_of_market_return_ex_g,t =
    causal market portfolio return excluding group g,
    using membership and weights frozen no later than t-1

beta_g,t-1 =
    group expected-response model fit only through t-1

expected_group_return_g,t =
    alpha_g,t-1
    + beta_market_g,t-1 * rest_of_market_return_ex_g,t
    + supported_pre_registered_board_or_style_controls

group_reaction_residual_g,t =
    observed_group_return_g,t - expected_group_return_g,t

group_residual_scale_g,t-1 =
    causal robust residual volatility fit only through t-1

group_shock_z_g,t =
    group_reaction_residual_g,t / group_residual_scale_g,t-1

group_specific_shock_g,t =
    group_shock_z_g,t crosses pre-registered directional cutoff
```

优先使用 `rest_of_market_return_ex_g`，避免大权重行业机械进入自己的 market control 并压小 residual。若无法构造
rest-of-market，22A 必须量化 benchmark contamination，并降低 claim ceiling 或阻断 group-specific arm。

若自建 group portfolio，membership 和权重必须在 `t-1` 冻结。下钻到个股 arm 时，group portfolio 还必须对目标股票
leave-one-out，避免股票自身机械进入 expected response。

### 4.6 市场冲击与行业冲击的互斥分类

价格数据只能识别冲击的统计作用范围，不能识别真实新闻来源。分类必须使用 `market_common_shock_t` 与
`group_specific_shock_g,t` 的二维状态，而不是强迫所有日期二选一。下表首先定义 `(date t, group g)` pair state：

| market common shock | group residual shock | event type |
|---|---|---|
| false | false | `no_qualified_shock` |
| true | false | `pure_market_common_shock` |
| false | true | `group_specific_residual_shock` |
| true | true，residual 与市场同向 | `market_shock_with_group_amplification` |
| true | true，residual 与市场反向 | `market_shock_with_group_resistance` |

Date-level event type 再由所有受支持 pair state 聚合：

```text
pure_market_common_shock_date:
    market_common_shock_t = true
    AND no supported group has group_specific_shock_g,t

group_specific_residual_shock_date:
    market_common_shock_t = false
    AND one or a pre-registered small share of groups has group_specific_shock_g,t

joint_market_group_shock_date:
    market_common_shock_t = true
    AND at least one supported group has amplification or resistance
```

进一步的 scope 规则：

- 只有一个或少数 group residual 异常，才可称 localized group-specific shock；
- 多个相同风格 group 同时异常时，应优先审计 `style_cluster_shock`，不得机械生成多个独立 industry event；
- 大多数 group 同向异常时，应审计遗漏的 common factor 或 market benchmark mismeasurement；
- 市值加权指数由少数大权重 group 驱动但横截面 breadth 不足时，应标记
  `index_concentrated_or_group_led_move`；
- 市场、交易板/风格、行业的 residualization 顺序必须预注册，不能 outcome 后改变层级。

上述 joint states 必须单独报告，不能塞入 pure market 或 pure group arm。正负方向以及 amplification/resistance 也不得假设对称。

### 4.7 Online episode 与冲击传播

M1 的 market/group event 必须在线聚合；future recovery、future high/low 和未来传播不得定义当前事件：

```text
episode_start = first causal threshold crossing
episode_end = pre-registered cooldown or max_age
```

若 `t` 日只有 group shock、`t+1` 才出现 market shock：

```text
t state = group_specific_residual_shock
t+1 episode update = group_led_market_spillover
```

不得利用 `t+1` 结果把 `t` 事后改成 market shock。反向顺序可以在线更新为：

```text
market_shock_with_delayed_group_amplification
```

同一 episode 的 market/group rows 必须进入同一 fold。

### 4.8 Preoutcome census 与 as-of 数据面板

22A 必须先完成 outcome-blind 的 M1 census，不能直接从“未来表现好的冲击”反推事件定义。最小中间产物为：

```text
m1_group_taxonomy_and_source_registry.csv
m1_group_membership_and_weight_pit_audit.csv
m1_common_shock_date_census.csv
m1_market_group_shock_episode_census.csv
m1_group_reaction_asof_panel.csv
m1_shock_threshold_power_and_support_preflight.csv
```

`m1_common_shock_date_census.csv` 至少记录：

```text
shock_date
shock_scope
benchmark_or_group_id
raw_return
causal_center_t_minus_1
causal_scale_t_minus_1
shock_z
shock_direction
candidate_threshold_id
magnitude_pass
breadth_pass
market_group_overlap_status
information_cutoff
first_usable_time
source_availability_status
```

`m1_group_reaction_asof_panel.csv` 每行是 shock-date 内的受支持 group，不是把个股当 primary row，至少记录：

```text
event_id
group_id
group_type
group_membership_status
observed_group_return_t
rest_of_market_return_ex_group_t
expected_group_return_t
group_reaction_residual_t
group_shock_z_t
group_breadth_t
group_residual_breadth_t
group_dispersion_t
group_volume_or_amount_anomaly_t
group_turnover_anomaly_t
group_liquidity_change_t
leader_concentration_t
limit_up_down_share_t
suspension_share_t
feature_cutoff
first_usable_time
```

只有 PIT membership 通过时，内部结构字段才可计算；否则必须为 structural missing，并附明确 reason，不得从当前成分回填。

As-of feature 与 future outcome 必须物理分表并分别 hash：

```text
m1_group_reaction_asof_panel
m1_group_forward_outcome_panel
```

先 checkpoint、验证并记录 as-of panel semantic hash，再连接 H1/H3/H5/H10/H20 outcome。同一次探索 run 可以在前序内部校验通过后
自动继续，不需要人工批准或 immutable seal。

### 4.9 Nested baseline 与观察量

Group-level nested ablation 顺序固定为：

```text
G0 raw market/group shock magnitude
G1 raw group return
G2 simple group-minus-market relative strength
G3 causal beta-adjusted group reaction residual
G4 G3 + group breadth / residual breadth / dispersion
G5 G4 + volume / turnover / liquidity / concentration confirmation
```

若 G3 不优于 G2，不能用 G4–G5 掩盖 group reaction residual 本身失败。

个股层 B0–B5 不得用来掩盖 group layer 失败；若要探索，必须作为单独 requirement/variant checkpoint 运行并独立裁决，不需要
逐阶段人工批准。届时以下个股量可以 nested 加入：

- overnight gap；
- open-to-close response；
- close location value；
- upper/lower shadow；
- amount/volume anomaly；
- stock versus supported group relative strength。

这些量全部只能使用截至 `t` close 已经完成的信息。`recovery speed`、post-shock MAE/MFE 和 path damage 属于 forward outcome，
不得进入 `t` 时 predictor。

### 4.10 Real-market outcomes

Primary horizon 由 22A 功效审计后冻结；候选 readout 可包含 H1/H3/H5/H10/H20：

- next-open-to-close / next-open-to-next-open return；
- group market-adjusted return；
- top-residual versus bottom-residual group spread；
- residual continuation / reversal；
- group breadth persistence；
- volume/liquidity confirmation or decay；
- MAE；
- MFE；
- time-to-recovery；
- realized volatility；
- downside tail / CVaR proxy。

Big Winner / +50% 不是 group-level outcome。它只可在 L3 stock decomposition 的独立 exploratory variant 中作 secondary
right-tail bridge，
不能参与 L0–L2 cohort、threshold 或 primary label 构造。

在 `t` 时点，`group_reaction_residual` 只能称“相对因果预期反应更强/更弱”，不能称过度或不足定价。未来 continuation、
reversal、recovery 或 damage 才是 outcome。二者必须作为预注册 competing mechanisms；不能看完未来路径后再选择叙事。

### 4.11 可选 landmark 诊断

若要检验“事件后持续观察”，只能做无动作的 landmark predictive diagnostic，并为每个 landmark 重新锚定时间：

```text
landmark_date = t+k, where k is pre-registered
feature_cutoff = close(t+k)
first_usable_time = next executable open after t+k
outcome_start = first_usable_time
outcome_end = outcome_start + frozen horizon
```

`t+1/t+3/t+5` 只是候选 landmark，22A 必须冻结一个 primary。晚到 feature 不得回填到 `t0`，landmark outcome 也不得复用
从 `t0` 开始的 label window。Landmark 只验证信息是否更新，不学习加仓、减仓、退出或 hedge action。

### 4.12 M1 可证伪假设

```text
H1a:
market common shock 下，group reaction residual 对后续 group-adjusted payoff、
continuation/reversal 或 path damage 具有相对 G2 的稳定增量。

H1b:
group-specific residual shock 与 pure market common shock 是不同 estimand；
其 forward path 关系在预注册方向、时间 fold 和 group scope 中可复现。

H1c:
group breadth / dispersion / liquidity structure 对单纯 group return 或 group-minus-market RS
提供预注册的增量，而不是少数权重 group/name 的机械贡献。

H1d:
结果不是 raw return、beta、volatility、liquidity、size、board/style cluster、
benchmark concentration 或 EP20B-SRC-like group trailing residual continuation 的重命名。
```

正负市场冲击、正负 group residual、continuation 与 reversal 必须按预注册 family 处理 multiplicity，不得假设对称，也不得在
outcome 后改变 orientation。若只能事后判定哪一侧叫“过度/不足反应”，不构成 PIT-valid signal。

### 4.13 M1 失败条件

- 只在 in-sample 或少数年份成立；
- genuine industry arm 依赖 current taxonomy 回填或无法证明 membership/return series 的 PIT 语义；
- market shock 只由权重指数驱动而缺少 group breadth confirmation；
- market、style-cluster 与 industry-specific scope 无法区分；
- 对 simple group-minus-market relative strength 无增量；
- G3 不优于 G2，却用 G4–G5 掩盖 residual 失败；
- 结果由 corporate-action gap 或不可成交样本驱动；
- 只有 group-row 或 stock-row nominal significance，没有 shock-date / episode support；
- 正负 shock 方向需要 outcome 后改 orientation；
- 只有看到未来 continuation/reversal 后才能定义 event type 或 episode boundary；
- 退化为 EP20B-SRC-like group trailing residual continuation；
- 只有 future-smoothed event boundary 才成立。

---

## 5. M2：情绪与“持仓结构”的可观测代理

### 5.1 Construct 边界

市场情绪和投资者持仓库存不可被 OHLCV 直接观察。M2 只能构造：

```text
sentiment_and_positioning_proxy_state
```

不得声称识别“谁已经买入”“谁会成为未来买家”。

### 5.2 候选可观测变量

在 PIT 与覆盖审计通过后，可用：

- 上涨股票占比；
- 涨停/跌停数量与比例；
- 新高/新低比例；
- 市场中位数收益；
- cap-weighted 与 equal-weighted return 差；
- 成交额及其历史分位；
- realized / downside volatility；
- 横截面离散度；
- `U_project` 内相对小盘/大盘；
- board 相对强弱；
- turnover concentration；
- financing balance change；
- ETF flow；
- fund issuance/subscription；
- valuation/crowding proxy。

后四类只有真实 PIT 数据通过 22A 才能使用。缺数据不能由 OHLCV 推断。

### 5.3 状态构造

Primary 应先使用透明、冻结的 causal rule/state score。HMM、state-space 或 change-point 模型只能作为 sensitivity。

所有模型必须满足：

```text
state_at_t uses data <= t
filtered_probability_only = true
full_sample_smoothed_state = forbidden
future_regime_relabeling = forbidden
cross_fold_state_label_mapping = pre_registered
```

五个叙事状态：

```text
distress
repair
hesitation_or_trend_development
euphoria
deterioration
```

不是预设真相。若样本厚度不足，primary 可冻结为较粗的三状态：

```text
risk_off / transition / risk_on
```

五状态只作 descriptive sensitivity。

### 5.4 要验证的市场命题

M2 分开检验：

```text
H2a distress:
    极端压力状态之后的 forward return / breadth / downside distribution
    是否区别于简单高波动或大跌 baseline？

H2b development:
    中间状态是否更容易表现为趋势延续，而不是无条件均值回归？

H2c euphoria:
    高广度、高换手或高拥挤状态之后，forward payoff / tail risk
    是否出现稳定恶化？

H2d transition:
    filtered transition probability 是否比 yesterday state、trend 和 volatility
    提供稳定的分布增量？
```

M2 不要求预测指数点位。它验证的是不同 observable state 是否对应可复现的未来分布。

### 5.5 Baselines

- unconditional market；
- current return only；
- trailing trend；
- realized volatility；
- drawdown；
- previous state；
- 既有 EP8 regime 作为 frozen historical comparator。

EP8 的 `transition` 历史结果不得被预设为稳定第三状态或正向 evidence。新状态必须证明不是 trend/vol/drawdown 的换名，
也不能因为和旧 transition 标签相似就自动通过。

### 5.6 M2 失败条件

- 只有 full-sample smoothed HMM 才清晰；
- state label 在 fold 间任意交换；
- forward distribution 没有增量；
- 结果仅由极少数 crash dates 驱动；
- 五状态样本太薄；
- validation 后重新定义“绝望/疯狂”；
- 用未来行情定义 state segment 结束。

即使 M2 通过，也只得到：

```text
observable_market_state_proxy_supported
```

不授权 market timing 或仓位调整。

---

## 6. M3：股权供给与资金需求

### 6.1 拆成 M3A/M3B，不先做总指数

原方法列出的供求项具有完全不同的时点、执行概率和传导机制。M3 第一原则：

```text
do_not_sum_heterogeneous_flows_before_component_validation
```

M3 必须拆成两个独立 estimand、requirement 和 terminal decision：

```text
M3A issuer_capital_action_event:
    issuer/event-level IPO, share change, issuance, unlock, reduction,
    buyback, ownership increase or privatization action

M3B aggregate_demand_flow:
    market/date-level ETF, fund, margin, external or long-horizon capital flow
```

M3A issuer capital-action 候选：

- IPO；
- 增发/配股；
- 解禁可售；
- 大股东/董监高减持；
- 股份稀释；
- 回购公告与实际回购；
- 股东/管理层增持；
- 私有化；

M3B aggregate demand-flow 候选：

- ETF creation/redemption；
- 公募发行与申赎；
- 融资余额变化；
- 可审计的长期资金代理。

当前本地 processed contract 未确认包含上述 announcement/execution/flow panel。Share-history cache 最多可能支持
`realized_share_count_change_proxy`，但如果缺少 change reason 与 announcement timestamp，就不能区分 IPO、增发、解禁、
回购或其他变动，更不能估计公告到执行的传导时滞。任何缺失 component 必须保留为 `not_evaluable`，不得补零。

M3A 的 inference unit 是 issuer-event episode；M3B 的 inference unit 是 non-overlapping market-date block。二者不得共享
primary baseline、horizon、sample-size gate 或 p-value family，也不得用 M3A 数据可用性替 M3B 通过。

### 6.2 公告、可用额度和实际执行必须分开

每类事件至少拆成：

```text
announcement
eligibility_or_unlock
planned_amount
actual_execution
completion_or_expiry
```

例如：

- 解禁不等于减持；
- 回购公告不等于回购成交；
- 基金发行不等于立即买股；
- 融资余额上涨不等于主动新增买盘；
- ETF 申购可能伴随套利与期货对冲。

不同阶段不得合并成同一个“流入/流出”字段。

### 6.3 数据合同

每一 component 必须审计：

- original source；
- announcement timestamp；
- revision/cancellation；
- actual execution date；
- shares / amount unit；
- issuer/instrument mapping；
- PIT denominator semantics：total cap、listed-A-share circulating cap proxy 或 independently verified official free-float cap；
- coverage by year/board；
- missingness；
- survivorship；
- backfill timestamp。

若只有当前累计值或事后完整记录，不能回填为历史 PIT signal。

### 6.4 市场验证设计

每一 supply/demand component 独立做：

1. event-time response；
2. matched controls；
3. distributed lag / half-life；
4. size、liquidity、valuation、prior return 与 market state controls；
5. announcement vs execution attribution；
6. future return、turnover、volatility、liquidity 与 price-impact readout；
7. calendar-time portfolio 仅作 association check，不作策略。

`U_project` 只覆盖项目大市值池。M3A 的结果默认只对 `issuers_observable_within_U_project` 成立，不能推断全 A IPO/股权供给；
M3B 若要声称 market-wide flow，必须另有覆盖全市场且口径一致的 aggregate source。

归一化候选：

```text
event_intensity =
    actual or announced shares/amount
    / audited PIT denominator with an exact semantic label
```

本地 raw `float_share_asof` 若通过 source/coverage audit，最多命名为：

```text
listed_A_share_market_cap_proxy
```

它不是自动等价于指数方法意义的 official free-float cap。若 PIT denominator 不可用，该 component 必须降级或 blocked，
不得用 current free float 回填。

### 6.5 M3 可证伪假设

```text
H3a:
实际执行的新增股权供给相对 matched controls 对未来价格/流动性存在稳定压力。

H3b:
实际回购/增持相对单纯公告具有不同且更稳定的市场关系。

H3c:
融资、ETF 或基金流变量在控制价格反向影响后仍有独立 market association。

H3d:
不同 component 的 lag 与 half-life 显著不同，简单相加会损失信息或产生错误方向。
```

### 6.6 M3 claim ceiling

即使通过，也只能说：

```text
observable_supply_or_demand_component_has_stable_historical_market_association
```

不能说：

```text
complete_market_net_flow_identified
causal_capital_inflow_proven
future_buyer_or_seller_identity_known
```

---

## 7. M4：风格与价格冲击效率

### 7.1 修正“资金消耗”的会计误区

M4 明确不验证：

```text
market_cap_change == capital_inflow
turnover == capital_consumed
small_cap_always_consumes_more_money
```

成交额是买卖双方的交换，边际价格可以重估全部存量市值。M4 真正验证的是：

> **不同风格在相似成交、流动性和市场状态下，价格响应、广度、冲击、持续性和反转是否存在稳定差异。**

### 7.2 Primary style universe

只使用 PIT-observable 且审计通过的 style：

- size；
- board；
- liquidity；
- volatility；
- momentum；
- turnover；
- 质量/价值仅在 M5 数据合同通过后作 sensitivity。

Genuine PIT industry 缺失时不得进入 primary。

`U_project` 本身是大市值门槛后的项目池，因此其中的 size buckets 只能称：

```text
relative_size_within_U_project
```

不得称为“全 A 股小盘/大盘”结论。

### 7.3 候选读数

- within-`U_project` relative-small-minus-relative-large return；
- small/large amount share；
- cap-weighted minus equal-weighted return；
- style breadth；
- style new-high/new-low share；
- style turnover；
- Amihud-like illiquidity；
- price response per turnover proxy；
- return concentration；
- top-weight contribution；
- intrastyle dispersion；
- future style continuation / reversal；
- liquidity deterioration after high-turnover low-progress states。

`top-weight contribution` 默认只指由项目 PIT cap 构造的 project-book contribution。当前 official benchmark constituent weights 与
index transaction amount 未确认可用，不得据此声称还原官方指数前十大权重贡献。

描述性 ratio 可写为：

```text
price_response_per_turnover_proxy_g,t =
    robust_style_return_g,t
    / max(turnover_to_exactly_named_audited_cap_g,t, denominator_floor)
```

但 primary inference 不得只依赖不稳定 ratio。应同时使用 robust regression/local projection：

```text
future_style_return_or_impact
    = a
    + gamma * current_turnover/liquidity state
    + pre_registered controls
    + error
```

因为 amount 不是 signed net flow，`gamma` 只能解释 price/turnover relation，不能解释资金净流入因果。

### 7.4 M4 可证伪假设

```text
H4a:
`U_project` 内相对 size 或其他 PIT style 的价格响应/换手关系存在稳定差异。

H4b:
高换手但低价格推进状态，对未来 continuation/reversal/liquidity deterioration
具有相对简单 style return 的增量信息。

H4c:
cap-weighted / equal-weighted divergence 与 breadth/amount-share 共同变化
能够解释“指数涨但多数股票不涨”等真实市场结构。

H4d:
这些关系在控制 size、volatility、liquidity 与 market state 后仍非零，
否则“资金效率”只是一组已知暴露的重命名。
```

### 7.5 M4 失败条件

- ratio 由近零 denominator 爆炸；
- current constituents 回填；
- style bucket 用全样本 quantile；
- 自建 style benchmark 未 leave-one-out；
- 结果仅由少数极端日期或头部股票贡献；
- 名义成交额被解释成 signed flow；
- value/quality style 使用未来财务数据。

---

## 8. M5：长期价值质量

### 8.1 与短线模块分离

M5 只验证长期横截面与路径关系，不为 M1/M2 提供短线 timing。

原材料中提到 ROE、稳定盈利与回购，但 ROE 可能由高杠杆或低权益基数机械提高。M5 必须先做杜邦与资本质量拆分：

```text
ROE = net_margin * asset_turnover * financial_leverage
```

当前 topic 的 processed contract 未确认存在带首次披露时间和修订历史的 PIT fundamentals。故 M5 默认是
`data_contract_gated`；22A 未找到合格 source 时，22F 应直接 `component_data_blocked`，不得生成 OHLCV quality proxy。

### 8.2 候选变量

在 PIT 财务数据通过后，可研究：

- ROIC 与 incremental ROIC；
- free-cash-flow yield；
- gross/operating margin level and stability；
- asset turnover；
- earnings volatility；
- net debt；
- interest coverage；
- accrual / cash conversion；
- buyback yield；
- dilution rate；
- R&D-adjusted profitability；
- analyst earnings revision，仅在 PIT source 可用时；
- quality × valuation interaction。

### 8.3 财务数据的硬时点

必须使用：

```text
as_reported_value
first_publication_timestamp
revision_history
first_market_usable_time
```

禁止：

- 用当前 restated 财务表回填历史；
- 用年报期末日代替披露日；
- 用未来退市公司缺失制造 survivorship；
- 用负净资产公司的 ROE 做普通排序；
- 把回购授权额当实际回购；
- 忽略 leverage 与行业结构。

### 8.4 Real-market validation

M5 primary horizon 应明显长于 M1/M2，并由 22A 的覆盖与功效审计冻结。候选包括 6/12/24/36 months。

读数：

- long-horizon absolute/excess return；
- drawdown；
- downside tail；
- earnings deterioration；
- delisting/distress；
- turnover/capacity；
- factor exposure；
- sector/board/size concentration；
- rolling-vintage stability。

Baseline 至少包括：

- ROE only；
- valuation only；
- profitability only；
- leverage only；
- simple quality composite；
- market/size/board controls。

### 8.5 M5 可证伪假设

```text
H5a:
经营来源的高质量相对 leverage-driven high ROE 具有更稳定的长期 payoff/risk 关系。

H5b:
实际回购和低稀释相对单纯 EPS/ROE 提升提供增量。

H5c:
quality 与 valuation 联合关系优于高质量无视价格。

H5d:
关系不是行业、size、survivorship 或 restatement hindsight 的产物。
```

若 PIT 财务历史不足，M5 的正确结果是 `data_blocked`，不是改用当前财务快照。

---

## 9. M6：风险预算原件、情景分解与对冲有效性

### 9.1 M6 拆成两个独立子问题

M6 不建设动态情景树、综合风险路由或决策控制器。它把原材料中的风险预算与对冲拆成两个独立验证面：

```text
M6A:
    volatility / liquidity / tail-risk sizing primitives

M6B:
    beta decomposition / shadow or executable hedge mechanics
```

M6A 与 M6B 不互相授权，也不在 EP22 中合成最终仓位。

### 9.2 M6A：风险预算原件

原材料给出的完整乘法式包含：

```text
RiskCap
* SignalConfidence
* RegimeFit
* VolatilityScale
* LiquidityCap
* TailPenalty
```

EP22 不验证这个完整乘积，因为这会提前构造决策路由。M6A 只分别验证三个可直接审计的 sizing primitive：

```text
VolatilityScale
LiquidityCap
TailPenalty
```

`SignalConfidence` 属于具体 alpha/module，`RegimeFit` 属于 M2；两者不得在 M6A outcome 后加入综合公式。

独立检验内容：

1. `VolatilityScale` 的 forecast volatility 是否校准，目标风险 breach rate 是否可控；
2. `LiquidityCap` proxy 是否与 ADV、turnover、Amihud-like impact 和未来流动性压力稳定对应；
3. `TailPenalty` 是否在不读取未来的前提下对应更高的 realized downside/tail risk；
4. 每个 primitive 相对简单历史均值/波动/流动性 baseline 是否有预测或校准增量；
5. calibration、coverage、monotonicity 和跨期稳定性是否成立。

M6A 在 EP22 中只做 forecast/calibration，不改变真实或反事实 portfolio weights。比较对象是：

```text
unconditional_historical_risk_rate
simple_realized_volatility_forecast
simple_ADV_or_turnover_proxy
simple_drawdown_or_tail_proxy
candidate_primitive_forecast
```

不得在 EP22 中增加：

```text
counterfactual_weight_change
continuous_NAV_sizing_replay
blocked_adjustment_replay
cost_after_sizing_utility
combined_best_primitive
signal_confidence_multiplier
regime_fit_multiplier
learned_action_policy
```

M6A 的目标是校准风险原件，不是证明收益 alpha 或仓位效用。所有 readout 必须分别给出：

- forecast / realized risk pair；
- calibration curve；
- coverage / breach rate；
- rank and bucket monotonicity；
- Brier、pinball、MAE 或与目标相符的 proper loss；
- date/block confidence interval；
- size/board/liquidity stability；
- `liquidity_capacity_proxy_only = true`。

没有订单簿、Level-2 或真实成交回报时，LiquidityCap 不能得到 executable capacity pass。若某个 primitive 通过，固定 eligibility
下的 single-primitive shadow sizing replay 必须由后续独立 exploratory requirement 启动，不属于当前 M6A component validation，
但在 EP22 数据探究范围内无需额外人工阶段授权。

### 9.3 M6B：对冲 mechanics

M6B 只验证以下命题：

1. 组合收益能否稳定分解为 market beta、style beta 与 residual；
2. market hedge 是否减少目标 market exposure；
3. style hedge 是否减少目标 style exposure；
4. 成本、基差、换月、保证金和 tracking error 是否抵消风险改善；
5. 当前数据是否足以从 shadow attribution 升级为 executable hedge validation。

### 9.4 Reference books

Reference book 必须在 outcome 前机械冻结，例如：

- PIT universe equal-weight book；
- PIT universe cap-weighted book；
- pre-registered size/style book；
- 已有候选只可作为带原有 caveat 的 secondary diagnostic cohort。

不得：

- 从已知赢家挑股票；
- 根据 risk/hedge outcome 选择 reference book；
- 使用未来 winner episode；
- 将 EP20/EP21 candidate 当作已批准策略。

M6A 的所有 calibration rows 必须共享相同 eligibility；primitive 不得改变入选股票或事件。

### 9.5 Exposure decomposition

公式骨架：

```text
R_book,t =
    alpha_hat_{t-1}
    + beta_market,t-1 * R_market,t
    + sum_s beta_style_s,t-1 * F_style_s,t
    + epsilon_t
```

所有 intercept/beta 仅用过去窗口估计。若 style factor 由 reference book 成分自建，必须使用非重叠构造或 leave-one-out，
避免 reference book 机械解释自身。M6B 分开报告：

```text
market_beta_error
style_exposure_error
idiosyncratic_residual_loss_unclassified
```

三者不得混为一个 stop/hedge signal。

### 9.6 Shadow 与 executable hedge 分开

当前已知本地 benchmark 是非交易指数序列，且未确认 ETF/期货、基差、展期和保证金数据。因此 22A 未引入并通过新的
executable-instrument contract 前，M6B 默认上限是 `synthetic_hedge_shadow`。

若只有指数现货序列：

```text
hedge_role = shadow_non_executable_attribution
```

它可以验证 exposure decomposition，但不能通过 executable hedge gate。

Executable hedge 必须有：

- 可交易 ETF 或期货合约；
- 合约/份额映射；
- actual price；
- bid/ask or conservative slippage；
- fee；
- futures multiplier；
- margin；
- expiry/roll；
- basis；
- blocked trading；
- cash collateral；
- continuous ledger。

数据不足则：

```text
executable_hedge_validation = data_blocked
```

### 9.7 M6 可证伪假设

```text
H6a:
volatility/liquidity/tail primitive 的预测风险、约束 breach 与 realized risk
在真实市场中校准。

H6b:
单项 primitive 相对简单风险 baseline 提供稳定增量，而不是同一历史波动/流动性变量的换名。

H6c:
只使用过去估计 beta 的 synthetic market hedge 在 shadow attribution 中按预期降低 realized market exposure。

H6d:
若 executable-instrument contract 通过，真实 hedge 在成本、基差、换月与保证金后仍降低目标 exposure。

H6e:
style hedge 相对 market-only hedge 对目标 style exposure 有真实增量。

H6f:
hedge effectiveness 在不同 market state 与 basis state 下可解释，而不是只在单一危机期有效。
```

“个股 thesis failure 时退出还是 hedge”在当前 EP22 中固定为：

```text
deferred_policy_construct_not_tested_in_EP22
```

EP22 没有获批的 alpha thesis、可观测 invalidation event 或实际 position ledger，只能 ex-post 分解 residual loss，不能事后把亏损
命名为 thesis failure，也不能做 oracle exit-vs-hedge replay。未来若研究，必须先独立冻结 thesis、invalidation、action time、fill 和
counterfactual ledger。

### 9.8 M6 不授权的内容

M6 即使通过，也不授权：

- 动态 hedge ratio policy；
- 综合 risk-budget score；
- signal × regime × risk multiplier；
- learned sizing policy；
- 多场景决策树；
- 杠杆；
- short individual stocks；
- portfolio optimization；
- live hedge。

它只说明单项 risk primitive 是否校准，以及某种 exposure isolation 在历史真实市场中是否可行。

---

## 10. Stage 22A：共同来源、数据与验证合同

22A 是共同数据与验证基线，不是人工授权闸门。它先做 outcome-blind source/PIT/support checkpoint；22B–22G 可以在绑定当前兼容
checkpoint 后自动继续历史探索，也可以在明确记录本地补充合同的前提下与 22A 共同迭代。

### 10.1 22A 必须回答

1. 六个模块各自哪些变量本地可得？
2. 哪些是 direct measurement，哪些只是 proxy？
3. 每个 source 的真实 PIT timestamp 能否证明？
4. 每个模块的 primary claim、outcome、horizon、baseline 和 inference unit 是什么？
5. 当前覆盖能否支持最低限度的真实市场检验？
6. 哪些模块应直接 `data_blocked`？
7. 现有历史的 split、purge、embargo 与 sample role 如何冻结？
8. multiplicity、effect-size floor 与 stability gate 如何冻结？
9. 哪些输入属于稳定 snapshot，哪些属于 working output；working input 如何 hash、标记 provisional 并限制 claim？
10. 每个模块完成后允许说什么、不允许说什么？
11. 当前每个 data gap 有哪些可试采的公开、vendor 或用户可提供 source？
12. 候选 source 是否可 PIT 重建，是否改善 construct fidelity、coverage 或 effective support？
13. 候选 source 应进入哪个 module-specific B0/B1 incremental-value attempt？

### 10.2 22A 必需 registry

建议最小输出：

- `source_claim_registry.csv`
- `source_statement_to_testable_hypothesis_map.csv`
- `data_gap_and_candidate_source_registry.csv`
- `source_discovery_and_acquisition_attempt_log.csv`
- `candidate_source_access_cost_and_license_registry.csv`
- `data_source_availability_and_pit_audit.csv`
- `candidate_source_field_coverage_profile.csv`
- `candidate_source_pit_reconstructability_audit.csv`
- `source_construct_and_support_gain_registry.csv`
- `source_incremental_value_experiment_registry.csv`
- `field_availability_timestamp_registry.csv`
- `module_estimand_registry.csv`
- `module_primary_secondary_metric_registry.csv`
- `module_baseline_registry.csv`
- `historical_split_and_sample_role_registry.csv`
- `multiplicity_family_registry.csv`
- `power_and_support_preflight.csv`
- `m1_group_taxonomy_and_source_registry.csv`
- `m1_group_membership_and_weight_pit_audit.csv`
- `m1_common_shock_date_census.csv`
- `m1_market_group_shock_episode_census.csv`
- `m1_group_reaction_asof_panel.csv`
- `m1_shock_threshold_power_and_support_preflight.csv`
- `module_research_readiness.csv`
- `claim_ceiling_registry.csv`
- `22A_source_data_availability_and_validation_contract_report.md`
- manifest、input hash audit 与 output hashes。

22A 可以完成 D0–D3；D4 empirical usefulness 由相应模块的 versioned B0/B1 attempt 读取 outcome。D3 通过不等于 D4 有用，
但 D3 阻断时不得用该 source 形成 empirical claim。

### 10.3 22A terminal states

```text
22A_contract_ready_for_selected_component_validation
22A_partial_data_ready_with_blocked_modules
22A_all_material_modules_data_blocked
22A_pit_or_construct_contract_blocked
```

22A 不得输出“六个模块全部有效”。它只能逐模块给出：

```text
exploration_ready
exploration_ready_low_power
data_blocked
construct_blocked
deferred_out_of_scope
```

这些状态表达数据与研究可行性，不表达人工授权。`exploration_ready` 的模块可以继续实现和运行本地历史诊断；
`exploration_ready_low_power` 可以尝试，但必须把低功效作为首要结论。

---

## 11. Stage 22B–22G：独立市场验证

### 11.1 独立执行原则

22B–22G 没有默认先后依赖。研究者可以只执行其中一个或几个，也可以并行试验多个方向。无需逐 requirement、逐 preoutcome、
逐 historical-outcome 请求人工批准。

每个模块 requirement 必须：

- 单独绑定 input hashes；
- 单独冻结 hypothesis；
- 单独冻结 outcome；
- 单独运行 train-only transforms；
- 单独报告 historical caveat；
- 单独给出 terminal state；
- 单独保留 config/input/code/output checkpoint 与 search-path 记录；
- 不读取其他尚未完成模块的 outcome。

### 11.2 模块预期 requirement 名称

```text
22B:
requirement_22b_observable_shock_abnormal_reaction_market_validation.md

22C:
requirement_22c_sentiment_positioning_proxy_state_market_validation.md

22D-A:
requirement_22d_a_issuer_capital_action_event_market_validation.md

22D-B:
requirement_22d_b_aggregate_capital_demand_flow_market_validation.md

22E:
requirement_22e_style_price_impact_efficiency_market_validation.md

22F:
requirement_22f_long_horizon_quality_value_market_validation.md

22G-A:
requirement_22g_a_risk_budget_primitives_validation.md

22G-B:
requirement_22g_b_beta_decomposition_and_hedge_effectiveness_validation.md
```

22D-A/22D-B 与 22G-A/22G-B 都是独立裁决的 sibling requirements。上述 roadmap 可在 EP22 探索范围内按数据可得性直接细化、
实现和运行；它不授权跨模块生产决策。

### 11.3 单模块统一 terminal states

每个模块必须落入一个互斥状态：

```text
component_directly_measurable_historically_stable
component_proxy_only_historically_informative
component_measurable_but_historically_unstable
component_historically_falsified
component_data_blocked
component_construct_invalid
component_not_evaluable_low_power
component_duplicate_research_closed
component_run_incomplete_working
```

M3A/M3B 与 M6A/M6B 都必须各自输出 terminal state；不得用 issuer supply 数据可用掩盖 aggregate flow 数据阻断，
不得用风险预算原件通过掩盖 executable hedge 数据阻断，也不得用 shadow hedge 归因结果替代 primitive 校准。

只有前两个状态可进入 `forward_freeze_candidate` 复核；仍不等于 forward support。

---

## 12. Stage 22H：量化与市场验证地图

22H 消费带版本、hash 与 lineage 的 22A–22G validated working snapshots。输入不要求 sealed，但 atlas 必须标注每个输入是
`working_checkpoint`、`validated_working_result` 还是 `formally_frozen`；working 结果不得被写成 immutable final evidence。

### 12.1 22H 输出

至少包含：

- `component_quantifiability_atlas.csv`
- `component_market_validation_atlas.csv`
- `direct_measurement_vs_proxy_registry.csv`
- `supported_falsified_blocked_hypothesis_registry.csv`
- `cross_component_comparability_limitations.csv`
- `forward_freeze_candidate_registry.csv`
- `append_only_forward_evidence_registry.csv`
- `episode_22_component_validation_final_report.md`

若存在 forward candidate，append-only registry 至少冻结：

- candidate/formula/config hash；
- exact data cutoff；
- freeze timestamp；
- first eligible forward timestamp；
- label maturity rule；
- backfill exclusion；
- minimum matured independent blocks；
- censoring rule；
- alpha-spending / repeated-look rule；
- allowed forward terminal states。

EP22 可以创建 registry，但在真实 forward labels 未成熟前不得生成正向 forward conclusion。

### 12.2 Atlas 维度

每个 module / claim 至少记录：

| 维度 | 含义 |
|---|---|
| construct validity | 是否真的测量所声称对象 |
| PIT availability | 能否按真实可用时间重建 |
| coverage | 时间、股票、事件和状态是否足够 |
| market association | 真实市场方向与效应量 |
| incremental value | 相对简单 baseline 是否有增量 |
| stability | 跨时间、board、size、state 是否稳定 |
| concentration | 是否由少数日期/股票驱动 |
| economic relevance | 效应是否超过噪声/成本数量级 |
| execution relevance | 是否只是描述，还是具有可执行时点 |
| evidence role | historical design / forward |
| claim ceiling | 最多允许说什么 |
| next action | stop / data repair / forward freeze / separate research |

### 12.3 22H 不做

- 不给六个模块加权；
- 不生成综合 score；
- 不学习 action；
- 不输出综合 risk budget、仓位动作或跨模块 sizing 公式；
- 不做 portfolio backtest；
- 不选择“最赚钱组合”；
- 不把数据更多的模块误判为理论更重要；
- 不因某模块失败而事后改写原 claim；
- 不把多个弱 p-value 合并成宏大叙事。

### 12.4 Episode 22 closure states

```text
EP22_component_atlas_complete_no_forward_candidate
EP22_component_atlas_complete_with_forward_candidates
EP22_partial_atlas_data_constraints_material
EP22_component_validation_incomplete
```

即使存在 forward candidate：

```text
decision_router_authorized = false
cross_module_model_authorized = false
position_sizing_authorized = false
portfolio_backtest_authorized = false
deployment_authorized = false
live_trading_authorized = false
```

---

## 13. 统计与稳定性最低要求

具体数值必须由 22A 在 outcome 前冻结，但每个模块至少遵守：

### 13.1 Effect size 优先

必须同时报告：

- point estimate；
- confidence interval；
- economic unit；
- baseline delta；
- sample/event/date count；
- effective independent block count；
- top-date/top-group/top-name contribution；
- missingness；
- direction stability。

不能用巨大 group-row / stock-row N 替代有效日期或事件数。

### 13.2 时间稳定性

至少报告：

- chronological folds；
- calendar-year readout；
- early/late；
- leave-one-year-out 或适配的 leave-block-out；
- market-state sensitivity；
- pre/post major market-structure period；
- forward-freeze eligibility。

### 13.3 横截面稳定性

按可用数据报告：

- main board / ChiNext；
- size；
- liquidity；
- volatility；
- ST/suspension/tradability caveat；
- concentration；
- supported style；
- industry return readout 仅在 historical industry-index source audit 通过时；
- industry breadth/dispersion/internal-structure readout 仅在 PIT membership 审计通过时。

### 13.4 Overlap 与 bootstrap

- M1 使用 market/group shock episode + date block；同一 shock-date 下的 group rows 不独立；
- M3A 使用 issuer-event/calendar block，M3B 使用 non-overlapping aggregate calendar block；
- M2 使用 state segment/calendar block；
- M4 使用 style-date block；
- M5 使用 firm + report-vintage block；
- M6A 使用 risk-forecast/date block，M6B 使用 portfolio/roll/calendar block；
- overlapping horizon 使用 HAC、purge/embargo 或 stationary/block bootstrap；
- 同一 episode 不得跨 fold。

### 13.5 Positive result gate

历史候选至少同时满足：

```text
construct gate
+ PIT/data gate
+ minimum evaluable effective-block support
+ ex-ante economic effect margin / MDE gate
+ primary direction gate
+ incremental baseline gate
+ time stability gate
+ concentration guard
+ multiplicity-adjusted inference
+ directionally correct adjusted confidence-bound gate
+ honest claim ceiling
```

22A 必须在读取 outcome 前冻结每个模块的 minimum effective blocks、economic floor/MDE、adjusted interval rule 与
`not_evaluable_low_power` terminal。点估计方向正确但低于经济 floor、区间跨过冻结 lower bound，或有效 block 不足时，
不得进入 forward candidate。

成本不是所有 descriptive module 的 hard gate，但只要 claim 涉及可执行性，必须加入 conservative cost、slippage、blocked fill 和 capacity。

---

## 14. 最小可发布证据

每个已执行模块至少发布：

1. requirement；
2. versioned config snapshot；
3. input artifact audit；
4. source/timestamp audit；
5. formula/feature registry；
6. sample denominator audit；
7. PIT/leakage audit；
8. primary baseline comparison；
9. fold/year/state readout；
10. concentration and influence audit；
11. multiplicity-adjusted inference；
12. terminal decision；
13. Chinese evidence-backed report；
14. manifest；
15. output hashes；
16. stage status registry。
17. data-gap/candidate-source/search-attempt accounting；
18. 若使用新增 source，B0 existing-data baseline 与 B1 augmented-source 的 paired comparison。

若 run 中断：

```text
status = working_or_incomplete
checkpoint_status = incomplete
```

EP22 遵守探索生命周期：

```text
working
  -> checkpointed
  -> diagnostic_complete
  -> validated_working_result
  -> optional_formal_freeze
```

中断、失败和被证伪的尝试也要保留可审计 checkpoint。普通历史数据探究不要求 sealed；只有进入正式 forward confirmation 时才创建
immutable freeze。

---

## 15. Anti-leakage / Anti-storytelling Checklist

### 15.1 通用

- [ ] Source 明确标为 practitioner narrative，不是 verified performance。
- [ ] 所有输入重新 hash，不从报告文字反推逐行数据。
- [ ] 所有字段有 observation/availability/usable time。
- [ ] close `t` 信息不在 close `t` 成交。
- [ ] current constituents / industry / fundamentals 不回填历史。
- [ ] threshold/scaler/model/state mapping 全部 train-only。
- [ ] 同 episode 不跨 fold。
- [ ] overlapping outcomes 有 purge/embargo/block inference。
- [ ] winner/MFE/MAE 只作 outcome，不参与 cohort 构造。
- [ ] validation/robustness 不用于回头选公式。
- [ ] historical evidence 标 design-contaminated/support=false。
- [ ] working EP21 outcome 不作为输入或授权。

### 15.2 M1

- [ ] Shock cutoff moments 只用 `<= t-1`。
- [ ] Market shock 同时通过预注册 magnitude 与 breadth 合同；指数集中波动不冒充 market-wide shock。
- [ ] Group expected-response beta、residual scale、membership 和权重只用 `<= t-1`。
- [ ] Group-specific residual 优先使用 rest-of-market-ex-group；无法构造时污染程度和 claim ceiling 已冻结。
- [ ] Market-only、group-only、amplification、resistance 和 index-concentrated states 互斥且 outcome-blind。
- [ ] 多 group 同向 residual 已审计 common/style-cluster，而非机械生成多个独立 industry event。
- [ ] 自建 group benchmark 使用 PIT membership；个股下钻 arm 使用 leave-one-out。
- [ ] Industry return-only 与 internal-structure 数据授权分开；current taxonomy 不回填。
- [ ] As-of group panel 在连接 future outcome 前已独立冻结并 hash。
- [ ] qfq/corporate-action gap 已审计。
- [ ] Positive/negative shock orientation pre-registered。
- [ ] G2 simple group-minus-market RS 与本次 group universe 上重建的 EP20B-SRC-like comparator 完整。
- [ ] Group layer 未通过时未用 stock-row 结果升级 M1。

### 15.3 M2

- [ ] 只用 filtered state，不用 smoothed state。
- [ ] State label mapping 在 outcome 前冻结。
- [ ] 状态 segment 不由未来转折点定义。
- [ ] Positioning 字段明确写 proxy。
- [ ] Crash-date influence 单列。

### 15.4 M3

- [ ] Announcement、eligibility、execution、completion 分开。
- [ ] Cap denominator 为 PIT，且 total/listed-circulating/official-free-float 语义不混用。
- [ ] Cancellation/revision 保留。
- [ ] 不把不同 flow 直接相加。
- [ ] Price response 不被写成投资者身份。

### 15.5 M4

- [ ] Turnover 不写成 signed flow。
- [ ] Market-cap change 不写成 cash inflow。
- [ ] Ratio 有 denominator floor 与 robust sensitivity。
- [ ] Style bucket 为 PIT/train-only。
- [ ] 头部权重贡献单列。

### 15.6 M5

- [ ] 使用 first-publication time，不用 report period end。
- [ ] Restatement/revision 有 lineage。
- [ ] Delisted/negative-equity 公司处理明确。
- [ ] ROE 做 leverage decomposition。
- [ ] Buyback authorization 与 execution 分开。

### 15.7 M6

- [ ] Volatility/liquidity/tail primitive 分开验证。
- [ ] 不生成 combined sizing arm 或 counterfactual weight replay。
- [ ] Forecast calibration、coverage 与 proper loss 完整。
- [ ] Liquidity/capacity 明确标 proxy-only。
- [ ] Hedge beta 只用过去窗口。
- [ ] Shadow 与 executable 分开。
- [ ] Basis/roll/margin/cost/collateral 完整。
- [ ] Market hedge、style hedge 与 ex-post residual attribution 分开。
- [ ] Thesis-failure exit-vs-hedge 保持 deferred，不做 oracle replay。

---

## 16. Claims Boundary

### 16.1 EP22 允许形成的结论

示例：

```text
在冻结的 PIT 历史 A 股样本中，
某 observable-shock reaction residual 相对 simple RS 存在/不存在稳定增量。

某 sentiment proxy 能/不能把未来市场分布区分为稳定状态。

某类实际执行的 supply event 与未来价格/流动性存在/不存在稳定历史关联。

某种 style 的 price/turnover relation 在控制已知暴露后仍存在/消失。

某组 PIT quality metrics 对长期 payoff/risk 有/没有稳定关系。

某个 volatility/liquidity/tail risk primitive 在固定 eligibility 下校准/不校准。

某类 shadow hedge 能/不能在非执行归因层隔离目标 beta，不附带成本后或可交易声明。

某类 executable hedge 在合约、成本、基差、展期和保证金完整时能/不能在成本后隔离目标 beta。
```

### 16.2 EP22 禁止形成的结论

```text
“14 亿元”业绩已被核验。
原交易者的方法已被完整复制。
OHLCV 识别了主力或机构行为。
资金净流入被完整测量。
小盘上涨必然更消耗资金。
某市场状态能预测唯一行情路径。
某状态或分类通过即代表可交易。
对冲能修复错误个股逻辑。
六个模块可以直接合成决策路由。
EP22 已产生部署策略。
```

### 16.3 后续研究边界

如果 22H 识别出一个或多个 `forward_freeze_candidate`，后续应优先为每个模块分别：

1. 将探索中的公式、数据源、阈值和 primary claim 正式冻结；
2. 建立 forward registry；
3. 等待真实新市场数据；
4. 独立验证；
5. 失败即关闭或降级。

只有多个组件各自获得独立 forward support 后，未来才可以另行发起“是否组合”的研究。该组合不属于 EP22 常规数据探究范围，
需要明确扩展项目范围。

---

## 17. EP22 的最小成功定义

EP22 不要求六个模块都有效。其最小成功是：

```text
1. 把 practitioner narrative 拆成清晰、互不偷换的 testable claims；
2. 说明每个 claim 是 direct measurement、proxy 还是当前 data-blocked；
3. 用真实 A 股市场数据对已可测 claim 做诚实的历史验证；
4. 明确哪些 claim 被证伪、哪些不稳定、哪些值得 forward freeze；
5. 不把描述性关系升级成策略；
6. 不构造完整决策路由。
```

最终判断标准不是“找到一个漂亮回测”，而是：

> **把一个宽泛的交易叙事压缩成可测量、可失败、可复现、可继续或可停止的真实市场证据地图。**
