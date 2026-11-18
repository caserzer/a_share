"""User-requested original E1 Q5 DOWN_DOWN equalweight account; no model search."""
import sys,json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from backtest import Inputs
from suspension_sensitivity import marks
from alpha_economics import run_account
from e1_return_attribution import ORIGINAL,END,benchmark,daily_returns,absolute_components
RUN='e1_down_down_account_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
CHECKS=[]
def check(name,ok):
 assert bool(ok),name
 CHECKS.append(dict(check=name,passed=True))
def freeze():
 assert not (D/'freeze.json').exists()
 D.mkdir(parents=True);L.mkdir(parents=True);R.mkdir(parents=True)
 rec=json.loads(ORIGINAL.with_suffix('.json').read_text());files=[ORIGINAL.with_suffix('.json'),ORIGINAL.with_suffix('.csv'),rec['orders_path'],PRIVATE/'e1_timing_mechanism_20261117/states.parquet']
 files += [PRIVATE/(x+'.parquet') for x in ['qfq_close','qfq_open','open','opening_trade_status_v2','daily_members','industry','limits/daily','suspensions/daily','weights/snapshots']]
 files += [PRIVATE/'net_excess_20261116/H00300.CSI.json',PRIVATE/'net_excess_20261116/H00300.CSI.receipt.json']
 files += [EP/'src'/x for x in ['e1_down_down_account.py','alpha_economics.py','backtest.py','portfolio.py','suspension_sensitivity.py','e1_return_attribution.py','common.py']]
 cfg=dict(created_at=datetime.now(timezone.utc).isoformat(),authorization='User asks original E1 retain only medium-down short-down and equalweight; monthly net return and excess',universe='Only original monthly phase1 E1 Q5 targets, not all down-down CSI300 stocks; original scores and membership unchanged',trend='raw frozen qfq close[t-5]/close[t-60]-1 < 0',short='raw frozen qfq close[t]/close[t-5]-1 < 0',target='1/k across retained names; if k=0 cash target; excluded/unknown/zero not selected; old blocked sells retained',fees_bps=[10,20],calendar='Original exact monthly execution dates, next market open after original signal; freeze state until next original monthly signal',valuation='Original suspend_flat <=20 sessions proxy; no new repair or terminal payment fabrication; stop at first held unknown',periods=dict(primary_end='2025-03-03',supplement_end='original monthly E1 available end, 2026-10-16; if DD blocked, truncate explicitly'),benchmark='H00300 full return close; arithmetic monthly net return minus index monthly return in percentage points; relative ratio separately',monthly='calendar months, continuous account NAV with prior month last NAV base; first month capital1 at 2021-01-08 close, includes first entry fees; final partial month labelled; no forced terminal liquidation',comparison='Original E1 replay via same engine and costs required before DD metrics; full and primary separate',evidence='Post-selection historical scenario requested after seeing state profits; not independent alpha confirmation',no_training=True,no_parameter_search=True)
 save_json(D/'config.json',cfg);files.append(D/'config.json');save_json(D/'freeze.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in files]))
 print('frozen',flush=True)
def verify():
 for x in json.loads((D/'freeze.json').read_text())['files']:assert sha(x['path'])==x['sha256'],x['path']
def prepare():
 verify();assert not (D/'selection.json').exists()
 inp=Inputs();raw=inp.c.copy();rec=json.loads(ORIGINAL.with_suffix('.json').read_text());o=pd.read_parquet(rec['orders_path']);rows=[];audit=[]
 old=pd.read_parquet(PRIVATE/'e1_timing_mechanism_20261117/states.parquet').set_index(['signal_date','instrument'])
 for date,g in o.groupby('date'):
  ei=inp.days.get_loc(date);si=ei-1;signal=inp.days[si];t=raw[si-5]/raw[si-60]-1;s=raw[si]/raw[si-5]-1
  v=g[g.target_weight>0].copy();ids=inp.symbols.get_indexer(v.instrument);finite=np.isfinite(t[ids])&np.isfinite(s[ids]);keep=finite&(t[ids]<0)&(s[ids]<0);k=int(keep.sum())
  for ix,r in enumerate(v.itertuples()):
   selected=bool(keep[ix]);key=(signal,r.instrument)
   if key in old.index:check(str(signal)+r.instrument+'_same_prior_state',selected==(old.loc[key,'state']=='DOWN_DOWN'))
   rows.append(dict(signal_date=signal,execution_date=date,instrument=r.instrument,trend=t[ids[ix]],short=s[ids[ix]],original_weight=r.target_weight,selected=selected,weight=1/k if selected else 0.,state_known=bool(finite[ix])))
  audit.append(dict(signal_date=signal,execution_date=date,original_count=len(v),selected_count=k,original_selected_budget=float(v.loc[keep,'target_weight'].sum()),cash_target=1. if k==0 else 0.,unknown_count=int((~finite).sum())))
 panel=pd.DataFrame(rows);panel.to_parquet(L/'selection.parquet',index=False);panel.to_csv(D/'selection.csv',index=False);pd.DataFrame(audit).to_csv(D/'schedule.csv',index=False)
 save_json(D/'selection.json',dict(created_at=datetime.now(timezone.utc).isoformat(),new_account_returns_seen=False,files=[dict(path=str(x),sha256=sha(x)) for x in [L/'selection.parquet',D/'selection.csv',D/'schedule.csv']],checks=CHECKS));print('selection frozen',len(audit),'dates',flush=True)
def run():
 verify();assert not (D/'evaluation_complete.json').exists()
 for x in json.loads((D/'selection.json').read_text())['files']:assert sha(x['path'])==x['sha256']
 inp=Inputs();marks(inp,0.);s=pd.read_parquet(L/'selection.parquet');dates=sorted(s.signal_date.unique());base=pd.read_csv(ORIGINAL.with_suffix('.csv'),parse_dates=['date']).set_index('date');last=base.index.max();accounts={}
 for name,weight in [('E1','original_weight'),('DD','weight')]:
  mapping={}
  for date,g in s.groupby('signal_date'):
   v=np.zeros(inp.n+1);v[inp.symbols.get_indexer(g.instrument)]=g[weight].to_numpy();v[-1]=max(0.,1-v[:-1].sum());check(name+str(date)+'_target_sum',abs(v.sum()-1)<1e-10);mapping[date]=v
  a,o,fail=run_account(inp,mapping,dates,(.001,.002),end=last);a.to_csv(D/(name+'_daily.csv'),index=False);o.to_parquet(L/(name+'_orders.parquet'),index=False);save_json(D/(name+'_account.json'),dict(failures=fail,nav_sha256=sha(D/(name+'_daily.csv')),orders_path=str(L/(name+'_orders.parquet')),orders_sha256=sha(L/(name+'_orders.parquet'))));a=a.set_index('date');accounts[name]=a
  check(name+'_no_negative_cash',(a.cash_weight>=-1e-10).all());change=o.units_after-o.units_before
  check(name+'_trade_gates',not ((change>1e-10)&~o.can_buy).any() and not ((change< -1e-10)&~o.can_sell).any())
  flow=o.assign(buy_value=change.clip(lower=0)*o.price,sell_value=(-change).clip(lower=0)*o.price).groupby('date')[['buy_value','sell_value']].sum();expected=flow.buy_value*.001+flow.sell_value*.002
  check(name+'_fees',np.allclose(a.fees.reindex(flow.index),expected,atol=1e-10));absolute_components(inp,a,o)
  if name=='E1':check('original_full_NAV_replay',a.index.equals(base.index) and np.allclose(a.nav,base.nav,atol=1e-10))
  print(name,len(a),'failures',fail,flush=True)
 actual_end=min(x.index.max() for x in accounts.values());daily=pd.DataFrame(index=accounts['DD'].index);daily['DD_nav']=accounts['DD'].nav;daily['E1_nav']=base.nav.reindex(daily.index);daily['index_nav']=benchmark(daily.index);daily['DD_return']=daily_returns(daily.DD_nav);daily['E1_return']=daily_returns(daily.E1_nav);daily['index_return']=daily_returns(daily.index_nav);daily['excess']=daily.DD_return-daily.index_return;daily.to_csv(D/'daily_comparison.csv',index_label='date')
 schedule=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date','execution_date']);summary=[];allperiods=[]
 for scope,plannedend in [('primary',END),('supplement',last)]:
  end=min(plannedend,actual_end);x=daily.loc[:end];dd=accounts['DD'].loc[:end]
  for freq in ['Y','M']:
   for period,g in x.groupby(x.index.to_period(freq)):
    rr={n:float(np.prod(1+g[n+'_return'])-1) for n in ['DD','E1','index']};sched=schedule[schedule.execution_date.between(g.index.min(),g.index.max())];native_days=inp.days[(inp.days.to_period(freq)==period)]
    partial=g.index.min()>native_days.min() or g.index.max()<native_days.max()
    allperiods.append(dict(scope=scope,frequency=freq,period=str(period),start=g.index.min(),end=g.index.max(),days=len(g),partial=bool(partial),DD_return=rr['DD'],index_return=rr['index'],excess_pp=(rr['DD']-rr['index'])*100,E1_return=rr['E1'],DD_minus_E1_pp=(rr['DD']-rr['E1'])*100,relative_return=(1+rr['DD'])/(1+rr['index'])-1,selected_count=int(sched.selected_count.iloc[-1]) if len(sched) else np.nan,selection_note='new_signal' if len(sched) else 'carry_previous_holdings',average_actual_holdings=float(dd.loc[g.index,'holdings'].mean()),average_cash_weight=float(dd.loc[g.index,'cash_weight'].mean())))
  for name,col in [('DD','DD_nav'),('E1','E1_nav'),('H00300','index_nav')]:
   v=x[col];draw=v/np.maximum.accumulate(np.r_[1.,v.to_numpy()])[1:]-1
   summary.append(dict(scope=scope,account=name,start=x.index.min(),end=end,planned_end=plannedend,complete=end==plannedend,days=len(x),terminal_per100=float(v.iloc[-1]*100),total_return=float(v.iloc[-1]-1),cagr=float(v.iloc[-1]**(252/len(v))-1),max_drawdown=float(draw.min())))
  m=pd.DataFrame(allperiods);m=m[m.scope.eq(scope)&m.frequency.eq('M')];check(scope+'_monthly_DD_compounds',np.isclose(np.prod(1+m.DD_return),x.DD_nav.iloc[-1]));check(scope+'_monthly_index_compounds',np.isclose(np.prod(1+m.index_return),x.index_nav.iloc[-1]))
 pd.DataFrame(allperiods).to_csv(D/'periods.csv',index=False);pd.DataFrame(summary).to_csv(D/'summary.csv',index=False)
 save_json(D/'validation.json',dict(status='PASS',checks=CHECKS,selection_checks=len(json.loads((D/'selection.json').read_text())['checks']),actual_end=actual_end));save_json(D/'evaluation_complete.json',dict(files=[dict(path=str(x),sha256=sha(x)) for x in list(D.glob('*.csv'))+list(L.glob('*_orders.parquet'))]));print(pd.DataFrame(summary).to_string(index=False),flush=True)
def report():
 verify();p=pd.read_csv(D/'periods.csv');summary=pd.read_csv(D/'summary.csv');schedule=pd.read_csv(D/'schedule.csv');validation=json.loads((D/'validation.json').read_text())
 def pretty(f):
  f=f.copy();f['DD_return']*=100;f['index_return']*=100;f['E1_return']*=100
  f['period']=f.period+np.where(f.partial,'*','');return f[['period','DD_return','index_return','excess_pp','E1_return','DD_minus_E1_pp','selected_count']].rename(columns={'period':'月份/年份','DD_return':'筛选组合净收益%','index_return':'指数收益%','excess_pp':'超额pp','E1_return':'原E1净收益%','DD_minus_E1_pp':'相对原E1差pp','selected_count':'本期目标只数'}).fillna('沿用前期').to_markdown(index=False,floatfmt='.2f')
 ss=summary.copy()
 for c in ['total_return','cagr','max_drawdown']:ss[c]*=100
 body=f'''# E1仅保留中期跌且短期跌股票的等权账户

本次按用户指定规则直接回测原E1 Q5名单的子集，不是从全沪深300另选下跌股票，也不是把上一轮状态损益贡献放大。仅在原每月第一周信号交易时重新等权，每次将全部可配置资金分给符合条件的股票；无符合股票则目标现金。旧仓若不能卖出仍保留，目标等权不保证成交后完全等权。

中期：close[t−5]/close[t−60]−1严格小于0；短期：close[t]/close[t−5]−1严格小于0。二者不重叠。使用原信号日已知原始封存前复权价格，零和缺失不入选，不在月中按新状态换仓。买10/卖20bps，下一交易日开盘执行，原停牌估值代理和涨跌停限制不变。

这是看过四状态历史贡献后指定的探索性策略，不是独立盲测。没有重新训练、挑选最优窗口、日期或成本。

## 区间汇总

主区间截至2025-03-03，与前面实验一致；补充区间尝试延伸至原月度E1可用终点2026-10-16，若新账户持仓未知则明确提前停止。末端为收盘市值，未强制清算；费用包含所有期间实际交易及首次建仓。

{ss[['scope','account','end','complete','days','terminal_per100','total_return','cagr','max_drawdown']].to_markdown(index=False,floatfmt='.3f')}

cagr为交易日252口径年化%，total_return为区间累计%，max_drawdown为%，terminal_per100为初始100元期末金额。原E1在完整可用区间逐日重放一致。

## 完整逐月收益与超额

下面展示补充区间完整逐月记录。超额是筛选组合当月净收益减同期沪深300全收益指数H00300收益，单位百分点；不是风格中性Alpha。自然月收益按上月末净值接续，首期从2021-01-08收盘基准及初始资金起算。*表示不完整自然月。本期目标只数为当月调仓时选入数量；实际持仓可能受不可交易旧仓影响。

{pretty(p[p.scope.eq('supplement')&p.frequency.eq('M')])}

## 统一主区间的末月

主区间仅计至2025-03-03，不能使用上表2025年3月整月收益替代：

{pretty(p[p.scope.eq('primary')&p.frequency.eq('M')].tail(1))}

## 逐年收益

{pretty(p[p.scope.eq('supplement')&p.frequency.eq('Y')])}

年份目标只数列是该年最后一次调仓的只数，不是全年均值；2021首期与2026末期非完整年度。

## 持仓、覆盖和风险解释

70个原月度计划信号中，符合条件目标只数：最少{schedule.selected_count.min()}、平均{schedule.selected_count.mean():.2f}、最多{schedule.selected_count.max()}；零选股月份{int(schedule.selected_count.eq(0).sum())}个。原始筛出预算平均{schedule.original_selected_budget.mean()*100:.2f}%，现在重新归一化配置至100%，集中度与行业/波动暴露随之改变，不能将收益提高解释成免费剔除拖累。

完整当期名单、等权目标、短中期状态数值保存在selection.csv；逐日账户和月度平均实际持仓/现金见daily_comparison.csv及periods.csv。后续已规划但账户因缺价停止的信号不视为实际成交。UNKNOWN不补零，未补合并换股终值。数据仍Historical-proxy，不是严格PIT或真实权益账本。

校验：{len(validation['checks'])}项执行/复放/加总检查及{validation['selection_checks']}条与上轮状态一致性检查通过。月收益连乘精确回到终值；原E1全区间精确重放；成本和交易门槛核对通过。

- [逐月逐年数据](../../outputs/diagnostics/{RUN}/periods.csv)
- [汇总指标](../../outputs/diagnostics/{RUN}/summary.csv)
- [所有原信号及目标只数](../../outputs/diagnostics/{RUN}/schedule.csv)
- [筛选名单与权重](../../outputs/diagnostics/{RUN}/selection.csv)
- [逐日净值](../../outputs/diagnostics/{RUN}/daily_comparison.csv)
- [冻结合同](../../outputs/diagnostics/{RUN}/config.json)
- [验证](../../outputs/diagnostics/{RUN}/validation.json)
'''
 (R/'REPORT.md').write_text(body);save_json(D/'delivery.json',dict(files=[dict(path=str(x),sha256=sha(x)) for x in [R/'REPORT.md']+list(D.glob('*.csv'))]));print('report',R/'REPORT.md')
if __name__=='__main__':globals()[sys.argv[1]]()
