"""Verify frozen EP32 scores and EP33 identity alignment before transfer evaluation."""
import sys,json
from pathlib import Path
import numpy as np
import pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,ID
EXT=EP.parent/'32_industry_rotation_cycle_observation/extensions'
OUT=EP/'restart/p02';OUT.mkdir(exist_ok=True)
refs={};parts={}
for name,folder in [('risk','v12_duration_risk'),('diffusion','v18_conditional_diffusion')]:
 receipt=EXT/folder/'outputs/prediction_receipt.json'
 e=next(x for x in json.loads(receipt.read_text())['tasks'] if x['task']=='W_0.15_CSI_ALL')
 assert sha(e['path'])==e['sha256']
 refs[str(receipt)]=sha(receipt);refs[e['path']]=e['sha256'];parts[name]=pd.read_parquet(e['path'])
fpath=Path('/home/xiaolv/.cache/a_share/ep32/economics_v31/frames/W_0.15_CSI_ALL.parquet')
f=pd.read_parquet(fpath);f=f[f.level.eq('L3')].copy();assert not f.duplicated(ID).any()
for name,model,column in [('risk','risk_tree','risk_score'),('diffusion','diffusion_tree','diffusion_tree')]:
 r=parts[name];r=r[r.model.eq(model)]
 x=f[['row_id',column]].merge(r[['row_id','prob']],on='row_id',validate='one_to_one')
 assert len(x)==len(f) and np.array_equal(x[column],x.prob)
assert (f.select_accepted==(f.state_eligible.eq(1)&f.risk_score.ge(.11)&f.diffusion_tree.ge(.11)&f.market_up)).all()
pfile=EP/'restart/p01/feature_panel.parquet';p=pd.read_parquet(pfile).reset_index(drop=True)
p=p[p.eligible].copy()
joined=p[ID].merge(f[ID+['row_id']],on=ID,how='left',validate='one_to_one',indicator=True)
joined['year']=joined.date.dt.year
coverage=joined.groupby('year').agg(price_rows=('date','size'),price_dates=('date','nunique'),matched_rows=('row_id','count')).reset_index()
coverage.to_csv(OUT/'transfer_coverage.csv',index=False)
# Seal only features and selectors, without future labels or old launch clock.
cols=ID+['row_id','state_eligible','risk_score','diffusion_tree','market_return126','market_up']
q=p.merge(f[cols],on=ID,how='inner',validate='one_to_one')
assert len(q)==len(f)
q.to_parquet(OUT/'common_features.parquet',index=False)
labels=EP/'outputs/r09/evaluation_panel.parquet';l=pd.read_parquet(labels)
a=q[ID].merge(l[ID+['status63','status126','status252']],on=ID,how='left',validate='one_to_one')
assert len(a)==len(q) and a.status126.notna().all()
for file in [fpath,pfile,labels,Path(__file__)]:refs[str(file)]=sha(file)
result=dict(status='PASS',source_hashes=refs,common_rows=len(q),common_dates=q.date.nunique(),first_date=str(q.date.min()),last_date=str(q.date.max()),known_outcomes={str(h):int(a[f'status{h}'].eq('KNOWN').sum()) for h in [63,126,252]},common_features_sha256=sha(OUT/'common_features.parquet'),scope='Historical transfer diagnostic; no extrapolation to dates without frozen predictions; no efficacy evaluated')
(OUT/'transfer_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(coverage.to_string(index=False));print(json.dumps({k:v for k,v in result.items() if k!='source_hashes'},indent=2))
