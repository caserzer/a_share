import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r53';rec=json.loads((out/'impact_receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 assert sha(out/'source_version_comparison.parquet')==rec['comparison_sha256']
 a={tuple(x[k] for k in KEY+['horizon','date','method']):x for x in json.loads((ROOT/'outputs/r41/predictions.json').read_text())};b={tuple(x[k] for k in KEY+['horizon','date','method']):x for x in json.loads((out/'predictions.json').read_text())}
 assert set(a)<=set(b) and len(b)-len(a)==8
 for key in set(b)-set(a):assert b[key]['date']=='2025-11-28T00:00:00'
 for row in json.loads((out/'source_impact.json').read_text()):
  common=[k for k in a if a[k]['level']==row['level'] and a[k]['horizon']==row['horizon'] and a[k]['method']==row['method'] and b[k]['target'] is not None]
  for version,lookup in [('old',a),('new',b)]:
   error=sum((lookup[k]['prediction']-lookup[k]['target'])**2 for k in common)/len(common);assert abs(error-row['common_mse_'+version])<1e-14
 # Source change cannot alter earlier predictions; 60-day new November label is not mature at Jan1.
 for k,x in a.items():
  if x['date']<'2025-10-31':assert abs(x['prediction']-b[k]['prediction'])<1e-12
  if x['horizon']==60 and x['method']=='FS':assert abs(x['prediction']-b[k]['prediction'])<1e-12
 js(out/'impact_verification.json',dict(status='PASS',common_prediction_rows=len(a),new_prediction_rows=8,common_cohort_metrics_checked=8,earlier_predictions_unchanged=True,sixty_day_price_model_unchanged=True))
 print('R53 SOURCE IMPACT VERIFIED')
if __name__=='__main__':run()
