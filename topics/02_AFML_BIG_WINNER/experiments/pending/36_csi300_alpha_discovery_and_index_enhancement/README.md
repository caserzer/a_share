# EP36 · 沪深300 Alpha 与指数增强

当前交付：**历史排序评价完成；严格账户运行至精确数据阻断；正式净增强未认证。**

用户于 2026-11-16 回复 `execute`，授权执行 GOAL.md 定义的研究，随后授权 `commit and push` 发布研究成果。原目标文档保留不改，其“仅生成文档”说明已被后续授权覆盖。未进行实盘、监控或消息发送。

- 阅读入口：[中文总报告](reports/REPORT.md)
- 独立裁决：[A 排序与 Q5](reports/A_report_cn.md)、[B 受约束增强](reports/B_report_cn.md)
- 主表：[model_comparison.csv](outputs/model_comparison.csv)
- 年度/季度：[annual_performance.csv](outputs/annual_performance.csv)、[quarterly_performance.csv](outputs/quarterly_performance.csv)
- 交付检查：[final_validation.json](outputs/manifests/final_validation.json)
- Q5 周度／双周／月度敏感性：[完整报告](reports/q5_rebalance_20261116/REPORT.md)
- E1/E2/E3 完整逐月记录：[逐月报告](reports/q5_rebalance_20261116/monthly_records/MONTHLY.md)、[Excel](outputs/sensitivity/q5_rebalance_20261116/monthly_records/E1_E2_E3_monthly_returns.xlsx)
- 扣费后相对沪深300全收益诊断：[报告](outputs/diagnostics/net_excess_20261116/REPORT.md)

## 可复核范围

607 只历史成分，501 个完整周信号，2017 年起准备数据；外层 2021Q1—2026Q4（末季度不完整）。行情截止 2026-10-21。

7 个登记模型；expanding 与 rolling36 各 24 折；E2/E3 各固定 3 个 seed，固定等权组合；48 个 Ridge、288 个最终 LightGBM 模型（另有 288 次内层早停拟合）。没有外层参数搜索。

192 个严格账户分支 = 2 条路径 × 8 个模型/对照 × 3 种成本 × 4 个单因素时钟/窗口设定。全部运行并明确记录估值阻断。另有 32 个主成本停牌估值敏感性账户，不替代严格结果。

`historical_simulated_oos`；真实前瞻始终 `FORWARD_PENDING`。

## 文件与数据

- `configs/protocol.json`、`feature_dictionary.csv`：首次训练前冻结；78 核心 + 12 扩展特征。
- `configs/execution_v2.json`：看过初版执行诊断后登记的停复牌补数版本。
- `configs/valuation_sensitivity.json`：已知停牌估值和折价情景，明确后登记。
- `outputs/fold_predictions/`：长表封存预测；不含未来标签。
- `outputs/manifests/`：数据、模型、预测、消费者和账本的独立哈希。
- `outputs/data_audit/`：逐证券、逐周、单位、执行、权重与缺价清单。
- `outputs/archive/`：初版及修正前的结果，保留失败历史。
- `private/`：原始供应商数据、归一化行情、标签、模型和完整账本。已在本目录 `.gitignore` 排除，不能随公开代码提交。

旧 EP 数据只读，读取的 EP30 文件逐个对照其封存清单 SHA256。任何新的模型或经济参数变更都应登记新版本，不覆盖本轮预测。当前数据缺口不等于 alpha 假说被否定。

## 复核命令

以下命令在本目录执行，依赖版本见 `requirements.txt` / `outputs/manifests/environment.json`。LightGBM 和 OSQP 已隔离安装在 `private/vendor`，其他库来自当前研究环境。凭据仅由采集器读取既有 `.env`，不写入输出。

```bash
OPENBLAS_NUM_THREADS=4 python -m pytest tests -q
OPENBLAS_NUM_THREADS=4 python src/replay_models.py
OPENBLAS_NUM_THREADS=4 python src/audit_delivery.py
```

已封存数据下的重建顺序：

```bash
python src/build_panel.py
python src/execution_status.py
python src/audit_inputs.py
python src/train.py expanding
python src/train.py rolling36
python src/evaluate_ranking.py expanding
python src/evaluate_ranking.py rolling36
python src/backtest.py expanding weekly
python src/backtest.py expanding biweekly
python src/backtest.py expanding delay1
python src/backtest.py rolling36 weekly
python src/suspension_sensitivity.py 0
python src/suspension_sensitivity.py 0.2
python src/ranking_sensitivity.py
python src/summarize.py
python src/replay_models.py
python src/audit_delivery.py
python src/report.py
```

采集器 `acquire_sources.py`、`acquire_members.py`、`acquire_limits.py`、`acquire_suspensions.py` 使用现有权限及可恢复缓存。新的供应商响应不应静默替换已封存输入。首次输入审计后保存的代码清单不在重跑时覆盖。

## 需补齐才能升级的证据

1. 历史指数权重的真实发布时间、精确调样生效及其间权重；并处理新增成分和公司行动，不能用未来月末权重倒填。
2. 海通证券等吸收合并/换股、退市和终值权益流水；不能虚构清仓、永久沿用旧价或无依据归零。
3. 与股票前复权代理一致的完整基准口径；官方价格指数只能作为诊断，不冒充开盘全收益。
4. 独立冻结后的真实前瞻观察。当前未创建任何前瞻任务。
