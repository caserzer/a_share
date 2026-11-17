"""Target, full daily holdings, and daily account validation for bridge."""
from e1_advantage_bridge import *

def main():
 verify();verify('selection_complete');verify('accounts_complete');verify('analysis_complete');checks=[]
 def check(name,ok):assert bool(ok),name;checks.append(dict(name=name,passed=True))
 inp=Inputs();marks(inp,0.);targets=pd.read_parquet(L/'targets.parquet');scores=pd.read_parquet(PRIVATE/OLD/'scores.parquet');prev=pd.read_parquet(PRIVATE/OLD/'targets.parquet');audit=pd.read_csv(D/'selection_audit.csv',parse_dates=['signal_date']).set_index('signal_date');actual=[]
 for date,t in targets.groupby('signal_date'):
  g=scores[scores.signal_date==date].sort_values('instrument').set_index('instrument');oldk=int(audit.loc[date,'original_k']);k=int(audit.loc[date,'new_k']);base=prev[(prev.signal_date==date)&(prev.strategy=='B')].set_index('instrument').weight;z=pd.DataFrame(standard(g[STYLES]),index=g.index,columns=STYLES)
  for st,r in t.groupby('strategy'):
   w=r.set_index('instrument').weight
   if st!='X':check(str(date)+st+' unit budget',np.isclose(w.sum(),1))
   if st in ['U','UI']:check(str(date)+st+' original k',len(w)==oldk)
   if st in ['K','I','F','KF']:check(str(date)+st+' new k',len(w)==k)
   if st not in ['O']:check(str(date)+st+' subset C',w.index.isin(g.index).all())
   if st in ['I','F','UI']:
    q=quotas(g.reset_index(),len(w));counts=g.loc[w.index].industry.value_counts().reindex(q.index,fill_value=0);check(str(date)+st+' industry slots',np.array_equal(q,counts))
   if st in ['F','KF']:
    delta=z.reindex(w.index).mul(w,axis=0).sum()-z.reindex(base.index).mul(base,axis=0).sum();check(str(date)+st+' risk bounds',abs(delta).max()<=.2500001)
  check(str(date)+' X retains original weights',np.allclose(t[t.strategy=='X'].set_index('instrument').weight,t[t.strategy=='O'].set_index('instrument').weight.reindex(t[t.strategy=='X'].instrument)))
 for path in (D/'accounts').glob('*.csv'):
  st=path.stem;a=pd.read_csv(path,parse_dates=['date']).set_index('date');o=pd.read_parquet(L/'orders'/(st+'.parquet'));units=o.pivot(index='date',columns='instrument',values='units_after').reindex(a.index).ffill().fillna(0);price=pd.DataFrame(inp.c,index=inp.days,columns=inp.symbols).reindex(index=a.index,columns=units.columns);values=(units*price).where(units>0,0)
  check(st+' holdings plus cash NAV',np.allclose(values.sum(axis=1),a.nav*(1-a.cash_weight),atol=1e-11));h=units.where(units>0).stack().rename('units').reset_index();h['price']=price.stack().reindex(pd.MultiIndex.from_frame(h[['date','instrument']])).to_numpy();h['weight']=h.units*h.price/h.date.map(a.nav);write(h,'holdings/'+st+'.parquet',True)
  check(st+' finite held prices',np.isfinite(h.price).all())
  for d,r in o.groupby('date'):
   sd=r.signal_date.iloc[0];g=scores[scores.signal_date==sd].set_index('instrument');w=r.set_index('instrument').actual_weight;known=w.index.intersection(g.index);unknown=float(w.loc[w.index.difference(known)].sum());z=pd.DataFrame(standard(g[STYLES]),index=g.index,columns=STYLES);base=prev[(prev.signal_date==sd)&(prev.strategy=='B')].set_index('instrument').weight;gap=(z.loc[known].mul(w.reindex(known),axis=0).sum()-z.reindex(base.index).mul(base,axis=0).sum()).abs().max();actual.append(dict(strategy=st,date=d,signal_date=sd,unknown_style_weight=unknown,max_style_gap_vs_B=gap,cash_weight=r.cash_weight.iloc[0]))
 write(pd.DataFrame(actual),'actual_rebalance_risk.csv');save_json(D/'target_holdings_validation.json',dict(status='PASS',count=len(checks),checks=checks,full_test_suite=54))
 print('target and holdings checks',len(checks),flush=True)
if __name__=='__main__':main()
