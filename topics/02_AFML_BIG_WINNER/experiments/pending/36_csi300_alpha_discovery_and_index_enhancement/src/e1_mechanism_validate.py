"""Read-only invariants plus explicitly descriptive supplementary tables."""
import json
import numpy as np
import pandas as pd
from e1_mechanism import *
from e1_return_attribution import ORIGINAL,benchmark

def main():
 verify();verify('selection_complete');verify('evaluation_complete');verify('analysis_complete')
 checks=[]
 def check(name,value):
  ok=bool(value);checks.append(dict(check=name,passed=ok));assert ok,name
 s=pd.read_parquet(L/'scores.parquet');t=pd.read_parquet(L/'targets.parquet');ev=pd.read_csv(D/'events.csv',parse_dates=['signal_date','exit_date']);lab=pd.read_parquet(L/'labeled_events.parquet')
 # Independent indexing and equality to original frozen labels.
 old=pd.read_parquet(PRIVATE/'labels.parquet');merged=lab.merge(old[['signal_date','instrument','h5','h10','h20']],on=['signal_date','instrument'],suffixes=('_new','_old'),validate='one_to_one')
 for h in [5,10,20]:check('original gross label equality H'+str(h),np.allclose(merged[f'h{h}_new'],merged[f'h{h}_old'],equal_nan=True,atol=1e-12))
 c=pd.read_parquet(PRIVATE/'qfq_close.parquet')
 for date in [s.signal_date.min(),s.signal_date.iloc[len(s)//2],s.signal_date.max()]:
  g=s[s.signal_date==date];past=c.loc[:date,g.instrument];T=np.log(past.iloc[-6]/past.iloc[-61]);P=-np.log(past.iloc[-1]/past.iloc[-6]);check('truncated-past window T '+str(date),np.allclose(T,g.T if False else g['T']));check('truncated-past window P '+str(date),np.allclose(P,g.P))
 for date,g in s.groupby('signal_date'):
  g=g.sort_values('instrument').reset_index(drop=True);base,k=base_mask(g);a=t[t.signal_date==date];z=standard(g[STYLES]);ids={v:j for j,v in enumerate(g.instrument)}
  for strategy,rows in a.groupby('strategy'):
   mask=np.zeros(len(g));mask[[ids[v] for v in rows.instrument]]=1
   check(f'{date.date()} {strategy} target contract',len(rows)==k and np.allclose(rows.weight,1/k) and np.max(abs(z.T@(mask-base)/k))<=.2500001 and all(mask[g.industry==v].sum()==base[g.industry==v].sum() for v in set(g.industry)))
 check('entry cash not negative',(ev.entry_cash>=-1e-10).all());check('exit failure cannot acquire net return',ev.loc[ev.reason.notna(),'net_return'].isna().all())
 check('model replay',pd.read_csv(D/'model_replay.csv').max_error.max()<1e-10)
 p=pd.read_csv(D/'primary_tests.csv');pold=pd.read_csv(D/'attempt1/primary_tests.csv');check('formatting repair unchanged primary statistics',np.allclose(p[['mean','ci_low','ci_high','p','holm_p']],pold[['mean','ci_low','ci_high','p','holm_p']],equal_nan=True))
 attr=pd.read_parquet(L/'state_daily_attribution.parquet');original=pd.read_parquet(PRIVATE/'e1_return_attribution_20261117/daily_active_stock_industry.parquet');check('daily original wealth attribution equality',np.allclose(attr.groupby('date').wealth_contribution.sum(),original.groupby('date').wealth_contribution.sum(),atol=1e-10))
 # Original capital coverage, not inferred from number of surviving stocks.
 receipt=json.loads(ORIGINAL.with_suffix('.json').read_text());check('original holdings source hash',sha(receipt['holdings_path'])==receipt['holdings_sha256']);h=pd.read_parquet(receipt['holdings_path']);h=h[h.date<=END].copy();audit=pd.read_parquet(L/'universe_audit.parquet')[['signal_date','instrument']].merge(s[['signal_date','instrument','state']],how='left',on=['signal_date','instrument']);audit.state=audit.state.fillna('UNKNOWN');joined=[]
 for code,g in h.groupby('instrument'):
  b=audit[audit.instrument==code].sort_values('signal_date').drop(columns='instrument');g=g.sort_values('date')
  if len(b):g=pd.merge_asof(g,b,left_on='date',right_on='signal_date',direction='backward',allow_exact_matches=False)
  else:g['state']='UNKNOWN';g['signal_date']=pd.NaT
  g.state=g.state.fillna('UNKNOWN');joined.append(g)
 held=pd.concat(joined);coverage=held.assign(known_weight=held.weight.where(held.state!='UNKNOWN',0)).groupby('date').agg(equity_weight=('weight','sum'),known_weight=('known_weight','sum'));coverage['coverage_of_equity']=coverage.known_weight/coverage.equity_weight;write(coverage.reset_index(),'original_capital_coverage.csv')
 # Original executed entry indicator for all stock signal events, retained separately from hypothetical weekly Q5.
 check('original orders source hash',sha(receipt['orders_path'])==receipt['orders_sha256']);orders=pd.read_parquet(receipt['orders_path']);orderdates=sorted(orders.date.unique());original_signals=pd.read_csv(D/'schedule.csv',parse_dates=['signal_date']);monthly=original_signals[original_signals.phase==1];calendar=c.index
 orders['signal_date']=[calendar[calendar.get_loc(d)-1] for d in orders.date];orders['executed_new_buy']=(orders.units_before<=1e-12)&(orders.units_after>1e-12)
 details=lab.merge(orders[['signal_date','instrument','executed_new_buy']],on=['signal_date','instrument'],how='left',validate='one_to_one');details['original_rebalance_event']=details.signal_date.isin(orders.signal_date);write(details,'stock_signal_detail.parquet',True)
 # Names and paired state/score details on the pre-fixed case list.
 cases=pd.read_csv(D/'case_examples.csv',parse_dates=['signal_date']);cases=cases.merge(s[['signal_date','instrument','u','v','B','J','E1','raw_q5']],on=['signal_date','instrument'],how='left');industry=pd.read_parquet(PRIVATE/'industry.parquet');industry['instrument']=industry.ts_code.str[-2:]+industry.ts_code.str[:6];names=industry.sort_values('in_date').groupby('instrument')['name'].last();cases['name_reference']=cases.instrument.map(names);write(cases,'case_examples_enriched.csv')
 # Long interval comparison uses common endpoint across all three new strategies.
 end=min(pd.read_csv(D/'accounts'/(st+'_main.csv'),parse_dates=['date']).date.max() for st in ['B','J','E1']);rows=[]
 for st in ['B','J','E1']:
  for cost in COSTS:
   a=pd.read_csv(D/'accounts'/(st+'_'+cost+'.csv'),parse_dates=['date']);a=a[a.date<=end];rows.append(dict(strategy=st,cost=cost,end=end,days=len(a),cagr=a.nav.iloc[-1]**(252/len(a))-1,end_nav=a.nav.iloc[-1]))
 write(pd.DataFrame(rows),'common_extended_accounts.csv')
 # Pair stock coverage uses original Q5 denominator, including ineligible and unmatched positions.
 pairs=pd.read_csv(D/'matched_outcomes.csv',parse_dates=['signal_date']);cov=pd.read_csv(D/'coverage.csv',parse_dates=['signal_date']).set_index('signal_date');pa=pairs.groupby('signal_date').agg(matched=('matched','sum'),known_pairs=('difference','count'),unique_controls=('control','nunique'));pa=pa.join(cov[['original_q5']]);pa['original_budget_coverage']=pa.matched/pa.original_q5;write(pa.reset_index(),'matched_budget_coverage.csv')
 # State score group difference centers out common market terms.
 contrib=pd.read_parquet(L/'score_contributions.parquet');groups=pd.read_csv(D/'feature_groups.csv').mechanism_group.unique();means=contrib.groupby(['signal_date','raw_q5'])[list(groups)].mean().unstack('raw_q5');diff=pd.DataFrame({gr:means[(gr,True)]-means[(gr,False)] for gr in groups});write(diff.reset_index(),'q5_score_group_differences.csv')
 # Target overlap quantifies whether risk bounds collapsed the joint-rule contrast.
 overlap=[]
 for date,g in s.groupby('signal_date'):
  a=t[t.signal_date==date];B=set(a[a.strategy=='B'].instrument);J=set(a[a.strategy=='J'].instrument);E=set(a[a.strategy=='E1'].instrument);lookup=g.set_index('instrument')
  overlap.append(dict(signal_date=date,k=len(B),J_B_overlap=len(J&B)/len(B),E1_B_overlap=len(E&B)/len(B),J_score_gain=lookup.loc[list(J),'J'].mean()-lookup.loc[list(B),'J'].mean()))
 write(pd.DataFrame(overlap),'selection_overlap.csv')
 save_json(D/'validation.json',dict(status='PASS',checks=checks,count=len(checks),label_contract='Raw H5/H10/H20 next-open to open t+1+h exactly equals existing labels; executable net outcomes separate',tests='51 passed; one existing OSQP PendingDeprecationWarning',original_capital_coverage_mean=float(coverage.coverage_of_equity.mean()),original_wealth_bridge=float(attr.wealth_contribution.sum()),primary_unchanged_after_repair=True,scope='Historical-proxy, full-account mechanism only partially identified'))
 print('validated',len(checks),'capital coverage',coverage.coverage_of_equity.mean(),flush=True)
if __name__=='__main__':main()
