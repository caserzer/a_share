import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r87';out.mkdir(exist_ok=True);p=ROOT/'outputs/r86/company_pairs.json';rows=[]
 for x in json.loads(p.read_text()):
  a,b,real=x['june_forecast'],x['december_forecast'],x['actual_profit_cny'];valid=a is not None and b is not None and real is not None
  e0=abs(a-real) if valid else None;e1=abs(b-real) if valid else None;scale=abs(a)+abs(real) if valid else None;delta=e1-e0 if valid else None;old=x['absolute_error_change']
  rows.append(dict(stock_code=x['stock_code'],fiscal_year=x['fiscal_year'],paired_brokers=x['paired_brokers'],june_forecast=a,december_forecast=b,actual_profit_cny=real,scale=scale,june_error_cny=e0,december_error_cny=e1,change_cny=delta,june_fixed_error=e0/scale if scale and scale>0 else None,december_fixed_error=e1/scale if scale and scale>0 else None,fixed_error_change=delta/scale if scale and scale>0 else None,amount_class='unknown' if delta is None else 'improved' if delta<-.01 else 'worsened' if delta>.01 else 'unchanged',symmetric_class='unknown' if old is None else 'improved' if old<-1e-12 else 'worsened' if old>1e-12 else 'unchanged',opposite_sign_both=bool(valid and a*real<0 and b*real<0)))
 js(out/'company_metrics.json',rows);d=pd.DataFrame(rows);summary=[]
 for year,g in d.groupby('fiscal_year'):
  q=g[g.change_cny.notna()];summary.append(dict(fiscal_year=int(year),company_years=len(g),amount_evaluable=len(q),fixed_evaluable=int(q.fixed_error_change.notna().sum()),june_mean_cny=float(q.june_error_cny.mean()),december_mean_cny=float(q.december_error_cny.mean()),mean_change_cny=float(q.change_cny.mean()),june_mean_fixed=float(q.june_fixed_error.mean()),december_mean_fixed=float(q.december_fixed_error.mean()),mean_change_fixed=float(q.fixed_error_change.mean()),amount_classes=q.amount_class.value_counts().to_dict(),classification_changes=int(q.amount_class.ne(q.symmetric_class).sum())))
 js(out/'summary.json',summary);js(out/'classification_matrix.json',d.groupby(['symmetric_class','amount_class']).size().rename('rows').reset_index().to_dict('records'));js(out/'changed_cases.json',[x for x in rows if x['amount_class']!=x['symmetric_class']]);inputs=[p,ROOT/'outputs/r86/verification.json',ROOT/'protocols/r87.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in inputs},frozen_sample=True,strict_PIT=False));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()
