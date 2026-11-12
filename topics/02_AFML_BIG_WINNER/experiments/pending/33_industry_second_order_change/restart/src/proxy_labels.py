import json,sys
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p30';OUT.mkdir(exist_ok=True);assert not (OUT/'label_receipt.json').exists()
newfile=EP/'restart/p29/daily_industries.parquet';wf=EP/'restart/p29/weekly_path_support.parquet';oldfile=EP/'restart/p21/evaluated.parquet';mf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet')
seal=json.loads((EP/'restart/p29/receipt.json').read_text());assert sha(newfile)==seal['artifacts'][newfile.name];assert sha(wf)==seal['artifacts'][wf.name]
d=pd.read_parquet(newfile);w=pd.read_parquet(wf);m=pd.read_parquet(mf).close.sort_index();cal=pd.DatetimeIndex(m.index);parts=[]
for _,g in d[d.nav.notna()].groupby(['era','industry_code','block']):
 g=g.sort_values('date').copy();assert np.all(np.diff(g.day_i)==1);bm=g.date.map(m)
 for h in [63,126,252]:
  ret=g.nav.shift(-h-1)/g.nav.shift(-1)-1;mr=bm.shift(-h-1)/bm.shift(-1)-1;end=g.date.shift(-h-1)
  g[f'new_return{h}']=ret;g[f'new_end{h}']=end;g[f'new_win{h}']=(ret.gt(0)&ret.gt(mr)).astype(float).where(end.notna())
 parts.append(g[['era','industry_code','date']+[c for h in [63,126,252] for c in [f'new_return{h}',f'new_end{h}',f'new_win{h}']]])
labels=pd.concat(parts,ignore_index=True);ids=['era','industry_code','date'];w=w.merge(labels,on=ids,how='left',validate='one_to_one')
for h in [63,126,252]:
 assert np.array_equal(w[f'new_win{h}'].notna().to_numpy(),w[f'path{h}'].to_numpy(dtype=bool))
 w[f'new_status{h}']=np.where(~w[f'calendar_mature{h}'],'IMMATURE',np.where(w[f'new_win{h}'].notna(),'KNOWN','MISSING_PATH'))
w.to_parquet(OUT/'weekly_labels.parquet',index=False)

(OUT/'label_receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [newfile,wf,mf,Path(__file__)]},labels_sha256=sha(OUT/'weekly_labels.parquet')),indent=2)+'\n')
