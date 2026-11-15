import pandas as pd
from common import *
from style_models_r55 import base_panel,METHODS

def run():
 out=ROOT/'outputs/r55';receipt=json.loads((out/'receipt.json').read_text())
 for path,d in receipt['reads'].items():assert sha(path)==d
 assert sha(out/'predictions.parquet')==receipt['prediction_sha256']
 p=pd.read_parquet(out/'predictions.parquet');base=base_panel();params=json.loads((out/'model_parameters.json').read_text());error=0;rows=0
 for m in params:
  g=base[base.era.eq(m['era'])&base.level.eq(m['level'])];ranks=g.groupby('date')[m['columns']].transform(lambda x:(x.rank(method='average')-.5)/len(x)-.5)
  h=m['horizon'];boundary=pd.Timestamp(m['year'],1,1);tr=g[g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()];assert len(tr)>=300 and tr.date.nunique()>=18
  x=ranks.loc[tr.index].to_numpy();mean=x.mean(axis=0);scale=x.std(axis=0);scale[scale==0]=1;x=(x-mean)/scale;w=(len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size'))).to_numpy();y=tr[f'excess{h}'].to_numpy();xm=np.average(x,axis=0,weights=w);ym=np.average(y,weights=w);xc=x-xm
  coef=np.linalg.solve((xc*w[:,None]).T@xc+10*np.eye(x.shape[1]),(xc*w[:,None]).T@(y-ym));intercept=ym-xm@coef
  q=p[p.era.eq(m['era'])&p.level.eq(m['level'])&p.horizon.eq(h)&p.year.eq(m['year'])&p.method.eq(m['method'])]
  assert set(q.row_id)==set(g.index[g.date.dt.year.eq(m['year'])]);assert np.allclose(q.target,g.loc[q.row_id,f'excess{h}'],equal_nan=True)
  prediction=((ranks.loc[q.row_id].to_numpy()-mean)/scale)@coef+intercept;error=max(error,float(np.abs(prediction-q.prediction).max()));rows+=len(q)
 assert rows==len(p) and error<1e-10
 for _,g in p.groupby(['era','level','horizon','year']):
  frames=[z.sort_values('row_id') for _,z in g.groupby('method')];assert len(frames)==4
  for z in frames[1:]:assert z.row_id.tolist()==frames[0].row_id.tolist() and np.allclose(z.target,frames[0].target,equal_nan=True)
 folds=pd.read_csv(out/'fold_ledger.csv');assert folds.status.eq('fit').eq(folds.train_rows.ge(300)&folds.train_months.ge(18)).all()
 js(out/'verification.json',dict(status='PASS',rows=rows,model_count=len(params),max_normal_equation_error_upper_bound=1e-10,checks=['all source and prediction hashes','four methods same cohort/target','all test origins preserved','maturity-purged training','independent weighted normal equations','fit and skip gates'],code_sha256=sha(__file__)))
 print('R55 VERIFIED',rows,error)
if __name__=='__main__':run()
