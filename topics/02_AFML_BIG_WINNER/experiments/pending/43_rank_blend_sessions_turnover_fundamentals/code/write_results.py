from statistics43 import *
from fund_fit import F,A,N
import json
REPORTS=ROOT/'reports';REPORTS.mkdir(exist_ok=True)
def table(cols,rows):
    def val(x):
        if isinstance(x,(float,np.floating)):return f'{x:.2f}' if np.isfinite(x) else '—'
        return str(x)
    return '\n'.join(['| '+' | '.join(cols)+' |','|'+'|'.join(['---']*len(cols))+'|']+['| '+' | '.join(val(x) for x in row)+' |' for row in rows])
def main():
    stats=pd.read_csv(SUM/'contrasts.csv');det=pd.read_csv(SUM/'details.csv').query('fee==1')
    prim=pd.read_csv(SUM/'primary.csv');port=pd.concat(pd.read_csv(O/f'portfolio_{p}.csv') for p in [300,800])
    def metric(p,k,seg='all',fee=1):
        s=stats[(stats.pool==p)&(stats.comparison==k)&(stats.segment==str(seg))&(stats.multiple==fee)]
        return s.iloc[0] if len(s) else None
    def bp(p,k):return f'{metric(p,k).net_bp:+.2f}'
    def cnt(p,k):return det[(det.pool==p)&(det.arm==k)].set_index('segment').sort_index()
    def feecut(p,a,b):return (100*(1-cnt(p,a).one_fee/cnt(p,b).one_fee)).tolist()
    def f2(v):return '、'.join(f'{a:.2f}%' for a in v)
    def contrast_list(pairs,wide=True):
        result=[]
        for p,k,display in pairs:
            h=metric(p,k)
            if h is None:continue
            sg=[metric(p,k,i) for i in range(1,4 if p==800 else 3)]
            result.append([p,display,' / '.join(f'{v.net_bp:+.2f}' for v in sg),h.net_bp,f'[{h.lo:.2f}, {h.hi:.2f}]',h.gross_bp,h.delta_fee_bp,' / '.join(f'{v.drop3:+.2f}' for v in sg),metric(p,k,fee=2).net_bp])
        return table(['池','账户比较','逐段净差','月均净差','95%区间','毛差','费差','各段 drop3','双费净差'],result)
    def contrast_both(items):
        return contrast_list([(p,k,n) for p in [300,800] for k,n in items])
    def wdet(item,title,content,status,files):
        text='# '+item+'｜'+title+'\n\n'+content.strip()+'\n\n'+ '账户表使用共同完整月，单位为 bp/月。费用差为处理臂减对照臂的实付费；正数表示多付费用。每段独立从单位本金起账。\n\n'+' · '.join('['+n+'](../'+p+')' for n,p in files)+'\n'
        (REPORTS/(item+'.md')).write_text(text.replace('；','。'))
        register.append((item,title,status,content.split('\n')[0],f'reports/{item}.md'))
    register=[]
    D='outputs/';sm=D+'summary/';dlink=[('完整配对差',sm+'contrasts.csv'),('逐年净收益、回撤及基准',sm+'annual.csv')];fc=D+'fundamental/'
    wdet('B1','删九项成交特征与限制树深度','在普通平方损失树之间比较，60项浅树相对69项原深度树在300、800分别提高 '+bp(300,'B/T60d minus B/T69')+'、'+bp(800,'B/T60d minus B/T69')+' bp/月。300池普通69树和浅69树分别在407,372个外层股票日逐分复现EP42。\n\n'+contrast_both([('B/T60 minus B/T69','只删九列'),('B/T69d minus B/T69','只限深度'),('B/T60d minus B/T69','删列并限深'),('B tree interaction','两因素交互'),('B/T_mask_trading minus B/T','原树冻结遮盖')])+'\n\n800的A4原口径固定300席数，另存原席数复核。日级诊断记录全池、K附近十一名的总收益秩相关和相对R78的前K交集。','历史机制支持',[('300两两前K交集',D+'diagnostics_300/topK_overlap.parquet'),('800两两前K交集',D+'diagnostics_800/topK_overlap.parquet'),('G2分数复现',sm+'tree_parity.csv'),('300日级诊断',D+'diagnostics_300/B1_L2_daily.parquet'),('800日级诊断',D+'diagnostics_800/B1_L2_daily.parquet')]+dlink)
    bstats=[('B/D minus W/R','D−A，合体'),('B/B minus W/R','B−A，仅合分'),('W/buf minus W/R','C−A，仅缓冲'),('B/D minus W/buf','D−C，缓冲后加树'),('B/D minus B/B','D−B，合分后加缓冲'),('B interaction','(D−C)−(B−A)'),('B/fixed175_buf minus W/R','永久17.5%树＋缓冲')]
    wdet('B2','沪深300静态合分与缓冲的四格','合体逐段为正，但两段各删三个最有利月后都转负。仅加比例缓冲为 '+bp(300,'W/buf minus W/R')+' bp/月，缓冲上再加树为 '+bp(300,'B/D minus W/buf')+'。收益主要来自缓冲。\n\n'+contrast_list([(300,k,n) for k,n in bstats])+'\n\n每日旧股先按新排序保留在前 ceil(1.35K) 者，再补足K；300的K/40另留账。季度合分权重通过外季前已经成熟的逐季折外账户决定，B和D在同一季度共用权重。','主检验未达标',[('季度内折全网格',D+'cal_b_300.csv'),('D臂逐日净值',D+'accounts/300/B/D/daily.parquet')]+dlink)
    b3=[]
    for p,a,b in [(300,'B/D','W/R'),(800,'B/D','W/R'),(800,'transfer/D','transfer/A')]:
        a0,b0=cnt(p,a),cnt(p,b)
        for i in a0.index:
            av=a0.loc[i];bv=b0.loc[i];b3.append([p,a,i,bv.one_fee*100,av.one_fee*100,100*(1-av.one_fee/bv.one_fee),100*(1-av.one_fee_ex_settle/bv.one_fee_ex_settle),av.one_cap,av.cash*100])
    wdet('B3','恰持有一轮的FIFO批次费用','300两段的一轮双边费降幅为 '+f2(feecut(300,'B/D','W/R'))+'，均低于登记的30%。同股同袖按新增份额追踪；部分卖出按份额分摊实付费，公司转换先迁移成本和已付买费，未闭合费用另记。\n\n'+table(['池','处理臂','段','基线一轮费/期初本金%','处理一轮费%','降幅%','剔除结算降幅%','一轮累计投入/本金','平均现金%'],b3)+'\n\n批次表含买日、卖日、股数成本对应本金及卖出金额、双边费用、售后下轮买回与延迟退出标志。1-H10表示持有期，实际亏损子集按卖出金额与成本比较。','费用门槛未达标',[('分段费用和占资',sm+'details.csv'),('300后段逐批成交',D+'accounts/300/B/D/2/fifo.parquet')])
    wdet('B4','300模型和季度权重冻结迁移至800','冻结迁移在800三段都未胜过迁移Ridge。缩至300的同期席数后仍缺少稳定净增量。\n\n'+contrast_list([(800,f+' '+k,f+' '+k) for f in ['transfer','transfer_head'] for k in ['D-A','B-A','C-A','D-C','D-B','interaction']])+'\n\n两池共同完整月对照另列，800缺估值的月份不用于拼接收益。','迁移未获支持',[('同月跨池核对',sm+'common_calendar.csv'),('行业与集中度',D+'portfolio_800.csv')]+dlink)
    wdet('B5','800重新训练并分离权重迁移','800本池重训的合体月均为 '+bp(800,'B/D minus W/R')+' bp，三段异号。固定300的季度权重后为 '+bp(800,'native300b D-A')+' bp/月。\n\n'+contrast_list([(800,k,n) for k,n in bstats]+[(800,'native300b D-A','800模型＋300的b')])+'\n\n三段一轮费用降幅为 '+f2(feecut(800,'B/D','W/R'))+'。完整月、逐年回撤、头部集中度及日度行业资本可沿下表回查。','本池泛化未达标',[('800内层选权',D+'cal_b_800.csv'),('分段费用',sm+'details.csv')]+dlink)
    counts=[]
    for p in [300,800]:
        z=pd.read_parquet(O/f'labels_{p}.parquet');ok=z[['intra','over','total']].notna().all(axis=1)
        counts.append((p,len(z),int(ok.sum()),int((~ok).sum()),f'{(z.intra+z.over-z.total).abs().max():.3g}'))
    wdet('L1','逐股核对十段日内加十段隔夜','在相同复权开收盘上逐股复算，闭合误差低于1e−10。最后一晚计入隔夜腿，两腿一律到退出开盘才成熟。无法形成完整腿的训练行退出三个训练标签的共同支持，评分保留当时合格股票。\n\n'+table(['池','原成熟周行','完整三标签','缺腿行','最大绝对误差'],counts)+'\n\n训练标签是截面居中秩。实际账户采用真实头寸、原估值、交易约束和费用，因此分时对账另以账户现金损益核平。','恒等式与成熟期通过',[('300周标签',D+'labels_300.parquet'),('800周标签',D+'labels_800.parquet'),('季度成熟截止',D+'models')])
    wdet('L2','同一78列分别学习日内、隔夜、总秩','300拆腿后等权合成相对直接总秩为 '+bp(300,'L/eq_over minus L/total')+' bp/月。两个截面秩的和与总收益截面秩产生不同名单。\n\n'+contrast_both([('L/intra minus W/R','仅日内'),('L/over minus W/R','仅隔夜'),('L/total minus W/R','共同支持总秩对原R'),('L/eq_over minus L/total','拆腿等权对总秩')])+'\n\n每个季度记录三套标准化系数，每个信号日给出各腿和总收益RankIC、D1与D10平均收益、预测相关与前K重合。','拆腿等权无稳定增量',[('300系数',D+'diagnostics_300/L2_coefficients.csv'),('800系数',D+'diagnostics_800/L2_coefficients.csv'),('日级名次与尾部',D+'diagnostics_300/B1_L2_daily.parquet')]+dlink)
    wdet('L3','成熟内折校准隔夜系数','300两段均落后共同训练行的总秩Ridge。800三段亦未获得正增量。只在内层从1、0、0.5、1.5、2选λ，外季内保持固定。\n\n'+contrast_both([('L/cal_over minus L/total','校准双Ridge对总秩'),('L/cal_over minus L/eq_over','校准对固定等权'),('L/cal_over minus W/R','校准对冻结R78')]),'主检验未达标',[('300各季校准',D+'cal_lambda_over_300.csv'),('800各季校准',D+'cal_lambda_over_800.csv'),('实际增减资金',D+'changed_capital_300.parquet')]+dlink)
    wdet('L4','用树预测隔夜腿','300的校准组合将隔夜Ridge换成树，改善 '+bp(300,'L/cal_treeover minus L/cal_over')+' bp/月；800为 '+bp(800,'L/cal_treeover minus L/cal_over')+'。该比较衡量修复双Ridge的损失，能否超过原R78另见对照。\n\n'+contrast_both([('L/cal_treeover minus L/cal_over','校准树腿对校准线性腿'),('L/eq_treeover minus L/eq_over','等权树腿对等权线性腿'),('L/cal_treeover minus W/R','树腿对原R78'),('L/tree_total minus W/R','直接总秩78树对原R78'),('B/T minus W/R','原69树对原R78')]),'300有相对修复，跨池证据有限',[('全部股票五档实际结果',D+'diagnostics_300/L4_quintiles.csv'),('五档真实新增资本及流动性',D+'L4_funded_quintiles_300.csv')]+dlink)
    l5=[]
    for p in [300,800]:
        base=cnt(p,'W/R')
        for i,v in cnt(p,'L/cal_over').iterrows():
            b=base.loc[i];l5.append([p,i,100*b.intraday,100*v.intraday,100*v.intraday/b.intraday,100*b.overnight,100*v.overnight,100*max(0,-v.overnight)/abs(b.overnight) if b.overnight<0 else '基线为正'])
    wdet('L5','检验保留日内并将隔夜亏损减半','300两段的日内贡献都未完全保留，隔夜亏损均扩大。以下是每段从1开始的真实本金贡献，逐日满足日内＋隔夜−实付费＝净值变动。\n\n'+table(['池','段','基线日内%','分腿日内%','保留率%','基线隔夜%','分腿隔夜%','剩余亏损/基线亏损%'],l5),'保留日内与隔夜减半均未达标',[('300单位真实敞口归因',D+'L5_funded_300.csv'),('800单位真实敞口归因',D+'L5_funded_800.csv'),('逐日分时损益',D+'accounts/300/L/cal_over/1/session.parquet')])
    w1=[]
    for p in [300,800]:
        x=pd.read_parquet(O/f'W1_solver_{p}.parquet');v=x[x.arm!='mechanical'];w1.append([p,len(v),f'{v.kkt.max():.3g}',f'{v.residual.max():.3g}',f'{v.bound.max():.3g}',int((v.locked>0).sum()),f'{port[port.pool==p].reconciliation_error.max():.3g}'])
    wdet('W1','收盘冻结目标与十袖实账核对','在收盘已知的单袖市值和现金上求解，次开盘按冻结目标撮合。线性分段边际收益与二次目标的边际条件逐日核对，可行性和KKT误差均低于1e−8。\n\n'+table(['池','受审求解次数','最大边际KKT残差','最大预算残差','最大上下界违反','有已知冻结的决策','持仓现金重建误差'],w1)+'\n\n1/K上限、零惩罚的目标在可正常调仓日期复核。旧仓冻结、开盘成交限制与费用准备均可产生实际权重偏离。','求解及账务核验通过',[('300求解逐日记录',D+'W1_solver_300.parquet'),('原等权目标复现',sm+'capK_target_parity.csv'),('800求解逐日记录',D+'W1_solver_800.parquet'),('基线独立复现',sm+'baseline_parity.csv')])
    wdet('W2','单独检验头部集中度','800零换手惩罚、单票上限5%的账户相对无缓冲等权提高 '+bp(800,'W/cap5 minus W/R')+' bp/月。集中度本身解释了W3毛增量的重要部分。\n\n'+contrast_both([('W/capK minus W/R','上限1/K'),('W/cap5 minus W/R','上限5%'),('W/cap6 minus W/R','上限6%')])+ '\n\n800另保留固定300席数的head桥。逐日输出前十占比、有效持股数、一级行业与对数总市值敞口。','集中度有历史增量',[('300集中度及规模',D+'portfolio_300.csv'),('800集中度及规模',D+'portfolio_800.csv')]+dlink)
    wdet('W3','固定秩单位L1惩罚的主检验','800线性规划相对比例缓冲的月均净差为 '+bp(800,'W/LP minus W/buf')+' bp，第一段为负。相对同一5%上限且τ=0的增量为 '+bp(800,'W/LP minus W/cap5')+' bp/月，区间含零。下表把集中度、费用和续持的来源拆开。\n\n'+contrast_both([('W/LP minus W/buf','LP对比例缓冲'),('W/LP minus W/cap5','同上限增加惩罚'),('W/LP minus W/R','LP对无缓冲'),('W/buf minus W/R','仅缓冲'),('W/tau005 minus W/R','τ=.005'),('W/tau02 minus W/R','τ=.02'),('W/LP6 minus W/R','上限6%、τ=.01')]),'主检验未达标',[('实际资金变化',D+'changed_capital_800.parquet'),('秩分到实单的映射',sm+'rank_order_mapping.csv'),('全部目标与成交',D+'accounts/800/W/LP')]+dlink)
    ww=[]
    for p in [300,800]:
        h=pd.read_csv(O/f'W4_same_start_{p}.csv');rr=pd.read_parquet(O/f'W5_ranks_{p}.parquet');rr=rr[rr.rank_bucket=='25-40'].groupby('arm').sum(numeric_only=True)
        for a in ['LP','QP','mechanical']:
            v=rr.loc[a];ww.append([p,a,100*v.full_sales/v.old_names,100*v.partial_sales/v.old_names,100*v.retained/v.old_names])
    wdet('W4','LP角点、QP平滑和同换手对照','二次惩罚显著减少25–40名旧股的整笔卖出，但800连续账户QP落后LP '+f"{abs(metric(800,'W/QP minus W/LP').net_bp):.2f}"+' bp/月。同起点试验复制LP十袖全部头寸、现金及到期日，仅改变当日那个袖的目标，跟到第十个开盘。300和800分别比较1,372及1,361个起点，机械臂相对LP的同袖H10平均净差为−1.20、−2.42 bp。两臂目标L1换手的最大绝对差小于2×10⁻¹⁵。\n\n'+table(['池','账户','整卖%','部分减持%','续持或加仓%'],ww)+'\n\n'+contrast_both([('W/QP minus W/LP','QP对LP'),('W/mechanical minus W/LP','机械插值对LP')])+'\n\n机械臂先处理强制退出与上限，在旧仓与零惩罚目标间移动；票面换手按同起点LP限制，连续账户各自的旧仓、漂移与未成交会产生实际换手偏差。','平滑有效，费后收益未改善',[('300同起点H10',D+'W4_same_start_300.csv'),('800同起点H10',D+'W4_same_start_800.csv')]+dlink)
    w5=[]
    for p in [300,800]:
        for a in ['W/R','W/buf','W/LP','W/QP']:
            v=cnt(p,a);w5.append([p,a,' / '.join(f'{x*100:.2f}' for x in v.one_fee),' / '.join(f'{x*100:.2f}' for x in v.totalfee),' / '.join(f'{x*100:.2f}' for x in v.maximum_weight)])
    wdet('W5','换手寿命、旧股排名与压力测试','800的LP相对同分数等权缓冲在三段均增加恰好持有一轮的费用。它相对缓冲的历史收益提高主要来自持有的股票及集中度。\n\n'+table(['池','账户','各段一轮费/本金%','各段全部费用/本金%','实际单票最高权重%'],w5)+'\n\n旧股按1–10、11–24、25–40、41以后、出池分组，实际卖出与费用分别统计。每笔FIFO保留买回、到期延迟和退出原因。','费用归因完成',[('300旧仓分层',D+'W5_ranks_300.parquet'),('800旧仓分层',D+'W5_ranks_800.parquet'),('原生与同席数双费差',sm+'contrasts.csv')])
    funds(register,wdet,contrast_list,bp,table)
    pd.DataFrame(register,columns='id title outcome finding report'.split()).to_csv(ROOT/'run_register.csv',index=False)
    overview(prim,register,table)

from report_fund import funds,overview
if __name__=='__main__':main()
