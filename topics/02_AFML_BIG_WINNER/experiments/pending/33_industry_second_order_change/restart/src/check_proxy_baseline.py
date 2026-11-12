import sys,json
from pathlib import Path
import numpy as np,pandas as pd,joblib
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p30';seal=json.loads((OUT/'prediction_seal.json').read_text())
for path,value in seal['inputs'].items():assert sha(Path(path))==value
for path,value in seal['artifacts'].items():assert sha(OUT/path)==value
p=pd.read_parquet(OUT/'training_panel.parquet');q=pd.read_parquet(OUT/'predictions.parquet');folds=pd.read_csv(OUT/'folds.csv',parse_dates=['cutoff']);ids=['era','industry_code','date'];bundle=joblib.load(EP/'restart/p05/models/2024-01-01_B.joblib');features=bundle['features'];replays=0
for _,f in folds.iterrows():
 tr=p[p.eligible&p.new_win126.notna()&p.new_end126.lt(f.cutoff)];assert len(tr)==f.train_rows and tr.date.nunique()==f.train_dates and tr.new_end126.max()<f.cutoff
 b=joblib.load(OUT/'models'/f'{f.cutoff.date()}.joblib');assert b['features']==features and b['model'].get_params()==bundle['model'].get_params()
 z=q[q.fit_cutoff.eq(f.cutoff)].merge(p[ids+features],on=ids,validate='one_to_one').sample(20,random_state=3326);assert np.allclose(b['model'].predict_proba(z[features])[:,1],z.raw_score,atol=1e-12);replays+=len(z)
e=pd.read_parquet(OUT/'evaluated.parquet');count=0
for _,g in e.groupby(['era','industry_code','block']):
 g=g.sort_values('date');prev=None
 for _,r in g.iterrows():
  continuous=prev is not None and r.week_i==prev.week_i+1
  for name in ['rebuilt','momentum']:
   edge=bool(r[name]) and continuous and not bool(prev[name]);boundary=bool(r[name]) and not continuous;assert edge==r[name+'_edge'] and boundary==r[name+'_boundary'];count+=1
  prev=r
s=pd.read_parquet(OUT/'catalog_status.parquet');assert len(s)==len(p[p.date.ge('2023-01-01')]);assert s.raw_score.notna().sum()==len(q);assert s.loc[~s.eligible,'raw_score'].isna().all()
s.groupby(s.date.dt.year).agg(catalog=('date','size'),scored=('raw_score','count')).to_csv(OUT/'catalog_coverage.csv')
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',folds=len(folds),prediction_replays=replays,event_checks=count,all_hashes_verified=True,catalog_rows=len(s),scored_rows=len(q),checker_sha256=sha(Path(__file__))),indent=2)+'\n')
print(pd.read_csv(OUT/'annual_events.csv').query('method=="rebuilt" and horizon==126').to_string(index=False));print(pd.read_csv(OUT/'catalog_coverage.csv').to_string(index=False))
