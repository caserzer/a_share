from common import *
import pandas as pd
out=ROOT/'outputs/r217';source=ROOT/'outputs/r202/scores.parquet';p=pd.read_parquet(source).rename(columns={'method':'original_method'});m=pd.read_parquet(out/'mapped_predictions.parquet');m=m[m.method.ne('momentum')];keys=KEY+['date','lag','variant','original_method'];q=p.merge(m,on=keys,validate='one_to_one',how='outer',indicator=True,suffixes=('_src','_mapped'));assert len(q)==len(p)==len(m) and q._merge.eq('both').all();assert np.array_equal(q.score_src,q.prediction);assert np.array_equal(q.selected_src,q.selected_mapped)
i=pd.read_csv(out/'intervals.csv');mapping=pd.read_csv(out/'mapping.csv');fixed=set(mapping[mapping.method.eq('F')].mapped_cohort);checks=0
for _,g in i[i.cohort.isin(fixed)].groupby(['era','level','cohort','horizon']):
 base=g[g.method.eq('base')]
 for variant in ['state','interaction']:
  a=g[g.method.eq(variant)].merge(base,on='origin',validate='one_to_one',suffixes=('_v','_b'));assert len(a)==len(base);assert a.status_v.eq(a.status_b).all()
  for col in ['gross','net20','net50','turnover']:assert np.allclose(a[col+'_v'],a[col+'_b'],equal_nan=True,atol=1e-12)
  checks+=len(a)
js(out/'independent_control_verification.json',dict(status='PASS',source_scores=len(q),F_control_intervals=checks,scope='All R202 scores and selection flags preserved, F full interval paths/status/fees/turnover invariant across variants',script_sha256=sha(__file__),inputs={str(source):sha(source),'intervals.csv':sha(out/'intervals.csv'),'mapped_predictions.parquet':sha(out/'mapped_predictions.parquet')}));print('PASS',len(q),checks)
