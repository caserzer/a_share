from common import *
import pandas as pd
out=ROOT/'outputs/r214';prices=pd.read_parquet(out/'combined_prices.parquet');market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=pd.DatetimeIndex(market.index);lookup={k:g.set_index('date').nav for k,g in prices.groupby(KEY)};i=pd.read_csv(out/'intervals.csv',parse_dates=['origin','entry','exit']);h=pd.read_parquet(out/'holdings.parquet');d=pd.read_parquet(out/'daily_returns.parquet');keys=['era','level','cohort','horizon','method'];hg={k:g for k,g in h.groupby(keys+['origin'])};dg={k:g for k,g in d.groupby(keys)};cache={};maximum=0.;checks=0
for key,g in i.groupby(keys):
 valid=g[g.status.eq('valid')].sort_values('origin');records=[]
 if valid.empty:continue
 for rec in valid.to_dict('records'):
  holding=hg[key+(rec['origin'],)];dates=cal[(cal>=rec['entry'])&(cal<=rec['exit'])];wealth=np.zeros(len(dates))
  for row in holding.to_dict('records'):
   pk=(row['era'],row['level'],row['industry_code'],rec['entry'],rec['exit'])
   if pk not in cache:
    v=lookup[pk[:3]].reindex(dates).to_numpy();cache[pk]=v/v[0]
   wealth+=row['weight']*cache[pk]
  daily=np.r_[1.,wealth[1:]/wealth[:-1]]
  for cost,rate in [('gross',0),('net20',.002),('net50',.005)]:
   factors=daily.copy();factors[0]*=1-rate*rec['turnover'];records.extend((day,cost,float(factor)) for day,factor in zip(dates,factors))
 for cost,rate in [('gross',0),('net20',.002),('net50',.005)]:records.append((valid.iloc[-1]['exit'],cost,1-rate))
 expected=pd.DataFrame(records,columns=['date','cost','factor']).groupby(['date','cost']).factor.prod().unstack()-1;actual=dg[key].set_index('date');assert set(expected.index)==set(actual.index)
 for cost in ['gross','net20','net50']:
  err=np.max(abs(expected[cost]-actual[cost]));assert err<1e-12;maximum=max(maximum,err);checks+=len(expected)
js(out/'independent_daily_verification.json',dict(status='PASS',daily_value_checks=checks,max_error=maximum,scope='Every daily portfolio factor independently reconstructed from saved holdings, original price levels and entry/final fees; includes discontinuous diagnostic fragments',code_sha256=sha(__file__)))
print('PASS daily',checks,maximum)
