import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha,ID,KEY
OUT=EP/'restart/p06';s=json.loads((OUT/'selection_seal.json').read_text());assert all(sha(f)==h for f,h in s['inputs'].items());assert sha(OUT/'selected_features.parquet')==s['features_sha256']
p=pd.read_parquet(OUT/'selected_features.parquet');e=pd.read_parquet(OUT/'evaluated.parquet');pd.testing.assert_frame_equal(p[ID],e[ID]);assert not any(c.startswith(('win','status')) for c in p)
checks=0
for m in ['top20','raw_gate']:
 for _,g in p.groupby(KEY):
  prev=None;last=None
  for i,r in g.sort_values('date').iterrows():
   contiguous=prev is not None and r.week_i-prev.week_i==1
   edge=bool(r[m] and contiguous and not prev[m])
   assert edge==r[m+'_edge'];assert bool(r[m] and not contiguous)==r[m+'_boundary']
   cool=edge and (last is None or r.day_i-last>=126)
   assert cool==r[m+'_edge_cooldown126']
   if cool:last=r.day_i
   prev=r;checks+=1
summary=pd.read_csv(OUT/'summary.csv')
for _,r in summary.iterrows():
 z=e[e[r.method+'_'+r.unit]];col=f'win{r.horizon}';assert len(z)==r.total;assert z[col].notna().sum()==r.known;assert r.known+r.immature+r.missing_path==r.total;assert np.isclose(z[col].mean(),r.win_rate)
# Post-result descriptive score bands, never used to change thresholds.
rows=[]
for m in ['top20','raw_gate']:
 z=e[e[m+'_edge']&e.win126.notna()].copy();z['band']=pd.cut(z.raw_score,[0,.4,.5,.6,.7,.8,1],include_lowest=True)
 for band,g in z.groupby('band',observed=True):rows.append(dict(method=m,band=str(band),known=len(g),mean_score=g.raw_score.mean(),win_rate=g.win126.mean()))
pd.DataFrame(rows).to_csv(OUT/'score_bands_diagnostic.csv',index=False)
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS',sequential_flag_checks=checks,summary_checks=len(summary),seal_verified=True,unknown_counts_reconciled=True,efficacy_established=False),indent=2)+'\n')
print(pd.read_csv(OUT/'annual.csv').query('horizon==126 and unit=="edge"').to_string(index=False));print(pd.DataFrame(rows).to_string(index=False))
