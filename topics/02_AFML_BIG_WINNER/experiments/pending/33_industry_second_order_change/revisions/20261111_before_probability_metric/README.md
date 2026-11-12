# EP33：泛行业早期机会研究池

[目标及用户修订](GOAL.md) · [阶段报告](reports/stage_report.md) · [历史候选卡](reports/candidate_cards.md)

**当前状态：研究池目标未完成。** 用户确认成功为“未来一段时间行业上涨且跑赢市场”。目标是覆盖全部可准入细分行业，验证早期变化信号能否提高入池成功比例，同时报告机会覆盖、容量和早期性。R00–R05的收益探索、R06–R08的案例与泛行业过程检验均为中间证据，尚无通过验收的准入规则。已执行R09及反思驱动的R10、R11，见[联合胜率研究报告](reports/pool_research_r09_r11.md)和[347行业状态清单](outputs/pool_latest_disposition.csv)。尚无可批准的高胜率规则，详细失败与探索线索均保留。

此前执行R00–R05：先提出想法并记录实验设定，计算结果，再反思并调整。用户允许历史代理和部分缺失；没有新增采集、部署、实盘或Git发布。主结果为历史探索，独立验证仍待完成。数据截止2026-10-21，候选卡是2026-10-16历史快照，非实时推荐。

主要发现：持续改善并向同业扩散的状态有候选筛选线索，但加速度幅度本身未显示稳定排序优势；恶化减速的现有方法偏弱。财务代理组合在较广可用池有线索，加到联合价格状态后没有额外改善。缺失路径压力情景可改变结论，不能把探索区间当作已确认投资优势。

## 已完成探索：R06–R08（变化过程）

[过程研究报告](reports/onset_process_report.md) · [全部18个过程档案与图](reports/onset_casebook.md) · [验证结果](outputs/onset_validation.json)

已完成3230个行业×入口登记、18片段/464条逐周记录、全行业时机与共同终点比较。每轮先写观察，再据反例调整；不是收益优化。当前未找到稳定统一的二阶起点指标，原目标保持开放。

主要发现：新低减少更像早期确认而非预测低点；等待广泛确认仅小幅减少未持续提示，却丢失约31%的最终持续变化并延迟约2周。完整口径、未知分母、年度差异及参考定义敏感性见报告，不能把这些比例当投资胜率。

原始checkpoint与人工分段反思保留。部分半年第27周在完整性审计时补齐，旧记录未回写；有单独修复说明。重复执行checkpoint命令只验证已有前缀，不覆盖收据。

主线离线复核（依赖既有缓存、旧R03名单和R04财务覆盖表；下面是复现已完成研究，不是新的盲测）：

```bash
EP=topics/02_AFML_BIG_WINNER/experiments/pending/33_industry_second_order_change
export OPENBLAS_NUM_THREADS=1
export MPLCONFIGDIR=/tmp/ep33_mpl
# 仅首次无cases.csv时执行 --sample；已有抽样不可更换。
python "$EP/src/onset_replay.py" --advance 4
python "$EP/src/onset_replay.py" --advance 8
python "$EP/src/onset_replay.py" --advance 12
python "$EP/src/onset_replay.py" --advance 18
python "$EP/src/onset_replay.py" --advance 26
python "$EP/src/onset_replay.py" --advance 27
python "$EP/src/onset_panel.py"
python "$EP/src/onset_timing.py"
python "$EP/src/plot_onset_cases.py"
python "$EP/src/report_onset_process.py"
python "$EP/src/validate_onset.py"
```

收益附表单独由`src/onset_secondary_outcomes.py`产生，依赖旧的`/tmp/ep33_r01_panel.parquet`；丢失时可仅调用旧`price_experiment.build_panel()`重建该临时面板，不需覆盖旧收益实验输出。主线验证含这份附表的来源哈希。代码保守性维护前的源版本保存在`outputs/r06/source_versions/`，用于核对旧执行收据。

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

本次目标修订前的GOAL、README及onset_manifest已保存于`revisions/20261111_before_pool_objective_correction/`；旧清单是当时执行快照，不是当前目标文件的校验清单。当前修订记录见`outputs/pool_objective_revision.json`。

## R09–R11：研究池联合成功率

R09评价旧价格规则，R10分解市场环境与一阶状态，R11改用现有营收二阶信息。计划先登记、结果后反思，完整保留所有期限和分支。原目标开放；末期清单是2026-10-16历史观察，不是实时投资建议。

```bash
EP=topics/02_AFML_BIG_WINNER/experiments/pending/33_industry_second_order_change
OPENBLAS_NUM_THREADS=1 python "$EP/src/pool_evaluation.py"
OPENBLAS_NUM_THREADS=1 python "$EP/src/conditional_pool.py"
OPENBLAS_NUM_THREADS=1 python "$EP/src/financial_pool.py"
OPENBLAS_NUM_THREADS=1 python "$EP/src/validate_pool_rounds.py"
OPENBLAS_NUM_THREADS=1 python "$EP/src/report_pool_rounds.py"
python -m pytest "$EP/tests" -q
```

以上依赖既有两个临时派生面板及R04/R07输入；重建方法见前述复现命令。`outputs/r09`–`r11`含完整结果、来源收据、逐期候选对照和派生面板；它们是历史研究产物。当前交付哈希见`outputs/pool_execution_manifest.json`；目标修订前快照见`revisions/20261111_before_r09_r11_status/`。
