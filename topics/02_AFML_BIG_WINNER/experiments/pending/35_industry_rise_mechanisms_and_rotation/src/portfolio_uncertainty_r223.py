from common import *
import pandas as pd
from scipy.stats import norm
IDENT=['era','level','cohort','horizon','first_cohort','second_cohort','first_variant','second_variant','kind','whole_pair']
def run():
 out=ROOT/'outputs/r223';out.mkdir(exist_ok=True);observations=[];reads=[]
 for rnd in [210,211,212,214,215,216,217]:
  path=ROOT/f'outputs/r{rnd}/intervals.csv';reads.append(path);d=pd.read_csv(path,parse_dates=['origin']);definitions=[]
  for (era,level,cohort,h),g in d.groupby(['era','level','cohort','horizon']):
   for first in ['state','interaction']:
    for second in ['base','momentum','equal']+(['fixed'] if rnd==216 else []):definitions.append((era,level,h,cohort,cohort,first,second,'regime'))
  mechanism=ROOT/f'outputs/r{rnd}/mechanism_intervals.csv'
  if mechanism.exists():
   mp=ROOT/f'outputs/r{rnd}/mapping.csv';reads +=[mechanism,mp];m=pd.read_csv(mp)
   for row in pd.read_csv(mechanism).to_dict('records'):
    a=m[m.family.eq(row['family'])&m.method.eq(row['mechanism'])].mapped_cohort.iloc[0];b=m[m.family.eq(row['family'])&m.method.eq(row['control'])].mapped_cohort.iloc[0];definitions.append((row['era'],row['level'],row['horizon'],a,b,row['variant'],row['variant'],'mechanism'))
  if rnd==215:
   for family,g in m.groupby('family'):
    a=g[g.method.eq('price_plus_expectation')].mapped_cohort.iloc[0];b=g[g.method.eq('price_only')].mapped_cohort.iloc[0]
    for era,level,h in d[d.cohort.eq(a)][['era','level','horizon']].drop_duplicates().itertuples(index=False,name=None):definitions.append((era,level,h,a,b,'interaction','base','original_price_anchor'))
  lookup={k:g for k,g in d.groupby(['era','level','horizon','cohort','method'])}
  for era,level,h,a,b,av,bv,kind in sorted(set(definitions)):
   aa=lookup[(era,level,h,a,av)];bb=lookup[(era,level,h,b,bv)];q=aa.merge(bb,on='origin',suffixes=('_a','_b'),how='outer',validate='one_to_one');assert len(q)==len(aa)==len(bb);assert q.entry_a.eq(q.entry_b).all() and q.exit_a.eq(q.exit_b).all();valid=q.status_a.eq('valid')&q.status_b.eq('valid');ident=dict(round=rnd,era=era,level=level,cohort=a,horizon=h,first_cohort=a,second_cohort=b,first_variant=av,second_variant=bv,kind=kind,whole_pair=bool(valid.all()),comparison=av+'-vs-'+bv)
   for metric in ['gross','net20','net50']:
    delta=(q[metric+'_a']-q[metric+'_b']).where(valid)
    for date,value in zip(q.origin,delta):observations.append(dict(ident,metric=metric,date=date,delta=value))
 raw=pd.DataFrame(observations);ids=['round']+[c for c in IDENT if c in raw]+['metric','comparison'];raw[ids]=raw[ids].fillna('not_applicable').astype(str);raw['date']=pd.to_datetime(raw.date);raw['month']=raw.date.dt.to_period('M').astype(str);raw.to_parquet(out/'paired_dates.parquet',index=False)
 monthly=raw.groupby(ids+['month'],dropna=False).agg(delta=('delta','mean'),valid_dates=('delta','count'),planned_dates=('delta','size')).reset_index();monthly['case_id']=monthly.groupby(ids,sort=True).ngroup();monthly.to_parquet(out/'monthly_deltas.parquet',index=False);rows=[];annual=[];family_size=monthly.case_id.nunique();critical=float(norm.ppf(1-.05/(2*family_size)));maximum=0.
 for cid,g in monthly.groupby('case_id'):
  ident={k:g.iloc[0][k] for k in ids};v=g[g.delta.notna()].sort_values('month');n=len(v);years=pd.PeriodIndex(v.month,freq='M').year;year_means=v.assign(year=years).groupby('year').delta.mean();mean=v.delta.mean();se=np.nan;months=pd.PeriodIndex(v.month,freq='M').asi8
  if n>=2:
   u=v.delta.to_numpy()-mean;distance=np.abs(months[:,None]-months[None,:]);kernel=np.maximum(0,1-distance/7);variance=float(u@kernel@u);se=np.sqrt(max(0,variance))/n
   independent=float(u@u)
   for lag in range(1,7):independent+=2*(1-lag/7)*sum(u[i]*u[j] for i in range(n) for j in range(i) if months[i]-months[j]==lag)
   err=abs(variance-independent);assert err<1e-9;maximum=max(maximum,err)
  eligible=n>=24 and len(year_means)>=3 and np.isfinite(se) and se>1e-15 and ident['whole_pair']=='True';lo=mean-critical*se if eligible else np.nan;hi=mean+critical*se if eligible else np.nan
  rows.append(dict(ident,case_id=int(cid),months=n,years=len(year_means),mean=mean,se=se,eligible=eligible,low95=mean-1.96*se if eligible else np.nan,high95=mean+1.96*se if eligible else np.nan,adjusted_low=lo,adjusted_high=hi,positive_years=int(year_means.gt(0).sum()),screen_positive=bool(eligible and lo>0 and year_means.gt(0).all()),status='approximate_HAC' if eligible else 'insufficient_or_incomplete_or_degenerate'))
  for year,value in year_means.items():annual.append(dict(case_id=int(cid),year=int(year),delta=value,months=int(sum(years==year))))
 result=pd.DataFrame(rows);result.to_csv(out/'uncertainty.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual.csv',index=False)
 js(out/'verification.json',dict(status='PASS',cases=family_size,eligible=int(result.eligible.sum()),screen_positive=int(result.screen_positive.sum()),adjusted_positive=int(result.adjusted_low.gt(0).sum()),adjusted_negative=int(result.adjusted_high.lt(0).sum()),critical_value=critical,kernel_independent_max_error=maximum,adoption=False,scope='Portfolio interval comparisons with both whole paths required; approximate historical HAC not finite-sample or independent future proof',inputs={str(x):sha(x) for x in reads+[ROOT/'protocols/r223.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['paired_dates.parquet','monthly_deltas.parquet','uncertainty.csv','annual.csv']}))
 print(result.groupby(['round','eligible']).size().to_string());print('cases',family_size,'screen',result.screen_positive.sum(),'adjusted positive',result.adjusted_low.gt(0).sum())
if __name__=='__main__':run()
