"""Independent rank-correlation and frozen top-selection metric check."""
from common import *
import pandas as pd
from scipy.stats import rankdata
from rank_target_r192 import K

def run():
 out=ROOT/'outputs/r192';v=json.loads((out/'verification.json').read_text())
 for p,h in v['inputs'].items():assert sha(ROOT/p)==h
 for p,h in v['outputs'].items():assert sha(out/p)==h
 p=pd.read_parquet(out/'predictions.parquet');metrics=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']).set_index(K+['date']);count=0
 for key,g in p.groupby(K+['date']):
  row=metrics.loc[key];known=g[g.y.notna()];k=max(1,int(np.ceil(len(g)*.2)))
  for method in ['raw','rank','momentum']:
   field=method+'_score';valid=len(known)>=20 and known[field].nunique()>1 and known.y.nunique()>1
   if valid:
    a=rankdata(known[field]);b=rankdata(known.y);a-=a.mean();b-=b.mean();ic=(a@b)/np.sqrt((a@a)*(b@b));assert abs(ic-row[method+'_ic'])<1e-12
   else:assert pd.isna(row[method+'_ic'])
   top=sorted(g.to_dict('records'),key=lambda x:(-x[field],x['industry_code']))[:k]
   unknown=sum(pd.isna(x['y']) for x in top);assert unknown==row[method+'_top_unknown']
   if unknown:assert pd.isna(row[method+'_top'])
   else:assert abs(sum(x['y'] for x in top)/k-row[method+'_top'])<1e-12
  count+=1
 js(out/'metric_verification.json',dict(status='PASS',dates_checked=count,scope='All raw/rank/momentum IC via independent rankdata-dot-product and top selections via Python sorting; hashes',code_sha256=sha(__file__),receipt_sha256=sha(out/'verification.json')))
 print('PASS',count)
if __name__=='__main__':run()
