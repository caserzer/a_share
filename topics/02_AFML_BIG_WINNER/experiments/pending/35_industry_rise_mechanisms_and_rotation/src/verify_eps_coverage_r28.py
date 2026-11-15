import pandas as pd
from common import *


def run():
 out=ROOT/'outputs/r28';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 assert sha(ROOT/'data/r28_common_coverage.parquet')==receipt['coverage_sha256']
 raw=pd.read_parquet(ROOT/'data/r28_raw_proxy_eps_monthly.parquet');guard=pd.read_parquet(ROOT/'data/r28_share_context_guard_eps_monthly.parquet')
 keys=['stock_code','broker','fiscal_year','date'];pair=raw.merge(guard,on=keys,suffixes=('_raw','_guard'),validate='one_to_one')
 assert len(pair)==len(raw)==len(guard)
 valid=pair.revision_guard.notna();assert np.allclose(pair.loc[valid,'revision_raw'],pair.loc[valid,'revision_guard'])
 assert not (pair.revision_raw.isna()&valid).any()
 profit=pd.read_parquet(ROOT/'data/r25_company_broker_revisions.parquet')
 details=[]
 for variant,eps in [('raw_proxy',raw),('share_context_guard',guard)]:
  common=pd.read_parquet(ROOT/f'data/r28_{variant}_paired_brokers.parquet')
  check=common[keys].merge(profit,on=keys,validate='one_to_one').merge(eps,on=keys,suffixes=('_profit','_eps'),validate='one_to_one')
  assert len(check)==len(common) and check.status_profit.eq('valid').all() and check.status_eps.eq('valid').all()
  assert check.latest_publication_profit.eq(check.latest_publication_eps).all() and check.previous_publication_profit.eq(check.previous_publication_eps).all()
  assert np.allclose(check.revision_profit,common.revision_profit) and np.allclose(check.revision_eps,common.revision_eps)
  unique=common.drop_duplicates(['stock_code','broker','fiscal_year','latest_publication_profit','previous_publication_profit'])
  details.append(dict(variant=variant,monthly_paired_rows=len(common),unique_report_pairs=len(unique),opposite_sign_unique=int((unique.revision_profit*unique.revision_eps<0).sum()),median_absolute_revision_gap=float((unique.revision_profit-unique.revision_eps).abs().median())))
 c=pd.read_parquet(ROOT/'data/r28_common_coverage.parquet');k=KEY+['date','fy_offset'];x=c[c.variant.eq('raw_proxy')].merge(c[c.variant.eq('share_context_guard')],on=k,suffixes=('_raw','_guard'),validate='one_to_one')
 assert x.members_raw.eq(x.members_guard).all() and x.eps_known_guard.le(x.eps_known_raw).all() and x.common_known_guard.le(x.common_known_raw).all()
 assert c.common_known.le(c.eps_known).all() and c.common_known.le(c.members).all()
 assert c.common_strict.eq(c.common_known.ge(5)&c.common_coverage.ge(.8)).all()
 # Independently reconstruct 80 deterministic industry/date medians from paired brokers and member IDs.
 cols=['month']+KEY+['security_id','instrument'];members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)]);members['stock_code']=members.instrument.str[2:]
 checks=0
 for variant in ['raw_proxy','share_context_guard']:
  common=pd.read_parquet(ROOT/f'data/r28_{variant}_paired_brokers.parquet');candidates=c[c.variant.eq(variant)&c.common_known.gt(0)].sort_values(k)
  for row in candidates.iloc[np.unique(np.linspace(0,len(candidates)-1,40,dtype=int))].itertuples():
   m=members[(members.month==row.date.to_period('M')-1)&(members.era==row.era)&(members.level==row.level)&(members.industry_code==row.industry_code)]
   company=common[(common.date==row.date)&(common.fiscal_year==row.date.year+row.fy_offset)].groupby('stock_code')[['revision_profit','revision_eps']].median()
   q=m.join(company,on='stock_code');assert len(q)==row.members and q.revision_profit.notna().sum()==row.common_known
   assert np.allclose([row.profit_common,row.eps_common],[q.revision_profit.median(),q.revision_eps.median()],equal_nan=True);checks+=1
 js(out/'verification.json',dict(status='PASS',lost_eps_broker_months=int((pair.revision_raw.notna()&pair.revision_guard.isna()).sum()),paired_details=details,industry_rows=len(c),direct_industry_checks=checks,code_sha256=sha(__file__),limitation='common samples remain selected-report historical proxies, no outcome test'))
 print(json.dumps(details,ensure_ascii=False));print('R28 verified',len(c),'coverage rows',checks,'direct medians')

if __name__=='__main__':run()
