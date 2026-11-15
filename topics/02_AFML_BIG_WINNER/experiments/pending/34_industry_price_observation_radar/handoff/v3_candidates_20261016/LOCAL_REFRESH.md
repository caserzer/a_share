# 本地更新流程补充核验

2026-11-12。此补充更新MONITORING.md中“未来日期增量生成及续接尚需核验”的技术状态：已实现并验证**同一起点完整重放**路径，不使用未经核验的序列化状态续接。未部署、未采集数据、未证明新行情有效。

## 实际验证

从原始本地价格重新生成10项特征，按年加载已登记且标签成熟时间早于年初的模型，重新排名并重放两个独立候选；107141行完整信号、事件、目录和决策复现M06。

截断到2021-11-26、2022-01-14、2025-12-31、2026-09-30后独立重算，与最终版本相应前缀一致。覆盖分类切换、无合格候选、跨年和近期追加。数值容忍1e-14，行业选择、事件身份及状态不变。

首版在某年度无合格候选时调用模型报空输入错，保留src/v3_local_refresh.py及原成功产物；当前使用v2，空候选不调用预测，保留目录和缺失分数。112项测试通过，年度模型缺失不允许静默复用。请求2026-11-12超过现有价格末日时被拒绝，未创建假新版本。

完整E02B评价和四期限后续路径也已重新执行：两个候选的匹配、覆盖、质量和13196条event-horizon路径与M06对应记录一致。收益仍只是后续追踪。

## 可执行命令

在仓库根目录运行，输出必须是尚不存在的新目录：

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/src/v3_local_refresh_v2.py --as-of YYYY-MM-DD --out <新观察目录>
```

可显式指定`--raw`、`--catalog`、`--calendar`、`--models`使用已准备好的本地新版本。不会联网或训练。要求保留原始目录及价格历史，从2020评价起点完整重放，不能只传新一期并假装旧池为空。输入修订可能改变过去信号，须单独记录迁移，不能覆盖原版。

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/src/v3_candidate_revaluate.py --observation-dir <观察目录> --tag <新评价标识> --parent-dir <对应父标签目录> --child-dir <对应增强标签目录>
python topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/src/v3_candidate_report.py --evaluation-dir <新评价目录> --observation-dir <观察目录> --out <新比较目录>
python topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/src/v3_candidate_evaluation_snapshot.py --evaluation-dir <新评价目录> --comparison-dir <新比较目录> --out <新评价快照目录>
```

后验标签生成必须沿用冻结L04D/H04D版本和数据血缘检查。不能用旧标签冒充新数据末日评价；本次实际核验只针对已有2026-10-21价格版本。新年度模型训练也需沿用成熟规则另行登记，不由更新脚本自动猜测或沿用旧年模型。

证据：outputs/v3_refresh/refresh_audit.json、evaluation_parity.json及各版本receipt.json。该本地工作流不等于生产部署或独立样本外验证。
