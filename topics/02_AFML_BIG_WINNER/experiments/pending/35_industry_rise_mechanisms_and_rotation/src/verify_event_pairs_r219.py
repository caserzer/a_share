from common import *
import pandas as pd
out=ROOT/'outputs/r219';d=pd.read_parquet(out/'decisions.parquet');q=pd.read_csv(out/'comparisons.csv');keys=['family','era','level','target_type','horizon'];groups={k:g for k,g in d.groupby(keys)};checks=0;maximum=0.
for row in q.to_dict('records'):
 g=groups[tuple(row[x] for x in keys)];am,av=row['first'].rsplit('_',1);bm,bv=row['second'].rsplit('_',1);a=g[g.method.eq(am)&g.variant.eq(av)].set_index(['event_id','date']);b=g[g.method.eq(bm)&g.variant.eq(bv)].set_index(['event_id','date']);assert a.index.equals(b.index);known=a.status.eq('valid')&b.status.eq('valid');assert known.sum()==row['matched'];assert known.index.get_level_values('date')[known].nunique()==row['dates']
 for metric in ['gross','net20','net50','drawdown']:
  delta=(a.loc[known,metric]-b.loc[known,metric]);values=[sum(v)/len(v) for _,v in delta.groupby(level='date')];expected=sum(values)/len(values) if values else np.nan;err=abs(expected-row['delta_'+metric]);assert np.isclose(expected,row['delta_'+metric],atol=1e-12,equal_nan=True);maximum=max(maximum,err if np.isfinite(err) else 0);checks+=1
baseline=[]
for key,g in d.groupby(keys+['method','variant']):
 v=g[g.status.eq('valid')];rec=dict(zip(keys+['method','variant'],key),known=len(v),dates=v.date.nunique())
 for baseline_name in ['event','reference']:rec['net50_vs_always_'+baseline_name]=(v.net50-v['always_'+baseline_name+'_net50']).groupby(v.date).mean().mean()
 baseline.append(rec)
pd.DataFrame(baseline).to_csv(out/'fixed_baselines.csv',index=False);js(out/'independent_pair_verification.json',dict(status='PASS',checks=checks,max_error=maximum,scope='All same-event paired identities/counts and independent equal-date mean differences; additional fixed-reference diagnostic',script_sha256=sha(__file__)));print('PASS',checks,maximum)
