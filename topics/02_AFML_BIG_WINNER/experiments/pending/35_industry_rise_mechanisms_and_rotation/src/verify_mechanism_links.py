"""Independent direct-source identity, clock and denominator checks for R20."""
from common import *
import pandas as pd


def run():
 out=ROOT/'outputs/r20';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 for p,h in receipt['outputs'].items():assert sha(out/p)==h
 links=pd.read_csv(out/'company_industry_links.csv');full=pd.read_csv(out/'full_catalogue_evidence.csv')
 facts={x['evidence_id']:x for x in json.loads((ROOT/'outputs/r19/reviewed_operating_observations.json').read_text())}
 cols=KEY+['month','date','instrument','security_id','unresolved']
 members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)],ignore_index=True)
 checked=0
 for (asof,clock),group in links.groupby(['asof','clock']):
  day=pd.Timestamp(asof);month=day.to_period('M')-1
  m=members[members.era.eq('SW2021')&members.month.eq(month)]
  for row in group.itertuples(index=False):
   source=facts[row.evidence_id]
   if clock=='publication_proxy':expected=pd.Timestamp(source['published_date'])<day
   else:
    field='recorded_at' if clock=='inherited_archive' else 'ep35_fetched_at'
    expected=pd.Timestamp(source[field]).tz_convert('Asia/Shanghai').date()<=day.date()
   assert row.clock_eligible==expected
   raw=m[m.instrument.eq(row.instrument)&m.level.eq(row.level)]
   assert len(raw)==1 and raw.iloc[0].industry_code==row.industry_code and raw.iloc[0].security_id==row.security_id
   assert raw.iloc[0].date<day
   checked+=1
  table=full[full['asof'].eq(asof)&full.clock.eq(clock)]
  assert len(table)==511 and not table.duplicated(KEY).any()
  for row in table.itertuples(index=False):
   raw=m[m.level.eq(row.level)&m.industry_code.eq(row.industry_code)]
   active=group[group.level.eq(row.level)&group.industry_code.eq(row.industry_code)&group.clock_eligible&group.mapping_status.eq('mapped')]
   assert row.observed_issuers==active.security_id.nunique() and row.facts==active.evidence_id.nunique()
   if raw.empty:assert pd.isna(row.identified_members) and pd.isna(row.all_member_proxy_sample_fraction)
   else:
    assert row.identified_members==raw.security_id.nunique()
    assert row.unresolved_members==raw.unresolved.max()
    assert abs(row.all_member_proxy_sample_fraction-row.observed_issuers/(row.identified_members+row.unresolved_members))<1e-12
 assert len(links)==234 and len(full)==3066
 js(out/'verification.json',dict(status='PASS',direct_membership_checks=checked,full_catalogue_checks=len(full),code_sha256=sha(__file__),limitation='identity and timing evidence only; does not establish issuer fact represents whole industry'))
 print('R20 verified',checked,'identity links;',len(full),'full-catalogue rows')

if __name__=='__main__':run()
