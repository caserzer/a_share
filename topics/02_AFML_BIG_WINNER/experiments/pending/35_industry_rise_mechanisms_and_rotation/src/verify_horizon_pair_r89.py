import statistics
from collections import Counter
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r89';rec=json.loads((out/'receipt.json').read_text())
 for path,h in rec['reads'].items():assert sha(path)==h,path
 current=pd.read_parquet(ROOT/'outputs/r88/events.parquet');old=pd.read_parquet(ROOT/'data/r26_mapped_report_events.parquet');keys=['stock_code','broker','publication_date'];n={k:g for k,g in old.groupby(keys)};expected={tuple(x[k] for k in keys):x for x in current.to_dict('records') if tuple(x[k] for k in keys) in n};paired=pd.read_parquet(out/'paired_events.parquet');assert len(paired)==len(expected)
 for x in paired.to_dict('records'):
  key=tuple(x[k] for k in keys);a=expected[key];g=n[key];assert g.fiscal_year.nunique()==1 and g.revision.nunique()==1 and g.previous_date.nunique()==1;oldrow=g.iloc[0]
  assert x['fiscal_year_current']==a['fiscal_year'] and x['fiscal_year_next']==oldrow.fiscal_year==a['fiscal_year']+1
  assert x['revision_current']==a['revision'] and x['revision_next']==oldrow.revision and x['same_previous_date']==(a['previous_date']==oldrow.previous_date)
  assert x['current_sign']==np.sign(a['revision']) and x['next_sign']==np.sign(oldrow.revision)
 actual=json.loads((out/'annual_actuals.json').read_text());lookup={};cache={};prior=json.loads((ROOT/'outputs/r84/receipt.json').read_text());paths={Path(p).stem.split('.')[0]:Path(p) for p in prior['reads'] if '/proxy/financials/' in p}
 for a in actual:
  key=a['stock_code'],a['fiscal_year'];assert key not in lookup;lookup[key]=a
  if a['fiscal_year']>=2026:assert a['status']=='not_ended' and a['profit_cny'] is None and not a['refs'];continue
  p=paths.get(a['stock_code'])
  if p is None:assert a['status']=='no_partition';continue
  if p not in cache:cache[p]=pd.read_parquet(p)
  q=[(i,x) for i,x in cache[p].iterrows() if pd.Timestamp(x.REPORT_DATE)==pd.Timestamp(a['fiscal_year'],12,31)];assert {(x['source_path'],x['source_row']) for x in a['refs']}=={(str(p),int(i)) for i,x in q}
  status='annual_absent';value=None
  if q:
   vv=[pd.to_numeric(x.PARENTNETPROFIT,errors='coerce') for i,x in q];good=all(x.REPORT_TYPE=='年报' and x.CURRENCY=='CNY' for i,x in q) and all(np.isfinite(v) for v in vv) and len(set(vv))==1;status='candidate' if good else 'unknown_basis_value_or_conflict';value=float(vv[0]) if good else None
  assert a['status']==status and a['profit_cny']==value
 for x in paired.itertuples():
  for suffix in ['current','next']:assert getattr(x,'actual_status_'+suffix)==lookup[x.stock_code,getattr(x,'fiscal_year_'+suffix)]['status']
 company=pd.read_parquet(out/'company_dates.parquet');group={k:g for k,g in paired.groupby(['stock_code','publication_date'])};assert len(company)==len(group)
 for x in company.itertuples():
  g=group[x.stock_code,x.publication_date];a=statistics.median(g.revision_current);b=statistics.median(g.revision_next);assert x.current_revision==a and x.next_revision==b and x.brokers==len(g) and x.opposite==(a*b<0)
 for x in json.loads((out/'by_year.json').read_text()):
  q=company[company.publication_date.dt.year.eq(x['publication_year'])];assert x['company_dates']==len(q) and x['opposite']==sum(q.opposite);assert np.isclose(x['current_mean'],statistics.mean(q.current_revision)) and np.isclose(x['next_mean'],statistics.mean(q.next_revision))
 matrix={(x['current_sign'],x['next_sign']):x['rows'] for x in json.loads((out/'direction_matrix.json').read_text())};assert matrix==dict(Counter(zip(paired.current_sign,paired.next_sign)))
 s=json.loads((out/'summary.json').read_text());assert s==dict(paired_events=len(paired),same_previous_date=int(paired.same_previous_date.sum()),same_direction=int(paired.current_sign.eq(paired.next_sign).sum()),opposite_nonzero=int((paired.current_sign*paired.next_sign<0).sum()),one_zero=int(((paired.current_sign==0)^(paired.next_sign==0)).sum()),both_zero=int((paired.current_sign.eq(0)&paired.next_sign.eq(0)).sum()),current_actual_status=paired.actual_status_current.value_counts().to_dict(),next_actual_status=paired.actual_status_next.value_counts().to_dict(),company_dates=len(company),company_dates_opposite=int(company.opposite.sum()),strict_PIT=False)
 js(out/'verification.json',dict(status='PASS',pairs=len(paired),annual_targets=len(actual),scope='all original event pair keys, annual financial rows and maturity exclusions, medians and summaries',receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R89 VERIFIED',len(paired),len(actual))
if __name__=='__main__':run()
