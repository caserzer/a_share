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

## 当前量化指标与下一轮

核心分数是未来126交易日“上涨且跑赢市场”的校准预测概率×100；入池与验收门槛见[指标协议](configs/pool_metric_v1.json)。[R12方案](rounds/r12_probability_score_plan.md)已执行，并依据反思完成R13；历史验收均未达标，见[量化模型报告](reports/probability_pool_r12_r13.md)。逻辑回归、树或其他模型均用同一标签和验收标准。此前执行清单按`revisions/20261111_before_probability_metric/`的文档快照解释。

## R12–R13：统一指标、模型评分与验收

[报告](reports/probability_pool_r12_r13.md) · [模型准入闸门](outputs/probability_release_gate.json) · [347行业×16版本历史分数](outputs/probability_latest_industry_scores.csv)。17项测试通过；R12共227124条封存预测，R13共378540条固定映射预测。模型分数尚未通过校准与胜率验收，不能当已认证成功概率。

首次执行入口依次为`src/probability_pool.py predict`、`src/probability_pool.py evaluate`；R13为`src/calibration_ablation.py predict`、`src/calibration_ablation.py evaluate`。已封存predict拒绝覆盖。正式评价使用`src/reevaluate_probability.py`保证主标签严格采用事前26周时间块；保留原预测源文件及旧25周评价以审计。

复核入口：`src/validate_probability_pool.py`、`src/probability_diagnostics.py`、`src/report_probability_pool.py`。建议设置OPENBLAS_NUM_THREADS=1与OMP_NUM_THREADS=1；依赖sklearn 1.4.2及既有R11面板。不要把重跑旧历史称作新独立验证。当前交付清单为`outputs/probability_execution_manifest.json`。

## R14–R15：条件校准与唯一机会准入

[本轮报告](reports/calibration_episodes_r14_r15.md) · [验收闸门](outputs/r14_r15_release_gate.json) · [347行业×12组合历史状态](outputs/r14_r15_industry_scores.csv)。原pool_metric_v1哈希未变，全部组合未通过，原目标保持开放。

R14先执行`src/market_calibration_pool.py predict`封存，再`evaluate`评价；`src/opportunity_episode_audit.py`生成簇首/重复/4周再激活比较。R15为`src/single_reconfirmation_pool.py predict`及`evaluate`，正式入池按唯一机会而非之后每次状态边沿计数。已有封存预测拒绝覆盖。

复核入口：`src/validate_market_calibration.py`、`src/audit_reconfirmation.py`；报告入口`src/report_calibration_episodes.py`。固定26周主标签时间块，建议OPENBLAS_NUM_THREADS=1、OMP_NUM_THREADS=1。23项测试通过。当前交付哈希见`outputs/calibration_episodes_manifest.json`；旧文档及清单快照见`revisions/20261111_before_r14_r15_status/`。

## R16–R18：唯一事件校准与观察宇宙

[完整报告](reports/event_calibration_r16_r18.md) · [验收闸门](outputs/event_probability_release_gate.json) · [347行业×10版本历史评分](outputs/event_probability_industry_scores.csv)。原量化标准保持不变，全部版本未通过。

顺序入口：`src/event_probability_pool.py predict/evaluate`（R16）、`src/event_context_pool.py predict/evaluate`（R17）、`src/broad_event_pool.py predict/evaluate`（R18）；已有封存预测拒绝覆盖。每轮计划、结果反思和输入哈希单独留存。R18只放宽观察候选，正式概率准入门槛未改。

复核：`src/audit_event_probability.py --round r16`（同样支持r17/r18）；报告：`src/report_event_calibration.py`。设置OPENBLAS_NUM_THREADS=1、OMP_NUM_THREADS=1。28项测试通过，旧预测和结果保留；当前交付清单为`outputs/event_calibration_execution_manifest.json`。历史评分不是实时或已认证概率，校准未知季度仍在机会覆盖分母中。
