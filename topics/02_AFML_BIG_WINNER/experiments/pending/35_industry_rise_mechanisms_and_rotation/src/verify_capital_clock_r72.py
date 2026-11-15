import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r72';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');selected=pd.read_parquet(out/'selected_fields.parquet');pairs=pd.read_parquet(out/'company_pairs.parquet');fields={'cashflow_vip':['c_pay_acq_const_fiolta','n_cashflow_act'],'income_vip':['n_income_attr_p']};source=raw[raw.api.isin(fields)].to_dict('records');checked=0
 for date in sorted(selected['asof'].unique()):
  latest={}
  for x in source:
   if not x['timing_valid'] or pd.isna(x['proxy_available_date']) or x['proxy_available_date']>date:continue
   key=(x['api'],x['ts_code'],x['end_date']);old=latest.get(key)
   if old is None or x['proxy_available_date']>old[0]['proxy_available_date']:latest[key]=[x]
   elif x['proxy_available_date']==old[0]['proxy_available_date']:old.append(x)
  lookup=selected[selected['asof'].eq(date)].set_index(['ts_code','end_date','field']);expected=0
  for (api,issuer,period),rs in latest.items():
   for field in fields[api]:
    vals={None if pd.isna(x[field]) else float(x[field]) for x in rs};v=next(iter(vals)) if len(vals)==1 else None;status='conflict' if len(vals)>1 else 'missing' if v is None else 'available'
    if status=='available' and api=='income_vip' and not all(x['report_type']=='1' and x['comp_type']=='1' for x in rs):status='incompatible_statement_type'
    if status=='available' and field=='c_pay_acq_const_fiolta' and v<0:status='invalid_sign'
    y=lookup.loc[(issuer,period,field)];assert y.status==status and y.available_at==rs[0]['proxy_available_date'];assert y.value==v if status=='available' else pd.isna(y.value);expected+=1
  assert expected==len(lookup);checked+=expected
  for x in pairs[pairs['asof'].eq(date)].to_dict('records'):
   known=True
   for field in sum(fields.values(),[]):
    for suffix,period in [('current',x['end_date']),('prior',x['end_date']-pd.DateOffset(years=1))]:
     key=(x['ts_code'],period,field);y=lookup.loc[key] if key in lookup.index else None;valid=y is not None and y.status=='available';known &= valid;v=x[field+'_'+suffix];assert v==y.value if valid else pd.isna(v)
   assert known==x['joint_known']
 for x in json.loads((out/'archive_clock.json').read_text()):assert x['archived_rows_before_snapshot']==int((raw.archived_available_at<pd.Timestamp(x['asof']).tz_localize('Asia/Shanghai')+pd.Timedelta(days=1)).sum())
 end=pairs[pairs['asof'].eq(pairs['asof'].max())&pairs.joint_known].set_index(['ts_code','end_date']);cols=[f'{f}_{t}' for f in sum(fields.values(),[]) for t in ['current','prior']]
 for x in json.loads((out/'coverage.json').read_text()):
  now=pairs[pairs['asof'].eq(pd.Timestamp(x['asof']))].set_index(['ts_code','end_date']);targets=end[end.index.get_level_values('end_date')==pd.Timestamp(x['period'])];known=changed=0
  for key,y in targets.iterrows():
   if key in now.index and now.loc[key,'joint_known']:
    known+=1;changed+=int(any(y[c]!=now.loc[key,c] for c in cols))
  assert len(targets)==x['september_joint_known'] and known==x['known_then'] and len(targets)-known==x['not_joint_known_then'] and changed==x['known_but_value_changed']
 js(out/'verification.json',dict(status='PASS',selected_fields_checked=checked,pair_rows_checked=len(pairs),independent_latest_version_and_clock_replay=True,strict_pit=False));print('R72 VERIFIED',checked,len(pairs))
if __name__=='__main__':run()
