from common import *
import pandas as pd
import re,math

def run():
 o=ROOT/'outputs/r276';records=json.loads((o/'export_registry.json').read_text());p=pd.read_parquet(o/'panel.parquet');pred=pd.read_parquet(o/'predictions.parquet');models=json.loads((o/'models.json').read_text());checks=0;err=0.
 for r in records:
  body=(ROOT/f"outputs/r275/bodies/{r['month']}.txt").read_text();assert sha(ROOT/f"outputs/r275/bodies/{r['month']}.txt")==r['body_sha256'];parts=re.split('[。；]',''.join(body.split()))
  for a in r['matches']:
   assert parts[a['sentence_index']]==a['sentence'];assert '累计' not in a['sentence'] and '企业电池' not in a['sentence'];assert a['export_gwh']==r['export_gwh']
   if a['context']:
    n=a['sentence_index'];offset=2 if a['bridge'] else 1;assert parts[n-offset]==a['context']
    if a['bridge']:assert parts[n-1]==a['bridge'] and re.fullmatch(r'合计出口占当月销量[\d.]+%',a['bridge'])
   checks+=1
  if r['export_gwh'] is not None:assert abs(r['export_log_ratio']-(math.log(r['export_gwh'])-math.log(r['installation_gwh'])))<1e-12
 for m in models:
  g=p.copy()
  for k in KEY:g=g[g[k]==m[k]]
  b=pd.Timestamp(m['year'],1,1);h=m['horizon'];tr=g[g.export_eligible & g.date.lt(b)&g[f'maturity{h}'].lt(b)&g[f'excess{h}'].notna()];te=g[g.export_eligible & g.date.dt.year.eq(m['year'])];assert len(tr)==m['train_n'] and tr.date.nunique()>=24
  vals=tr[m['columns']].to_numpy();mu=vals.mean(axis=0);sd=vals.std(axis=0);sd[sd==0]=1;assert np.max(abs(mu-m['mean']))<1e-12;assert np.max(abs(sd-m['scale']))<1e-12
  def design(frame):
   out=[]
   for _,r in frame.iterrows():
    z=(r[m['columns']].to_numpy(float)-mu)/sd;flags=[float(r.regime==s) for s in ['down_high','up_low','up_high']];a=[1.]+list(z)
    if m['variant']!='base':a+=flags
    if m['variant']=='interaction':a+=[f*v for f in flags for v in z]
    out.append(a)
   return np.array(out)
  x=design(tr);xt=design(te);coef=np.linalg.solve(x.T@x+np.diag([0]+[10]*(x.shape[1]-1)),x.T@tr[f'excess{h}'].to_numpy());actual=pred.copy()
  for k in KEY+['horizon','year','method','variant']:actual=actual[actual[k]==m[k]]
  actual=actual.set_index('date').loc[te.date];e=float(max(abs(xt@coef-actual.prediction.to_numpy())));assert e<1e-10;err=max(err,e)
 for r in pd.read_csv(o/'metrics.csv').to_dict('records'):
  g=pred.copy()
  for k in KEY+['horizon']:g=g[g[k]==r[k]]
  if r['period'].startswith('year:'):g=g[g.year==int(r['period'][5:])]
  if r['period'].startswith('state:'):g=g[g.regime==r['period'][6:]]
  a,v=r['first'].split('/');b,w=r['second'].split('/');aa=g[(g.method==a)&(g.variant==v)].set_index('date');bb=g[(g.method==b)&(g.variant==w)].set_index('date');z=aa.join(bb[['prediction']],rsuffix='_control').dropna(subset=['target']);assert len(z)==r['n']
  if len(z):assert abs(((z.prediction_control-z.target)**2-(z.prediction-z.target)**2).mean()-r['mse_improvement'])<1e-12
 receipt=json.loads((o/'receipt.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(ROOT/f)==h
 for f,h in receipt['outputs'].items():assert sha(o/f)==h
 js(o/'independent_verification.json',dict(status='PASS',source_quote_contexts=checks,models_reconstructed=len(models),predictions=len(pred),max_error=err,scope='Corrected source text and explicit amount contexts; independent training scaling, design, normal equations and paired MSE; not publisher-definition, causal, optimizer or future certification'))
 print('PASS',len(models),len(pred),err)
if __name__=='__main__':run()
