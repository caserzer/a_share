import json,sys
from pathlib import Path
import pandas as pd,numpy as np,joblib
from sklearn.metrics import roc_auc_score
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,sha
OUT=EP/'restart/p12';OUT.mkdir(exist_ok=True)
source=EP/'outputs/r11/coverage30/evaluation_panel.parquet';p=pd.read_parquet(source);p=p[p.price_eligible].reset_index(drop=True)
qfile=EP/'restart/p11/combined_predictions.parquet';s=json.loads((EP/'restart/p11/prediction_seal.json').read_text());assert sha(qfile)==s['artifacts']['combined_predictions.parquet'];q=pd.read_parquet(qfile)
model=joblib.load(EP/'restart/p05/models/2024-01-01_B.joblib');features=model['features']
# Use identities rather than relying on sample index positions.
q=q.merge(p[ID+features+['win126','end126']],on=ID,validate='one_to_one');q['outside_any']=False
support=[];shifts=[]
for cut,test in q.groupby('fit_cutoff'):
 train=p[p.win126.notna()&p.end126.lt(cut)];w=1/train.groupby('date').date.transform('size');support.append(dict(cutoff=cut,train_rows=len(train),train_dates=train.date.nunique(),train_industries=train.industry_code.nunique(),sw2014_rows=int(train.era.eq('SW2014').sum()),sw2021_rows=int(train.era.eq('SW2021').sum()),date_equal_positive=float(np.average(train.win126,weights=w)),last_observation=train.date.max(),last_label_end=train.end126.max()))
 outside=pd.Series(False,index=test.index)
 for c in features:
  lo,hi=train[c].quantile([.01,.99]);flag=test[c].lt(lo)|test[c].gt(hi);outside|=flag
  shifts.append(dict(cutoff=cut,feature=c,train_q01=lo,train_q99=hi,train_median=train[c].median(),test_median=test[c].median(),outside_fraction=flag.mean(),missing_fraction=test[c].isna().mean()))
 q.loc[test.index,'outside_any']=outside
# Fix all rankings without using future label availability.
for name,col,asc in [('tree','raw_score',False),('momentum','rate60',False),('reversal','rate60',True)]:
 a=q.sort_values(['date',col,'era','industry_code'],ascending=[True,asc,True,True]);q[name]=False;q.loc[a.index,name]=a.groupby('date').cumcount().lt(np.ceil(a.groupby('date').date.transform('size')*.2))
q['regime']=np.where(q.market126.gt(0),'UP','NONUP')
daily=[]
for date,g in q.groupby('date'):
 known=g[g.win126.notna()]
 if not len(known):continue
 row=dict(date=date,quarter=str(date.to_period('Q')),year=date.year,regime=g.regime.iloc[0],base=known.win126.mean(),brier=((known.raw_score-known.win126)**2).mean(),auc=roc_auc_score(known.win126,known.raw_score) if known.win126.nunique()==2 else np.nan,outside_fraction=g.outside_any.mean())
 for m in ['tree','momentum','reversal']:row[m]=g.loc[g[m],'win126'].mean()
 daily.append(row)
d=pd.DataFrame(daily);d['tree_uplift']=d.tree-d.base;d['tree_minus_reversal']=d.tree-d.reversal;d['tree_minus_momentum']=d.tree-d.momentum
stats=['base','tree','reversal','momentum','tree_uplift','tree_minus_reversal','tree_minus_momentum','brier','auc','outside_fraction']
d.to_csv(OUT/'daily.csv',index=False);d.groupby(['quarter','regime'])[stats].mean().to_csv(OUT/'quarter_performance.csv');d.groupby(['year','regime'])[stats].mean().to_csv(OUT/'annual_performance.csv')
pd.DataFrame(support).to_csv(OUT/'training_support.csv',index=False);pd.DataFrame(shifts).to_csv(OUT/'feature_shifts.csv',index=False)
eventfile=EP/'restart/p11/evaluated.parquet';e=pd.read_parquet(eventfile);z=e[e.edge].merge(q[ID+['outside_any']],on=ID,validate='one_to_one');ref=q.groupby('date').win126.mean();z['delta']=z.win126-z.date.map(ref)
rows=[]
for (year,out),g in z.groupby([z.date.dt.year,'outside_any']):rows.append(dict(year=int(year),outside=bool(out),events=len(g),known=g.win126.notna().sum(),win_rate=g.win126.mean(),uplift=g.delta.mean()))
pd.DataFrame(rows).to_csv(OUT/'event_range_diagnostic.csv',index=False)
(OUT/'receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [source,qfile,eventfile,Path(__file__),EP/'restart/P12_failure_diagnostic_plan.md']},no_retraining=True,no_policy_change=True),indent=2)+'\n')
print(d.groupby(['year','regime'])[stats].mean().to_string());print(pd.DataFrame(support).head(4).to_string(index=False));print(pd.DataFrame(rows).to_string(index=False))
