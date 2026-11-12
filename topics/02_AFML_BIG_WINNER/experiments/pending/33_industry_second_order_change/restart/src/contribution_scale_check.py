import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p31';source=OUT/'feature_panel.parquet';a=pd.read_parquet(source);n=(a.breadth*a.valid_members).round();a['positive_gain_cv2']=(n-1)*a.concentration
for x in [np.array([1.,2.,3.]),np.array([1.,1.,10.])]:
 cv=lambda v:len(v)*sum((v/v.sum())**2)-1
 assert np.isclose(cv(x),cv(np.tile(x,2)))
a['matched']=False;a['arm']='UNKNOWN';a['cell']=''
for date,g in a[a.candidate].groupby('date'):
 g=g.sort_values(['era','industry_code']);count=len(g);g['momentum_bin']=np.minimum((g.rate60.rank(method='first')-1)*3//count,2).astype(int);g['size_bin']=g.valid_members.rank(method='first').gt(count/2).astype(int);g['breadth_bin']=g.breadth.rank(method='first').gt(count/2).astype(int)
 for key,b in g.groupby(['momentum_bin','size_bin','breadth_bin']):
  if len(b)<6:continue
  b=b.sort_values(['positive_gain_cv2','era','industry_code']);k=len(b)//2;a.loc[b.index,'matched']=True;a.loc[b.index,'cell']='_'.join(map(str,key));a.loc[b.index[:k],'arm']='LOW_DISPERSION';a.loc[b.index[k:],'arm']='HIGH_DISPERSION'
a.to_parquet(OUT/'cv2_feature_panel.parquet',index=False);b=a[a.matched].groupby(['date','cell','arm'])[['positive_gain_cv2','concentration','breadth','valid_members','rate60']].mean().unstack('arm');delta=pd.DataFrame({c:b[c]['LOW_DISPERSION']-b[c]['HIGH_DISPERSION'] for c in ['positive_gain_cv2','concentration','breadth','valid_members','rate60']});delta.to_csv(OUT/'cv2_balance_differences.csv')
(OUT/'cv2_receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [source,Path(__file__),EP/'restart/P31_definition_amendment.md']},feature_sha256=sha(OUT/'cv2_feature_panel.parquet'),no_future_labels_read=True,matched=int(a.matched.sum()),dates=int(a.loc[a.matched,'date'].nunique())),indent=2)+'\n');print(delta.groupby(level=0).mean().mean().to_string())
