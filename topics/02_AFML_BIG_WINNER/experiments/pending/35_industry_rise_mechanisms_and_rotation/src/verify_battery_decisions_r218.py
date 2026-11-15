from common import *
import pandas as pd
out=ROOT/'outputs/r218';d=pd.read_parquet(out/'decisions.parquet');p=pd.read_parquet(ROOT/'outputs/r198/predictions.parquet');k=KEY+['horizon','method','variant','date'];q=d.merge(p,on=k,validate='one_to_one',suffixes=('_out','_src'));assert len(q)==len(p)==len(d);assert np.array_equal(q.prediction_out,q.prediction_src);assert q.choose_industry.eq(q.prediction_src.gt(0)).all();price=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;lookup={k:g.set_index('date') for k,g in price.groupby(KEY)};cache={};checks=0;maximum=0
for row in d.to_dict('records'):
 key=tuple(row[c] for c in KEY)+(row['date'],row['horizon'])
 if key not in cache:
  e=row['entry_date'];x=row['maturity'];known=pd.notna(e) and pd.notna(x) and e in market.index and x in market.index;v=None
  if known:
   dates=market.loc[e:x].index;a=lookup[key[:3]].reindex(dates);known=a.nav.notna().all() and a.block.nunique()==1
   if known:
    industry=a.nav.to_numpy()/a.nav.iloc[0];bench=market.loc[dates].to_numpy()/market.loc[e];assert len(dates)==row['horizon']+1;v=(industry,bench)
  cache[key]=v
 paths=cache[key];assert (paths is not None)==(row['status']=='valid')
 if paths is None:continue
 a,b=paths;chosen=a if row['choose_industry'] else b;ret=chosen[-1]-1;peak=1.;dd=0.
 for value in chosen:peak=max(peak,value);dd=min(dd,value/peak-1)
 values={'gross':ret,'drawdown':dd,'excess':ret-(b[-1]-1)}
 for label,cost in [('net20',.002),('net50',.005)]:values[label]=chosen[-1]*(1-cost)-(1+cost);values['industry_'+label]=a[-1]*(1-cost)-(1+cost);values['market_'+label]=b[-1]*(1-cost)-(1+cost)
 for col,v in values.items():err=abs(row[col]-v);assert err<1e-12;maximum=max(maximum,err);checks+=1
 assert bool(row['wrong_industry'])==(row['choose_industry'] and a[-1]<b[-1]);assert bool(row['missed_positive'])==(not row['choose_industry'] and a[-1]>b[-1])
js(out/'independent_verification.json',dict(status='PASS',forecast_choices=len(q),unique_paths=len(cache),value_checks=checks,max_error=maximum,scope='All original predictions/zero-boundary choices, complete original price paths, original horizons, cashflow fees, sequential peak drawdown and missed/wrong direction flags',script_sha256=sha(__file__)));print('PASS',len(q),checks,maximum)
