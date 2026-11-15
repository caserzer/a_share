"""Verify audit provenance, adopted routes, and every known monthly source amount."""
from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r154';receipt=json.loads((out/'receipt.json').read_text());audit=json.loads((out/'audit.json').read_text());contract=json.loads((out/'basis_contract.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 for p,h in receipt['outputs'].items():assert sha(out/p)==h
 release=json.loads((out/'release_snapshot.json').read_text())
 for name in ['accounting_historical_monitor','accounting_monthly_evidence','accounting_contemporaneous_controls']:
  x=release['routes'][name];assert x['path'].startswith('outputs/r147/evaluation/') and sha(ROOT/x['path'])==x['sha256'];assert sha(ROOT/x['verification']['path'])==x['verification']['sha256']
 base=ROOT/'outputs/r147/evaluation/outputs';monthly=pd.read_parquet(base/'r73/member_evidence.parquet');q=monthly[monthly.known.eq(True)].copy();pairs=pd.read_parquet(ROOT/'outputs/r72/company_pairs.parquet');fields=[f'{f}_{period}' for f in ['c_pay_acq_const_fiolta','n_cashflow_act','n_income_attr_p'] for period in ['current','prior']];keys=['asof','ts_code','end_date'];joined=q.merge(pairs[keys+fields],on=keys,how='left',validate='many_to_one',suffixes=('','_source'))
 assert len(joined)==len(q)
 for f in fields:assert joined[f].eq(joined[f+'_source']).all(),f
 a=pd.read_parquet(base/'r70/member_evidence.parquet');prior=pd.read_parquet(base/'r69/member_evidence.parquet');pd.testing.assert_frame_equal(a[prior.columns],prior)
 raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');g=raw[raw.api.eq('income_vip')&raw.timing_valid&raw.proxy_available_date.le(pd.Timestamp('2026-09-30'))];g=g[g.proxy_available_date.eq(g.groupby(['ts_code','end_date']).proxy_available_date.transform('max'))];lookup=g.groupby(['ts_code','end_date']).n_income_attr_p.agg(['first',lambda x:x.nunique(dropna=False)]);lookup.columns=['value','distinct'];q70=a[a.joint_profit_known.eq(True)]
 for x in q70.itertuples():
  sym=x.instrument[2:]+'.'+x.instrument[:2];date=pd.Timestamp(x.audit_period)
  for field,period in [('profit_current',date),('profit_prior',date-pd.DateOffset(years=1))]:
   v=lookup.loc[(sym,period)];assert v['distinct']==1 and getattr(x,field)==v['value']
 assert contract['profit']['field']=='n_income_attr_p' and contract['cashflow']['field']=='n_cashflow_act'
 assert not contract['ratio_of_cashflow_to_profit'] and not contract['historical_model_admitted'] and contract['numerical_definition_unchanged']
 assert audit['member_audits'][0]['known_rows']==len(q70) and audit['member_audits'][1]['known_rows']==len(q)
 js(out/'verification.json',dict(status='PASS',adopted_routes=3,monthly_source_amounts=len(joined)*6,current_prior_profit_source_amounts=len(q70)*2,prior_cashflow_member_rows=len(prior),no_late_pdf_substitution=True,no_model_or_data_changes=True))
 print('PASS',len(joined)*6,'monthly source amounts;',len(q70)*2,'profit source amounts')
if __name__=='__main__':run()
