from common import *
import pandas as pd
from scipy.stats import norm
IDS=['era','level','strategy','variant','cost','policy','comparison']

def run():
    out=ROOT/'outputs/r293';out.mkdir(exist_ok=True);d=pd.read_parquet(ROOT/'outputs/r292/date_metrics.parquet');parts=[]
    planned=pd.read_parquet(ROOT/'outputs/r290/date_metrics.parquet');planned=planned[planned.variant.eq('base')&planned.cost.eq(0)]
    coverage={k:dict(planned_dates=len(g),incomplete_dates=int((~g.complete_date).sum())) for k,g in planned.groupby(['era','level','strategy'])}
    for name,first,second,mc in [('worst_vs_hold','hold_worst','model_worst',None),('mean_vs_hold','hold_mean','model_mean',None),('worst_vs_random','random_worst','model_worst','random_worst_mc_variance'),('mean_vs_random','random_mean','model_mean','random_mean_mc_variance'),('terminal_vs_hold','terminal_gain',None,None)]:
        g=d[IDS[:-1]+['date']].copy();g['comparison']=name;g['delta']=d[first]-(d[second] if second else 0);g['mc_variance']=d[mc] if mc else 0.;parts.append(g)
    common=['era','level','date','strategy','cost','policy'];base=d[d.variant.eq('base')];q=d[d.variant.ne('base')].merge(base,on=common,suffixes=('','_base'),validate='many_to_one')
    for field,name,sign in [('model_worst','regime_worst',-1),('model_mean','regime_mean',-1),('terminal_gain','regime_terminal',1)]:
        g=q[IDS[:-1]+['date']].copy();g['comparison']=name;g['delta']=sign*(q[field]-q[field+'_base']);g['mc_variance']=0.;parts.append(g)
    raw=pd.concat(parts,ignore_index=True);raw['month']=raw.date.dt.to_period('M').astype(str);raw['case_id']=raw.groupby(IDS,sort=True).ngroup();raw.to_parquet(out/'paired_dates.parquet',index=False)
    monthly=raw.groupby(IDS+['case_id','month']).agg(delta=('delta','mean'),dates=('delta','size'),mc_sum=('mc_variance','sum')).reset_index();monthly['mc_variance']=monthly.mc_sum/monthly.dates**2;monthly.to_parquet(out/'monthly.parquet',index=False)
    family=monthly.case_id.nunique();assert family==1008;critical=float(norm.ppf(1-.05/(4*family)));rows=[];annual=[]
    for cid,g in monthly.groupby('case_id'):
        g=g.sort_values('month');n=len(g);months=pd.PeriodIndex(g.month,freq='M');x=g.delta.to_numpy();mean=float(x.mean());u=x-mean;variance=float(u@u)
        for lag in range(1,7):
            lookup=dict(zip(months.asi8,u));variance+=2*(1-lag/7)*sum(value*lookup.get(index-lag,0.) for index,value in lookup.items())
        se=float(np.sqrt(max(variance,0))/n);mc=float(np.sqrt(g.mc_variance.sum())/n);years=g.assign(year=months.year).groupby('year').delta.mean();cov=coverage[tuple(g.iloc[0][k] for k in ['era','level','strategy'])];whole_pair=cov['incomplete_dates']==0;eligible=n>=24 and len(years)>=3 and se>1e-15 and whole_pair
        width=critical*(se+mc);low=mean-width if eligible else np.nan;high=mean+width if eligible else np.nan
        rows.append(dict({k:g.iloc[0][k] for k in IDS},case_id=int(cid),months=n,years=len(years),mean=mean,date_weighted_mean=float(np.average(g.delta,weights=g.dates)),historical_hac_se=se,mc_se=mc,whole_pair=whole_pair,**cov,eligible=eligible,adjusted_low=low,adjusted_high=high,positive_years=int(years.gt(0).sum()),negative_years=int(years.lt(0).sum()),stable_support=bool(eligible and low>0 and years.gt(0).all())))
        for year,value in years.items():
            v=g[months.year==year];annual.append(dict(case_id=int(cid),year=int(year),mean=float(value),months=len(v),first_month=v.month.min(),last_month=v.month.max()))
    result=pd.DataFrame(rows);result.to_csv(out/'uncertainty.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual.csv',index=False)
    summary=dict(status='PASS',cases=family,eligible=int(result.eligible.sum()),stable_support=int(result.stable_support.sum()),max_months=int(result.months.max()),max_years=int(result.years.max()),all_years_positive=int(result.positive_years.eq(result.years).sum()),mixed_year_sign=int((result.positive_years.gt(0)&result.negative_years.gt(0)).sum()),critical_value=critical,adoption=False)
    js(out/'summary.json',summary);reads=json.loads((ROOT/'protocols/r293.json').read_text())['inputs']+['protocols/r293.json','src/reversal_stability_r293.py'];js(out/'receipt.json',dict(inputs={p:sha(ROOT/p) for p in reads},outputs={p:sha(out/p) for p in ['paired_dates.parquet','monthly.parquet','uncertainty.csv','annual.csv','summary.json']}));print(summary);print(result.groupby('comparison').agg(cases=('case_id','size'),all_years_positive=('positive_years',lambda x:int((x==result.loc[x.index,'years']).sum())),mixed=('negative_years',lambda x:int(((x>0)&(result.loc[x.index,'positive_years']>0)).sum()))).to_string())
if __name__=='__main__':run()
