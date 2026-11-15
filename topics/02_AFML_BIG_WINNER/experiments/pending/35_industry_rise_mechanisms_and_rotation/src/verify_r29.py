"""Independent weighted normal-equation audit of EPS experiment."""
import pandas as pd
from common import *
from train_r02 import F

def run():
 out=ROOT/'outputs/r29';receipt=json.loads((out/'data_receipt.json').read_text())
 for path,digest in receipt['reads'].items():assert sha(path)==digest
 panel=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet'),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')],ignore_index=True);panel['log_members']=np.log(panel.members)
 member_cols=['month']+KEY+['security_id','instrument']
 members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=member_cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=member_cols)],ignore_index=True)
 members['stock_code']=members.instrument.str[2:]
 gates=pd.read_csv(ROOT/'outputs/r28/training_gates.csv');results=[];increments=[]
 for variant in ['raw_proxy','share_context_guard']:
  dest=out/variant;cov=pd.read_parquet(ROOT/f'data/r29_{variant}_coverage.parquet');assert sha(ROOT/f'data/r29_{variant}_coverage.parquet')==next(x['sha256'] for x in receipt['outputs'] if x['variant']==variant)
  monthly=pd.read_parquet(ROOT/f'data/r28_{variant}_eps_monthly.parquet')
  for row in cov[cov.known.ge(5)].sample(n=40,random_state=29).itertuples():
   mem=members[members.month.eq(row.date.to_period('M')-1)&members.era.eq(row.era)&members.level.eq(row.level)&members.industry_code.eq(row.industry_code)]
   source=monthly[monthly.date.eq(row.date)&monthly.fiscal_year.eq(row.date.year+row.fy_offset)&monthly.status.eq('valid')]
   values=[source[source.stock_code.eq(code)].revision.median() for code in mem.stock_code]
   assert len(values)==row.members and np.isfinite(values).sum()==row.known and np.isclose(np.nanmedian(values),row.covered_member_median)
  p=pd.read_parquet(dest/'predictions.parquet');params=json.loads((dest/'model_parameters.json').read_text());folds=pd.read_csv(dest/'fold_ledger.csv')
  gate=gates[gates.variant.eq(variant)&gates.branch.eq('eps_only')];check=folds.merge(gate,on=['era','level','fy_offset','population','horizon','year'],suffixes=('','_r28'),validate='one_to_one');assert len(check)==len(folds)==len(gate)
  assert check.status.eq('fit').eq(check.passes).all() and check.train_rows.eq(check.train_rows_r28).all() and check.test_rows.eq(check.test_rows_r28).all()
  base=cov.merge(panel,on=KEY+['date'],suffixes=('_coverage',''),validate='many_to_one');base=base[base.price_ready].dropna(subset=F+['covered_member_median']);error=0;rows=0
  for m in params:
   g=base[base.era.eq(m['era'])&base.level.eq(m['level'])&base.fy_offset.eq(m['fy_offset'])];g=g[g.eligible] if m['population']=='strict' else g[g.known.ge(5)&~g.eligible];g=g[g.groupby('date').date.transform('size')>=2].copy();g['expectation']=g.covered_member_median
   ranks=g.groupby('date')[F+['expectation']].transform(lambda x:(x.rank(method='average')-.5)/len(x)-.5)
   boundary=pd.Timestamp(m['year'],1,1);h=m['horizon'];tr=g[g.date.lt(boundary)&g[f'maturity{h}'].lt(boundary)&g[f'excess{h}'].notna()];assert len(tr)>=300 and tr.date.nunique()>=18
   x=ranks.loc[tr.index,m['columns']].to_numpy();mean=x.mean(axis=0);scale=x.std(axis=0);scale[scale==0]=1;x=(x-mean)/scale
   w=(len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size'))).to_numpy();y=tr[f'excess{h}'].to_numpy();xm=np.average(x,axis=0,weights=w);ym=np.average(y,weights=w);xc=x-xm
   coef=np.linalg.solve((xc*w[:,None]).T@xc+10*np.eye(x.shape[1]),(xc*w[:,None]).T@(y-ym));intercept=ym-xm@coef
   q=p[p.fy_offset.eq(m['fy_offset'])&p.horizon.eq(h)&p.year.eq(m['year'])&p.method.eq(m['method'])&p.population.eq(m['population'])&p.era.eq(m['era'])&p.level.eq(m['level'])]
   assert set(q.row_id)==set(g.index[g.date.dt.year.eq(m['year'])]);assert np.allclose(q.target,g.loc[q.row_id,f'excess{h}'],equal_nan=True)
   pred=((ranks.loc[q.row_id,m['columns']].to_numpy()-mean)/scale)@coef+intercept;error=max(error,float(np.abs(pred-q.prediction).max()));rows+=len(q)
  assert error<1e-10 and rows==len(p)
  for _,z in p.groupby(['era','level','fy_offset','population','horizon','year']):
   a=[q.sort_values('row_id') for _,q in z.groupby('method')];assert len(a)==3
   for b in a[1:]:assert a[0].row_id.tolist()==b.row_id.tolist() and np.allclose(a[0].target,b.target,equal_nan=True)
  metrics=pd.read_csv(dest/'metrics_by_date.csv');metric_keys=['era','level','fy_offset','population','horizon','method','date']
  metrics['date']=pd.to_datetime(metrics.date)
  for key,z in p.groupby(metric_keys):
   actual=metrics
   for col,value in zip(metric_keys,key):actual=actual[actual[col].eq(value)]
   assert len(actual)==1
   q=z.dropna(subset=['target']);expected=((q.prediction-q.target)**2).mean()
   assert np.isclose(actual.iloc[0].mse,expected,equal_nan=True)
   ic=q.prediction.corr(q.target,method='spearman') if len(q)>=5 and q.prediction.nunique()>1 and q.target.nunique()>1 else np.nan
   assert np.isclose(actual.iloc[0].rank_ic,ic,equal_nan=True)
  idx=['era','level','fy_offset','population','horizon','date'];wide=metrics.pivot(index=idx,columns='method',values=['mse','rank_ic'])
  for key,z in wide.groupby(level=idx[:-1]):
   dm=z['mse']['price_plus_expectation']-z['mse']['price_only'];di=z['rank_ic']['price_plus_expectation']-z['rank_ic']['price_only']
   increments.append(dict(zip(idx[:-1],key),variant=variant,months=int(dm.count()),ic_months=int(di.count()),delta_mse=dm.mean(),relative_mse_change=dm.mean()/z['mse']['price_only'].mean(),delta_ic=di.mean()))
  results.append(dict(variant=variant,rows=rows,fits=int(folds.status.eq('fit').sum()),skips=int(folds.status.eq('skip').sum()),normal_equation_prediction_error=error))
 pd.DataFrame(increments).to_csv(out/'paired_increments.csv',index=False);js(out/'verification.json',dict(status='PASS',results=results,checks=['source hashes','R28 fold identities and counts','same three-method cohorts and targets','strict label maturity','independent weighted Ridge solution','80 direct EPS industry aggregations','all per-date metrics recomputed'],code_sha256=sha(__file__)))
 print(results);print(pd.DataFrame(increments).to_string(index=False))
if __name__=='__main__':run()
