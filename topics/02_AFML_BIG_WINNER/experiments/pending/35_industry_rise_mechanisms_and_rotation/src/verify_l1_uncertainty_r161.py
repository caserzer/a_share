"""Reconstruct every calendar block and resampled ratio difference independently."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r161';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 a=pd.read_parquet(ROOT/'outputs/r160/alerts.parquet');events=pd.read_parquet(ROOT/'outputs/r160/event_hits.parquet');scores=pd.read_parquet(ROOT/'outputs/r160/candidate_scores.parquet');blocks=pd.read_csv(out/'blocks.csv',parse_dates=['start','end']);summary=pd.read_csv(out/'summary.csv');draws=pd.read_parquet(out/'resamples.parquet');old=pd.read_csv(ROOT/'outputs/r160/comparisons.csv');calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);assert len(summary)==24 and len(draws)==480000;checked=0
 for row in summary.itertuples():
  key=['year','strategy','baseline','metric'];b=blocks;ds=draws
  for k in key:b=b[b[k].eq(getattr(row,k))];ds=ds[ds[k].eq(getattr(row,k))]
  b=b.sort_values('block');ds=ds.sort_values('replicate');cal=calendar[(calendar.year==row.year)&(calendar<=scores.loc[scores.date.dt.year.eq(row.year),'date'].max())];assert len(b)==row.blocks==(len(cal)+20)//21 and row.calendar_sessions==len(cal)
  for x in b.itertuples():
   assert x.start==cal[x.block*21] and x.end==cal[min((x.block+1)*21,len(cal))-1]
   source=a if row.metric=='precision' else events
   for method,prefix in [('raw_logit','model'),(row.baseline,'baseline')]:
    q=source[source.method.eq(method)&source.strategy.eq(row.strategy)&source.date.between(x.start,x.end)];q=q[q.y.notna()] if row.metric=='precision' else q[q.evaluable];target='y' if row.metric=='precision' else 'hit';assert len(q)==getattr(x,prefix+'_count') and q[target].sum()==getattr(x,prefix+'_success')
  original=old[old.year.eq(row.year)&old.strategy.eq(row.strategy)&old.baseline.eq(row.baseline)].iloc[0];assert np.isclose(row.point,original['delta_'+row.metric],atol=1e-12)
  xs=b.model_success.to_numpy();xn=b.model_count.to_numpy();ys=b.baseline_success.to_numpy();yn=b.baseline_count.to_numpy();rng=np.random.default_rng(35161);sim=[]
  for _ in range(20000):
   weights=np.bincount(rng.integers(0,len(b),size=len(b)),minlength=len(b));n1=weights@xn;n2=weights@yn;sim.append((weights@xs)/n1-(weights@ys)/n2 if n1 and n2 else np.nan)
  assert list(ds.replicate)==list(range(20000)) and np.allclose(ds.difference,sim,equal_nan=True,atol=1e-14);assert row.invalid_draws==sum(not np.isfinite(x) for x in sim)
  if row.status=='evaluated':
   assert row.blocks>=8 and row.invalid_draws==0
   for c,q in [('low95',.025),('high95',.975),('low_family',.05/48),('high_family',1-.05/48)]:assert np.isclose(getattr(row,c),np.quantile(sim,q),atol=1e-12)
   conclusion='model_better' if row.low_family>0 else 'model_worse' if row.high_family<0 else 'inconclusive';assert row.family_conclusion==conclusion
  checked+=len(sim)
 js(out/'verification.json',dict(status='PASS',comparisons=len(summary),calendar_block_rows=len(blocks),independent_replicate_checks=checked,scope='all original block counts, exact R160 ratio differences, independent multiplicity-weighted joint draws and every interval quantile',verifier_sha256=sha(Path(__file__))))
 print('R161 VERIFIED',len(summary),len(blocks),checked)
if __name__=='__main__':run()
