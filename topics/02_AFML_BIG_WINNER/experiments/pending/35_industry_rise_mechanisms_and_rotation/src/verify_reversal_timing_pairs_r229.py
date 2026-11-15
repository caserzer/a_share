from pathlib import Path
import json,hashlib
import pandas as pd,numpy as np
r=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/35_industry_rise_mechanisms_and_rotation');o=r/'outputs/r229';assert json.loads((o/'independent_verification.json').read_text())['status']=='PASS'
d=pd.read_csv(o/'date_metrics.csv');q=pd.read_csv(o/'comparisons.csv');keys=['source_round','family','era','level','cohort','method','horizon','objective'];lookup={k:g for k,g in d.groupby(keys)}
for row in q.to_dict('records'):
 g=lookup[tuple(row[k] for k in keys)];variant=row['comparison'].split('-')[0]
 for metric in ['precision','recall','mean_entry_lead']:
  a=g[g.variant.eq(variant)].set_index('date')[metric];b=g[g.variant.eq('base')].set_index('date')[metric];x=a-b;assert int(x.notna().sum())==row[metric+'_paired_dates'];assert np.isclose(x.mean(),row['delta_'+metric],equal_nan=True)
(o/'independent_pair_verification.json').write_text(json.dumps({'status':'PASS','comparisons':len(q),'metrics':3,'scope':'Date-paired metric deltas and known-date counts'},indent=2)+'\n')
