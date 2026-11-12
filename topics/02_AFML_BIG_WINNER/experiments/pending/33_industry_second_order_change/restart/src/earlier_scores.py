import json,sys
from pathlib import Path
import numpy as np,pandas as pd,joblib
from sklearn.base import clone
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha
OUT=EP/'restart/p11';OUT.mkdir(exist_ok=True)
if (OUT/'prediction_seal.json').exists():raise RuntimeError('sealed; no overwrite')
source=EP/'outputs/r11/coverage30/evaluation_panel.parquet';p=pd.read_parquet(source);p=p[p.price_eligible].reset_index(drop=True);p['sample_id']=np.arange(len(p))
oldfile=EP/'restart/p05/predictions.parquet';olds=json.loads((EP/'restart/p05/prediction_seal.json').read_text());assert sha(oldfile)==olds['artifacts']['predictions.parquet']
old=pd.read_parquet(oldfile);old=old[old.model.eq('B')]
# Stable IDs verified independently of source row ordering.
check=old.merge(p[ID+['sample_id']],on=ID,suffixes=('_old','_new'),validate='one_to_one');assert check.sample_id_old.eq(check.sample_id_new).all()
modelpath=EP/'restart/p05/models/2024-01-01_B.joblib';assert sha(modelpath)==olds['artifacts']['models/2024-01-01_B.joblib'];bundle=joblib.load(modelpath);features=bundle['features']
rows=[];receipts=[];(OUT/'models').mkdir(exist_ok=True)
for cut in pd.date_range('2023-01-01','2023-10-01',freq='QS'):
 train=p[p.win126.notna()&p.end126.lt(cut)];test=p[p.date.ge(cut)&p.date.lt(cut+pd.DateOffset(months=3))];assert len(train)>=500 and train.date.nunique()>=26 and train.win126.nunique()==2
 w=1/train.groupby('date').date.transform('size').to_numpy();w/=w.mean();model=clone(bundle['model']);model.fit(train[features],train.win126.astype(int),sample_weight=w)
 z=test[['sample_id']+ID].copy();z['model']='B';z['fit_cutoff']=cut;z['raw_score']=model.predict_proba(test[features])[:,1];rows.append(z);joblib.dump(dict(model=model,features=features),OUT/'models'/f'{cut.date()}_B.joblib',compress=3)
 receipts.append(dict(cutoff=str(cut),train=len(train),train_dates=train.date.nunique(),test=len(test),max_label_end=str(train.end126.max())));print(cut.date(),len(train),len(test),flush=True)
new=pd.concat(rows,ignore_index=True);new.to_parquet(OUT/'2023_predictions.parquet',index=False);q=pd.concat([new,old],ignore_index=True);assert not q.duplicated(ID).any();q.to_parquet(OUT/'combined_predictions.parquet',index=False)
(OUT/'folds.json').write_text(json.dumps(receipts,indent=2)+'\n')
(OUT/'prediction_seal.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [source,oldfile,modelpath,Path(__file__),EP/'restart/P11_earlier_scores_plan.md']},artifacts={str(f.relative_to(OUT)):sha(f) for f in OUT.rglob('*') if f.is_file()}),indent=2)+'\n')
# Construct states from features only, independently of future outcomes.
stfile=EP/'restart/p03/selected_features.parquet';st=pd.read_parquet(stfile)
g=q.merge(p[ID+['day_i','week_i','market126']],on=ID,validate='one_to_one').merge(st[ID+['candidate_low_date']],on=ID,how='left',validate='one_to_one').sort_values(KEY+['date']).reset_index(drop=True)
a=g.sort_values(['date','raw_score','era','industry_code'],ascending=[True,False,True,True]);g['top20']=False;g.loc[a.index,'top20']=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2));g['candidate']=g.top20&g.market126.le(0)
cont=g.week_i.sub(g.groupby(KEY).week_i.shift()).eq(1);g['edge']=g.candidate&g.groupby(KEY).candidate.shift().eq(False)&cont;g['boundary']=g.candidate&~cont;g['cooldown']=False
for _,b in g[g.edge].groupby(KEY):
 last=-100000
 for i,r in b.iterrows():
  if r.day_i-last>=126:g.loc[i,'cooldown']=True;last=r.day_i
g['low_first']=False;first=g[g.edge&g.candidate_low_date.notna()].drop_duplicates(KEY+['candidate_low_date']);g.loc[first.index,'low_first']=True
g.to_parquet(OUT/'selected_features.parquet',index=False);(OUT/'selection_seal.json').write_text(json.dumps(dict(feature_sha256=sha(OUT/'selected_features.parquet'),combined_prediction_sha256=sha(OUT/'combined_predictions.parquet'),state_source_sha256=sha(stfile)),indent=2)+'\n')
g=g.merge(p[ID+['win126','end126']],on=ID,validate='one_to_one');g.to_parquet(OUT/'evaluated.parquet',index=False);folds=[];metrics=[]
for unit in ['edge','cooldown','low_first']:
 for cut in pd.date_range('2023-01-01','2026-10-01',freq='QS'):
  ev=g[g[unit]&g.win126.notna()&g.end126.lt(cut)];state=g[g.market126.le(0)&g.win126.notna()&g.end126.lt(cut)]
  ok=len(ev)>=100 and ev.date.nunique()>=12 and len(state)>=500 and state.date.nunique()>=12 and ev.win126.nunique()==2 and state.win126.nunique()==2
  folds.append(dict(unit=unit,cutoff=cut,events=len(ev),event_dates=ev.date.nunique(),state_rows=len(state),state_dates=state.date.nunique(),max_label_end=ev.end126.max(),supported=ok))
 for year,b in g[g[unit]].groupby(g[g[unit]].date.dt.year):metrics.append(dict(unit=unit,year=int(year),total=len(b),known=b.win126.notna().sum(),win_rate=b.win126.mean()))
f=pd.DataFrame(folds);f.to_csv(OUT/'quarter_support.csv',index=False);pd.DataFrame(metrics).to_csv(OUT/'annual_events.csv',index=False)
ceil=[]
for unit in ['edge','cooldown','low_first']:
 cuts=f[f.unit.eq(unit)&f.supported].cutoff;allowed=g.date.dt.to_period('Q').isin(cuts.dt.to_period('Q'))
 for period,start in [('original_2024',pd.Timestamp('2024-01-01')),('expanded_2023',pd.Timestamp('2023-01-01'))]:
  scope=g.date.ge(start);z=g[g.candidate&allowed&scope];ceil.append(dict(unit=unit,period=period,first_supported=str(cuts.min()),successful_candidate_weeks=z.win126.sum(),all_successful_weeks=g.loc[scope,'win126'].sum(),coverage_ceiling=z.win126.sum()/g.loc[scope,'win126'].sum()))
pd.DataFrame(ceil).to_csv(OUT/'coverage_ceiling.csv',index=False)
print(pd.DataFrame(ceil).to_string(index=False));print(pd.DataFrame(metrics).to_string(index=False))
