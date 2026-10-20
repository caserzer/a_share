# EP25：条件收益分布的信息增量验证

研究日期2026-10-20。已完成有限候选研究；**不支持本轮信息集带来稳定完整分布优势，独立确认的证据不足**。原EP24不改写。先读[结论](final_conclusion.md)，再查[比较](baseline_comparison.md)、[数据审计](data_audit.md)、[消融](factor_ablation.md)、[校准](calibration_report.md)及[评分前方案](research_plan.md)。没有实盘建议或自动交易。

两基线、四个固定CatBoost MultiQuantile候选；四期限各22个季度，共352次候选拟合。共710,304条逐模型预测，653,190条到期且结果可得的评分记录。预测起点2021-01至2026-04；标签源截至2026-05-29。所有历史已被EP24查看，仅为探索性walk-forward。

## 环境与输入

从仓库根目录运行。复用topics/02_AFML_BIG_WINNER/.venv/bin/python；精确版本见requirements.txt及outputs/runtime_versions.json。无新增下载或认证信息。输入包括：

- EP24 outputs/local_cache/four_horizon_panel.parquet（冻结原资格规则和日历月收益）。
- EP24 outputs/r10_four_horizons/predictions_{1,3,6,12}m.parquet及outputs/local_cache/r10_distributions/中的原冻结B0/B1原子。
- 主题data/raw/akshare/day/qfq、data/qlib/cn_data_pit_largecap/calendars/day.txt与EP24财报缓存，供来源审计。

每项输入哈希见outputs/input_receipts.json；EP24被保护文件见ep24_preservation_before.json。公开API重下可能修订历史，因此只克隆Git不能精确复现；需要原本即未纳入Git的缓存与数据。不能把缺失输入用模拟数据替代真实实验。

## 复现

```bash
EP=topics/02_AFML_BIG_WINNER/experiments/pending/25_incremental_distribution_validation
PY=topics/02_AFML_BIG_WINNER/.venv/bin/python
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=2
export MPLCONFIGDIR=/tmp/ep25_matplotlib
$PY -m pytest -q "$EP/tests"
$PY "$EP/src/audit.py"
$PY "$EP/src/run.py"
$PY "$EP/src/controls.py"
$PY "$EP/src/evaluate.py"
$PY "$EP/src/report.py"
$PY "$EP/src/validate.py"
```

首次run.py在任何模型评分前写preregistration.json，记录评分前方案、配置、核心代码、当时测试和输入收据哈希；已有锁时拒绝这些文件发生改变。随后增加的报告、档案验证与前瞻工具不改变注册模型或评分规则，其交付哈希由supporting_code_manifest.json和delivery_manifest.json保留；不把它们追溯称为评分前写好。精确时间见preregistration.json。

run.py每个期限×季度完成后保存原子、模型、逐条指标与checkpoint。重跑核对锁与输出哈希并跳过已完成季度；不覆盖既有评分前方案，不自动搜索参数。想从头重算，应在独立复制目录中保留原记录并提供完全同哈希输入，不能删除EP24或历史结果。没有候选失败或未运行。

`validate.py`重算全部710,304条预测的CRPS、Brier、尾部概率、PIT和分位覆盖；额外从16个实际序列化模型重放四期限最后季度预测。`tests/`验证CRPS直接能量距离公式、混合CDF距离、缺失与并列、键配对、月份权重、严格成熟隔离、重叠收益统计单位和前瞻拒绝规则。正负控制输出见controls.json；pytest实际记录见outputs/pytest.txt。

## 保存范围

outputs中CSV/JSON、三张独立PNG与六份研究文档是可评审交付。outputs/local_cache约934MB，包括200原子的完整分布、各季度模型、逐条预测和合并预测，按主题既有规则忽略，不加入Git；checkpoint记录原子与预测精确哈希。delivery_manifest.json同时列出交付文件与本地缓存的位置、大小和哈希，避免把未上传误称为已上传。没有执行git commit或push。

分布文件`{h}_{quarter}_atoms.npz`包含B0/B1/M_R/M_V/M_F/M_VF，形状为本季度股票月数×200，float64，等权；相应`*_predictions.parquet`每个model内部按date/instrument排序，与该模型原子顺序一一对应。分位数及盈利/重大亏损概率可从原子重算；尾部是离散近似，不能解读为真实灾难上界。

## 冻结后的前瞻流程

本次未获取新行情或建立定时任务；不得把今天的旧数据冒称2026-10-20实盘预测。首次候选起点为2026-10-30（届时应以有来源的实际交易日历核验）。仅在当日收盘后16:00（上海时间）且取得合规字段与来源后运行：

```bash
$PY "$EP/src/prospective.py" forecast \
  --panel /absolute/path/asof_panel.parquet \
  --receipts /absolute/path/input_receipts.json \
  --date 2026-10-30 \
  --destination "$EP/outputs/local_cache/prospective/2026-10-30"
```

新面板沿用原字段、历史训练与资格规则，预测行四个y列必须缺失；旧训练标签只能用严格结束于季度开始前的记录。财报可用日须早于预测日。输入收据必须包含panel_sha256、asof、price_source、universe_source、valuation_source、financial_source、vintage_limitations、corporate_action_limitations。必须自行审计原始披露版本与完整收益口径；接口及本地哈希不能证明供应商声明真实。不能擅自改变原股票池以改善表现。

工具拒绝未来日期、事后补作、收盘前运行、已知未来标签与已有目标目录；保存全部六模型原子、四候选模型、训练键哈希、输入收据及manifest。远端可信时间戳/只增存储可加强证据，但本次未部署，单机文件时间戳不应当成不可伪造证明。

标签到期后另存Parquet（date/instrument/horizon/actual/label_end），来源凭据包含labels_sha256和同源起止价格、目标交易日、公司行动限制，不改预测：

```bash
$PY "$EP/src/prospective.py" attach-labels \
  --archive "$EP/outputs/local_cache/prospective/2026-10-30" \
  --labels /absolute/path/matured_labels.parquet \
  --receipts /absolute/path/label_receipts.json \
  --asof YYYY-MM-DD \
  --destination "$EP/outputs/local_cache/prospective_labels/2026-10-30-6m"
```

标签按期限一次归档，不能重复/修订同一键而不先审计。先作完整性核验，不按中途收益调模型。累计至少36个连续成熟6月起点之后，运行一次计划内确认：

```bash
$PY "$EP/src/confirm_prospective.py" \
  --forecasts "$EP/outputs/local_cache/prospective" \
  --labels "$EP/outputs/local_cache/prospective_labels" \
  --destination "$EP/outputs/local_cache/prospective_confirmation/first36"
```

确认入口拒绝不足36月、起点不连续、原档案哈希变化、重复或修订标签。只取首36月，不延长直到出现正结果；提供同样月度配对CRPS/Brier/尾部区间与缺失覆盖，结论仍须结合校准、分位覆盖、消融、阶段稳健性及历史可用性来源复审，不能凭CRPS一个显著区间宣称成功。未来12月样本可能尚未全部到期，单独列出可评价期限；不得把未到期当缺失已知标签。

停止规则已经触发：预注册候选与消融完成；无新的独立信息来源，不扩展模型。研究交付完成不等于独立增量预测命题已获确认。
