from collections import Counter
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r88';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 values=pd.read_parquet(ROOT/'data/r24_source_exclusion_overlay.parquet');values=values[values.basis.eq('profit_cny')&values.fiscal_year.between(2020,2025)&values.broker.notna()];lookup={(x.infoCode,x.fiscal_year):x.value for x in values.itertuples()};reports=pd.read_parquet(ROOT/'outputs/r85/report_roster.parquet');roster={}
 for x in reports.itertuples():
  if pd.notna(x.broker):roster.setdefault((x.stock_code,x.broker),{}).setdefault(x.publication_proxy_date,[]).append(x.infoCode)
 ledger=pd.read_parquet(out/'event_ledger.parquet');keycols=['stock_code','broker','fiscal_year','publication_date'];assert not ledger.duplicated(keycols).any();index=ledger.set_index(keycols);seen=set()
 for code,broker,year in values[['stock_code','broker','fiscal_year']].drop_duplicates().itertuples(index=False,name=None):
  prior_date=None;prior_value=None
  for date,ids in sorted(roster.get((code,broker),{}).items()):
   vv=[lookup.get((i,year),np.nan) for i in ids];value=float(vv[0]) if all(np.isfinite(v) for v in vv) and len(set(vv))==1 else None;revision=None
   if date.year!=year:status='not_current_fiscal_year'
   elif prior_date is None:status='no_prior_cached_report'
   elif (date-prior_date).days>365:status='prior_older_than365'
   elif value is None or prior_value is None:status='conflicting_current_or_prior'
   elif abs(value)+abs(prior_value)==0:status='zero_denominator'
   else:status='valid';revision=(value-prior_value)/(abs(value)+abs(prior_value))
   key=(code,broker,year,date);seen.add(key);x=index.loc[key];assert x.status==status and list(x.report_ids)==sorted(ids)
   for field,expected in [('current_profit',value),('previous_profit',prior_value),('revision',revision)]:assert pd.isna(x[field]) if expected is None else np.isclose(x[field],expected)
   assert pd.isna(x.previous_date) if prior_date is None else x.previous_date==prior_date
   prior_date=date;prior_value=value
 assert seen==set(index.index)
 events=pd.read_parquet(out/'events.parquet');pd.testing.assert_frame_equal(events[ledger.columns].reset_index(drop=True),ledger[ledger.status.eq('valid')].reset_index(drop=True))
 actual={(x['stock_code'],x['fiscal_year']):x for x in json.loads((ROOT/'outputs/r84/annual_actual_candidates.json').read_text())}
 for x in events.itertuples():
  a=actual.get((x.stock_code,x.fiscal_year))
  if a is None:assert pd.isna(x.actual_profit_cny)
  else:assert x.status_actual==a['status'] and x.actual_profit_cny==a['actual_profit_cny'] and x.update_after_notice==a['update_after_notice']
 old=pd.read_parquet(ROOT/'data/r26_mapped_report_events.parquet')[keycols].drop_duplicates();oldkeys=set(old.itertuples(index=False,name=None));newkeys=set(events[keycols].itertuples(index=False,name=None));oldgroups={x[:3] for x in oldkeys};newgroups={x[:3] for x in newkeys};paired=[x for x in json.loads((ROOT/'outputs/r86/broker_pairs.json').read_text()) if x['paired']];overlap=json.loads((out/'paired_overlap.json').read_text());assert len(overlap)==len(paired)
 for x,y in zip(paired,overlap):
  key=x['stock_code'],x['broker'],x['fiscal_year'];assert key==(y['stock_code'],y['broker'],y['fiscal_year']);assert y['has_r26_next_year_event']==(key in oldgroups) and y['has_r88_current_year_event']==(key in newgroups)
 s=json.loads((out/'summary.json').read_text());assert s==dict(ledger_rows=len(ledger),status_counts=dict(Counter(ledger.status)),valid_current_year_events=len(events),zero_revision_events=int(events.revision.eq(0).sum()),nonzero_revision_events=int(events.revision.ne(0).sum()),actual_candidate_events=int(events.status_actual.eq('candidate').sum()),actual_missing_events=int(events.actual_profit_cny.isna().sum()),old_unique_next_year_events=len(old),exact_event_overlap=len(oldkeys&newkeys),shared_company_broker_publication_dates=len({(x[0],x[1],x[3]) for x in oldkeys}&{(x[0],x[1],x[3]) for x in newkeys}),paired_broker_years=len(paired),paired_with_old_next_year_event=sum(x['has_r26_next_year_event'] for x in overlap),paired_with_current_year_event=sum(x['has_r88_current_year_event'] for x in overlap))
 for x in json.loads((out/'by_year.json').read_text()):
  q=events[events.fiscal_year.eq(x['fiscal_year'])];assert x['events']==len(q) and x['companies']==q.stock_code.nunique() and x['nonzero']==int(q.revision.ne(0).sum())
 js(out/'verification.json',dict(status='PASS',ledger_rows=len(ledger),events=len(events),scope='all original report barriers and current-year decisions reconstructed; all overlap keys and actual joins',receipt_sha256=sha(out/'receipt.json'),verifier_sha256=sha(Path(__file__))))
 print('R88 VERIFIED',len(ledger),len(events))
if __name__=='__main__':run()
