# B01-D 遗漏和迟到机制分解

本诊断不修改标签或方法、不构造未来最优成绩。按事前登记的优先顺序，为每个过程记录最接近可提示的一次机会，同时保存全部19,590个活跃周机会。

全部2,776个过程均可与原覆盖台账对上：实际有效事件存在与587个已覆盖一致；及时窗口事件存在与192个及时覆盖一致。

## 遗漏过程

- RANKED_OUT：2024
- POSITIVE_20D_GATE：76
- POOL_FULL：59
- EXIT_OR_REENTRY_LIMIT：29
- NO_NEW_ENHANCEMENT_EVIDENCE：1

## 迟到过程在及时窗口的阻断点

- RANKED_OUT：183
- POSITIVE_20D_GATE：158
- EXIT_OR_REENTRY_LIMIT：16
- NO_NEW_ENHANCEMENT_EVIDENCE：15
- POOL_FULL：12
- NO_REVIEW_OPPORTUNITY：8
- NO_LOCAL_IMPROVEMENT：3

全体及时窗口中，20日转正门槛阻断1,461个、排名阻断865个；不能只看全部阶段中排名阻断2,024个，就以为早期窗口也主要是排名问题。

这些互斥原因是诊断分类，不是因果贡献：换排名、增加容量或放宽准入后池状态会变化，不能把人数直接当成可增加覆盖。完整分母、没有及时复核机会者均保留。

下一步已登记B02，仅检验相邻两段动量变化的排序信息：相同40日前史母体、准入、标签和逐周新增负担；另报等待一次复核的延迟/遗漏代价及低负担档位。不在本轮放宽20日正收益准入。

证据：[逐过程](../outputs/v2_b01/diagnosis/process_diagnosis.parquet)、[逐机会](../outputs/v2_b01/diagnosis/opportunity_gates.parquet)、[完整汇总](../outputs/v2_b01/diagnosis/summary.json)、[B02事前计划](../protocols/v2_b02/plan.md)。
