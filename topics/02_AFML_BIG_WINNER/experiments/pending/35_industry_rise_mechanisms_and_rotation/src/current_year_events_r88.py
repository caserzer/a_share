import pandas as pd
from common import *
from events_r26 import all_report_barriers

def run():
 out=ROOT/'outputs/r88';out.mkdir(exist_ok=True);vp=ROOT/'data/r24_source_exclusion_overlay.parquet';rp=ROOT/'outputs/r85/report_roster.parquet';oldp=ROOT/'data/r26_mapped_report_events.parquet';ap=ROOT/'outputs/r84/annual_actual_candidates.json';bp=ROOT/'outputs/r86/broker_pairs.json'
 v=pd.read_parquet(vp);v=v[v.fiscal_year.between(2020,2025)];reports=pd.read_parquet(rp);expanded=all_report_barriers(v,reports);rows=[]
 for key,g in expanded.groupby(['stock_code','broker','fiscal_year']):
  previous=None
  for date,q in g.groupby('publication_proxy_date',sort=True):
   known=q.value.notna().all() and q.value.nunique()==1;value=float(q.value.iloc[0]) if known else None;status='valid';revision=None
   if key[2]!=date.year:status='not_current_fiscal_year'
   elif previous is None:status='no_prior_cached_report'
   elif (date-previous['date']).days>365:status='prior_older_than365'
   elif value is None or previous['value'] is None:status='conflicting_current_or_prior'
   elif abs(value)+abs(previous['value'])==0:status='zero_denominator'
   else:revision=(value-previous['value'])/(abs(value)+abs(previous['value']))
   rows.append(dict(stock_code=key[0],broker=key[1],fiscal_year=int(key[2]),publication_date=date,previous_date=previous['date'] if previous else None,current_profit=value,previous_profit=previous['value'] if previous else None,revision=revision,status=status,report_ids=sorted(q.infoCode)))
   previous=dict(date=date,value=value)
 ledger=pd.DataFrame(rows);ledger.to_parquet(out/'event_ledger.parquet',index=False);events=ledger[ledger.status.eq('valid')].copy();actual=pd.DataFrame(json.loads(ap.read_text())).drop(columns=['source_rows']);events=events.merge(actual[['stock_code','fiscal_year','status','actual_profit_cny','update_after_notice']],on=['stock_code','fiscal_year'],how='left',suffixes=('','_actual'),validate='many_to_one');events.to_parquet(out/'events.parquet',index=False)
 old=pd.read_parquet(oldp);keys=['stock_code','broker','fiscal_year','publication_date'];old=old[keys].drop_duplicates();assert (old.fiscal_year==old.publication_date.dt.year+1).all();common=events.merge(old,on=keys,how='inner');paired=pd.DataFrame(json.loads(bp.read_text()));paired=paired[paired.paired];k3=['stock_code','broker','fiscal_year'];oldgroups=set(old[k3].itertuples(index=False,name=None));newgroups=set(events[k3].itertuples(index=False,name=None));pairedrows=[]
 for x in paired.to_dict('records'):
  key=(x['stock_code'],x['broker'],x['fiscal_year']);pairedrows.append(dict(stock_code=key[0],broker=key[1],fiscal_year=key[2],has_r26_next_year_event=key in oldgroups,has_r88_current_year_event=key in newgroups))
 js(out/'paired_overlap.json',pairedrows);summary=dict(ledger_rows=len(ledger),status_counts=ledger.status.value_counts().to_dict(),valid_current_year_events=len(events),zero_revision_events=int(events.revision.eq(0).sum()),nonzero_revision_events=int(events.revision.ne(0).sum()),actual_candidate_events=int(events.status_actual.eq('candidate').sum()),actual_missing_events=int(events.actual_profit_cny.isna().sum()),old_unique_next_year_events=len(old),exact_event_overlap=len(common),shared_company_broker_publication_dates=len(set(old[['stock_code','broker','publication_date']].itertuples(index=False,name=None))&set(events[['stock_code','broker','publication_date']].itertuples(index=False,name=None))),paired_broker_years=len(pairedrows),paired_with_old_next_year_event=sum(x['has_r26_next_year_event'] for x in pairedrows),paired_with_current_year_event=sum(x['has_r88_current_year_event'] for x in pairedrows));js(out/'summary.json',summary)
 js(out/'by_year.json',events.groupby('fiscal_year').agg(events=('revision','size'),companies=('stock_code','nunique'),nonzero=('revision',lambda x:int(x.ne(0).sum()))).reset_index().to_dict('records'));inputs=[vp,rp,oldp,ap,bp,ROOT/'src/events_r26.py',ROOT/'protocols/r88.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in inputs},no_new_price_evaluation=True,strict_PIT=False));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()
