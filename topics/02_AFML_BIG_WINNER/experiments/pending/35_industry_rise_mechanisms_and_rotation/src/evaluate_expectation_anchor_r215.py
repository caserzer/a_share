from common import *
import pandas as pd
out=ROOT/'outputs/r215';s=pd.read_csv(out/'summary.csv');m=pd.read_csv(out/'mapping.csv');rows=[]
for family,g in m.groupby('family'):
 a=g[g.method.eq('price_plus_expectation')].mapped_cohort.iloc[0];b=g[g.method.eq('price_only')].mapped_cohort.iloc[0]
 x=s[s.cohort.eq(a)&s.method.eq('interaction')];y=s[s.cohort.eq(b)&s.method.eq('base')];q=x.merge(y,on=['era','level','horizon','cost'],suffixes=('_new','_original'),validate='one_to_one');assert len(q)==len(x)==len(y)
 for z in q.to_dict('records'):
  assert z['scheduled_new']==z['scheduled_original'];valid=bool(z['whole_path_valid_new'] and z['whole_path_valid_original']);r={k:z[k] for k in ['era','level','horizon','cost']};r.update(family=family,scheduled=z['scheduled_new'],both_whole=valid)
  for col in ['total_return','cagr','drawdown','mean_turnover']:r['delta_'+col]=z[col+'_new']-z[col+'_original'] if valid else np.nan
  rows.append(r)
d=pd.DataFrame(rows);d.to_csv(out/'original_price_anchor.csv',index=False);js(out/'anchor_verification.json',dict(status='PASS',rows=len(d),inputs={x:sha(out/x) for x in ['summary.csv','mapping.csv']},output_sha256=sha(out/'original_price_anchor.csv'),script_sha256=sha(__file__)));print(d.query("horizon==20 and cost=='net50'")[['family','scheduled','delta_cagr','delta_total_return']].to_string(index=False))
