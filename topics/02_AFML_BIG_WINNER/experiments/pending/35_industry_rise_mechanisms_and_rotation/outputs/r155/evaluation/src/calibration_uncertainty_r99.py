import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r99';out.mkdir(exist_ok=True);pp=ROOT/'outputs/r97/predictions.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet';p=pd.read_parquet(pp);calendar=pd.DatetimeIndex(pd.read_parquet(bp).index).sort_values();dates=[];blocks=[];summary=[];draws=[]
 for key,g in p.groupby(['era','level','year']):
  v=g[g.y.notna()].copy();v['difference']=(v.daily_probability-v.y)**2-(v.monthly_probability-v.y)**2;daily=v.groupby('date').agg(difference=('difference','mean'),rows=('y','size'));cal=calendar[calendar.year==key[2]];indices={d:i for i,d in enumerate(cal)};daily['session_index']=[indices[d] for d in daily.index];daily['block']=daily.session_index//21
  for date,x in daily.iterrows():dates.append(dict(zip(['era','level','year'],key),date=date,session_index=int(x.session_index),block=int(x.block),rows=int(x.rows),difference=x.difference))
  block= daily.groupby('block').agg(total=('difference','sum'),dates=('difference','size'),first=('session_index','min'),last=('session_index','max'))
  for b in range((len(cal)+20)//21):
   x=block.loc[b] if b in block.index else None;blocks.append(dict(zip(['era','level','year'],key),block=b,calendar_start=cal[b*21],calendar_end=cal[min((b+1)*21,len(cal))-1],observed_dates=int(x.dates) if x is not None else 0,total=float(x.total) if x is not None else None))
  rec=dict(zip(['era','level','year'],key),dates=len(daily),calendar_sessions=len(cal),missing_dates=len(cal)-len(daily),observed_blocks=len(block),minimum_dates_per_block=int(block.dates.min()),maximum_dates_per_block=int(block.dates.max()),point=float(daily.difference.mean()),status='evaluated' if len(block)>=8 else 'insufficient_blocks')
  if len(block)>=8:
   rng=np.random.default_rng(35099);index=rng.integers(0,len(block),size=(20000,len(block)));sim=block.total.to_numpy()[index].sum(axis=1)/block.dates.to_numpy()[index].sum(axis=1);lo,hi=np.quantile(sim,[.025,.975]);adjlo,adjhi=np.quantile(sim,[.05/16,1-.05/16]);rec.update(low95=float(lo),high95=float(hi),low_family=float(adjlo),high_family=float(adjhi));draws.extend(dict(zip(['era','level','year'],key),replicate=i,difference=float(x)) for i,x in enumerate(sim))
  summary.append(rec)
 js(out/'date_differences.json',dates);js(out/'calendar_blocks.json',blocks);js(out/'summary.json',summary);pd.DataFrame(draws).to_parquet(out/'resamples.parquet',index=False);paths=[pp,bp,ROOT/'outputs/r97/verification.json',ROOT/'protocols/r99.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},folds=len(summary),replicates=20000,family=8,no_new_training=True));print(json.dumps(summary,default=str))
if __name__=='__main__':run()
