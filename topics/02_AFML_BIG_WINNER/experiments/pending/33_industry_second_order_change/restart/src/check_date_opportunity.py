import sys,json
from pathlib import Path
import pandas as pd,numpy as np,joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p19';seal=json.loads((OUT/'prediction_seal.json').read_text())
for path,value in seal['inputs'].items():assert sha(Path(path))==value
for path,value in seal['artifacts'].items():assert sha(OUT/path)==value
x=pd.read_parquet(OUT/'features.parquet');y=pd.read_parquet(OUT/'targets.parquet');q=pd.read_parquet(OUT/'predictions.parquet');old=pd.read_parquet(EP/'restart/p17/evaluated.parquet')
checks=0
for h in [63,126,252]:
 a=old.groupby('date').agg(joint=(f'joint{h}','mean'),absolute=(f'absolute{h}','mean'),total=('date','size'),known=(f'joint{h}','count'))
 a.loc[(a.known/a.total)<.95,['joint','absolute']]=np.nan
 b=y[y.horizon.eq(h)].set_index('date').loc[a.index]
 assert np.allclose(a[['joint','absolute']],b[['joint','absolute']],equal_nan=True)
 assert a.total.equals(b.total) and a.known.equals(b.known);checks+=len(a)
# Refit selected early/late quarters from eligible matured targets and compare all their predictions.
refits=0
for cut in [pd.Timestamp('2023-01-01'),pd.Timestamp('2025-01-01')]:
 for name in ['M','MB']:
  rows=q[q.cutoff.eq(cut)&q.horizon.eq(126)&q.target.eq('joint')&q.model.eq(name)];bundle=joblib.load(OUT/'models'/rows.model_file.iloc[0]);cols=bundle['features']
  t=y[y.horizon.eq(126)].set_index('date').join(x);tr=t[t.end.lt(cut)&t.joint.notna()].dropna(subset=['market21','market126','vol21','breadth_now','change'])
  model=make_pipeline(StandardScaler(),Ridge(alpha=10));model.fit(tr[cols],tr.joint);pred=np.clip(model.predict(x.loc[rows.date,cols]),0,1);assert np.allclose(pred,rows.prediction,atol=1e-12);refits+=1
z=pd.read_parquet(OUT/'evaluated.parquet');z[z.actual.notna()].groupby(['year','horizon','target','model']).agg(mature=('actual','count'),actual=('actual','mean'),prediction=('prediction','mean'),mse=('squared_error','mean')).to_csv(OUT/'annual_mature.csv')
(OUT/'independent_validation.json').write_text(json.dumps(dict(status='PASS',all_sealed_hashes_verified=True,p17_date_horizon_target_checks=checks,independent_model_refits=refits,checker_sha256=sha(Path(__file__))),indent=2)+'\n')
print(pd.read_csv(OUT/'folds.csv').groupby('horizon').train_dates.agg(['min','max']).to_string());print(pd.read_csv(OUT/'comparisons.csv').to_string(index=False));print(y.groupby('horizon').agg(dates=('date','size'),known=('joint','count')).to_string())
