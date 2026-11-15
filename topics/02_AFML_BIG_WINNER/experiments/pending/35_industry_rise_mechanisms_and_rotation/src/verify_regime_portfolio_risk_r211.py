from common import *
import pandas as pd
out=ROOT/'outputs/r211';s=pd.read_csv(out/'summary.csv');d=pd.read_parquet(out/'daily_returns.parquet');i=pd.read_csv(out/'intervals.csv');keys=['era','level','cohort','horizon','method'];dg={k:g.sort_values('date') for k,g in d.groupby(keys)};ig={k:g for k,g in i.groupby(keys)};checks=0;maximum=0
for row in s.to_dict('records'):
 key=tuple(row[k] for k in keys);interval=ig[key];good=interval[interval.status.eq('valid')];whole=len(good)==len(interval) and len(good)>0;assert whole==row['whole_path_valid'];assert row['valid']==len(good)
 if not whole:
  for col in ['total_return','cagr','drawdown','vol','beta']:assert pd.isna(row.get(col))
  continue
 g=dg[key];cost=row['cost'];rr=g[cost].to_numpy();w=np.cumprod(1+rr);rate={'gross':0,'net20':.002,'net50':.005}[cost];expected=np.prod(1+good[cost])*(1-rate);assert np.isclose(w[-1],expected,rtol=1e-11)
 values={'total_return':w[-1]-1,'cagr':w[-1]**(365.25/(g.date.max()-g.date.min()).days)-1,'drawdown':np.min(w/np.maximum.accumulate(np.r_[1.,w])[1:]-1),'vol':np.std(rr,ddof=1)*np.sqrt(252),'beta':np.cov(rr,g.benchmark,ddof=1)[0,1]/np.var(g.benchmark,ddof=1),'mean_interval_return':good[cost].mean(),'mean_turnover':good.turnover.mean()}
 for col,value in values.items():
  err=abs(value-row[col]);maximum=max(maximum,err);assert err<1e-10;checks+=1
js(out/'independent_risk_verification.json',dict(status='PASS',checks=checks,max_error=maximum,scope='All complete path compounded returns, final fees, CAGR, drawdown, volatility, beta, mean intervals and turnover; all incomplete curves withheld',script_sha256=sha(__file__)))
print('PASS risk',checks,maximum)
