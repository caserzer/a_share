from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS
out=ROOT/'outputs/r228';d=pd.read_csv(out/'date_metrics.csv');q=pd.read_csv(out/'comparisons.csv');keys=[x for x in IDS if x!='variant']+['followup_cohort'];lookup={k:g for k,g in d.groupby(keys)};maximum=0.
for row in q.to_dict('records'):
 g=lookup[tuple(row[k] for k in keys)];variant=row['comparison'].split('-')[0];a=g[g.variant.eq(variant)].set_index('date');b=g[g.variant.eq('base')].set_index('date');values=[]
 for day in a.index:
  av=a.loc[day,row['metric']];bv=b.loc[day,row['metric']]
  if pd.notna(av) and pd.notna(bv):values.append(av-bv)
 mean=sum(values)/len(values) if values else np.nan;assert len(values)==row['paired_dates'];assert np.isclose(mean,row['delta'],atol=1e-12,equal_nan=True)
 if values:maximum=max(maximum,abs(mean-row['delta']))
js(out/'independent_pair_verification.json',dict(status='PASS',comparisons=len(q),max_error=maximum,code_sha256=sha(__file__),scope='Every paired-date difference and date-equal comparison mean'))
print(len(q),maximum)
