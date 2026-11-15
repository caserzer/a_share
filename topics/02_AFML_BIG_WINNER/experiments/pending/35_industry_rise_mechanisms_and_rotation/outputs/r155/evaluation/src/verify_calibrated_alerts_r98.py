import math,statistics
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r98';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 p=pd.read_parquet(ROOT/'outputs/r97/predictions.parquet');s=pd.read_parquet(ROOT/'data/r09_daily_scores.parquet');a=pd.read_parquet(out/'alerts.parquet');ak=KEY+['date','strategy'];old=pd.read_parquet(ROOT/'outputs/r09/alerts.parquet');baseline=a[a.version.eq('monthly_calibration')];assert set(map(tuple,baseline[ak].to_numpy()))==set(map(tuple,old[ak].to_numpy()));meta={tuple(r[k] for k in KEY)+(r['date'],):r for r in s.to_dict('records')};calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);months={}
 for date in calendar:months[date.to_period('M')]=date
 ends={v for k,v in months.items() if k.end_time.normalize()<=calendar.max()}
 for version,col in [('monthly_calibration','monthly_probability'),('daily_calibration','daily_probability')]:
  raw=[]
  for _,g in p.groupby(['era','level','date']):raw.extend(sorted(g.to_dict('records'),key=lambda r:(-r[col],r['industry_code']))[:math.ceil(.2*len(g))])
  expected_daily={tuple(r[k] for k in KEY)+(r['date'],) for r in raw};expected_monthly={x for x in expected_daily if x[-1] in ends};last={};expected_cd=set()
  for r in sorted(raw,key=lambda r:(r['date'],r['industry_code'])):
   key=tuple(r[k] for k in KEY);full=key+(r['date'],);day=meta[full]['day_i']
   if key not in last or day-last[key]>20:expected_cd.add(full);last[key]=day
  for strategy,expected in [('daily',expected_daily),('monthly',expected_monthly),('daily_cooldown20',expected_cd)]:
   q=a[a.version.eq(version)&a.strategy.eq(strategy)];assert not q.duplicated(KEY+['date']).any();assert set(map(tuple,q[KEY+['date']].to_numpy()))==expected
  for r in a[a.version.eq(version)].to_dict('records'):
   original=meta[tuple(r[k] for k in KEY)+(r['date'],)]
   for k in ['day_i','block','return20','excess20','y']:assert (pd.isna(r[k]) and pd.isna(original[k])) or r[k]==original[k]
   assert r['selected_score']==r[col]
 h=pd.read_parquet(out/'event_hits.parquet');events=pd.read_csv(ROOT/'outputs/r09/confirmation_events.csv',parse_dates=['date']);assert len(h)==len(events)*6;ev={tuple(r[k] for k in KEY)+(r['block'],r['date']):r for r in events.to_dict('records')};lookup={k:g.sort_values('day_i') for k,g in a.groupby(['version','strategy']+KEY+['block'])}
 for r in h.to_dict('records'):
  origin=ev[tuple(r[k] for k in KEY)+(r['block'],r['date'])]
  for k in events.columns:assert r[k]==origin[k]
  key=(r['version'],r['strategy'])+tuple(r[k] for k in KEY)+(r['block'],);g=lookup.get(key);q=[] if g is None else [x for x in g[['day_i','date']].itertuples(index=False) if 0<r['day_i']-x.day_i<=20];hit=bool(r['evaluable'] and q);assert r['hit']==hit and r['matched_alerts']==len(q)
  if hit:assert r['first_alert']==q[0].date and r['lead_sessions']==r['day_i']-q[0].day_i
  else:assert pd.isna(r['first_alert']) and pd.isna(r['lead_sessions'])
 originalhits=pd.read_csv(ROOT/'outputs/r09/event_hits.csv',parse_dates=['date','first_alert']);check=h[h.version.eq('monthly_calibration')].merge(originalhits,on=KEY+['date','strategy'],suffixes=('','_old'),validate='one_to_one');assert len(check)==len(originalhits) and check.hit.eq(check.hit_old).all() and check.matched_alerts.eq(check.matched_alerts_old).all() and np.allclose(check.lead_sessions,check.lead_sessions_old,equal_nan=True)
 for r in json.loads((out/'summary.json').read_text()):
  g=a[a.date.dt.year.eq(r['year'])];z=h[h.date.dt.year.eq(r['year'])]
  for k in ['era','level','strategy','version']:g=g[g[k].eq(r[k])];z=z[z[k].eq(r[k])]
  v=g[g.y.notna()];valid=z[z.evaluable];unique={(x.industry_code,x.date.to_period('M')) for x in g.itertuples()};assert r['alerts']==len(g) and r['mature']==len(v) and r['unknown']==len(g)-len(v) and r['events']==len(valid) and r['hit_events']==sum(valid.hit) and r['left_censored']==sum(~z.evaluable) and r['unique_industry_months']==len(unique) and r['repeat_alerts']==len(g)-len(unique)
  for k,value in [('precision',v.y.mean()),('recall',valid.hit.mean()),('median_lead',valid.loc[valid.hit,'lead_sessions'].median()),('hits_per100alerts',100*sum(valid.hit)/len(g))]:assert (r[k] is None and pd.isna(value)) or np.isclose(r[k],value)
 changes=pd.read_parquet(out/'alert_identity_changes.parquet');oldkeys=set(map(tuple,baseline[ak].to_numpy()));newkeys=set(map(tuple,a[a.version.eq('daily_calibration')][ak].to_numpy()));assert len(changes)==len(oldkeys|newkeys)
 for r in changes.to_dict('records'):
  key=tuple(r[k] for k in ak);assert r['_merge']==('both' if key in oldkeys and key in newkeys else 'left_only' if key in oldkeys else 'right_only')
 js(out/'verification.json',dict(status='PASS',alert_rows=len(a),event_hit_rows=len(h),baseline_all_identities_and_hits_match=True,scope='independent top20% and cooldown selections, all underlying labels, full event windows and prior alerts, baseline identity/hit equivalence and all summaries',verifier_sha256=sha(Path(__file__))));print('R98 VERIFIED',len(a),len(h))
if __name__=='__main__':run()
