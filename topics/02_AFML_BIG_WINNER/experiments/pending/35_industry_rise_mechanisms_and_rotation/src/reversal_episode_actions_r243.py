from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS
from followup_r10 import exit_economics
STRATA=['unknown_signal','ongoing','ongoing_left_boundary','unknown_future','new_on_entry','new_within20','left_boundary_future','no_new20']
def run():
 out=ROOT/'outputs/r243';out.mkdir(exist_ok=True)
 e=pd.read_parquet(ROOT/'outputs/r242/episodes.parquet');s=pd.read_parquet(ROOT/'outputs/r242/segments.parquet');p=pd.read_parquet(ROOT/'outputs/r220/actions.parquet');m=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=pd.DatetimeIndex(m.index)
 el={k:g for k,g in e.groupby(KEY)};sl={k:g for k,g in s.groupby(KEY)};rows=[]
 for r in p[KEY+['date','status']].drop_duplicates().to_dict('records'):
  key=tuple(r[k] for k in KEY);i=cal.get_indexer([r['date']])[0];segments=sl[key];seg=segments[segments.start_i.le(i)&segments.end_i.ge(i)];state='unknown';active_id=np.nan;future='unknown';future_id=np.nan
  if len(seg):
   assert len(seg)==1;sid=seg.segment.iloc[0];ev=el[key];ev=ev[ev.segment.eq(sid)];active=ev[ev.breach_i.le(i)&(ev.recovery_i.isna()|ev.recovery_i.gt(i))]
   assert len(active)<=1
   state='clear'
   if len(active):state='ongoing_left_boundary' if active.left_boundary.iloc[0] else 'ongoing';active_id=int(active.episode_id.iloc[0])
  if r['status']=='valid':
   future='no_new20';ev=el[key];hit=ev[ev.breach_i.between(i+1,i+21)]
   if len(hit):
    first=hit.iloc[0];future_id=int(first.episode_id);future='left_boundary_future' if first.left_boundary else 'new_on_entry' if first.breach_i==i+1 else 'new_within20'
  stratum='unknown_signal' if state=='unknown' else state if state.startswith('ongoing') else 'unknown_future' if future=='unknown' else future
  rows.append(dict(r,asof_state=state,future_state=future,stratum=stratum,active_episode_id=active_id,future_episode_id=future_id))
 origins=pd.DataFrame(rows);origins.to_parquet(out/'origin_states.parquet',index=False);p=p.merge(origins.drop(columns='status'),on=KEY+['date'],validate='many_to_one');metrics=[]
 for key,g in p.groupby(IDS+['date']):
  ident=dict(zip(IDS+['date'],key));v=g[g.status.eq('valid')];n=len(v)
  for cost in [0,.002,.005]:
   cash,switch=exit_economics(v.ret,v.market,cost)
   for st in STRATA:
    a=g[g.stratum.eq(st)];ix=v.stratum.eq(st);selected=ix&v.alert
    metrics.append(dict(ident,cost=cost,stratum=st,candidates=len(a),alerts=int(a.alert.sum()),known=int(ix.sum()),known_alerts=int(selected.sum()),unknown_alerts=int((a.alert&a.status.ne('valid')).sum()),all_known=n,cash_contribution=float((cash*selected).sum()/n) if n else np.nan,market_contribution=float((switch*selected).sum()/n) if n else np.nan,cash_alert_mean=cash[selected].mean(),market_alert_mean=switch[selected].mean()))
 metrics=pd.DataFrame(metrics);metrics.to_parquet(out/'date_contributions.parquet',index=False)
 ids=IDS+['cost','stratum'];summary=metrics.groupby(ids).agg(dates=('date','size'),valid_dates=('cash_contribution','count'),alerts=('alerts','sum'),known_alerts=('known_alerts','sum'),unknown_alerts=('unknown_alerts','sum'),cash_contribution=('cash_contribution','mean'),market_contribution=('market_contribution','mean')).reset_index();summary.to_csv(out/'summary.csv',index=False)
 old=pd.read_csv(ROOT/'outputs/r220/date_metrics.csv',parse_dates=['date']);calc=metrics.groupby(IDS+['date','cost'])[['cash_contribution','market_contribution']].sum(min_count=1).reset_index();q=calc.merge(old,on=IDS+['date','cost'],validate='one_to_one');assert len(q)==len(old);errors={}
 for a,b in [('cash_contribution','cash_policy_gain'),('market_contribution','market_policy_gain')]:
  assert np.allclose(q[a],q[b],equal_nan=True,atol=1e-12);errors[a]=float((q[a]-q[b]).abs().max())
 baseids=[x for x in IDS if x!='variant']+['cost','stratum'];pairs=[]
 for key,g in summary.groupby(baseids):
  ident=dict(zip(baseids,key));base=g[g.variant.eq('base')].iloc[0]
  for variant in ['state','interaction']:
   row=g[g.variant.eq(variant)].iloc[0];pairs.append(dict(ident,comparison=variant+'-base',delta_cash=row.cash_contribution-base.cash_contribution,delta_market=row.market_contribution-base.market_contribution,delta_alerts=int(row.alerts-base.alerts)))
 pairs=pd.DataFrame(pairs);pairs.to_csv(out/'comparisons.csv',index=False)
 inputs=[ROOT/'outputs/r242/episodes.parquet',ROOT/'outputs/r242/segments.parquet',ROOT/'outputs/r220/actions.parquet',ROOT/'outputs/r220/date_metrics.csv',CACHE/'forecast_v5/CSI_ALL.parquet',ROOT/'protocols/r243.json',Path(__file__),ROOT/'src/followup_r10.py']
 js(out/'verification.json',dict(status='PASS',origins=len(origins),predictions=len(p),date_strata_cost_records=len(metrics),original_date_cost_checks=len(q),reconciliation_errors=errors,inputs={str(x):sha(x) for x in inputs},outputs={f.name:sha(f) for f in out.iterdir() if f.suffix in ['.csv','.parquet']},adoption=False));print(origins.stratum.value_counts().to_string());print(p[p.alert].groupby(['variant','stratum']).size().unstack(fill_value=0).to_string())
if __name__=='__main__':run()
