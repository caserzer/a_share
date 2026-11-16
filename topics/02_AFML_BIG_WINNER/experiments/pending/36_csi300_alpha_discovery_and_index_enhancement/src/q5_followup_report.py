"""Full Chinese report of the three pre-frozen follow-up directions."""
import json,base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from common import EP,sha,save_json
from q5_followup import DEST,CONFIG

REPORT=EP/'reports'/DEST.name
FREQ={'1w':'周度','2w':'双周','1m':'月度'}
def pct(x):return f'{x:.2%}'
def pp(x):return f'{100*x:+.2f}'
def tab(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    m=pd.read_csv(DEST/'metrics.csv');pairs=pd.read_csv(DEST/'paired_comparisons.csv');inv=pd.read_csv(DEST/'account_inventory.csv')
    v=json.loads((DEST/'validation.json').read_text());sel=json.loads((DEST/'selection_validation.json').read_text());assert v['status']==sel['status']=='PASS'
    periods=json.loads((DEST/'comparison_periods.json').read_text());main=m.loc[m.cost.eq('main')]
    control=main.loc[main.scope.eq('control')];phase=main.loc[main.scope.eq('phase')];buf=main.loc[main.scope.eq('buffer')]
    pc=pairs.loc[pairs.scope.eq('family_common')&pairs.cost.eq('main')];cm=pc.loc[pc.family.eq('control')]
    # Three readable charts, with the actual fixed experiment axes.
    fig,ax=plt.subplots(figsize=(9,4.5));x=np.arange(3)
    for i,f in enumerate(['1w','2w','1m']):
        z=cm.loc[cm.frequency.eq(f)].set_index('model').reindex(['E1','E2','E3']);ax.bar(x+(i-1)*.24,100*z.cagr_difference,.24,label=f)
    ax.set_xticks(x,['E1','E2','E3']);ax.axhline(0,color='#555');ax.set_ylabel('Net CAGR minus matched EW (pp/year)');ax.set_title('Q5 versus same-frequency constituent EW | main costs');ax.legend();fig.tight_layout();fig.savefig(REPORT/'control.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5));x=np.arange(4)
    for i,model in enumerate(['EW','E1','E2','E3']):
        z=phase.loc[phase.model.eq(model)].sort_values('phase');ax.bar(x+(i-1.5)*.2,z.cagr*100,.2,label=model)
    ax.set_xticks(x,['First weekly signal','Second','Third','Fourth']);ax.axhline(0,color='#555');ax.set_ylabel('Net CAGR (%)');ax.set_title('Monthly signal phase | identical dates and main costs');ax.legend();fig.tight_layout();fig.savefig(REPORT/'phases.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4.2),sharey=True)
    bp=pc.loc[pc.family.eq('buffer')]
    for ax,model in zip(axes,['E1','E2','E3']):
        for i,b in enumerate([.3,.4]):
            z=bp.loc[bp.model.eq(model)&bp.buffer.eq(b)].set_index('frequency').reindex(['1w','2w','1m']);ax.bar(np.arange(3)+(i-.5)*.3,z.cagr_difference*100,.3,label=f'Keep top {int(b*100)}%')
        ax.set_xticks(range(3),['1w','2w','1m']);ax.axhline(0,color='#555');ax.set_title(model);ax.legend(fontsize=8)
    axes[0].set_ylabel('Net CAGR change vs no buffer (pp/year)');fig.tight_layout();fig.savefig(REPORT/'buffers.png',dpi=160);plt.close(fig)
    ct=tab(['模型','周期','Q5净年化','同周期EW净年化','Q5−EW年化差(pp)','日均差年化95%区间(pp)','Holm p'],[[r.model,FREQ[r.frequency],pct(control.loc[control.account.eq(r.account),'cagr'].iloc[0]),pct(control.loc[control.account.eq(r.baseline),'cagr'].iloc[0]),pp(r.cagr_difference),f'[{pp(r.ci_low)}, {pp(r.ci_high)}]',f'{r.p_holm:.3f}'] for r in cm.itertuples()])
    pt=tab(['模型','月内第1信号','第2信号','第3信号','第4信号','四相位中位数','四相位最低'],[[model]+[pct(x) for x in phase.loc[phase.model.eq(model)].sort_values('phase').cagr]+[pct(phase.loc[phase.model.eq(model),'cagr'].median()),pct(phase.loc[phase.model.eq(model),'cagr'].min())] for model in ['EW','E1','E2','E3']])
    bt=tab(['模型','周期','无缓冲净年化','保留前30%净年化','保留前40%净年化','无缓冲换手','30%换手','40%换手'],[[model,FREQ[f]]+[pct(buf.loc[buf.model.eq(model)&buf.frequency.eq(f)&(buf.buffer.isna() if b is None else buf.buffer.eq(b)),'cagr'].iloc[0]) for b in [None,.3,.4]]+[f'{buf.loc[buf.model.eq(model)&buf.frequency.eq(f)&(buf.buffer.isna() if b is None else buf.buffer.eq(b)),"annual_one_way_turnover"].iloc[0]:.2f}' for b in [None,.3,.4]] for model in ['E1','E2','E3'] for f in ['1w','2w','1m']])
    allpair=tab(['检验族','模型','周期','相位','缓冲','净年化差(pp)','日均差年化95%区间(pp)','原始p','Holm p'],[[r.family,r.model,FREQ[r.frequency],r.phase,'无' if pd.isna(r.buffer) else f'{r.buffer:.0%}',pp(r.cagr_difference),f'[{pp(r.ci_low)}, {pp(r.ci_high)}]',f'{r.p_raw:.3f}',f'{r.p_holm:.3f}'] for r in pc.itertuples()])
    costrows=[]
    for r in main.loc[main.scope.isin(['control','phase','buffer'])].drop_duplicates('account').itertuples():
        z=m.loc[m.scope.eq(r.scope)&m.model.eq(r.model)&m.frequency.eq(r.frequency)&m.phase.eq(r.phase)&(m.buffer.isna() if pd.isna(r.buffer) else m.buffer.eq(r.buffer))].set_index('cost')
        costrows.append([r.model,FREQ[r.frequency],r.phase,'无' if pd.isna(r.buffer) else f'{r.buffer:.0%}']+[pct(z.loc[c,'cagr']) for c in ['zero','main','stress']])
    costs=tab(['模型','周期','相位','缓冲','零成本年化','主成本年化','压力成本年化'],costrows)
    # Retain every available calendar year; blocked years remain unavailable.
    monthly=pd.read_csv(DEST/'monthly_returns.csv');annual=[]
    for (account,year),g in monthly.groupby(['account',monthly.month.str[:4]]):
        a=g.dropna(subset=['net_return']);base=dict(account=account,year=year)
        if a.empty:annual.append({**base,'status':'BLOCKED'});continue
        nr=(1+a.net_return).prod()-1;br=(1+a.benchmark_return).prod()-1
        annual.append({**base,'start':a.start.min(),'end':a.end.max(),'months':len(a),'net_return':nr,'benchmark_return':br,'excess_difference':nr-br,'status':'FULL' if len(a)==12 and a.status.eq('FULL').all() else 'PARTIAL'})
    pd.DataFrame(annual).to_csv(DEST/'annual_returns.csv',index=False)
    native=main.loc[main.scope.eq('native')]
    nt=tab(['模型','周期','相位','缓冲','有效终点','净年化','最大回撤'],[[r.model,FREQ[r.frequency],r.phase,'无' if pd.isna(r.buffer) else f'{r.buffer:.0%}',str(r.end)[:10],pct(r.cagr),pct(r.max_drawdown)] for r in native.itertuples()])
    ex=pd.read_csv(DEST/'monthly_industry_deviations.csv');industry=ex.groupby(['account','industry']).active_weight.mean().reset_index();industry['abs']=industry.active_weight.abs();it=[]
    for model in ['E1','E2','E3']:
        g=industry.loc[industry.account.eq(f'{model}__1m__p1__b0__main')].nlargest(3,'abs')
        for r in g.itertuples():it.append([model,r.industry,pp(r.active_weight)])
    it=tab(['模型（月度第1相位）','申万一级行业代码','月末平均主动权重(pp)'],it)
    linked='../../outputs/sensitivity/'+DEST.name+'/'
    lines=['# Q5 后续验证：等权对照、月度相位与持仓缓冲','',
        '**结论：月初第1个周信号的表现不能推广为普遍的月度优势。等权配置解释了部分相对指数收益，剩余选股增量仍不确定；缓冲稳定降低换手，但未证明稳定提高收益。**','',
        '本轮只验证用户授权的第2、3、4项，不修补数据缺口，不改停牌估值与中止规则，不重新训练。126账户中27个原账户按哈希复用，99个新增。全部使用原 expanding E1/E2/E3 H10 预测。证据为 historical_simulated_oos；FORWARD_PENDING。','',
        f'三个检验族的共同截止日均为 {str(periods["family_ends"]["control"])[:10]}，统一从2021-01-08信号收盘的初始资金1计算，2021-01-11首次开盘建仓，含全部初始费用。共同区间由组内所有成本分支可估值终点机械决定。各账户至2026年的可用结果另列，不混用区间。','',
        '## 1. 同周期成分等权：模型还有多少增量？','',ct,'',
        '月度成分等权 EW 净年化为−3.32%，同期沪深300全收益指数约−6.05%，即 EW 本身有+2.73个百分点/年的差异。月度Q5的 E1/E2/E3 对EW净年化差分别约+8.16、+7.99、+6.05个百分点。这是同费用、同日期账户之间的差，不是纯因果alpha；EW还包含模型未评分成员，差异同时包含评分覆盖及行业风格选择。','',
        '**九个Q5对EW比较的配对95%区间均包含零，Holm调整后均未通过5%水平。** 因此，不能把对指数约9—11个百分点的月度年化差全部归功于模型，也不能把点估计为正升级为稳定模型增量。EW持有全部成员，主要交易来自调样和等权再平衡，年化单边换手仅约0.56—1.02倍；Q5额外承担了排名换仓。','',
        '![同周期对照](control.png)','',
        '## 2. 月度相位：优势高度依赖第1个周信号','',pt,'',
        '四相位共同使用2021-01-08首次建仓，自2021年2月起分别选择每月第1/2/3/4个可用周信号，下一市场开盘执行。该月不足指定序号时跳过，不用事后可知的“最后一周”替换。第4相位因此同时受到部分月份跳过的影响，不能解释为纯粹平移一天的实验；第2、3相位也明显较弱。','',
        '**三个模型在共同区间只有第1相位净年化为正，四相位中位数均为负。** 其他相位换手相近或更低，收益仍明显下降，所以“少付手续费”不足以解释全部月度优势。不能据此证明月初效应的经济机制，也不应继续搜寻更优日历日。','',
        '在较长可用区间，E2四相位都到2026-10-21，净年化依次约5.59%、−3.03%、−5.43%、−1.56%；E3依次约4.70%、−2.04%、−1.49%、1.45%。相位依赖在这些补充区间仍存在。E1各相位终点不同，不直接横向比较其原生年化。','',
        '部分未调整相位差区间低于零，但在本轮相位族的多重检验调整后均未达到5%水平。这里的关键是稳健性未建立，不能反过来把未显著差异解释成四相位等价。','',
        '![月度相位](phases.png)','',
        '## 3. 持仓缓冲：降换手可靠，增收益不稳定','',bt,'',
        '缓冲定义：新入选优先高分股；对原有实际持仓，若仍位于当前可评分成员的前30%或前40%，优先保留。保留数超过原Q5目标数时按分数截断，再从最高分未入选股票填满原Q5数量。目标仍等权，实际成交受原始可交易限制。无分数、调出成分不属于有意保留；不能卖出的遗留仓位照实保留。','',
        '周度保留前30%使 E1/E2/E3 净年化分别提高约2.25、2.19、1.28个百分点，但配对区间均跨零，尚无稳定收益提升证据。前40%更省换手，却未持续更好，表明降低费用可能同时丢掉信号更新收益。','',
        '月度叠加缓冲多数变差：E2由4.67%降至约1.53%—1.55%；E3由2.73%降至−0.83%—−1.87%。E1月度40%缓冲约5.17%虽高于原4.84%，其改善区间跨零，不挑选为赢家。双周E3的30%缓冲出现负向差异，Holm调整后仍低于5%水平；本轮没有缓冲方案获得调整后显著的正向改进。','',
        '![缓冲增量](buffers.png)','',
        '## 4. 行业暴露与解释边界','',it,'',
        '上表为各月最后共同可估值日的行业权重差均值，比较对象为同周期、同相位EW，不是沪深300市值权重。全部42个主成本账户的行业权重及偏离另附明细，行业缺失显式记为UNKNOWN。该历史行业映射不宣称严格PIT认证；行业偏离不等于行业收益归因，也不证明这些偏离造成收益。','',
        'metrics.csv 另列对全收益指数的样本beta与日收益OLS截距年化，仅为描述性统计，不冒充多因子风险调整alpha。冻结输入没有可直接配对的已认证时点市值面板，本轮不补数，也不输出伪精确的规模归因。','',
        '## 5. 完整成本敏感性','',costs,'',
        '费用：零成本0/0bps，主成本买10/卖20bps，压力成本买30/卖80bps。已含原协议的滑点／冲击代理，不重复收费。成本是按实际成交扣除；零成本与主成本的差异可能通过持仓和现金路径复利传导，不能简单称作累计手续费金额。','',
        '## 6. 全部主成本配对结果与不确定性','',allpair,'',
        'control：Q5减同周期EW；phase：同模型第2/3/4相位减第1相位；phase_selection：其他相位Q5减对应相位EW；buffer：同模型同周期缓冲减无缓冲。95%区间对应日均收益差×252，不是CAGR差。65交易日循环时间块、2000次抽样、固定种子20261116；双侧p值采用中心化自助零假设分布，Holm按检验族／比较区间口径／成本分组调整。成本主结论仅使用main，其他成本及更长成对区间为补充。','',
        '## 7. 原生完整可用区间与逐月逐年文件','',nt,'',
        '原生表只保留所有账户能实际估值到的终点。不同终点不能直接排名；主结论只使用共同区间。逐月表覆盖全部126账户×70个月，账户中止后为BLOCKED而非零收益；首月、末月及不足完整年度单列。','',
        f'- [逐月收益]({linked}monthly_returns.csv) · [逐年收益]({linked}annual_returns.csv)',
        f'- [所有指标]({linked}metrics.csv) · [配对差异和补充区间]({linked}paired_comparisons.csv)',
        f'- [账户及中止记录]({linked}account_inventory.csv) · [冻结日历]({linked}schedule.csv)',
        f'- [行业权重]({linked}monthly_industry_weights.csv) · [行业主动偏离]({linked}monthly_industry_deviations.csv)','',
        '## 8. 审计和本轮裁决','',
        f'账本审计 PASS：{len(v["checks"])}项；独立目标持仓复核 PASS：{sel["rebalance_targets_checked"]}次调仓。全部21项测试通过（1条第三方OSQP弃用提醒）。执行引擎与原版的差异仅为A路径选股回调和可选缓冲参数，费用、缺价、成交及现金逻辑未改。原冻结输入与预测哈希一致。','',
        '**第2项：保留模型选股的正向点估计，但稳定的对等权增量未获证明。第3项：月度优势不具备已验证的相位稳健性。第4项：缓冲能降低换手，但未证明稳定增收，不能按本轮最高点估计挑选配置。**','',
        '这轮结果收窄了后续方向：优先理解第1相位与其他相位的差异，以及周度适度缓冲是否能在独立冻结验证中保留优势；不扩大模型、日历或阈值搜索。上述仅为下一步讨论建议，本轮未执行额外候选、未部署或启动前瞻任务。']
    content='\n'.join(lines)+'\n';(REPORT/'REPORT.md').write_text(content)
    html=markdown.markdown(content,extensions=['tables','fenced_code'])
    for name in ['control','phases','buffers']:
        encoded=base64.b64encode((REPORT/(name+'.png')).read_bytes()).decode();html=html.replace('src="'+name+'.png"','src="data:image/png;base64,'+encoded+'"')
    (REPORT/'REPORT.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Q5 后续验证</title><style>body{max-width:1400px;margin:32px auto;padding:0 24px;font:16px/1.7 system-ui;color:#243446}table{display:block;overflow:auto;border-collapse:collapse;font-size:14px;margin:20px 0}th,td{padding:7px 12px;border-bottom:1px solid #dce4eb;white-space:nowrap}th{background:#eaf0f5}tr:nth-child(even){background:#f7f9fb}img{width:100%;height:auto}h2{margin-top:40px}a{color:#17568b}</style><body>'+html+'</body></html>')
    save_json(DEST/'report_manifest.json',dict(report_sha256=sha(REPORT/'REPORT.md'),html_sha256=sha(REPORT/'REPORT.html'),config_sha256=sha(CONFIG),metrics_sha256=sha(DEST/'metrics.csv'),validation_sha256=sha(DEST/'validation.json'),selection_validation_sha256=sha(DEST/'selection_validation.json')))
    print('Report written',REPORT)

if __name__=='__main__':main()
