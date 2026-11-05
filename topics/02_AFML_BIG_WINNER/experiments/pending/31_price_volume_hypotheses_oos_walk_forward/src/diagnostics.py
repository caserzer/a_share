"""Interpret fixed controls and utility tradeoffs without any new model search."""
import pandas as pd

from common import EP, OUT
from report import table


def main():
    nulls=pd.read_csv(OUT/'metrics/placebo.csv')
    flagged=nulls.loc[nulls.control.isin(['shuffle_gain','permlabel_gain']) & nulls.estimate.gt(0) & nulls.p_one_sided.lt(.05)]
    winner=pd.read_csv(OUT/'metrics/big_winner_incremental.csv')
    w=winner.loc[winner.scheme.eq('expanding')];base=w.loc[w.variant.eq('baseline')].iloc[0]
    tradeoffs=w.loc[w.variant.ne('baseline') & w.failure_10_rate.lt(base.failure_10_rate) & w.winner_recall.lt(1)]
    text='# EP31 诊断案例与负控制调查\n\n'
    if len(tradeoffs):
        text+='以下规则表面上降低早期失败率，但同时误杀原始 Big Winner，不能只凭左尾改善称作筛选成功：\n\n'
        text+=table(tradeoffs,['variant','baseline_candidates','retained','failure_10_rate','winner_recall','winner_false_kill_rate','cash_opportunity_per_original_candidate'])+'\n\n'
        text+=f"原基线早失败率为 {base.failure_10_rate:.6g}；右尾召回基准为 1。两种损失不能互相隐藏。\n\n"
    else:text+='本轮没有出现“早失败率下降且右尾召回同时下降”这一特定案例，已完整检查固定候选，不捏造负面样本。\n\n'
    pooled=pd.read_csv(OUT/'metrics/pooled_oos_metrics.csv')
    for _,r in pooled.loc[pooled.scheme.eq('expanding') & pooled.q_bh.lt(.05)].iterrows():
        candidate=w.loc[w.variant.eq(r.hypothesis)]
        if len(candidate) and candidate.iloc[0].winner_recall<1 and candidate.iloc[0].failure_10_rate>=base.failure_10_rate:
            c=candidate.iloc[0]
            text+=f"**汇总显著却未通过筛选净效用的实际案例：{r.hypothesis}。** 主端点 q={r.q_bh:.6g}；固定过滤后保留 {int(c.retained)}/{int(c.baseline_candidates)} 个候选，原始 {int(c.baseline_winners)} 个赢家只剩 {int(c.retained_winners)} 个；早失败率从 {base.failure_10_rate:.4%} 上升到 {c.failure_10_rate:.4%}。不能从汇总统计改善推出 Big Winner 筛选成功。费用情景下该规则也未改善原槽位净队列均值；这是条件于共同可观测标签的诊断，不是实际策略 P&L。\n\n"
    if len(flagged):
        text+='固定负控制存在名义显著的正向损失改善，按合同标异常；对应主张不升级为可靠独立信息：\n\n'+table(flagged,['hypothesis','scheme','control','estimate','ci_low','ci_high','p_one_sided'])+'\n\n'
        text+='调查边界：训练成熟性与预测无标签入口单独验收；同日板块内置乱保留日期和板块的公共均值，而控制模型没有经过认证的行业/板块暴露模型。因此，保留的公共结构可成为增量的替代渠道；这是从置乱构造作出的解释，尚不能独立判定真实机制或证明数据泄漏。名义 p 未作为新的确认性家族使用，保守主裁决仍为 INCONCLUSIVE。\n\n'
    else:text+='训练标签置乱及同日板块内特征置乱未出现名义显著的正向损失改善；完整数值见 placebo.csv。阴性结果不等于证明一切潜在泄漏不存在。\n\n'
    text+='20 个市场交易日整体滞后属于信息衰减诊断。量价/动量具有持久性时滞后变量仍可有效，所以它不是强制零效应的数学零假说；其数值与真正置乱控制分列。\n\n'
    text+='未来数据改写、未来因子注入、全样本标准化、未成熟标签、跨标的区间重叠、未来上市、ST 回填、未匹配代码链、同收盘信号成交和重复 episode 均由对抗测试或全量时间线验收。正控制在合成已知线性信号上可恢复，随机标签负控制不泛化；该测试不是 A 股市场有效性结果。\n\n'
    text+='H10 的预测概率由线性模型截断到 [0,1]，不是经独立前瞻校准的赔率。H10_calibration.csv 按固定概率区间同时给出预测均值、实际事件率、股票行数和市场日期数；行数不能当独立试验次数。\n\n'
    text+='H12 与 H01/H02 的训练期共线性见 H12_train_collinearity.csv；在同面板加入 H01/H02 控制后的增量见 H12_after_H01_H02.csv。H02 换手重算见 H02_turnover_sensitivity.csv。额外历史均值、HAR 类、纯高换手、纯小实体和纯价格突破基线分别见 constant_baseline.csv、required_baseline_ablations.csv。全部是原合同指定对照，未纳入七项主 FDR 以外的确认性宣称。\n'
    (EP/'reports/diagnostic_cases.md').write_text(text)


if __name__=='__main__':main()
