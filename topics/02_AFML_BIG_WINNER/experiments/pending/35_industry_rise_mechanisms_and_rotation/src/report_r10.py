import pandas as pd
from common import ROOT

def run():
    d=pd.read_csv(ROOT/'outputs/r10/exit_summary_dates.csv')
    d=d.query("cohort=='risk_alert' and horizon==20 and cost==0.002")
    lines=['# R10 提示后持续性与错误退出诊断','',
    '## 想验证什么','',
    '冻结R09启动提示和R02反转模型，不增加模型或调阈值。启动提示追踪次日收盘后的5/20/60日新增收益、相对收益和路径回撤；反转提示检验退出现金或转入市场的代价。协议见 protocols/r10.json。','',
    '## 发现什么','',
    '保留37,157条启动提示及6,052条反转任务行业日期/期限记录。未知终点保留缺失。以下为反转分数前20%样本，20日期限、单边20基点成本、先逐月平均再跨月等权的终值改善（百分点）：','',
    '| 分类 | 层级 | 月数 | 退出现金 | 转入市场 | 错失绝对上涨比例 |','|---|---|---:|---:|---:|---:|']
    for row in d.itertuples():lines.append(f'| {row.era} | {row.level} | {row.months} | {row.cash_improvement*100:.2f} | {row.market_improvement*100:.2f} | {row.wrong_exit_absolute*100:.1f}% |')
    lines+=['','四组历史均值均未显示退出改善。不能用反转分类能力替代退出经济价值。完整0/20/50基点、20/60日以及未提示对照保存在 outputs/r10/exit_summary_dates.csv，逐行平均另存，避免行业数量形成隐性月份权重。','',
    '启动跟踪见 followup_summary.csv、followup_annual.csv、continuation.csv。20日至60日延续同时报告全部成熟样本和20日成功条件样本；后者只有第20日后才可识别，不是原提示日可知的选股条件。','',
    '## 为什么不能下更强结论','',
    '重复提示与重叠期限高度相关；本轮是描述性跟踪，不新增独立显著性结论。持有、现金和市场比较使用合成行业篮子终值，未解决R06成交与缺价问题，不是可执行退出策略。现金不计利息；股票持有最终卖出一次，转市场包含初始卖出及买入、最终卖出。分组背景并非随机对照，不能做因果解释。','',
    '原提示20日结果与R09、反转超额收益与R02逐项相符；验证还检查选样先于结果、未知分母、时间顺序、回撤定义和日期等权。测试覆盖次日收盘错位、路径高点回撤与相对/绝对退出区别。盈利与预期兑现仍缺独立证据，不以价格路径填补。','']
    (ROOT/'reports/R10_持续性与错误退出.md').write_text('\n'.join(lines))
if __name__=='__main__':run()
