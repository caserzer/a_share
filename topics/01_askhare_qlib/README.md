# AkShare 到 Qlib 的 A 股数据链路

本主题研究如何把 `AkShare` 作为 A 股数据源，完成数据抽取、字段标准化、复权处理、导入 `Qlib`，并在 `Qlib` 中跑通一个最小可复现的回测流程。

当前仓库中的实际主题路径是：

```bash
/home/xiaolv/code/a_share/topics/01_askhare_qlib
```

下文所有命令默认从当前主题目录执行，`uv` 也使用这个目录下的 `pyproject.toml` 和 `uv.lock`：

```bash
cd /home/xiaolv/code/a_share/topics/01_askhare_qlib
export TOPIC_DIR="$PWD"
```

> 说明：目录名里 `askhare` 是当前仓库已有路径。后续如果统一修正为 `akshare`，需要同时更新本文中的 `TOPIC_DIR`。

## 研究目标

这个主题不只是验证单个接口能否取数，而是要形成一条可重复执行的数据与回测链路：

1. 从 `AkShare` 拉取 A 股日频行情、股票列表和必要的复权数据。
2. 把中文字段、代码格式、交易日、复权价格、成交量、成交额转换成 `Qlib` 可识别的格式。
3. 用 `Qlib` 的 `dump_bin.py` 把 CSV 数据导入为 `.bin` 数据集。
4. 验证 `Qlib` 能读取 `$open`、`$close`、`$volume`、`$factor` 等字段。
5. 使用一个简单预测信号或 `Alpha158 + LightGBM` 流程，跑通回测与结果记录。
6. 沉淀数据质量检查、增量更新和回测约束，避免只得到一次性的实验脚本。

## 推荐目录结构

为了让数据路径和脚本路径可复制，建议本主题按下面方式组织：

```text
topics/01_askhare_qlib/
├── README.md
├── pyproject.toml                     # 后续用 uv 管理依赖时补充
├── uv.lock                            # 后续锁定依赖版本时生成
├── configs/
│   ├── qlib_backtest_topk.yaml
│   └── qlib_lightgbm_alpha158.yaml
├── data/
│   ├── universe/
│   │   ├── selected_stock_pool.csv   # 本主题选定股票池
│   │   └── qlib_selected.txt         # Qlib instruments 自定义股票池
│   ├── raw/
│   │   └── akshare/day/              # AkShare 原始导出，不直接给 Qlib 使用
│   ├── interim/
│   │   └── qlib_csv/day/             # 转换后的 Qlib CSV
│   └── qlib/
│       └── cn_data/                  # dump_bin.py 生成的 Qlib bin 数据
├── notebooks/
├── outputs/
│   ├── reports/
│   └── backtests/
└── scripts/
    ├── 01_fetch_akshare_day.py
    ├── 02_transform_to_qlib_csv.py
    ├── 03_dump_qlib_bin.sh
    ├── 04_check_qlib_data.py
    └── 05_backtest_topk.py
```

初始化目录：

```bash
mkdir -p \
  "$TOPIC_DIR/configs" \
  "$TOPIC_DIR/data/universe" \
  "$TOPIC_DIR/data/raw/akshare/day" \
  "$TOPIC_DIR/data/interim/qlib_csv/day" \
  "$TOPIC_DIR/data/qlib/cn_data" \
  "$TOPIC_DIR/notebooks" \
  "$TOPIC_DIR/outputs/reports" \
  "$TOPIC_DIR/outputs/backtests" \
  "$TOPIC_DIR/scripts"
```

## 数据流

```text
AkShare 接口
  -> data/raw/akshare/day/*.csv
  -> 清洗、复权、字段映射、代码标准化
  -> data/interim/qlib_csv/day/SH600000.csv
  -> Qlib scripts/dump_bin.py dump_all
  -> data/qlib/cn_data/
  -> Qlib DataHandler / Dataset / Strategy / Backtest
```

## Python 环境与依赖管理

本主题的 Python 环境统一使用 `uv` 管理，包括 Python 版本、虚拟环境、依赖安装和命令执行。后续不要混用 `conda install`、系统级 `pip install` 或手动维护虚拟环境。

推荐约定：

- 使用 `pyproject.toml` 声明依赖。
- 使用 `uv.lock` 锁定依赖版本，保证回测环境可复现。
- 使用 `uv sync` 创建或同步本地环境。
- 使用 `uv add` 增加依赖，例如 `akshare`、`pyqlib`、`pandas`、`numpy`、`lightgbm`。
- 运行 Python 脚本或命令行工具时统一使用 `uv run`。

初始化环境时的参考命令：

```bash
cd "$TOPIC_DIR"
uv init --bare
uv add akshare pyqlib pandas numpy lightgbm
uv sync
```

后续执行脚本时统一使用：

```bash
uv run python scripts/01_fetch_akshare_day.py
uv run python scripts/02_transform_to_qlib_csv.py
uv run qrun configs/qlib_lightgbm_alpha158.yaml
```

## 股票池选择

本主题先使用一个偏大盘、偏高流动性的 A 股样本池跑通链路。用户原始列表中包含重复股票，去重后共 `36` 只。

股票池主文件建议保存为：

```text
data/universe/selected_stock_pool.csv
```

字段：

```csv
code,name,instrument,exchange
```

当前股票池：

| 原始代码 | Qlib instrument | 股票名称 |
| --- | --- | --- |
| `601628` | `SH601628` | 中国人寿 |
| `601319` | `SH601319` | 中国人保 |
| `600030` | `SH600030` | 中信证券 |
| `600104` | `SH600104` | 上汽集团 |
| `000858` | `SZ000858` | 五粮液 |
| `002415` | `SZ002415` | 海康威视 |
| `000333` | `SZ000333` | 美的集团 |
| `601166` | `SH601166` | 兴业银行 |
| `601998` | `SH601998` | 中信银行 |
| `601138` | `SH601138` | 工业富联 |
| `600519` | `SH600519` | 贵州茅台 |
| `000651` | `SZ000651` | 格力电器 |
| `601318` | `SH601318` | 中国平安 |
| `600276` | `SH600276` | 恒瑞医药 |
| `600585` | `SH600585` | 海螺水泥 |
| `601766` | `SH601766` | 中国中车 |
| `601800` | `SH601800` | 中国交建 |
| `600036` | `SH600036` | 招商银行 |
| `601601` | `SH601601` | 中国太保 |
| `000001` | `SZ000001` | 平安银行 |
| `600028` | `SH600028` | 中国石化 |
| `601668` | `SH601668` | 中国建筑 |
| `603288` | `SH603288` | 海天味业 |
| `600000` | `SH600000` | 浦发银行 |
| `600887` | `SH600887` | 伊利股份 |
| `601328` | `SH601328` | 交通银行 |
| `600900` | `SH600900` | 长江电力 |
| `300498` | `SZ300498` | 温氏股份 |
| `300760` | `SZ300760` | 迈瑞医疗 |
| `601088` | `SH601088` | 中国神华 |
| `601988` | `SH601988` | 中国银行 |
| `601818` | `SH601818` | 光大银行 |
| `601398` | `SH601398` | 工商银行 |
| `601288` | `SH601288` | 农业银行 |
| `600016` | `SH600016` | 民生银行 |
| `601939` | `SH601939` | 建设银行 |

回测基准指数需要额外导入 `Qlib` 数据集，但不放入 `selected` 股票池：

| 指数代码 | Qlib instrument | 指数名称 |
| --- | --- | --- |
| `000300` | `SH000300` | 沪深 300 |

如果需要让 `Qlib` 使用这个股票池作为 `market`，后续可以在 `data/qlib/cn_data/instruments/selected.txt` 中维护自定义股票池。每行对应一只股票，包含 `instrument`、起始日期和结束日期。

之后在 Qlib 配置中使用：

```yaml
market: &market selected
benchmark: &benchmark SH000300
```

## AkShare 数据获取

优先使用 `stock_zh_a_hist` 获取个股日频行情。该接口返回中文字段，需要在转换阶段统一重命名。

示例输入：

```python
import akshare as ak

df_raw = ak.stock_zh_a_hist(
    symbol="000001",
    period="daily",
    start_date="20170101",
    end_date="20251231",
    adjust="",
)

df_qfq = ak.stock_zh_a_hist(
    symbol="000001",
    period="daily",
    start_date="20170101",
    end_date="20251231",
    adjust="qfq",
)
```

建议同时保存不复权数据和前复权数据：

- 不复权数据用于保留真实成交量、成交额、原始价格。
- 前复权数据用于构造连续价格序列。
- `factor` 建议用 `qfq_close / raw_close` 对齐日期后计算。
- 如果只是先跑通导入和回测链路，可以临时使用前复权 OHLC 并把 `factor` 设为 `1.0`，但这只能作为 plumbing 验证，不适合作为严肃研究数据。

## 字段转换规则

`Qlib` 的基础字段至少需要：

| Qlib 字段 | AkShare 字段 | 说明 |
| --- | --- | --- |
| `date` | `日期` | 格式统一为 `YYYY-MM-DD` |
| `open` | `开盘` | 建议使用复权后的开盘价 |
| `close` | `收盘` | 建议使用复权后的收盘价 |
| `high` | `最高` | 建议使用复权后的最高价 |
| `low` | `最低` | 建议使用复权后的最低价 |
| `volume` | `成交量` | AkShare 单位通常为手，落库前需确认是否乘以 100 |
| `money` | `成交额` | 单位通常为元 |
| `factor` | 计算得到 | `复权收盘价 / 不复权收盘价` |

股票代码统一转成 `Qlib` 常见格式：

| 原始代码 | Qlib instrument |
| --- | --- |
| `600000` | `SH600000` |
| `000001` | `SZ000001` |
| `300750` | `SZ300750` |
| `688981` | `SH688981` |
| `830799` | `BJ830799` |

转换后的单只股票 CSV 示例：

```csv
date,open,close,high,low,volume,money,factor
2020-01-02,8.41,8.46,8.52,8.35,153023100,1530231870.0,0.8421
2020-01-03,8.47,8.55,8.62,8.45,111619400,1116194870.0,0.8430
```

建议一只股票一个文件，文件名使用 `Qlib` instrument：

```text
data/interim/qlib_csv/day/SH600000.csv
data/interim/qlib_csv/day/SZ000001.csv
```

## 导入 Qlib

`Qlib` 官方通过 `scripts/dump_bin.py` 把 CSV 或 Parquet 转成 `.bin` 格式。假设本地已经有 Qlib 源码：

```bash
export QLIB_REPO="${QLIB_REPO:-$HOME/code/qlib}"
test -f "$QLIB_REPO/scripts/dump_bin.py"
```

如果上面的检查失败，先准备 Qlib 源码：

```bash
mkdir -p "$HOME/code"
git clone https://github.com/microsoft/qlib.git "$HOME/code/qlib"
```

执行全量导入：

```bash
uv run python "$QLIB_REPO/scripts/dump_bin.py" dump_all \
  --data_path "$TOPIC_DIR/data/interim/qlib_csv/day" \
  --qlib_dir "$TOPIC_DIR/data/qlib/cn_data" \
  --freq day \
  --include_fields open,close,high,low,volume,money,factor \
  --date_field_name date \
  --file_suffix .csv
```

导入后重点检查这些路径：

```bash
find "$TOPIC_DIR/data/qlib/cn_data" -maxdepth 3 -type f | head
test -f "$TOPIC_DIR/data/qlib/cn_data/calendars/day.txt"
test -f "$TOPIC_DIR/data/qlib/cn_data/instruments/all.txt"
```

## Qlib 读取验证

导入成功后，用最小脚本检查 `Qlib` 是否能读到数据：

```python
import qlib
from qlib.constant import REG_CN
from qlib.data import D

provider_uri = "/home/xiaolv/code/a_share/topics/01_askhare_qlib/data/qlib/cn_data"

qlib.init(provider_uri=provider_uri, region=REG_CN)

df = D.features(
    instruments=["SZ000001"],
    fields=["$open", "$close", "$high", "$low", "$volume", "$factor"],
    start_time="2020-01-01",
    end_time="2020-01-31",
    freq="day",
)

print(df.tail())
```

如果这里报 `instruments not exists`，优先检查：

- `data/qlib/cn_data/instruments/all.txt` 是否存在。
- CSV 文件名是否是 `SH600000.csv`、`SZ000001.csv` 这种格式。
- `dump_bin.py` 是否真的扫到了转换后的 CSV 文件。
- `qlib.init(provider_uri=...)` 是否指向本文生成的 `cn_data` 目录。

## 回测方案

先做两层回测，避免一开始就把数据问题、特征问题和模型问题混在一起。

### 1. 简单信号回测

先构造一个最小预测分数，例如过去 20 日动量、过去 5 日反转、成交额分位数等，生成 `pred_score`：

```text
MultiIndex: datetime, instrument
Column: score
```

然后使用 `TopkDropoutStrategy` 回测：

```python
import qlib
from qlib.constant import REG_CN
from qlib.backtest import backtest, executor
from qlib.contrib.strategy import TopkDropoutStrategy
from qlib.utils.time import Freq

provider_uri = "/home/xiaolv/code/a_share/topics/01_askhare_qlib/data/qlib/cn_data"
qlib.init(provider_uri=provider_uri, region=REG_CN)

freq = "day"

strategy = TopkDropoutStrategy(
    signal=pred_score,
    topk=30,
    n_drop=3,
)

executor_obj = executor.SimulatorExecutor(
    time_per_step=freq,
    generate_portfolio_metrics=True,
)

portfolio_metric_dict, indicator_dict = backtest(
    executor=executor_obj,
    strategy=strategy,
    start_time="2021-01-01",
    end_time="2024-12-31",
    benchmark="SH000300",
    account=1000000,
    exchange_kwargs={
        "freq": freq,
        "limit_threshold": 0.095,
        "deal_price": "close",
        "open_cost": 0.0005,
        "close_cost": 0.0015,
        "min_cost": 5,
    },
)

analysis_freq = "{}{}".format(*Freq.parse(freq))
report, positions = portfolio_metric_dict.get(analysis_freq)
```

这个阶段的目标不是追求收益，而是确认：

- 数据集能稳定读取。
- 交易日历和股票池正常。
- 停牌、涨跌停、缺失值不会导致回测崩溃。
- 交易成本、基准、持仓数和换手逻辑符合预期。

### 2. Alpha158 + LightGBM 回测

数据链路稳定后，再使用 `Qlib` 的标准工作流：

```bash
uv run qrun configs/qlib_lightgbm_alpha158.yaml
```

配置中应显式使用本主题数据路径：

```yaml
qlib_init:
  provider_uri: /home/xiaolv/code/a_share/topics/01_askhare_qlib/data/qlib/cn_data
  region: cn

market: &market selected
benchmark: &benchmark SH000300
```

建议切分：

| 用途 | 日期 |
| --- | --- |
| 训练集 | `2017-01-01` 到 `2022-12-31` |
| 验证集 | `2023-01-01` 到 `2024-12-31` |
| 测试集 | `2025-01-01` 到 `2026-04-30` |

## 数据质量检查清单

每次重新导入数据后，至少检查：

- 同一只股票的 `date` 是否严格递增且无重复。
- `open/high/low/close` 是否存在非正数或极端跳变。
- `high >= max(open, close, low)`、`low <= min(open, close, high)` 是否成立。
- `volume` 和 `money` 的单位是否一致。
- `factor` 是否为空、为 0 或出现异常跳变。
- 样本内是否混入退市股、北交所股票或上市前空数据。
- 股票池文件是否符合预期，例如只跑沪深 300、全 A 或自定义池。
- 使用未来数据的字段不能进入特征。

## 增量更新思路

初期建议每天全量重建最近若干年的 CSV，再执行 `dump_all`，这样最简单也最容易排查问题。等链路稳定后再拆分：

- `dump_all`：首次构建或字段逻辑变化时使用。
- `dump_update`：只追加新交易日时使用。
- `dump_fix`：历史复权因子变化、分红送转导致历史价格需要修正时使用。

对于 A 股复权数据，历史价格可能因为除权除息发生回写。只做追加容易引入前后不一致，因此正式研究前需要设计“回看窗口”，例如每次重建最近 180 个自然日的数据。

## 参考资料

- Qlib 数据格式与 `dump_bin.py`：https://qlib.readthedocs.io/en/latest/component/data.html
- Qlib workflow 与 `qrun`：https://qlib.readthedocs.io/en/latest/component/workflow.html
- Qlib 策略与回测：https://qlib.readthedocs.io/en/latest/component/strategy.html
- AkShare A 股历史行情接口：https://akshare.akfamily.xyz/data/stock/stock.html

## 当前结论

本主题的第一阶段成功标准是：用 `AkShare` 拉取少量股票数据，转换成 `Qlib` CSV，导入为 `Qlib` bin 数据，并能在本地路径 `/home/xiaolv/code/a_share/topics/01_askhare_qlib/data/qlib/cn_data` 上完成一次简单 TopK 回测。

后续再逐步扩大到全 A 股票池、自动更新、严肃的数据质量检查和模型化回测。
