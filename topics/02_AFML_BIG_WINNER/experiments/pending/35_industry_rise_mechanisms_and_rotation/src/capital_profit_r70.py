"""Profit cross-check of fixed cash-spending evidence, with explicit financial exclusion."""
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r70';out.mkdir(exist_ok=True)
 paths=[ROOT/'data/financial_archive_all_market.parquet',ROOT/'outputs/r69/member_evidence.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'outputs/r69/industry_evidence.json',ROOT/'protocols/r70.json',Path(__file__)]
 raw=pd.read_parquet(paths[0]);g=raw[raw.api.eq('income_vip')&raw.timing_valid&raw.proxy_available_date.le(pd.Timestamp('2026-09-30'))];facts=[]
 for (issuer,period),q in g.groupby(['ts_code','end_date']):
  q=q[q.proxy_available_date.eq(q.proxy_available_date.max())];vals=q.n_income_attr_p;distinct=vals.nunique(dropna=False);v=float(vals.iloc[0]) if distinct==1 and pd.notna(vals.iloc[0]) else None;compatible=q.report_type.eq('1').all() and q.comp_type.eq('1').all()
  facts.append(dict(ts_code=issuer,end_date=period,value=v,status='conflict' if distinct>1 else 'missing' if v is None else 'incompatible_statement_type' if not compatible else 'available',available_at=q.proxy_available_date.max(),source_refs=q[['query_id','source_row','source_page_sha256']].to_dict('records')))
 js(out/'profit_facts.json',facts);by={(x['ts_code'],x['end_date']):x for x in facts}
 m=pd.read_parquet(paths[2]);m=m[m.month.eq(pd.Period('2026-08'))];assert not m.security_id.duplicated().any();mapping=m.set_index('security_id').industry_code.to_dict()
 base=pd.read_parquet(paths[1]);records=[]
 for x in base.to_dict('records'):
  issuer=x['instrument'][2:]+'.'+x['instrument'][:2];period=pd.Timestamp(x['audit_period']);a=by.get((issuer,period));b=by.get((issuer,period-pd.DateOffset(years=1)));parent=mapping.get(x['security_id']);scope='identity_unknown' if parent is None else 'financial_excluded' if parent in ['801780.SI','801790.SI'] else 'nonfinancial_accounting'
  known=scope=='nonfinancial_accounting' and x['known'] and a is not None and b is not None and a['status']==b['status']=='available'
  x.update(parent_l1=parent,mechanism_scope=scope,joint_profit_known=bool(known),profit_current=a['value'] if a else None,profit_prior=b['value'] if b else None,profit_current_status=a['status'] if a else 'missing_period',profit_prior_status=b['status'] if b else 'missing_period')
  if known:x.update(profit_up=a['value']>b['value'],profit_down=a['value']<b['value'],profit_flat=a['value']==b['value'],profit_negative=a['value']<0)
  records.append(x)
 d=pd.DataFrame(records);d.to_parquet(out/'member_evidence.parquet',index=False);rows=[]
 for cov in json.loads(paths[3].read_text()):
  q=d[d.audit_period.eq(cov['period'])]
  for k in KEY:q=q[q[k].eq(cov[k])]
  valid=q[q.joint_profit_known];up=valid[valid.capex_up.eq(True)];n=len(valid);den=cov['denominator'];scopes=sorted(q.mechanism_scope.unique())
  rows.append(dict(**{k:cov[k] for k in KEY+['period']},scope=scopes,denominator=den,joint_known=n,coverage_gate=bool(n>=5 and den and n/den>=.8),capex_up=len(up),both_improve=int((up.ocf_up.eq(True)&up.profit_up.eq(True)).sum()),both_decline=int((up.ocf_down.eq(True)&up.profit_down.eq(True)).sum()),cash_down_profit_up=int((up.ocf_down.eq(True)&up.profit_up.eq(True)).sum()),cash_up_profit_down=int((up.ocf_up.eq(True)&up.profit_down.eq(True)).sum()),either_flat=int((up.ocf_flat.eq(True)|up.profit_flat.eq(True)).sum())))
 js(out/'industry_evidence.json',rows);summary=[]
 for (level,period),q in d.groupby(['level','audit_period']):
  valid=q[q.joint_profit_known];up=valid[valid.capex_up.eq(True)]
  summary.append(dict(level=level,period=period,mapped_members=len(q),financial_excluded=int(q.mechanism_scope.eq('financial_excluded').sum()),identity_unknown=int(q.mechanism_scope.eq('identity_unknown').sum()),joint_known=len(valid),capex_up=len(up),both_improve=int((up.ocf_up.eq(True)&up.profit_up.eq(True)).sum()),both_decline=int((up.ocf_down.eq(True)&up.profit_down.eq(True)).sum()),cash_down_profit_up=int((up.ocf_down.eq(True)&up.profit_up.eq(True)).sum()),cash_up_profit_down=int((up.ocf_up.eq(True)&up.profit_down.eq(True)).sum()),either_flat=int((up.ocf_flat.eq(True)|up.profit_flat.eq(True)).sum()),negative_profit=int(valid.profit_negative.eq(True).sum())))
 js(out/'summary.json',summary);js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},profit_facts=len(facts),member_rows=len(d),industry_rows=len(rows),no_market_outcomes=True));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()
