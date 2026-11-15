from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r204';p=pd.read_parquet(out/'predictions.parquet');keys=['era','level','cohort','method','horizon','year','variant'];groups={k:g for k,g in p[p.variant.ne('fixed')].groupby(keys)};err=0.;count=0
 for m in json.loads((out/'models.json').read_text()):
  q=groups[tuple(m[k] for k in keys)];x=(q.score.to_numpy()-m['mean'][0])/m['scale'][0];u=np.array([[float(s==t) for t in ['down_high','up_low','up_high']] for s in q.regime]);a=x[:,None]
  if m['variant']!='base':a=np.column_stack([a,u])
  if m['variant']=='interaction':a=np.column_stack([a,x[:,None]*u])
  pred=a@np.array(m['coef'])+m['intercept'];e=float(np.max(abs(pred-q.prediction)));assert e<1e-12;err=max(err,e);count+=len(q)
 d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);old=pd.read_csv(ROOT/'outputs/r132/evaluation/outputs/r01/date_metrics.csv',parse_dates=['date']);fixed=d[d.variant.eq('fixed')];pk=['era','level','cohort','method','horizon','date'];paired=fixed.merge(old,on=pk,validate='one_to_one',suffixes=('_new','_old'));assert len(paired)==len(fixed)
 for metric in ['ic','top_excess']:assert np.allclose(paired[metric+'_new'],paired[metric+'_old'],atol=1e-12,equal_nan=True)
 # For a scalar affine score every within-date rank is preserved or reversed.
 raw=fixed[pk+['ic']];other=d[d.variant.ne('fixed')].merge(raw,on=pk,suffixes=('_model','_raw'),validate='many_to_one');q=other.dropna(subset=['ic_model','ic_raw']);assert np.allclose(q.ic_model,np.sign(q.slope)*q.ic_raw,atol=1e-12)
 metric_keys=pk+['variant'];lookup={k:g for k,g in p.groupby(metric_keys)}
 for row in d.to_dict('records'):
  g=lookup[tuple(row[k] for k in metric_keys)];ranked=g.assign(ordered=np.sign(g.slope)*g.score).sort_values(['ordered','industry_code'],ascending=[False,True]);top=ranked.head(int(np.ceil(.2*len(g))));value=top.y.mean() if top.y.notna().all() else np.nan
  assert np.isclose(value,row['top_excess'],atol=1e-12,equal_nan=True)
  if row['variant']!='fixed':
   v=g[g.y.notna()];loss=sum((z.prediction-z.y)**2 for z in v.itertuples())/len(v) if len(v) else np.nan;assert np.isclose(loss,row['mse'],atol=1e-12,equal_nan=True)
 js(out/'independent_verification.json',dict(status='PASS',parameter_prediction_rows=count,max_prediction_error=err,original_fixed_metric_rows=len(paired),affine_rank_checks=len(q),scope='all learned predictions; original fixed IC/top outputs; exact scalar-affine rank implication',code_sha256=sha(__file__)))
 print(count,len(paired),len(q),err)
if __name__=='__main__':run()
