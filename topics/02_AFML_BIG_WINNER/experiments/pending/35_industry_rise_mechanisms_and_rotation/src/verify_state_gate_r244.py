from common import *
import pandas as pd
from itertools import combinations
from regime_reversal_actions_r220 import IDS

def run():
 out=ROOT/'outputs/r244';d=pd.read_parquet(out/'date_policies.parquet');dec=pd.read_parquet(out/'decisions.parquet');original=pd.read_parquet(ROOT/'outputs/r220/actions.parquet');state=pd.read_parquet(ROOT/'outputs/r243/origin_states.parquet',columns=KEY+['date','asof_state']);keys=IDS+['industry_code','date']
 p=original.merge(state,on=KEY+['date'],validate='many_to_one');q=dec.merge(p,on=keys,validate='one_to_one',suffixes=('_saved','_source'));assert len(q)==len(original)
 assert q.alert_saved.eq(q.alert_source).all() and q.asof_state_saved.eq(q.asof_state_source).all()
 expected=q.alert_source & q.asof_state_source.ne('ongoing');assert q.retained_alert.eq(expected).all() and q.suppressed_alert.eq(q.alert_source&~expected).all()
 aggregate=dec.groupby(IDS+['date']).agg(A=('alert','sum'),K=('retained_alert','sum'));countcheck=d.merge(aggregate,on=IDS+['date'],validate='many_to_one');assert countcheck.original_alerts.eq(countcheck.A).all() and countcheck.retained_alerts.eq(countcheck.K).all()
 assert np.allclose(countcheck.retain_probability,np.divide(countcheck.K,countcheck.A,out=np.zeros(len(countcheck)),where=countcheck.A.ne(0)))
 prev=pd.read_parquet(ROOT/'outputs/r243/date_contributions.parquet');prev=prev[prev.stratum.eq('ongoing')];joined=d.merge(prev,on=IDS+['date','cost'],validate='one_to_one',suffixes=('','_r243'));assert len(joined)==len(d)
 checks=0
 for name in ['cash','market']:
  assert np.allclose(joined[name+'_gated'],joined[name+'_original']-joined[name+'_contribution'],equal_nan=True,atol=1e-12)
  assert np.allclose(d[name+'_thinning'],d.retain_probability*d[name+'_original'],equal_nan=True,atol=1e-12);checks+=2*len(d)
 # Independent scalar terminal-wealth construction for all per-date lost/avoided sums.
 p=p.merge(dec[keys+['retained_alert','suppressed_alert']],on=keys,validate='one_to_one');v=p[p.status.eq('valid')].copy();group=IDS+['date'];n=v.groupby(group).size().rename('n')
 for c in [0,.002,.005]:
  hold=(1+v.ret)*(1-c);gains={'cash':(1-c)-hold,'market':(1+v.market)*(1-c)**3-hold};part=d[d.cost.eq(c)].set_index(group)
  for name,gain in gains.items():
   for kind,vals in [('lost_benefit',gain.where(gain.gt(0),0)),('avoided_cost',(-gain).where(gain.lt(0),0))]:
    sums=(vals*v.suppressed_alert).groupby([v[k] for k in group]).sum()/n;want=sums.reindex(part.index)
    assert np.allclose(want,part[name+'_'+kind],equal_nan=True,atol=1e-12);checks+=len(part)
 # Exact uniform K-of-A expectation, including unknown-outcome chosen alerts.
 gains=[.03,-.04,None,.02];A=len(gains);enumerations=0
 for K in range(A+1):
  returns=[];unknown=[]
  for chosen in combinations(range(A),K):returns.append(sum(gains[j] for j in chosen if gains[j] is not None)/3);unknown.append(sum(gains[j] is None for j in chosen));enumerations+=1
  assert np.isclose(np.mean(returns),(K/A)*sum(x for x in gains if x is not None)/3)
  assert np.isclose(np.mean(unknown),K/A)
 saved=pd.read_csv(out/'summary.csv');fields=[c for c in d if c.startswith(('cash_','market_'))];recomputed=d.groupby(IDS+['cost'])[fields].mean().reset_index();q=saved.merge(recomputed,on=IDS+['cost'],validate='one_to_one',suffixes=('_saved','_expected'))
 for c in fields:assert np.allclose(q[c+'_saved'],q[c+'_expected'],equal_nan=True,atol=1e-12)
 receipt=json.loads((out/'verification.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(Path(f))==h
 for f,h in receipt['outputs'].items():assert sha(out/f)==h
 js(out/'independent_verification.json',dict(status='PASS',decisions=len(dec),date_count_checks=len(d),policy_scalar_checks=checks,summary_values=len(q)*len(fields),enumerated_control_subsets=enumerations,code_sha256=sha(Path(__file__)),adoption=False));print('PASS',len(dec),len(d),checks,enumerations)
if __name__=='__main__':run()
