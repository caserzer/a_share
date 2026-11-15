"""Paired leader increment, not a causal catch-up or execution test."""
import pandas as pd
from common import *
from evaluate_unique_r105 import interval
G=['era','level','cohort','task','horizon']

def run():
    out=ROOT/'outputs/r109';p=pd.read_parquet(out/'predictions.parquet');keys=KEY+['date','cohort','task','horizon','year']
    a=p[p.method.eq('controls')].drop(columns='method');b=p[p.method.eq('with_leader')][keys+['prediction','decision']]
    paired=a.merge(b,on=keys,how='outer',validate='one_to_one',suffixes=('_base','_leader'),indicator=True);assert paired._merge.eq('both').all();paired=paired.drop(columns='_merge');paired.to_parquet(out/'paired_predictions.parquet',index=False)
    rows=[]
    for key,g in paired.groupby(G+['date']):
        v=g[g.y.notna()];k=max(1,int(np.ceil(len(g)*.2)))
        old=set(g.sort_values(['prediction_base','industry_code'],ascending=[False,True]).head(k).industry_code);new=set(g.sort_values(['prediction_leader','industry_code'],ascending=[False,True]).head(k).industry_code)
        r=dict(zip(G+['date'],key),n_signal=len(g),n_mature=len(v),selected=k,shared_selected=len(old&new),baseline_utility=np.nan,leader_utility=np.nan,delta=np.nan,mse_reduction=np.nan,logloss_reduction=np.nan)
        if len(v):
            r['mse_reduction']=float(((v.prediction_base-v.y)**2-(v.prediction_leader-v.y)**2).mean())
            if key[3]=='return':
                if len(v)>=20 and v.prediction_base.nunique()>1 and v.prediction_leader.nunique()>1:
                    r.update(baseline_utility=v.prediction_base.corr(v.y,method='spearman'),leader_utility=v.prediction_leader.corr(v.y,method='spearman'))
            else:
                r.update(baseline_utility=-float(((v.prediction_base-v.y)**2).mean()),leader_utility=-float(((v.prediction_leader-v.y)**2).mean()))
                def loss(x):
                    x=np.clip(x,1e-15,1-1e-15);return -(v.y*np.log(x)+(1-v.y)*np.log1p(-x)).mean()
                r['logloss_reduction']=loss(v.prediction_base)-loss(v.prediction_leader)
        r['delta']=r['leader_utility']-r['baseline_utility'];rows.append(r)
    dates=pd.DataFrame(rows);dates.to_csv(out/'paired_date_metrics.csv',index=False);annual=[];summary=[]
    for key,g in dates.assign(year=dates.date.dt.year).groupby(G+['year']):annual.append(dict(zip(G+['year'],key),months=int(g.delta.notna().sum()),mean_delta=g.delta.mean(),mean_mse_reduction=g.mse_reduction.mean(),mean_logloss_reduction=g.logloss_reduction.mean()))
    for key,g in dates.groupby(G):
        se,lo,hi,alo,ahi=interval(g,3 if key[-1]==20 else 6);years=g.groupby(g.date.dt.year).delta.mean().dropna();n=int(g.delta.notna().sum())
        support=key[2]=='main80' and key[-1]==20 and n>=24 and len(years)>=3 and years.gt(0).all() and alo>0
        summary.append(dict(zip(G,key),metric='IC_improvement' if key[3]=='return' else 'Brier_reduction',months=n,mean_delta=g.delta.mean(),standard_error=se,low95=lo,high95=hi,family60_low=alo,family60_high=ahi,positive_years=int(years.gt(0).sum()),evaluated_years=len(years),mean_mse_reduction=g.mse_reduction.mean(),mean_logloss_reduction=g.logloss_reduction.mean(),selected=int(g.selected.sum()),shared_selected=int(g.shared_selected.sum()),historical_support=bool(support),adopted=False))
    pd.DataFrame(annual).to_csv(out/'annual_metrics.csv',index=False);pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
    coverage=pd.read_parquet(out/'coverage.parquet');coverage.groupby(['era','level']).agg(catalogue_union_rows=('date','size'),original_panel_rows=('observed_panel_row','sum'),baseline_ready=('baseline_ready','sum'),main80=('main80','sum'),strict100=('strict100','sum')).to_csv(out/'coverage_summary.csv')
    paths=[out/'predictions.parquet',out/'coverage.parquet',Path(__file__),ROOT/'src/evaluate_unique_r105.py']
    js(out/'evaluation_receipt.json',dict(reads={str(p):sha(p) for p in paths},outputs={n:sha(out/n) for n in ['paired_predictions.parquet','paired_date_metrics.csv','annual_metrics.csv','summary.csv','coverage_summary.csv']},historical_support_groups=sum(x['historical_support'] for x in summary),adopted=False))
    print(pd.DataFrame(summary)[G+['months','mean_delta','family60_low','family60_high','historical_support']].to_string(index=False))

if __name__=='__main__':run()
