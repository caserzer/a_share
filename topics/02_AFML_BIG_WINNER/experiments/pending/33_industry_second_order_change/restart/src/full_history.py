import sys,json
from pathlib import Path
import numpy as np,pandas as pd,joblib
from sklearn.base import clone
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,calendar_dates,block_ci
OUT=EP/'restart/p13';OUT.mkdir(exist_ok=True)
if (OUT/'prediction_seal.json').exists():raise RuntimeError('sealed; no overwrite')
cache=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5');rawfile=cache/'daily_industries.parquet';mfile=cache/'CSI_ALL.parquet'
d=pd.read_parquet(rawfile);d=d[d.level.eq('L3')];m=pd.read_parquet(mfile).close.sort_index();cal=pd.DatetimeIndex(m.index)
v=pd.Series(cal,index=cal);weeks=v.groupby(v.index.to_period('W-FRI')).max();weeks=weeks[[x.end_time.normalize()<=cal.max() for x in weeks.index]]
chunks=[]
for _,g in d.groupby(KEY,sort=True):
 g=g.sort_values('date').copy();assert np.all(np.diff(cal.get_indexer(g.date))==1);x=np.log(g.nav.to_numpy()/m.reindex(g.date).to_numpy());x=pd.Series(x,index=g.index)
 for w in [5,20,60]:g[f'rate{w}']=(x-x.shift(w))*5/w
 g['vol60']=x.diff().rolling(60,min_periods=60).std();g['market126']=g.date.map(m/m.shift(126)-1);g['eligible']=g.rate60.notna()&g.coverage.ge(.8)&g.members.ge(5)
 ret=g.nav.shift(-127)/g.nav.shift(-1)-1;bm=pd.Series(m.reindex(g.date).to_numpy(),index=g.index);excess=ret-(bm.shift(-127)/bm.shift(-1)-1);g['end126']=g.date.shift(-127);g['win126']=((ret>0)&(excess>0)).astype(float).where(g.end126.notna())
 chunks.append(g[g.date.isin(weeks)&g.eligible])
p=pd.concat(chunks,ignore_index=True);oldsource=EP/'outputs/r11/coverage30/evaluation_panel.parquet';old=pd.read_parquet(oldsource);old=old[old.price_eligible]
modelpath=EP/'restart/p05/models/2024-01-01_B.joblib';bundle=joblib.load(modelpath);features=bundle['features'];z=p[p.date.ge('2021-01-01')].merge(old[ID+features+['win126','end126']],on=ID,suffixes=('_new','_old'),how='outer',indicator=True,validate='one_to_one');assert z._merge.eq('both').all()
for c in features+['win126']:assert np.allclose(z[c+'_new'],z[c+'_old'],equal_nan=True,atol=1e-12,rtol=1e-10),c
assert (z.end126_new.eq(z.end126_old)|(z.end126_new.isna()&z.end126_old.isna())).all()
p[ID+features+['win126','end126','week_i'] if 'week_i' in p else ID+features+['win126','end126','day_i']].to_parquet(OUT/'training_panel.parquet',index=False)
p.groupby(p.date.dt.year).agg(rows=('date','size'),dates=('date','nunique'),known=('win126','count')).to_csv(OUT/'data_coverage.csv')
(OUT/'data_validation.json').write_text(json.dumps(dict(status='PASS',overlap_rows=len(z),feature_columns=len(features),labels_aligned=True,daily_continuity_verified=True),indent=2)+'\n')
rows=[];folds=[];(OUT/'models').mkdir(exist_ok=True)
for cut in pd.date_range('2023-01-01','2026-10-01',freq='QS'):
 tr=p[p.win126.notna()&p.end126.lt(cut)];te=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))];model=clone(bundle['model']);w=1/tr.groupby('date').date.transform('size').to_numpy();w/=w.mean();model.fit(tr[features],tr.win126.astype(int),sample_weight=w)
 a=te[ID].copy();a['fit_cutoff']=cut;a['raw_score']=model.predict_proba(te[features])[:,1];rows.append(a);joblib.dump(dict(model=model,features=features),OUT/'models'/f'{cut.date()}_B.joblib',compress=3);folds.append(dict(cutoff=str(cut),train_rows=len(tr),train_dates=tr.date.nunique(),latest_label_end=str(tr.end126.max()),test_rows=len(te)));print(cut.date(),len(tr),len(te),flush=True)
q=pd.concat(rows,ignore_index=True);q.to_parquet(OUT/'predictions.parquet',index=False);(OUT/'folds.json').write_text(json.dumps(folds,indent=2)+'\n')
oldpred=EP/'restart/p11/combined_predictions.parquet'
(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [rawfile,mfile,oldsource,modelpath,oldpred,Path(__file__),EP/'restart/P13_full_history_plan.md']},artifacts={str(f.relative_to(OUT)):sha(f) for f in OUT.rglob('*') if f.is_file()}),indent=2)+'\n')
orig=pd.read_parquet(oldpred);assert set(map(tuple,q[ID].to_numpy()))==set(map(tuple,orig[ID].to_numpy()))
combined=pd.concat([q.assign(method='full2017'),orig[ID+['fit_cutoff','raw_score']].assign(method='old2021')],ignore_index=True).merge(p[ID+['win126','market126','day_i']],on=ID,validate='many_to_one')
weekmap={date:i for i,date in enumerate(weeks)};combined['week_i']=combined.date.map(weekmap);daily=[];events=[]
for method,g in combined.groupby('method'):
 g=g.sort_values(KEY+['date']).copy();rank=g.sort_values(['date','raw_score','era','industry_code'],ascending=[True,False,True,True]);g['selected']=False;g.loc[rank.index,'selected']=rank.groupby('date').cumcount().lt(np.ceil(rank.groupby('date').date.transform('size')*.2));g['candidate']=g.selected&g.market126.le(0);g['edge']=g.candidate&g.groupby(KEY).candidate.shift().eq(False)&g.week_i.sub(g.groupby(KEY).week_i.shift()).eq(1);g['cooldown']=False
 for _,b in g[g.edge].groupby(KEY):
  last=-100000
  for i,r in b.iterrows():
   if r.day_i-last>=126:g.loc[i,'cooldown']=True;last=r.day_i
 for date,b in g.groupby('date'):
  k=b[b.win126.notna()];sel=b[b.selected];daily.append(dict(method=method,date=date,regime='UP' if b.market126.iloc[0]>0 else 'NONUP',base=k.win126.mean(),win_rate=sel.win126.mean(),brier=((k.raw_score-k.win126)**2).mean()))
 base=g.groupby('date').win126.mean()
 for unit in ['edge','cooldown']:
  for year,b in g[g[unit]].groupby(g[g[unit]].date.dt.year):
   k=b[b.win126.notna()];events.append(dict(method=method,unit=unit,year=int(year),total=len(b),known=len(k),win_rate=k.win126.mean(),uplift=(k.win126-k.date.map(base)).mean()))
a=pd.DataFrame(daily);a['uplift']=a.win_rate-a.base;a.to_csv(OUT/'daily.csv',index=False);a.groupby([a.date.dt.year,'regime','method'])[['base','win_rate','uplift','brier']].mean().to_csv(OUT/'annual.csv');pd.DataFrame(events).to_csv(OUT/'annual_events.csv',index=False)
comparisons=[];dates=calendar_dates();dates=dates[dates>=pd.Timestamp('2023-01-01')]
for regime,g in a.groupby('regime'):
 for metric in ['win_rate','brier']:
  b=g.pivot(index='date',columns='method',values=metric);v=(b.full2017-b.old2021).reindex(dates);lo,hi=block_ci(v,26);comparisons.append(dict(regime=regime,metric=metric,full_minus_old=v.mean(),lo=lo,hi=hi))
pd.DataFrame(comparisons).to_csv(OUT/'comparisons.csv',index=False);print(a.groupby([a.date.dt.year,'regime','method'])[['win_rate','uplift','brier']].mean().to_string());print(pd.DataFrame(events).query('unit=="edge"').to_string(index=False))
