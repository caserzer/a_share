import json,sys
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import KEY,sha,calendar_dates
OUT=EP/'restart/p18';OUT.mkdir(exist_ok=True)
assert not (OUT/'feature_seal.json').exists(),'sealed'
raw=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');sf=EP/'restart/p17/selected_features.parquet';df=EP/'restart/p17/daily.csv'
d=pd.read_parquet(raw);d=d[d.level.eq('L3')];chunks=[]
for _,g in d.groupby(KEY):
 g=g.sort_values('date').copy();r=g.nav/g.nav.shift(21)-1
 ok=g.coverage.ge(.8)&g.members.ge(5)&g.nav.shift(60).notna()
 g['eligible']=ok;g['common']=ok&ok.shift(21,fill_value=False)&r.notna()&r.shift(21).notna()
 g['up_now']=r.gt(0);g['up_before']=r.shift(21).gt(0);chunks.append(g[KEY+['date','eligible','common','up_now','up_before']])
z=pd.concat(chunks,ignore_index=True);a=z[z.common].groupby('date').agg(n_common=('date','size'),breadth_now=('up_now','mean'),breadth_before=('up_before','mean'));a['n_eligible']=z[z.eligible].groupby('date').size();a['retention']=a.n_common/a.n_eligible;a['change']=a.breadth_now-a.breadth_before;a['expanding']=a.change.gt(0)
s=pd.read_parquet(sf);dates=s[['date','regime']].drop_duplicates();assert dates.date.is_unique
a=dates.merge(a.reset_index(),on='date',how='left',validate='one_to_one');assert a.change.notna().all();a['year']=a.date.dt.year
a.to_parquet(OUT/'date_features.parquet',index=False)
a.groupby(['year','regime','expanding']).agg(dates=('date','size'),min_common=('n_common','min'),min_retention=('retention','min')).to_csv(OUT/'support.csv')
(OUT/'feature_seal.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in [raw,sf,Path(__file__),EP/'restart/P18_breadth_regime_plan.md']},'features':sha(OUT/'date_features.parquet')},indent=2)+'\n')
r=pd.read_csv(df,parse_dates=['date']);r=r.merge(a[['date','expanding']],on='date',validate='many_to_one')
base=r[r.method.eq('all')][['date','horizon','joint']].rename(columns={'joint':'base'});r=r.merge(base,on=['date','horizon'],validate='many_to_one');r['uplift']=r.joint-r.base
cols=['absolute','relative','joint','uplift'];r.groupby(['year','regime','expanding','method','horizon']).agg(dates=('date','size'),mature_dates=('joint','count'),**{c:(c,'mean') for c in cols}).to_csv(OUT/'annual.csv')
axis=calendar_dates();axis=axis[(axis>=a.date.min())&(axis<=a.date.max())];rng=np.random.default_rng(3318);n=len(axis);samples=[np.concatenate([(j+np.arange(26))%n for j in rng.integers(0,n,int(np.ceil(n/26)))])[:n] for _ in range(500)]
rows=[]
for (regime,method,h),g in r.groupby(['regime','method','horizon']):
 b=g.set_index('date').reindex(axis)
 for c in cols:
  v=b[c].to_numpy();e=b.expanding.eq(True).to_numpy();ne=b.expanding.eq(False).to_numpy();n1=int(np.sum(e&np.isfinite(v)));n0=int(np.sum(ne&np.isfinite(v)));supported=min(n1,n0)>=26
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
