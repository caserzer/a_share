from common import *
import pandas as pd
from scipy.stats import norm
from financing_components_model_r262 import METHODS

def run():
 out=ROOT/'outputs/r269';a=pd.read_parquet(out/'snapshot/predictions.parquet');b=pd.read_parquet(out/'signal/predictions.parquet');keys=KEY+['date','method','variant','horizon','year'];z=a.merge(b,on=keys,suffixes=('_snapshot','_signal'),validate='one_to_one');assert len(z)==len(a)==len(b);assert np.allclose(z.target_snapshot,z.target_signal,equal_nan=True);assert np.allclose(z[z.method.isin(['FS','FSE'])].prediction_snapshot,z[z.method.isin(['FS','FSE'])].prediction_signal,atol=1e-12)
 pa=pd.read_parquet(out/'snapshot/panel.parquet');pb=pd.read_parquet(out/'signal/panel.parquet');assert pa.drop(columns=['balance_component','cap_component']).equals(pb.drop(columns=['balance_component','cap_component']));industry=pd.read_parquet(ROOT/'outputs/r268/industry_pairs.parquet');industry=industry[industry.qualified].rename(columns={'current_date':'date'}).set_index(KEY+['date'])
 for clock,p in [('signal',pb),('snapshot',pa)]:
  match=industry.loc[p.set_index(KEY+['date']).index]
  for field,col in [('balance_component','balance'),('cap_component','cap')]:assert np.array_equal(p[field].to_numpy(),match[clock+'_'+col].to_numpy())
 metrics=[]
 for k,g in z.groupby(['era','level','horizon','variant','method','date']):
  v=g[g.target_snapshot.notna()];ic=[]
  for clock in ['snapshot','signal']:ic.append(v['prediction_'+clock].corr(v.target_snapshot,method='spearman') if len(v)>=5 and v.target_snapshot.nunique()>1 and v['prediction_'+clock].nunique()>1 else np.nan)
  metrics.append(dict(zip(['era','level','horizon','variant','method','date'],k),ic_delta=ic[0]-ic[1]))
 d=pd.DataFrame(metrics);d.to_parquet(out/'clock_date_deltas.parquet',index=False);rows=[]
 for era,level in [('SW2014','L2'),('SW2014','L3'),('SW2021','L1'),('SW2021','L2'),('SW2021','L3')]:
  for h in [20,60]:
   for variant in ['base','state','interaction']:
    for method in METHODS:
     ident=dict(era=era,level=level,horizon=h,variant=variant,method=method);g=d[d.era.eq(era)&d.level.eq(level)&d.horizon.eq(h)&d.variant.eq(variant)&d.method.eq(method)].dropna(subset=['ic_delta']).sort_values('date');n=len(g)
     if not n:rows.append(dict(ident,status='no_fit',historical_support=False));continue
     u=g.ic_delta.to_numpy()-g.ic_delta.mean();months=g.date.dt.to_period('M').astype('int64').to_numpy();var=sum(u*u);lag=3 if h==20 else 6
     for i in range(n):
      for j in range(i):
       distance=months[i]-months[j]
       if 0<distance<=lag:var+=2*(1-distance/(lag+1))*u[i]*u[j]
     se=np.sqrt(max(0,var))/n;lo=g.ic_delta.mean()-norm.ppf(1-.05/840)*se;hi=g.ic_delta.mean()+norm.ppf(1-.05/840)*se;annual=g.groupby(g.date.dt.year).ic_delta.mean();rows.append(dict(ident,status='evaluated',months=n,years=len(annual),ic_delta=g.ic_delta.mean(),low_family=lo,high_family=hi,positive_years=int(annual.gt(0).sum()),historical_support=bool(n>=24 and len(annual)>=3 and annual.gt(0).all() and lo>0)))
 pd.DataFrame(rows).to_csv(out/'clock_summary.csv',index=False);assert len(rows)==180
 js(out/'comparison_verification.json',dict(status='PASS',paired_predictions=len(z),identical_control_predictions=int(z.method.isin(['FS','FSE']).sum()),identical_cohort=True,original_control_unchanged=True,source_component_checks=len(pa)*4,planned_family=420,adoption=False));print('COMPARED',len(z),sum(x['historical_support'] for x in rows))
if __name__=='__main__':run()
