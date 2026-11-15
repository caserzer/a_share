from common import *
import pandas as pd
from scipy.stats import norm
out=ROOT/'outputs/r269';keys=['era','level','horizon','variant','method','date'];a=pd.read_parquet(out/'snapshot/metrics.parquet').set_index(keys);b=pd.read_parquet(out/'signal/metrics.parquet').set_index(keys);d=pd.read_parquet(out/'clock_date_deltas.parquet').set_index(keys);assert a.index.equals(b.index) and d.index.equals(a.index);assert np.allclose(d.ic_delta,a.ic-b.ic,equal_nan=True);d=d.reset_index();s=pd.read_csv(out/'clock_summary.csv');checks=0
for row in s.to_dict('records'):
 g=d.copy()
 for k in keys[:-1]:g=g[g[k].eq(row[k])]
 g=g.dropna(subset=['ic_delta']).sort_values('date');n=len(g)
 if row['status']=='no_fit':assert n==0;continue
 delta=g.set_index('date').ic_delta;u=pd.Series(delta.to_numpy()-delta.mean(),index=delta.index.to_period('M').astype('int64'));v=float((u*u).sum());lag=3 if row['horizon']==20 else 6
 for k in range(1,lag+1):v+=2*(1-k/(lag+1))*float(np.nansum(u.to_numpy()*u.reindex(u.index-k).to_numpy()))
 se=np.sqrt(max(0,v))/n;bounds=delta.mean()+np.array([-1,1])*norm.ppf(1-.05/840)*se;assert np.allclose(bounds,[row['low_family'],row['high_family']],atol=1e-12);annual=delta.groupby(delta.index.year).mean();assert row['historical_support']==bool(n>=24 and len(annual)>=3 and annual.gt(0).all() and bounds[0]>0);checks+=1
for clock in ['signal','snapshot']:assert json.loads((out/clock/'independent_verification.json').read_text())['status']=='PASS'
js(out/'independent_verification.json',dict(status='PASS',paired_metric_groups=len(d),evaluated_clock_comparisons=checks,planned_clock_comparisons=180,planned_within_clock_comparisons=240,normal_equation_checks=134748,scope='Both independent weighted normal-equation verifiers plus paired metrics, independent calendar-lag uncertainty and support gates; no independent prospective or portfolio certification',adoption=False));print('CROSS VERIFIED',checks,len(d))
