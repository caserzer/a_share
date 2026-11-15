from common import *
import pandas as pd
from decimal import Decimal
FIELDS={'c_pay_acq_const_fiolta':'cashflow_vip','n_cashflow_act':'cashflow_vip','n_income_attr_p':'income_vip'}
PERIODS=['2025-03-31','2025-06-30','2026-03-31','2026-06-30']
def sign(v):return 'positive' if v>0 else 'negative' if v<0 else 'zero'
def run():
 out=ROOT/'outputs/r247';out.mkdir(exist_ok=True);selected=pd.read_parquet(ROOT/'outputs/r72/selected_fields.parquet');raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');rows=[]
 for date,s in selected.groupby('asof'):
  source=raw[raw.timing_valid&raw.proxy_available_date.le(date)&raw.api.isin(FIELDS.values())].copy();keys=['api','ts_code','end_date'];source=source[source.proxy_available_date.eq(source.groupby(keys).proxy_available_date.transform('max'))];types=source.assign(type_ok=source.report_type.eq('1')&source.comp_type.eq('1')).groupby(keys).type_ok.all().to_dict();lookup=s.set_index(['ts_code','end_date','field']);issuers=sorted(x for x in s.ts_code.unique() if pd.Series([x]).str.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)').iloc[0])
  for issuer in issuers:
   for field,api in FIELDS.items():
    r=dict(asof=date,ts_code=issuer,field=field);vals={};states={};clocks=[]
    for period in PERIODS:
     key=(issuer,pd.Timestamp(period),field);name=period.replace('-','');x=lookup.loc[key] if key in lookup.index else None;status=x.status if x is not None else 'absent'
     if status=='available' and not types.get((api,issuer,pd.Timestamp(period)),False):status='incompatible_statement_type'
     states[period]=status;r['status_'+name]=status;r['value_'+name]=str(Decimal(str(x.value))) if status=='available' else None;r['clock_'+name]=x.available_at if x is not None else pd.NaT
     if status=='available':vals[period]=Decimal(str(x.value));clocks.append(x.available_at)
    for label,period in [('q1','03-31'),('h1','06-30')]:
     a='2025-'+period;b='2026-'+period;v=vals[b]-vals[a] if a in vals and b in vals else None;r[label+'_delta']=str(v) if v is not None else None;r[label+'_sign']=sign(v) if v is not None else 'unknown'
    r.update(q2_status='unavailable_inputs',q2_2025=None,q2_2026=None,q2_delta=None,q2_sign='unknown',q2_available_at=pd.NaT)
    if len(vals)==4:
     old=vals['2025-06-30']-vals['2025-03-31'];new=vals['2026-06-30']-vals['2026-03-31']
     if field=='c_pay_acq_const_fiolta' and (old<0 or new<0):r['q2_status']='nonmonotone_capex_cumulative'
     else:
      delta=new-old;assert Decimal(r['h1_delta'])==Decimal(r['q1_delta'])+delta;r.update(q2_status='derived_historical_proxy',q2_2025=str(old),q2_2026=str(new),q2_delta=str(delta),q2_sign=sign(delta),q2_available_at=max(clocks))
    rows.append(r)
 q=pd.DataFrame(rows);q['comparison_basis']='same_cutoff_latest_proxy_mixed_reports';q['restatement_consistency']='unverified';q.to_parquet(out/'quarter_fields.parquet',index=False);coverage=q.groupby(['asof','field','q2_status']).size().reset_index(name='issuer_fields');coverage.to_csv(out/'coverage.csv',index=False)
 transitions=q.groupby(['asof','field','q1_sign','h1_sign','q2_sign']).size().reset_index(name='issuer_fields');transitions.to_csv(out/'transitions.csv',index=False);summary=[]
 for key,g in q.groupby(['asof','field']):
  h=g[g.h1_sign.eq('positive')];summary.append(dict(zip(['asof','field'],key),catalogue=len(g),qualified=int(g.q2_status.eq('derived_historical_proxy').sum()),h1_positive=len(h),h1_positive_q2_positive=int(h.q2_sign.eq('positive').sum()),h1_positive_q2_zero=int(h.q2_sign.eq('zero').sum()),h1_positive_q2_negative=int(h.q2_sign.eq('negative').sum()),h1_positive_q2_unknown=int(h.q2_sign.eq('unknown').sum())))
 summary=pd.DataFrame(summary);summary.to_csv(out/'summary.csv',index=False)
 joint=q.pivot(index=['asof','ts_code'],columns='field',values='q2_sign');joint.columns=['q2_'+c for c in joint.columns];first=q.pivot(index=['asof','ts_code'],columns='field',values='q1_sign');first.columns=['q1_'+c for c in first.columns];joint=joint.join(first).reset_index();joint['joint_q2_known']=joint[['q2_'+c for c in FIELDS]].ne('unknown').all(axis=1)
 for quarter in ['q1','q2']:
  known=joint[[quarter+'_'+c for c in FIELDS]].ne('unknown').all(axis=1);joint['joint_'+quarter+'_known']=known;flag=joint[[quarter+'_'+c for c in FIELDS]].eq('positive').all(axis=1).astype('boolean');joint[quarter+'_all_increase']=flag.where(known,pd.NA)
 joint.to_parquet(out/'joint_company_diagnostic.parquet',index=False)
 inputs=[ROOT/'outputs/r72/selected_fields.parquet',ROOT/'data/financial_archive_all_market.parquet',ROOT/'protocols/r247.json',Path(__file__)];js(out/'verification.json',dict(status='PASS',issuer_field_snapshots=len(q),snapshots=q['asof'].nunique(),primary='2026-09-30',strict_pit=False,adoption=False,inputs={str(p):sha(p) for p in inputs},outputs={p.name:sha(p) for p in out.iterdir() if p.suffix in ['.parquet','.csv']}));print(summary[summary['asof'].eq(pd.Timestamp('2026-09-30'))].to_string(index=False));print(coverage[coverage['asof'].eq(pd.Timestamp('2026-09-30'))].to_string(index=False))
if __name__=='__main__':run()
