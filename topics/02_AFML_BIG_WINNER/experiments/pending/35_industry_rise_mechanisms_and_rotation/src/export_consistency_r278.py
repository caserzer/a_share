from common import *
from decimal import Decimal,localcontext
import re
import pandas as pd

def bounds(token):
 v=Decimal(token);digits=len(token.split('.')[1]) if '.' in token else 0;half=Decimal(5)*Decimal(10)**(-digits-1);return v-half,v+half

def run():
 o=ROOT/'outputs/r278';o.mkdir(exist_ok=True);records=json.loads((ROOT/'outputs/r276/export_registry.json').read_text());lookup={r['month']:r for r in records};rows=[]
 for r in records:
  if r['export_gwh'] is None:continue
  amounts=[];rates=[]
  for a in r['matches']:
   amt=re.search(r'动力电池出口(?:销量|量)?(?:共计|为)?(\d+(?:\.\d+)?)GWh',a['sentence']);assert amt;amounts.append(amt.group(1))
   for match in re.finditer(r'同比(增长|上升|增加|下降|减少)(\d+(?:\.\d+)?)%',a['sentence']):rates.append(('-' if match.group(1) in ['下降','减少'] else '')+match.group(2))
  assert len(set(amounts))==1
  prior=f"{int(r['month'][:4])-1:04d}{r['month'][4:]}";q=lookup.get(prior);row=dict(month=r['month'],prior_month=prior,current_amount_token=amounts[0],current_sha256=r['raw_sha256'],current_available_at=r['available_at'],quotes=r['matches'],rate_tokens=rates,prior_amount_token=None,prior_sha256=None,reported_rate_token=rates[0] if len(set(rates))==1 else None,status='missing_reported_rate' if not rates else 'ambiguous_rate' if len(set(rates))!=1 else 'missing_prior_direct_power_amount')
  if q and q['export_gwh'] is not None:
   a=q['matches'][0];prior_token=re.search(r'动力电池出口(?:销量|量)?(?:共计|为)?(\d+(?:\.\d+)?)GWh',a['sentence']).group(1);row.update(prior_amount_token=prior_token,prior_sha256=q['raw_sha256'],prior_quotes=q['matches'],audit_available_at=max(r['available_at'],q['available_at']))
   if row['reported_rate_token'] is not None:
    with localcontext() as ctx:
     ctx.prec=40;c0,c1=bounds(amounts[0]);p0,p1=bounds(prior_token);r0,r1=bounds(row['reported_rate_token']);r0/=100;r1/=100;assert p0>0 and r0>-1
     low=c0/p1-1;high=c1/p0-1;overlap=max(low,r0)<=min(high,r1);impliedlow=c0/(1+r1);impliedhigh=c1/(1+r0)
     row.update(status='rounding_compatible' if overlap else 'inconsistent_beyond_rounding',derived_yoy_low=str(low),derived_yoy_high=str(high),reported_yoy_low=str(r0),reported_yoy_high=str(r1),point_recomputed_yoy=str(Decimal(amounts[0])/Decimal(prior_token)-1),implied_prior_low=str(impliedlow),implied_prior_high=str(impliedhigh),prior_rounding_low=str(p0),prior_rounding_high=str(p1),cause='unresolved; implied prior is diagnostic only, not replacement data')
  rows.append(row)
 js(o/'comparisons.json',rows);pd.DataFrame([{k:v for k,v in r.items() if k not in ['quotes','prior_quotes']} for r in rows]).to_csv(o/'comparisons.csv',index=False)
 summary=dict(status='PASS',direct_power_months=len(rows),classification_counts=pd.Series([r['status'] for r in rows]).value_counts().to_dict(),inconsistent_months=[r['month'] for r in rows if r['status']=='inconsistent_beyond_rounding'],source_values_changed=0,models_refit=0,strict_pit=False,adoption=False);js(o/'summary.json',summary)
 reads=['protocols/r278.json','src/export_consistency_r278.py','outputs/r276/export_registry.json'];js(o/'receipt.json',dict(inputs={s:sha(ROOT/s) for s in reads},outputs={f.name:sha(f) for f in o.iterdir() if f.is_file() and f.name!='receipt.json'}));print(summary)
if __name__=='__main__':run()
