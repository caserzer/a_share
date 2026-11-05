# EP31：八项 A 股量价假说 · EP30 数据 · OOS / Walk-forward

研究合同以 [GOAL.md](GOAL.md) 为准，原文保持冻结。P0—P4 的可执行研究已交付；七项主张均为 `INCONCLUSIVE`，H09 为 `BLOCKED_DATA`，真实前瞻仍 `FORWARD_PENDING`。结果与验收分别见 [最终结论](reports/final_conclusion.md)、[逐项证据](reports/requirement_matrix.md) 和 `outputs/audits/delivery_check.json`。

## 研究范围

H01、H02、H03、H07、H09、H10、H11、H12；EP30 D2-v5 是前复权推断价格与标签主输入，原始 OHLCV/成交额/历史换手与身份事实按已封存 D2 输入与字段质量准入。历史评估严格标记 `Historical-proxy`，真实权益结算和可交易性尚未认证。

## 执行与复核

1. 先完成 GOAL P0：冻结数据 release/hash、注册假说/端点、控制组、季度 outer splits 和 inner purged CV，检查各字段能否按时点读取；**不能先看 OOS 结果再修改规则**。
2. H09 如无逐笔/委托数据，保持 `BLOCKED_DATA`；其余七条独立推进。
3. 构建训练时可见特征、按事件从 EP30 价格路径派生已成熟标签，必须核对 t0 收盘 / t+1 首个假设可成交开盘及未来公司行动的泄漏。
4. 逐季度 nested expanding/rolling walk-forward；输出完整 OOS 预测、折内参数、主端点、时间块区间、FDR 与同面板基线增量，供独立核查。
5. 报告 Big Winner 成功召回、失败过滤和机会成本的取舍；生成真正新时间的 forward shadow 封存记录并等待标签到期。

**注意：** 仅克隆 Git 并不包含 EP30 私有大表。运行前需要校验 EP30 `outputs/pit_v5/release.json` 指向的本机受控 release；不得用公开汇总 CSV 冒充完整明细。

从仓库根目录运行，Python 为 `topics/02_AFML_BIG_WINNER/.venv/bin/python`。源码目录为本实验 `src/`。计算使用 numpy / pandas / PyYAML / pyarrow / pytest / matplotlib；版本见 `requirements.txt` 和 `outputs/audits/environment.json`。

执行顺序：`build_data.py` → `audit_data.py` / `event_audit.py` → `walk_forward.py --hypothesis H01`（依次七项可用 H）→ `big_winner.py` / `turnover_sensitivity.py` / `h12_independence.py` / `auxiliary_baselines.py` → **`admit_folds.py`** → `constant_baseline.py` → `evaluate.py` → 各辅助模块 `--evaluate` → `report.py` → `audit_delivery.py`。独立准入使用完整 24 个日历月，拒收拟合预筛中不足整月的折，且发生在任何评分之前。原目录的已冻结预测拒绝覆盖。

R01 在任何外层评分之前将六个月内验证对齐到实际端点的成熟区间，见 `configs/revision_01_inner_maturity.yaml`、`outputs/manifests/revision_01.json`。原 P0 配置及未评分 attempt01 均保留；不修改主端点、方向、测试起点或成功标准。

独立重放使用单独目录，避免触及原始输出。例如：

```bash
PY=topics/02_AFML_BIG_WINNER/.venv/bin/python
EP=topics/02_AFML_BIG_WINNER/experiments/pending/31_price_volume_hypotheses_oos_walk_forward
OPENBLAS_NUM_THREADS=1 "$PY" "$EP/src/replay.py" --destination /tmp/ep31_replay --phase data
"$PY" "$EP/src/replay.py" --destination /tmp/ep31_replay --phase verify-data
OPENBLAS_NUM_THREADS=1 "$PY" "$EP/src/replay.py" --destination /tmp/ep31_replay --phase fit --hypothesis H01
```

其余六项 fit 后，按 `winner`、`sensitivity`、`h12-independence`、`auxiliary`、`admit`、`constant`、`score` 阶段继续。重放只读取原封存 EP30，独立写入输出与私有缓存；不使用外层结果择模。全量预测和模型索引在 `outputs/fold_predictions/index.csv`，大型 payload 留私有缓存，不提交供应商明细。

运行测试：

```bash
OPENBLAS_NUM_THREADS=1 topics/02_AFML_BIG_WINNER/.venv/bin/python -m pytest -q topics/02_AFML_BIG_WINNER/experiments/pending/31_price_volume_hypotheses_oos_walk_forward/tests
```
