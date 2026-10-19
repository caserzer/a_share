"""R14 report: explicitly separate refitting from frozen-forecast new-label evaluation."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/ep24-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from run_four_horizons import EP,OUT
A=OUT/'r14_monthly_walk_forward';B=OUT/'r14_newly_matured'


def report():
    summary=pd.read_csv(A/'summary.csv');new=pd.read_csv(B/'summary.csv').query("scope=='stable_source'")
    monthly=pd.read_csv(A/'monthly_scores.csv',parse_dates=['date'])
    fig,axes=plt.subplots(3,2,figsize=(11,10))
    for row,h in enumerate([1,3,6]):
        w=monthly[monthly.months==h].pivot(index='date',columns='model',values='multiclass_brier')
        delta=w.peers_risk_size-w.expanding_empirical
        axes[row,0].plot(delta.index,delta.rolling(6,min_periods=1).mean(),label='6-origin rolling mean')
        axes[row,0].axhline(0,color='gray',linestyle='--');axes[row,0].set_title(f'{h}m: interval Brier difference (lower is better)')
        g=new[new.months==h].set_index('model')
        axes[row,1].bar(['History','Risk/size'],[g.loc['expanding_empirical','below_q05'],g.loc['peers_risk_size','below_q05']])
        axes[row,1].axhline(.05,color='red',linestyle='--',label='Nominal 5%')
        axes[row,1].set_ylim(0,.20);axes[row,1].set_title(f'{h}m: new outcomes below predicted Q05')
        axes[row,1].legend(fontsize=8)
    fig.tight_layout();fig.savefig(A/'walk_forward_evidence.png',dpi=150);plt.close(fig)
    lines=['# 1、3、6个月 Walk-forward 继续验证（R14）','',
        '**结论：按月重训复现了幅度区间预测的改善，但没有建立上涨概率优势；新增到期结果仍显示尾部低估。**','',
        '本轮按确认方案分别完成按月重训与旧预测新增到期标签检验。两部分独立存放，不用新增结果调参，不用策略盈亏验收。','',
        '## A：每个预测日重新训练','',
        '2021-01至2026-04共64个预测月份，每期限29,596个股票月；训练只纳入该预测日之前已经结束的标签。按月更新扩展训练集，另固定36个月窗口作为非平稳对照。模型是风险/规模1000近邻，沿用75%近邻分位数+25%总体分位数，无参数搜索。', '',
        '|期限|历史分布方向Brier|近邻方向Brier|历史分布五档Brier|近邻五档Brier|','|---|---|---|---|---|']
    for h in [1,3,6]:
        g=summary[summary.months==h].set_index('model');b=g.loc['expanding_empirical'];p=g.loc['peers_risk_size']
        lines.append(f'|{h}个月|{b.brier:.5f}|{p.brier:.5f}|{b.multiclass_brier:.5f}|{p.multiclass_brier:.5f}|')
    lines+=['','分数越低越好。五档改善在2021–2023、2024+两阶段均出现；用6/12个月时间块估计不确定性后，1/3/6月五档改善仍有支持。1/3月CRPS改善也有支持，6月整体CRPS改善不够稳定。方向Brier没有稳定优势。', '',
        '36个月滚动训练窗没有胜过扩展训练集，尤其3/6月方向和区间误差更大；不能假定“只看最近数据”能解决状态变化。', '',
        '相对旧季度重训，月度更新总体变化很小：多数差异区间跨零；6个月CRPS有小幅改善，但没有转化为可靠的上涨概率识别。这里是已查看历史的回溯研究，时间块区间也未校正多模型探索。','',
        '## B：冻结原预测，核验新增到期结果','',
        '旧R10预测文件在下载前记录SHA256；原始上涨/下跌/五档概率保持逐值一致。新增公开行情截至2026-10-19，预测起点仍取旧文件已有日期，不伪装成事前长期封存的前瞻实测。', '',
        '|期限|预测月份数|候选股票月|源一致样本|源差异待审样本|','|---|---|---|---|---|']
    coverage=pd.read_csv(B/'outcome_coverage.csv')
    for h in [1,3,6]:
        g=coverage[coverage.months==h]
        lines.append(f'|{h}个月|{g.date.nunique()}|{g.rows.sum()}|{g.loc[g.status=="valid","rows"].sum()}|{g.loc[g.status=="source_unstable","rows"].sum()}|')
    lines+=['','1月对应2026-04预测；3月对应2026-03/04预测；6月对应2025-12至2026-03预测。独立时间窗口只有1/2/4个月，不能因股票数多就宣称统计稳定。','',
        '公开取回544只股票行情和市场交易日，全部成功。对每只股票检查最多60个交叠日的收益差，至少20日且最大差小于0.3个百分点才纳入主分析；其余作为源差异敏感性另报。这不是证明复权口径完全一致，阈值本身也可能影响样本，不能隐藏被排除样本。','',
        '|期限|历史方向Brier|近邻方向Brier|历史五档Brier|近邻五档Brier|近邻Q05实际跌破率|近邻90%区间覆盖|','|---|---|---|---|---|---|---|']
    for h in [1,3,6]:
        g=new[new.months==h].set_index('model');b=g.loc['expanding_empirical'];p=g.loc['peers_risk_size']
        lines.append(f'|{h}个月|{b.brier:.5f}|{p.brier:.5f}|{b.multiclass_brier:.5f}|{p.multiclass_brier:.5f}|{p.below_q05:.1%}|{p.coverage90:.1%}|')
    lines+=['','新标签中，近邻五档分数优于历史基线，方向分数仍较差。预测5%左尾之外，实际约有9.7%/14.5%/12.3%的结果；90%区间仅覆盖约82.9%/75.8%/80.1%。幅度区间相对更好，不等于尾部概率已校准。包括源不稳定样本的敏感性分析仍得到相同定性结论。','',
        '![Walk-forward证据](outputs/r14_monthly_walk_forward/walk_forward_evidence.png)','',
        '## 交付及复跑','',
        '- `outputs/r14_monthly_walk_forward/`：逐股概率、训练审计、月度/年度/阶段分数、6/12月块比较、月度对季度比较、方向与五档可靠性。',
        '- `outputs/r14_newly_matured/`：冻结文件哈希、公开数据回执、源一致性、标签覆盖、固定概率的新结果评分及各档校准。',
        '- `outputs/r14_completion_audit.json`：本次1/3/6月工作验收；不替代概率可信度判断。','',
        '```bash','EP=experiments/pending/24_conditional_return_distribution_exploration',
        'OPENBLAS_NUM_THREADS=1 .venv/bin/python "$EP/src/run_monthly_walk_forward.py"',
        '.venv/bin/python "$EP/src/evaluate_walk_forward.py"',
        '.venv/bin/python "$EP/src/fetch_walk_forward_extension.py"',
        '.venv/bin/python "$EP/src/score_newly_matured.py"',
        '.venv/bin/python "$EP/src/report_walk_forward.py"',
        '.venv/bin/python "$EP/src/audit_walk_forward.py"','```','',
        '数据仍是前复权价格代理；历史池选择偏差、可修订数据和缺少独立全新市场阶段等限制继续成立。本轮支持保留短期幅度信息作为研究线索；下一问题是尾部在新时段失准，而非继续提高重训频率。']
    (EP/'walk_forward_report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':report()
