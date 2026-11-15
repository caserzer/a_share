# M07：当前竞争候选的一次确认等待代价

## 结论

保留原NOW候选，不把WAIT升级为主方案。模型独立等待一次：少96次新增、少52个父过程覆盖、少75个及时发现，有效率增加1.59个百分点但区间包含0；在相同1549次新增的配对中，两版有效率完全相同，等待少及时40个。等待不是免费提高质量，也不是新增信息。

动量结果更复杂：独立等待少91次新增、少58个父覆盖、少18个及时；等新增配对时少9个总覆盖但多23个及时。因此不能把等待描述为所有路径都机械变晚；选择和池维护会改变后续覆盖。其独立总覆盖仍下降，不支持共同目标改善。

## 唯一变更与样本

沿用冻结M02评分、5/20竞争池与E02B完整4540父/458子分母。WAIT仅对新候选要求相邻同链上次复核也满足基础准入；不要求上次排名靠前，不改变存续池优先级、更新、退出、8周上限或4周冷却。所有NOW独立事件复现M06（版本ID除外）。

独立四条，1/3/5新增上限等新增配对12条，共16条。没有测试第二个等待长度，也不搜索阈值。本轮为补足最终竞争规则的确认代价，不覆盖原静态池历史结果。

## 主档完整结果

| run_id | new_total | new_unknown | new_effective_rate | parent_covered | parent_timely | parent_late | child_covered | lag_p50 |
|---|---|---|---|---|---|---|---|---|
| q5_d0_BALANCED_NOW_COMPETE | 1549 | 18 | 82.30% | 1328 | 765 | 563 | 176 | 18.0 |
| q5_d0_BALANCED_WAIT_COMPETE | 1549 | 18 | 82.30% | 1324 | 725 | 599 | 186 | 20.0 |
| q5_d0_BROAD20_NOW_COMPETE | 1549 | 13 | 85.55% | 1386 | 514 | 872 | 249 | 24.0 |
| q5_d0_BROAD20_WAIT_COMPETE | 1549 | 6 | 85.03% | 1377 | 537 | 840 | 243 | 24.0 |
| solo_BALANCED_NOW_COMPETE | 1651 | 23 | 80.65% | 1380 | 804 | 576 | 176 | 18.0 |
| solo_BALANCED_WAIT_COMPETE | 1555 | 18 | 82.24% | 1328 | 729 | 599 | 186 | 20.0 |
| solo_BROAD20_NOW_COMPETE | 1648 | 18 | 84.29% | 1440 | 554 | 886 | 254 | 23.0 |
| solo_BROAD20_WAIT_COMPETE | 1557 | 6 | 84.98% | 1382 | 536 | 846 | 243 | 24.0 |

模型等待的增强覆盖176→186，收益也保留；不能只展示及时损失。但子过程增量区间跨0，且父及时性有明确下降，不据此自动改主池。模型已覆盖过程的延迟中位数18→20交易日；遗漏保持在覆盖分母中，不从延迟中位数推断全体过程。

## 条件区间

下表为WAIT减NOW，单位百分点；共同13周块、2000次、事前种子34107。只描述当前重用历史和固定方案下的不确定性，不包含全部方案选择或标签修订风险。

| comparison | metric | difference | lo95 | hi95 |
|---|---|---|---|---|
| q5_d0_BALANCED_WAIT_COMPETE minus q5_d0_BALANCED_NOW_COMPETE | parent_coverage | -0.088 | -0.793 | 0.529 |
| q5_d0_BALANCED_WAIT_COMPETE minus q5_d0_BALANCED_NOW_COMPETE | timely_coverage | -0.881 | -1.489 | -0.359 |
| q5_d0_BALANCED_WAIT_COMPETE minus q5_d0_BALANCED_NOW_COMPETE | new_matching_rate | 0.000 | -1.324 | 1.338 |
| q5_d0_BALANCED_WAIT_COMPETE minus q5_d0_BALANCED_NOW_COMPETE | child_coverage | 2.183 | -0.485 | 5.469 |
| q5_d0_BROAD20_WAIT_COMPETE minus q5_d0_BROAD20_NOW_COMPETE | parent_coverage | -0.198 | -0.737 | 0.332 |
| q5_d0_BROAD20_WAIT_COMPETE minus q5_d0_BROAD20_NOW_COMPETE | timely_coverage | 0.507 | 0.000 | 1.045 |
| q5_d0_BROAD20_WAIT_COMPETE minus q5_d0_BROAD20_NOW_COMPETE | new_matching_rate | -0.518 | -1.578 | 0.579 |
| q5_d0_BROAD20_WAIT_COMPETE minus q5_d0_BROAD20_NOW_COMPETE | child_coverage | -1.310 | -3.393 | 0.655 |
| solo_BALANCED_WAIT_COMPETE minus solo_BALANCED_NOW_COMPETE | parent_coverage | -1.145 | -1.968 | -0.443 |
| solo_BALANCED_WAIT_COMPETE minus solo_BALANCED_NOW_COMPETE | timely_coverage | -1.652 | -2.376 | -1.000 |
| solo_BALANCED_WAIT_COMPETE minus solo_BALANCED_NOW_COMPETE | new_matching_rate | 1.587 | -0.081 | 3.325 |
| solo_BALANCED_WAIT_COMPETE minus solo_BALANCED_NOW_COMPETE | child_coverage | 2.183 | -0.469 | 5.001 |
| solo_BROAD20_WAIT_COMPETE minus solo_BROAD20_NOW_COMPETE | parent_coverage | -1.278 | -1.970 | -0.635 |
| solo_BROAD20_WAIT_COMPETE minus solo_BROAD20_NOW_COMPETE | timely_coverage | -0.396 | -0.996 | 0.188 |
| solo_BROAD20_WAIT_COMPETE minus solo_BROAD20_NOW_COMPETE | new_matching_rate | 0.683 | -0.546 | 1.931 |
| solo_BROAD20_WAIT_COMPETE minus solo_BROAD20_NOW_COMPETE | child_coverage | -2.402 | -4.312 | -0.583 |

## 完整账目和核验

`outputs/v3_m07_comparison/`保留所有1/3/5档、年度/此前状态/市场环境分层、提示质量/未知/重复、时机、观察负担和四个期限后续路径。`outputs/v3_m07_audit/all_process_transitions.parquet`保留WAIT新覆盖、NOW独有及双方遗漏的父子完整清单，不只展示获益过程。

114项测试通过。独立审计核对16条联合排序、只对新候选施加确认、替换对象、UPDATE/EXIT互斥、冷却及容量；确认字段还从完整目录相邻同链复核条件重新计算验证。所有独立NEW的20/60/90/180日路径逐ID核对。后续收益不用于选是否等待。

## 停止与交付

当前竞争候选的确认代价缺项已补齐，停止这个分支，不因结果再尝试更多确认周数。原候选清单和已提出的模型/动量取舍保持不变。

研究与本地交付的技术项目已完成本轮登记核验；仍不能把模型在弱势中的及时优势说成全行业、所有过程类型全面占优。主池选择及成本取舍仍待用户决定，不据约50%研究参考或测试通过自行宣布目标完成。
