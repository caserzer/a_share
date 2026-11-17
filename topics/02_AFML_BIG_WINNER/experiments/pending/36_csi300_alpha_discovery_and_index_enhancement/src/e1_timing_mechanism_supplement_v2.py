"""Pre-result auxiliary diagnostics and audit receipts; no new selection or tolerances."""
import sys,json
import numpy as np
import pandas as pd
from e1_timing_mechanism_evaluate_v2 import *

def supplement_freeze():
 assert not (D/'supplement_freeze.json').exists()
 save_json(D/'supplement_freeze.json',dict(created_at=datetime.now(timezone.utc).isoformat(),source_sha256=sha(__file__),new_results_seen=False,analyses=['selected-holding residual rank association within fixed states and matched tiers, conditional on fixed trend/REV','industry-relative signs auxiliary, no selection change','entry to5,5to10,10to20 on joint marked sample','residual missing coverage in original ledger','largest contributions and yearly/monthly concentration descriptive']))

def supplement():
 assert sha(__file__)==json.loads((D/'supplement_freeze.json').read_text())['source_sha256'];verify(True)
 s=pd.read_parquet(L/'states.parquet');m=pd.read_csv(D/'residual_matches.csv',parse_dates=['signal_date']);grid=pd.DatetimeIndex(pd.read_csv(D/'schedule.csv',parse_dates=['signal_date']).signal_date)
 m=m.merge(s[['signal_date','instrument','trend','REV']],on=['signal_date','instrument'],how='left',validate='many_to_one');rows=[]
 for (tier,st),h in m.groupby(['tier','state']):
  for outcome in ['immediate_excess','date_gap_excess']:
   values=[]
   for date,g in h.groupby('signal_date'):
    g=g.dropna(subset=['score_residual',outcome,'trend','REV']);plain=conditional=np.nan
    if len(g)>=10 and g[outcome].std(ddof=0)>1e-12 and g.score_residual.std(ddof=0)>1e-12:
     plain=rankcorr(g.score_residual,g[outcome]);x=np.column_stack([np.ones(len(g)),g[['trend','REV']].rank(pct=True)])
     _,rx,_,rank=project(x,g.score_residual.rank().to_numpy());_,ry,_,_=project(x,g[outcome].rank().to_numpy());conditional=float(np.corrcoef(rx,ry)[0,1]) if len(g)-rank>=5 else np.nan
    values.append(dict(signal_date=date,n=len(g),plain=plain,conditional=conditional))
   v=pd.DataFrame(values).set_index('signal_date')
   for metric in ['plain','conditional']:rows.append(dict(tier=tier,state=st,outcome=outcome,metric=metric,mean_known_stocks=v.n.mean(),**stats(v[metric].reindex(grid))))
 dump(pd.DataFrame(rows),'selected_residual_association')
 # No return-based classification: industry median of signal-time original scored universe.
 scored=s[s.E1.notna()&s.industry.ne('UNKNOWN')];med=scored.groupby(['signal_date','industry'])[['trend','short']].median().rename(columns={'trend':'industry_trend','short':'industry_short'})
 ss=s.merge(med,on=['signal_date','industry'],how='left');ss['relative_state']=state(ss.trend-ss.industry_trend,ss.short-ss.industry_short)
 ledger=pd.read_parquet(L/'ledger_detail.parquet');ledger=ledger.merge(ss[['signal_date','instrument','relative_state','score_residual']],on=['signal_date','instrument'],how='left',validate='many_to_one');ledger['relative_state']=ledger.relative_state.fillna('UNKNOWN');ledger.loc[ledger.instrument.str.startswith('__'),'relative_state']=ledger.instrument
 dump(ledger.groupby('relative_state',as_index=False)[['wealth_contribution','absolute_cash_pnl_per100','capital_days']].sum(),'industry_relative_state')
 ledger['residual_status']=np.where(ledger.score_residual.notna(),'SCORABLE','UNSCORABLE');ledger.loc[ledger.instrument.str.startswith('__'),'residual_status']=ledger.instrument
 dump(ledger.groupby(['state','residual_status'],as_index=False)[['wealth_contribution','absolute_cash_pnl_per100','capital_days']].sum(),'ledger_residual_coverage')
 p=pd.read_csv(D/'event_paths.csv',parse_dates=['signal_date']);curve=p[p.age.notna()&p.delay.eq('immediate')].pivot(index='signal_date',columns='age',values='mark');valid=curve[[0,5,10,20]].notna().all(axis=1);rows=[]
 for label,lo,hi in [('entry_to5',None,5),('5to10',5,10),('10to20',10,20)]:
  v=curve[hi] if lo is None else curve[hi]-curve[lo];rows.append(dict(segment=label,**stats(v.where(valid).reindex(grid))))
 dump(pd.DataFrame(rows),'marginal_marked_segments')
 seg=p[p.state.notna()];rows=[]
 for (delay,h,st),g in seg.groupby(['delay','horizon','state']):
  for metric in ['early','shared','delayed_entry_fees','gap']:rows.append(dict(delay=delay,horizon=h,state=st,metric=metric,**stats(g.set_index('signal_date')[metric].reindex(grid))))
 dump(pd.DataFrame(rows),'segment_state_summary')
 # Joint-sample state immediate and delayed means, avoiding separate-sample means in display.
 e=pd.read_csv(D/'event_states.csv',parse_dates=['signal_date']);rows=[]
 for (clock,h,st),g in e[e.cost.eq('main')].groupby(['clock','horizon','state']):
  pp=g.pivot(index='signal_date',columns='delay',values='net');valid=pp[['immediate','phase2']].notna().all(axis=1)
  rows.append(dict(clock=clock,horizon=h,state=st,n=int(valid.sum()),immediate_paired_mean=pp.loc[valid,'immediate'].mean(),delayed_paired_mean=pp.loc[valid,'phase2'].mean()))
 dump(pd.DataFrame(rows),'paired_state_means')
 # Explicit execution/maturity coverage, rather than silently removing failures.
 ev=pd.read_csv(D/'events.csv');dump(ev.groupby(['cost','clock','horizon','delay','reason'],dropna=False).size().rename('events').reset_index(),'event_coverage')
 print('supplement done',flush=True)

if __name__=='__main__':globals()[sys.argv[1]]()
