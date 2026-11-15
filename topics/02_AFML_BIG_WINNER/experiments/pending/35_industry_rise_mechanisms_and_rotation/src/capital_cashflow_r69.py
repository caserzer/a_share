"""Same-statement operating cashflow checks for capital-cycle counterevidence."""
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r69';out.mkdir(exist_ok=True)
 paths=[ROOT/'outputs/r67/selected_facts.json',ROOT/'data/financial_archive_all_market.parquet',ROOT/'outputs/r68/member_links.parquet',ROOT/'outputs/r68/industry_coverage.json',ROOT/'protocols/r69.json',Path(__file__)]
 facts=json.loads(paths[0].read_text());raw=pd.read_parquet(paths[1]);lookup=raw[raw.api.eq('cashflow_vip')].set_index(['query_id','source_row']);assert lookup.index.is_unique;cash=[]
 for x in facts:
  if x['api']!='cashflow_vip':continue
  vals=[lookup.loc[(ref['query_id'],ref['source_row']),'n_cashflow_act'] for ref in x['source_refs']];distinct={None if pd.isna(v) else float(v) for v in vals};v=next(iter(distinct)) if len(distinct)==1 else None
  cash.append(dict(ts_code=x['ts_code'],end_date=x['end_date'],ocf=v,status='conflict' if len(distinct)>1 else 'missing' if v is None else 'available',source_refs=x['source_refs']))
 js(out/'cashflow_facts.json',cash);by={(x['ts_code'],pd.Timestamp(x['end_date'])):x for x in cash}
 links=pd.read_parquet(paths[2]);links=links[links.audit_field.eq('c_pay_acq_const_fiolta')].copy();records=[]
 for x in links.to_dict('records'):
  instrument=x['instrument'];issuer=instrument[2:]+'.'+instrument[:2];period=pd.Timestamp(x['audit_period']);a=by.get((issuer,period));b=by.get((issuer,period-pd.DateOffset(years=1)));known=x['eligible']==True and a is not None and b is not None and a['status']==b['status']=='available'
  rec={k:x[k] for k in KEY+['security_id','instrument','audit_period']};rec.update(known=bool(known),capex_current=x['current_value'],capex_prior=x['prior_value'],ocf_current=a['ocf'] if a else None,ocf_prior=b['ocf'] if b else None,ocf_current_status=a['status'] if a else 'no_statement',ocf_prior_status=b['status'] if b else 'no_statement')
  if known:
   increase=x['current_value']>x['prior_value'];delta=a['ocf']-b['ocf'];rec.update(capex_up=increase,ocf_up=delta>0,ocf_down=delta<0,ocf_flat=delta==0,ocf_negative=a['ocf']<0,cash_spending_gap=a['ocf']<x['current_value'])
  records.append(rec)
 d=pd.DataFrame(records);d.to_parquet(out/'member_evidence.parquet',index=False);rows=[]
 for cov in json.loads(paths[3].read_text()):
  if cov['field']!='c_pay_acq_const_fiolta':continue
  g=d[d.audit_period.eq(cov['period'])]
  for k in KEY:g=g[g[k].eq(cov[k])]
  q=g[g.known];up=q[q.capex_up.eq(True)];n=len(q);den=cov['denominator'];ready=n>=5 and bool(den) and n/den>=.8
  rows.append(dict(**{k:cov[k] for k in KEY+['period']},denominator=den,joint_known=n,coverage=n/den if den else None,coverage_gate=ready,capex_up=len(up),capex_up_ocf_up=int(up.ocf_up.eq(True).sum()),capex_up_ocf_down=int(up.ocf_down.eq(True).sum()),capex_up_ocf_flat=int(up.ocf_flat.eq(True).sum()),negative_ocf=int(q.ocf_negative.eq(True).sum()),cash_spending_gap=int(q.cash_spending_gap.eq(True).sum())))
 js(out/'industry_evidence.json',rows)
 summary=[]
 for (level,period),g in d.groupby(['level','audit_period']):
  assert not g.security_id.duplicated().any();q=g[g.known];up=q[q.capex_up.eq(True)]
  summary.append(dict(level=level,period=period,mapped_members=len(g),joint_known=len(q),capex_up=len(up),up_ocf_up=int(up.ocf_up.eq(True).sum()),up_ocf_down=int(up.ocf_down.eq(True).sum()),up_ocf_flat=int(up.ocf_flat.eq(True).sum()),negative_ocf=int(q.ocf_negative.eq(True).sum()),cash_spending_gap=int(q.cash_spending_gap.eq(True).sum()),industries_passing=sum(x['coverage_gate'] for x in rows if x['level']==level and x['period']==period)))
 js(out/'summary.json',summary);js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},cashflow_facts=len(cash),member_rows=len(d),industry_rows=len(rows),no_market_outcomes=True));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()
