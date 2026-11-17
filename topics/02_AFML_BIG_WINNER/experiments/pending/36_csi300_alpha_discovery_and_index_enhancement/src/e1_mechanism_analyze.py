"""Registered statistics and descriptive attribution for EP36 mechanism trial."""
import sys,json
import numpy as np
import pandas as pd
from scipy.stats import norm
from e1_mechanism import *
from e1_return_attribution import benchmark

def analyze():
 verify();verify('selection_complete');verify('analysis_registration');verify('evaluation_complete')
 assert not (D/'analysis_complete.json').exists()
 schedule=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date']);reg=pd.read_csv(D/'conditional.csv',parse_dates=['signal_date','exit_date']);events=pd.read_csv(D/'events.csv',parse_dates=['signal_date','entry_date','exit_date']);scores=pd.read_parquet(L/'labeled_events.parquet')
 phases=schedule.set_index('signal_date').phase;dates=pd.DatetimeIndex(schedule.signal_date);main_dates=dates[(dates>=START)&(dates<=END)];month_dates=pd.DatetimeIndex(schedule.loc[(schedule.phase==1)&(schedule.signal_date>=START)&(schedule.signal_date<=END),'signal_date'])
 # Both auxiliary scopes and all horizons preserved. Main family exactly P1 P2 P3.
 stats=[];primary=[]
 for scope in ['primary','extended']:
  for h in [5,10,20]:
   for test in ['P1','P3']:
    a=reg[(reg.horizon==h)&(reg.test==test)&(reg.signal_date>=START)]
    if scope=='primary':a=a[a.exit_date<=END]
    ix=main_dates if scope=='primary' else dates
    s=a.set_index('signal_date').value.reindex(ix);r=bootstrap(s,'W-FRI',13);row=dict(scope=scope,horizon=h,test=test,**r);stats.append(row)
    if scope=='primary' and h==10:primary.append(row.copy())
  a=events[(events.phase==1)&(events.cost=='main')&(events.horizon==10)&events.strategy.isin(['B','J'])]
  if scope=='primary':a=a[(a.exit_date<=END)&(a.signal_date>=START)]
  pivot=a.pivot(index='signal_date',columns='strategy',values='net_return');ix=month_dates if scope=='primary' else pd.DatetimeIndex(schedule.loc[schedule.phase==1,'signal_date'])
  s=(pivot.J-pivot.B).reindex(ix);r=bootstrap(s,'M',3);row=dict(scope=scope,horizon=10,test='P2',coverage=float(s.notna().sum()/len(s)),planned=len(s),**r);stats.append(row)
  if scope=='primary':primary.append(row.copy());write(s.rename('J_minus_B').reset_index(),'primary_p2_months.csv')
 primary=pd.DataFrame(primary).sort_values('test');primary['holm_p']=holm(primary.p.to_numpy());primary['coverage_gate']=True
 primary.loc[primary.test=='P2','coverage_gate']=(primary.loc[primary.test=='P2','coverage']>=.8)&(primary.loc[primary.test=='P2','n']>=36)
 primary['verdict']=np.where(~primary.coverage_gate,'PARTIAL_IDENTIFICATION',np.where((primary['mean']>0)&(primary.holm_p<.05),'HISTORICAL_SUPPORT',np.where((primary['mean']<0)&(primary.holm_p<.05),'EVIDENCE_AGAINST','INCONCLUSIVE')))
 write(primary,'primary_tests.csv');write(pd.DataFrame(stats),'all_tests.csv')
 # Years and influence, never replace primary result.
 sensitivities=[]
 for test in ['P1','P3']:
  a=reg[(reg.horizon==10)&(reg.test==test)&(reg.exit_date<=END)&(reg.signal_date>=START)].set_index('signal_date').value.reindex(main_dates)
  for year in sorted(set(a.index.year)):
   for mode in ['year_only','leave_year_out']:
    s=a.copy();mask=s.index.year==year;s.loc[~mask if mode=='year_only' else mask]=np.nan;sensitivities.append(dict(test=test,mode=mode,year=year,**bootstrap(s,'W-FRI',13)))
  s=a.copy();s.loc[s.index.to_period('M').astype(str).isin(['2024-02','2022-05','2024-01'])]=np.nan;sensitivities.append(dict(test=test,mode='remove_known_top3',year='',**bootstrap(s,'W-FRI',13)))
 write(pd.DataFrame(sensitivities),'influence.csv')
 # State enrichment and returns; regression and portfolio evidence kept separate.
 main=scores[(scores.signal_date>=START)&(scores.signal_date<=END)].copy()
 enrich=main.groupby(['signal_date','state']).agg(n=('instrument','size'),q5=('raw_q5','sum')).reset_index();enrich['pool_share']=enrich.n/enrich.groupby('signal_date').n.transform('sum');enrich['q5_share']=enrich.q5/enrich.groupby('signal_date').q5.transform('sum');write(enrich,'state_enrichment.csv')
 sr=[]
 for h in [5,10,20]:
  a=main[main['exit'+str(h)]<=END]
  for (d,state),g in a.groupby(['signal_date','state']):sr.append(dict(signal_date=d,state=state,horizon=h,n=len(g),known=int(g['h'+str(h)].notna().sum()),mean_return=g['h'+str(h)].mean(),q5_return=g.loc[g.raw_q5,'h'+str(h)].mean()))
 write(pd.DataFrame(sr),'state_returns.csv')
 # Original wealth bridge: latest signal strictly before each daily contribution.
 ledger=pd.read_parquet(PRIVATE/'e1_return_attribution_20261117/daily_active_stock_industry.parquet')
 states=scores[['signal_date','instrument','state']]
 audit=pd.read_parquet(L/'universe_audit.parquet')[['signal_date','instrument']].merge(states,on=['signal_date','instrument'],how='left');audit.state=audit.state.fillna('UNKNOWN')
 attached=[]
 for code,a in ledger.groupby('instrument'):
  a=a.sort_values('date');b=audit[audit.instrument==code].sort_values('signal_date').drop(columns='instrument')
  if code.startswith('__'):a['state']=code;a['signal_date']=pd.NaT
  elif len(b):a=pd.merge_asof(a,b,left_on='date',right_on='signal_date',direction='backward',allow_exact_matches=False);a.state=a.state.fillna('UNKNOWN')
  else:a['state']='UNKNOWN';a['signal_date']=pd.NaT
  attached.append(a)
 attr=pd.concat(attached);write(attr,'state_daily_attribution.parquet',True)
 summary=attr.groupby('state',as_index=False)[['log_contribution','wealth_contribution']].sum();assert np.isclose(summary.wealth_contribution.sum(),ledger.wealth_contribution.sum(),atol=1e-10);write(summary,'state_wealth_bridge.csv');write(attr.groupby(['month','state'],as_index=False).wealth_contribution.sum(),'state_month_contributions.csv')
 cases=attr[~attr.instrument.str.startswith('__')].groupby(['instrument','signal_date','state'],dropna=False,as_index=False).wealth_contribution.sum();write(cases,'all_case_events.csv');top=cases.nlargest(5,'wealth_contribution');bottom=cases.nsmallest(5,'wealth_contribution');other=cases.drop(top.index.union(bottom.index));random=other.sample(min(10,len(other)),random_state=20261117);write(pd.concat([top.assign(case='top5'),bottom.assign(case='bottom5'),random.assign(case='random10')]),'case_examples.csv')
 # Matched original Q5 gross fixed-event outcomes, explicit missing controls.
 pairs=pd.read_csv(D/'matched_pairs.csv',parse_dates=['signal_date']);labels=scores[['signal_date','instrument','h10','exit10']];pairs=pairs.merge(labels,on=['signal_date','instrument'],how='left').merge(labels.rename(columns={'instrument':'control','h10':'control_h10','exit10':'control_exit10'}),on=['signal_date','control'],how='left');pairs['difference']=pairs.h10-pairs.control_h10;write(pairs,'matched_outcomes.csv')
 # Prior market state only. benchmark file has longer raw history than attribution period.
 body=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data'];market=pd.DataFrame(body['items'],columns=body['fields']);market['date']=pd.to_datetime(market.trade_date);market=market.set_index('date').close.sort_index();ret=market.pct_change(fill_method=None);vol=ret.rolling(20).std(ddof=0);threshold=vol.shift(1).rolling(252).median();mom=market/market.shift(20)-1
 regime=pd.DataFrame({'market_mom20':mom,'market_vol20':vol,'past_vol_median':threshold}).reindex(dates);regime['regime']=np.where(regime.notna().all(axis=1),np.where(regime.market_mom20>0,'UP','DOWN')+'_'+np.where(regime.market_vol20>regime.past_vol_median,'HIGHVOL','LOWVOL'),'UNKNOWN');regime.index.name='signal_date';write(regime.reset_index(),'market_regimes.csv')
 paths=pd.read_csv(D/'paths.csv',parse_dates=['signal_date']);pathrows=[]
 for (date,strategy),a in paths.groupby(['signal_date','strategy']):
  w=a.set_index('horizon').mark
  ev=events[(events.signal_date==date)&(events.strategy==strategy)&(events.cost=='main')&(events.horizon==20)]
  if len(ev):
   fee=ev.exit_fees.iloc[0];pathrows.append(dict(signal_date=date,strategy=strategy,exit_date=ev.exit_date.iloc[0],first5=w.get(5,np.nan)-1,next5=w.get(10,np.nan)-w.get(5,np.nan),last10=w.get(20,np.nan)-w.get(10,np.nan)-fee,net20=ev.net_return.iloc[0],reason=ev.reason.iloc[0]))
 pathdf=pd.DataFrame(pathrows);known=pathdf.net20.notna();assert np.allclose(pathdf.loc[known,['first5','next5','last10']].sum(axis=1),pathdf.loc[known,'net20'],atol=1e-10);write(pathdf,'marginal_paths.csv')
 delayed=pd.read_csv(D/'delayed_events.csv',parse_dates=['signal_date','execution_signal','exit_date']);timing=[]
 for _,a in delayed[delayed.horizon==10].iterrows():
  now=events[(events.signal_date==a.signal_date)&(events.strategy==a.strategy)&(events.horizon==10)&(events.cost=='main')];fresh=events[(events.signal_date==a.execution_signal)&(events.strategy==a.strategy)&(events.horizon==10)&(events.cost=='main')]
  timing.append(dict(signal_date=a.signal_date,strategy=a.strategy,exit_date=a.exit_date,immediate=now.net_return.iloc[0] if len(now) else np.nan,delayed=a.net_return,fresh=fresh.net_return.iloc[0] if len(fresh) else np.nan))
 timing=pd.DataFrame(timing);timing['immediate_minus_delayed']=timing.immediate-timing.delayed;timing['fresh_minus_delayed']=timing.fresh-timing.delayed;write(timing,'timing_comparisons.csv')
 e=events[(events.horizon==10)&(events.cost=='main')&(events.exit_date<=END)].copy();e=e.merge(regime.reset_index(),on='signal_date',how='left');write(e.groupby(['strategy','phase','regime']).net_return.agg(['count','mean']).reset_index(),'regime_events.csv')
 # Per-replicate placebo differences; seeds are not independent time observations.
 placebo=[]
 for phase in [1,2]:
  a=e[e.phase==phase].pivot(index='signal_date',columns='strategy',values='net_return')
  for c in [s for s in a if s.startswith('P')]:
   for strategy in ['B','J','E1']:
    s=a[strategy]-a[c];placebo.append(dict(phase=phase,replicate=c,strategy=strategy,n=int(s.notna().sum()),mean=s.mean()))
 write(pd.DataFrame(placebo),'placebo_comparisons.csv')
 # Independent accounts; benchmark and B compared over same daily interval.
 metrics=[];periodrows=[];riskrows=[]
 for strategy in ['B','J','E1']:
  for cost in COSTS:
   key=strategy+'_'+cost;a=pd.read_csv(D/'accounts'/(key+'.csv'),parse_dates=['date']).set_index('date');orders=pd.read_parquet(L/'orders'/(key+'.parquet'))
   for scope in ['primary','extended']:
    d=a.loc[:END] if scope=='primary' else a;nav=d.nav;n=len(d);b=benchmark(d.index);base=pd.read_csv(D/'accounts'/('B_'+cost+'.csv'),parse_dates=['date']).set_index('date').nav.reindex(d.index);r=nav.pct_change(fill_method=None);r.iloc[0]=nav.iloc[0]-1;br=b.pct_change(fill_method=None);br.iloc[0]=b.iloc[0]-1;ar=base.pct_change(fill_method=None);ar.iloc[0]=base.iloc[0]-1;relative=nav/base;prev=nav.shift(fill_value=1)
    metrics.append(dict(strategy=strategy,cost=cost,scope=scope,days=n,end=str(d.index[-1].date()),cagr=float(nav.iloc[-1]**(252/n)-1),end_nav=nav.iloc[-1],benchmark_cagr=float(b.iloc[-1]**(252/n)-1),mean_active_B=float((r-ar).mean()*252),tracking_error_B=float((r-ar).std(ddof=1)*np.sqrt(252)),relative_drawdown_B=float((relative/relative.cummax().clip(lower=1)-1).min()),annual_oneway_turnover=float(((d.buy+d.sell)/(2*prev)).sum()*252/n),fees=float(d.fees.sum()),average_cash=float(d.cash_weight.mean())))
    for freq in ['Y','M']:
     for period,rr in r.groupby(r.index.to_period(freq)):periodrows.append(dict(strategy=strategy,cost=cost,scope=scope,frequency=freq,period=str(period),own=float((1+rr).prod()-1),B=float((1+ar.reindex(rr.index)).prod()-1),index=float((1+br.reindex(rr.index)).prod()-1)))
   # Actual daily close exposures versus B targets at the same latest scheduled signal.
   from backtest import Inputs
   # Load price panel once; units unchanged between order dates.
   close=pd.read_parquet(PRIVATE/'qfq_close.parquet')
   holdings=orders.pivot(index='date',columns='instrument',values='units_after').fillna(0).reindex(a.index).ffill().fillna(0)
   latest=pd.Series(orders.groupby('date').signal_date.first()).reindex(a.index).ffill()
   for date,units in holdings.iterrows():
    sd=latest.loc[date]
    if pd.isna(sd):continue
    panel=scores[scores.signal_date==sd].set_index('instrument');bt=targets_for_date(sd,'B');names=units.index[units>0];weights=units.loc[names]*close.loc[date,names]/a.loc[date,'nav'];known=names.intersection(panel.index);unknown=float(weights.loc[names.difference(known)].sum());target=bt.set_index('instrument').weight
    if len(bt):
     zz=panel[['z_'+s for s in STYLES]];actual=zz.reindex(known).mul(weights.reindex(known),axis=0).sum();desired=zz.reindex(target.index).mul(target,axis=0).sum();gap=float(abs(actual-desired).max())
     riskrows.append(dict(strategy=strategy,cost=cost,date=date,signal_date=sd,unknown_weight=unknown,cash=a.loc[date,'cash_weight'],max_style_gap=gap,complete=unknown<1e-12))
 write(pd.DataFrame(metrics),'account_metrics.csv');write(pd.DataFrame(periodrows),'account_periods.csv');write(pd.DataFrame(riskrows),'actual_daily_risk.csv')
 # Power is planning approximation, not evidence of achieved power.
 p2=primary[primary.test=='P2'].iloc[0];power=[]
 sd=p2.get('bootstrap_sd',np.nan)
 for m in [24,36]:power.append(dict(months=m,approximate_min_detectable_event_return=float((norm.ppf(1-.05/6)+norm.ppf(.8))*sd*np.sqrt(p2.n/m)),assumed_power=.8,method='normal approximation, Bonferroni conservative planning alpha, historical block mean SD scaled sqrt(n/months); dependence stationary assumption'))
 save_json(D/'forward_registration.json',dict(status='FORWARD_PENDING',model_status='FORWARD_BLOCKED_MODEL',data_status='FORWARD_BLOCKED_DATA_REFRESH',reason='sealed local historical panel ends 2026-10-21; no verified live signal pipeline or scheduler installed',proposed_first_signal='2026-12-04 after November implementation freeze, subject to actual data receipt and completed trading week; not yet generated',observation_start='2026-12-01',observation_end='2029-11-30',descriptive_review_after='2028-11-30',formal_review='after 2029-11-30 and final H20 maturity',signal_timestamp_required=True,automatic_execution=False,power=power))
 save_json(D/'analysis_complete.json',dict(status='COMPLETE_HISTORICAL_PROXY',files=records(list(D.glob('*.csv'))+[D/'forward_registration.json',L/'state_daily_attribution.parquet']),state_bridge_total=float(summary.wealth_contribution.sum()),primary=primary.to_dict('records')))
 print(primary.to_string(index=False),flush=True)

def targets_for_date(date,strategy):
 global _targets
 if '_targets' not in globals():_targets=pd.read_parquet(L/'targets.parquet')
 return _targets[(_targets.signal_date==date)&(_targets.strategy==strategy)]

if __name__=='__main__':
 if sys.argv[1]=='register':save_json(D/'analysis_registration.json',dict(files=records([Path(__file__)]),new_outcomes_seen=False))
 else:analyze()
