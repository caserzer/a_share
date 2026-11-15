from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS

def run():
 out=ROOT/'outputs/r243';o=pd.read_parquet(out/'origin_states.parquet');d=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');m=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=pd.DatetimeIndex(m.index);episodes=pd.read_parquet(ROOT/'outputs/r242/episodes.parquet');lookup={k:g.sort_values('date').copy() for k,g in d.groupby(KEY)}
 for key,g in lookup.items():
  g['i']=cal.get_indexer(g.date);g['relative']=g.nav.to_numpy()/m.reindex(g.date).to_numpy();valid=np.isfinite(g.relative)&g.relative.gt(0)&g.block.notna()&g.i.ge(0);g['valid']=valid;g['segment']=(~valid|~valid.shift(fill_value=False)|g.i.diff().ne(1)|g.block.ne(g.block.shift())).cumsum()
 for r in o.to_dict('records'):
  key=tuple(r[k] for k in KEY);g=lookup[key];today=g[g.date.eq(r['date'])];state='unknown'
  if len(today) and today.valid.iloc[0]:
   prefix=g[g.segment.eq(today.segment.iloc[0])&g.date.le(r['date'])];a=prefix.relative.to_numpy();peak=float(a.max());j=int(np.flatnonzero(a==peak)[-1]);cross=np.flatnonzero(a[j:]/peak<=.92)
   state=('ongoing_left_boundary' if j==0 else 'ongoing') if len(cross) else 'clear'
  assert state==r['asof_state']
  future='unknown';eid=np.nan
  if r['status']=='valid':
   i=cal.get_indexer([r['date']])[0];ev=episodes
   for k,v in zip(KEY,key):ev=ev[ev[k].eq(v)]
   ev=ev[ev.breach_date.gt(r['date'])&ev.breach_date.le(cal[i+21])].sort_values('breach_date');future='no_new20'
   if len(ev):
    e=ev.iloc[0];eid=int(e.episode_id);future='left_boundary_future' if e.left_boundary else 'new_on_entry' if e.breach_date==cal[i+1] else 'new_within20'
  assert future==r['future_state'] and (pd.isna(eid) and pd.isna(r['future_episode_id']) or eid==r['future_episode_id'])
  expected='unknown_signal' if state=='unknown' else state if state in ['ongoing','ongoing_left_boundary'] else 'unknown_future' if future=='unknown' else future
  assert expected==r['stratum']
 p=pd.read_parquet(ROOT/'outputs/r220/actions.parquet').merge(o[KEY+['date','stratum']],on=KEY+['date'],validate='many_to_one');metrics=pd.read_parquet(out/'date_contributions.parquet');allkeys=IDS+['date'];groupkeys=allkeys+['stratum'];checks=0
 p['known']=p.status.eq('valid');p['known_alert']=p.known&p.alert;p['unknown_alert']=~p.known&p.alert
 counts=p.groupby(groupkeys).agg(candidates=('alert','size'),alerts=('alert','sum'),known=('known','sum'),known_alerts=('known_alert','sum'),unknown_alerts=('unknown_alert','sum'))
 den=p.groupby(allkeys).known.sum().rename('den')
 for cost in [0,.002,.005]:
  # Independent terminal wealth arithmetic; no call to shared exit_economics.
  hold=(1+p.ret)*(1-cost);cash=1-cost;sw=(1+p.market)*(1-cost)*(1-cost)*(1-cost)
  p['cash_gain']=(cash-hold).where(p.known_alert,0);p['market_gain']=(sw-hold).where(p.known_alert,0)
  sums=p.groupby(groupkeys)[['cash_gain','market_gain']].sum();expected=counts.join(sums).reset_index().merge(den.reset_index(),on=allkeys,validate='many_to_one');actual=metrics[metrics.cost.eq(cost)].copy();q=actual.merge(expected,on=groupkeys,how='left',suffixes=('_saved','_expected'),validate='one_to_one')
  for col in ['candidates','alerts','known','known_alerts','unknown_alerts']:
   assert q[col+'_saved'].eq(q[col+'_expected'].fillna(0)).all();checks+=len(q)
  for label in ['cash','market']:
   want=q[label+'_gain'].fillna(0)/q.all_known.replace(0,np.nan)
   assert np.allclose(want,q[label+'_contribution'],equal_nan=True,atol=1e-12);checks+=len(q)
 summary=pd.read_csv(out/'summary.csv');ids=IDS+['cost','stratum'];recomputed=metrics.groupby(ids)[['cash_contribution','market_contribution']].mean().reset_index();q=summary.merge(recomputed,on=ids,suffixes=('_saved','_expected'),validate='one_to_one')
 for c in ['cash_contribution','market_contribution']:assert np.allclose(q[c+'_saved'],q[c+'_expected'],equal_nan=True,atol=1e-12)
 pairs=pd.read_csv(out/'comparisons.csv');baseids=[x for x in IDS if x!='variant']+['cost','stratum']
 wide=recomputed.pivot(index=baseids,columns='variant',values=['cash_contribution','market_contribution'])
 for variant in ['state','interaction']:
  pp=pairs[pairs.comparison.eq(variant+'-base')].set_index(baseids).sort_index();w=wide.reindex(pp.index)
  for action in ['cash','market']:assert np.allclose(pp['delta_'+action],w[(action+'_contribution',variant)]-w[(action+'_contribution','base')],equal_nan=True,atol=1e-12)
 receipt=json.loads((out/'verification.json').read_text())
 for path,h in receipt['inputs'].items():assert sha(Path(path))==h
 for path,h in receipt['outputs'].items():assert sha(out/path)==h
 js(out/'independent_verification.json',dict(status='PASS',prefix_asof_checks=len(o),future_and_stratum_checks=len(o),scalar_aggregate_checks=checks,summary_rows=len(summary),pair_rows=len(pairs),code_sha256=sha(Path(__file__)),adoption=False));print('PASS',len(o),checks,len(pairs))
if __name__=='__main__':run()
