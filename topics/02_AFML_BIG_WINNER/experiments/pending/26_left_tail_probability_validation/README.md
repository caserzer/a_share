# EP26：未来6个月重大亏损概率

研究日期2026-10-20。**基础风险排序有历史证据，估值有局部排序线索；新增估值与陈旧财报的联合概率优势未获支持，独立前瞻确认仍证据不足。** 研究完成不要求正结果。

先读[最终结论](final_conclusion.md)，再读[基线比较](baseline_comparison.md)、[匹配消融](factor_ablation.md)、[概率校准](probability_calibration.md)、[风险排序](tail_risk_ranking.md)、[组合辅助](portfolio_risk_test.md)。[事件定义](tail_event_definition.md)、[数据审计](data_audit.md)、[评分前方案](research_plan.md)、[前瞻协议](validation_protocol.md)保留适用边界。没有交易建议、自动交易或定时任务。

## 模型和证据

主事件严格R_6m<−20%，与EP25一致；辅助−10/−30和原冻结Q05/Q10。B0是成熟历史原始事件率，B1是EP25冻结风险/市值近邻，D_R/V/F/VF是EP25原冻结分位树（D_R即EP25 M_R）。EP26直接分类模型M_R/V/F/VF和单个市场交互M_VFS，共5个预指定候选，三个事件、22季度、330次正式拟合。主对比M_VF−M_R。同样本、同训练方式，不把算法变化混成信息变化。

2021-01至2026-04预测，原标签源截至2026-05-29；29,596个股票月、11个模型的325,556条预测。可评价27,230个股票月、4,581个重大亏损、59个重叠起点；25条成熟缺失单列。历史全部已被EP24/EP25查看，只有探索性walk-forward，没有独立留出。

## 环境及原始输入

运行于主题既有.venv/bin/python，精确环境见requirements.txt与outputs/runtime_versions.json。原输入包括EP24四期限面板、1647只qfq价格及日历、历史行业面板；EP25的6月冻结原子/逐条预测与输入审计。全部输入路径及SHA256在outputs/source_receipts.csv。旧研究1191个可评审文件的保护承诺见prior_episodes_preservation.json。

真实原始数据本来就没有全部进Git；只克隆Git不能复原已修订供应商历史或完整旧缓存。需要原哈希数据才能精确重跑，缺数据时应明确不能执行，不能用合成数据冒充真实实验。合成数据仅用于正控制；真实月内标签置乱是负控制。

## 复现命令

从仓库根目录运行：

```bash
EP=topics/02_AFML_BIG_WINNER/experiments/pending/26_left_tail_probability_validation
PY=topics/02_AFML_BIG_WINNER/.venv/bin/python
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=2
export MPLCONFIGDIR=/tmp/ep26_matplotlib
$PY -m pytest -q "$EP/tests"
$PY "$EP/src/audit.py"
$PY "$EP/src/run.py"
$PY "$EP/src/controls.py"
$PY "$EP/src/evaluate.py"
$PY "$EP/src/portfolio.py"
$PY "$EP/src/portfolio_attribution.py"
$PY "$EP/src/economic_diagnostics.py"
$PY "$EP/src/report.py"
$PY "$EP/src/validate.py"
$PY "$EP/src/archive.py"
```

首次run.py在任何EP26模型评分前生成preregistration.json，冻结方案、事件定义、配置、当时全部核心执行/评分/组合/控制代码与测试、输入收据；重复运行检查冻结哈希与已有季度checkpoint，不自动重拟合或搜索。每个checkpoint包含训练键、严格成熟时点、预测哈希、辅助相干修正统计。B0/B1/D_*全部同样本评价，D_*的p20及Brier与EP25逐条/逐月精确一致。

报告绘图、行业/指数暴露补充诊断、前瞻工具与档案验证在历史注册之后增加，不改变候选、标签、主评分或筛选规则；提交时由supporting_code_manifest.json另行记录，不能追溯称评分前全已写好。行业/指数诊断不重新选股；原始portfolio.py及名单已冻结。

validate.py核对全部330个序列化分类器重放、全部月度Brier/AUC/AP/预警指标与原分位模型一致性、全输入/旧文件哈希、现金/NAV/成交成本和匹配层持股数。测试包括严格阈值、缺失、概率嵌套、Brier分解、ROC/AP常数基线、月内置乱事件率、月份权重、时间隔离、风险组不按未来结果筛样本、交易现金和无报价、前瞻日期/事件/功效门槛。实际回执为outputs/pytest.txt、validation.json与controls.json。

## 输出读取与发布边界

每季度outputs/local_cache/{quarter}_predictions.parquet与合并all_predictions.parquet保存每只股票的p_loss10/20/30、原始辅助概率、目标日/标签结束日、模型/数据版本、置信度标签、字段可用比例、财报/利率时点、B0/B1/D_R概率及对B1差异。直接分类器的Q05/Q10不可识别，明确为空；旧分布模型分位原样保留。src/core.py与tail_event_definition.md明确概率的严格边界及200原子来源。

逐月评分、区间、校准桶的行数/事件数/覆盖月数、年份/市场状态、财报年龄、风险十分位、组合净值/换手/成本/机会成本与暴露归因均保存为CSV。完整预测和模型在本地outputs/local_cache，按主题原有规则忽略，不推送GitHub；哈希和大小在delivery_manifest.json。不能将本地保留误称上传。报告、代码、配置、测试、汇总CSV/PNG和收据提交GitHub。EP25未提交的可评审材料作为原字节依赖独立提交；不修改旧README、报告或结果。

## 前瞻冻结与追加

先生成outputs/prospective_protocol_lock.json（archive.py完成），固定本期前瞻协议/工具/测试。目标最早2026-10-30，实际当日收盘后上海16:00，有真实时点来源才允许：

```bash
$PY "$EP/src/prospective.py" forecast \
  --panel /absolute/path/true_asof_panel.parquet \
  --receipts /absolute/path/input_receipts.json \
  --calendar /absolute/path/official_market_calendar.csv \
  --date 2026-10-30 \
  --destination "$EP/outputs/local_cache/prospective/2026-10-30"
```

面板沿用EP25基础字段及标签列，未来预测行y_6必须缺失，财报/利率日期严格过去；新鲜度和状态交互按冻结公式生成。日历为无表头单列市场交易日，须覆盖当前月后，以验证真正月末；下一年度日历尚未公布时冻结日历月目标及“之后首个交易日”规则，不伪造未来日程，精确截止日到期后据真实日历核验。

输入收据字段：panel_sha256、calendar_sha256、asof、price_source、universe_source、financial_vintage_evidence、valuation_vintage_evidence、corporate_action_limitations、calendar_source。工具能检查哈希/日期，不能认证供应商声明真伪；缺原始披露版本的限制继续存在。保存模型、概率、版本、训练键、来源与manifest；拒绝事后补档、未来日期、已有目录或代码变更。

标签单独归档，列date/instrument/label_end/actual；收据包括labels_sha256、price_source、origin_price_snapshot_sha256、endpoint_source_sha256、corporate_action_limitations、missing_outcomes，以及calendar_path/calendar_sha256（到期真实完整日历）。

```bash
$PY "$EP/src/prospective.py" attach-labels \
  --archive "$EP/outputs/local_cache/prospective/2026-10-30" \
  --labels /absolute/path/matured_labels.parquet \
  --receipts /absolute/path/label_receipts.json \
  --asof YYYY-MM-DD \
  --destination "$EP/outputs/local_cache/prospective_labels/2026-10-30"
$PY "$EP/src/prospective.py" confirmation \
  --forecasts "$EP/outputs/local_cache/prospective" \
  --labels "$EP/outputs/local_cache/prospective_labels" \
  --destination "$EP/outputs/local_cache/confirmation/first_eligible"
```

最早36个连续成熟起点、300事件、24个事件月，同时预设0.002幅度达到近似80%功效；仅在36/48/60固定门槛核验，取最早合格窗口，不看效应好坏决定延期。首次确认后写全局一次标记，拒绝反复测试；均不足则终止本确认计划并报告不足。自动入口只生成必要的主评分区间，完整校准、分层、消融、稳健性、时点与组合审计仍须按协议复核，不能自动贴“成功”。没有真实前瞻数据时不声称独立确认完成。

本轮预注册候选已完成，按停止规则结束，不继续增加模型追求正结果。
