from common import *
import pandas as pd
import sys
out=ROOT/'outputs/r270'/sys.argv[1]
p=pd.read_parquet(out/'predictions.parquet');d=pd.read_csv(out/'secondary_date_metrics.csv',parse_dates=['date']);keys=['era','level','task','horizon','method','variant','date'];lookup=d.set_index(keys);n=0
for k,g in p.groupby(keys):
 v=g.dropna(subset=['y']);pos=v[v.y.eq(1)].prediction.to_numpy();neg=v[v.y.eq(0)].prediction.to_numpy()
 if len(pos) and len(neg):
  auc=float(np.mean((pos[:,None]>neg[None,:])+0.5*(pos[:,None]==neg[None,:])));ordered=sorted(set(v.prediction),reverse=True);tp=0;count=0;ap=0.
  for score in ordered:
   block=v[v.prediction.eq(score)];new=int(block.y.sum());tp+=new;count+=len(block);ap+=(new/len(pos))*(tp/count)
 else:auc=ap=np.nan
 row=lookup.loc[k];assert np.isclose(auc,row.auc,equal_nan=True) and np.isclose(ap,row.ap,equal_nan=True);n+=1
js(out/'secondary_verification.json',dict(status='PASS',date_groups=n,scope='R263 independent pairwise ROC-AUC and grouped-score average precision including undefined single-class months',code_sha256=sha(__file__)));print('SECONDARY VERIFIED',n)
