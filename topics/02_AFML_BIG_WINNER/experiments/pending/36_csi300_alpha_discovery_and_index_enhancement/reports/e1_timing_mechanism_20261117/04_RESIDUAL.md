# 残差是否解释净收益和日期差

想验证：剥离已知风格后的分数高低，能否解释同日起点风险相近股票的净损益，以及日期差。

分数残差是截面E1对13风格+行业的线性投影余项；收益残差是实际成本后个股收益减冻结同行对照收益，两者不是一回事。没有行业至少10只的筛选，没有用残差重新选一套替代E1。

## 全可评分股票

| state     | outcome   | metric              |   n |     mean |   ci_low |   ci_high |
|:----------|:----------|:--------------------|----:|---------:|---------:|----------:|
| ALL       | date_gap  | rank_ic             |  50 |   0.0044 |  -0.0092 |    0.0187 |
| ALL       | date_gap  | conditional_rank_ic |  50 |   0.0020 |  -0.0147 |    0.0189 |
| ALL       | immediate | rank_ic             |  50 |   0.0093 |  -0.0036 |    0.0231 |
| ALL       | immediate | conditional_rank_ic |  50 |   0.0077 |  -0.0073 |    0.0231 |
| DOWN_DOWN | date_gap  | rank_ic             |  48 |  -0.0044 |  -0.0596 |    0.0502 |
| DOWN_DOWN | date_gap  | conditional_rank_ic |  48 |  -0.0185 |  -0.0779 |    0.0374 |
| DOWN_DOWN | immediate | rank_ic             |  48 |  -0.0034 |  -0.0693 |    0.0557 |
| DOWN_DOWN | immediate | conditional_rank_ic |  48 |  -0.0279 |  -0.0866 |    0.0246 |
| DOWN_UP   | date_gap  | rank_ic             |  50 |  -0.0072 |  -0.0391 |    0.0258 |
| DOWN_UP   | date_gap  | conditional_rank_ic |  50 |  -0.0106 |  -0.0573 |    0.0315 |
| DOWN_UP   | immediate | rank_ic             |  50 |   0.0121 |  -0.0261 |    0.0488 |
| DOWN_UP   | immediate | conditional_rank_ic |  50 |   0.0095 |  -0.0297 |    0.0468 |
| UNKNOWN   | date_gap  | rank_ic             |   0 | nan      | nan      |  nan      |
| UNKNOWN   | date_gap  | conditional_rank_ic |   0 | nan      | nan      |  nan      |
| UNKNOWN   | immediate | rank_ic             |   0 | nan      | nan      |  nan      |
| UNKNOWN   | immediate | conditional_rank_ic |   0 | nan      | nan      |  nan      |
| UP_DOWN   | date_gap  | rank_ic             |  49 |  -0.0100 |  -0.0572 |    0.0362 |
| UP_DOWN   | date_gap  | conditional_rank_ic |  49 |  -0.0068 |  -0.0521 |    0.0369 |
| UP_DOWN   | immediate | rank_ic             |  49 |  -0.0038 |  -0.0495 |    0.0381 |
| UP_DOWN   | immediate | conditional_rank_ic |  49 |   0.0049 |  -0.0432 |    0.0476 |
| UP_UP     | date_gap  | rank_ic             |  49 |   0.0153 |  -0.0285 |    0.0594 |
| UP_UP     | date_gap  | conditional_rank_ic |  49 |   0.0142 |  -0.0307 |    0.0586 |
| UP_UP     | immediate | rank_ic             |  49 |  -0.0053 |  -0.0609 |    0.0515 |
| UP_UP     | immediate | conditional_rank_ic |  49 |  -0.0032 |  -0.0594 |    0.0527 |
| ZERO      | date_gap  | rank_ic             |   0 | nan      | nan      |  nan      |
| ZERO      | date_gap  | conditional_rank_ic |   0 | nan      | nan      |  nan      |
| ZERO      | immediate | rank_ic             |   0 | nan      | nan      |  nan      |
| ZERO      | immediate | conditional_rank_ic |   0 | nan      | nan      |  nan      |

所有个股收益都要求当日可买、终点可卖、窗口估值完整；不把这些统计相关冒充组合净收益。conditional_rank_ic进一步控制信号日非重叠趋势与1日/5日REV。

## 同行对照支持

| tier     |   planned_budget |   recorded_budget |   supported_budget |   residual_scored_budget |
|:---------|-----------------:|------------------:|-------------------:|-------------------------:|
| all13    |           1.0000 |            0.9976 |             0.0000 |                   0.9506 |
| industry |           1.0000 |            0.9976 |             0.9844 |                   0.9506 |
| price    |           1.0000 |            0.9976 |             0.1518 |                   0.9506 |

控制层依次是同行业非原Q5、再短/中期价格各在0.25行业SD以内、再全部13风格逐项在0.25行业SD以内。未改门槛，行业未知不配对，全13零支持不是收益零。同行可被多个原持仓复用，不能把这些条件均值当成保持原持仓数的独立可交易组合。

匹配在未来收益评估前封存；实际净收益比较要求所有冻结同行都可观测，失败不事后删掉不方便的同行。分状态结果：[residual_excess_summary.csv](../../outputs/diagnostics/e1_timing_mechanism_20261117/evaluation_v2/residual_excess_summary.csv)。原持仓内部的残差—净超额及残差—日期差关联：[selected_residual_association.csv](../../outputs/diagnostics/e1_timing_mechanism_20261117/evaluation_v2/selected_residual_association.csv)。

一个辅助结果是中期涨／短期跌组内，残差与行业相对日期差的条件相关为负，未校正p约0.019；这既不是事前主检验，也不是正向独立Alpha，不能挑出来当主发现。价格匹配层有效样本更少；无足够股票的相关为NA。

原账本残差不可评分持仓没有丢弃，见[ledger_residual_coverage.csv](../../outputs/diagnostics/e1_timing_mechanism_20261117/evaluation_v2/ledger_residual_coverage.csv)。信号目标预算约95.06%可评分，剩余约4.94%保留为未识别。残差预测价值尚未解释清楚，不能以统计不显著宣布其不存在。
