"""Causal, ratio-based features. No future labels or future membership filters."""
import numpy as np
import pandas as pd
from common import zscore

def dictionary():
 rows=[]
 def add(name,formula,group='core'):rows.append(dict(feature=name,formula=formula,group=group,availability='signal close; retrospective source proxy'))
 for k in range(20):
  add(f'ret_lag{k}',f'close/close.shift(1)-1 at lag{k}')
  add(f'xsret_lag{k}',f'daily contemporaneous CSI300 zscore return ddof0, min100; lag{k}')
 for h in [1,3,5,10,20,60]:add(f'mom{h}',f'close/close.shift({h})-1')
 add('seg2_5','close.shift(1)/close.shift(5)-1');add('seg6_20','close.shift(5)/close.shift(20)-1')
 for h in [5,20,60]:
  for name,formula in [('vol',f'return rolling{h} std ddof0'),('amp',f'rolling{h} mean(high/low-1)'),('dd',f'close/rolling{h} max(close)-1'),('pos',f'(close-rolling{h} min(low))/(rolling{h} max(high)-rolling{h} min(low))')]:add(f'{name}{h}',formula)
  for field in ['volume','money','turnover']:add(f'{field}_rel{h}',f'{field}/rolling{h} mean({field})')
  for name in ['mom','vol','dd']:add(f'market_{name}{h}',f'CSI300 price index {name}{h}')
 for h in [5,10,20,60]:
  add(f'body{h}',f'rolling{h} mean((close-open)/(high-low))','extension')
  add(f'upvolume{h}',f'rolling{h} sum(volume*I(return>0))/rolling{h} sum(volume)','extension')
  add(f'price_volume_corr{h}',f'rolling{h} corr(return,volume.pct_change)','extension')
 return pd.DataFrame(rows)

def compute(c,o,h,l,v,m,tr,member,market):
 ret=c.pct_change(fill_method=None)
 xs=ret.where(member).apply(lambda r:zscore(r),axis=1)
 f={}
 for k in range(20):f[f'ret_lag{k}']=ret.shift(k);f[f'xsret_lag{k}']=xs.shift(k)
 for n in [1,3,5,10,20,60]:f[f'mom{n}']=c/c.shift(n)-1
 f['seg2_5']=c.shift(1)/c.shift(5)-1;f['seg6_20']=c.shift(5)/c.shift(20)-1
 for n in [5,20,60]:
  f[f'vol{n}']=ret.rolling(n).std(ddof=0);f[f'amp{n}']=(h/l-1).rolling(n).mean()
  f[f'dd{n}']=c/c.rolling(n).max()-1;lo=l.rolling(n).min();hi=h.rolling(n).max();f[f'pos{n}']=(c-lo)/(hi-lo)
  for name,x in [('volume',v),('money',m),('turnover',tr)]:f[f'{name}_rel{n}']=x/x.rolling(n).mean()
  for name,series in [('mom',market/market.shift(n)-1),('vol',market.pct_change(fill_method=None).rolling(n).std(ddof=0)),('dd',market/market.rolling(n).max()-1)]:
   f[f'market_{name}{n}']=pd.DataFrame(np.repeat(series.to_numpy()[:,None],len(c.columns),axis=1),index=c.index,columns=c.columns)
 for n in [5,10,20,60]:
  f[f'body{n}']=((c-o)/(h-l)).rolling(n).mean()
  f[f'upvolume{n}']=v.where(ret.notna()).mul(ret.gt(0)).rolling(n).sum()/v.rolling(n).sum()
  f[f'price_volume_corr{n}']=ret.rolling(n).corr(v.pct_change(fill_method=None))
 return {k:x.replace([np.inf,-np.inf],np.nan) for k,x in f.items()}
