"""Exact original E1 monthly attribution and same-date industry-budget controls.

Original ledger immutable. All arithmetic is reconciled to original NAV, not a
new constrained E1. Attribution is descriptive and is not causal identification.
"""
from datetime import datetime,timezone
import json,sys
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from backtest import Inputs
from suspension_sensitivity import marks
from evaluate_ranking import predictions
from alpha_economics import run_account

RUN='e1_return_attribution_20261117';DEST=OUT/'diagnostics'/RUN;LOCAL=PRIVATE/RUN
CONFIG=EP/'configs'/(RUN+'.json');END=pd.Timestamp('2025-03-03');ANCHOR=pd.Timestamp('2021-01-08')
ORIGINAL=OUT/'sensitivity/q5_rebalance_20261116/accounts/suspend_flat__E1__1m__main'
EW=OUT/'sensitivity/q5_controls_phases_buffers_20261116/accounts/EW__1m__p1__b0__main'


def freeze():
 if CONFIG.exists():raise RuntimeError('Already registered')
 DEST.mkdir(parents=True,exist_ok=True);LOCAL.mkdir(parents=True,exist_ok=True)
 files=[]
 for root in [ORIGINAL,EW]:
  r=json.loads(root.with_suffix('.json').read_text());assert sha(root.with_suffix('.csv'))==r['nav_sha256']
  for key in ['orders','holdings']:assert sha(r[key+'_path'])==r[key+'_sha256']
  files.extend([root.with_suffix('.csv'),root.with_suffix('.json'),r['orders_path'],r['holdings_path']])
 _,pred=predictions('expanding')
 files += [PRIVATE/(n+'.parquet') for n in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','industry']]
 files += [PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'weights/snapshots.parquet',PRIVATE/'net_excess_20261116/H00300.CSI.json',PRIVATE/'net_excess_20261116/H00300.CSI.receipt.json']
 cfg=dict(run=RUN,created_at=datetime.now(timezone.utc).isoformat(),authorization='User requested year/month concentration, industry/stock contribution, same-date industry controls',
 original='Original E1 expanding monthly first weekly signal Q5, main cost, suspend_flat; not alpha_economics constrained S1',anchor=str(ANCHOR),primary_end=str(END),
 cost_bps=[10,20],evidence='historical_simulated_oos_posthoc_descriptive_Historical_proxy',forward='FORWARD_PENDING',
 attribution=dict(stock_pnl='change in close marked stock value minus net executed trade cash; prior NAV denominator',
 opportunity_charge='Subtract previous-close stock weight times actual H00300 close-to-close return; cash charged previous cash weight, fees separate; opening index value never fabricated',
 daily_link='k=(log(1+portfolio_return)-log(1+index_return))/(portfolio_return-index_return), continuous limit 1/(1+index_return)',
 wealth_link='Sum daily linked contributions gives log relative wealth. Multiply all contributions by 100*(terminal portfolio NAV-terminal benchmark NAV)/log(relative NAV) to attribute terminal wealth difference per initial100yuan; single common scale for all months/years/stocks',
 industry='Historical L1 interval at previous market close, UNKNOWN explicit. New stock PnL assigned same previous-close industry. Industry totals locate the account contribution; NOT allocation/selection attribution relative to true index constituent weights',
 periods='Calendar years and months, initial build included; annual/month raw return differences are not additive; linked wealth contributions are additive across all periods',
 concentration='Report top3 months, top5/10 stocks and top3 industries with shares of signed total; no pruning to create strategy'),
 controls=dict(EW_ALL='All historical members equalweight, exact original dates; verify against existing same-period EW ledger',
 EW_SCORED='Original E1 finite-score contemporaneous members equalweight; no new 13-style complete-case filter',
 INDUSTRY='Original E1 target industry capital fractions, spread equally within each historical industry over SAME finite-score member pool; same initial1 cash, dates, costs, gates and mark rules; not same number of holdings',
 E1_REPLAY='Original target weights exactly; require original NAV and order replication',
 chain='Index -> EW_ALL -> EW_SCORED -> INDUSTRY -> original E1. Linked log increments and CAGR differences telescope exactly on common available interval',
 interpretation='EW_ALL/index includes equalweight, investable-universe and benchmark-account basis effects. INDUSTRY/EW_SCORED is target-industry-budget/path effect. E1/INDUSTRY includes within-industry selection, concentration, drift and execution, not pure causal stock alpha',
 risk='Target industry fractions identical; realized post-fill industry mismatch, cash, fees and holdings count disclosed; normalized proportions equal, evolving absolute NAV budgets may differ',
 missing='Never fill held unknown values or invent corporate-action terminal payoffs. If control stops before primary end, reduce common bridge endpoint and keep original full-period attribution separately'),
 statistics='Bridge contrasts descriptive paired daily means, 65 trading-day circular blocks, 2000 draws, seed20261117; intervals for annual mean daily return difference, not CAGR gap; no new confirmatory family',
 no_change='No model retraining, score changes, trading-date search, tolerance optimization, original artifact overwrite, deployment or publishing')
 save_json(CONFIG,cfg)
 sources=[EP/'src'/n for n in ['e1_return_attribution.py','alpha_economics.py','backtest.py','portfolio.py','suspension_sensitivity.py','common.py']]
 save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),inputs=[dict(path=str(p),sha256=sha(p)) for p in files],sources=[dict(path=str(p),sha256=sha(p)) for p in sources],predictions=pred,prior_results_seen=True,new_attribution_and_controls_seen=False))
 print('frozen',RUN,flush=True)


def verify():
 r=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==r['config_sha256']
 for x in r['inputs']+r['sources']+r['predictions']:assert sha(x['path'])==x['sha256'],x['path']
 return r


def daily_returns(nav):
 return nav.div(nav.shift(fill_value=1.))-1


def log_link(rp,rb):
 rp=np.asarray(rp,float);rb=np.asarray(rb,float);diff=rp-rb
 out=1/(1+rb)
 return np.divide(np.log1p(rp)-np.log1p(rb),diff,out=out.copy(),where=np.abs(diff)>1e-12)


def wealth_scale(p,b):
 gap=np.log(p/b)
 return 100*b*(np.expm1(gap)/gap if abs(gap)>1e-12 else 1.)


def industry_map(inp,date):
 h=inp.ind[(inp.ind.start<=date)&(inp.ind.end>date)]
 codes=h.groupby('instrument').l1_code.agg(lambda x:x.iloc[0] if x.notna().all() and x.nunique()==1 else 'UNKNOWN')
 return codes.reindex(inp.symbols).fillna('UNKNOWN')


def benchmark(index):
 raw=PRIVATE/'net_excess_20261116/H00300.CSI.json';r=json.loads(raw.with_suffix('.receipt.json').read_text());assert sha(raw)==r['sha256']
 body=json.loads(raw.read_text())['data'];f=pd.DataFrame(body['items'],columns=body['fields']);f['date']=pd.to_datetime(f.trade_date);s=f.set_index('date').close.sort_index()
 b=s.reindex(index)/s.loc[ANCHOR];assert b.notna().all();return b


def attribute():
 verify()
 if (DEST/'attribution_complete.json').exists():raise RuntimeError('Attribution sealed')
 inp=Inputs();r=json.loads(ORIGINAL.with_suffix('.json').read_text());a=pd.read_csv(ORIGINAL.with_suffix('.csv'),parse_dates=['date']).set_index('date').loc[:END]
 h=pd.read_parquet(r['holdings_path']);h=h[h.date<=END].copy();h['value']=h.synthetic_units*h.valuation_close
 # Unheld positions are known zero, not missing market prices.
 values=h.pivot(index='date',columns='instrument',values='value').reindex(a.index).fillna(0)
 orders=pd.read_parquet(r['orders_path']);orders=orders[orders.date<=END].copy();orders['trade_cash']=(orders.units_after-orders.units_before)*orders.qfq_open
 traded=orders.groupby(['date','instrument']).trade_cash.sum().unstack().reindex(index=a.index,columns=values.columns).fillna(0)
 prevvalues=values.shift(fill_value=0);pnl=values-prevvalues-traded
 prevnav=a.nav.shift(fill_value=1.);rp=daily_returns(a.nav);b=benchmark(a.index);rb=daily_returns(b)
 gross=pnl.div(prevnav,axis=0)
 priorweights=prevvalues.div(prevnav,axis=0)
 fee=-a.fees/prevnav;priorcash=(prevnav-prevvalues.sum(axis=1))/prevnav
 active=gross-priorweights.mul(rb,axis=0)
 active['__FEES__']=fee;active['__CASH__']=-priorcash*rb
 checks=[]
 def check(name,ok):assert bool(ok),name;checks.append(dict(check=name,passed=True))
 check('absolute daily pnl fees equals NAV return',np.allclose(gross.sum(axis=1)+fee,rp,atol=1e-11))
 check('cash and stocks previous weights sum1',np.allclose(priorweights.sum(axis=1)+priorcash,1,atol=1e-11))
 check('daily active attribution',np.allclose(active.sum(axis=1),rp-rb,atol=1e-11))
 linked=active.mul(log_link(rp,rb),axis=0)
 gap=np.log(a.nav.iloc[-1]/b.iloc[-1]);scale=wealth_scale(a.nav.iloc[-1],b.iloc[-1])
 check('log relative wealth',np.isclose(linked.to_numpy().sum(),gap,atol=1e-10))
 check('terminal wealth difference',np.isclose(linked.to_numpy().sum()*scale,100*(a.nav.iloc[-1]-b.iloc[-1]),atol=1e-9))
 daily=pd.DataFrame(dict(portfolio_nav=a.nav,benchmark_nav=b,portfolio_return=rp,benchmark_return=rb,active_return=rp-rb,log_gap=linked.sum(axis=1),wealth_contribution=linked.sum(axis=1)*scale,fees=a.fees))
 daily.to_csv(DEST/'daily_account.csv',index_label='date')
 records=[]
 for freq in ['Y','M']:
  for period,g in daily.groupby(daily.index.to_period(freq)):
   own=float(np.prod(1+g.portfolio_return)-1);bench=float(np.prod(1+g.benchmark_return)-1)
   records.append(dict(frequency=freq,period=str(period),start=g.index.min(),end=g.index.max(),days=len(g),portfolio_return=own,benchmark_return=bench,return_difference=own-bench,relative_return=(1+own)/(1+bench)-1,log_contribution=g.log_gap.sum(),wealth_contribution=g.wealth_contribution.sum(),share_of_total=g.log_gap.sum()/gap,positive_days=int(g.active_return.gt(0).sum())))
 periods=pd.DataFrame(records);periods.to_csv(DEST/'periods.csv',index=False)
 names=inp.ind.sort_values('start').groupby('instrument')['name'].last().to_dict() if 'name' in inp.ind else {}
 industry_names=inp.ind.groupby('l1_code').l1_name.first().to_dict();industry_names.update(UNKNOWN='未知行业',__FEES__='交易费用',__CASH__='现金机会成本')
 monthrows=[];industryrows=[];stockrows=[]
 for instrument,value in linked.sum().items():
  stockrows.append(dict(instrument=instrument,name=names.get(instrument,instrument),log_contribution=value,wealth_contribution=value*scale,share_of_total=value/gap,absolute_pnl_per100=float(pnl[instrument].sum()*100) if instrument in pnl else (-a.fees.sum()*100 if instrument=='__FEES__' else 0.),holding_days=int(values[instrument].gt(0).sum()) if instrument in values else 0))
 for date,row in linked.iterrows():
  previous=inp.days[inp.days.get_loc(date)-1];groups=industry_map(inp,previous)
  for instrument,value in row.items():
   if value==0:continue
   ind=instrument if instrument.startswith('__') else groups.loc[instrument]
   monthrows.append(dict(date=date,month=str(date.to_period('M')),instrument=instrument,industry=ind,log_contribution=value,wealth_contribution=value*scale))
 detail=pd.DataFrame(monthrows)
 detail.to_parquet(LOCAL/'daily_active_stock_industry.parquet',index=False)
 detail.groupby(['month','instrument'],as_index=False)[['log_contribution','wealth_contribution']].sum().to_csv(DEST/'stock_month.csv',index=False)
 im=detail.groupby(['month','industry'],as_index=False)[['log_contribution','wealth_contribution']].sum();im['name']=im.industry.map(industry_names);im.to_csv(DEST/'industry_month.csv',index=False)
 industry=detail.groupby('industry',as_index=False)[['log_contribution','wealth_contribution']].sum();industry['name']=industry.industry.map(industry_names);industry['share_of_total']=industry.log_contribution/gap;industry.sort_values('wealth_contribution',ascending=False).to_csv(DEST/'industry_contributions.csv',index=False)
 stocks=pd.DataFrame(stockrows).sort_values('wealth_contribution',ascending=False);stocks.to_csv(DEST/'stock_contributions.csv',index=False)
 components=gross.copy();components['__FEES__']=fee;components.to_parquet(LOCAL/'E1_components.parquet')
 checks.extend([dict(check='industry sum',passed=bool(np.isclose(industry.wealth_contribution.sum(),100*(a.nav.iloc[-1]-b.iloc[-1])))),dict(check='stocks sum',passed=bool(np.isclose(stocks.wealth_contribution.sum(),100*(a.nav.iloc[-1]-b.iloc[-1]))))])
 assert all(x['passed'] for x in checks)
 months=periods[periods.frequency=='M'];top=months.nlargest(3,'log_contribution');stock_only=stocks[~stocks.instrument.str.startswith('__')]
 save_json(DEST/'attribution_summary.json',dict(start=str(ANCHOR),first_execution=str(a.index[0]),end=str(a.index[-1]),days=len(a),portfolio_nav=float(a.nav.iloc[-1]),benchmark_nav=float(b.iloc[-1]),portfolio_cagr=float(a.nav.iloc[-1]**(252/len(a))-1),benchmark_cagr=float(b.iloc[-1]**(252/len(a))-1),log_gap=float(gap),wealth_difference_per100=float(100*(a.nav.iloc[-1]-b.iloc[-1])),wealth_link_scale=float(scale),positive_months=int(months.log_contribution.gt(0).sum()),months=len(months),top3_months=top.period.tolist(),top3_month_share=float(top.log_contribution.sum()/gap),top5_stock_share=float(stock_only.head(5).log_contribution.sum()/gap),top10_stock_share=float(stock_only.head(10).log_contribution.sum()/gap),proxy='Synthetic qfq units and explicit suspension marks; industry vintage proxy; relative account attribution not formal index allocation'))
 save_json(DEST/'attribution_validation.json',dict(checks=checks,status='PASS'))
 files=[p for p in DEST.iterdir() if p.is_file()]+[LOCAL/'daily_active_stock_industry.parquet',LOCAL/'E1_components.parquet']
 save_json(DEST/'attribution_complete.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in files]))
 print('original account attributed',len(a),'days',flush=True)


def prepare_controls():
 verify();inp=Inputs()
 r=json.loads(ORIGINAL.with_suffix('.json').read_text());o=pd.read_parquet(r['orders_path']);o=o[o.date<=END]
 p,_=predictions('expanding');p=p[(p.model_id=='E1')&(p.seed_or_ensemble=='fixed')]
 targets=[];audit=[]
 for date,g in o.groupby('date'):
  ei=inp.days.get_loc(date);si=ei-1;signal=inp.days[si]
  member,_,_,_,industry,_,_,_=inp.context(si,ei)
  scores=p[p.signal_date==signal].set_index('instrument').score.reindex(inp.symbols)
  eligible=member & scores.notna().to_numpy()
  original=np.zeros(inp.n);original[inp.symbols.get_indexer(g.instrument)]=g.target_weight.to_numpy()
  assert np.isclose(original.sum(),1) and not ((original>0)&~eligible).any()
  all_ew=member.astype(float)/member.sum();score_ew=eligible.astype(float)/eligible.sum();indtarget=np.zeros(inp.n)
  for group in set(industry[original>0]):
   budget=original[industry==group].sum();candidates=eligible&(industry==group);assert candidates.any()
   indtarget[candidates]=budget/candidates.sum()
  error=max(abs(indtarget[industry==group].sum()-original[industry==group].sum()) for group in set(industry))
  assert error<1e-12
  audit.append(dict(signal_date=signal,execution_date=date,members=int(member.sum()),scored=int(eligible.sum()),original_count=int((original>0).sum()),industry_control_count=int((indtarget>0).sum()),industry_target_error=error,unknown_industry_budget=original[industry=='UNKNOWN'].sum()))
  for name,v in [('E1_REPLAY',original),('EW_ALL',all_ew),('EW_SCORED',score_ew),('INDUSTRY',indtarget)]:
   for j in np.flatnonzero(v):targets.append(dict(control=name,signal_date=signal,instrument=inp.symbols[j],weight=v[j],industry=industry[j]))
 pd.DataFrame(targets).to_parquet(LOCAL/'control_targets.parquet',index=False);pd.DataFrame(audit).to_csv(DEST/'control_target_audit.csv',index=False)
 save_json(DEST/'control_selection.json',dict(targets_sha256=sha(LOCAL/'control_targets.parquet'),audit_sha256=sha(DEST/'control_target_audit.csv'),new_control_outcomes_seen=False))
 print('control targets sealed',len(audit),flush=True)


def run_controls():
 verify();sel=json.loads((DEST/'control_selection.json').read_text());assert sha(LOCAL/'control_targets.parquet')==sel['targets_sha256']
 inp=Inputs();marks(inp,0.);targets=pd.read_parquet(LOCAL/'control_targets.parquet');folder=DEST/'controls';folder.mkdir(exist_ok=True)
 for name,g in targets.groupby('control'):
  mapping={}
  for date,h in g.groupby('signal_date'):
   v=np.zeros(inp.n+1);v[inp.symbols.get_indexer(h.instrument)]=h.weight.to_numpy();mapping[date]=v
  daily,orders,fail=run_account(inp,mapping,sorted(mapping),(.001,.002),end=END)
  daily.to_csv(folder/(name+'.csv'),index=False);orders.to_parquet(LOCAL/(name+'_orders.parquet'),index=False)
  save_json(folder/(name+'.json'),dict(failures=fail,nav_sha256=sha(folder/(name+'.csv')),orders_path=str(LOCAL/(name+'_orders.parquet')),orders_sha256=sha(LOCAL/(name+'_orders.parquet'))))
  print(name,len(daily),fail,flush=True)


def absolute_components(inp,account,orders):
 ids=account.index
 units=orders.pivot(index='date',columns='instrument',values='units_after').reindex(ids).ffill().fillna(0)
 cols=inp.symbols.get_indexer(units.columns);price=pd.DataFrame(inp.c[np.ix_(inp.days.get_indexer(ids),cols)],index=ids,columns=units.columns)
 assert not ((units>0)&price.isna()).any().any()
 values=(units*price).where(units>0,0)
 o=orders.copy();o['trade_cash']=(o.units_after-o.units_before)*o.price
 cash=o.groupby(['date','instrument']).trade_cash.sum().unstack().reindex(index=ids,columns=units.columns).fillna(0)
 pnl=values-values.shift(fill_value=0)-cash;prev=account.nav.shift(fill_value=1.)
 components=pnl.div(prev,axis=0);components['__FEES__']=-account.fees/prev
 assert np.allclose(components.sum(axis=1),daily_returns(account.nav),atol=1e-10)
 return components


def paired_ci(x):
 a=np.asarray(x,float);n=len(a)
 if n<130:return np.nan,np.nan
 rng=np.random.default_rng(20261117);L=65;idx=((rng.integers(0,n,(2000,int(np.ceil(n/L))))[:,:,None]+np.arange(L))%n).reshape(2000,-1)[:,:n]
 return np.quantile(a[idx].mean(axis=1)*252,[.025,.975])


def analyze_controls():
 verify();inp=Inputs();marks(inp,0.);frames={};components={};checks=[]
 def check(name,ok):assert bool(ok),name;checks.append(dict(check=name,passed=True))
 for name in ['E1_REPLAY','EW_ALL','EW_SCORED','INDUSTRY']:
  root=DEST/'controls'/name;r=json.loads(root.with_suffix('.json').read_text());check(name+' NAV hash',sha(root.with_suffix('.csv'))==r['nav_sha256']);check(name+' orders hash',sha(r['orders_path'])==r['orders_sha256'])
  frames[name]=pd.read_csv(root.with_suffix('.csv'),parse_dates=['date']).set_index('date')
 original=pd.read_csv(ORIGINAL.with_suffix('.csv'),parse_dates=['date']).set_index('date').loc[:END]
 ewall=pd.read_csv(EW.with_suffix('.csv'),parse_dates=['date']).set_index('date').loc[:END]
 check('original exact daily NAV replay',frames['E1_REPLAY'].index.equals(original.index) and np.allclose(frames['E1_REPLAY'].nav,original.nav,atol=1e-12,rtol=1e-12))
 check('original EW exact daily NAV replay',frames['EW_ALL'].index.equals(ewall.index) and np.allclose(frames['EW_ALL'].nav,ewall.nav,atol=1e-12,rtol=1e-12))
 end=min(f.index.max() for f in frames.values());ids=original.loc[:end].index;n=len(ids);b=benchmark(ids)
 metrics=[];allnav=pd.DataFrame({'INDEX':b},index=ids)
 for name,frame in frames.items():
  f=frame.loc[ids];allnav[name]=f.nav
  metrics.append(dict(account=name,start=ids[0],end=end,days=n,nav=f.nav.iloc[-1],cagr=f.nav.iloc[-1]**(252/n)-1,mean_cash=f.cash_weight.mean(),mean_holdings=f.holdings.mean(),total_fees_initial=f.fees.sum(),annual_oneway_turnover=.5*(f.buy.sum()+f.sell.sum())*252/n,unfilled_buy_mean=f.unfilled_buy.mean(),unfilled_sell_mean=f.unfilled_sell.mean()))
  orders=pd.read_parquet(LOCAL/(name+'_orders.parquet'));orders=orders[orders.date<=end]
  comp=absolute_components(inp,f,orders);r=daily_returns(f.nav);k=np.divide(np.log1p(r),r,out=np.ones(n),where=np.abs(r)>1e-12)
  components[name]=comp.mul(k,axis=0)
  check(name+' log components',np.isclose(components[name].to_numpy().sum(),np.log(f.nav.iloc[-1]),atol=1e-10))
 metrics.append(dict(account='INDEX',start=ids[0],end=end,days=n,nav=b.iloc[-1],cagr=b.iloc[-1]**(252/n)-1))
 pd.DataFrame(metrics).to_csv(DEST/'control_metrics.csv',index=False);allnav.to_csv(DEST/'control_navs.csv',index_label='date')
 stages=[('EW_ALL','INDEX','equalweight_and_basis'),('EW_SCORED','EW_ALL','score_coverage'),('INDUSTRY','EW_SCORED','industry_budget_path'),('E1_REPLAY','INDUSTRY','within_industry_concentration_execution')]
 lg=np.log(allnav).diff();lg.iloc[0]=np.log(allnav.iloc[0]);total_log=np.log(allnav.E1_REPLAY.iloc[-1]/allnav.INDEX.iloc[-1]);scale=wealth_scale(allnav.E1_REPLAY.iloc[-1],allnav.INDEX.iloc[-1])
 bridge=[];periods=[];industryrows=[];stockrows=[]
 names=inp.ind.groupby('l1_code').l1_name.first().to_dict();names.update(UNKNOWN='未知行业',__FEES__='费用差')
 for own,base,stage in stages:
  gap=lg[own]-lg[base];active=daily_returns(allnav[own])-daily_returns(allnav[base]);lo,hi=paired_ci(active)
  bridge.append(dict(stage=stage,own=own,base=base,end=end,cagr_difference=allnav[own].iloc[-1]**(252/n)-allnav[base].iloc[-1]**(252/n),log_contribution=gap.sum(),wealth_contribution=gap.sum()*scale,share_of_total=gap.sum()/total_log,annual_mean_daily_difference=active.mean()*252,ci_low=lo,ci_high=hi))
  for freq in ['Y','M']:
   for period,x in gap.groupby(gap.index.to_period(freq)):periods.append(dict(stage=stage,frequency=freq,period=str(period),log_contribution=x.sum(),wealth_contribution=x.sum()*scale))
  if base=='INDEX':continue
  delta=components[own].subtract(components[base],fill_value=0)
  check(stage+' component chain',np.isclose(delta.to_numpy().sum(),gap.sum(),atol=1e-10))
  byindustry={}
  for date,row in delta.iterrows():
   groups=industry_map(inp,inp.days[inp.days.get_loc(date)-1])
   for instrument,value in row.items():
    if value==0:continue
    ind=instrument if instrument.startswith('__') else groups.loc[instrument]
    key=(str(date.to_period('M')),ind);byindustry[key]=byindustry.get(key,0.)+value
  for (month,ind),value in byindustry.items():industryrows.append(dict(stage=stage,month=month,industry=ind,name=names.get(ind,ind),log_contribution=value,wealth_contribution=value*scale))
  for instrument,value in delta.sum().items():stockrows.append(dict(stage=stage,instrument=instrument,log_contribution=value,wealth_contribution=value*scale))
 bridge=pd.DataFrame(bridge);check('bridge log sum',np.isclose(bridge.log_contribution.sum(),total_log,atol=1e-10));check('bridge wealth sum',np.isclose(bridge.wealth_contribution.sum(),100*(allnav.E1_REPLAY.iloc[-1]-allnav.INDEX.iloc[-1]),atol=1e-9));check('bridge CAGR gap sum',np.isclose(bridge.cagr_difference.sum(),allnav.E1_REPLAY.iloc[-1]**(252/n)-allnav.INDEX.iloc[-1]**(252/n),atol=1e-12))
 bridge.to_csv(DEST/'attribution_bridge.csv',index=False);pd.DataFrame(periods).to_csv(DEST/'bridge_periods.csv',index=False);pd.DataFrame(industryrows).to_csv(DEST/'bridge_industry_month.csv',index=False);pd.DataFrame(stockrows).to_csv(DEST/'bridge_stock.csv',index=False)
 # Audit actual same-day industry weights, not just target equality.
 own=pd.read_parquet(LOCAL/'E1_REPLAY_orders.parquet');ctrl=pd.read_parquet(LOCAL/'INDUSTRY_orders.parquet');risk=[]
 for date,g in own.groupby('date'):
  h=ctrl[ctrl.date==date]
  if h.empty:continue
  groups=industry_map(inp,inp.days[inp.days.get_loc(date)-1]);w=g.set_index('instrument').actual_weight.reindex(inp.symbols).fillna(0);v=h.set_index('instrument').actual_weight.reindex(inp.symbols).fillna(0)
  dg=(w-v).groupby(groups).sum();tw=g.set_index('instrument').target_weight.reindex(inp.symbols).fillna(0);tv=h.set_index('instrument').target_weight.reindex(inp.symbols).fillna(0)
  targetdiff=(tw-tv).groupby(groups).sum()
  check('industry target identical '+str(date),targetdiff.abs().max()<1e-12)
  risk.append(dict(date=date,max_industry_gap=dg.abs().max(),half_L1_industry_gap=.5*dg.abs().sum(),cash_gap=g.cash_weight.iloc[0]-h.cash_weight.iloc[0],own_holdings=int(g.actual_weight.gt(0).sum()),control_holdings=int(h.actual_weight.gt(0).sum())))
 pd.DataFrame(risk).to_csv(DEST/'industry_actual_matching.csv',index=False)
 save_json(DEST/'control_validation.json',dict(status='PASS',checks=checks,common_end=str(end),planned_end=str(END),same_target_industries=True,exact_original_and_EW_replay=True))
 verify();print('control attribution PASS',len(checks),flush=True);print(bridge.to_string(index=False),flush=True)


if __name__=='__main__':
 {'freeze':freeze,'attribute':attribute,'prepare':prepare_controls,'controls':run_controls,'analyze':analyze_controls,'verify':verify}[sys.argv[1]]()
