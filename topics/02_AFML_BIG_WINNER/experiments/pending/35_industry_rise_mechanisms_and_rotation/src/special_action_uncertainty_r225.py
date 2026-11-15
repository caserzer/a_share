from common import *
import pandas as pd
from scipy.stats import norm
IDENT=['family','era','level','industry_code','horizon','target_type','first_method','second_method','first_variant','second_variant','kind']
def run():
 out=ROOT/'outputs/r225';out.mkdir(exist_ok=True);observations=[];reads=[]
 for rnd in [213,218]:
  path=ROOT/f'outputs/r{rnd}/intervals.csv'
  if rnd==218:path=ROOT/'outputs/r218/decisions.parquet';d=pd.read_parquet(path);d['family']='battery'
  else:d=pd.read_csv(path,parse_dates=['date']);d['horizon']=0
  cp=ROOT/f'outputs/r{rnd}/comparisons.csv';reads += [path,cp];cases=pd.read_csv(cp);ids=['family','era','level']+(['industry_code','horizon'] if rnd==218 else [])
  if rnd==218:cases['family']='battery'
  lookup={k:g for k,g in d.groupby(ids)}
  for row in cases.to_dict('records'):
   g=lookup[tuple(row[c] for c in ids)];am,av=row['first'].rsplit('_',1);bm,bv=row['second'].rsplit('_',1);a=g[g.method.eq(am)&g.variant.eq(av)];b=g[g.method.eq(bm)&g.variant.eq(bv)];q=a.merge(b,on='date',suffixes=('_a','_b'),how='outer',validate='one_to_one');assert len(q)==len(a)==len(b);valid=q.status_a.eq('valid')&q.status_b.eq('valid');ident={c:row[c] for c in ids};ident.update(round=rnd,horizon=row.get('horizon',0),first_method=am,second_method=bm,first_variant=av,second_variant=bv,kind=row['kind'],comparison=av+'-vs-'+bv)
   for metric in ['gross','net20','net50']:
    delta=(q[metric+'_a']-q[metric+'_b']).where(valid)
    for date,value in zip(q.date,delta):observations.append(dict(ident,date=date,metric=metric,delta=value))
 path=ROOT/'outputs/r219/paired_dates.parquet';reads.append(path);d=pd.read_parquet(path)
 for row in d[d.metric.isin(['gross','net20','net50'])].to_dict('records'):
  am,av=row['first'].rsplit('_',1);bm,bv=row['second'].rsplit('_',1);observations.append(dict({k:row[k] for k in ['family','era','level','horizon','target_type','kind','date','metric','delta']},round=219,first_method=am,second_method=bm,first_variant=av,second_variant=bv,comparison=av+'-vs-'+bv))
 raw=pd.DataFrame(observations);ids=['round']+[c for c in IDENT if c in raw]+['metric','comparison'];raw[ids]=raw[ids].fillna('not_applicable').astype(str);raw['date']=pd.to_datetime(raw.date);raw['month']=raw.date.dt.to_period('M').astype(str);raw.to_parquet(out/'paired_dates.parquet',index=False)
 monthly=raw.groupby(ids+['month'],dropna=False).agg(delta=('delta','mean'),valid_dates=('delta','count'),planned_dates=('delta','size')).reset_index();monthly['case_id']=monthly.groupby(ids,sort=True).ngroup();monthly.to_parquet(out/'monthly_deltas.parquet',index=False);rows=[];annual=[];family_size=monthly.case_id.nunique();critical=float(norm.ppf(1-.05/(2*family_size)));maximum=0.
 for cid,g in monthly.groupby('case_id'):
  ident={k:g.iloc[0][k] for k in ids};v=g[g.delta.notna()].sort_values('month');n=len(v);years=pd.PeriodIndex(v.month,freq='M').year;year_means=v.assign(year=years).groupby('year').delta.mean();mean=v.delta.mean();se=np.nan;months=pd.PeriodIndex(v.month,freq='M').asi8
  if n>=2:
   u=v.delta.to_numpy()-mean;distance=np.abs(months[:,None]-months[None,:]);kernel=np.maximum(0,1-distance/7);variance=float(u@kernel@u);se=np.sqrt(max(0,variance))/n
   independent=float(u@u)
   for lag in range(1,7):independent+=2*(1-lag/7)*sum(u[i]*u[j] for i in range(n) for j in range(i) if months[i]-months[j]==lag)
   err=abs(variance-independent);assert err<1e-9;maximum=max(maximum,err)
  eligible=n>=24 and len(year_means)>=3 and np.isfinite(se) and se>1e-15;lo=mean-critical*se if eligible else np.nan;hi=mean+critical*se if eligible else np.nan
  rows.append(dict(ident,case_id=int(cid),months=n,years=len(year_means),mean=mean,se=se,eligible=eligible,low95=mean-1.96*se if eligible else np.nan,high95=mean+1.96*se if eligible else np.nan,adjusted_low=lo,adjusted_high=hi,positive_years=int(year_means.gt(0).sum()),screen_positive=bool(eligible and lo>0 and year_means.gt(0).all()),status='approximate_HAC' if eligible else 'insufficient_or_degenerate'))
  for year,value in year_means.items():annual.append(dict(case_id=int(cid),year=int(year),delta=value,months=int(sum(years==year))))
 result=pd.DataFrame(rows);result.to_csv(out/'uncertainty.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual.csv',index=False)
 js(out/'verification.json',dict(status='PASS',cases=family_size,eligible=int(result.eligible.sum()),screen_positive=int(result.screen_positive.sum()),adjusted_positive=int(result.adjusted_low.gt(0).sum()),adjusted_negative=int(result.adjusted_high.lt(0).sum()),critical_value=critical,kernel_independent_max_error=maximum,adoption=False,scope='Separate event/battery/catchup interval economics; complete-case historical approximate HAC, not pooled returns or independent confirmation',inputs={str(x):sha(x) for x in reads+[ROOT/'protocols/r225.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['paired_dates.parquet','monthly_deltas.parquet','uncertainty.csv','annual.csv']}))
 print(result.groupby(['round','eligible']).size().to_string());print('cases',family_size,'screen',result.screen_positive.sum(),'adjusted positive',result.adjusted_low.gt(0).sum())
if __name__=='__main__':run()
