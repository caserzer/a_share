"""Post-result exploratory uncertainty for frozen rank-target comparisons."""
from common import *
import pandas as pd
K=['era','level','cohort','method','horizon']

def scalar_quantile(x,q):
 a=sorted(x);pos=q*(len(a)-1);lo=int(np.floor(pos));hi=int(np.ceil(pos));return a[lo]+(pos-lo)*(a[hi]-a[lo])

def run():
 out=ROOT/'outputs/r193';out.mkdir(exist_ok=True)
 source=ROOT/'outputs/r192/date_metrics.csv';d=pd.read_csv(source,parse_dates=['date']);old=pd.read_csv(ROOT/'outputs/r192/summary.csv');old=old[old.year.eq('all')].set_index(K+['baseline'])
 rows=[];annual=[];grids=[];replicates={};maxerr=0.
 for key,g in d.groupby(K):
  ident=dict(zip(K,key));g=g.sort_values('date');g['month']=g.date.dt.to_period('M');assert not g.month.duplicated().any()
  calendar=pd.period_range(g.month.min(),g.month.max(),freq='M');z=g.set_index('month').reindex(calendar);n=len(calendar)
  rng=np.random.default_rng(35193);starts=rng.integers(0,n,size=(20000,(n+5)//6));indices=((starts[:,:,None]+np.arange(6))%n).reshape(20000,-1)[:,:n]
  weights=np.zeros((20000,n),dtype=np.int16)
  for j in range(n):weights[:,j]=(indices==j).sum(axis=1)
  for baseline in ['raw','momentum']:
   prior=old.loc[key+(baseline,)]
   for metric in ['ic','top']:
    x=(z['rank_'+metric]-z[baseline+'_'+metric]).to_numpy();finite=np.isfinite(x);count=int(finite.sum());value=float(np.nanmean(x)) if count else np.nan
    expected=prior['delta_ic' if metric=='ic' else 'delta_top'];assert np.isclose(value,expected,atol=1e-12,equal_nan=True)
    rec=dict(ident,baseline=baseline,metric=metric,calendar_months=n,known=count,unknown=n-count,mean=value,zero_denominator_draws=None,status='insufficient_paired_months',positive_adjusted=False)
    for mo,val in zip(calendar,x):grids.append(dict(ident,baseline=baseline,metric=metric,month=str(mo),difference=val))
    for year in sorted(set(calendar.year)):
     yy=x[calendar.year==year];annual.append(dict(ident,baseline=baseline,metric=metric,year=int(year),known=int(np.isfinite(yy).sum()),mean=float(np.nanmean(yy)) if np.isfinite(yy).any() else np.nan))
    if count>=24:
     sampled=x[indices];den=np.isfinite(sampled).sum(axis=1);zero=int((den==0).sum());rec['zero_denominator_draws']=zero
     if zero:rec['status']='zero_denominator_resample'
     else:
      means=np.nansum(sampled,axis=1)/den
      alternate=(weights@np.nan_to_num(x,nan=0.))/(weights@finite.astype(float));error=float(np.max(np.abs(alternate-means)));assert error<1e-12;maxerr=max(maxerr,error)
      qs=[.025,.975,.05/112/2,1-.05/112/2];vals=np.quantile(means,qs)
      for q,v in zip(qs,vals):assert abs(scalar_quantile(means,q)-v)<1e-12
      rec.update(status='exploratory_interval',low95=vals[0],high95=vals[1],low_family=vals[2],high_family=vals[3],positive_adjusted=bool(vals[2]>0))
      replicates['|'.join(map(str,key+(baseline,metric)))]=means
    rows.append(rec)
 result=pd.DataFrame(rows);assert result.groupby('horizon').size().eq(112).all()
 result.to_csv(out/'summary.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual.csv',index=False);pd.DataFrame(grids).to_csv(out/'calendar_grid.csv',index=False);np.savez_compressed(out/'replicates.npz',**replicates)
 reads=[source,ROOT/'outputs/r192/summary.csv',ROOT/'outputs/r192/metric_verification.json',ROOT/'protocols/r193.json',Path(__file__),ROOT/'src/common.py'];files=['summary.csv','annual.csv','calendar_grid.csv','replicates.npz']
 js(out/'verification.json',dict(status='PASS',scope='All prior means reconciled, actual calendar grids retained; all resamples independently count-weight checked; all quantiles scalar sorted check',comparisons=len(rows),intervals=len(replicates),resample_means_checked=len(replicates)*20000,max_recompute_error=maxerr,adoption=False,inputs={str(x):sha(x) for x in reads},outputs={x:sha(out/x) for x in files}))
 print(result.groupby(['horizon','baseline','metric']).agg(comparisons=('mean','size'),positive_means=('mean',lambda x:int(x.gt(0).sum())),eligible=('status',lambda x:int(x.eq('exploratory_interval').sum())),positive_adjusted=('positive_adjusted','sum')).to_string())
if __name__=='__main__':run()
