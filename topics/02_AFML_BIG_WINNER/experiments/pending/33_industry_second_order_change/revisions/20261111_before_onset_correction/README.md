# EP33：行业二阶变化与配置研究候选

[目标及用户修订](GOAL.md) · [阶段报告](reports/stage_report.md) · [历史候选卡](reports/candidate_cards.md)

本次执行R00–R05：先提出想法并记录实验设定，计算结果，再反思并调整。用户允许历史代理和部分缺失；没有新增采集、部署、实盘或Git发布。主结果为历史探索，独立验证仍待完成。数据截止2026-10-21，候选卡是2026-10-16历史快照，非实时推荐。

主要发现：持续改善并向同业扩散的状态有候选筛选线索，但加速度幅度本身未显示稳定排序优势；恶化减速的现有方法偏弱。财务代理组合在较广可用池有线索，加到联合价格状态后没有额外改善。缺失路径压力情景可改变结论，不能把探索区间当作已确认投资优势。

## 文件与复现

- `rounds/`：每轮执行前计划、结果反思和完成审计补充。
- `outputs/r01`–`r05`：完整选择、配对结果、覆盖、输入/代码哈希。
- `outputs/final/`：全行业覆盖库存、未来结果状态、年度切片、全池基线与缺失情景、候选卡及相关矩阵。
- `reports/validation.json`：运行结果、哈希与表格对账。
- `reports/completion_audit.json`：逐项交付证据与限制。

依赖本机既有EP30/EP32私有缓存；仓库不包含原始供应商大表。EP33临时派生面板在`/tmp/ep33_r01_panel.parquet`，丢失后由第一条价格实验命令重建。所有命令离线读取旧数据，只写EP33或临时目录；不要并行运行以下有依赖的步骤。

从仓库根执行：

```bash
EP=topics/02_AFML_BIG_WINNER/experiments/pending/33_industry_second_order_change
export OPENBLAS_NUM_THREADS=1
python "$EP/src/audit_existing.py"
python "$EP/src/price_experiment.py"
python "$EP/src/confirmation_experiment.py"
python "$EP/src/conditional_experiment.py"
python "$EP/src/financial_experiment.py"
python "$EP/src/financial_increment.py"
python "$EP/src/global_comparison.py"
python "$EP/src/build_report.py"
python -m pytest -q "$EP/tests"
python "$EP/src/validate_results.py"
```

环境版本见`outputs/final/environment.json`。复现是对既有探索的重放，不把原先已经查看的历史重新变成独立验证。每轮文件不用于覆盖EP32结论。
