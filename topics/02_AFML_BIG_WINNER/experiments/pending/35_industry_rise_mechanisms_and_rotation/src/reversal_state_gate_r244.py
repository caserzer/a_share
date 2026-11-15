from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS
from followup_r10 import exit_economics

def run():
 out=ROOT/'outputs/r244';out.mkdir(exist_ok=True)
 p=pd.read_parquet(ROOT/'outputs/r220/actions.parquet');state=pd.read_parquet(ROOT/'outputs/r243/origin_states.parquet',columns=KEY+['date','asof_state']);p=p.merge(state,on=KEY+['date'],validate='many_to_one');assert p.asof_state.notna().all()
 p['retained_alert']=p.alert&p.asof_state.ne('ongoing');p['suppressed_alert']=p.alert&~p.retained_alert
 p[IDS+['industry_code','date','asof_state','alert','retained_alert','suppressed_alert']].to_parquet(out/'decisions.parquet',index=False)
 rows=[]
 for key,g in p.groupby(IDS+['date']):
  ident=dict(zip(IDS+['date'],key));A=int(g.alert.sum());K=int(g.retained_alert.sum());q=K/A if A else 0.;v=g[g.status.eq('valid')];n=len(v);unknown=g[g.status.ne('valid')]
  for cost in [0,.002,.005]:
   cash,market=exit_economics(v.ret,v.market,cost)
   r=dict(ident,cost=cost,candidates=len(g),known=n,original_alerts=A,retained_alerts=K,suppressed_alerts=A-K,retain_probability=q,original_unknown_alerts=int(unknown.alert.sum()),retained_unknown_alerts=int(unknown.retained_alert.sum()),thinning_expected_unknown_alerts=float(q*unknown.alert.sum()))
   for name,gain in [('cash',cash),('market',market)]:
    original=float((gain*v.alert).sum()/n) if n else np.nan;gated=float((gain*v.retained_alert).sum()/n) if n else np.nan;thin=q*original;lost=float((gain.clip(lower=0)*v.suppressed_alert).sum()/n) if n else np.nan;avoided=float((-gain.clip(upper=0)*v.suppressed_alert).sum()/n) if n else np.nan
    r.update({name+'_original':original,name+'_gated':gated,name+'_thinning':thin,name+'_gate_minus_original':gated-original,name+'_gate_minus_thinning':gated-thin,name+'_lost_benefit':lost,name+'_avoided_cost':avoided})
   rows.append(r)
 dates=pd.DataFrame(rows);dates.to_parquet(out/'date_policies.parquet',index=False);numeric=[c for c in dates if c.startswith(('cash_','market_'))];summary=dates.groupby(IDS+['cost'])[numeric].mean().reset_index();counts=dates.groupby(IDS+['cost']).agg(dates=('date','size'),valid_dates=('cash_original','count'),years=('date',lambda x:x.dt.year.nunique()),original_alerts=('original_alerts','sum'),retained_alerts=('retained_alerts','sum'),suppressed_alerts=('suppressed_alerts','sum'),original_unknown_alerts=('original_unknown_alerts','sum'),retained_unknown_alerts=('retained_unknown_alerts','sum'),thinning_expected_unknown_alerts=('thinning_expected_unknown_alerts','sum'),zero_retained_dates=('retained_alerts',lambda x:int(x.eq(0).sum()))).reset_index();summary=summary.merge(counts,on=IDS+['cost'],validate='one_to_one');summary.to_csv(out/'summary.csv',index=False)
 old=pd.read_csv(ROOT/'outputs/r220/date_metrics.csv',parse_dates=['date']);check=dates.merge(old,on=IDS+['cost','date'],validate='one_to_one');assert len(check)==len(old)
 for name in ['cash','market']:
  assert np.allclose(check[name+'_original'],check[name+'_policy_gain'],equal_nan=True,atol=1e-12)
  assert np.allclose(dates[name+'_gate_minus_original'],dates[name+'_avoided_cost']-dates[name+'_lost_benefit'],equal_nan=True,atol=1e-12)
 inputs=[ROOT/'outputs/r220/actions.parquet',ROOT/'outputs/r220/date_metrics.csv',ROOT/'outputs/r243/origin_states.parquet',ROOT/'protocols/r244.json',Path(__file__),ROOT/'src/followup_r10.py'];js(out/'verification.json',dict(status='PASS',prediction_rows=len(p),original_alerts=int(p.alert.sum()),retained_alerts=int(p.retained_alert.sum()),date_policy_rows=len(dates),summary_rows=len(summary),inputs={str(x):sha(x) for x in inputs},outputs={f.name:sha(f) for f in out.iterdir() if f.suffix in ['.csv','.parquet']},adoption=False,posthoc_exploration=True))
 print(summary[summary.cost.eq(.005)].groupby('variant')[['market_original','market_gated','market_gate_minus_thinning','market_avoided_cost','market_lost_benefit']].median().to_string());print(len(p),p.alert.sum(),p.retained_alert.sum())
if __name__=='__main__':run()
