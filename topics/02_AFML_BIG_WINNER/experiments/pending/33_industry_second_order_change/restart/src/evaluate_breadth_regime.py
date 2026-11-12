# Resume evaluation after sealed feature creation; fixes pandas expanding name collision only.
import json,sys
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import KEY,sha,calendar_dates
OUT=EP/'restart/p18';raw=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');df=EP/'restart/p17/daily.csv'
seal=json.loads((OUT/'feature_seal.json').read_text())
assert sha(OUT/'date_features.parquet')==seal['features']
for path,value in seal['inputs'].items():assert sha(Path(path))==value
assert not (OUT/'validation.json').exists()
a=pd.read_parquet(OUT/'date_features.parquet');d=pd.read_parquet(raw);d=d[d.level.eq('L3')]
r=pd.read_csv(df,parse_dates=['date']);r=r.merge(a[['date','expanding']],on='date',validate='many_to_one')
base=r[r.method.eq('all')][['date','horizon','joint']].rename(columns={'joint':'base'});r=r.merge(base,on=['date','horizon'],validate='many_to_one');r['uplift']=r.joint-r.base
cols=['absolute','relative','joint','uplift'];r.groupby(['year','regime','expanding','method','horizon']).agg(dates=('date','size'),mature_dates=('joint','count'),**{c:(c,'mean') for c in cols}).to_csv(OUT/'annual.csv')
axis=calendar_dates();axis=axis[(axis>=a.date.min())&(axis<=a.date.max())];rng=np.random.default_rng(3318);n=len(axis);samples=[np.concatenate([(j+np.arange(26))%n for j in rng.integers(0,n,int(np.ceil(n/26)))])[:n] for _ in range(500)]
rows=[]
for (regime,method,h),g in r.groupby(['regime','method','horizon']):
 b=g.set_index('date').reindex(axis)
 for c in cols:
  v=b[c].to_numpy();e=b['expanding'].eq(True).to_numpy();ne=b['expanding'].eq(False).to_numpy();n1=int(np.sum(e&np.isfinite(v)));n0=int(np.sum(ne&np.isfinite(v)));supported=min(n1,n0)>=26
  delta=np.nanmean(v[e])-np.nanmean(v[ne]);boot=[]
  if supported:
   for ix in samples:
    vv=v[ix];ee=e[ix];nn=ne[ix]
    if np.isfinite(vv[ee]).any() and np.isfinite(vv[nn]).any():boot.append(np.nanmean(vv[ee])-np.nanmean(vv[nn]))
  lo,hi=np.quantile(boot,[.025,.975]) if boot else [np.nan,np.nan]
  rows.append(dict(regime=regime,method=method,horizon=h,metric=c,n_expanding=n1,n_not_expanding=n0,supported=supported,delta=delta,lo=lo,hi=hi,valid_bootstrap=len(boot)))
pd.DataFrame(rows).to_csv(OUT/'comparisons.csv',index=False)
# Independent direct slicing of raw paths for random dates verifies both cohort and breadth.
checks=a.sample(12,random_state=3318)
for _,row in checks.iterrows():
 vals=[];eligible=0
 for _,g in d[d.date.le(row.date)].groupby(KEY):
  g=g.sort_values('date')
  if len(g)==0 or g.date.iloc[-1]!=row.date:continue
  if len(g)>=61 and g.coverage.iloc[-1]>=.8 and g.members.iloc[-1]>=5:eligible+=1
  if len(g)<82 or not (g.coverage.iloc[[-1,-22]].ge(.8).all() and g.members.iloc[[-1,-22]].ge(5).all()):continue
  vals.append((g.nav.iloc[-1]>g.nav.iloc[-22],g.nav.iloc[-22]>g.nav.iloc[-43]))
 assert len(vals)==row.n_common and eligible==row.n_eligible
 assert np.allclose(np.mean(vals,axis=0),[row.breadth_now,row.breadth_before])
assert sha(OUT/'date_features.parquet')==json.loads((OUT/'feature_seal.json').read_text())['features']
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',raw_date_cohort_checks=12,dates=len(a),features_sealed=True,outcome_source_sha256=sha(df)),indent=2)+'\n')
print(a.groupby(['year','regime','expanding']).size().unstack(fill_value=0).to_string());print(pd.DataFrame(rows).query('horizon==126 and method=="tree" and metric in ["joint","uplift"]').to_string(index=False))
