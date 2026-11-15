from common import *
import pandas as pd
from scipy.stats import norm
IDENT=['source_round','family','era','level','cohort','method','task','horizon','objective','cost']
def run():
 out=ROOT/'outputs/r222';out.mkdir(exist_ok=True);observations=[];reads=[]
 for rnd,task in [(220,'reversal'),(221,'onset')]:
  path=ROOT/f'outputs/r{rnd}/date_metrics.csv';reads.append(path);d=pd.read_csv(path,parse_dates=['date']);d['task']=task;ids=IDENT
  for key,g in d.groupby(ids,dropna=False):
   ident=dict(zip(ids,key));ident['round']=rnd
   for metric in ['cash_policy_gain','market_policy_gain']:
    w=g.pivot(index='date',columns='variant',values=metric)
    for variant in ['state','interaction']:
     for date,value in (w[variant]-w['base']).items():observations.append(dict(ident,metric=metric,comparison=variant+'-base',date=date,delta=value))
    for variant in ['base','state','interaction']:
     for date,value in w[variant].items():observations.append(dict(ident,metric=metric,comparison=variant+'-reference',date=date,delta=value))
 path=ROOT/'outputs/r221/capacity_baseline_dates.csv';reads.append(path);d=pd.read_csv(path,parse_dates=['date']);d['task']='onset'
 for key,g in d.groupby(IDENT+['variant'],dropna=False):
  ident=dict(zip(IDENT,key[:-1]));ident['round']=221;variant=key[-1]
  for metric in ['cash_selection_increment','market_selection_increment']:
   for row in g.to_dict('records'):observations.append(dict(ident,metric=metric,comparison=variant+'-capacity_pool',date=row['date'],delta=row[metric]))
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
 js(out/'verification.json',dict(status='PASS',cases=family_size,eligible=int(result.eligible.sum()),screen_positive=int(result.screen_positive.sum()),adjusted_positive=int(result.adjusted_low.gt(0).sum()),adjusted_negative=int(result.adjusted_high.lt(0).sum()),critical_value=critical,kernel_independent_max_error=maximum,adoption=False,scope='Frozen classifier action economics only; exploratory approximate HAC not finite-sample or prospective proof',inputs={str(x):sha(x) for x in reads+[ROOT/'protocols/r222.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['paired_dates.parquet','monthly_deltas.parquet','uncertainty.csv','annual.csv']}))
 print(result.groupby(['round','eligible']).size().to_string());print('cases',family_size,'screen',result.screen_positive.sum(),'adjusted positive',result.adjusted_low.gt(0).sum())
if __name__=='__main__':run()
