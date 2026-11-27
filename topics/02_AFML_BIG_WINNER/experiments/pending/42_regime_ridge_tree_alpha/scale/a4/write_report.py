"""Render a standalone A4 evidence report from the persisted books and position diagnostics."""
from report_data import *
def tab(head,rows):
    def render(k):
        if isinstance(k,(float,np.floating)):return '缺估值' if not np.isfinite(k) else f'{k:.2f}'
        return str(k)
    return '\n'.join(['| '+' | '.join(head)+' |','|'+'---|'*len(head)]+['| '+' | '.join(map(render,row))+' |' for row in rows])
def main():
    benchmark=pd.read_csv(OUT/'benchmarks.csv'); pa=pd.read_csv(OUT/'parity.csv')
    dd=pd.read_parquet(OUT/'daily.parquet'); cf=pd.read_csv(OUT/'contrasts.csv'); ref=pd.read_csv(OUT/'session_parity.csv')
    fac=pd.read_parquet(OUT/'factors.parquet'); ss=pd.read_parquet(OUT/'sessions.parquet')
    cols='size beta idio_vol earnings_yield industry unexplained_on_support unsupported'.split()
    names={'short':'短期收益与反转','medium':'中期动量与位置','volatility':'波动与振幅','trading':'成交量与换手','candle':'K线与量价关系','market':'市场共同项','other':'其余'}
    ex=fac.groupby(['pool','segment','arm'])[cols].sum()*100
    proj=ex.xs('T',level=2)-ex.xs('R',level=2)
    z=fac['Z1']
    fac['state']=np.select([z<1/3,z>2/3,z.notna()],['低','高','中'],default='未知')
    fac['year']=fac.date.dt.year
    fac.groupby(['pool','segment','arm','year','state','session'])[['held_amount','covered_amount','actual_gross']+cols].sum().to_csv(OUT/'risk_year_state.csv')
    signal=pd.read_parquet(OUT/'sessions_signal_cohort.parquet')
    z=signal.Z1;signal['state']=np.select([z<1/3,z>2/3,z.notna()],['低','高','中'],default='未知');signal['year']=signal.signal_date.dt.year
    signal.groupby(['pool','segment','arm','year','state'])[['overnight','intraday','fee']].sum().to_csv(OUT/'session_signal_year_state.csv')
    c=ss.groupby(['pool','segment','arm'])[['overnight','intraday','fee']].sum()*100
    order=[];benchrows=[]
    for (pool,n,win),g in benchmark[benchmark.arm.isin(['R','T'])&benchmark.year.eq('all')].groupby(['pool','segment','window']):
        if win=='shared_equal' and (pool==300 or n==3):continue
        a=g.set_index('arm')
        dates=a.loc['R']
        benchrows.append([pool,n,dates.start,dates.end,'等权共窗' if win=='shared_equal' else '整段',a.loc['R','net']*100,a.loc['T','net']*100,dates.equal_net*100,dates.index_total_return*100])
    famrows=[]
    for pool,group in cf[(cf.segment=='all') & cf.fee_multiple.eq(1)].groupby('pool'):
        for key in FAMILIES:
            r=group[(group.arm=='R') & group.base.eq('R_mask_'+key)].iloc[0]
            t=group[(group.arm=='T') & group.base.eq('T_mask_'+key)].iloc[0]
            famrows.append((pool,names[key],r.net_bp,f'[{r.lo:.1f}, {r.hi:.1f}]',t.net_bp,f'[{t.lo:.1f}, {t.hi:.1f}]'))
    actual=[]
    for (p,n,a),g in c.iterrows():actual.append((p,n,a,*g.values,g.overnight+g.intraday-g.fee))
    flow=fac.groupby(['pool','arm'])[['held_amount','covered_amount']].sum()
    quality=pd.read_csv(OUT/'quality.csv')
    agree=pd.read_csv(OUT/'session_parity.csv');dsg=pd.read_csv(OUT/'risk_design.csv')
    streak=pd.read_parquet(OUT/'stock_month.parquet')
    for key in ['overnight','intraday']:
        grouped=streak.groupby(['pool','segment','arm'])[key]
        streak[key+'_abs_share']=abs(streak[key])/grouped.transform(lambda x:abs(x).sum())
    top=[]
    for key in ['overnight','intraday']:
        for (p,n,a),g in streak.groupby(['pool','segment','arm']):
            part=g.nlargest(3,key+'_abs_share')
            top.append((p,n,a,key,part[key+'_abs_share'].sum(),'/'.join(part.symbol+'@'+part.month)))
    conc=pd.DataFrame(top,columns='pool segment arm session share_of_absolute_contribution stocks_months'.split());conc.to_csv(OUT/'concentration.csv',index=False)
    agg=pa.groupby('pool').rows.sum()
    import hashlib
    rc={'stage':'historical_replay','rows_by_pool':{str(k):int(v) for k,v in agg.items()},'max_ridge_error':pa.ridge_max_error.max(),'max_tree_error':pa.tree_max_error.max(),'max_family_sum_error':pa.family_sum_max_error.max(),'max_daily_pnl_error':ref.max_gross_error.max(),'max_daily_equity_error':ref.max_net_error.max(),'days_reconciled':int(ref.days.sum()),'stock_sleeve_rows_audited':int(ref.stock_sleeve_rows.sum()),'rank_identified_designs':int(dsg.identified.sum()),'designs':len(dsg),'input_source':'EP41 CSI300 scores, CSI800 frozen refit scores and models, EP32 PE receipt; historical proxy','files_sha256':{}}
    for f in sorted([*(f for f in OUT.rglob('*') if f.is_file() and f.name!='verification.json'),*Path(__file__).parent.glob('*.py')]):
        rc['files_sha256'][str(f.relative_to(OUT.parent))]=hashlib.sha256(f.read_bytes()).hexdigest()
    (OUT/'verification.json').write_text(json.dumps(rc,indent=2,ensure_ascii=False)+'\n')
    body=f'''# A4｜个股特征、日内隔夜和风险暴露

两池五个独立账户段里，Ridge 的日内毛贡献全部高于原值树。沪深300两段树的隔夜损失较轻，但这项优势不足以抵消日内差距。中证800中段两者隔夜均获利，树仍有隔夜优势。全体历史账户可以逐日加回。这给出了利润发生的时段，选股前可预测性仍须后续实盘前封存检验。

## 账户和基准

沪深300用冻结的78列 Ridge（R）与69列原值树（T）。中证800用在800池历史样本训练、冻结的对应模型，每日选与300相同的头部席位，逐段独立起账。每段本金1，十份H10滚动，买10 bp、卖20 bp，同股票跨份额净额计费。指数取始末收盘全收益端点；同池等权按同交易约束记账。表中各收益单位为百分比。

{tab(['池','段','开始','结束','窗口','R净','T净','等权净','指数全收益'],benchrows)}

800等权的两个提前停估日期分别为2022-06-29、2024-07-30。两模型和指数同时缩短至该端点后列出等权比较。各年、各段、每个遮盖臂相对于等权和指数的超额、最大回撤见[基准表](results/benchmarks.csv)，双费各臂净差及删除最佳三月见[费用与区间](results/contrasts.csv)。

## 哪些输入影响给分和盈利

逐列清单共78项，包括16项短期、38项中期、6项波动振幅、9项成交量与换手，以及9项市场共同列。K线与量价关系独立族在这两个冻结模型中有0项，其他未归类项有0项。R额外保留截距，T不含9项市场列。实值或缺失先按各自季度存档的中位数、标准差和均值处理。R的分类分数加截距在300池{int(agg.loc[300]):,}行、800池{int(agg.loc[800]):,}行逐行重建，其最大误差为{pa.family_sum_max_error.max():.2g}。原树叶预测最大误差为{pa.tree_max_error.max():.2g}。覆盖、列映射和实际分裂次数见[映射表](results/feature_map.csv)、[各折模型与分裂](results/family_splits.csv)、[逐股核平](results/parity.csv)。

逐族替换为当季训练中位数后保持所有其余输入、树与系数冻结，重排全池和重跑账户。下表为**原臂减遮盖臂**的共同完整月平均费后差，单位 bp/月。区间按各段三个月连续时间块、10,000次重抽后按月数汇总。这些相关输入的边际效应不能相加。EP36曾固定2021Q4的78列Ridge，在约192股的缩减池保留13项风格能解释的部分，再删除或加回位置／风险残差；约39只等权，月初执行。本轮每季采用当季冻结模型，在全合格池每日重排并按H10账本执行，遮盖的是该族所有输入。

{tab(['池','被遮盖族','R差','R 95%区间','T差','T 95%区间'],famrows)}

同日共同市场列只有常数项作用，树未使用这些列；无实际输入的两族本次遮盖不会换股。各日原始名单、改选席及独立资金账可查[名单](results/targets.parquet)、[席位变化](results/changed_seats.parquet)、[月度](results/monthly.csv)、[年度](results/annual.csv)。

## 利润在什么时候发生

隔夜以上收盘持股数量乘以到本日开盘的价格变化，日内以开盘成交后的数量乘以开盘到收盘的变化。策略到期的末日使用开盘结算；800第一段市场缺估终点为独立中止日。停牌、现金、转换关系和对应成交限制继承EP41正式账，价格使用其已有的复权与已确认停牌估值，现金不计息；实际手续费独立列出。表为各段单位初始本金的贡献百分比，可横向加回。各日成本和净值加回最大误差为{ref.max_net_error.max():.2g}。

{tab(['池','段','臂','隔夜','日内','实付费','净收益'],actual)}

实际{int(agree.stock_sleeve_rows.sum()):,}条股票×份额×日轨迹进入核账，包括零成交目标和遗留持仓。开盘前持股原开盘字段缺值合计{quality.loc[quality.condition.eq('opening_position_missing_provider_open'),'stock_sleeve_rows'].sum():,}条（两池两臂重复保留），详细到涉及股票数、停牌估值和公司行动前身、部分日见[覆盖核查](results/quality.csv)。账龄1–10日与逾期单列，隔夜归原份额、日内归新份额，净买方向的费用归新股龄、净卖归原股龄。[实际账龄贡献](results/age.csv) · [账龄费用](results/fee_age.csv) · [逐日收支](results/sessions.parquet) · [信号年及入场前状态](results/session_signal_year_state.csv)

各段各模型中，对绝对日内或隔夜贡献最大的三个股月合计占绝对股月贡献的{100*conc.share_of_absolute_contribution.min():.2f}%至{100*conc.share_of_absolute_contribution.max():.2f}%。[股月排名](results/concentration.csv) · [完整股月](results/stock_month.parquet)

## 已观测风格能解释多少

按当日之前的历史申万一级行业、自由流通股市值代理、与沪深300市场同期有效窗口120日（至少60对）的Beta及残差波动率、当时历史记录的盈利收益率分解。盈利收益率从本地EP32审计过哈希的个股PE面板取倒数，行情聚合、行业及估值来源均保留历史代理边界，无法认证首次发布时间。每个交易日和时段在当时合格股票上使用四项截面标准化风格与全套行业哑变量回归，检查满秩；没有足够截面、缺风格或行业不支持的持仓单列损益。{int(dsg.identified.sum()):,}/{len(dsg):,}个截面可估。可支持持仓市值比例分别为300 R {100*flow.loc[('300','R'),'covered_amount']/flow.loc[('300','R'),'held_amount']:.2f}%、T {100*flow.loc[('300','T'),'covered_amount']/flow.loc[('300','T'),'held_amount']:.2f}%，800 R {100*flow.loc[('800','R'),'covered_amount']/flow.loc[('800','R'),'held_amount']:.2f}%、T {100*flow.loc[('800','T'),'covered_amount']/flow.loc[('800','T'),'held_amount']:.2f}%。

下表为树减Ridge的毛贡献之差，占初始本金的百分点。未解释项包括在列示变量下无法由截面回归解释的部分，各段方向并不一致。

{tab(['池','段','市值','Beta','残差波动','盈利收益率','行业','支持内未解释','无支持'],[(p,n,*v.values) for (p,n),v in proj.iterrows()])}

各年、各段、前一日Z1状态及成交时段的分解、可估截面、实际持仓加权行业和风格暴露分别列在[年和状态](results/risk_year_state.csv)、[每日设计与支持](results/risk_design.csv)、[行业](results/sector_exposure.parquet)、[风格](results/style_exposure.parquet)。入场信号状态另按实际持仓批次回连，见[原始信号批次](results/sessions_signal_cohort.parquet)。这些均为历史条件归因，不能将回归剩余直接解释为独立Alpha。

## 复现

依次运行 `scores.py`、`accounts_a4.py`、`sessions.py`、`report_data.py`、`write_report.py`。800日频特征取本轮 events 子目录按季度生成的面板；300真实交易轨迹对齐 state 主账。[复核摘要与哈希](results/verification.json)
'''
    (OUT.parent/'REPORT.md').write_text(body)
if __name__=='__main__':main()
