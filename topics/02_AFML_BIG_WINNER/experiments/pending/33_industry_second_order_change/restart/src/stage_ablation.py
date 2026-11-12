import sys,json
from pathlib import Path
import numpy as np,pandas as pd,joblib
from sklearn.ensemble import HistGradientBoostingClassifier
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,sha,calendar_dates,block_ci
OUT=EP/'restart/p05';OUT.mkdir(exist_ok=True)
B=['rate5','rate20','rate60','vol60','market126','coverage','members','volume_ratio']
S=['state_direction','state_left','state_age','state_confirm_age','state_drawup','state_drawdown','state_previous_decline','state_eligible']
D=['breadth21','breadth63','breadth_change5','breadth_change20','market_breadth_up_fraction']
ARMS={'B':B,'S':B+S,'D':B+D,'SD':B+S+D}
source=EP/'outputs/r11/coverage30/evaluation_panel.parquet'
receipt=EP.parent/'32_industry_rotation_cycle_observation/extensions/v7_online_stage/outputs/state_receipt.json'
r=json.loads(receipt.read_text());assert sha(r['path'])==r['sha256']
p=pd.read_parquet(source);p=p[p.price_eligible].copy()
s=pd.read_parquet(r['path']);s=s[s.level.eq('L3')&s.threshold.eq(.15)]
assert s.groupby(ID)[S].nunique(dropna=False).le(1).all().all();s=s[ID+S].drop_duplicates(ID)
p=p.merge(s,on=ID,how='left',validate='one_to_one').reset_index(drop=True)
assert p.level.eq('L3').all();p['sample_id']=np.arange(len(p))
p[B+S+D].isna().mean().rename('missing_fraction').to_csv(OUT/'feature_missingness.csv')
if (OUT/'prediction_seal.json').exists():raise RuntimeError('Existing sealed run; do not overwrite')
folds=[];preds=[];(OUT/'models').mkdir(exist_ok=True)
for cut in pd.date_range('2024-01-01','2026-10-01',freq='QS'):
 train=p[p.win126.notna()&p.end126.lt(cut)];test=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))]
 ok=len(train)>=500 and train.date.nunique()>=26 and train.win126.nunique()==2
 folds.append(dict(cutoff=str(cut),train=len(train),train_dates=train.date.nunique(),test=len(test),max_label_end=str(train.end126.max()),supported=ok))
 if not ok:continue
 weights=1/train.groupby('date').date.transform('size').to_numpy();weights/=weights.mean()
 for name,features in ARMS.items():
  model=HistGradientBoostingClassifier(max_iter=100,learning_rate=.05,max_leaf_nodes=7,max_depth=3,min_samples_leaf=100,l2_regularization=10,early_stopping=False,random_state=3312)
  model.fit(train[features],train.win126.astype(int),sample_weight=weights)
  z=test[['sample_id']+ID].copy();z['model']=name;z['fit_cutoff']=cut;z['raw_score']=model.predict_proba(test[features])[:,1];preds.append(z)
  joblib.dump(dict(model=model,features=features),OUT/'models'/f'{cut.date()}_{name}.joblib',compress=3)
 print(str(cut.date()),len(train),len(test),flush=True)
q=pd.concat(preds,ignore_index=True);q.to_parquet(OUT/'predictions.parquet',index=False)
(OUT/'folds.json').write_text(json.dumps(folds,indent=2)+'\n')
(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [source,Path(r['path']),receipt,Path(__file__),EP/'restart/P05_stage_ablation_plan.md']},artifacts={str(f.relative_to(OUT)):sha(f) for f in OUT.rglob('*') if f.is_file()},features=ARMS),indent=2)+'\n')
# Only now attach held-forward outcome values to saved scores.
q=q.merge(p[['sample_id','win63','win126','win252','state_age','state_drawup']],on='sample_id',validate='many_to_one')
q=q.sort_values(['model','date','raw_score','era','industry_code'],ascending=[True,True,False,True,True]);q['selected']=q.groupby(['model','date']).cumcount().lt(np.ceil(q.groupby(['model','date']).date.transform('size')*.2))
q.to_parquet(OUT/'evaluated.parquet',index=False)
dates=calendar_dates();dates=dates[dates>=pd.Timestamp('2024-01-01')];daily=[];rows=[];annual=[]
for name,g in q.groupby('model'):
 b=(g.raw_score-g.win126)**2;bd=b.groupby(g.date).mean();z=g[g.selected]
 for h in [63,126,252]:
  col=f'win{h}';rate=z.groupby('date')[col].mean();base=g.groupby('date')[col].mean();delta=(rate-base).reindex(dates);lo,hi=block_ci(delta,26 if h==126 else round(h/5))
  rows.append(dict(model=name,horizon=h,selected=len(z),known=z[col].notna().sum(),date_win_rate=rate.mean(),date_uplift=delta.mean(),lo=lo,hi=hi,success_week_coverage=z[col].sum()/g[col].sum(),median_age_days=z.state_age.median()*90,median_drawup=z.state_drawup.median(),brier126=bd.mean()))
  for date,value in rate.items():daily.append(dict(model=name,horizon=h,date=date,win_rate=value,brier126=bd.get(date,np.nan)))
  for year,v in rate.groupby(rate.index.year):annual.append(dict(model=name,horizon=h,year=int(year),dates=v.notna().sum(),win_rate=v.mean(),uplift=delta[delta.index.year==year].mean()))
df=pd.DataFrame(daily);comparisons=[]
for h in [63,126,252]:
 a=df[df.horizon.eq(h)];wins=a.pivot(index='date',columns='model',values='win_rate').reindex(dates);bs=a.pivot(index='date',columns='model',values='brier126').reindex(dates)
 for added,base in [('S','B'),('SD','D'),('D','B'),('SD','S')]:
  v=wins[added]-wins[base];lo,hi=block_ci(v,26 if h==126 else round(h/5));bv=bs[base]-bs[added];blo,bhi=block_ci(bv,26)
  comparisons.append(dict(added=added,base=base,horizon=h,win_delta=v.mean(),lo=lo,hi=hi,brier_improvement126=bv.mean(),brier_lo=blo,brier_hi=bhi))
pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False);df.to_csv(OUT/'daily.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False);pd.DataFrame(comparisons).to_csv(OUT/'comparisons.csv',index=False)
print(pd.DataFrame(rows).query('horizon==126').to_string(index=False));print(pd.DataFrame(comparisons).query('horizon==126').to_string(index=False))
