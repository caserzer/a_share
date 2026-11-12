import sys,json
from pathlib import Path
import pandas as pd,numpy as np,joblib
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p46';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
sf=EP/'restart/p45/scores.parquet';tf=EP/'restart/p30/training_panel.parquet';bf=EP/'restart/p05/models/2024-01-01_B.joblib';features=joblib.load(bf)['features'];ids=['era','industry_code','date'];q=pd.read_parquet(sf,columns=ids+['fixed','updated']);p=pd.read_parquet(tf,columns=ids+features);q=q.merge(p,on=ids,validate='one_to_one');rows=[];states=[]
for date,g in q.groupby('date'):
 k=int(np.ceil(len(g)*.2))
 for method in ['fixed','updated']:
  z=g.sort_values([method,'era','industry_code'],ascending=[False,True,True]).head(k);assert len(z)==k
  states.append(dict(date=date,year=date.year,method=method,rows=len(g),selected=k,rate20_nonpositive=z.rate20.le(0).mean(),base_rate20_nonpositive=g.rate20.le(0).mean(),rate60_nonpositive=z.rate60.le(0).mean(),base_rate60_nonpositive=g.rate60.le(0).mean()))
  for feature in features:
   valid=g[[method,feature]].dropna();rho=valid[method].rank().corr(valid[feature].rank()) if valid[method].nunique()>1 and valid[feature].nunique()>1 else np.nan
   rank=g[feature].rank(method='average',pct=True);rows.append(dict(date=date,year=date.year,method=method,feature=feature,spearman=rho,selected_mean_percentile=rank.loc[z.index].mean(),known_feature=g[feature].notna().sum()))
r=pd.DataFrame(rows);s=pd.DataFrame(states);r.to_csv(OUT/'daily_preferences.csv',index=False);s.to_csv(OUT/'daily_states.csv',index=False);r.groupby(['year','method','feature'])[['spearman','selected_mean_percentile']].mean().to_csv(OUT/'annual_preferences.csv');s.groupby(['year','method'])[['rate20_nonpositive','base_rate20_nonpositive','rate60_nonpositive','base_rate60_nonpositive']].mean().to_csv(OUT/'annual_states.csv')
inputs=[sf,tf,bf,Path(__file__),EP/'restart/P46_model_preference_plan.md'];(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',no_future_labels_read=True,rows=len(q),dates=q.date.nunique(),same_capacity=True,constant_correlations_unknown=True,inputs={str(p):sha(p) for p in inputs},artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}),indent=2)+'\n');print(r[r.feature.isin(['rate5','rate20','rate60'])].groupby(['year','method','feature'])[['spearman','selected_mean_percentile']].mean().to_string());print(s.groupby(['year','method'])[['rate20_nonpositive','base_rate20_nonpositive','rate60_nonpositive','base_rate60_nonpositive']].mean().to_string())
