from common import *
import pandas as pd
from decimal import Decimal

def run():
 out=ROOT/'outputs/r247';q=pd.read_parquet(out/'quarter_fields.parquet');raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');fields={'c_pay_acq_const_fiolta':'cashflow_vip','n_cashflow_act':'cashflow_vip','n_income_attr_p':'income_vip'};periods=['2025-03-31','2025-06-30','2026-03-31','2026-06-30'];source=raw[raw.api.isin(fields.values())].to_dict('records');checks=0;archives=[]
 def eq(a,b):return pd.isna(a) and pd.isna(b) or a==b
 def sg(v):return 'positive' if v>0 else 'negative' if v<0 else 'zero'
 for date,g in q.groupby('asof'):
  latest={}
  for x in source:
   if not x['timing_valid'] or pd.isna(x['proxy_available_date']) or x['proxy_available_date']>date:continue
   k=(x['api'],x['ts_code'],x['end_date']);old=latest.get(k)
   if old is None or x['proxy_available_date']>old[0]['proxy_available_date']:latest[k]=[x]
   elif x['proxy_available_date']==old[0]['proxy_available_date']:old.append(x)
  for r in g.to_dict('records'):
   vals={};clocks=[];field=r['field'];api=fields[field]
   for period in periods:
    suffix=period.replace('-','');rs=latest.get((api,r['ts_code'],pd.Timestamp(period)));status='absent';value=None;clock=pd.NaT
    if rs:
     vv={None if pd.isna(x[field]) else Decimal(str(x[field])) for x in rs};clock=rs[0]['proxy_available_date'];value=next(iter(vv)) if len(vv)==1 else None;status='conflict' if len(vv)>1 else 'missing' if value is None else 'available';types=all(x['report_type']=='1' and x['comp_type']=='1' for x in rs)
     if status=='available' and api=='income_vip' and not types:status='incompatible_statement_type'
     if status=='available' and field=='c_pay_acq_const_fiolta' and value<0:status='invalid_sign'
     if status=='available' and not types:status='incompatible_statement_type'
    assert r['status_'+suffix]==status and eq(r['clock_'+suffix],clock)
    if status=='available':assert Decimal(r['value_'+suffix])==value;vals[period]=value;clocks.append(clock)
    else:assert pd.isna(r['value_'+suffix])
    checks+=3
   for label,month in [('q1','03-31'),('h1','06-30')]:
    a='2025-'+month;b='2026-'+month;value=vals[b]-vals[a] if a in vals and b in vals else None
    assert r[label+'_sign']==(sg(value) if value is not None else 'unknown')
    assert pd.isna(r[label+'_delta']) if value is None else Decimal(r[label+'_delta'])==value
   status='unavailable_inputs'
   if len(vals)==4:
    old=vals['2025-06-30']-vals['2025-03-31'];new=vals['2026-06-30']-vals['2026-03-31'];status='nonmonotone_capex_cumulative' if field=='c_pay_acq_const_fiolta' and min(old,new)<0 else 'derived_historical_proxy'
   assert r['q2_status']==status
   if status=='derived_historical_proxy':
    assert Decimal(r['q2_2025'])==old and Decimal(r['q2_2026'])==new and Decimal(r['q2_delta'])==new-old
    assert r['q2_sign']==sg(new-old) and r['q2_available_at']==max(clocks)<=date
    assert Decimal(r['h1_delta'])-Decimal(r['q1_delta'])==Decimal(r['q2_delta'])
   else:assert r['q2_sign']=='unknown' and all(pd.isna(r[k]) for k in ['q2_2025','q2_2026','q2_delta','q2_available_at'])
   assert r['restatement_consistency']=='unverified';checks+=10
  cutoff=date.tz_localize('Asia/Shanghai')+pd.Timedelta(days=1);archives.append(dict(asof=date,raw_rows_archived_before_cutoff=int((raw.archived_available_at<cutoff).sum()),raw_rows=len(raw)))
 summary=pd.read_csv(out/'summary.csv',parse_dates=['asof']);coverage=pd.read_csv(out/'coverage.csv',parse_dates=['asof']);transitions=pd.read_csv(out/'transitions.csv',parse_dates=['asof'])
 for r in summary.to_dict('records'):
  g=q[q['asof'].eq(r['asof'])&q.field.eq(r['field'])];h=g[g.h1_sign.eq('positive')];assert r['catalogue']==len(g) and r['qualified']==sum(g.q2_status=='derived_historical_proxy') and r['h1_positive']==len(h)
  for st in ['positive','zero','negative','unknown']:assert r['h1_positive_q2_'+st]==sum(h.q2_sign==st)
 expected=q.groupby(['asof','field','q2_status']).size().reset_index(name='issuer_fields');pd.testing.assert_frame_equal(expected,coverage)
 expected=q.groupby(['asof','field','q1_sign','h1_sign','q2_sign']).size().reset_index(name='issuer_fields');pd.testing.assert_frame_equal(expected,transitions)
 joint=pd.read_parquet(out/'joint_company_diagnostic.parquet');lookup=q.set_index(['asof','ts_code','field']);assert len(joint)==len(q[['asof','ts_code']].drop_duplicates())
 for r in joint.to_dict('records'):
  for quarter in ['q1','q2']:
   signs=[lookup.loc[(r['asof'],r['ts_code'],field),quarter+'_sign'] for field in fields];known=all(x!='unknown' for x in signs);assert bool(r['joint_'+quarter+'_known'])==known
   if known:assert bool(r[quarter+'_all_increase'])==all(x=='positive' for x in signs)
   else:assert pd.isna(r[quarter+'_all_increase'])
 receipt=json.loads((out/'verification.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(Path(f))==h
 for f,h in receipt['outputs'].items():assert sha(out/f)==h
 js(out/'archive_clock.json',archives);js(out/'independent_verification.json',dict(status='PASS',issuer_field_snapshots=len(q),raw_field_and_arithmetic_checks=checks,joint_company_snapshots=len(joint),summary_rows=len(summary),code_sha256=sha(Path(__file__)),strict_pit=False,adoption=False));print('PASS',len(q),checks,len(joint))
if __name__=='__main__':run()
