# M06：同新增负担下，模型有早期信息价值，但不全面优于动量

## 结论与业务含义

竞争维护实际生效、每臂每周新增相同且主档各1615次时，组合模型覆盖1360、及时786；同准入20日动量覆盖1421、及时533；10个事前固定随机种子均值1208.4、553。

模型相对随机平均多覆盖151.6个、多及时233个，质量提高9.46个百分点；2020—2026各起始年度的覆盖与及时数均高于随机平均。这支持冻结模型排序有额外信息，而不是所有收益都来自增加周转。

但模型相对同准入动量少覆盖61个、多及时253个，提示有效率低3.63个百分点，增强过程少覆盖78个。总覆盖差区间跨0不代表非劣已证；增强覆盖差有明确负面证据。不能称模型全面更好，也不能把回暖的收益冒充强势中新增强的改善。

当前证据支持保留两个有明确取舍的研究候选：组合竞争偏早期发现，动量竞争偏总覆盖和增强。尚未自动选定唯一主池或宣称完整目标完成。

## 固定设计

13臂全部使用M05竞争维护：原准入动量、宽准入动量、冻结组合以及10个固定随机种子。宽准入动量、模型和随机共享r5正及40日支持；原动量另要求r20正。随机排名用事前341060—341069种子及当时日期/行业身份哈希生成，每周更新；仍保留相同价格准入和退出，并不是完全没有价格信息。

39条1/3/5上限配对、13条独立5/20，共52条。所有标签沿用E02B，完整4540父过程和458增强过程不变，343支持周与5边界未知周不混记。无新拟合、无随机种子筛选、无参数搜索。

## 同新增主档完整结果

| run_id | new_total | new_unknown | new_effective_rate | parent_covered | parent_timely | child_covered | lag_p50 |
|---|---|---|---|---|---|---|---|
| q5_d0_BALANCED_COMPETE | 1615 | 23 | 81.34% | 1360 | 786 | 176 | 18.0 |
| q5_d0_BROAD20_COMPETE | 1615 | 18 | 84.97% | 1421 | 533 | 254 | 24.0 |
| q5_d0_ORIGINAL20_COMPETE | 1615 | 17 | 84.79% | 1417 | 530 | 255 | 24.0 |
| q5_d0_RANDOM00_COMPETE | 1615 | 26 | 71.93% | 1217 | 578 | 130 | 20.0 |
| q5_d0_RANDOM01_COMPETE | 1615 | 37 | 72.56% | 1202 | 560 | 124 | 21.5 |
| q5_d0_RANDOM02_COMPETE | 1615 | 24 | 72.66% | 1221 | 552 | 123 | 21.0 |
| q5_d0_RANDOM03_COMPETE | 1615 | 27 | 69.77% | 1183 | 547 | 135 | 20.0 |
| q5_d0_RANDOM04_COMPETE | 1615 | 30 | 71.55% | 1203 | 555 | 123 | 22.0 |
| q5_d0_RANDOM05_COMPETE | 1615 | 30 | 72.24% | 1205 | 549 | 124 | 20.0 |
| q5_d0_RANDOM06_COMPETE | 1615 | 24 | 71.34% | 1209 | 559 | 117 | 21.0 |
| q5_d0_RANDOM07_COMPETE | 1615 | 27 | 72.54% | 1222 | 540 | 137 | 23.0 |
| q5_d0_RANDOM08_COMPETE | 1615 | 26 | 71.49% | 1205 | 543 | 133 | 21.0 |
| q5_d0_RANDOM09_COMPETE | 1615 | 26 | 72.75% | 1217 | 547 | 131 | 21.0 |

随机10种子的父覆盖范围1183—1222，及时540—578，有效率69.77%—72.75%。模型786个及时覆盖不是提前天数；相对参考起点延迟中位数为18交易日，动量24日，且中位数只含已覆盖过程，遗漏仍在完整覆盖分母中。

主档实际竞争退出模型904次、宽动量888次、原动量891次；随机652—698次。新增相同不代表持续更新及退出负担完全相同，完整库存/更新/重复/未知在逐run摘要和主指标表中保留。

## 事前比较的条件区间

13周共同时间块、2000次、种子34106。下表为百分点差。随机平均在每次时间块内分别计算10个种子的率再平均；没有把10条随机路径当10倍独立市场样本。区间不包含历史方案选择、标签选择及全部随机种子空间的不确定性。

| comparison | metric | difference | lo95 | hi95 |
|---|---|---|---|---|
| q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE | parent_coverage | -1.344 | -2.764 | 0.163 |
| q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE | timely_coverage | 5.573 | 4.268 | 7.226 |
| q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE | new_matching_rate | -3.628 | -6.525 | -0.799 |
| q5_d0_BALANCED_COMPETE minus q5_d0_BROAD20_COMPETE | child_coverage | -17.031 | -22.507 | -12.695 |
| q5_d0_BROAD20_COMPETE minus q5_d0_ORIGINAL20_COMPETE | parent_coverage | 0.088 | 0.021 | 0.178 |
| q5_d0_BROAD20_COMPETE minus q5_d0_ORIGINAL20_COMPETE | timely_coverage | 0.066 | 0.000 | 0.148 |
| q5_d0_BROAD20_COMPETE minus q5_d0_ORIGINAL20_COMPETE | new_matching_rate | 0.178 | -0.271 | 0.573 |
| q5_d0_BROAD20_COMPETE minus q5_d0_ORIGINAL20_COMPETE | child_coverage | -0.218 | -1.188 | 0.643 |
| q5_d0_BALANCED_COMPETE minus q5_d0_ORIGINAL20_COMPETE | parent_coverage | -1.256 | -2.682 | 0.258 |
| q5_d0_BALANCED_COMPETE minus q5_d0_ORIGINAL20_COMPETE | timely_coverage | 5.639 | 4.309 | 7.271 |
| q5_d0_BALANCED_COMPETE minus q5_d0_ORIGINAL20_COMPETE | new_matching_rate | -3.449 | -6.354 | -0.637 |
| q5_d0_BALANCED_COMPETE minus q5_d0_ORIGINAL20_COMPETE | child_coverage | -17.249 | -22.252 | -13.309 |
| q5_d0_BALANCED_COMPETE minus q5_d0_RANDOM_MEAN | parent_coverage | 3.339 | 2.066 | 4.806 |
| q5_d0_BALANCED_COMPETE minus q5_d0_RANDOM_MEAN | timely_coverage | 5.132 | 3.935 | 6.668 |
| q5_d0_BALANCED_COMPETE minus q5_d0_RANDOM_MEAN | new_matching_rate | 9.461 | 7.084 | 11.850 |
| q5_d0_BALANCED_COMPETE minus q5_d0_RANDOM_MEAN | child_coverage | 10.546 | 7.115 | 14.672 |
| q5_d0_BROAD20_COMPETE minus q5_d0_RANDOM_MEAN | parent_coverage | 4.683 | 3.413 | 6.251 |
| q5_d0_BROAD20_COMPETE minus q5_d0_RANDOM_MEAN | timely_coverage | -0.441 | -1.588 | 0.750 |
| q5_d0_BROAD20_COMPETE minus q5_d0_RANDOM_MEAN | new_matching_rate | 13.088 | 9.629 | 16.736 |
| q5_d0_BROAD20_COMPETE minus q5_d0_RANDOM_MEAN | child_coverage | 27.576 | 23.080 | 33.619 |

宽动量相对原动量仅多覆盖4个、及时3个，单独放宽r20准入不是主要解释。宽动量相对随机平均的及时覆盖差区间跨0，不能把它的高匹配质量称为明确早期发现能力。

## 回暖、升温与跨时期

此前弱势背景3616个父过程：模型覆盖1038、及时580，宽动量1049、322；主要及时收益集中于这里。此前已不弱背景924个：模型322、206，宽动量372、211，模型同时少覆盖50个和少及时5个。H04D增强另计：模型176、宽动量254，不能用弱势回暖收益冲销这一缺口。

2020—2026每个起始年度模型相对随机平均总覆盖分别增加25.2、19.2、13.2、26.5、31.2、19.7、14.7个；及时分别增加31.4、37.9、38.2、36.7、32.5、24.4、29.8个。2019左边界170个过程单列，不称2019训练验证。

完整年度、此前状态、市场环境分层见 `all_grid_strata.csv`，1/3/5实际质量点见 `all_grid_metrics.csv`，每个随机种子及均值/最小/最大见 `random_seed_summary.csv`。没有精确共同质量点时不插值声称同准确率提升。

## 独立运行与后续路径

组合独立1651个NEW、覆盖1380、及时804；原动量1615、1417、530，完整复现M05。各独立方案的实际新增不同，不将差异全解释为排序能力。随机独立新增1649—1654，父覆盖1207—1244、及时563—596，全部种子保留。

全部13条独立方案NEW的20/60/90/180日绝对与算术超额均值/中位数、成熟和缺口数在 `main_followup.csv`；逐提示路径完整保存且逐ID核验。未来收益不参与选择标签、种子或排名。

## 审计和剩余工作

110项测试通过，包括随机分数前缀/行序稳定、不同种子顺序、竞争资格和冷却。52条重放的独立审计逐周重建当日候选及在池联合排序、替换、UPDATE/EXIT互斥、容量与配对新增；M05两条确定性独立事件精确复现（版本ID除外）。过程得失完整记录在 `outputs/v3_m06_audit/all_process_transitions.parquet`。

本轮完成了被M05退化配对遗漏的必要比较，不据此继续搜索混合权重或状态阈值。下一步固定这两个候选的规则和证据边界，完成可解释逐期全目录清单、失效/未知说明及持续评价机制，并对完整目标逐项验收。展示候选取舍不等于替用户确认唯一主池，技术检查不等于获验证方法。
