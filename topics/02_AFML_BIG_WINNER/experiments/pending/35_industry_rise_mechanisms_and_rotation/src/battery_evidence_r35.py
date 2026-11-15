"""Audit local theme assertions without treating workflow promotion as source truth."""
import re
import pandas as pd
from urllib.parse import urlsplit,urlunsplit
from common import *

BASE=Path('/home/xiaolv/code/golden_loop_artifacts/themes/电池板块盈利兑现与ETF配置--theme-73ad8b2e-dc69-4bd1-a50e-2bf241db0706')
def canonical(url):
 if not url:return None
 p=urlsplit(url);return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,p.query,''))
def run():
 out=ROOT/'outputs/r35';out.mkdir(exist_ok=True);paths=[BASE/'state.json',BASE/'evidence.jsonl',Path(__file__),ROOT/'protocols/r35.json']
 state=json.loads(paths[0].read_text());ev=[json.loads(x) for x in paths[1].read_text().splitlines() if x.strip()];docs=state['documents'];lookup={d['document_id']:d for d in docs};assert len(lookup)==len(docs)
 rows=[];candidates=[]
 for e in ev:
  d=lookup.get(e.get('document_id'),{});quote=e.get('original_quote') or '';pub=pd.to_datetime(d.get('published_at'),utc=True);retr=pd.to_datetime(d.get('retrieved_at'),utc=True);eff=pd.to_datetime(e.get('effective_at'),utc=True)
  row=dict(evidence_id=e['evidence_id'],document_id=e.get('document_id'),document_found=bool(d),url=canonical(d.get('canonical_url')),source_id=e.get('source_id'),promotion=e.get('promotion_status'),period_start=e.get('period_start'),period_end=e.get('period_end'),published_at=d.get('published_at'),retrieved_at=d.get('retrieved_at'),effective_at=e.get('effective_at'),content_hash=d.get('content_hash'),effective_before_publication=bool(pd.notna(eff) and pd.notna(pub) and eff<pub),quote=quote,source_proximity=e.get('source_proximity'))
  rows.append(row)
  # Narrow monthly installations only; cumulative and company/forecast facts are not pooled.
  m=re.search(r'(?<![\d-])(\d{1,2})月[，,]\s*国内动力电池装车量\s*([\d.]+)\s*GWh',quote)
  if m:
   period=pd.to_datetime(e.get('period_end'),utc=True);month=int(m[1]);value=float(m[2]);consistent=pd.notna(period) and period.month==month
   candidates.append(dict(row,metric='china_power_battery_monthly_installations',unit='GWh',value=value,month=f'{period.year}-{month:02d}' if consistent else None,period_consistent=consistent,ep35_status='unverified_local_quote',numeric_factor_eligible=False))
 a=pd.DataFrame(rows);a.to_csv(out/'evidence_audit.csv',index=False);c=pd.DataFrame(candidates);c.to_csv(out/'monthly_installation_leads.csv',index=False)
 groups=[]
 for month,g in c.groupby('month'):
  groups.append(dict(month=month,assertions=len(g),document_ids=g.document_id.nunique(),canonical_urls=g.url.nunique(),distinct_values=g.value.nunique(),values=sorted(g.value.unique().tolist()),earliest_recorded_publication=g.published_at.dropna().min(),earliest_recorded_retrieval=g.retrieved_at.dropna().min(),source_content_hashes_present=int(g.content_hash.notna().sum()),source_verified=False))
 js(out/'monthly_lead_groups.json',groups)
 d=pd.DataFrame(docs);d['url']=d.canonical_url.map(canonical);repeats=d.groupby('url').agg(records=('document_id','size')).query('records>1').reset_index();repeats.to_csv(out/'repeated_document_urls.csv',index=False)
 obs=state['metric_observations'];js(out/'existing_numeric_observations.json',obs)
 summary=dict(evidence_rows=len(ev),document_rows=len(docs),unique_document_urls=d.url.nunique(),repeated_url_groups=len(repeats),missing_document_refs=int((~a.document_found).sum()),documents_missing_hash=int(d.content_hash.isna().sum()),effective_before_publication=int(a.effective_before_publication.sum()),original_numeric_observations=len(obs),monthly_installation_quote_rows=len(c),monthly_periods=len(groups),eligible_predictive_series=0,conclusion='two-month assertion lead is not a verified continuous historical factor; publication must not be replaced by economic period-end or workflow promotion')
 js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},summary=summary));print(json.dumps(summary,ensure_ascii=False));print(json.dumps(groups,ensure_ascii=False))
if __name__=='__main__':run()
