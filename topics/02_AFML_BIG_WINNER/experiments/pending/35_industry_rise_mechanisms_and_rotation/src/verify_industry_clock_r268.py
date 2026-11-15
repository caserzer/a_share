from common import *
import pandas as pd
from statistics import median
K=KEY+['previous_date','current_date'];out=ROOT/'outputs/r268';r=pd.read_parquet(out/'industry_pairs.parquet');links=pd.read_parquet(out/'company_links.parquet');oldlinks=pd.read_parquet(ROOT/'outputs/r261/common_company_links.parquet');end=pd.read_parquet(ROOT/'outputs/r267/endpoints.parquet').set_index(['date','instrument','security_id']);assert links[K+['instrument','security_id']].equals(oldlinks[K+['instrument','security_id']]);valid=np.ones(len(links),bool);checks=0
for side in ['previous','current']:
 idx=pd.MultiIndex.from_arrays([links[side+'_date'],links.instrument,links.security_id]);a=end.reindex(idx);valid&=a.common_valid.eq(True).to_numpy()
 for col in ['financing','raw_close','total_shares','snapshot_raw_close','snapshot_shares']:
  assert np.allclose(links[col+'_'+side],a[col].to_numpy(),equal_nan=True);checks+=len(a)
assert np.array_equal(valid,links.dual_complete);groups={k:g for k,g in links[valid].groupby(K)};qualified=0
for row in r.to_dict('records'):
 k=tuple(row[x] for x in K);g=groups.get(k);n=0 if g is None else len(g);ok=row['native_rows_present'] and n>=5 and n>=.8*row['members_previous'] and n>=.8*row['members_current'];assert row['dual_common']==n and row['qualified']==ok
 if not ok:
  assert pd.isna(row['signal_change']) and pd.isna(row['snapshot_change']);continue
 qualified+=1
 for clock,price,shares in [('signal','raw_close','total_shares'),('snapshot','snapshot_raw_close','snapshot_shares')]:
  values={}
  for bi in [0,1]:
   for mi in [0,1]:
    bside=['previous','current'][bi];mside=['previous','current'][mi];values[bi,mi]=median((g['financing_'+bside]/(g[price+'_'+mside]*g[shares+'_'+mside])).tolist());assert np.isclose(values[bi,mi],row[clock+f'_f{bi}{mi}'],atol=1e-12)
  bal=((values[1,0]-values[0,0])+(values[1,1]-values[0,1]))/2;cap=((values[0,1]-values[0,0])+(values[1,1]-values[1,0]))/2;assert np.isclose(bal,row[clock+'_balance'],atol=1e-12) and np.isclose(cap,row[clock+'_cap'],atol=1e-12)
 if n==row['complete_common']:
  for a,b in [('signal_balance','original_balance'),('signal_cap','original_cap'),('signal_change','original_change')]:assert np.isclose(row[a],row[b],atol=1e-12)
summary=pd.read_csv(out/'summary.csv')
for row in summary.itertuples():
 g=r[r.era.eq(row.era)&r.level.eq(row.level)];q=g[g.qualified];assert len(q)==row.qualified;assert sum(np.sign(q.signal_change)!=np.sign(q.snapshot_change))==row.change_sign_disagree;assert sum(np.sign(q.signal_balance)!=np.sign(q.snapshot_balance))==row.balance_sign_disagree
js(out/'independent_verification.json',dict(status='PASS',endpoint_value_checks=checks,original_links_preserved=len(links),qualified_industry_checks=qualified,scope='Input common links and both-clock endpoints, all gates, independent statistics.median, symmetric contributions, original same-company reproduction and direction counts',adoption=False));print('VERIFIED',checks,qualified)
