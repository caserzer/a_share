"""Read sealed predictions only after training; preserve weekly cross-sectional blocks."""
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from common import *

def block_ci(x,B=2000,L=13):
 x=np.asarray(x,float);x=x[np.isfinite(x)];n=len(x)
 if n<2*L:return np.nan,np.nan
 rng=np.random.default_rng(20261116);starts=rng.integers(0,n,(B,int(np.ceil(n/L))))
 idx=((starts[:,:,None]+np.arange(L))%n).reshape(B,-1)[:,:n];means=x[idx].mean(axis=1)
 return tuple(np.quantile(means,[.025,.975]))

def predictions(scheme):
 receipts=json.loads((OUT/'manifests'/f'{scheme}_predictions.json').read_text());frames=[]
 for r in receipts:
  assert sha(r['prediction_path'])==r['prediction_sha256'];frames.append(pd.read_parquet(r['prediction_path']))
 return pd.concat(frames,ignore_index=True),[dict(path=r['prediction_path'],sha256=r['prediction_sha256']) for r in receipts]

def evaluate(scheme):
 p,consumption=predictions(scheme);y=pd.read_parquet(PRIVATE/'labels.parquet');f=p.merge(y,on=['signal_date','instrument'],validate='many_to_one');rows=[]
 for (model,seed,date),g in f.groupby(['model_id','seed_or_ensemble','signal_date']):
  valid=g[g.score.notna()].sort_values(['score','instrument']).copy();valid['quintile']=np.floor(5*np.arange(len(valid))/max(1,len(valid))).astype(int)+1
  for horizon in ['h5','h10','h20','h10_delay1']:
   known=valid.loc[valid[horizon].notna()];ic=spearmanr(known.score,known[horizon]).statistic if len(known)>=100 and known.score.nunique()>1 else np.nan
   r=dict(scheme=scheme,model=model,seed=seed,signal_date=date,horizon=horizon,raw_members=len(g),scored=len(valid),known_labels=len(known),unknown_labels=len(valid)-len(known),rank_ic=ic)
   for q in range(1,6):
    a=valid.loc[valid.quintile.eq(q),horizon];r[f'q{q}']=a.mean() if a.notna().all() and len(a)>0 else np.nan;r[f'q{q}_unknown']=int(a.isna().sum())
   r['q5_q1']=r['q5']-r['q1'];rows.append(r)
 detail=pd.DataFrame(rows);dest=OUT/'path_a';dest.mkdir(parents=True,exist_ok=True);detail.to_csv(dest/f'{scheme}_ranking_weekly.csv',index=False)
 summaries=[]
 for (model,seed,horizon),g in detail.groupby(['model','seed','horizon']):
  x=g.rank_ic.dropna();lo,hi=block_ci(x);spread=g.q5_q1.dropna();sl,sh=block_ci(spread)
  summaries.append(dict(scheme=scheme,model=model,seed=seed,horizon=horizon,weeks=len(g),known_ic_weeks=len(x),mean_rank_ic=x.mean(),raw_icir=x.mean()/x.std(ddof=1),ic_positive_fraction=x.gt(0).mean(),ic_ci_low=lo,ic_ci_high=hi,mean_q5_q1=spread.mean(),spread_ci_low=sl,spread_ci_high=sh,unknown_scored_labels=int(g.unknown_labels.sum()),q5_known_weeks=int(g.q5.notna().sum())))
 pd.DataFrame(summaries).to_csv(dest/f'{scheme}_ranking_summary.csv',index=False)
 detail['year']=pd.to_datetime(detail.signal_date).dt.year;detail['quarter']=pd.to_datetime(detail.signal_date).dt.to_period('Q').astype(str)
 for period in ['year','quarter']:
  detail.groupby(['model','seed','horizon',period]).agg(rank_ic=('rank_ic','mean'),ic_weeks=('rank_ic','count'),q5_q1=('q5_q1','mean'),unknown_labels=('unknown_labels','sum')).to_csv(dest/f'{scheme}_ranking_{period}.csv')
 save_json(OUT/'manifests'/f'path_a_{scheme}_consumption.json',consumption)
 print('ranking evaluated',scheme,len(detail),flush=True)
if __name__=='__main__':
 import sys
 evaluate(sys.argv[1] if len(sys.argv)>1 else 'expanding')
