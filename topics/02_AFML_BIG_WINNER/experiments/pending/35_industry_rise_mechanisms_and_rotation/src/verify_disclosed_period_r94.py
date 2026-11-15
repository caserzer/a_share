import pandas as pd
from pandas.testing import assert_frame_equal
from common import *
def run():
 out=ROOT/'outputs/r94';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 fields=pd.read_parquet(ROOT/'outputs/r72/selected_fields.parquet');members=pd.read_parquet(ROOT/'outputs/r73/member_evidence.parquet');industry=pd.DataFrame(json.loads((ROOT/'outputs/r73/industry_evidence.json').read_text()));industry['snapshot']=pd.to_datetime(industry.snapshot);fg={k:g for k,g in fields.groupby(['asof','ts_code','end_date'])};mg={k:g for k,g in members.groupby(KEY+['snapshot','period'])};audit=pd.read_parquet(out/'period_coverage.parquet');assert len(audit)==len(industry);source=industry.set_index(KEY+['snapshot','period']);groups={}
 for r in audit.to_dict('records'):
  key=tuple(r[k] for k in KEY)+ (r['snapshot'],r['period']);original=source.loc[key]
  for k in ['members','denominator','joint_known','coverage_gate','capex_up','both_improve','both_decline']:assert r[k]==original[k]
  observed=[]
  for m in mg[key].itertuples():
   q=fg.get((r['snapshot'],m.ts_code,pd.Timestamp(r['period'])))
   if q is not None:observed.append(q)
  assert r['observed_members']==len(observed)
  if observed:
   q=pd.concat(observed);assert r['first_proxy']==q.available_at.min() and r['last_proxy']==q.available_at.max()<=r['snapshot'] and r['invalid_fields']==q.status.ne('available').sum()
  else:assert pd.isna(r['first_proxy']) and pd.isna(r['last_proxy']) and r['invalid_fields']==0
  groups.setdefault(key[:-1],[]).append(r)
 rows=json.loads((out/'observations.json').read_text());assert len(rows)==len(groups);obs={}
 def eq(a,b):return (pd.isna(a) and pd.isna(b)) or a==b
 for r in rows:
  key=tuple(r[k] for k in KEY)+(pd.Timestamp(r['snapshot']),);g=[x for x in groups[key] if x['observed_members']>0];x=max(g,key=lambda x:x['period']) if g else None;obs[key]=r
  if x is None:assert r['period'] is None and r['status']=='no_observed_period';continue
  assert r['period']==x['period'];status='financial_excluded' if x['financial_excluded']==x['members'] and x['members']>0 else 'source_limited_disclosed_period_available' if x['coverage_gate'] else 'latest_observed_period_insufficient_coverage';assert r['status']==status
  for k in ['observed_members','invalid_fields','denominator','joint_known']:assert r[k]==x[k]
  assert pd.Timestamp(r['first_proxy'])==x['first_proxy'] and pd.Timestamp(r['last_proxy'])==x['last_proxy']
  for k,num,den in [('capex_up_fraction','capex_up','joint_known'),('both_improve_fraction','both_improve','capex_up'),('both_decline_fraction','both_decline','capex_up')]:assert eq(r[k],x[num]/x[den] if status=='source_limited_disclosed_period_available' and x[den] else None)
 base=pd.read_parquet(ROOT/'outputs/r93/task_evidence.parquet');d=pd.read_parquet(out/'task_evidence.parquet');assert_frame_equal(base,d[base.columns]);v=pd.read_parquet(out/'industry_date_view.parquet');assert len(v)==len(base[KEY+['asof']].drop_duplicates())
 for r in v.to_dict('records'):
  key=tuple(r[k] for k in KEY);eligible=[(k,x) for k,x in obs.items() if k[:3]==key and k[3]<=r['asof']]
  if not eligible:assert r['disclosed_view_status']=='no_source_snapshot';continue
  k,z=max(eligible,key=lambda a:a[0][3]);assert r['disclosed_source_snapshot']==k[3] and r['disclosed_source_age_days']==(r['asof']-k[3]).days;assert r['disclosed_view_status']==(z['status'] if k[3]==r['asof'] else 'older_source_snapshot_not_current');assert r['disclosed_last_period']==z['period'] and r['disclosed_last_status']==z['status']
  assert eq(r['disclosed_period_age_days'],(r['asof']-pd.Timestamp(z['period'])).days if z['period'] else None)
  for f in ['capex_up_fraction','both_improve_fraction','both_decline_fraction']:assert eq(r['disclosed_last_'+f],z[f])
  assert eq(r['disclosed_last_proxy'],pd.Timestamp(z['last_proxy']) if z['last_proxy'] else None)
 expected=base.merge(v,on=KEY+['asof'],how='left',validate='many_to_one');assert_frame_equal(d,expected)
 summary=v.groupby(['asof','level','disclosed_view_status','disclosed_last_period'],dropna=False).size().reset_index(name='industries');actual=pd.DataFrame(json.loads((out/'coverage.json').read_text()));actual['asof']=pd.to_datetime(actual['asof']);assert_frame_equal(summary.astype(object).where(summary.notna(),None),actual.astype(object).where(actual.notna(),None),check_dtype=False)
 js(out/'verification.json',dict(status='PASS',period_rows=len(audit),observations=len(rows),task_rows=len(d),scope='all original member/selected-field clocks, latest-period selection including conflicts, original coverage and ratios, all prior task values and exact source-age annotations',verifier_sha256=sha(Path(__file__))));print('R94 VERIFIED',len(audit),len(rows),len(d))
if __name__=='__main__':run()
