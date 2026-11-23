# 观察名单生成

在已登记的 H10 主相位或平移五日相位，使用收盘后生成的完整 EP37 合格成员评分表、截至该日的历史行业有效期表、完整交易日历及 EP34 完整周目录。交易日历为单列无标题日期 CSV，包含起点 2021-01-08 至下一交易日。目录根下包含 early_model/periods 和 momentum/periods。运行方式如下。

```bash
python capture.py --signal-date YYYY-MM-DD --scores SCORES.parquet --industry INDUSTRY.parquet --calendar CALENDAR.csv --catalog CATALOG_ROOT
```

程序在上海时间信号日收盘至下次开盘前生成一次本地观察记录，写入 predictions/YYYY-MM-DD.json。目标含四套全名单与权重、选股规则版本、替换股、来源文件哈希和生成时刻。重复运行不能覆盖既有记录。输入评分须由冻结的预测流程生成，行业目录须由完整的 EP34 刷新流程交付；文件哈希用于识别取用版本，不能单独证明上游数据最初公布时间。缺少新数据时继续保留缺口。历史复核使用 `python verify_capture.py`，只写复核回执。
