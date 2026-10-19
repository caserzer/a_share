"""Build the readable episode report from the actual retained outputs."""
import json
import numpy as np
import pandas as pd
from run_price_pilot import OUT

NAMES={'expanding_empirical':'总体历史分布','peers_risk_size':'风险/市值邻居','peers_valuation':'加入估值邻居',
       'peers_fundamental':'加入财报邻居','peers_macro':'加入信用/利率邻居','catboost_full':'完整CatBoost'}


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def run():
    ep=OUT.parent
    r05=pd.read_csv(OUT/'r05_holdout/summary.csv').set_index(['horizon','model'])
    absolute=[]
    for model,name in NAMES.items():
        a,b=r05.loc[(126,model)],r05.loc[(252,model)]
        absolute.append([name,f'{a.crps:.6f}',f'{b.crps:.6f}',f'{b.brier:.6f}',f'{b.below_q05:.2%}',f'{b.coverage90:.2%}'])
    portfolio=pd.read_csv(OUT/'r06_portfolio_probe/summary.csv')
    selected=portfolio[(portfolio.model=='peers_valuation') & (portfolio.fee==.001)].set_index('style')
    allocation=[]
    for style,name in [('all_equal','全池等权'),('selected_equal','同20只候选等权'),('selected_inverse_vol','同候选逆波动率'),
                       ('distribution_full','同候选分布权重、满仓对照'),('distribution_dynamic','同候选分布权重、动态总仓位')]:
        r=selected.loc[style]
        allocation.append([name,f'{r.total_return:.2%}',f'{r.max_drawdown:.2%}',f'{r.average_gross:.2%}'])
    matched=pd.read_csv(OUT/'r07_sensitivities/matched_gross_summary.csv')
    m=matched[(matched.model=='peers_valuation') & (matched.fee==.001)].iloc[0]
    allocation.append(['相同动态总仓位、全池等权（事后对照）',f'{m.total_return:.2%}',f'{m.max_drawdown:.2%}',f'{m.average_gross:.2%}'])
    excess=pd.read_csv(OUT/'r08_excess_probe/phase_summary.csv').set_index(['phase','horizon','model'])
    exrows=[]
    for model,name in NAMES.items():
        early=excess.loc[('exploration_2021_2023',252,model)]
        later=excess.loc[('posthoc_2024_plus',252,model)]
        exrows.append([name,f'{early.crps:.6f}',f'{later.crps:.6f}',f'{later.brier:.6f}'])
    definitions=pd.read_csv(OUT/'r09_total_return_sensitivity/return_definition_difference.csv')
    defrows=[[int(r.horizon),int(r.rows),f'{r.median_abs_difference*100:.4f}个百分点',
              f'{r.p95_abs_difference*100:.4f}个百分点',f'{r.max_abs_difference*100:.2f}个百分点',
              f'{r.up_direction_disagreement:.3%}'] for r in definitions.itertuples()]
    factor=pd.read_csv(OUT/'r09_total_return_sensitivity/unexplained_factor_events.csv')
    text=f'''# EP24：条件收益分布与动态仓位——探索实验总结

整理日期：2026-10-19。行情及收益观察截至2026-05-29，本文不是今日行情预测。

## 结论

**本轮没有找到足以支持概率驱动动态仓位的稳定预测优势。** 方案、公开数据准备、概率模型、滚动评估、配仓对照和针对暴露问题的追加实验均已执行。实验完成不等于原始强命题得到证实。

简单历史分布和风险/市值邻居是有价值的最低基线。估值、保守可用财报与信用变量在部分阶段有局部改善，但未表现出跨阶段稳定增量；完整树模型也没有稳定胜出。概率偏差会直接传入仓位，产生明显的资金闲置和错误集中。

这支持“暂不升级为概率配仓系统”，不支持“估值、财报或信用信息永远无效”。历史行业、原始财报版本、全市场无偏覆盖和完整公司行动仍限制更强的推断。

## 做了哪些实验

| 轮次 | 暴露的问题与追加行动 | 结果 |
| --- | --- | --- |
| R01 | 经验分布与多分位数树模型比较 | 技术模型未稳定胜出，左尾低估 |
| R02 | 用已成熟的过去预测误差校准；与近期历史比较 | 一端覆盖改善，但整体误差未改善 |
| R03 | 同样本逐组加入估值、财报、信用 | 更复杂的信息组合经常更差 |
| R04 | 用固定历史邻居和收缩代替树模型 | 风险/市值匹配有小幅改善，其他增量不稳定 |
| R05 | 先记录规则，再检验2024以后阶段；输出完整近似分布 | 市场阶段切换导致上涨尾部低估 |
| R06 | 同候选池等权、逆波动率、分布权重和动态总仓位 | 未显示概率配仓增值 |
| R07 | 相同总仓位全池对照、创业板独立训练、缺失结果压力情景 | 主要结论未被推翻 |
| R08 | 直接预测相对沪深300超额收益分布 | 未发现被大盘波动掩盖的稳定超额优势 |
| R09 | 分红送转再投资收益重建与复权口径检查 | 大多数口径差异较小，但部分公司行动记录无法解释复权变化 |

R01—R04是探索；R05是按事先记录规则执行的历史预留检验；R07—R09为看到结果后追加的诊断，不重新称为独立验证。既有项目曾研究历史行情，因此任何一轮都不能替代今后真正的前瞻检验。

## 数据与评价范围

- 现有主板400/创业板100历史成员池，共1,647只曾入池股票；112个月、56,000条月度记录。不是全A股覆盖。
- 行情2017-01-03—2026-05-29。估值1,646只可用，财报1,647只取得；中债国债与AAA中短票曲线覆盖2017—2026年。没有采用聊天中的密钥或收费账户。
- 以126/252交易日近似6/12个月，月末预测，下一交易日开盘作为收益起点。不是严格自然月标签。
- R05可评价的6个月预测起始日为2024-01-31—2025-10-31，22个月、10,553条有效结果；12个月为2024-01-31—2025-04-30，16个月、7,699条。成熟但端点缺失分别18/12条，另做压力情景，不补零进主表。
- 每次训练仅使用当时已经成熟的标签。财报只在公告与更新较晚日期之后使用；利率使用前一可用观测日。模型预测人群不依赖未来结果是否完整。
- 指标先逐月平均，再跨月平均。16个重叠的12个月起点远不是16个独立年度，更不能把数千只股票当成数千次独立市场试验。

## 绝对收益概率预测

CRPS和Brier越低越好。Q05跌破率理想约5%，90%区间覆盖理想约90%；这些条件满足也不单独证明有预测优势。

{table(['方法','6个月CRPS','12个月CRPS','12个月Brier','12个月Q05跌破','12个月90%覆盖'],absolute)}

在12个月评价样本中，总体历史分布预测的平均上涨概率约43.3%，实际上涨约64.4%（样本层比例）。探索段则出现明显的下跌风险低估。误差方向随市场阶段变化，表明模型校准不能直接外推。

分布用200个等概率原子表示，CRPS对该离散近似精确。经验分布与邻居分布由历史样本构造；树模型用23个分位点插值，两端按边界值延伸。均值、ES和情景概率都依赖这种表示，尤其不能把其尾部估计视为可靠的极端风险上界。

![概率漂移](outputs/report/probability_drift.png)

## 动态仓位是否创造价值

下面是2024-02-01—2026-05-29的累计结果，单边交易成本/滑点假设10bp，现金收益假定0。以12个月估值邻居预测选择相同20只候选；单股目标上限10%，无杠杆。动态总仓位来自预先固定的概率映射，没有用本段收益调参。

{table(['方法','累计收益','最大回撤','平均股票仓位'],allocation)}

动态组合的低回撤主要伴随较低仓位。保持相同的每月目标总仓位，分散到全池反而收益更高、回撤更低，削弱了选股和概率配仓增值的解释。30bp成本压力情景与风险/市值模型对照也已保留，不能只看最有利的一格结果。

模拟包含现金守恒、卖出后买入、缺报价不能成交、保守开盘跳空限制及过去成交量参与上限。没有使用当日最高/最低价或当日收盘后成交量决定开盘成交。终点无滞后报价持仓，但这仍是调整价格单位的研究模拟：没有声称精确处理交易所涨跌停、券商整手规则、税费或全部公司行动。满仓权重对照在截断后剩余权重全零时，对剩余候选等分，以保持同总仓位比较。

未把个股边际分布相乘作为组合联合分布；没有使用未经验证的凯利或Black-Litterman优化给出资金金额。

![仓位对照](outputs/report/allocation_comparison.png)

## 能否预测跑赢大盘

R08直接预测个股收益减同期沪深300价格收益，其正值概率表示跑赢基准，区别于上涨概率。未来指数收益只用作已经成熟的标签。

{table(['方法','12个月探索段CRPS','12个月后段CRPS','12个月后段Brier'],exrows)}

相对收益建模没有揭示出稳定的信息增量。后段已被前轮查看，R08只作为机制诊断，不能充当又一次全新测试。

## 收益口径与数据缺口

R09取得32,680条公开分红送转记录和70条配股记录，以除息日收盘价再投资税前现金、计入送转股份，独立重建可处理窗口。配股、公司行动日无价格、金额未知和无法解释的复权跳变明确排除。

{table(['交易日期限','可对照窗口','差异绝对值中位数','差异绝对值95分位','最大差异','上涨方向不同占比'],defrows)}

检查发现{len(factor)}个无法由公开普通分红送转表解释的复权变化，可能涉及特殊转增/重整或来源差错，具体原因待核实。这些窗口不能标为可靠重建的总收益。保留相同可处理样本、替换评价收益后，主要预测结论没有实质变化；这是一项口径敏感性检验，不是完整公司行动数据库或重新训练的严格总收益模型。

仍然限制强命题的数据问题：

1. 沪市原股票池使用全生命周期ST排除，带有选择偏差风险；R07用独立创业板训练/评价作对照，结果未显示估值稳定超过总体历史基线，但不能因此宣称全部股票池已无偏。
2. 122,461条财报中85,473条更新日晚于公告日。保守可用规则使2017—2024年财报期末距预测日中位数约15个月，检验对象不是当时最新、原始版本完整的财报。
3. 缺可靠历史行业和一致预期快照；历史估值原始版本也没有逐项证明不可修订。因此没有证明严格控制行业后的独立估值/信用效应。
4. 完整含分红总收益、退市结算、配股融资与特殊重整未全部解决。主实验仍以复权收益代理为主，R09量化了可检查部分，不把缺口包装成已解决。
5. 缺少足够长且多市场阶段的独立测试历史；不声称复现了附件设想的2012年起步研究。

## 本轮交付与后续边界

已交付原讨论、完整路线、实际数据缺口表、九轮实验、分布预测、情景概率、评分/校准、仓位对照、图表和复跑代码。数据真实性与统计有效性的局限保留在结论中；程序测试通过不等于投资假设通过。

本轮结果不支持继续在同一历史段上搜索更复杂仓位参数。值得继续的新工作应由新增证据驱动：更长的历史、原始披露版本、完整公司行动与行业数据，或固定模型后的真正前瞻记录。联合尾部建模和更复杂优化应建立在可重复的预测增量之上。

完整数字见各轮 `outputs/`，方法与失败路径见[实验日志](notes/round_log.md)，数据获取和缓存边界见[README](README.md)及[数据缺口](notes/data_gaps.md)。
'''
    (ep/'EP24_research_report.md').write_text(text)
    # Historical illustration only; never presented as a current investment signal.
    pred=pd.read_parquet(OUT/'r05_holdout/predictions.parquet')
    last=pred.date.max()
    row=pred[(pred.date==last)&(pred.model=='peers_valuation')&(pred.horizon==252)].sort_values('instrument').iloc[0]
    quarter=last.to_period('Q')
    keys=pd.read_parquet(OUT/f'local_cache/r05_distributions/252_{quarter}_keys.parquet')
    index=np.flatnonzero((keys.date==last)&(keys.instrument==row.instrument))[0]
    atoms=np.load(OUT/f'local_cache/r05_distributions/252_{quarter}_peers_valuation.npz')['atoms'][index]
    ex=pd.read_parquet(OUT/'r08_excess_probe/predictions.parquet')
    relative=ex[(ex.date==last)&(ex.instrument==row.instrument)&(ex.horizon==252)&(ex.model=='peers_valuation')].iloc[0]
    card={'decision_date':str(last.date()),'instrument':row.instrument,'horizon_sessions':252,
          'model':'peers_valuation','expected_return_model_estimate':row['mean'],'probability_up':row.p_up,
          'probability_outperform_csi300_separate_model':relative.p_up,
          'probability_gain_at_least_20pct':float((atoms>=.20).mean()),
          'probability_loss_at_least_20pct':float((atoms<=-.20).mean()),
          'q05':row.q05,'q50':row.q50,'q95':row.q95,'es05_model_estimate':row.es05,
          'reliability':'cross-regime calibration not established; no investment position recommendation',
          'scope':'historical demonstration, not current quote or forecast; outcome quantiles are not parameter confidence intervals'}
    (OUT/'report/historical_prediction_example.json').write_text(json.dumps(card,indent=2,ensure_ascii=False)+'\n')
    print('Built EP24_research_report.md and historical_prediction_example.json')


if __name__=='__main__':
    run()
