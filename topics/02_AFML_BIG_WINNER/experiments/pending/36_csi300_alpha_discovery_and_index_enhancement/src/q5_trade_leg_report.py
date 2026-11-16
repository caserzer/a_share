"""Matched-state buy/sell decomposition and fixed-date signal-age report."""
import json,base64
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown
from common import EP,sha,save_json
from evaluate_ranking import block_ci
from q5_trade_leg_investigation import DEST
from q5_signal_age_matched import DEST as AGE

REPORT=EP/'reports'/DEST.name
def pp(x):return f'{100*x:+.3f}'
def pct(x):return f'{x:.1%}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n'

def balanced_tables():
    records=[];age_records=[]
    for directory,windows,field,metrics,dest in [(DEST,['1_sessions','5_sessions','10_sessions','20_sessions','actual_phase2_open'],'window',['sell_increment','buy_increment','full_increment'],records),(AGE,[1,5,10,20],'horizon',['new_minus_old'],age_records)]:
        f=pd.read_csv(directory/'episodes.csv')
        for scope,flag in [('primary','primary_eligible'),('full','full_eligible')]:
            for (model,cost),g in f.loc[f[flag]&f.status.eq('OBSERVED')].groupby(['model','cost']):
                common=set.intersection(*[set(g.loc[g[field].eq(w),'event']) for w in windows])
                for w in windows:
                    h=g.loc[g.event.isin(common)&g[field].eq(w)].sort_values('month')
                    for metric in metrics:
                        x=h[metric];lo,hi=block_ci(x.to_numpy(),L=3);dest.append(dict(scope=scope,model=model,cost=cost,window=w,metric=metric,episodes=len(h),mean=x.mean(),ci_low=lo,ci_high=hi))
    pd.DataFrame(records).to_csv(DEST/'balanced_horizon_summary.csv',index=False);pd.DataFrame(age_records).to_csv(AGE/'balanced_horizon_summary.csv',index=False)
    return pd.DataFrame(records),pd.DataFrame(age_records)

def main():
    REPORT.mkdir(parents=True,exist_ok=True);balanced,age=balanced_tables()
    v=json.loads((DEST/'validation.json').read_text());av=json.loads((AGE/'validation.json').read_text());assert v['status']==av['status']=='PASS'
    s=pd.read_csv(DEST/'summary.csv');types=pd.read_csv(DEST/'trade_type_summary.csv');annual=pd.read_csv(DEST/'annual_episode_summary.csv');past=pd.read_csv(DEST/'past_return_characteristics.csv');states=pd.read_csv(DEST/'starting_states.csv');episodes=pd.read_csv(DEST/'episodes.csv')
    main=s.loc[s.scope.eq('primary')&s.cost.eq('main')&s.window.eq('actual_phase2_open')]
    rows=[]
    for m in ['E1','E2','E3']:
        z=main.loc[main.model.eq(m)].set_index('metric');rows.append([m,int(z.loc['full_increment','episodes']),pp(z.loc['sell_increment','mean']),pp(z.loc['buy_increment','mean']),pp(z.loc['full_increment','mean']),pct(z.loc['buy_increment','mean']/z.loc['full_increment','mean']),f'[{pp(z.loc["full_increment","ci_low"])}, {pp(z.loc["full_increment","ci_high"])}]'])
    early=table(['模型','独立窗口数','卖出贡献(pp)','买入贡献(pp)','完整换仓增量(pp)','买入占净增量','完整增量95%区间(pp)'],rows)
    tr=types.loc[types.scope.eq('primary')&types.window.eq('actual_phase2_open')]
    typetable=table(['模型','新进入股票贡献(pp)','原持仓补仓贡献(pp)','完全退出贡献(pp)','原持仓减仓贡献(pp)'],[[m]+[pp(tr.loc[tr.model.eq(m)&tr.category.eq(c),'mean_increment'].iloc[0]) for c in ['entry','top_up','exit','trim']] for m in ['E1','E2','E3']])
    profile=balanced.loc[balanced.scope.eq('primary')&balanced.cost.eq('main')]
    horizon=table(['模型','交易日窗口','相同窗口数','卖出增量(pp)','买入增量(pp)','完整换仓增量(pp)','完整增量95%区间(pp)'],[[m,h,int(profile.loc[profile.model.eq(m)&profile.window.eq(str(h)+'_sessions'),'episodes'].iloc[0])]+[pp(profile.loc[profile.model.eq(m)&profile.window.eq(str(h)+'_sessions')&profile.metric.eq(metric),'mean'].iloc[0]) for metric in ['sell_increment','buy_increment','full_increment']]+[f'[{pp(profile.loc[profile.model.eq(m)&profile.window.eq(str(h)+"_sessions")&profile.metric.eq("full_increment"),"ci_low"].iloc[0])}, {pp(profile.loc[profile.model.eq(m)&profile.window.eq(str(h)+"_sessions")&profile.metric.eq("full_increment"),"ci_high"].iloc[0])}]'] for m in ['E1','E2','E3'] for h in [1,5,10,20]])
    year=annual.loc[annual.scope.eq('primary')&annual.cost.eq('main')&annual.window.eq('actual_phase2_open')]
    year_table=table(['模型','年份','窗口数','卖出平均贡献(pp)','买入平均贡献(pp)','完整平均增量(pp)'],[[r.model,r.year,r.episodes,pp(r.sell_increment),pp(r.buy_increment),pp(r.full_increment)] for r in year.itertuples()])
    agetable=table(['区间','模型','交易日窗口','匹配窗口数','新名单−旧名单(pp)','描述性95%区间(pp)'],[[r.scope,r.model,r.window,r.episodes,pp(r.mean),f'[{pp(r.ci_low)}, {pp(r.ci_high)}]'] for r in age.loc[age.cost.eq('main')].itertuples()])
    pr=past.loc[past.scope.eq('primary')&past.window.eq('actual_phase2_open')]
    past_table=table(['模型','交易类别','信号前5日涨幅均值','信号前20日涨幅均值','20日已知成交权重占比'],[[r.model,r.category,f'{r.past_5_weighted_mean:.2%}',f'{r.past_20_weighted_mean:.2%}',pct(r.past_20_known_trade_fraction)] for r in pr.itertuples()])
    costtable=table(['区间','模型','成本','窗口数','卖出增量(pp)','买入增量(pp)','完整换仓增量(pp)'],[[scope,m,c,int(s.loc[s.scope.eq(scope)&s.model.eq(m)&s.cost.eq(c)&s.window.eq('actual_phase2_open'),'episodes'].iloc[0])]+[pp(s.loc[s.scope.eq(scope)&s.model.eq(m)&s.cost.eq(c)&s.window.eq('actual_phase2_open')&s.metric.eq(metric),'mean'].iloc[0]) for metric in ['sell_increment','buy_increment','full_increment']] for scope in ['primary','full'] for m in ['E1','E2','E3'] for c in ['zero','main','stress']])
    allintervals=table(['模型','窗口','分解项','窗口数','均值(pp)','95%区间(pp)'],[[r.model,r.window,r.metric,r.episodes,pp(r.mean),f'[{pp(r.ci_low)}, {pp(r.ci_high)}]'] for r in s.loc[s.scope.eq('primary')&s.cost.eq('main')&s.metric.isin(['sell_increment','buy_increment','full_increment'])].itertuples()])
    coverage=[]
    for name,d in [('trade_legs',DEST),('signal_age',AGE)]:
        f=pd.read_csv(d/'episodes.csv')
        for (status,reason),g in f.groupby(['status','reason'],dropna=False):coverage.append([name,status,'—' if pd.isna(reason) else reason,len(g)])
    cover=table(['实验','状态','原因','记录数'],coverage)
    fig,ax=plt.subplots(figsize=(9,4.3));x=np.arange(3)
    sell=np.array([main.loc[main.model.eq(m)&main.metric.eq('sell_increment'),'mean'].iloc[0]*100 for m in ['E1','E2','E3']]);buy=np.array([main.loc[main.model.eq(m)&main.metric.eq('buy_increment'),'mean'].iloc[0]*100 for m in ['E1','E2','E3']])
    ax.bar(x,sell,label='Sell old holdings');ax.bar(x,buy,bottom=sell,label='Buy new target');ax.set_xticks(x,['E1','E2','E3']);ax.set_ylabel('Mean episode increment (percentage points)');ax.set_title('Same starting state: rebalance minus hold until phase2');ax.legend();fig.tight_layout();fig.savefig(REPORT/'early_legs.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.5))
    for m in ['E1','E2','E3']:
        values=[profile.loc[profile.model.eq(m)&profile.window.eq(str(h)+'_sessions')&profile.metric.eq('full_increment'),'mean'].iloc[0]*100 for h in [1,5,10,20]];ax.plot([1,5,10,20],values,marker='o',label=m)
    ax.axhline(0,color='#555');ax.set_xticks([1,5,10,20]);ax.set_xlabel('Trading sessions since phase1 execution');ax.set_ylabel('Mean episode increment (percentage points)');ax.set_title('48 identical monthly starting states per model | main costs');ax.legend();fig.tight_layout();fig.savefig(REPORT/'horizon_profile.png',dpi=160);plt.close(fig)
    root='../../outputs/diagnostics/'+DEST.name+'/'
    lines=['# 月初换仓机制调查：卖出旧仓、买入新仓与信号年龄','',
        '**当前证据更支持：及时换仓的早期收益差，主要与买入新进入名单的股票有关；不是提前卖掉旧仓就能复制。但这种贡献随年份变化，不能升级为独立的“只买不卖”策略。相同执行日、相同起点的新旧名单比较，仍未发现更换成最新名单的稳定优势。**','',
        '本轮是已有相位结果之后的事后机制诊断，两项实验分别冻结规则。全部沿用原预测、原停牌估值代理和缺价规则；不补数据、不重训、不搜索日历或阈值。用原B延迟账户作为各月真实起始状态的来源，所有反事实在同一起始现金、同一持仓和同一执行开盘价上比较。','',
        '## 1. 同起点三分解：早期增量主要来自买入部分','',early,'',
        '主区间事件从2021年2月开始，实际第2相位开盘不晚于2025-03-03，共49个月度起点。表中单位均为“单个独立窗口平均收益差的百分点”，不是年化收益。主成本买10bps、卖20bps。','',
        '- H：不交易，继续持有原仓和现金。\n- S：只执行完整换仓F实际会成交的卖出数量，卖出后持有现金。\n- F：执行原第1相位Q5完整换仓，卖出后按原资金与成交规则买入。\n- 恒等式：完整换仓增量 F−H＝卖出贡献 S−H＋买入贡献 F−S。所有方案不融资，不能卖的保留、不能买的留现金。','',
        '卖出和买入各自的置信区间较宽、均跨零。二者的贡献比例只是样本点估计，不能视为稳定分成。完整换仓与继续持仓的比较保留较接近的市场敞口，而单独卖出会持有较多现金；两项贡献的波动可能互相抵消，因此合计的区间可以比单项更清晰。','',
        '![买卖分解](early_legs.png)','',typetable,'',
        'entry：此前没有持有、这次新买入；top_up：原持仓补仓；exit：完全卖出；trim：原持仓减仓。新增股票在平均早期净增量中贡献约85%—92%，补仓贡献较小。该拆分不代表这些股票一定具有独立于市场、行业或风格的alpha。','',
        '## 2. 收益需要时间兑现，不是次日立刻占优','',horizon,'',
        '为了比较期限，表中强制使用四个期限及实际延迟窗口都完整可估值的同一组48个月度起点，避免20日少一个月份导致样本变化。每个窗口从同一开盘起点独立持有，不做中间再平衡；末端只按开盘价估值，不虚构清仓，也不计不存在的末端清仓费。','',
        '第1日完整换仓的平均增量都略负；到5—10日转正。20日时，E2/E3的买入和卖出两侧都有正向点估计，不能说所有价值都集中在最初一周。E1在10—20日并未继续明显提高。不同期限共用起点且可能重叠，因此不是独立检验，更不能据此挑选最佳卖出日。','',
        '![期限剖面](horizon_profile.png)','',
        '## 3. 年份分解揭示重要反例','',year_table,'',
        '**2023年三个模型都出现“买入贡献为负、卖出贡献为正”。** 全样本“买入贡献占主要部分”的结论并不适用于每一年。2021、2022和2024年的方向与2023年不同，2025仅含两个事件，不能按全年解读。因此，当前数据不支持直接设计一个永久只买新名单、忽略退出管理的规则。','',
        '## 4. 在同一日期更新名单，是否更好？','',agetable,'',
        '这项对照把起点进一步统一：在第2相位执行前复制B账户实际持仓和现金，OLD使用第1相位已冻结名单，NEW使用第2相位最新名单；两者在同一个开盘、同一费用和成交约束下执行，并分别持有1/5/10/20日。两者只在选股名单上不同，历史资金和旧持仓路径相同。表中再次限制为各期限共同完整的事件集合。','',
        '**所有主成本新名单减旧名单的描述性95%区间均跨零，主区间和更长可用区间均如此。** 不能据此证明名单完全等价，但当前没有“更新一周后的分数一定更好”的可靠支持。此前连续账户B−C同样不清晰，这次统一起始持仓后仍保持该判断。','',
        '## 5. 买入与卖出是否只是简单动量／反转？','',past_table,'',
        '历史涨幅只用原信号日已存在的冻结qfq收盘价比值，不使用停牌估值填补作为特征；按实际成交额占起始资金的比例加权。原持仓补仓常发生在此前下跌的股票，减仓常发生在此前上涨的股票，这与等权再平衡的机械性质一致。','',
        '但新进入股票并非统一“买跌”：E1过去20日均值约−2.12%，E2约+0.63%，E3约−0.90%。不能把三模型的现象归结为单一反转或动量机制。这里只是已交易股票的描述统计，没有进行风格中性或因果归因。','',
        '## 6. 全部费用与更长区间','',costtable,'',
        'primary固定末端不晚于2025-03-03；full按各模型原A/B/C共同可用终点（E1至2026-10-16，E2/E3至2026-10-21）保留完整事件。每个事件结束日必须在相应终点内；无法完整观察的窗口显式留空，不按零收益处理。不同模型的full样本不直接排名。','',
        '## 7. 全部主区间分解区间','',allintervals,'',
        '区间使用按月排序的事件收益、3个月循环时间块、2000次重抽样、固定种子20261116。它们是事后诊断区间，没有新的独立确认或多重检验成功裁决；“95%区间不跨零”不等于已确认可交易策略。','',
        '## 8. 覆盖、核验及下一步判断','',cover,'',
        f'买卖分解记录{v["rows"]}个计划事件窗口，{len(v["checks"])}项检查通过；信号年龄对照记录{av["rows"]}个窗口，{len(av["checks"])}项检查通过。卖出和买入的逐证券贡献能精确还原F−H，费用、现金和交易限制均核对；新增两项已知结果单元测试覆盖买卖贡献拆分和无法卖出时不虚构融资。','',
        '**研究方向进一步收窄：关注新进入名单在信号产生后5—20日的相对表现，并保留退出管理；暂不把“更新更频繁”或“只买不卖”当作改进方向。** 接下来若继续，应比较新进入股票与同日、同预算的简单对照，检查是否只是行业／市场反弹，并在独立冻结规则下验证；本轮没有自动追加这些候选。','',
        '这些独立窗口不能拼接为净值，也不能用窗口均值乘以一年交易次数作为预期年化收益。前期完整连续账户的结果仍以原报告为准。','',
        f'- [全部事件窗口]({root}episodes.csv) · [同样本期限表]({root}balanced_horizon_summary.csv)',
        f'- [逐证券买卖贡献]({root}stock_leg_contributions.csv) · [交易类别贡献]({root}trade_type_summary.csv)',
        f'- [逐年分解]({root}annual_episode_summary.csv) · [交易前收益特征]({root}past_return_characteristics.csv)',
        f'- [起始状态]({root}starting_states.csv) · [账本审计]({root}validation.json)',
        f'- [同日期新旧名单全部窗口](../../outputs/diagnostics/{AGE.name}/episodes.csv) · [同样本汇总](../../outputs/diagnostics/{AGE.name}/balanced_horizon_summary.csv) · [审计](../../outputs/diagnostics/{AGE.name}/validation.json)']
    content='\n'.join(lines)+'\n';(REPORT/'REPORT.md').write_text(content);html=markdown.markdown(content,extensions=['tables'])
    for name in ['early_legs','horizon_profile']:
        encoded=base64.b64encode((REPORT/(name+'.png')).read_bytes()).decode();html=html.replace('src="'+name+'.png"','src="data:image/png;base64,'+encoded+'"')
    (REPORT/'REPORT.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>月初换仓机制调查</title><style>body{max-width:1400px;margin:32px auto;padding:0 24px;font:16px/1.7 system-ui;color:#243445}table{display:block;overflow:auto;border-collapse:collapse;font-size:14px;margin:20px 0}th,td{padding:7px 12px;border-bottom:1px solid #dce4eb;white-space:nowrap}th{background:#eaf0f5}tr:nth-child(even){background:#f7f9fb}img{width:100%;height:auto}h2{margin-top:40px}</style><body>'+html+'</body></html>')
    save_json(DEST/'report_manifest.json',dict(report_sha256=sha(REPORT/'REPORT.md'),html_sha256=sha(REPORT/'REPORT.html'),source_sha256=sha(EP/'src/q5_trade_leg_report.py'),trade_leg_validation_sha256=sha(DEST/'validation.json'),signal_age_validation_sha256=sha(AGE/'validation.json')))
    print('Report written',REPORT)

if __name__=='__main__':main()
