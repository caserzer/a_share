import sys,json
from pathlib import Path
import numpy as np,pandas as pd,joblib
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p44';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
f=EP/'restart/p30/training_panel.parquet';bf=EP/'restart/p05/models/2024-01-01_B.joblib';features=joblib.load(bf)['features'];p=pd.read_parquet(f,columns=['era','industry_code','date','eligible','new_win126','new_end126']+features);p['available']=p.new_win126.notna();p=p.drop(columns='new_win126');p=p[p.eligible];old=pd.read_csv(EP/'restart/p30/folds.csv');refs=[];daily=[];seen=[]
def quantile(x,w):
 ix=np.argsort(x,kind='stable');x=x[ix];w=w[ix];c=np.cumsum(w)/w.sum();return x[np.searchsorted(c,[.01,.25,.5,.75,.99],side='left').clip(0,len(x)-1)]
for _,fold in old.iterrows():
 cut=pd.Timestamp(fold.cutoff);tr=p[p.available&p.new_end126.lt(cut)];te=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))];assert len(tr)==fold.train_rows and tr.date.nunique()==fold.train_dates;seen.extend(te.index)
 assert te.groupby('date').market126.nunique().eq(1).all()
 for ref,t in [('ALL',tr),('SW2014',tr[tr.era.eq('SW2014')]),('SW2021',tr[tr.era.eq('SW2021')])]:
  if not len(t):continue
  w=1/t.groupby('date').date.transform('size').to_numpy();w/=w.sum()
  for feature in features:
   x=t[feature].to_numpy(float);valid=np.isfinite(x);qs=quantile(x[valid],w[valid]) if valid.any() else np.full(5,np.nan);assert np.all(np.diff(qs)>=0);iqr=qs[3]-qs[1]
   refs.append(dict(cutoff=str(cut.date()),reference=ref,feature=feature,rows=len(t),dates=t.date.nunique(),supported=t.date.nunique()>=26,q01=qs[0],q25=qs[1],q50=qs[2],q75=qs[3],q99=qs[4],missing_weight=float(w[~valid].sum())))
   for date,g in te.groupby('date'):
    y=g[feature].to_numpy(float);good=np.isfinite(y);v=y[good];low=int((v<qs[0]).sum());high=int((v>qs[4]).sum());n=len(v)
    daily.append(dict(date=date,year=date.year,cutoff=str(cut.date()),reference=ref,feature=feature,train_dates=t.date.nunique(),rows=len(g),known=n,missing_fraction=1-n/len(g),below=low/n if n else np.nan,above=high/n if n else np.nan,outside=(low+high)/n if n else np.nan,median_shift_iqr=(np.median(v)-qs[2])/iqr if n and iqr>0 else np.nan))
assert len(seen)==len(set(seen))==len(p[p.date.ge('2023-01-01')])
r=pd.DataFrame(refs);d=pd.DataFrame(daily);r.to_csv(OUT/'training_reference.csv',index=False);d.to_csv(OUT/'daily.csv',index=False);d.groupby(['year','reference','feature'])[['outside','below','above','median_shift_iqr','missing_fraction']].mean().to_csv(OUT/'annual.csv');d.groupby(['cutoff','reference','feature'])[['outside','below','above','median_shift_iqr','missing_fraction']].mean().to_csv(OUT/'quarterly.csv')
inputs=[f,bf,EP/'restart/p30/folds.csv',Path(__file__),EP/'restart/P44_feature_shift_plan.md'];(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',fold_checks=len(old),test_rows=len(seen),reference_rows=len(r),daily_rows=len(d),outcomes_not_used_beyond_availability=True,weighted_quantile_definition='inverse weighted empirical CDF; nonmissing weights normalized',inputs={str(x):sha(x) for x in inputs},artifacts={x.name:sha(x) for x in OUT.iterdir() if x.is_file()}),indent=2)+'\n');print(d[d.reference.eq('ALL')].groupby(['year','feature'])[['outside','median_shift_iqr','missing_fraction']].mean().to_string())
