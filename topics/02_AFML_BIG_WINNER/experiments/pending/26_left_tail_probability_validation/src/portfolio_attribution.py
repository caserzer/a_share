"""Industry allocation/selection diagnosis for frozen matched filter lists."""
from core import *


def main():
    selection=pd.read_parquet(CACHE/'portfolio_selections.parquet')
    full=pd.read_parquet(CACHE/'all_predictions.parquet');ref=full[full.model.eq('M_R')][['date','instrument','actual','industry_sector','industry_stale']]
    d=selection.merge(ref,on=['date','instrument'],validate='many_to_one')
    weights=[];attribution=[]
    for date,cohort in d.groupby('date'):
        pool=cohort[['instrument','actual','industry_sector']].drop_duplicates('instrument')
        observed=pool[pool.actual.notna()].copy()
        if not len(observed):continue
        observed['event']=(observed.actual<-.2).astype(float)
        industry_pool=observed.groupby('industry_sector').agg(return_value=('actual','mean'),loss_rate=('event','mean'))
        tables={}
        for strategy,g in cohort.groupby('strategy'):
            g=g[g.selected&g.actual.notna()].copy();g['event']=(g.actual<-.2).astype(float)
            t=g.groupby('industry_sector').agg(count=('instrument','size'),return_value=('actual','mean'),loss_rate=('event','mean'))
            t['weight']=t['count']/len(g);tables[strategy]=t
            for sector,row in t.iterrows():weights.append(dict(date=date,strategy=strategy,industry_sector=sector,weight=row.weight,rows=int(row['count']),realized_return=row.return_value,loss20_rate=row.loss_rate))
        for left,right in [('S1','S0'),('S2','S0'),('S2','S1')]:
            a=tables[left].reindex(industry_pool.index);b=tables[right].reindex(industry_pool.index)
            wa=a.weight.fillna(0);wb=b.weight.fillna(0)
            for metric,pcol in [('return_value','return_value'),('loss_rate','loss_rate')]:
                total=float((wa*a[metric].fillna(0)).sum()-(wb*b[metric].fillna(0)).sum())
                allocation=float(((wa-wb)*industry_pool[pcol]).sum())
                attribution.append(dict(date=date,comparison=left+'-'+right,metric=metric,total_difference=total,industry_allocation=allocation,within_industry_residual=total-allocation))
    pd.DataFrame(weights).to_csv(OUT/'portfolio_industry_weights.csv',index=False)
    pd.DataFrame(attribution).to_csv(OUT/'portfolio_industry_attribution.csv',index=False)
    scores=pd.read_csv(OUT/'portfolio_cohort_scores.csv',parse_dates=['date']);intervals=[]
    for left,right in [('S1','S0'),('S2','S0'),('S2','S1')]:
        for metric in ['loss20_rate','cohort_return']:
            a=scores[scores.strategy.eq(left)];b=scores[scores.strategy.eq(right)]
            for block in [6,12]:intervals.append(dict(comparison=left+'-'+right,metric=metric,**ci(paired(a,b,metric),block)))
    pd.DataFrame(intervals).to_csv(OUT/'portfolio_cohort_intervals.csv',index=False)
    print('industry attribution and paired cohort intervals complete',flush=True)

if __name__=='__main__':main()
