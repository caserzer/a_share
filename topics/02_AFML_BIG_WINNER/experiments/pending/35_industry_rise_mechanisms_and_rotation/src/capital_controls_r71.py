import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r71';out.mkdir(exist_ok=True);source=ROOT/'outputs/r70/member_evidence.parquet';d=pd.read_parquet(source);d=d[d.joint_profit_known].copy();d['both_improve']=d.ocf_up.eq(True)&d.profit_up.eq(True);d['both_decline']=d.ocf_down.eq(True)&d.profit_down.eq(True)
 cov=json.loads((ROOT/'outputs/r70/industry_evidence.json').read_text());rows=[]
 for c in cov:
  g=d[d.audit_period.eq(c['period'])]
  for k in KEY:g=g[g[k].eq(c[k])]
  a=g[g.capex_up.eq(True)];b=g[g.capex_up.eq(False)];reasons=[]
  if not c['coverage_gate']:reasons.append('R70_coverage_gate')
  if len(a)<5:reasons.append('increase_group_lt5')
  if len(b)<5:reasons.append('nonincrease_group_lt5')
  for outcome in ['both_improve','both_decline']:
   rows.append(dict(**{k:c[k] for k in KEY+['period']},outcome=outcome,n_up=len(a),n_other=len(b),events_up=int(a[outcome].sum()),events_other=int(b[outcome].sum()),rate_up=float(a[outcome].mean()) if len(a) else None,rate_other=float(b[outcome].mean()) if len(b) else None,eligible=not reasons,reasons=reasons))
 js(out/'industry_contrasts.json',rows);summaries=[]
 for (level,period),g in d.groupby(['level','audit_period']):
  for outcome in ['both_improve','both_decline']:
   a=g[g.capex_up.eq(True)];b=g[g.capex_up.eq(False)];eligible=[x for x in rows if x['level']==level and x['period']==period and x['outcome']==outcome and x['eligible']];n=sum(x['n_up']+x['n_other'] for x in eligible)
   wa=sum((x['n_up']+x['n_other'])*x['rate_up'] for x in eligible)/n if n else None;wb=sum((x['n_up']+x['n_other'])*x['rate_other'] for x in eligible)/n if n else None
   pa=sum(x['events_up'] for x in eligible)/sum(x['n_up'] for x in eligible) if eligible else None;pb=sum(x['events_other'] for x in eligible)/sum(x['n_other'] for x in eligible) if eligible else None
   summaries.append(dict(level=level,period=period,outcome=outcome,n_up=len(a),n_other=len(b),pooled_up=float(a[outcome].mean()),pooled_other=float(b[outcome].mean()),eligible_industries=len(eligible),eligible_members=n,eligible_pooled_up=pa,eligible_pooled_other=pb,standardized_up=wa,standardized_other=wb,standardized_difference=wa-wb if n else None,equal_industry_difference=float(np.mean([x['rate_up']-x['rate_other'] for x in eligible])) if eligible else None))
 js(out/'summary.json',summaries);paths=[source,ROOT/'outputs/r70/industry_evidence.json',ROOT/'protocols/r71.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},industry_rows=len(rows),summaries=len(summaries),no_causal_or_predictive_claim=True));print(pd.DataFrame(summaries)[['level','period','outcome','pooled_up','pooled_other','eligible_industries','standardized_difference']].to_string(index=False))
if __name__=='__main__':run()
