import pandas as pd
from pandas.testing import assert_frame_equal
from common import *
def run():
 out=ROOT/'outputs/r95';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 original=pd.read_parquet(ROOT/'data/r10_alert_followup.parquet');d=pd.read_parquet(out/'alerts.parquet');assert_frame_equal(original,d[original.columns]);obs=json.loads((ROOT/'outputs/r94/observations.json').read_text());groups={}
 for r in obs:groups.setdefault(tuple(r[k] for k in KEY),[]).append(r)
 def eq(a,b):return (pd.isna(a) and pd.isna(b)) or a==b
 for x in d.to_dict('records'):
  eligible=[r for r in groups.get(tuple(x[k] for k in KEY),[]) if pd.Timestamp(r['snapshot'])<x['date']];r=max(eligible,key=lambda a:a['snapshot']) if eligible else None
  if r is None:assert x['accounting_status']=='no_prior_source_snapshot' and pd.isna(x['accounting_snapshot']) and pd.isna(x['accounting_coherence']) and x['accounting_group']=='unknown';continue
  assert x['accounting_snapshot']==pd.Timestamp(r['snapshot']) and eq(x['accounting_period'],r['period']) and x['accounting_age_days']==(x['date']-pd.Timestamp(r['snapshot'])).days>0 and x['accounting_status']==r['status'];z=None
  if r['status']=='source_limited_disclosed_period_available' and r['both_improve_fraction'] is not None and r['both_decline_fraction'] is not None:z=r['both_improve_fraction']-r['both_decline_fraction']
  assert eq(x['accounting_coherence'],z);assert x['accounting_group']==('unknown' if z is None else 'positive' if z>0 else 'negative' if z<0 else 'zero')
 for s in json.loads((out/'summary.json').read_text()):
  q=d
  for k in ['era','level','strategy','accounting_group']:q=q[q[k].eq(s[k])]
  v=q[q[s['metric']].notna()];dates={date:list(g[s['metric']]) for date,g in v.groupby('date')};means=[sum(vals)/len(vals) for vals in dates.values()];assert s['alerts']==len(q) and s['known']==len(v) and s['unknown']==len(q)-len(v) and s['dates']==q.date.nunique() and s['known_dates']==len(dates);assert s['industries']==q.industry_code.nunique() and s['source_snapshots']==q.accounting_snapshot.nunique() and s['economic_periods']==q.accounting_period.nunique()
  expected=sum(means)/len(means) if means else None;assert (s['date_equal_mean'] is None and expected is None) or np.isclose(s['date_equal_mean'],expected)
  assert (s['mean_age_days'] is None and q.accounting_age_days.isna().all()) or np.isclose(s['mean_age_days'],q.accounting_age_days.mean())
 coverage=pd.DataFrame(json.loads((out/'coverage.json').read_text()));expected=d.groupby(['era','level','strategy','accounting_status','accounting_group']).size().reset_index(name='alerts');assert_frame_equal(coverage,expected)
 assert rec['all_alerts']==len(d) and rec['known_exposure']==d.accounting_coherence.notna().sum()
 js(out/'verification.json',dict(status='PASS',alerts=len(d),known_exposure=rec['known_exposure'],scope='all original alert fields unchanged, strictly prior snapshot maximum including failures, exact exposure and grouping, all aggregate arithmetic',verifier_sha256=sha(Path(__file__))));print('R95 VERIFIED',len(d),rec['known_exposure'])
if __name__=='__main__':run()
