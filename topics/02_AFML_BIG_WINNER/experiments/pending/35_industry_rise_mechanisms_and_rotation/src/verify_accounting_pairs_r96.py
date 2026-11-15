import statistics
import pandas as pd
from pandas.testing import assert_frame_equal
from common import *
def run():
 out=ROOT/'outputs/r96';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h,p
 a=pd.read_parquet(ROOT/'outputs/r95/alerts.parquet');a=a[a.strategy.eq('monthly')].reset_index(drop=True);d=pd.read_parquet(out/'monthly_alerts.parquet');assert_frame_equal(d[a.columns],a);features=['past_excess20','past_excess60','mom20','mom60','vol20','dd60','breadth21','members'];panel=pd.read_parquet(ROOT/'data/monthly_panel.parquet').set_index(KEY+['date']);assert panel.index.is_unique
 for x in d.to_dict('records'):
  p=panel.loc[tuple(x[k] for k in KEY)+(x['date'],)]
  for f in features:assert (pd.isna(x[f]) and pd.isna(p[f])) or x[f]==p[f]
 groups={k:g for k,g in d.groupby(['era','level','date'])};ledger=json.loads((out/'date_ledger.json').read_text());assert len(ledger)==len(groups);paired=set()
 for x in ledger:
  key=x['era'],x['level'],pd.Timestamp(x['date']);g=groups[key];counts=g.accounting_group.value_counts();assert x['alerts']==len(g)
  for label in ['positive','negative','zero','unknown']:assert x[label]==counts.get(label,0)
  expected=x['positive']>0 and x['negative']>0;assert x['paired']==expected
  if expected:paired.add(key)
 contrasts=json.loads((out/'contrasts.json').read_text());metrics=['excess20','return20','continuation_excess20_60']+features;assert len(contrasts)==len(paired)*len(metrics);seen=set()
 for x in contrasts:
  key=x['era'],x['level'],pd.Timestamp(x['date']);assert key in paired;identity=key+(x['metric'],);assert identity not in seen;seen.add(identity);g=groups[key];pos=g[g.accounting_group.eq('positive')][x['metric']];neg=g[g.accounting_group.eq('negative')][x['metric']];assert x['positive']==len(pos) and x['negative']==len(neg) and x['positive_known']==pos.notna().sum() and x['negative_known']==neg.notna().sum();valid=all(pd.notna(v) for v in list(pos)+list(neg));assert x['status']==('complete' if valid else 'incomplete_group')
  if valid:
   p=statistics.mean(pos);n=statistics.mean(neg)
   for k,v in [('positive_mean',p),('negative_mean',n),('difference',p-n)]:assert np.isclose(x[k],v,rtol=1e-12,atol=1e-12)
  else:assert all(x[k] is None for k in ['positive_mean','negative_mean','difference'])
 summary=json.loads((out/'summary.json').read_text());assert len(summary)==len({(x['era'],x['level'],x['metric']) for x in contrasts})
 for s in summary:
  g=[x for x in contrasts if all(x[k]==s[k] for k in ['era','level','metric'])];q=[x for x in g if x['status']=='complete'];assert s['paired_dates']==len(g) and s['complete_dates']==len(q) and s['unknown_dates']==len(g)-len(q)
  for label in ['positive','negative']:assert s[label+'_rows']==sum(x[label] for x in q)
  assert s['positive_dates']==sum(x['difference']>0 for x in q) and s['negative_dates']==sum(x['difference']<0 for x in q)
  assert (not q and s['date_equal_difference'] is None) or np.isclose(s['date_equal_difference'],statistics.mean(x['difference'] for x in q))
 assert receipt['monthly_alerts']==len(d) and receipt['date_groups']==len(groups) and receipt['paired_date_groups']==len(paired)
 js(out/'verification.json',dict(status='PASS',monthly_alerts=len(d),date_groups=len(groups),paired_date_groups=len(paired),contrasts=len(contrasts),scope='all original monthly alerts and source price features, complete date census, exact positive/negative membership, all-or-unknown outcomes and aggregate contrasts',verifier_sha256=sha(Path(__file__))));print('R96 VERIFIED',len(d),len(paired),len(contrasts))
if __name__=='__main__':run()
