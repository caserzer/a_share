# EP29：全局学习、同行迁移与个股适配

**没有确认稳定、可迁移的联合适配优势。** 主GPI−G Brier差+0.000177，95%区间[−0.000369,+0.001000]；公司历史存在约0.04%的极小历史相对改善线索，但同行修正未带来总体优势，跨公司权重、阶段与校准结果不稳健。没有独立前瞻确认。

研究对象为未来6日历月收益严格低于−20%的概率。M_R 是主要全局基线，L2 是固定次要参照；G、GP、GI、GPI、L 五个模型分别检验全局、同行、个股、联合和局部历史。科学上负面或证据不足的结果同样构成完整交付。

历史数据截至2026-05-29。全部历史均为 EP24—EP28 已多次研究的探索样本，没有独立留出确认。不能把单股历史概率用作可靠实盘赔率。

## 阅读入口

| 文件 | 用途 |
| --- | --- |
| [GOAL.md](GOAL.md) | 原始用户目标完整存档 |
| [研究方案](research_plan.md)、[固定配置](configs/preregistration.yaml)、[目标队列](configs/target_cohort.yaml) | 评分前候选、选择规则、窗口、统计与停止规则 |
| [数据审计](reports/data_audit.md) | 股票池、收益、行业、OOS、版本及缺失限制 |
| [同行迁移](reports/peer_similarity.md) | 同行集合、回退与增量 |
| [收缩验证](reports/shrinkage_validation.md) | 正负控制、身份置乱、弱先验与严格无收缩区别 |
| [单股案例](reports/single_stock_case.md) | SZ000002 全路径及有效事件 |
| [跨公司验证](reports/cross_stock_validation.md) | 冻结40公司、全D0、条件异质性 |
| [校准报告](reports/calibration_report.md) | 可靠性、排序、尾部预警及概率解释 |
| [统计验证](reports/statistical_validation.md) | 配对区间、权重、阶段、功效和多重比较 |
| [结果全表](reports/result_tables.md) | 全模型、全部40家公司和所有事前分组 |
| [最终结论](reports/final_conclusion.md) | 直接回答Q1–Q10，区分历史支持、不支持和不足 |
| [设计澄清](reports/design_clarifications.md) | 两项正确性修复、无收缩诊断与后加展示的时序 |
| [前瞻协议](validation_protocol.md) | 真实月末、独立封存、共享标签、禁止倒填 |

## 证据链

原输入→`input_sources.csv`；原 EP24—EP28 文件→`prior_preservation.json`；模型定义→`preregistration.json`及正确性修复链；16个暖启动全局模型→`global_fit_audit.json`；每月预测/同行→各起点审计回执；真实适配→`real_M_R_fits.json`、`real_L2_fits.json`；评分→全部指标CSV；重放→`validation.json`；交付→`delivery_check.json`；公开文件及本地缓存→两个归档清单。

原注册保持原字节。两项修复保留修复前源码和错误/旧评分记录：pandas `sparse`属性冲突；控制评分排除完全未到期月份。没有改模型、标签、选股、种子或阈值。原 `L_unshrunk` 实际为弱 Jeffreys 平滑，因此另以独立评分前登记补足严格经验频率 `L_MLE`；正式五候选不变。历史校准上下文与实际同行配对排序是随后登记的描述性材料，不追溯称初始预注册。

## 环境与复现

Python 3.11.12；依赖见 [requirements.txt](requirements.txt)，实际环境见 `outputs/manifests/environment.json`。`.yaml`文件采用合法JSON子集，用标准JSON解析，无需另装YAML库。

**Git克隆不足以精确复现。** 需取得清单对应的 EP28 面板、季度概率、前期原始源、上市元数据、EP29 模型/逐条预测缓存。每项本地缓存有相对路径、字节数、SHA256；不得用最新供应商修订值替换后声称同一实验。归档模型可能带序列化元数据，重新训练文件哈希不必相同；数值回放用归档模型核对。

在仓库根目录、原缓存完整时：

```bash
EP=topics/02_AFML_BIG_WINNER/experiments/pending/29_global_stock_adaptation
PY=topics/02_AFML_BIG_WINNER/.venv/bin/python
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2
export MPLCONFIGDIR=/tmp/ep29_matplotlib
$PY -m pytest -q "$EP/tests"
$PY "$EP/src/global_model.py"           # 核验注册并复用已有季度，不增加候选
$PY "$EP/src/controls.py" synthetic     # 固定控制；已有预测检查点保持原字节
$PY "$EP/src/controls.py" identity
$PY "$EP/src/walk_forward.py"           # 固定顺序历史适配，已有起点只核验复用
$PY "$EP/src/evaluate.py"
$PY "$EP/src/strict_local_diagnostic.py"
$PY "$EP/src/diagnostics.py"            # 在evaluate之后，给单股CSV附加历史校准上下文
$PY "$EP/src/peer_ranking.py"
$PY "$EP/src/presentation.py"
$PY "$EP/src/report.py"
$PY "$EP/src/validate.py"               # 完整重放或核验已有重放回执
$PY "$EP/src/delivery_check.py"
$PY "$EP/src/archive.py"               # 核验既有锁，不覆盖前瞻规则
```

两个基础的独立适配重放可分别执行 `validate.py --foundation M_R` 与 `--foundation L2`；最终无参数验证同时核对回执所承诺的输入、预测、同行及代码字节，并重建评分和区间。

`audit.py`只允许初次注册前运行。需要从原来源重新构造时，在独立复现实验副本中保持原注册作为参照，不删除本目录封存件来绕过检查。初始顺序：来源/旧文件快照→数据审计与选股→核心测试→注册/全局OOS→控制→真实适配→评分/诊断→验证。该流程明确依赖历史缓存可得性，不保证仅靠当前网络即可重获同字节历史。

## 保存范围与前瞻

代码、配置、报告、指标、单股及40公司全路径、单股同行、审计及哈希清单进入GitHub；全D0逐条预测、全部同行、模型及大型面板留在忽略的 `outputs/local_cache`，清单逐项承诺。`actual`为空表示未到期或明确缺失，不是无事件。

正式解释概率时使用附带历史校准的`outputs/predictions/single_stock_*.csv`、`cohort40_*.csv`和本地`annotated_predictions_*.parquet`。`real_*_all.parquet`、`evaluation_*.parquet`等是模型/评分中间件，须按日期和代码关联`calibration_context_*.parquet`后阅读，不能把脱离校准/历史范围的原始概率当作可靠赔率。

前瞻工具见 `src/forward.py --help`。它复用同日EP28的M_R和L2原概率，核对全准备面板及源凭证；EP29形成独立不可覆写归档，后来只追加绑定的同源标签。只接受真实当日月末16:00后，最早2026-10-30；没有生成未来预测、补造中间月份或创建自动任务。历史缺失标签在本版工具中保持缺失。日期/哈希门禁已测试，真实供应商链及当日端到端运行尚未发生。

本轮完成后停止模型扩展。原历史不能升级为独立验证；需要真正新的冻结前瞻月份，EP27/28/29共享月份只算同一份市场证据。
