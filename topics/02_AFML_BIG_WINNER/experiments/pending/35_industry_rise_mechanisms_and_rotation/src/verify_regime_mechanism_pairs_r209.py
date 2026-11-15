from common import *
import pandas as pd
from regime_uncertainty_r207 import IDENT
def canon(v):
 try:return str(float(v))
 except (ValueError,TypeError):return str(v)
out=ROOT/'outputs/r209';raw=pd.read_parquet(out/'paired_dates.parquet');checks=0;maximum=0.
for rnd in [197,198,199,200,201,202,205]:
 if rnd==198:
  source=pd.read_parquet(ROOT/'outputs/r198/predictions.parquet');source['negative_mse']=-(source.prediction-source.target)**2;source['family']='battery'
 else:source=pd.read_csv(ROOT/f'outputs/r{rnd}/date_metrics.csv',parse_dates=['date'])
 if 'family' not in source:source['family']='macro_interaction'
 cols=[c for c in IDENT if c in source and c!='method'];groups={tuple(canon(v) for v in k):g for k,g in source.groupby(cols,dropna=False)}
 for key,g in raw[raw['round'].eq(str(rnd))].groupby(cols+['method','metric'],dropna=False):
  sub=groups[tuple(canon(v) for v in key[:len(cols)])];a,b=key[-2].split('-minus-');metric=key[-1];src='utility' if metric in ['ic','brier_reduction'] and rnd in [199,200,201] else 'negative_mse' if metric=='mse_reduction' and rnd in [198,199,200,201] else 'mse' if metric=='mse_reduction' else metric
  left=sub[sub.method.eq(a)][['date','variant',src]];right=sub[sub.method.eq(b)][['date','variant',src]];paired=left.merge(right,on=['date','variant'],how='outer',validate='one_to_one');paired['delta']=(paired[src+'_x']-paired[src+'_y'])*(-1 if src=='mse' else 1)
  base=paired[paired.variant.eq('base')].set_index('date').delta
  for comparison,rows in g.groupby('comparison'):
   variant=comparison.removeprefix('mechanism_').removeprefix('increment_change_');p=paired[paired.variant.eq(variant)].set_index('date').delta
   if comparison.startswith('increment_change_'):p=p-base
   z=rows.set_index('date').delta;assert set(z.index)==set(p.index);v=p.reindex(z.index).to_numpy();w=z.to_numpy();assert np.allclose(v,w,atol=1e-12,equal_nan=True);err=np.nanmax(abs(v-w)) if np.isfinite(v-w).any() else 0;maximum=max(maximum,err);checks+=len(z)
js(out/'independent_pair_verification.json',dict(status='PASS',dated_checks=checks,max_error=maximum,scope='All raw mechanism pairs rebuilt by outer one-to-one date/variant merge; all incremental change contrasts recomputed',code_sha256=sha(__file__)))
print('PASS',checks,maximum)
