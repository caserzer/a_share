from common import *
import re,math
from fractions import Fraction
import pandas as pd

def bounds(s):
 n=len(s.split('.')[1]) if '.' in s else 0;v=Fraction(s);h=Fraction(1,2*10**n);return v-h,v+h

def run():
 o=ROOT/'outputs/r280';o.mkdir(exist_ok=True);sources=json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text());rows=[];lookup={r['month']:r for r in sources}
 for r in sources:
  m=int(r['month'][-2:]);body=(ROOT/f"outputs/r275/bodies/{r['month']}.txt").read_text();text=''.join(body.split());matches=[]
  pattern=rf'(?:(?<![\d至到—–-]){m}月份?[，,]?(?:我国|国内)|(?:我国|国内){m}月份?)动力电池装车量(?:共计|为)?(?P<value>\d+(?:\.\d+)?)GWh'
  for a in re.finditer(pattern,text,re.I):
   tail=re.split('[。；]',text[a.end():],1)[0].split('其中')[0];matches.append(dict(quote=a.group(),amount_token=a.group('value'),start=a.start(),end=a.end(),rate_context=tail))
  if r['month']=='2020-02':
   a=re.search(r'2月，我国动力电池装车量再次呈现较大幅度下降，共计装车(?P<value>\d+(?:\.\d+)?)GWh',text);assert a;tail=re.split('[。；]',text[a.end():],1)[0].split('其中')[0];matches.append(dict(quote=a.group(),amount_token=a.group('value'),start=a.start(),end=a.end(),rate_context=tail))
  vals={Fraction(a['amount_token']) for a in matches};status='matches_frozen_value' if len(vals)==1 and float(next(iter(vals)))==r['value_gwh'] else 'conflict' if vals else 'unmatched';rates=[]
  for a in matches:
   for g in re.finditer(r'(?:同比|同环比均)(增长|上升|增加|下降|减少)(\d+(?:\.\d+)?)%',a['rate_context']):rates.append(('-' if g.group(1) in ['下降','减少'] else '')+g.group(2))
  row=dict(month=r['month'],status=status,frozen_gwh=r['value_gwh'],raw_sha256=r['raw_sha256'],body_sha256=sha(ROOT/f"outputs/r275/bodies/{r['month']}.txt"),matches=matches,rate_tokens=rates,annual_status='missing_prior_or_rate',growth_reproduced=None)
  prior=f"{int(r['month'][:4])-1:04d}{r['month'][4:]}";q=lookup.get(prior)
  if q:
   assert r['prior_month']==prior and r['prior_gwh']==q['value_gwh'] and r['prior_sha256']==q['raw_sha256'];assert abs(r['log_yoy']-math.log(r['value_gwh']/q['value_gwh']))<1e-12;assert r['growth_available_at']==max(r['available_at'],q['available_at']);row['growth_reproduced']=True
   if len(set(rates))==1 and len(vals)==1:
    # R60 amounts are floats; prior displayed precision is obtained from extracted prior record, below.
    row.update(prior_month=prior,reported_rate_token=rates[0])
  rows.append(row)
 bymonth={r['month']:r for r in rows}
 for r in rows:
  if 'reported_rate_token' not in r:continue
  q=bymonth[r['prior_month']]
  if not r['matches'] or not q['matches'] or q['status']!='matches_frozen_value':continue
  c=r['matches'][0]['amount_token'];p=q['matches'][0]['amount_token'];c0,c1=bounds(c);p0,p1=bounds(p);r0,r1=[x/100 for x in bounds(r['reported_rate_token'])];lo=c0/p1-1;hi=c1/p0-1;ok=max(lo,r0)<=min(hi,r1)
  r.update(annual_status='rounding_compatible' if ok else 'inconsistent_beyond_rounding',current_amount_token=c,prior_amount_token=p,derived_low=float(lo),derived_high=float(hi),reported_low=float(r0),reported_high=float(r1),audit_available_at=max(lookup[r['month']]['available_at'],lookup[q['month']]['available_at']))
 js(o/'records.json',rows);pd.DataFrame([{k:v for k,v in r.items() if k!='matches'} for r in rows]).to_csv(o/'summary_rows.csv',index=False)
 summary=dict(status='PASS' if all(r['status']=='matches_frozen_value' for r in rows) else 'PARTIAL',months=len(rows),amount_status=pd.Series([r['status'] for r in rows]).value_counts().to_dict(),growth_reproduced=sum(r['growth_reproduced'] is True for r in rows),annual_status=pd.Series([r['annual_status'] for r in rows]).value_counts().to_dict(),inconsistent_months=[r['month'] for r in rows if r['annual_status']=='inconsistent_beyond_rounding'],source_values_changed=0,models_refit=0,strict_pit=False);js(o/'summary.json',summary)
 reads=['protocols/r280.json','src/installation_body_r280.py','outputs/r60/frozen_monthly_series.json']+[str(f.relative_to(ROOT)) for f in (ROOT/'outputs/r275/bodies').glob('*.txt')];js(o/'receipt.json',dict(inputs={s:sha(ROOT/s) for s in reads},outputs={f.name:sha(f) for f in o.iterdir() if f.is_file() and f.name!='receipt.json'}));print(summary)
if __name__=='__main__':run()
