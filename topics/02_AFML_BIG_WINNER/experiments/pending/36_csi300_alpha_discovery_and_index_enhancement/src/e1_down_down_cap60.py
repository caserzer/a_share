"""Original E1 DOWN_DOWN subset with max 1/60 post-fee NAV at monthly rebalance."""
import sys,json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from backtest import Inputs
from portfolio import trade
from suspension_sensitivity import marks
from e1_return_attribution import ORIGINAL,END,benchmark,daily_returns,absolute_components
RUN='e1_down_down_cap60_20261117';D=OUT/'diagnostics'/RUN;L=PRIVATE/RUN;R=EP/'reports'/RUN
PREV=OUT/'diagnostics/e1_down_down_account_20261117';PL=PRIVATE/'e1_down_down_account_20261117';CAP=1/60
CHECKS=[]
def check(name,ok):
 assert bool(ok),name
 CHECKS.append(dict(check=name,passed=True))
def cap_trade(old,cash,prices,target,buy,sell):
 """Fee-consistent target: selected names <=1/60 of actual post-fee NAV.
 Nontradable inherited positions cannot be forcibly sold. No intra-month reset.
 """
 nav=cash+old@np.nan_to_num(prices);q=1.
 for iteration in range(40):
  v=target.copy();v[:-1]*=q;v[-1]=1-v[:-1].sum()
  units,after,info=trade(old.copy(),cash,prices,v,buy,sell,.001,.002)
  post=after+units@np.nan_to_num(prices);newq=post/nav
  if abs(newq-q)<1e-13:break
  q=newq
 else:raise AssertionError('post-fee target did not converge')
 weights=units*np.nan_to_num(prices)/post
 assert not np.any((weights>CAP+1e-10)&sell)
 return units,after,info,v,weights

def freeze():
 assert not (D/'freeze.json').exists();D.mkdir(parents=True);L.mkdir(parents=True);R.mkdir(parents=True)
 files=[PL/'selection.parquet',PREV/'selection.json',PREV/'DD_daily.csv',ORIGINAL.with_suffix('.csv'),ORIGINAL.with_suffix('.json')]
 files += [PRIVATE/(s+'.parquet') for s in ['qfq_close','qfq_open','open','opening_trade_status_v2','daily_members','industry','limits/daily','suspensions/daily','weights/snapshots']]
 files += [PRIVATE/'net_excess_20261116/H00300.CSI.json',PRIVATE/'net_excess_20261116/H00300.CSI.receipt.json']
 files += [EP/'src'/s for s in ['e1_down_down_cap60.py','portfolio.py','backtest.py','suspension_sensitivity.py','e1_return_attribution.py']]
 save_json(D/'config.json',dict(created_at=datetime.now(timezone.utc).isoformat(),authorization='User requests same original E1 double-down subset, each stock max 1/60, recalculate monthly returns and excess',selection='Exactly reuse sealed original E1 Q5 double-down list and 70 original monthly dates; medium close[t-5]/close[t-60]-1<0 and short close[t]/close[t-5]-1<0',allocation='Each selected stock target1/60 of total account NAV including cash; residual cash; no search or refill with other stocks',cap_semantics='Enforce at scheduled monthly execution using post-fee NAV when sells possible; blocked legacy sells retained and disclosed; price drift allowed between scheduled trades, no added daily rebalancing',fee_consistency='Solve target scale q=post_fee_NAV/pretrade_NAV at same observed execution open; numerical fixed point <=40 steps tolerance1e-13; not economic optimization',cash_return=0.,costs_bps=[10,20],primary_end='2025-03-03',supplement_end='2026-10-16 or first unvalued holding',benchmark='H00300 full return index close, monthly arithmetic excess in percentage points; cash materially lowers exposure so not risk-adjusted alpha',evidence='Post-selection historical sensitivity, Historical-proxy',no_training=True))
 files.append(D/'config.json');save_json(D/'freeze.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in files]));print('frozen',flush=True)
def verify():
 for x in json.loads((D/'freeze.json').read_text())['files']:assert sha(x['path'])==x['sha256'],x['path']
def prepare():
 verify();assert not (D/'selection.json').exists()
 for x in json.loads((PREV/'selection.json').read_text())['files']:assert sha(x['path'])==x['sha256']
 s=pd.read_parquet(PL/'selection.parquet');s['fullweight_prior']=s.weight;s['weight']=np.where(s.selected,CAP,0.)
 check('same_negative_states',np.array_equal(s.selected,(s.trend<0)&(s['short']<0)))
 schedule=s.groupby(['signal_date','execution_date'],as_index=False).agg(selected_count=('selected','sum'),stock_target=('weight','sum'));schedule['cash_target']=1-schedule.stock_target
 check('positive_cash_targets',schedule.cash_target.min()>=-1e-12)
 s.to_parquet(L/'selection.parquet',index=False);s.to_csv(D/'selection.csv',index=False);schedule.to_csv(D/'schedule.csv',index=False)
 save_json(D/'selection.json',dict(new_account_returns_seen=False,files=[dict(path=str(p),sha256=sha(p)) for p in [L/'selection.parquet',D/'selection.csv',D/'schedule.csv']],checks=CHECKS));print('selection sealed',len(schedule),flush=True)
def run():
 verify();assert not (D/'evaluation_complete.json').exists()
 for x in json.loads((D/'selection.json').read_text())['files']:assert sha(x['path'])==x['sha256']
 inp=Inputs();marks(inp,0.);s=pd.read_parquet(L/'selection.parquet');mapping={}
 for date,g in s.groupby('signal_date'):
  v=np.zeros(inp.n+1);v[inp.symbols.get_indexer(g.instrument)]=g.weight.to_numpy();v[-1]=1-v[:-1].sum();mapping[inp.days.get_loc(date)+1]=v
 units=np.zeros(inp.n);cash=1.;last=pd.Timestamp('2026-10-16');daily=[];orders=[];fail=[];previous=1.
 for i in range(min(mapping),len(inp.days)):
  date=inp.days[i]
  if date>last:break
  row=dict(date=date,buy=0.,sell=0.,fees=0.,posttrade_max_weight=np.nan,posttrade_cap_exceptions=0,unfilled_buy=0.,unfilled_sell=0.)
  if i in mapping:
   member,_,_,_,_,buy,sell,_=inp.context(i-1,i)
   if np.any((units>0)&~np.isfinite(inp.o[i])):fail.append(dict(date=date,reason='HELD_OPEN_UNKNOWN'));break
   old=units.copy();beforecash=cash;units,cash,info,effective,w=cap_trade(old,cash,inp.o[i],mapping[i],buy&member,sell)
   delta=units-old;px=np.nan_to_num(inp.o[i]);fees=np.maximum(delta,0)@px*.001+np.maximum(-delta,0)@px*.002
   check(str(date)+'_self_financing',abs(cash-(beforecash-delta@px-fees))<1e-10)
   check(str(date)+'_gates',not np.any((delta>1e-10)&~(buy&member)) and not np.any((delta< -1e-10)&~sell))
   check(str(date)+'_cap_sellable',not np.any((w>CAP+1e-10)&sell))
   row.update(info);row.update(posttrade_max_weight=float(w.max()),posttrade_cap_exceptions=int((w>CAP+1e-10).sum()))
   for j in np.flatnonzero((old>0)|(units>0)|(mapping[i][:-1]>0)):
    orders.append(dict(date=date,signal_date=inp.days[i-1],instrument=inp.symbols[j],units_before=old[j],units_after=units[j],target_weight=mapping[i][j],effective_pretrade_weight=effective[j],actual_weight=w[j],can_buy=bool(buy[j]&member[j]),can_sell=bool(sell[j]),price=inp.o[i,j],pretrade_nav=info['pretrade_nav']))
  if np.any((units>0)&~np.isfinite(inp.c[i])):fail.append(dict(date=date,reason='HELD_CLOSE_UNKNOWN'));break
  values=units*np.nan_to_num(inp.c[i]);nav=cash+values.sum();weights=values/nav
  row.update(nav=nav,daily_return=nav/previous-1,cash_weight=cash/nav,holdings=int((units>0).sum()),max_stock_weight=float(weights.max()),stocks_above_cap=int((weights>CAP+1e-10).sum()));daily.append(row);previous=nav
 a=pd.DataFrame(daily).set_index('date');o=pd.DataFrame(orders);a.to_csv(D/'CAP60_daily.csv',index_label='date');o.to_parquet(L/'orders.parquet',index=False)
 check('no_negative_cash',a.cash_weight.min()>=-1e-10);absolute_components(inp,a,o)
 base=pd.read_csv(ORIGINAL.with_suffix('.csv'),parse_dates=['date']).set_index('date');old=pd.read_csv(PREV/'DD_daily.csv',parse_dates=['date']).set_index('date')
 comp=pd.DataFrame(dict(CAP60_nav=a.nav,FULL_DD_nav=old.nav.reindex(a.index),E1_nav=base.nav.reindex(a.index),index_nav=benchmark(a.index)),index=a.index)
 for name in ['CAP60','FULL_DD','E1','index']:comp[name+'_return']=daily_returns(comp[name+'_nav'])
 comp.to_csv(D/'daily_comparison.csv',index_label='date');schedule=pd.read_csv(D/'schedule.csv',parse_dates=['execution_date']);periods=[];summaries=[]
 for scope,planned in [('primary',END),('supplement',last)]:
  end=min(planned,a.index.max());x=comp.loc[:end];account=a.loc[:end]
  for freq in ['Y','M']:
   for period,g in x.groupby(x.index.to_period(freq)):
    returns={name:float(np.prod(1+g[name+'_return'])-1) for name in ['CAP60','FULL_DD','E1','index']};native=inp.days[inp.days.to_period(freq)==period];sc=schedule[schedule.execution_date.between(g.index.min(),g.index.max())]
    periods.append(dict(scope=scope,frequency=freq,period=str(period),start=g.index.min(),end=g.index.max(),days=len(g),partial=g.index.min()>native.min() or g.index.max()<native.max(),**{name+'_return':v for name,v in returns.items()},excess_pp=(returns['CAP60']-returns['index'])*100,vs_full_DD_pp=(returns['CAP60']-returns['FULL_DD'])*100,vs_E1_pp=(returns['CAP60']-returns['E1'])*100,average_stock_weight=float((1-account.loc[g.index].cash_weight).mean()),average_holdings=float(account.loc[g.index].holdings.mean()),selected_count=int(sc.selected_count.iloc[-1]) if len(sc) else np.nan,stock_target=float(sc.stock_target.iloc[-1]) if len(sc) else np.nan))
  for name in ['CAP60','FULL_DD','E1','index']:
   v=x[name+'_nav'];draw=v/np.maximum.accumulate(np.r_[1.,v.to_numpy()])[1:]-1
   summaries.append(dict(scope=scope,account=name,end=end,complete=end==planned,days=len(x),terminal_per100=float(v.iloc[-1]*100),total_return=float(v.iloc[-1]-1),cagr=float(v.iloc[-1]**(252/len(v))-1),max_drawdown=float(draw.min()),average_stock_weight=float((1-account.cash_weight).mean()) if name=='CAP60' else np.nan))
  p=pd.DataFrame(periods);m=p[p.scope.eq(scope)&p.frequency.eq('M')];check(scope+'_monthly_reconcile',np.isclose(np.prod(1+m.CAP60_return),x.CAP60_nav.iloc[-1]))
 pd.DataFrame(periods).to_csv(D/'periods.csv',index=False);pd.DataFrame(summaries).to_csv(D/'summary.csv',index=False)
 save_json(D/'validation.json',dict(status='PASS',checks=CHECKS,failures=fail,posttrade_max_weight=float(a.posttrade_max_weight.max()),posttrade_cap_exception_rows=int(a.posttrade_cap_exceptions.sum()),close_drift_days=int(a.stocks_above_cap.gt(0).sum()),close_max_stock_weight=float(a.max_stock_weight.max())))
 files=list(D.glob('*.csv'))+[L/'orders.parquet'];save_json(D/'evaluation_complete.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in files]));print(pd.DataFrame(summaries).to_string(index=False));print('limits',json.loads((D/'validation.json').read_text())|{'checks':len(CHECKS)},flush=True)
def report():
 verify();summary=pd.read_csv(D/'summary.csv');periods=pd.read_csv(D/'periods.csv');schedule=pd.read_csv(D/'schedule.csv');v=json.loads((D/'validation.json').read_text())
 def tab(f):
  f=f.copy()
  for c in ['CAP60_return','index_return','FULL_DD_return','E1_return','average_stock_weight']:f[c]*=100
  f['period']=f.period+np.where(f.partial,'*','')
  return f[['period','CAP60_return','index_return','excess_pp','FULL_DD_return','E1_return','average_stock_weight']].rename(columns={'period':'期间','CAP60_return':'1/60上限净收益%','index_return':'指数收益%','excess_pp':'超额pp','FULL_DD_return':'上轮满仓双跌收益%','E1_return':'原E1收益%','average_stock_weight':'平均股票仓位%'}).to_markdown(index=False,floatfmt='.2f')
 z=summary.copy()
 for c in ['total_return','cagr','max_drawdown','average_stock_weight']:z[c]*=100
 primary=summary[(summary.scope=='primary')&(summary.account=='CAP60')].iloc[0];full=summary[(summary.scope=='supplement')&(summary.account=='CAP60')].iloc[0]
 body=f'''# E1双跌子集每只最多1/60的月度账户

**主区间截至2025-03-03累计收益{primary.total_return*100:+.2f}%、净年化{primary.cagr*100:+.2f}%；补充区间至{full.end}累计{full.total_return*100:+.2f}%、净年化{full.cagr*100:+.2f}%。**

## 固定规则

完全复用上一轮70个原E1月初Q5内双跌名单和执行日期。中期为close[t−5]/close[t−60]−1<0，短期为close[t]/close[t−5]−1<0；非原Q5股票不补入。每只入选股最多配置账户总资产（包括现金）的1/60，剩余资金留现金，现金收益按0，不再按剩余股票数重新归一化。

例如选中12只，目标股票仓位20%、现金80%；只有1只时股票约1.67%；没有符合则现金。为避免扣费后分母缩小使单股超过1/60，执行时按实际扣费后NAV做一致性求解；它是会计校正，不是优化权重。

上限在原每月调仓开盘执行时约束；月内涨跌导致权重漂移，不擅自新增每日卖出规则。无法卖出的旧仓不能强制成交，超限另列。买10/卖20bps、涨跌停门槛和原suspend_flat估值代理不变。首次建仓费用计入，终点收盘估值、不假装清仓。

## 汇总

{z[['scope','account','end','complete','terminal_per100','total_return','cagr','max_drawdown','average_stock_weight']].to_markdown(index=False,floatfmt='.3f')}

CAP60是本轮；FULL_DD是上一轮筛选后满仓等权；E1是原全组合；index是沪深300全收益H00300。收益/年化/回撤为%，终值为初始100元对应金额。两个主区间和补充区间独立汇总，不把部分月拼成整月。

## 完整逐月收益与超额

超额=本轮组合净收益−同期H00300全收益指数收益，单位百分点；高现金账户与满仓指数风险不同，这不是风格或市场风险中性Alpha。*为不完整自然月：2021年1月从首次执行1月11日起，2026年10月到16日。

{tab(periods[(periods.scope=='supplement')&(periods.frequency=='M')])}

## 原主区间末月

2025年3月主区间仅到3月3日，与上表整月不同：

{tab(periods[(periods.scope=='primary')&(periods.frequency=='M')].tail(1))}

## 逐年

{tab(periods[(periods.scope=='supplement')&(periods.frequency=='Y')])}

## 仓位及上限审计

70个信号平均选{schedule.selected_count.mean():.2f}只，目标股票仓位平均{schedule.stock_target.mean()*100:.2f}%，范围{schedule.stock_target.min()*100:.2f}%至{schedule.stock_target.max()*100:.2f}%。目标股票仓位的信号均值与每日实际仓位均值不同。

成交后最大单股权重{v['posttrade_max_weight']*100:.6f}%；因不能卖出造成的成交后超限证券记录{v['posttrade_cap_exception_rows']}条。收盘至少一只超过1/60的日数{v['close_drift_days']}，月内最大收盘单股权重{v['close_max_stock_weight']*100:.4f}%。后者是月内漂移，不能声称每天严格1/60。如果要求每天硬上限，需要另定义调仓与费用合同。

完成{len(v['checks'])}项目标/交易/现金/上限/月度复利检查。运行阻断：{v['failures']}。旧输入与名单保留哈希，新目标先封存后算收益，不覆盖上一轮。看过历史结果后指定的新回测仍是探索性情景，Historical-proxy及公司行动边界不变。

- [逐月逐年数据](../../outputs/diagnostics/{RUN}/periods.csv)
- [汇总](../../outputs/diagnostics/{RUN}/summary.csv)
- [名单及权重](../../outputs/diagnostics/{RUN}/selection.csv)
- [每日净值对照](../../outputs/diagnostics/{RUN}/daily_comparison.csv)
- [现金与权重漂移](../../outputs/diagnostics/{RUN}/CAP60_daily.csv)
- [冻结合同](../../outputs/diagnostics/{RUN}/config.json)
- [上限与账本核验](../../outputs/diagnostics/{RUN}/validation.json)
'''
 (R/'REPORT.md').write_text(body);save_json(D/'delivery.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in [R/'REPORT.md']+list(D.glob('*.csv'))]));print(R/'REPORT.md')
if __name__=='__main__':globals()[sys.argv[1]]()
