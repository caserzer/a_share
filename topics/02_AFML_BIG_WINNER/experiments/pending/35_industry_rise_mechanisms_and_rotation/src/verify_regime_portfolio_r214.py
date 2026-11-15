"""Verify selections independently of portfolio engine, including unknown paths."""
from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r214';proof=json.loads((out/'verification.json').read_text())
 for path,h in proof['inputs'].items():assert sha(path)==h
 for path,h in proof['outputs'].items():assert sha(out/path)==h
 p=pd.read_parquet(ROOT/'outputs/r214/mapped_predictions.parquet');p=p[p.task.eq('return')]
 prices=pd.read_parquet(ROOT/'outputs/r214/combined_prices.parquet');market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
 cal=pd.DatetimeIndex(market.index);lookup={k:v.set_index('date') for k,v in prices.groupby(KEY)}
 holdings=pd.read_parquet(out/'holdings.parquet');intervals=pd.read_csv(out/'intervals.csv',parse_dates=['origin','entry','exit']);checked=0;path_cache={}
 pmap={key:g for key,g in p.groupby(['era','level','cohort','horizon','method','date'])}
 hmap={key:g for key,g in holdings.groupby(['era','level','cohort','horizon','method','origin'])}
 k=['era','level','cohort','horizon','method']
 for key,g in intervals.groupby(k):
  drift={}
  for rec in g.sort_values('origin').to_dict('records'):
   source_method='base' if rec['method']=='equal' else rec['method']
   s=pmap.get(tuple(rec[c] for c in ['era','level','cohort','horizon'])+(source_method,rec['origin']),p.iloc[:0])
   hh=hmap.get(tuple(rec[c] for c in k)+(rec['origin'],),holdings.iloc[:0])
   if s.empty:assert rec['status']=='missing_prediction' and hh.empty;drift={};continue
   ordered=sorted(s.to_dict('records'),key=lambda x:(-x['prediction'],x['industry_code']))
   selected=ordered if rec['method']=='equal' else ordered[:max(1,int(np.ceil(len(s)*.2)))]
   codes={x['industry_code'] for x in selected};assert codes==set(hh.industry_code);assert np.allclose(hh.weight,1/len(codes))
   dates=cal[(cal>=rec['entry'])&(cal<=rec['exit'])];factors={};bad=[]
   for c in codes:
    pk=(rec['era'],rec['level'],c,rec['entry'],rec['exit'])
    if pk not in path_cache:
     a=lookup.get(pk[:3]);value=None
     if a is not None:
      a=a.reindex(dates)
      if not a.nav.isna().any() and len(set(a.block.dropna()))==1:value=float(a.nav.iloc[-1]/a.nav.iloc[0])
     path_cache[pk]=value
    if path_cache[pk] is None:bad.append(c)
    else:factors[c]=path_cache[pk]
   if bad:assert rec['status']=='missing_selected_path';drift={};continue
   assert rec['status']=='valid'
   end=sum(factors.values())/len(codes)
   buy=sum(max(1/len(codes)-drift.get(c,0),0) for c in codes)
   sell=sum(max(w-(1/len(codes) if c in codes else 0),0) for c,w in drift.items())
   t=buy+sell
   assert abs(t-rec['turnover'])<1e-12 and abs(end-1-rec['gross'])<1e-12
   for cost,rate in [('net20',.002),('net50',.005)]:assert abs((1-rate*t)*end-1-rec[cost])<1e-12
   drift={c:f/len(codes)/end for c,f in factors.items()};checked+=1
 js(out/'independent_verification.json',dict(status='PASS',valid_intervals_checked=checked,scope='Independent selection sorting, full calendar path coverage/block, endpoint value, buys plus sells and fee algebra',verifier_sha256=sha(__file__),receipt_sha256=sha(out/'verification.json')))
 print('PASS',checked)
if __name__=='__main__':run()
