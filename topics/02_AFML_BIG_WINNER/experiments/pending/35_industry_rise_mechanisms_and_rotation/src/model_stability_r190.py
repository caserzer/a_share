"""Calendar-year stability and fixed tails, refusing incomplete paths."""
from common import *
import pandas as pd
K=['era','level','cohort','horizon','method']

def metrics(g,cost):
 r=g[cost].to_numpy();w=np.cumprod(1+r);peak=np.maximum.accumulate(np.r_[1.,w])[1:]
 q=float(np.quantile(r,.05));negative=g.benchmark.lt(0)
 # Independent scalar product and running maximum.
 value=1.;high=1.;dd=0.
 for x in r:value*=1+x;high=max(high,value);dd=min(dd,value/high-1)
 assert abs(value-w[-1])<1e-11 and abs(dd-np.min(w/peak-1))<1e-12
 return dict(days=len(g),start=str(g.date.min().date()),end=str(g.date.max().date()),total_return=value-1,drawdown=dd,min_day=float(min(r)),q05=q,tail_mean=float(r[r<=q].mean()),negative_market_days=int(negative.sum()),mean_negative_market=float(g.loc[negative,cost].mean()),benchmark_return=float(np.prod(1+g.benchmark)-1))

def run():
 out=ROOT/'outputs/r190';out.mkdir(exist_ok=True)
 root=ROOT/'outputs/r189';proof=json.loads((root/'verification.json').read_text())
 for x,h in proof['outputs'].items():assert sha(root/x)==h
 d=pd.read_parquet(root/'daily_returns.parquet');s=pd.read_csv(root/'summary.csv');records=[];ledger=[]
 for key,g in d.groupby(K):
  g=g.sort_values('date');ident=dict(zip(K,key));assert not g.date.duplicated().any()
  valid=bool(g.whole_path_valid.all());ledger.append(dict(ident,eligible=valid,reason='complete' if valid else 'whole_path_incomplete'))
  if not valid:continue
  ss=s
  for k,v in ident.items():ss=ss[ss[k].eq(v)]
  for cost in ['gross','net20','net50']:
   full=metrics(g,cost);old=ss[ss.cost.eq(cost)].iloc[0]
   assert np.isclose(full['total_return'],old.total_return,atol=1e-11) and np.isclose(full['drawdown'],old.drawdown,atol=1e-12)
   records.append(dict(ident,cost=cost,year='all',**full));annual_product=1.
   for year,a in g.groupby(g.date.dt.year):
    m=metrics(a,cost);annual_product*=1+m['total_return'];records.append(dict(ident,cost=cost,year=str(year),**m))
   assert np.isclose(annual_product,1+full['total_return'],atol=1e-11)
 result=pd.DataFrame(records);result.to_csv(out/'metrics.csv',index=False);pd.DataFrame(ledger).to_csv(out/'eligibility.csv',index=False)
 pairs=[];pair_ledger=[]
 for key,g in d.groupby(K[:-1]):
  ident=dict(zip(K[:-1],key));f=g[g.method.eq('F')].sort_values('date');e=g[g.method.eq(key[2])].sort_values('date')
  valid=bool(len(f) and len(e) and f.whole_path_valid.all() and e.whole_path_valid.all())
  if valid:assert f.date.reset_index(drop=True).equals(e.date.reset_index(drop=True))
  pair_ledger.append(dict(ident,eligible=valid))
  if not valid:continue
  z=result
  for k,v in ident.items():z=z[z[k].eq(v)]
  for (cost,year),a in z.groupby(['cost','year']):
   x=a[a.method.eq('F')].iloc[0];y=a[a.method.eq(key[2])].iloc[0]
   pairs.append(dict(ident,cost=cost,year=year,start=x.start,end=x.end,days=x.days,f_return=x.total_return,extension_return=y.total_return,delta_return=y.total_return-x.total_return,delta_drawdown=y.drawdown-x.drawdown,delta_tail_mean=y.tail_mean-x.tail_mean))
 pd.DataFrame(pairs).to_csv(out/'paired_metrics.csv',index=False);pd.DataFrame(pair_ledger).to_csv(out/'paired_eligibility.csv',index=False)
 inputs=[root/'verification.json',root/'independent_verification.json',root/'daily_returns.parquet',root/'summary.csv',ROOT/'protocols/r190.json',Path(__file__),ROOT/'src/common.py']
 files=['metrics.csv','eligibility.csv','paired_metrics.csv','paired_eligibility.csv']
 js(out/'verification.json',dict(status='PASS',scope='Original source hashes, scalar wealth/peak checks, full R189 return/drawdown matching, annual/full compounding, exact paired grids',groups=len(ledger),eligible=sum(x['eligible'] for x in ledger),paired_groups=len(pair_ledger),eligible_pairs=sum(x['eligible'] for x in pair_ledger),inputs={str(x):sha(x) for x in inputs},outputs={x:sha(out/x) for x in files}))
 print(pd.DataFrame(pairs).query("era=='SW2021' and horizon==20 and cost=='net20'").to_string(index=False))
if __name__=='__main__':run()
