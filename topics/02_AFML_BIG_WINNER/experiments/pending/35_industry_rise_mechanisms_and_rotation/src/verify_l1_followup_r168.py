"""Independent scalar reconstruction and all summary denominators."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r168';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 z=pd.read_parquet(out/'followup.parquet');d=pd.read_parquet(ROOT/'data/l1_daily.parquet');b=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
 lookup={(code,block):g.sort_values('date').reset_index(drop=True) for (code,block),g in d.groupby(['industry_code','block'])};checked=0
 for row in z.drop_duplicates(KEY+['date']).to_dict('records'):
  g=lookup[(row['industry_code'],row['block'])];ix=g.index[g.date.eq(row['date'])].item()
  for h in [5,20,60]:
   w=g.iloc[ix+1:ix+h+2]
   if len(w)!=h+1:assert pd.isna(row[f'return{h}']);continue
   ret=w.nav.iloc[-1]/w.nav.iloc[0]-1;bm=b.loc[w.date.iloc[-1]]/b.loc[w.date.iloc[0]]-1;peak=w.nav.iloc[0];dd=0
   for nav in w.nav:peak=max(peak,nav);dd=min(dd,nav/peak-1)
   for name,val in [(f'return{h}',ret),(f'excess{h}',ret-bm),(f'drawdown{h}',dd)]:assert np.isclose(row[name],val,atol=1e-12)
   checked+=1
  if pd.notna(row['return60']):
   a=(1+row['return60'])/(1+row['return20'])-1;m=(1+row['market60'])/(1+row['market20'])-1;assert np.isclose(row['continuation_excess20_60'],a-m)
 for row in pd.read_csv(out/'followup_summary.csv').to_dict('records'):
  g=z[z.strategy.eq(row['strategy'])];g=g if row['year']==0 else g[g.date.dt.year.eq(row['year'])];h=row['horizon'];q=g.dropna(subset=[f'return{h}',f'excess{h}'])
  assert (len(g),len(q),len(g)-len(q))==(row['alerts'],row['complete'],row['unknown'])
  for name,val in [('absolute_mean',q[f'return{h}'].mean()),('excess_mean',q[f'excess{h}'].mean()),('mean_drawdown',q[f'drawdown{h}'].mean()),('positive_absolute',q[f'return{h}'].gt(0).mean())]:assert np.isclose(row[name],val,equal_nan=True)
 for row in pd.read_csv(out/'continuation.csv').to_dict('records'):
  g=z[z.strategy.eq(row['strategy'])];g=g if row['year']==0 else g[g.date.dt.year.eq(row['year'])]
  if row['cohort']!='all':g=g[g.success20.eq(1 if row['cohort']=='success20' else 0)]
  q=g.dropna(subset=['continuation_excess20_60']);assert (len(g),len(q),len(g)-len(q))==(row['selected'],row['complete'],row['unknown'])
  for name,val in [('absolute_increment',q.continuation20_60.mean()),('relative_increment',q.continuation_excess20_60.mean()),('positive_relative',q.continuation_excess20_60.gt(0).mean()),('breadth_change20',q.breadth_change20.mean())]:assert np.isclose(row[name],val,equal_nan=True)
 js(out/'verification.json',dict(status='PASS',alert_rows=len(z),unique_origins=len(z.drop_duplicates(KEY+['date'])),complete_horizon_paths_checked=checked,summary_rows=27,continuation_rows=27,adoption=False,calibrated=False))
 print('PASS L1 followup',len(z),checked)
if __name__=='__main__':run()
