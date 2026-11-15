"""Joint calendar-block uncertainty for fixed L1 process comparisons."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r161';out.mkdir(parents=True,exist_ok=True);prior=ROOT/'outputs/r160';a=pd.read_parquet(prior/'alerts.parquet');h=pd.read_parquet(prior/'event_hits.parquet');s=pd.read_parquet(prior/'candidate_scores.parquet');calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);blocks=[];summaries=[];draws=[]
 for year in [2025,2026]:
  end=s.loc[s.date.dt.year.eq(year),'date'].max();cal=calendar[(calendar.year==year)&(calendar<=end)];mapping={d:i//21 for i,d in enumerate(cal)};n=(len(cal)+20)//21;rng=np.random.default_rng(35161);idx=rng.integers(0,n,size=(20000,n))
  for strategy in ['daily','monthly','daily_cooldown20']:
   for baseline in ['F','momentum']:
    for metric in ['precision','recall']:
     counts=[]
     for method in ['raw_logit',baseline]:
      q=a if metric=='precision' else h;q=q[q.date.dt.year.eq(year)&q.strategy.eq(strategy)&q.method.eq(method)].copy();q=q[q.y.notna()] if metric=='precision' else q[q.evaluable];q['b']=q.date.map(mapping);assert q.b.notna().all();target='y' if metric=='precision' else 'hit';ag=q.groupby('b')[target].agg(['sum','count']).reindex(range(n),fill_value=0);counts.append(ag[['sum','count']].to_numpy(float))
     x,y=counts;point=x[:,0].sum()/x[:,1].sum()-y[:,0].sum()/y[:,1].sum();key=dict(year=year,strategy=strategy,baseline=baseline,metric=metric)
     for b in range(n):blocks.append(dict(**key,block=b,start=cal[b*21],end=cal[min((b+1)*21,len(cal))-1],model_success=int(x[b,0]),model_count=int(x[b,1]),baseline_success=int(y[b,0]),baseline_count=int(y[b,1])))
     with np.errstate(divide='ignore',invalid='ignore'):sim=x[:,0][idx].sum(axis=1)/x[:,1][idx].sum(axis=1)-y[:,0][idx].sum(axis=1)/y[:,1][idx].sum(axis=1)
     invalid=int((~np.isfinite(sim)).sum());rec=dict(**key,point=point,blocks=n,calendar_sessions=len(cal),invalid_draws=invalid,status='evaluated' if n>=8 and invalid==0 else 'insufficient_blocks_or_denominator')
     if rec['status']=='evaluated':
      lo,hi,al,ah=np.quantile(sim,[.025,.975,.05/48,1-.05/48]);rec.update(low95=lo,high95=hi,low_family=al,high_family=ah,family_conclusion='model_better' if al>0 else 'model_worse' if ah<0 else 'inconclusive')
     summaries.append(rec);draws.extend(dict(**key,replicate=i,difference=float(v)) for i,v in enumerate(sim))
 pd.DataFrame(blocks).to_csv(out/'blocks.csv',index=False);pd.DataFrame(summaries).to_csv(out/'summary.csv',index=False);pd.DataFrame(draws).to_parquet(out/'resamples.parquet',index=False);paths=[prior/'alerts.parquet',prior/'event_hits.parquet',prior/'candidate_scores.parquet',prior/'verification.json',CACHE/'forecast_v5/CSI_ALL.parquet',ROOT/'protocols/r161.json',Path(__file__)];js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in paths},comparisons=len(summaries),replicates=20000,family=24,no_refit=True));print(pd.DataFrame(summaries).to_string(index=False))
if __name__=='__main__':run()
