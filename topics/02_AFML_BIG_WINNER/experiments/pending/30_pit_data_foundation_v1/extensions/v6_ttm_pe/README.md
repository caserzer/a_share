# D2 V6：历史 Universe 的 TTM PE 补充

范围：沿用 EP32 已冻结研究日历，2017-01-03 至 2026-10-21 的全部 2,377 个交易日；以历史证券身份、上市/退市边界和代码区间连接数据，不用今天的股票名单筛选过去。新文件独立保存，不改 V2/V5 或 EP32 V1—V34。

## 字段与可得性合同

- `vendor_pe_ttm`：供应商指定交易日原始 TTM PE，保留负值、零值、缺失；无穷值记为无效。
- `pe_ttm`：仅保留有限正值，供对数扩张研究使用。负值标记 `NONPOSITIVE_EARNINGS_PROXY`，不视为估值收缩，不填零；零值标记 `ZERO_OR_UNDEFINED`。
- `date` / `session_close`：估值日期及该日 15:00（上海时区），只约束价格部分的观察时点，**不是财务分母当时可得的证明**。
- `source_observed_at` / `ingested_at`：实际查询和归档时间。`known_at` 留空，`earnings_vintage_status=UNPROVEN`。
- `source_sha256` / `response_sha256` / 分区回执：可追溯原始供应商回复；旧日分区只在哈希验证后复用。
- 全部值为 `Historical-proxy`。严格 PIT 查询拒绝返回这些估值；历史回放必须显式选择代理口径。`archived` 模式还要求实际接收时间不晚于决策时点。
- 盘中只能查上一个已收盘交易日；同日 15:00 起可用当日代理。仅连接准确交易日，不跨日补值，也不跨缺口计算变化。
- Universe 继承 D2 的历史成员资格代理边界，不把停牌、ST 或不完整交易资格误认证为可交易池。北交所及接口未覆盖成员保留缺失。

## 实现

`src/acquire.py` 可断点续传；最初使用 8 个进程重叠网络等待，全局每次 RPC 发起间隔至少 1.05 秒。BaoStock 随后明确返回访问拒绝，所有进程已停止，并设置硬停止标记，后续不会自动重试；保留获取成功的原始分区。旧 RPC 未把“黑名单用户”识别为权限错误，导致停止前出现重复失败；本扩展已修复识别并增加回归测试，默认并发改为 1，但不自行解除停止标记。

`src/acquire_eastmoney.py` 使用另一个独立公开来源，顺序请求，请求发起间隔至少 1 秒，遵循实际 10,000 行分页上限，校验总数及证券日期唯一性。主源固定为 Eastmoney，BaoStock 只作为独立对照，查询时不自动拼接。新增原始响应和分区写入私有 `~/.cache/a_share/ep30_d2/ttm_pe_v6`，不读取个人 API 密钥。

`src/build.py` 生成日期分区、身份映射和 Universe 覆盖审计；`src/ttm_pe_dataset.py` 提供只读 `universe_asof` / `join_universe` / `get_asof`。封存发布由 `src/seal.py` 执行，报告和小型审计表留在本扩展。

供应商可能以现行代码回写过去的估值：使用 D2 已审核的唯一代码别名解析稳定证券 ID，同时保留 `provider_instrument` 和历史有效 `instrument`。同一证券同日若出现两个代码且估值相同，归并但保留别名和原始行；估值冲突则规范值为 UNKNOWN，不任选一个。

## 调用示例

将本扩展 `src` 加入 Python 导入路径，再使用：

```python
from ttm_pe_dataset import D2TTMPEDataset
data = D2TTMPEDataset()
universe = data.universe_asof(
    '2024-06-28 15:00:00',
    quality_tier='Historical-proxy', provider='eastmoney')
# 对调用方已经冻结的、security_id 唯一的历史 Universe 作左连接：
enriched = data.join_universe(
    my_universe, '2024-06-28 15:00:00',
    quality_tier='Historical-proxy', provider='eastmoney')
# 默认严格模式返回 UNKNOWN；不会把查询日当作财报首次可得日。
strict = data.get_asof('SH600000', 'pe_ttm', '2024-06-28 15:00:00')
```

`src/readiness.py` 仅审计 21/42/63/126/252/504/756 日连续正 PE 窗口和 EP32 历史行业成员覆盖，不读取未来收益字段、不训练模型。不同来源的 PE 不能混在同一个滚动窗口中。

这次补数据，不重跑或覆盖 V34 的模型结论。完成后，PE × 成交扩张可以开展历史代理验证；财报首次披露版本未认证的限制仍在。
