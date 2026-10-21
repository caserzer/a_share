# EP30：D2 PIT基础与缺口审计

## D2-v5：前复权价格变化推断（用户指定的新主口径）

当前收益推断入口为 `D2PriceInferenceDataset`，结果及覆盖见[本轮报告](reports/pit_v5.md)、[标签摘要](outputs/pit_v5/label_summary.json)和[逐期限状态](outputs/pit_v5/label_status_totals.csv)。[价格口径审计](outputs/pit_v5/source_price_basis_evidence.json)确认原 D2 主行情为未复权；新版本从原始 OHLC 与独立保存的新浪前复权因子生成前复权 OHLC，保留未复权比较值。大表仍只在本机私有缓存，封存入口为[release.json](outputs/pit_v5/release.json)。

用户指定所有收益标签按价格变化推断，并选择前复权。v5 的 `price`、`total`、`executable` 三个请求名统一返回 `effective_policy=qfq_price_change_inferred_for_all_requested_policies`，数值相同，状态为 `KNOWN_INFERRED`、`UNKNOWN` 或 `CENSORED`，质量为 `Historical-proxy`。开盘执行及现金权益流水不再阻断这一推断口径；三套冻结严格口径的历史结果仍保留。缺失因子、冲突端点、退市后未知终值及未成熟标签不会补零。其余历史资格、财报版本和行业等域仍按原质量门槛独立判断。

```python
from v5_dataset import D2PriceInferenceDataset

data = D2PriceInferenceDataset()  # 默认读取当前 v5 封存入口，验证文件哈希。
label = data.build_labels("SH600000", "2017-01-26", "6_calendar_months", "total")
assert label["status"] == "KNOWN_INFERRED"
assert label["adjustment_basis"] == "qfq"
assert label["execution_assumed"] is True
# 同一个标签在尚未成熟的时点不返回未来收益。
assert data.build_labels("SH600000", "2017-01-26", "6_calendar_months",
                         asof_time="2017-02-01 15:00")["value"] is None
```

离线重建顺序为 `v5_prices.py`、`v5_labels.py`、`v5_qualify.py`、`v5_validate.py`、`v5_report.py`；首次联网补取仅由 `v5_factors.py` 进行，源和频率单列于 `configs/source_registry_v5.yaml`。`v5_seal.py` 独立复制源及输入并封存；`v5_offline_replay.py` 用封存代码在禁止网络、禁止读取活动工作区和缓存的环境重新生成价格、标签和桥表，结果见 `outputs/pit_v5/frozen_code_replay.json`。单独克隆 Git 不含私有数据。

## D2-v4：连续代码变更纠错与退市后财报桥接（2026-10-21）

当前追加版见[本轮报告](reports/pit_v4.md)、[覆盖摘要](outputs/pit_v4/delivery_summary.json)、[剩余选定年报期](outputs/pit_v4/selected_financial_remaining_gaps.csv)及[质量门槛](outputs/pit_v4/domain_quality_gates.csv)。封存和校验入口为 [release.json](outputs/pit_v4/release.json)。三份实施原件确认 `000022→001872`、`000043→001914`、`300114→302132` 是连续代码变更，修正三个误报退市并消除重复身份：5922→5919个暂定身份，525917→525762个候选证券月。486561条旧桥接记录与原列保留，另标旧别名及规范身份，不改旧收益或模型。

退市代码原件对应67→85家；新增两条摘牌事实，财报披露索引新增1183条，关联完整年报PDF208份，原先两版共同缺报期66→43；新增15条原页核验报告值。重建6309144条严格标签，已知仍为0。逐日资格、开盘执行、完整权益流水、实际支付和终值及全域财务修订仍阻断研究准入；代理行情和报告索引不升级为认证事实。

```python
import json
from v4_core import PUBLIC
from v4_dataset import D2V4Dataset

v4 = D2V4Dataset(json.loads((PUBLIC / "release.json").read_text())["path"])
# 在原代码下解析同一规范身份，按历史生效区间返回交易代码。
assert v4.get_asof("SZ300114", "trading_code", "2025-02-17 15:00").value == "SZ302132"
assert v4.get_asof("SH600290", "listed", "2024-01-23 09:30").value is False
field = "financial:reviewed_reported_operating_cash_flow:2018-12-31"
assert v4.get_asof("SZ002680", field, "2019-12-31 15:00").value is None
assert v4.get_asof("SZ002680", field, "2020-11-24 09:30").value == -203122781.04
assert v4.get_asof("SZ002680", field, "2020-11-24 09:30", mode="archived").value is None
assert v4.build_labels("SZ302132", "2020-01-23", 20, "total")["value"] is None
```

v4读取器以封存文件为输入；可显式传入 `baseline_release=不可变v3路径` 读取未变更的数据域。旧三版、原始研究和质量门槛保留。v4独立冻结版带有其变更管道所需的v3规范化输入，原始大文件仍仅在私有缓存。

## D2-v3：历史资格、退市权益与财报版本链（2026-10-21）

前一追加版见[本轮结果与剩余门槛](reports/pit_v3.md)、[覆盖摘要](outputs/pit_v3/delivery_summary.json)及[离线核验](outputs/pit_v3/validation.json)。封存位置和全文件校验入口为 [release.json](outputs/pit_v3/release.json)。本轮保留5922个临时身份，补正7只退市漏标、恢复2095条原文状态事件、67个退市代码对应；补回304894个历史字段。年报原文3120份，报告链25999条；229份扫描件OCR候选独立留存。全部仍按字段与域区分质量。

全量候选月度面板5823个身份、525917个证券月份，四期限三口径共6311004条严格标签。**严格已知仍为0；缺失执行、完整权益、到账或终值时不生成数值。** 当前归档不足以认证全市场每日资格和全部财报修订，独立人工验收为false；旧研究、v1/v2和D1到期未知结论未改写。

```python
import json
from v3_core import PUBLIC3
from v3_dataset import D2V3Dataset

release = json.loads((PUBLIC3 / "release.json").read_text())
v3 = D2V3Dataset(release["path"])
# 正式原文能证明本上市身份已经离场；整体历史成员仍未认证。
assert v3.get_asof("SH600193", "listed", "2026-07-06 15:00").value is False
# 只查询已复核版本，不冒充全量财务修订已经闭合。
f = "financial:reviewed_reported_operating_cash_flow:2020-12-31"
assert v3.get_asof("BJ920132", f, "2023-04-04 15:00").value == 4456443.98
assert v3.get_asof("BJ920132", f, "2023-04-06 09:30").value == -4549865.76
assert v3.get_asof("BJ920132", f, "2023-04-06 09:30", mode="archived").value is None
assert v3.build_labels("SH600000", "2020-01-23 15:00", 20, "total")["value"] is None
```

日期级停牌事件不推定全天状态；未知日内生效时间保守置于日末，明确时点保留。OCR候选不自动进入已核验权益表；计划支付日不等于实际到账。原始PDF、OCR模型和Parquet位于本机私有缓存，Git中保留代码、摘要、收据和文档。运行顺序见本轮报告；读取封存数据不请求网络。

前一追加版本为 **D2 v2 补数版（2026-10-21）**，见[补数结果、残余缺口与质量边界](reports/backfill_v2.md)。已将缺失历史与近期日线、历史股本、公司行动、原始年报及北交所身份事件接入独立 Parquet 数据集。批量回溯值仍为 Historical-proxy；原 v1 报告、快照及 EP01—EP29 保留。

以下 Python 片段需将本实验的 `src/` 加入 `PYTHONPATH`。

```python
from backfill_dataset import D2BackfillDataset

v2 = D2BackfillDataset()
quote = v2.get_asof("SH600000", "close", "2026-10-21 15:00", "Historical-proxy")
shares = v2.get_asof("SH600000", "total_shares", "2026-05-29 15:00", "Historical-proxy")
# 稳定 ID 解析旧代码；试点股票 2025-05-06 起已切换，非统一到 10 月。
code = v2.get_asof("BJ830799", "code", "2025-05-06", "Historical-proxy")
original = v2.get_asof("BJ920001", "financial:original_revenue:2025-12-31", "2026-03-30 09:30")
# 即使行情已补齐，实际买入/支付/权益证据缺失时仍返回 UNKNOWN。
label = v2.build_labels("SH600000", "2026-05-29 15:00", 20, "total")
```

原始字节与工作目录为 `~/.cache/a_share/ep30_d2/backfill_v2/` 及其父级 `raw/sha256/`。公开结果为 `outputs/backfill_v2/`；`release.json` 指向本轮独立冻结版。冻结版读取：`D2BackfillDataset(root=release_path / "normalized", manifest=release_path / "provenance/normalized_manifest.json", baseline=False)`，其中已保留 v1 原始/更正财务样例。默认工作接口另可读取 v1 的身份事实；严格历史总体仍受阻。

有本机原始档案时，离线复建顺序为 `backfill_financials.py`、`backfill_codes.py`、`backfill_exits.py`、`backfill_review.py`、`backfill_build.py`、`backfill_bridge.py`、`backfill_validate.py`、`backfill_report.py`、`backfill_freeze.py`。网络采集器为 `backfill_market.py`、`backfill_sina.py`、`backfill_tables.py`、`backfill_documents.py`、`backfill_listings.py`、`backfill_bse.py`；仅使用公开匿名源，逐源限频，不会购买权限。证券底表及旧缓存需要既有 v1 输入与已归档的官方来源；仅克隆 Git 不包含大型原始字节，不能凭空恢复它们。每次封存产生新快照，不覆盖已有 release。

```bash
python -m pytest -q topics/02_AFML_BIG_WINNER/experiments/pending/30_pit_data_foundation_v1/tests
python topics/02_AFML_BIG_WINNER/experiments/pending/30_pit_data_foundation_v1/src/backfill_freeze.py --verify-release /absolute/path/from/outputs/backfill_v2/release.json
```

## v1 冻结交付记录

本轮交付可运行的D2数据基础、来源/质量矩阵、真实财报版本回放、旧新桥接和受阻证据。**完整历史全市场PIT、总收益及可执行标签仍BLOCKED**。先读[最终裁决](reports/final_conclusion.md)、[质量门禁](reports/quality_gate_report.md)及[数据字典](data_dictionary.md)。GOAL.md和P0冻结配置保持不变。

现有旧行情截止2026-05-29；运行日2026-10-21的新名单与部分估值/财务观察不能补齐其间OHLCV和状态。5,540条临时身份不是认证全市场。一个财务附注的原始/修订版本可重建，不外推到全部财报。

从仓库根运行（无需模型框架迁移）：

```bash
python -m pytest -q topics/02_AFML_BIG_WINNER/experiments/pending/30_pit_data_foundation_v1/tests
python topics/02_AFML_BIG_WINNER/experiments/pending/30_pit_data_foundation_v1/src/run_all.py --freeze
```

安装依赖见 `requirements.txt`；准确运行环境见 `outputs/manifests/environment.json`。测试用合成夹具不需网络/私有数据。全量审计依赖本机已有EP01/24/28缓存及本轮原始响应，单独克隆Git不能重建缺失源字节。`--live` 才会追加有限公共来源探测；不自动买数据或读凭据。默认重建完全离线、不会重跑旧模型。重复运行产生新的真实采集/审计时间，不伪造首次观测；每次发布按内容哈希形成独立快照。

旧口径兼容桥表保留452,846行；扩展D2临时身份桥表另有486,561个股票月，新增33,715个全部缺收益。逐证券/逐月摘要分别为 `bridge_expanded_by_security.csv` / `bridge_expanded_by_month.csv`，完整表留外部缓存。

外部工作缓存默认 `~/.cache/a_share/ep30_d2/`，可在整条流水线开始前设置 `EP30_CACHE`。工作分区允许重算；`releases/{release_id}`是独立复制、只读数据文件的冻结版，禁止用硬链接共享可改字节。原始网络字节保存在外部 `raw/sha256/`；受限旧缓存原位保留，清单注明不得公开。仓库内只有公开审计摘要与哈希。

读取和标签接口（在src路径可导入时）：

```python
from dataset import D2Dataset

d2 = D2Dataset()
# 默认严格级别；空结果表示认证受阻，不是现实中没有股票。
universe = d2.universe_asof("2021-01-29 15:00")
# 代理必须明确请求，返回实际观察日期、质量及来源。
quote = d2.get_asof("SH600000", "close", "2021-01-29 15:00", "Historical-proxy")
# 一个真实原版/更正财务字段；历史可重建，历史系统归档仍不存在。
original = d2.get_asof("SZ000584", "financial:other_receivables_intercompany_balance:2023-12-31", "2024-07-31 15:00")
corrected = d2.get_asof("SZ000584", "financial:other_receivables_intercompany_balance:2023-12-31", "2024-08-01 15:00")
path = d2.price_and_corporate_action_path("SH600000", "2021-01-29", "2021-08-02", "total")
label = d2.build_labels("SH600000", "2021-01-29 15:00", "6_calendar_months", "total")
# 真实执行证据未认证，label保持UNKNOWN。支持20/60/120交易日及price/total/executable。
manifest = d2.snapshot_manifest("2024-08-01 15:00")
```

`FactStore` 支持更正追加、跨源冲突阻断、两类as-of、Parquet往返与 `qlib_frame`（Qlib MultiIndex datetime/instrument，另附逐格来源）。`LabelBuilder` 可接受经独立核验的执行标志与完整行动覆盖证明，计算简单现金/股份流；当前真实数据未取得这些证明，不填假值。

只读冻结版验收：

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/30_pit_data_foundation_v1/src/verify_release.py --release /absolute/path/from/outputs/manifests/release.json
```

该路径见 `outputs/manifests/release.json`，脚本核验全部冻结Parquet、代码/公开报告/配置、真实财报重放；全原始输入核验另由 `validate_delivery.py` 完成。读取冻结版可用 `D2Dataset(root=release_path, manifests=release_path / "provenance/outputs/manifests")`，随版保存旧已核验日历及原始网络字节。后续工作只追加新版本，不覆盖EP01—EP29原始结论，也不把本轮接口测试通过写成认证全市场READY。未配置定时采集、交易、邮件、部署或Git提交。
