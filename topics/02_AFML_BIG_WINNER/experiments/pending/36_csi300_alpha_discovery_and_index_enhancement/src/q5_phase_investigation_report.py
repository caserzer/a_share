"""Report post-hoc diagnostics and the separately frozen delayed-basket control."""
import json,base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from common import EP,PRIVATE,sha,save_json
from summarize import returns
from q5_followup import DEST as SOURCE
from q5_phase_investigation import DEST
from q5_phase_delay_control import DEST as DELAY

REPORT=EP/'reports'/DEST.name
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n'
def pct(x):return f'{x:.2%}'
def pp(x):return f'{100*x:+.2f}'

def windows():
    sch=pd.read_csv(SOURCE/'schedule.csv',parse_dates=['signal_date','execution_date']);sch=sch.loc[sch.frequency.eq('1m')&sch.phase.isin([1,2])].copy();sch['month']=sch.signal_date.dt.to_period('M');wide=sch.pivot(index='month',columns='phase',values='execution_date').dropna();rows=[]
    for model in ['E1','E2','E3']:
        a=pd.read_csv(SOURCE/'accounts'/f'{model}__1m__p1__b0__main.csv',parse_dates=['date']).set_index('date');b=pd.read_csv(DELAY/'accounts'/f'{model}__main.csv',parse_dates=['date']).set_index('date')
        for scope,end in [('primary',pd.Timestamp('2025-03-03')),('model_common',min(a.index.max(),b.index.max()))]:
            aa=a.loc[:end];bb=b.loc[aa.index];gap=np.log1p(returns(aa.nav))-np.log1p(returns(bb.nav));window=pd.Series(False,index=gap.index)
            for _,r in wide.iterrows():window |= (gap.index>=r[1])&(gap.index<r[2])
            rows.append(dict(model=model,scope=scope,end=end,total_log_gap=gap.sum(),early_window_log_gap=gap.loc[window].sum(),remaining_log_gap=gap.loc[~window].sum(),early_share=gap.loc[window].sum()/gap.sum(),early_days=int(window.sum()),all_days=len(gap)))
    f=pd.DataFrame(rows);f.to_csv(DEST/'delay_window_attribution.csv',index=False);return f

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    v=json.loads((DEST/'validation.json').read_text());dv=json.loads((DELAY/'validation.json').read_text());assert v['status']==dv['status']=='PASS'
    influence=pd.read_csv(DEST/'influence.csv');annual=pd.read_csv(DEST/'annual_gaps.csv');monthly=pd.read_csv(DEST/'monthly_gaps.csv');stocks=pd.read_csv(DEST/'stock_contributions.csv');signals=pd.read_csv(DEST/'signal_quality.csv');cost=pd.read_csv(DEST/'cost_decomposition.csv');duration=pd.read_csv(DEST/'holding_durations.csv');overlap=pd.read_csv(DEST/'score_and_selection_overlap.csv')
    dm=pd.read_csv(DELAY/'metrics.csv');dc=pd.read_csv(DELAY/'contrasts.csv');win=windows()
    primary=dm.loc[dm.scope.eq('primary')&dm.cost.eq('main')];long=dm.loc[dm.scope.eq('model_common')&dm.cost.eq('main')]
    delayed=table(['模型','A 月初名单立即执行','B 同名单延迟一周执行','C 第二信号新名单执行','A−B净年化差(pp)','B−C净年化差(pp)'],[[m]+[pct(primary.loc[primary.model.eq(m)&primary.tag.eq(t),'cagr'].iloc[0]) for t in ['A','B','C']]+[pp(dc.loc[dc.model.eq(m)&dc.scope.eq('primary')&dc.cost.eq('main')&dc.contrast.eq(c),'cagr_difference'].iloc[0]) for c in ['A-B','B-C']] for m in ['E1','E2','E3']])
    longtable=table(['模型','共同终点','A净年化','B净年化','C净年化'],[[m,long.loc[long.model.eq(m),'end'].iloc[0][:10]]+[pct(long.loc[long.model.eq(m)&long.tag.eq(t),'cagr'].iloc[0]) for t in ['A','B','C']] for m in ['E1','E2','E3']])
    contrasts=table(['区间','模型','比较','净年化差(pp)','日均差年化95%区间(pp)'],[[r.scope,r.model,r.contrast,pp(r.cagr_difference),f'[{pp(r.ci_low)}, {pp(r.ci_high)}]'] for r in dc.loc[dc.cost.eq('main')].itertuples()])
    inf=influence.loc[influence.scope.eq('primary')&influence.baseline.eq('mean_other')&~influence.model.eq('EW')]
    concentration=[]
    for model in ['E1','E2','E3']:
        g=inf.loc[inf.model.eq(model)];full=g.loc[g.test.eq('full')].iloc[0];excluded=g.loc[g.test.eq('exclude_largest_3_months_posthoc')].iloc[0];leave=g.loc[g.test.eq('leave_one_year_out')]
        concentration.append([model,pct(full.top3_positive_share),excluded.removed,pct(full.relative_cagr),pct(excluded.relative_cagr),pct(leave.relative_cagr.min()),f'{int(full.positive_months)}/{int(full.months)}'])
    concentration=table(['模型','前三个月占总对数差','事后识别的三个月','原相对年化','剔除三月后相对年化','逐年留一法最低相对年化','领先月份/总月份'],concentration)
    years=annual.loc[annual.scope.eq('primary')&annual.baseline.eq('mean_other')&~annual.model.eq('EW')]
    year_table=table(['模型','年份','第1相位收益','其余相位几何均值收益','对数差×100'],[[r.model,str(r.year)+('（部分）' if r.year in [2021,2025] else ''),pct(r.phase1_return),pct(r.other_return),pp(r.log_gap)] for r in years.itertuples()])
    stockrows=[];tops=[]
    for model in ['E1','E2','E3']:
        g=stocks.loc[stocks.model.eq(model)&stocks.baseline.eq('mean_other')];total=g.log_gap_contribution.sum();top=g.loc[~g.instrument.eq('__FEES__')].nlargest(5,'log_gap_contribution');tops.append([model,pct(top.log_gap_contribution.sum()/total),pp(g.loc[g.instrument.eq('__FEES__'),'log_gap_contribution'].sum())])
        for r in top.itertuples():stockrows.append([model,r.instrument,pp(r.log_gap_contribution),pct(r.log_gap_contribution/total)])
    st=table(['模型','证券代码','对数差贡献×100','占净对数差'],stockrows)
    top_table=table(['模型','前5只股票贡献占比','费用贡献差×100'],tops)
    signal_rows=[]
    for scope in ['primary','full_complete_months']:
        for model in ['E1','E2','E3']:
            for horizon in ['h5','h10','h20']:
                g=signals.loc[signals.scope.eq(scope)&signals.model.eq(model)&signals.horizon.eq(horizon)&signals.metric.eq('rank_ic')].sort_values('phase')
                signal_rows.append([scope,model,horizon,int(g.balanced_months.iloc[0])]+[f'{x:.4f}' for x in g['mean']])
    ranktable=table(['区间','模型','标签期限','四相位共同月份','第1信号RankIC','第2','第3','第4'],signal_rows)
    qrows=[]
    for (model,horizon,metric),g in signals.loc[signals.scope.eq('primary')&signals.metric.isin(['q5','q5_q1'])].groupby(['model','horizon','metric']):
        qrows.append([model,horizon,metric,int(g.balanced_months.iloc[0])]+[pct(x) for x in g.sort_values('phase')['mean']])
    qtable=table(['模型','期限','诊断','共同月份','第1','第2','第3','第4'],qrows)
    ct=table(['模型','比较（第1−其他）','零成本年化差(pp)','主成本年化差(pp)','主成本−零成本差(pp)'],[[r.model,str(r.phase),pp(r.zero_cagr_gap),pp(r.main_cagr_gap),pp(r.main_minus_zero_gap)] for r in cost.loc[cost.scope.eq('primary')&~cost.model.eq('EW')].itertuples()])
    dur=duration.loc[~duration.initial_shared_interval].groupby('phase').holding_sessions.agg(['count','mean','median','min','max'])
    dt=table(['相位','完整持仓区间数','平均交易日','中位数','最短','最长'],[[i,int(r['count']),f'{r["mean"]:.2f}',int(r['median']),int(r['min']),int(r['max'])] for i,r in dur.iterrows()])
    ov=overlap.loc[overlap.month.le('2025-02')].groupby(['model','phase'])[['rank_correlation','q5_retention']].mean().reset_index()
    ot=table(['模型','第1信号对比相位','平均分数秩相关','第1信号Q5保留比例'],[[r.model,r.phase,f'{r.rank_correlation:.3f}',pct(r.q5_retention)] for r in ov.itertuples()])
    wt=table(['模型','首次执行至第二相位前的交易日','总交易日','该窗口占A−B对数差'],[[r.model,r.early_days,r.all_days,pct(r.early_share)] for r in win.loc[win.scope.eq('primary')].itertuples()])
    fig,ax=plt.subplots(figsize=(10,4.5));x=np.arange(3)
    for i,tag in enumerate(['A','B','C']):
        z=primary.loc[primary.tag.eq(tag)].set_index('model').reindex(['E1','E2','E3']);ax.bar(x+(i-1)*.24,z.cagr*100,.24,label={'A':'A: phase1 basket, immediate','B':'B: same basket, delayed','C':'C: phase2 basket, immediate'}[tag])
    ax.axhline(0,color='#555');ax.set_xticks(x,['E1','E2','E3']);ax.set_ylabel('Net CAGR (%)');ax.set_title('Fixed-basket timing control | 2021-01-08 to 2025-03-03');ax.legend(fontsize=9);fig.tight_layout();fig.savefig(REPORT/'delayed_basket.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4.5));x=np.arange(5)
    for i,model in enumerate(['E1','E2','E3']):
        z=years.loc[years.model.eq(model)].sort_values('year');ax.bar(x+(i-1)*.25,z.log_gap*100,.25,label=model)
    ax.set_xticks(x,['2021*','2022','2023','2024','2025*']);ax.set_ylabel('Log-wealth gap x 100');ax.set_title('Phase1 minus mean log wealth of phases2/3/4; * partial years');ax.axhline(0,color='#555');ax.legend();fig.tight_layout();fig.savefig(REPORT/'annual_contributions.png',dpi=160);plt.close(fig)
    root='../../outputs/diagnostics/'+DEST.name+'/'
    lines=['# 月度第1信号优势：收益来源与固定名单延迟对照','',
        '**调查结论：执行时点和持有路径比“月初名单本身长期更优”更能解释当前结果。保留同一月初Q5名单、仅把每月执行推迟约一周，三个模型的共同区间净年化都转为负值；同一较晚执行日用旧名单或新名单，差异区间均跨零。**','',
        '这是看到相位结果后的事后调查，不是独立盲测或经济因果证明。第一阶段冻结五项已有账户诊断；看到名单变化与成本/期限结果后，另行冻结第二阶段9个延迟名单账户。未补数据缺口、未更改停牌估值、未重训、未搜索新的日历日或阈值。两个阶段配置和源哈希分别保留。','',
        '主比较区间：2021-01-08信号收盘至2025-03-03，1001个净值交易日。首次交易2021-01-11，全部首次建仓费用计入。主成本买入10bps、卖出20bps；继续使用已确认停牌估值代理和原缺价中止规则。','',
        '## 1. 最关键的固定名单对照','',delayed,'',
        'A：第1个周信号选股并在下一市场开盘执行。B：冻结A在第1个信号时选出的Q5名单，推迟到第2个信号的下一市场开盘执行。C：第2个信号重新选Q5，在与B相同的日期执行。A/B/C统一首次建仓，此后按各自日历循环。B只检查较晚时点的当期成员资格、不用较晚分数替换名单；本轮较晚时点因非成员剔除的数量为0。','',
        '**主区间A−B净年化差约7.75、7.42、6.01个百分点；B−C仅约−0.55、+2.29、+0.50个百分点。** 同一名单的执行日期改变带来的差异更大。A−B同时改变买入、卖出、持仓期间与等权再平衡，不能说是只延迟一次买入，也不能直接宣称发现某个固定月初效应。','',
        '![固定名单延迟对照](delayed_basket.png)','',
        '较长同模型共同区间也保持这一方向：','',longtable,'',
        '## 2. 差异是否来自交易成本或持有天数？','',ct,'',
        '第1相位相对其他相位的优势在零成本下仍然存在，而且通常略大；成本没有制造这次月初优势。另一个问题“月度相对周度更好”确实有降低换手的作用，两种比较不能混在一起解释。','',dt,'',
        '统计为全可用日历中的完整连续执行区间，排除共同首次建仓区间。第1、2、3相位的典型间隔都约20个交易日；第4相位在月内不足4个信号时跳过，最长40日。因此第4相位不纯粹是时点平移，但第2、3相位的差异不能用该跳过规则解释。','',
        '## 3. 是否只是某一年或几个大涨月？','',concentration,'',
        '基准为第2/3/4相位对数收益的均值，即三条净值的几何平均，仅作诊断，不是另一个已执行组合。“相对年化”是该净值比值的年化，不能当作策略净年化；剔除月份后按保留交易日重算。前三个月是事后按差异贡献识别，不能用来构建交易规则。51个月含首尾部分月，且共同建仓的首月差异为零。','',
        '剔除任意一个年份后，三个模型的第1相位相对优势仍为正，所以不是只由2024年决定；E1和E3在2023年反而落后。最大三个贡献月份解释了约53%、43%、78%的净对数差，E3明显更集中。剔除这三个月后差异仍为正，但E3剩余相对年化仅约1.27%。','',year_table,'',
        '![年度贡献](annual_contributions.png)','',
        '## 4. 是否由少数股票制造？','',top_table,'',st,'',
        '使用实际合成持仓单位、成交现金和每日估值计算证券损益，并单列费用。每天证券损益之和减费用与账户净值变化对账；再乘 log(1+r)/r，使各项累加精确还原全期对数净值。上表是第1相位相对其他三相位平均的净贡献，不是股票自身涨幅，也不是可独立交易的贡献收益率。贡献存在正负抵消，占比可能超过100%；证券代码避免历史更名歧义。','',
        '前5只股票贡献约23%—35%的净差异，不像单一股票决定全部结果；但它们仍可能共同暴露于某类行情，不能据此排除风格贡献。费用项为负，进一步说明成本不是第1相位领先的来源。全部证券×月份贡献均已保存。','',
        '## 5. 月初分数是否在固定预测期限上更好？','',ranktable,'',
        'primary：2021-02至2025-02；full_complete_months：2021-02至2026-09。每个模型、期限、指标只使用四相位都有有效值的共同月份。RankIC和Q5收益的缺失条件不同，所以不同表的有效月份数可以不同，未知标签不填零。H5/H10/H20都复用同一H10模型预测，未另训模型。','',
        '主区间E2的第1信号H10 RankIC高于其他相位；E3却不是第1相位最高。扩展区间的H10第1相位点估计均最高，但没有新的独立验证。RankIC不是Q5净收益，在共同完整标签月份中，Q5固定期限收益也不是所有模型都以第1相位最高。因此不能把账户相位差简单等同于“月初预测精度普遍更高”。','',qtable,'',
        'q5为固定期限标签均值，q5_q1为组间差，均非年化且未扣账户交易成本；没有融券账户，也不将重叠标签拼成净值。标签缺失导致完整月份子样本变化，不能将这些均值直接对比全账户累计收益。描述性配对区间见明细，不作新的显著性确认。','',
        '## 6. 名单更新与月内窗口','',ot,'',
        '相隔一个周信号后，原Q5保留比例约52%、51%、59%，即约48%、49%、41%的名单发生变化。仅比较相位1和相位2账户，会同时混入选股变化与执行路径变化，所以新增固定名单延迟对照是必要的。','',wt,'',
        'A−B的对数差中，约49%—62%来自每月第1次执行至第2次执行之前，覆盖238/1001个交易日；其余差异在之后仍产生。因此不能说所有优势都在第一周兑现。之后两账户虽持有同一月初名单，但买卖价格、权重漂移、再平衡与资金路径不同，收益率仍可能不同。','',
        '## 7. 延迟对照的区间与证据强度','',contrasts,'',
        '65交易日循环时间块、2000次抽样、固定种子20261116。区间对应日均收益差×252，不是CAGR差。三个模型A−B的描述性95%区间均高于零，B−C均跨零；但该对照是看到相位结果之后设计，未做独立样本确认或新的多重检验裁决，不能升级为已证明的可交易规律。','',
        '## 8. 后续方向与完整交付','',
        '**当前优先方向应从“哪一个月度相位最好”转向“信号产生后及时换仓与持仓路径如何影响收益”。** E2的第1相位排序线索相对清晰，E1的简单基准仍应保留，E3需要更重视月份集中度。不能直接将第1相位部署为最终策略，也不应继续枚举更优调仓日。下一步若继续，应另行冻结信号年龄／换仓收益分解或独立前瞻检验，而不是追加模型和阈值。','',
        f'本轮第一阶段通过{len(v["checks"])}项检查，第二阶段9个新增账户通过{len(dv["checks"])}项检查；逐日证券损益、费用、对数净值、固定名单和共同首月均已核对。原始预测与输入保持原哈希。未修复或掩盖原有数据缺口，未部署或自动推送。','',
        f'- [年度差异]({root}annual_gaps.csv) · [月度差异]({root}monthly_gaps.csv) · [集中度与剔除诊断]({root}influence.csv)',
        f'- [证券贡献]({root}stock_contributions.csv) · [证券逐月贡献]({root}stock_month_contributions.csv)',
        f'- [固定期限信号质量]({root}signal_quality.csv) · [描述性配对区间]({root}signal_quality_paired.csv)',
        f'- [名单与分数变化]({root}score_and_selection_overlap.csv) · [持有期限]({root}holding_durations.csv)',
        '- [延迟对照指标](../../outputs/diagnostics/'+DELAY.name+'/metrics.csv) · [延迟对照区间](../../outputs/diagnostics/'+DELAY.name+'/contrasts.csv)',
        f'- [第一阶段审计]({root}validation.json) · [第二阶段审计](../../outputs/diagnostics/{DELAY.name}/validation.json)']
    content='\n'.join(lines)+'\n';(REPORT/'REPORT.md').write_text(content);html=markdown.markdown(content,extensions=['tables'])
    for name in ['delayed_basket','annual_contributions']:
        encoded=base64.b64encode((REPORT/(name+'.png')).read_bytes()).decode();html=html.replace('src="'+name+'.png"','src="data:image/png;base64,'+encoded+'"')
    (REPORT/'REPORT.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>月度相位调查</title><style>body{max-width:1400px;margin:32px auto;padding:0 24px;font:16px/1.7 system-ui;color:#263545}table{display:block;overflow:auto;border-collapse:collapse;font-size:14px;margin:20px 0}th,td{padding:7px 12px;border-bottom:1px solid #dde5ec;white-space:nowrap}th{background:#e9f0f5}tr:nth-child(even){background:#f7f9fb}img{width:100%;height:auto}h2{margin-top:40px}</style><body>'+html+'</body></html>')
    save_json(DEST/'report_manifest.json',dict(report_sha256=sha(REPORT/'REPORT.md'),html_sha256=sha(REPORT/'REPORT.html'),phase1_validation_sha256=sha(DEST/'validation.json'),phase2_validation_sha256=sha(DELAY/'validation.json'),source_sha256=sha(EP/'src/q5_phase_investigation_report.py')))
    print('Report written',REPORT)

if __name__=='__main__':main()
