"""Account metrics separate completed horizons, valid prefixes, and benchmark semantics."""
from pathlib import Path
import json,numpy as np,pandas as pd
from common import *
from evaluate_ranking import block_ci,predictions

def returns(nav):
 r=nav.pct_change(fill_method=None);r.iloc[0]=nav.iloc[0]-1;return r

def metrics(nav,bench):
 r=returns(nav);br=returns(bench);rel=nav/bench;active=r-br;T=len(nav)
 cagr=nav.iloc[-1]**(252/T)-1;bcagr=bench.iloc[-1]**(252/T)-1
 peak=np.maximum.accumulate(np.r_[1.,nav]);dd=np.min(np.r_[1.,nav]/peak-1)
 relpeak=np.maximum.accumulate(np.r_[1.,rel]);rdd=np.min(np.r_[1.,rel]/relpeak-1)
 lo,hi=block_ci(active.to_numpy(),L=65)
 return dict(total_return=nav.iloc[-1]-1,cagr=cagr,max_drawdown=dd,benchmark_cagr=bcagr,cagr_difference=cagr-bcagr,relative_nav_cagr=rel.iloc[-1]**(252/T)-1,relative_max_drawdown=rdd,tracking_error=active.std(ddof=1)*np.sqrt(252),information_ratio=active.mean()/active.std(ddof=1)*np.sqrt(252) if active.std()>0 else np.nan,annualized_arithmetic_active=active.mean()*252,active_ci_low=lo*252,active_ci_high=hi*252)

def main():
 market=pd.read_parquet(PRIVATE/'market.parquet');records=[];annual=[];quarterly=[];fail=[]
 for p in sorted((OUT/'accounts').glob('*.csv')):
  f=pd.read_csv(p,parse_dates=['date']);key=p.stem;receipt=json.loads((OUT/'manifests'/(key+'.json')).read_text());fail.extend(receipt['failures'])
  scheme,scenario,path,model,cost=key.split('_');r=dict(account=key,scheme=scheme,scenario=scenario,path=path,model=model,cost=cost,days=len(f),completed=receipt['completed_to_data_end'],failure_reason=receipt['failures'][0]['reason'] if receipt['failures'] else '',failure_date=receipt['failures'][0]['date'] if receipt['failures'] else '',quality='historical_proxy')
  if not len(f):records.append(r);continue
  f=f.set_index('date');nav=f.nav;r.update(start=f.index.min(),end=f.index.max(),turnover_buys=f.buy.sum(),turnover_sells=f.sell.sum(),total_fees=f.fees.sum(),mean_cash=f.cash_weight.mean(),mean_holdings=f.holdings.mean(),skipped_B_targets=int(f.target_status.fillna('').str.contains('UNKNOWN|MISMATCH|OUTSIDE').sum()),constraint_relaxations=int(f.relaxed.fillna(False).astype(bool).sum()))
  for k in ['actual_active_share','actual_max_stock_deviation','actual_max_industry_deviation','unknown_state_weight','legacy_weight']:
   r[k+'_max']=f[k].max() if k in f else np.nan
  official=market.reindex(f.index).close/market.loc[f.index[0],'open'];z=metrics(nav,official);r['full_available_account_cagr']=z['cagr'];r['full_available_account_total_return']=z['total_return'];r['first_actual_buy']=f.loc[f.buy.gt(0)].index.min();r.update({'price_index_diagnostic_'+k:v for k,v in z.items()})
  # Benchmark a separately run, zero-cost account with exactly the same execution clock.
  baseline='EW' if path=='A' else 'B0';bp=OUT/'accounts'/f'{scheme}_{scenario}_{path}_{baseline}_zero.csv'
  bf=pd.read_csv(bp,parse_dates=['date']).set_index('date');ix=nav.index.intersection(bf.index);bm=bf.nav.reindex(ix)
  # No silent extension of a baseline after its own valuation failure.
  r['matched_benchmark']=baseline+'_zero';r['matched_days']=len(ix);r['matched_full_prefix']=len(ix)==len(nav)
  if len(ix):r.update(metrics(nav.loc[ix],bm))
  for freq,table in [('Y',annual),('Q',quarterly)]:
   nr=returns(nav);pr=returns(official)
   for period,part in nr.groupby(nr.index.to_period(freq)):
    ids=part.index;bn=pr.loc[ids];a=dict(account=key,scheme=scheme,scenario=scenario,path=path,model=model,cost=cost,period=str(period),days=len(part),portfolio_return=float((1+part).prod()-1),price_index_diagnostic_return=float((1+bn).prod()-1),prefix_only=not receipt['completed_to_data_end'],calendar_period_complete=period.end_time.normalize()<=market.index.max(),observed_start=ids.min(),observed_end=ids.max())
    bix=ids.intersection(bf.index)
    if len(bix)==len(ids):
     bret=returns(bf.nav).reindex(ids);a['matched_return']=float((1+bret).prod()-1);a['relative_return']=(1+a['portfolio_return'])/(1+a['matched_return'])-1
    table.append(a)
  records.append(r)
 pd.DataFrame(records).to_csv(OUT/'account_metrics.csv',index=False)
 for tab,name,freq in [(annual,'annual_performance','Y'),(quarterly,'quarterly_performance','Q')]:
  present={(a['account'],a['period']) for a in tab}
  for r in records:
   for period in pd.period_range('2021-01-01','2026-10-21',freq=freq):
    if (r['account'],str(period)) not in present:tab.append({**{k:r[k] for k in ['account','scheme','scenario','path','model','cost']},'period':str(period),'days':0,'status':'BLOCKED_AFTER_'+str(r['failure_date']),'prefix_only':True})
  pd.DataFrame(tab).to_csv(OUT/(name+'.csv'),index=False)
 pd.DataFrame(fail).to_csv(OUT/'data_audit/account_valuation_failures.csv',index=False)
 # Main ranking table with full-horizon net certification status kept separate.
 rk=pd.read_csv(OUT/'path_a/expanding_ranking_summary.csv');rk=rk.loc[rk.horizon.eq('h10')&rk.seed.isin(['fixed','equal_seed_ensemble'])].set_index('model');ac=pd.DataFrame(records);comp=rk.copy()
 for path in ['A','B']:
  q=ac.loc[ac.scheme.eq('expanding')&ac.scenario.eq('weekly')&ac.path.eq(path)&ac.cost.eq('main')].set_index('model')
  for col in ['completed','failure_date','failure_reason','cagr','relative_nav_cagr','information_ratio','days','matched_days','skipped_B_targets']:
   comp[path+'_'+col]=q[col] if col in q else np.nan
  comp[path+'_valid_prefix_cagr']=comp[path+'_cagr'];comp[path+'_valid_prefix_relative_nav_cagr']=comp[path+'_relative_nav_cagr']
  comp.loc[~comp[path+'_completed'].fillna(False),[path+'_cagr',path+'_relative_nav_cagr',path+'_information_ratio']]=np.nan
  comp[path+'_full_horizon_net_certified']=False
  comp[path+'_valid_prefix_only']=~comp[path+'_completed'].fillna(False)
 comp['B_formal_status']='BLOCKED_PIT_WEIGHTS_AND_MATCHED_TOTAL_RETURN';comp.to_csv(OUT/'model_comparison.csv')
 paired=[]
 for scheme in ['expanding','rolling36']:
  d=pd.read_csv(OUT/'path_a'/f'{scheme}_ranking_weekly.csv');d=d.loc[d.horizon.eq('h10')&d.seed.isin(['fixed','equal_seed_ensemble'])]
  wide=d.pivot(index='signal_date',columns='model',values='rank_ic')
  for other in ['E0-MOM','E0-REV','E0-RES','E0-MIX','E1','E3']:
   x=(wide.E2-wide[other]).dropna();lo,hi=block_ci(x)
   paired.append(dict(scheme=scheme,comparison='E2_minus_'+other,paired_weeks=len(x),mean_delta_rank_ic=x.mean(),ci_low=lo,ci_high=hi))
  # Missingness sensitivity: retain dates with complete outcome coverage among scored securities.
  for model,g in d.groupby('model'):
   allx=g.rank_ic.dropna();clean=g.loc[g.unknown_labels.eq(0),'rank_ic'].dropna();lo,hi=block_ci(clean)
   paired.append(dict(scheme=scheme,comparison=model+'_complete_label_dates',paired_weeks=len(clean),mean_delta_rank_ic=clean.mean()-allx.mean(),mean_rank_ic=clean.mean(),ci_low=lo,ci_high=hi))
 (OUT/'sensitivity').mkdir(exist_ok=True);pd.DataFrame(paired).to_csv(OUT/'sensitivity/paired_and_missingness.csv',index=False)
 print('summary accounts',len(records),'valuation-blocked',len(fail),flush=True)
if __name__=='__main__':main()
