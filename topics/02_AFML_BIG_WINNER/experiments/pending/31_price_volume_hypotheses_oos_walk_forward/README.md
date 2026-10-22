# EP31：八项 A 股量价假说 · EP30 数据 · OOS / Walk-forward

**研究已立项，尚未执行任何回测或产生结果。** 研究合同以 [GOAL.md](GOAL.md) 为准，不以 README 覆盖。

## 研究范围

H01、H02、H03、H07、H09、H10、H11、H12；EP30 D2-v5 是前复权推断价格与标签主输入，原始 OHLCV/成交额/历史换手与身份事实按已封存 D2 输入与字段质量准入。历史评估严格标记 `Historical-proxy`，真实权益结算和可交易性尚未认证。

## 执行入口（后续实现）

1. 先完成 GOAL P0：冻结数据 release/hash、注册假说/端点、控制组、季度 outer splits 和 inner purged CV，检查各字段能否按时点读取；**不能先看 OOS 结果再修改规则**。
2. H09 如无逐笔/委托数据，保持 `BLOCKED_DATA`；其余七条独立推进。
3. 构建训练时可见特征、按事件从 EP30 价格路径派生已成熟标签，必须核对 t0 收盘 / t+1 首个假设可成交开盘及未来公司行动的泄漏。
4. 逐季度 nested expanding/rolling walk-forward；输出完整 OOS 预测、折内参数、主端点、时间块区间、FDR 与同面板基线增量，供独立核查。
5. 报告 Big Winner 成功召回、失败过滤和机会成本的取舍；生成真正新时间的 forward shadow 封存记录并等待标签到期。

**注意：** 仅克隆 Git 并不包含 EP30 私有大表。运行前需要校验 EP30 `outputs/pit_v5/release.json` 指向的本机受控 release；不得用公开汇总 CSV 冒充完整明细。
