"""Supplemental attribution uncertainty and realized benchmark beta, no selection changes."""
from core import *


def main():
    daily=pd.read_csv(OUT/'portfolio_daily.csv',parse_dates=['date'])
    indexpath=TOPIC/'data/processed/index/benchmark_indices_daily.csv'
    index=pd.read_csv(indexpath,parse_dates=['date']);index=index[index.index_alias=='csi300'].set_index('date').sort_index()
    market=index.close.pct_change(fill_method=None).rename('market_return')
    rows=[]
    for (strategy,cost),g in daily.groupby(['strategy','cost_bps']):
        z=g.set_index('date')[['daily_return']].join(market,how='left').dropna()
        beta=float(np.cov(z.daily_return,z.market_return,ddof=1)[0,1]/z.market_return.var(ddof=1))
        rows.append(dict(strategy=strategy,cost_bps=cost,paired_days=len(z),realized_csi300_beta=beta,mean_excess_daily_return=float((z.daily_return-z.market_return).mean())))
    pd.DataFrame(rows).to_csv(OUT/'portfolio_benchmark_beta.csv',index=False)
    write_json(OUT/'economic_source_receipt.json',dict(path=str(indexpath.relative_to(TOPIC)),sha256=digest(indexpath),role='post-registration benchmark exposure attribution only; never enters selection or model'))
    attribution=pd.read_csv(OUT/'portfolio_industry_attribution.csv',parse_dates=['date']);intervals=[]
    for (comparison,metric),g in attribution.groupby(['comparison','metric']):
        for col in ['total_difference','industry_allocation','within_industry_residual']:
            for block in [6,12]:intervals.append(dict(comparison=comparison,metric=metric,component=col,**ci(g.sort_values('date')[col],block)))
    pd.DataFrame(intervals).to_csv(OUT/'portfolio_attribution_intervals.csv',index=False)
    # Paired ES of six-month static cohorts and monthly-rebalanced returns: month blocks only.
    cohorts=pd.read_csv(OUT/'portfolio_cohort_scores.csv',parse_dates=['date'])
    monthly=pd.read_csv(OUT/'portfolio_monthly.csv',parse_dates=['date'])
    from portfolio import es
    esrows=[]
    datasets=[('six_month_cohort',cohorts.pivot(index='date',columns='strategy',values='cohort_return'))]
    datasets += [(f'monthly_rebalance_cost{cost}',g.pivot(index='date',columns='strategy',values='return_value')) for cost,g in monthly.groupby('cost_bps')]
    for name,table in datasets:
        for left,right in [('S1','S0'),('S2','S0'),('S2','S1')]:
            for block in [6,12]:
                idx=bootstrap_indices(len(table),block);a=table[left].to_numpy();b=table[right].to_numpy();k=max(1,int(np.ceil(len(table)*.05)))
                da=np.sort(a[idx],axis=1)[:,:k].mean(axis=1);db=np.sort(b[idx],axis=1)[:,:k].mean(axis=1);diff=da-db
                lo,hi=np.quantile(diff,[.025,.975]);esrows.append(dict(dataset=name,comparison=left+'-'+right,months=len(table),block=block,delta_es05=es(a)-es(b),low95=float(lo),high95=float(hi),interpretation='positive means less-negative tail return'))
    pd.DataFrame(esrows).to_csv(OUT/'portfolio_es_intervals.csv',index=False)
    print('economic diagnostics completed',flush=True)

if __name__=='__main__':main()
