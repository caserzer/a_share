"""Audit the adopted accounting-direction branch without substituting late facts."""
from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r154';base=ROOT/'outputs/r147/evaluation/outputs';raw=pd.read_parquet(ROOT/'data/financial_archive_all_market.parquet');a=pd.read_parquet(base/'r70/member_evidence.parquet');b=pd.read_parquet(base/'r73/member_evidence.parquet');records=[]
 for round_,d,flag,scope in [('R70',a,'joint_profit_known','mechanism_scope'),('R73',b,'known','scope')]:
  q=d[d[flag].eq(True)];assert q[scope].eq('nonfinancial_accounting').all();mismatches={}
  for short,field in [('capex','c_pay_acq_const_fiolta'),('ocf','n_cashflow_act'),('profit','n_income_attr_p')]:
   left,right=(short+'_current',short+'_prior') if round_=='R70' else (field+'_current',field+'_prior')
   assert q[[left,right]].notna().all().all()
   for direction,expected in [('up',q[left]>q[right]),('down',q[left]<q[right]),('flat',q[left]==q[right])]:
    column=short+'_'+direction
    if column not in q:continue
    count=int((q[column].astype(bool)!=expected).sum());assert count==0;mismatches[column]=count
  records.append(dict(stage=round_,rows=len(d),known_rows=len(q),unknown_rows=len(d)-len(q),direction_mismatches=mismatches,unique_issuers=int(q.instrument.nunique())))
 # Check every adopted industry partition against members, including coverage-gated rows.
 aggregate_checks=0
 for stage,d,flag,date_col in [('r70',a,'joint_profit_known','audit_period'),('r73',b,'known','period')]:
  keys=KEY+(['snapshot'] if stage=='r73' else [])+[date_col];groups={k:g for k,g in d.groupby(keys)}
  for x in json.loads((base/stage/'industry_evidence.json').read_text()):
   key=tuple(x[k] for k in KEY)+((pd.Timestamp(x['snapshot']),) if stage=='r73' else ())+(x['period'],);g=groups.get(key,d.iloc[:0]);q=g[g[flag].eq(True)];up=q[q.capex_up.eq(True)]
   assert len(q)==x['joint_known'] and len(up)==x['capex_up']
   for category,cs,ps in [('both_improve','up','up'),('both_decline','down','down'),('cash_down_profit_up','down','up'),('cash_up_profit_down','up','down')]:
    if category in x:assert int((up['ocf_'+cs].eq(True)&up['profit_'+ps].eq(True)).sum())==x[category]
   assert x['coverage_gate']==bool(len(q)>=5 and x['denominator'] and len(q)/x['denominator']>=.8);aggregate_checks+=1
 dictionary=json.loads((out/'dictionary_snapshot.json').read_text());entry=next(x for x in dictionary if x['factor']=='capital_cashflow_profit_joint_evidence');assert '归母利润' in entry['formula'];assert '非阶段概率' in entry['theory'];assert entry['strict_pit_certified'] is False
 inventory=raw.groupby(['api','report_type','comp_type'],dropna=False).size().rename('rows').reset_index().where(lambda x:pd.notna(x),None).to_dict('records')
 financial=raw[raw.api.isin(['cashflow_vip','income_vip'])];assert financial.report_type.eq('1').all()
 contract=dict(factor='capital_cashflow_profit_joint_evidence',version='R154 basis addendum',numerical_definition_unchanged=True,cashflow=dict(field='n_cashflow_act',basis='consolidated_operating_cashflow',comparison='same-report-period current versus prior year, signed amount comparison'),profit=dict(field='n_income_attr_p',basis='parent_attributable_net_profit',comparison='same-report-period current versus prior year, signed amount comparison'),capital_spending=dict(field='c_pay_acq_const_fiolta',basis='consolidated_cash_paid_for_long_term_assets',comparison='current greater than prior, nonnegative amount required'),aggregation='Counts and proportions of common eligible nonfinancial issuer members; at least 5 and 80 percent coverage',ratio_of_cashflow_to_profit=False,meaning='Co-direction or divergence of two explicitly different accounting measures; not profit-to-cashflow reconciliation',prohibited_interpretations=['consolidated profit conversion ratio','cash attributable to parent shareholders','accounting identity','causal investment payoff','predictive probability'],negative_profit='valid signed comparison, not percentage growth',small_or_zero_profit='no profit denominator used',strict_pit_certified=False,historical_model_admitted=False,local_pdf_substitution=False)
 js(out/'basis_contract.json',contract);js(out/'source_type_inventory.json',inventory)
 result=dict(status='PASS',member_audits=records,aggregate_rows_checked=aggregate_checks,raw_financial_rows=len(financial),all_raw_financial_report_type_one=True,consolidated_net_profit_column_in_archive='n_income' in raw.columns,existing_dictionary_names_parent_profit=True,decision='No numeric basis defect demonstrated in audited branch; preserve results and clarify interpretation',scope='R147 adopted R70/R73 direction branch, not blanket certification of every financial factor')
 js(out/'audit.json',result)
 paths=[ROOT/'data/financial_archive_all_market.parquet',base/'r70/member_evidence.parquet',base/'r73/member_evidence.parquet',base/'r70/industry_evidence.json',base/'r73/industry_evidence.json',out/'dictionary_snapshot.json',out/'release_snapshot.json',ROOT/'protocols/r154.json']+[ROOT/f'src/{n}.py' for n in ['capital_profit_r70','capital_clock_r72','capital_monthly_r73','reconcile_accounting_r75','audit_accounting_basis_r154']]
 js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},outputs={p.name:sha(p) for p in [out/'basis_contract.json',out/'source_type_inventory.json',out/'audit.json']},data_or_model_modified=False));print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
