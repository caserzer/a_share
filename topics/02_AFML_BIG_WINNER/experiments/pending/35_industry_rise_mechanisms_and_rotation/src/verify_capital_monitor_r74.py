import pandas as pd
from common import *
from capital_monitor_r74 import build

def run():
 out=ROOT/'outputs/r74';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 raw=json.loads((ROOT/'outputs/r73/industry_evidence.json').read_text());lookup={}
 for x in raw:lookup.setdefault(tuple(x[k] for k in KEY)+(pd.Timestamp(x['snapshot']),),[]).append(x)
 obs=json.loads((out/'monthly_observations.json').read_text());assert len(obs)==len(lookup)
 for x in obs:
  date=pd.Timestamp(x['snapshot']);ends=[pd.Timestamp(y,m,1)+pd.offsets.MonthEnd(0) for y in [date.year-1,date.year] for m in [3,6,9,12]];e=max(z for z in ends if z<=date);assert e==pd.Timestamp(x['expected_period']);g=lookup[tuple(x[k] for k in KEY)+(date,)];q=next((z for z in g if pd.Timestamp(z['period'])==e),None);financial=max(z['financial_excluded'] for z in g)>0 and max(z['financial_excluded'] for z in g)==max(z['members'] for z in g);status='financial_excluded' if financial else 'period_not_in_source' if q is None else 'historical_proxy_available' if q['coverage_gate'] else 'insufficient_coverage';assert x['status']==status
  good=[z for z in g if z['coverage_gate'] and pd.Timestamp(z['period'])<=e];last=max(good,key=lambda z:z['period']) if good else None;assert x['last_covered_period']==(last['period'] if last else None)
  if status=='historical_proxy_available':
   assert x['current_capex_up_fraction']==q['capex_up']/q['joint_known']
   for k in ['both_improve','both_decline']:assert x['current_'+k+'_fraction']==(q[k]/q['capex_up'] if q['capex_up'] else None)
  else:assert all(x[k] is None for k in ['current_capex_up_fraction','current_both_improve_fraction','current_both_decline_fraction'])
 base=pd.read_parquet(ROOT/'outputs/r63/evidence_matrix.parquet');d=pd.read_parquet(out/'evidence_matrix.parquet');pd.testing.assert_frame_equal(d[base.columns],base);assert len(d)==rec['base_rows']
 for x in d.to_dict('records'):
  q=[z for z in obs if all(z[k]==x[k] for k in KEY) and pd.Timestamp(z['snapshot'])<=pd.Timestamp(x['asof'])];z=max(q,key=lambda z:z['snapshot']) if q else None
  assert x['operating_status']==('no_snapshot' if z is None else z['status'] if pd.Timestamp(z['snapshot'])==pd.Timestamp(x['asof']) else 'older_snapshot_not_current')
  assert all(pd.isna(x['operating_current_'+k]) for k in ['capex_up_fraction','both_improve_fraction','both_decline_fraction'])
 # New economic period unknown must not inherit previous good evidence.
 fake=[dict(era='SW2021',level='L2',industry_code='test',snapshot='2026-07-31',period=p,members=10,denominator=10,financial_excluded=0,identity_unknown=0,coverage_gate=ready,joint_known=10 if ready else 0,capex_up=5 if ready else 0,both_improve=3 if ready else 0,both_decline=2 if ready else 0) for p,ready in [('2026-03-31',True),('2026-06-30',False)]]
 z=build(fake)[0];assert z['status']=='insufficient_coverage' and z['current_capex_up_fraction'] is None and z['last_covered_period']=='2026-03-31'
 js(out/'verification.json',dict(status='PASS',observations=len(obs),unchanged_base_rows=len(base),quarter_calendar_checked=True,unknown_latest_no_fallback=True,no_prediction_promotion=True));print('R74 VERIFIED',len(obs),len(base))
if __name__=='__main__':run()
