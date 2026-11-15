# V3 M04：过程参考加权没有解决覆盖与及时性的共同目标

## 想验证什么

训练按行业周计损失，而业务按唯一改善过程评价。较长过程可能多次出现在正例中。本轮只改变正例权重：在每个历史训练时点，按当时已成熟的前缀过程参考均衡正例总权重，保留负例逐行权重及正负两类总权重。未使用未来最终过程编号；标签、10项特征、模型参数、固定等权组合及池规则不变。

事前方案为 `protocols/v3_r00/m04_process_weight_plan.md`。沿用50%研究参考，不作为硬筛除或验收线。

## 结论

**不采用过程加权为新主方法，停止这一固定权重分支。** 配对主档中，覆盖模型多覆盖2个过程、多及时发现23个，但独立运行时少覆盖14个、多及时发现15个；组合模型独立运行覆盖少11个、及时发现少8个。早期模型则多覆盖27个、少及时发现16个。没有稳定的共同改善，不搜索组权重指数、窗口或混合比例。

相对20日动量，过程加权组合独立运行多发20次新增提示，却少覆盖66个过程、多及时发现184个。它仍是以部分整体覆盖和提示质量换及时性，不能宣称实现完整目标。

## 样本和口径

2020-01-03至2026-10-16，343个支持周、5个分类边界未知周。全部方法使用同一4540个父改善过程和458个增强过程，不按准入和候选名单缩小分母。包括170个在2019年开始、与评价期重叠的父过程；年度分层按过程起始年，不代表2019年进行了模型评价。原始价格截至2026-10-21。

14次年度拟合，42条七臂等新增负担重放（1/3/5上限×0/1额外确认），另7条独立5/20重放。主配对档各992个NEW。独立运行新增量不同，因此只在配对中解释同新增负担增量。UPDATE工作量另报，配对并不使更新量完全一致。

有效率是E02成熟可评价唯一NEW的过程匹配率，不是提示后上涨概率。父过程覆盖含NEW和有对应证据的UPDATE去重并集；父子分别计数。未知从有效率已知分母中单列，不作失败。及时定义及事后起点均沿用冻结协议，不进入信号。

## 主档完整结果

DATE代表原日期均衡训练权重；PROCESS代表本轮正例参考均衡。COVER为覆盖目标，EARLY为早期父/子联合目标，BALANCED为固定等权百分位组合。

| run_id | new_total | new_unknown | new_effective_rate | parent_covered | parent_timely | parent_late | child_covered | lag_p50 | pre_gain_p50 |
|---|---|---|---|---|---|---|---|---|---|
| q5_d0_DATE_BALANCED | 992 | 16 | 82.58% | 896 | 558 | 338 | 124 | 15.0 | 13.49% |
| q5_d0_DATE_COVER | 992 | 10 | 86.25% | 932 | 403 | 529 | 175 | 25.0 | 19.78% |
| q5_d0_DATE_EARLY | 992 | 20 | 70.37% | 769 | 582 | 187 | 75 | 10.0 | 8.87% |
| q5_d0_ORIGINAL20 | 992 | 11 | 88.38% | 949 | 372 | 577 | 172 | 25.0 | 19.52% |
| q5_d0_PROCESS_BALANCED | 992 | 14 | 82.41% | 903 | 563 | 340 | 129 | 15.0 | 13.89% |
| q5_d0_PROCESS_COVER | 992 | 11 | 86.65% | 934 | 426 | 508 | 178 | 21.0 | 19.27% |
| q5_d0_PROCESS_EARLY | 992 | 21 | 72.50% | 798 | 573 | 225 | 88 | 10.0 | 10.34% |
| solo_DATE_BALANCED | 1067 | 18 | 81.98% | 955 | 591 | 364 | 135 | 15.0 | 13.19% |
| solo_DATE_COVER | 1068 | 9 | 86.59% | 1002 | 441 | 561 | 194 | 24.5 | 18.99% |
| solo_DATE_EARLY | 1130 | 26 | 68.75% | 846 | 640 | 206 | 87 | 10.0 | 8.82% |
| solo_ORIGINAL20 | 1055 | 11 | 88.79% | 1010 | 399 | 611 | 184 | 25.0 | 19.00% |
| solo_PROCESS_BALANCED | 1075 | 15 | 80.47% | 944 | 583 | 361 | 136 | 15.0 | 13.66% |
| solo_PROCESS_COVER | 1062 | 12 | 85.52% | 988 | 456 | 532 | 185 | 21.0 | 17.93% |
| solo_PROCESS_EARLY | 1111 | 30 | 71.69% | 873 | 624 | 249 | 101 | 10.0 | 9.89% |

发现延迟中位数相对事后父过程参考起点计算，仅对已覆盖过程；不能把遗漏过程从这一中位数消失解释为整体更早。过程加权组合独立运行覆盖944/4540=20.79%，及时583/4540=12.84%；动量为1010/4540=22.25%、399/4540=8.79%。

## 配对不确定性

共同13周循环时间块，2000次，种子34104；下表差异和区间单位为百分点。只覆盖这套冻结历史标签和方案下的条件不确定性，不包括模型选择、标签选择及历史反复使用风险，不是独立样本外证明。

| comparison | metric | difference | lo95 | hi95 |
|---|---|---|---|---|
| q5_d0_PROCESS_COVER minus q5_d0_DATE_COVER | parent_coverage | 0.044 | -0.307 | 0.439 |
| q5_d0_PROCESS_COVER minus q5_d0_DATE_COVER | timely_coverage | 0.507 | 0.222 | 0.811 |
| q5_d0_PROCESS_COVER minus q5_d0_DATE_COVER | new_matching_rate | 0.394 | -0.509 | 1.209 |
| q5_d0_PROCESS_COVER minus q5_d0_DATE_COVER | child_coverage | 0.655 | -0.433 | 1.866 |
| q5_d0_PROCESS_EARLY minus q5_d0_DATE_EARLY | parent_coverage | 0.639 | -0.021 | 1.313 |
| q5_d0_PROCESS_EARLY minus q5_d0_DATE_EARLY | timely_coverage | -0.198 | -0.660 | 0.252 |
| q5_d0_PROCESS_EARLY minus q5_d0_DATE_EARLY | new_matching_rate | 2.132 | 0.048 | 4.265 |
| q5_d0_PROCESS_EARLY minus q5_d0_DATE_EARLY | child_coverage | 2.838 | -0.517 | 6.010 |
| q5_d0_PROCESS_BALANCED minus q5_d0_DATE_BALANCED | parent_coverage | 0.154 | -0.254 | 0.597 |
| q5_d0_PROCESS_BALANCED minus q5_d0_DATE_BALANCED | timely_coverage | 0.110 | -0.188 | 0.405 |
| q5_d0_PROCESS_BALANCED minus q5_d0_DATE_BALANCED | new_matching_rate | -0.169 | -1.370 | 1.133 |
| q5_d0_PROCESS_BALANCED minus q5_d0_DATE_BALANCED | child_coverage | 1.092 | -2.174 | 4.441 |
| q5_d0_PROCESS_BALANCED minus q5_d0_ORIGINAL20 | parent_coverage | -1.013 | -1.850 | -0.090 |
| q5_d0_PROCESS_BALANCED minus q5_d0_ORIGINAL20 | timely_coverage | 4.207 | 3.238 | 5.420 |
| q5_d0_PROCESS_BALANCED minus q5_d0_ORIGINAL20 | new_matching_rate | -5.966 | -8.841 | -3.240 |
| q5_d0_PROCESS_BALANCED minus q5_d0_ORIGINAL20 | child_coverage | -9.389 | -15.442 | -5.263 |
| solo_PROCESS_COVER minus solo_DATE_COVER | parent_coverage | -0.308 | -0.775 | 0.116 |
| solo_PROCESS_COVER minus solo_DATE_COVER | timely_coverage | 0.330 | 0.046 | 0.611 |
| solo_PROCESS_COVER minus solo_DATE_COVER | new_matching_rate | -1.067 | -2.250 | -0.065 |
| solo_PROCESS_COVER minus solo_DATE_COVER | child_coverage | -1.965 | -3.572 | -0.245 |
| solo_PROCESS_EARLY minus solo_DATE_EARLY | parent_coverage | 0.595 | -0.180 | 1.423 |
| solo_PROCESS_EARLY minus solo_DATE_EARLY | timely_coverage | -0.352 | -0.943 | 0.228 |
| solo_PROCESS_EARLY minus solo_DATE_EARLY | new_matching_rate | 2.943 | 1.141 | 4.849 |
| solo_PROCESS_EARLY minus solo_DATE_EARLY | child_coverage | 3.057 | -0.191 | 6.516 |
| solo_PROCESS_BALANCED minus solo_DATE_BALANCED | parent_coverage | -0.242 | -0.841 | 0.330 |
| solo_PROCESS_BALANCED minus solo_DATE_BALANCED | timely_coverage | -0.176 | -0.619 | 0.231 |
| solo_PROCESS_BALANCED minus solo_DATE_BALANCED | new_matching_rate | -1.511 | -2.931 | -0.026 |
| solo_PROCESS_BALANCED minus solo_DATE_BALANCED | child_coverage | 0.218 | -2.556 | 2.680 |
| solo_PROCESS_BALANCED minus solo_ORIGINAL20 | parent_coverage | -1.454 | -2.506 | -0.371 |
| solo_PROCESS_BALANCED minus solo_ORIGINAL20 | timely_coverage | 4.053 | 3.120 | 5.135 |
| solo_PROCESS_BALANCED minus solo_ORIGINAL20 | new_matching_rate | -8.321 | -11.778 | -5.071 |
| solo_PROCESS_BALANCED minus solo_ORIGINAL20 | child_coverage | -10.480 | -15.740 | -6.929 |

配对组合的覆盖与及时性小幅改善区间均跨0，独立运行两项点估计均下降。不能将“差异不显著”解释为非劣或成功。覆盖模型配对及时性增量有支持，但没有可靠整体覆盖增量。

## 分层和等待代价

独立过程组合相对原日期组合，在2022、2023、2024、2025起始过程上的覆盖分别减少4、4、4、4个，仅2020增加1个、2026增加5个；及时性在2021、2022、2024、2025分别减少2、3、4、6个。改善不跨期稳定。

弱势背景3616个过程：日期组合覆盖709、及时414，过程组合698、405；已不弱背景924个：246、177与246、178。弱势回暖没有受益。此前已不弱的父过程不等同于H04D新增增强；增强458个独立报告。

所有年度、此前状态、市场环境的49条分层结果见 `all_grid_strata.csv`。所有容量及等待档实际结果见 `all_grid_metrics.csv` 和 `actual_quality_coverage_points.csv`；不插值构造精确同质量比较。配对主档多等一次确认后，过程组合少59个NEW、少39个覆盖、少56个及时发现，有效率仅增加0.87个百分点；确认等待不能当作信息增量。


各配对档相对原日期权重的变化如下，顺序为“覆盖变化／及时变化／有效率百分点变化”。低容量档的局部收益同样保留，不能只报主档。

| 上限/等待 | COVER | EARLY | BALANCED |
|---|---|---|---|
| 1/0 | +6 / +12 / +1.20 | +12 / +4 / +4.22 | -4 / -15 / +0.88 |
| 1/1 | +5 / +6 / -0.02 | +5 / -5 / +1.50 | +1 / -10 / +1.83 |
| 3/0 | -4 / +18 / -1.15 | +18 / -1 / +2.17 | -6 / -13 / +0.26 |
| 3/1 | +4 / +18 / -0.13 | -2 / -26 / -0.27 | +4 / -5 / +1.12 |
| 5/0 | +2 / +23 / +0.39 | +29 / -9 / +2.13 | +7 / +5 / -0.17 |
| 5/1 | +0 / +15 / -0.66 | +8 / -7 / +0.71 | +13 / +9 / +0.38 |

## 负担与提示阶段

七条独立池的在池中位数及90分位均为20；新增90分位均为5，EARLY两版新增中位数4，其余3。所有上限均需独立核验。原日期组合更新5231次，过程组合5210次；动量5170次。

过程组合有效NEW中确认前提示502次，日期组合494次，动量330次；该计数只针对最终匹配成功的NEW，不等于所有早期提示成功，也不能替代完整及时覆盖分母。未知分别15、18、11次，重复NEW分别25、32、36次，完整状态在E02各run摘要保留。

## 权重变化及限制

2026覆盖目标45236个训练行，33284个正例，4987个前缀参考；早期联合目标13955个正例、5388个参考。参考不是独立市场机会，前缀身份修订仍可能将一个最终过程拆成多个训练参考。

负例逐行权重和两类总权重保持不变，StandardScaler与原模型逐项相同。但日期总权重不再均衡：2026覆盖目标日期质量比10/90分位0.586/1.484，最大2.684；早期目标0.794/1.199，最大2.768。此次结果不能解释为完全消除了所有重复或市场拥挤效应。

## 入池后表现

全部7条独立池的每个NEW均跟踪20/60/90/180交易日，保留成熟、未成熟、数据或分类缺口。下列收益与超额单位为%；超额是行业收益减CSI_ALL收益，非几何相对收益。仅作后续价值追踪，未用于标签、权重或选模型。

| run_id | horizon | total | mature | immature | gap | absolute_mean | absolute_median | excess_mean | excess_median |
|---|---|---|---|---|---|---|---|---|---|
| solo_DATE_BALANCED | 20 | 1067 | 1038 | 19 | 10 | 0.70 | -0.23 | -0.00 | -0.77 |
| solo_DATE_BALANCED | 60 | 1067 | 978 | 42 | 47 | 2.98 | 0.44 | 0.58 | -0.71 |
| solo_DATE_BALANCED | 90 | 1067 | 935 | 69 | 63 | 5.22 | 1.97 | 1.32 | -0.70 |
| solo_DATE_BALANCED | 180 | 1067 | 815 | 133 | 119 | 10.53 | 5.38 | 3.16 | -0.97 |
| solo_DATE_COVER | 20 | 1068 | 1044 | 19 | 5 | 0.50 | -0.64 | -0.19 | -1.38 |
| solo_DATE_COVER | 60 | 1068 | 987 | 42 | 39 | 1.92 | -0.35 | -0.39 | -2.19 |
| solo_DATE_COVER | 90 | 1068 | 946 | 65 | 57 | 4.79 | 1.15 | 0.99 | -1.53 |
| solo_DATE_COVER | 180 | 1068 | 825 | 127 | 116 | 9.90 | 4.87 | 2.67 | -1.46 |
| solo_DATE_EARLY | 20 | 1130 | 1095 | 22 | 13 | 0.71 | -0.15 | -0.04 | -0.79 |
| solo_DATE_EARLY | 60 | 1130 | 1033 | 48 | 49 | 3.08 | 0.65 | 0.65 | -0.58 |
| solo_DATE_EARLY | 90 | 1130 | 986 | 76 | 68 | 4.89 | 0.97 | 1.09 | -1.10 |
| solo_DATE_EARLY | 180 | 1130 | 862 | 146 | 122 | 9.73 | 4.73 | 2.24 | -1.86 |
| solo_ORIGINAL20 | 20 | 1055 | 1031 | 16 | 8 | 0.42 | -0.77 | -0.39 | -1.57 |
| solo_ORIGINAL20 | 60 | 1055 | 977 | 37 | 41 | 2.58 | 0.22 | 0.02 | -1.80 |
| solo_ORIGINAL20 | 90 | 1055 | 935 | 60 | 60 | 4.93 | 2.22 | 1.27 | -1.21 |
| solo_ORIGINAL20 | 180 | 1055 | 812 | 124 | 119 | 9.57 | 4.35 | 2.47 | -1.51 |
| solo_PROCESS_BALANCED | 20 | 1075 | 1045 | 20 | 10 | 0.48 | -0.33 | -0.27 | -1.12 |
| solo_PROCESS_BALANCED | 60 | 1075 | 989 | 42 | 44 | 2.65 | 0.07 | 0.22 | -1.13 |
| solo_PROCESS_BALANCED | 90 | 1075 | 946 | 70 | 59 | 4.91 | 1.27 | 0.96 | -1.08 |
| solo_PROCESS_BALANCED | 180 | 1075 | 823 | 135 | 117 | 10.51 | 5.67 | 3.03 | -1.08 |
| solo_PROCESS_COVER | 20 | 1062 | 1035 | 18 | 9 | 0.57 | -0.51 | -0.17 | -1.31 |
| solo_PROCESS_COVER | 60 | 1062 | 977 | 40 | 45 | 2.17 | -0.23 | -0.17 | -1.94 |
| solo_PROCESS_COVER | 90 | 1062 | 937 | 63 | 62 | 5.12 | 1.07 | 1.26 | -1.34 |
| solo_PROCESS_COVER | 180 | 1062 | 819 | 124 | 119 | 10.12 | 4.65 | 2.84 | -1.18 |
| solo_PROCESS_EARLY | 20 | 1111 | 1077 | 19 | 15 | 0.44 | -0.23 | -0.32 | -0.91 |
| solo_PROCESS_EARLY | 60 | 1111 | 1021 | 45 | 45 | 2.54 | -0.05 | 0.19 | -1.44 |
| solo_PROCESS_EARLY | 90 | 1111 | 972 | 74 | 65 | 4.49 | 0.64 | 0.72 | -1.56 |
| solo_PROCESS_EARLY | 180 | 1111 | 848 | 143 | 120 | 9.72 | 4.28 | 2.14 | -2.40 |

## 全量遗漏对账

过程组合独立运行遗漏3596/4540个父过程。与动量共同覆盖547个，模型独有397个，动量独有463个，两者均遗漏3133个；净少66个，不是只展示成功案例。

遗漏过程的观察约束集合：仅冷却21；冷却加池容量1；冷却加池容量加周排名184；无支持的正向对应证据1；仅池容量1；池容量加周排名3383；仅周排名5，总计3596。集合内约束可能发生在同一过程的不同周，不表示某一规则单独造成全部遗漏，也不能据此断言放宽容量就能捕获。全部49条的名单、约束和覆盖变迁均保留。

## 核验与下一步

105项测试通过。独立审计通过：621个哈希引用、49条重放、259843条事件、6组配对及7条独立池；逐条重建准入排序和容量，核对全部遗漏过程和所有独立池NEW的四个后续期限，检查14次拟合的成熟性及权重守恒。结果在 `outputs/v3_m04_comparison/independent_audit.json`。技术通过不代表业务目标完成。

下一步先汇总现有分支的业务证据与遗漏结构，判断是否存在尚未回答的必要比较。必须先找具体机制或信息缺口，再登记实验；本轮不追加模型、权重或窗口。尚未找到在5/20内稳定同时提高整体覆盖和及时性的获验证方法，完整goal保持未完成。

## 证据位置

- `outputs/v3_m04_models/`：14次拟合、逐行权重、系数和来源收据。
- `outputs/v3_m04_replay/`：49条全目录逐期状态和全部事件。
- `outputs/evaluation_versions/v3_m04/`：完整过程分母、匹配、质量及负担。
- `outputs/v3_m04_comparison/`：全部档位、分层、时间块区间、等待代价及后续路径。
- `outputs/v3_m04_decisions/`：线上排序复核、所有遗漏过程及相对基线覆盖变迁。
