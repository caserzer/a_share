# EP27：重大亏损风险分层归因

研究日2026-10-20。**在固定历史观察样本和注册模型中发现条件估值风险增量，但未证明全A股独立、可靠校准或新增经济价值。** 研究完成不要求正结果。

[最终结论](final_conclusion.md)逐一回答六个问题。[研究方案](research_plan.md)及config.json在任何EP27模型评分前哈希冻结；P0先审计再训练，P1比较完成后才进入P2，随后P3滚动校准、P4辅助组合。原EP24/25/26及双20%结论不改。

## 阅读入口

| 材料 | 用途 |
| --- | --- |
| [数据完整性](data_integrity_audit.md) | 两类总体、未来ST、退市缺价、财报/估值版本、行业发布与收益代理 |
| [市场分层](market_risk_decomposition.md) | 共同结构与真实预测增量分开 |
| [行业分层](industry_risk_decomposition.md) | 时点身份、同行业AUC及不可评价覆盖 |
| [个股条件风险](idiosyncratic_risk_report.md) | 误差会计与独立风险证据边界 |
| [估值财务消融](valuation_financial_ablation.md) | 主Delta、完整五组消融、期限及阶段 |
| [条件校准](conditional_calibration.md) | 严格成熟OOS全局/状态校准及失效 |
| [匹配风险组](matched_risk_group_test.md) | 预测时卡尺、数量、事件差及区间 |
| [组合尾部](portfolio_tail_risk_test.md) | 目标行业中性、风格/流动性、成本/机会成本 |
| [统计验证](statistical_validation.md) | 月份块、功效、正负控制、重建证据 |
| [前瞻协议](validation_protocol.md) | 真正新日期、冻结/追加、事件/功效门槛 |

主事件严格未来6日历月R<−20%，原月末收盘至目标日后首个交易日收盘，前复权代理，原标签源截至2026-05-29。预测2021-01至2026-04，6月可评分起点截至2025-11，共59月、27,230股票月、4581事件、25个成熟缺失。辅助1/3/12月分开，不能代替主检验。

B0历史原始事件率，B1原冻结近邻；六个直接分类候选R/RM/RMI/RMIV/RMIF/RMIVF。同架构、同人群、同训练方式，4期限×22季度×6=528拟合。6月主比较Full−RMI；6月M_R与EP26原预测、B1与原冻结分布核验一致。行业字段重建到完整固定人群，宽度/同伴状态用单列的未做终身ST排除报价覆盖快照，仍非完整无偏市场。

## 环境与输入

从仓库根目录运行，复用topics/02_AFML_BIG_WINNER/.venv/bin/python。精确依赖见requirements.txt、outputs/runtime_versions.json，无新增模型/参数搜索。

原始依赖包括：EP24 four_horizon_panel.parquet、公开财报/估值衍生字段；目标板块元数据、退市及名称变更、约4591只可用报价文件与原始未复权价格、市场日历和CSI300；19份行业PDF/解析表；普通分红送转、配股及未解释复权变化；EP25原分布/逐条预测及EP26原M_R/控制记录。源SHA256详见source_receipts.csv与inherited_baseline_receipts.csv，旧研究保护在prior_preservation.json。

这些数据原本未全部进Git，且公开API可能历史修订。**只克隆Git不能精确重建全部结果**；必须取得同哈希输入与模型缓存。缺资料应明确不能执行，不能以合成数据替代真实研究。旧行业parse_manifest包含本机绝对路径；换机器须提供原目录映射或同路径数据，先核对原哈希，不改旧清单/源字节让检查通过。

## 复现

```bash
EP=topics/02_AFML_BIG_WINNER/experiments/pending/27_hierarchical_tail_risk_attribution
PY=topics/02_AFML_BIG_WINNER/.venv/bin/python
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=2
export MPLCONFIGDIR=/tmp/ep27_matplotlib
$PY -m pytest -q "$EP/tests"
$PY "$EP/src/audit.py"
$PY "$EP/src/run.py"
$PY "$EP/src/controls.py"
$PY "$EP/src/evaluate.py"
$PY "$EP/src/calibrate.py"
$PY "$EP/src/portfolio.py"
$PY "$EP/src/diagnostics.py"
$PY "$EP/src/context_audit.py"
$PY "$EP/src/report.py"
$PY "$EP/src/validate.py"
$PY "$EP/src/archive.py"
```

run.py先完成所有P1预测及层比较，p1_gate通过后才拟合P2；审计可解释而非正效果是门槛。每季度/期限可按checkpoint哈希恢复，不能重写注册文件或已产生预测。evaluate.py生成P2条件组/匹配/误差会计与p2_gate；calibrate.py只在其后执行，再由p3_gate放行portfolio。发生源日期/标签错误需停止审计，不能放宽指标。

P0曾在评分前发现旧聚合状态继承未来ST选择，改为覆盖普查重建；p0_initial_audit.json保留初始诊断。主标签及固定池未修改。最终P0、数据版本和核心代码哈希在preregistration.json。报告、额外风险暴露/端点背景诊断、前瞻工具和完整重建器在注册后添加，supporting_code_manifest.json单列，不追溯称全在评分前完成。它们不拟合新候选或改变筛选。

原误差分解与Oracle是事后会计，不能当真实风险来源的因果百分比。AUC/AP按月平均；行业/风险格AUC有最低事件数，排除原因和覆盖全部保留。风险匹配的卡尺及20对目标不因结果改变。ordinary-action收益敏感性统一对所有模型同一子集重评分，不替换主标签。

校准全部来自过去成熟OOS概率，108次预热回退、276次有效拟合；没有优化失败。状态共同logit位移理论保存排序，双精度实现有两个模型各一个月的1e−17并列扰动，预警名单不变。未改原预测；不将该数值噪声解释为新增AUC能力。

## 文件与存储边界

outputs/*.csv/json/png及规定文档、代码、测试、环境说明为GitHub可评审交付。outputs/local_cache保存P0面板/覆盖快照/收益代理、528个模型、P1/P2逐条概率、合并预测、校准概率、控制与组合持仓权重，按主题原规则忽略，保留本地并逐项哈希。大缓存不上传，不把本地保留误称发布。

基础预测约947,072行（4期限×29,596股票月×8模型），horizon/model/date/instrument唯一；字段含概率、旧基准差、label_end、版本/置信度、行业发布/陈旧及财报可用日期等。逻辑目标日期可由date+horizon日历月得到，精确label_end由真实市场日历决定，未到期为NaT；P0 panel保留target_h原列。所有示例是历史研究，非今日预测。

outputs/prediction_target_calendar.csv另列每个期限/起点的逻辑目标日期与原日历可确认的交易日，可与逐股预测按horizon/date连接。SHA256承诺归档字节；CatBoost重新训练时模型GUID/时间等序列化元数据可能改变，不能把新文件哈希冒称原文件。推断重放使用原模型缓存核验概率及评分，不只比较模型文件名。

核验器重放全部528模型、重建全部主要月度指标/条件AUC、校准成熟历史/参数/预测，验证匹配不看未来、行业权重与风险格持股数、现金/NAV/费用，以及1304项旧文件哈希。实际回执为outputs/validation.json、pytest.txt及controls.json，不能用文件存在或脚本可运行替代实际通过。

## 前瞻封存

archive.py在outputs/prospective_protocol_lock.json封存forward.py、协议与对应测试，先于任何真实前瞻预测。最早2026-10-30收盘后上海16:00，有真实时点数据和来源才能运行：

```bash
$PY "$EP/src/forward.py" forecast \
  --panel /absolute/path/true_prepared_panel.parquet \
  --receipts /absolute/path/source_receipts.json \
  --calendar /absolute/path/actual_market_calendar.csv \
  --date 2026-10-30 \
  --destination "$EP/outputs/local_cache/prospective/2026-10-30" \
  --forecast-root "$EP/outputs/local_cache/prospective" \
  --label-root "$EP/outputs/local_cache/prospective_labels"
```

prepared panel包含原资格字段、全部注册字段、y_6/end_6/date/instrument/financial_available_date/industry_published/yield_observation_date；预测行y_6缺失，M字段同月共同。来源收据包含panel_sha256、calendar_sha256、asof、population_rule、market_state_sources、industry_release_sources、financial_vintage_limitations、valuation_vintage_limitations、ST_delisting_limitations、corporate_action_limitations。此入口不自动下载/认证数据；缺真实来源会阻止执行，不能用当前分类或最新财报历史回填。

保存模型、原始及校准概率、实际校准历史/系数、版本、训练键、源收据和manifest；拒绝未来或事后日期、非真实月末、收盘前、未来标签、旧目录或代码变化。未来日历未知时冻结日历月目标及首个实际交易日规则，不猜开市安排。

到期后标签单独追加，列date/instrument/actual/label_end/start_close/end_close；起止qfq价必须来自同源同版本响应，源回执含labels_sha256、same_source_same_vintage_price_response_sha256、corporate_action_limitations、missing_outcomes、calendar_path/calendar_sha256。

```bash
$PY "$EP/src/forward.py" attach-labels \
  --archive "$EP/outputs/local_cache/prospective/2026-10-30" \
  --labels /absolute/path/mature_labels.parquet \
  --receipts /absolute/path/label_receipts.json \
  --asof YYYY-MM-DD \
  --destination "$EP/outputs/local_cache/prospective_labels/2026-10-30"
```

原预测不变，目标交易日校验、重复/修订键拒绝、后来OOS历史可由collect_history加入未来滚动校准。确认门槛见validation_protocol.md和check_confirmation_gate：36/48/60固定门槛、300事件/24事件月/重要0.002幅度功效，取首个合格窗口，不按效应好坏延期。完整确认仍须依原协议执行分层/消融/匹配/校准/经济分析和来源审核；工具不会自动宣称成功。没有真实前瞻样本，没有部署自动任务。

本轮P0–P4完成后停止，不以获得更好AUC/Brier为由追加搜索。
