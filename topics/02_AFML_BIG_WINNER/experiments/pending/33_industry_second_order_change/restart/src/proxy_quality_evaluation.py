import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p30';q=pd.read_parquet(OUT/'evaluated.parquet');w=pd.read_parquet(OUT/'weekly_labels.parquet');ids=['era','industry_code','date'];qualitycols=[c for h in [63,126,252] for c in [f'path_proxy{h}',f'entry_stale{h}',f'end_stale{h}',f'new_status{h}']];q=q.merge(w[ids+qualitycols],on=ids,validate='one_to_one');rows=[]
for h in [63,126,252]:
 label=f'new_win{h}';endpoint=q[f'entry_stale{h}'].eq(True)|q[f'end_stale{h}'].eq(True)
 q[f'quality{h}']=np.select([q[label].isna(),endpoint,q[f'path_proxy{h}'].eq(1)],['UNKNOWN','ENDPOINT_STALE','INTERNAL_PROXY_ENDPOINTS_OBSERVED'],default='ALL_OBSERVED_PATH')
 base=q.groupby('date')[label].mean();qualitybase=q.groupby(['date',f'quality{h}'])[label].mean()
 for method in ['rebuilt','momentum']:
  for unit in ['state','edge']:
   z=q[q[method if unit=='state' else method+'_edge']].copy();z['delta_overall']=z[label]-z.date.map(base);z['delta_within_quality']=z[label]-pd.MultiIndex.from_frame(z[['date',f'quality{h}']]).map(qualitybase).to_numpy()
   for quality,g in z.groupby(f'quality{h}'):
    rows.append(dict(method=method,unit=unit,horizon=h,quality=quality,rows=len(g),valued=int(g[label].notna().sum()),win=g[label].mean(),uplift_overall=g.delta_overall.mean(),uplift_within_quality=g.delta_within_quality.mean()))
pd.DataFrame(rows).to_csv(OUT/'quality_results.csv',index=False);q.to_parquet(OUT/'quality_evaluated.parquet',index=False)
strictfile=EP/'restart/p25/weekly_labels.parquet';strict=pd.read_parquet(strictfile);a=w.merge(strict[ids+[f'new_win{h}' for h in [63,126,252]]],on=ids,suffixes=('_proxy','_strict'),validate='one_to_one');checks=[]
for h in [63,126,252]:
 both=a[f'new_win{h}_proxy'].notna()&a[f'new_win{h}_strict'].notna();flips=int(a.loc[both,f'new_win{h}_proxy'].ne(a.loc[both,f'new_win{h}_strict']).sum());checks.append(dict(horizon=h,common=int(both.sum()),flips=flips))
pd.DataFrame(checks).to_csv(OUT/'strict_label_comparison.csv',index=False)
d=pd.read_parquet(EP/'restart/p29/daily_industries.parquet');groups={k:g.set_index('day_i') for k,g in d.groupby(['era','industry_code'])};m=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet').close.sort_index();n=0
for _,r in w.sample(80,random_state=3330).iterrows():
 g=groups[(r.era,r.industry_code)];i=int(r.day_i)
 for h in [63,126,252]:
  b=g.reindex(range(i,i+h+2));valid=b.nav.notna().all() and b.block.nunique(dropna=False)==1;assert valid==pd.notna(r[f'new_win{h}'])
  if valid:
   ret=b.nav.iloc[-1]/b.nav.iloc[1]-1;bm=m.iloc[i+h+1]/m.iloc[i+1]-1;assert float(ret>0 and ret>bm)==r[f'new_win{h}']
  n+=1
(OUT/'quality_validation.json').write_text(json.dumps(dict(status='PASS',raw_label_window_checks=n,strict_comparison=checks,quality_is_posthoc_not_selection=True,inputs={str(p):sha(p) for p in [OUT/'evaluated.parquet',OUT/'weekly_labels.parquet',strictfile,Path(__file__)]}),indent=2)+'\n')
print(pd.DataFrame(rows).query('horizon==126 and method=="rebuilt" and unit=="edge"').to_string(index=False));print(pd.DataFrame(checks).to_string(index=False))
