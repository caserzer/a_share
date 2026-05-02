# AkShare 到 Qlib 初始链路执行报告

生成时间：2026-05-02  
主题目录：`/home/xiaolv/code/a_share/topics/01_askhare_qlib`

## 结论摘要

本次已经按 `README.md` 的第一阶段目标跑通完整链路：

1. 使用 `AkShare` 拉取选定 A 股股票池和 `SH000300` 基准指数日频数据。
2. 将原始数据转换为 Qlib CSV 格式。
3. 使用 Qlib `dump_bin.py` 导入为 `.bin` 数据集。
4. 验证 Qlib provider 能读取 `$open`、`$close`、`$volume`、`$factor`。
5. 完成简单 TopK 动量回测。
6. 完成 `Alpha158 + LightGBM` 的训练、验证、预测和组合回测。

这次运行的核心结果是：数据链路已经可执行，模型链路也能训练和回测；但当前结果只能作为 plumbing/初始验证，不应直接作为严肃投资结论。

## 本次完成的工作

### 1. 环境准备

使用 `uv` 创建并同步本主题环境。

为了让 Qlib 0.9.x、MLflow 1.27.0 和当前 Python 环境兼容，调整了依赖约束：

- `numpy>=1.26.0,<2.0.0`
- `pandas>=2.2.0,<3.0.0`
- `protobuf>=3.20.0,<4.0.0`
- `setuptools<81.0.0`

原因：

- `mlflow==1.27.0` 不能兼容过新的 `protobuf`。
- `mlflow==1.27.0` 仍依赖 `pkg_resources`，新版 `setuptools` 已移除该入口。
- Qlib 0.9.x 对 `numpy/pandas` 最新大版本组合不够稳。

相关文件：

- `pyproject.toml`
- `uv.lock`
- `.python-version`

### 2. Qlib 源码准备

`dump_bin.py` 来自本地 Qlib 源码目录：

```text
/home/xiaolv/code/qlib/scripts/dump_bin.py
```

当前 checkout 短 hash：

```text
d5379c52
```

### 3. 数据获取

股票池来自：

```text
data/universe/selected_stock_pool.csv
```

本次拉取范围：

```text
2017-01-01 到 2026-04-30
```

实际生成：

| 数据类型 | 文件数 |
| --- | ---: |
| raw 原始日频 CSV | 37 |
| qfq 前复权日频 CSV | 37 |
| Qlib CSV | 37 |
| Qlib features instrument 目录 | 37 |

37 个标的包括：

- `36` 只 selected 股票池股票。
- `SH000300` 沪深 300 基准指数。

原始数据路径：

```text
data/raw/akshare/day/raw/
data/raw/akshare/day/qfq/
```

### 4. 网络与数据源处理

最初使用 README 推荐的 `ak.stock_zh_a_hist`，但 Eastmoney endpoint 在当前网络环境下大量出现：

```text
RemoteDisconnected
ProxyError
```

进一步检查后发现配置的代理会使 Eastmoney 请求失败；直接访问可用但仍存在部分连接中断。因此对抓取脚本做了增强：

- 优先使用 `stock_zh_a_hist`。
- 失败后 fallback 到 `stock_zh_a_daily`。
- 进一步保留 `stock_zh_a_hist_tx` 作为备用 fallback。
- 运行完整抓取时使用了去掉代理变量的命令环境：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY uv run python scripts/01_fetch_akshare_day.py \
  --start-date 2017-01-01 \
  --end-date 2026-04-30 \
  --sleep 0.2 \
  --timeout 30
```

注意：这意味着部分股票数据来自 Eastmoney，部分来自 fallback 源。字段已标准化，但正式研究前仍需要更严格的跨源一致性检查。

### 5. Qlib CSV 转换

转换脚本：

```text
scripts/02_transform_to_qlib_csv.py
```

输出路径：

```text
data/interim/qlib_csv/day/
```

转换结果：

| 指标 | 数值 |
| --- | ---: |
| Qlib CSV 文件数 | 37 |
| 总行数 | 82,339 |
| 数据质量错误文件数 | 0 |

字段包括：

```text
date, open, close, high, low, volume, money, factor
```

`factor` 计算方式：

```text
qfq_close / raw_close
```

`SH000300` 基准指数没有复权概念，qfq 文件由 raw 文件复制生成，因此 factor 为 `1.0`。

### 6. 数据质量检查

检查脚本：

```text
scripts/04_check_qlib_data.py
```

报告路径：

```text
outputs/reports/data_quality_report.csv
```

检查内容包括：

- date 是否递增。
- date 是否重复。
- OHLC 是否为正。
- `high >= open/close/low`。
- `low <= open/close/high`。
- volume/factor 是否异常。
- 缺失值统计。

结果：

```text
files: 37
rows: 82339
files_with_errors: 0
```

### 7. Qlib bin 导入

导入脚本：

```text
scripts/03_dump_qlib_bin.sh
```

输出目录：

```text
data/qlib/cn_data/
```

已生成：

```text
data/qlib/cn_data/calendars/day.txt
data/qlib/cn_data/instruments/all.txt
data/qlib/cn_data/instruments/selected.txt
data/qlib/cn_data/features/*/*.day.bin
```

并验证 Qlib 可读取样例：

```text
instrument: SZ000001
fields: $open, $close, $high, $low, $volume, $factor
period: 2020-01-01 到 2020-01-31
```

### 8. 简单 TopK 回测

脚本：

```text
scripts/05_backtest_topk.py
```

配置：

```text
configs/qlib_backtest_topk.yaml
```

策略：

- 20 日动量信号。
- `TopkDropoutStrategy`
- `topk=30`
- `n_drop=3`
- 初始资金：`1,000,000`
- 回测区间：`2021-01-04` 到 `2026-04-29`

输出：

```text
outputs/backtests/topk_portfolio_metrics.csv
outputs/backtests/topk_positions.pkl
outputs/backtests/topk_indicators.pkl
```

TopK 结果摘要：

| 指标 | 数值 |
| --- | ---: |
| 起始资金 | 1,000,000 |
| 结束账户价值 | 1,298,841.92 |
| 累计收益 | 29.88% |
| 年化收益 | 5.25% |
| 最大回撤 | -26.39% |
| 同期 benchmark 累计收益 | -7.69% |
| 同期 benchmark 年化收益 | -1.55% |
| 平均换手 | 7.15% |
| 累计交易成本 | 95,758.25 |

说明：这个 TopK 结果主要用于验证数据和回测 plumbing，不代表已经得到可用策略。

### 9. Alpha158 + LightGBM 工作流

配置：

```text
configs/qlib_lightgbm_alpha158.yaml
```

运行命令：

```bash
uv run qrun configs/qlib_lightgbm_alpha158.yaml -e alpha158_lightgbm_selected
```

数据切分：

| 用途 | 日期 |
| --- | --- |
| 训练集 | 2017-01-01 到 2022-12-31 |
| 验证集 | 2023-01-01 到 2024-12-31 |
| 测试集 | 2025-01-01 到 2026-04-30 |
| 组合回测 | 2025-01-01 到 2026-04-29 |

注意：组合回测结束日是 `2026-04-29`，不是 `2026-04-30`。Qlib backtest 在最后一个交易步需要读取下一个 calendar entry，而当前数据截止到 `2026-04-30`，所以实际可执行的最后回测日必须提前一日。

MLflow/Qlib run：

```text
mlruns/1/2698476e930d480ab6864013c9277dd8/
```

主要产物：

```text
pred.pkl
sig_analysis/ic.pkl
sig_analysis/ric.pkl
portfolio_analysis/port_analysis_1day.pkl
portfolio_analysis/report_normal_1day.pkl
portfolio_analysis/positions_normal_1day.pkl
portfolio_analysis/indicator_analysis_1day.pkl
```

模型训练摘要：

| 指标 | 数值 |
| --- | ---: |
| best iteration | 10 |
| best valid l2 | 0.971981 |
| logged final train l2 | 0.963342 |
| logged final valid l2 | 0.972184 |
| IC | 0.015701 |
| ICIR | 0.071812 |
| Rank IC | 0.005315 |
| Rank ICIR | 0.022721 |

组合分析摘要：

| 指标 | 数值 |
| --- | ---: |
| benchmark annualized_return | 16.12% |
| excess return without cost annualized | -7.77% |
| excess return without cost information_ratio | -0.6715 |
| excess return without cost max_drawdown | -21.48% |
| excess return with cost annualized | -11.39% |
| excess return with cost information_ratio | -0.9844 |
| excess return with cost max_drawdown | -24.33% |
| ffr | 0.99886 |

结论：LightGBM workflow 已跑通，但初始模型在测试期相对基准表现较差，当前不具备策略有效性结论。

## 本次代码与配置变更

新增或修改了这些关键文件：

```text
pyproject.toml
uv.lock
.python-version
.gitignore
configs/qlib_backtest_topk.yaml
configs/qlib_lightgbm_alpha158.yaml
data/universe/selected_stock_pool.csv
data/universe/qlib_selected.txt
scripts/pipeline_utils.py
scripts/01_fetch_akshare_day.py
scripts/02_transform_to_qlib_csv.py
scripts/03_dump_qlib_bin.sh
scripts/04_check_qlib_data.py
scripts/05_backtest_topk.py
```

重要修复：

- 为 AkShare 抓取增加 fallback 数据源。
- 修复 Qlib `D.features` 对 `selected` market 字符串不直接接受的问题。
- 修复 TopK positions 在当前 Qlib 版本中返回 dict 时的保存逻辑。
- 将 TopK 和 LightGBM 的组合回测结束日调整为 `2026-04-29`。
- 将 `mlruns/` 加入 `.gitignore`。

## 需要重点注意的问题

### 1. 当前数据混合了多个 AkShare 后端

由于 Eastmoney 请求不稳定，本次实际数据来源包含：

- Eastmoney `stock_zh_a_hist`
- Sina `stock_zh_a_daily`

字段已经标准化，但正式研究前需要确认：

- 同一只股票 raw 与 qfq 是否来自同一后端。
- 不同后端的成交量单位是否完全一致。
- `money` 字段在不同后端是否口径一致。
- qfq 价格与 raw 价格计算出的 `factor` 是否符合预期。

### 2. qfq/factor 处理仍是初始版本

当前 `factor = qfq_close / raw_close`。这能满足 Qlib 导入和基础回测，但严肃研究前建议：

- 和 AkShare/交易所/其他供应商复权因子交叉校验。
- 检查分红送转日前后 factor 跳变。
- 检查 raw OHLC 与 qfq OHLC 的比例是否一致。

### 3. `volume` 和 `money` 需要进一步确认口径

转换阶段默认把 AkShare A 股成交量从“手”乘以 100 转为“股”。  
Sina fallback 原始 `volume` 已经是股，因此抓取脚本在保存为 AkShare 中文字段时先除以 100，保持后续 transformer 的统一逻辑。

这个逻辑已经跑通，但正式使用前仍应抽样比对：

- `SZ000001`
- `SH600519`
- `SH600000`
- `SH601318`
- `SH000300`

### 4. 股票池较小，模型结论不稳定

当前股票池只有 36 只大盘/高流动性股票。  
这适合验证链路，但对 Alpha158 + LightGBM 来说样本过小，横截面 IC 和组合结果容易不稳定。

后续如果要做有效策略研究，应扩大到：

- 沪深 300 全成分。
- 中证 500。
- 全 A 可交易股票池。

### 5. 回测终止日需要保留下一交易日

Qlib backtest 会在 trade step 边界读取下一 calendar entry。  
如果数据只到 `2026-04-30`，组合回测结束日应设置为 `2026-04-29`。

后续每日增量更新时应保证：

- 数据截止日 >= 回测结束日后的一个交易日。

### 6. Qlib warning 不全是错误，但需要理解

运行过程中出现过这些 warning：

- `$close field data contains nan`
- `load calendar error: freq=day, future=True; return current calendar`
- `Mean of empty slice`
- `Gym has been unmaintained since 2022`

本次没有阻断流程。主要原因：

- 股票上市日期不同，早期横截面存在 NaN。
- 当前没有 future calendar。
- 部分交易日部分股票不可交易或缺失。
- Qlib 间接依赖旧版 gym。

正式研究前建议减少或解释这些 warning，而不是简单忽略。

### 7. LightGBM 初始结果偏弱

本次 `Alpha158 + LightGBM` 在测试期：

- IC 为正但很弱。
- Rank IC 接近 0。
- 扣成本超额年化为负。

这说明链路可用，但模型/股票池/特征/标签/交易设定都需要继续调试。

### 8. 不要把生成数据和 mlruns 当作源码提交

当前 `.gitignore` 已忽略：

- `.venv/`
- raw/qfq CSV
- Qlib CSV
- Qlib bin 数据
- backtest 输出
- `mlruns/`

这些文件体积大且可重建，应作为本地运行产物管理。

## 推荐的下一步

1. 对 5 到 10 只股票做人工抽样核验，确认价格、成交量、成交额和 factor。
2. 增加一份数据源审计表，记录每只股票 raw/qfq 最终来自 Eastmoney 还是 fallback。
3. 给 transformer 增加更严格的 factor 跳变检查。
4. 将 `SH000300` benchmark 的指数数据单独处理，避免和股票 qfq 逻辑混在一起。
5. 扩大股票池后重新训练 Alpha158 + LightGBM。
6. 增加一个固定 smoke test，例如只跑 `SZ000001`、`SH600000`、`SH000300` 的小链路。
7. 若后续要正式研究，建议引入成分股历史变更和上市/退市过滤，避免 survivorship bias。

## 复现命令

从主题目录执行：

```bash
cd /home/xiaolv/code/a_share/topics/01_askhare_qlib
uv sync --locked
```

抓取数据：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY uv run python scripts/01_fetch_akshare_day.py \
  --start-date 2017-01-01 \
  --end-date 2026-04-30 \
  --sleep 0.2 \
  --timeout 30
```

转换为 Qlib CSV：

```bash
uv run python scripts/02_transform_to_qlib_csv.py \
  --start-date 2017-01-01 \
  --end-date 2026-04-30 \
  --force \
  --fail-fast
```

质量检查：

```bash
uv run python scripts/04_check_qlib_data.py \
  --csv-dir data/interim/qlib_csv/day \
  --report outputs/reports/data_quality_report.csv \
  --fail-on-error
```

导入 Qlib bin：

```bash
QLIB_REPO="$HOME/code/qlib" bash scripts/03_dump_qlib_bin.sh
```

检查 Qlib provider：

```bash
uv run python scripts/04_check_qlib_data.py \
  --csv-dir data/interim/qlib_csv/day \
  --qlib-dir data/qlib/cn_data \
  --sample-instrument SZ000001 \
  --start-time 2020-01-01 \
  --end-time 2020-01-31 \
  --report outputs/reports/data_quality_report.csv \
  --check-provider \
  --fail-on-error
```

运行简单 TopK 回测：

```bash
uv run python scripts/05_backtest_topk.py
```

运行 Alpha158 + LightGBM：

```bash
uv run qrun configs/qlib_lightgbm_alpha158.yaml -e alpha158_lightgbm_selected
```

