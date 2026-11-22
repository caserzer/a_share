"""Exact industry decomposition and pre-return matching of disagreement names."""
from scipy.optimize import linear_sum_assignment
from settings import *
import accounts


def matches(g,other,control):
    pair_rows=[]
    donors=g[g.E1_low & ~g[other+'_low']]
    opposite=g[~g.E1_low & g[other+'_low']]
    groups=['industry','REV_low'] if control else ['industry']
    groups=groups[0] if len(groups)==1 else groups
    rhs=dict(tuple(opposite.groupby(groups)))
    for group,a in donors.groupby(groups):
        b=rhs.get(group)
        if b is None or a.industry.iloc[0]=='UNKNOWN':
            continue
        a=a.sort_index()
        b=b.sort_index()
        distance=np.abs(np.log(a.base.values[:,None]/b.base.values))
        allowed=distance<=np.log(1.25)+1e-12
        penalty=1+len(a)
        costs=np.column_stack((np.where(allowed,distance,2*penalty),np.full((len(a),len(a)),penalty)))
        left,right=linear_sum_assignment(costs)
        for i,j in zip(left,right):
            if j>=len(b) or not allowed[i,j]:
                continue
            x=a.iloc[i]
            y=b.iloc[j]
            budget=min(x.base-x.E1_target,y.base-y[other+'_target'])
            pair_rows.append(dict(e1_avoided=x.name,other_avoided=y.name,industry=x.industry,
                                 weight_ratio=np.exp(distance[i,j]),budget=budget))
    return pair_rows, float((donors.base-donors.E1_target).sum())


def run():
    accounts.OUT=D
    m=accounts.Market()
    marks=m.marks['flat'][0]
    p=pd.read_parquet(WEAK/'results/targets.parquet')
    sch=pd.read_csv(WEAK/'results/schedule.csv',parse_dates=['signal_date','entry_date','exit_date']).set_index('signal_date')
    ref=pd.read_csv(WEAK/'results/bridge.csv',parse_dates=['signal_date']).set_index('signal_date')
    all_stock=[]
    pairs=[]
    coverage=[]
    rows=[]
    for date,h in p.groupby('signal_date'):
        r=sch.loc[date]
        scope=section(r.exit_date)
        g=h.dropna(subset=['E1','REV','RANK']).set_index('instrument').sort_index().copy()
        # Membership of identical-weight bins deterministically follows instrument order.
        g['size']=pd.qcut(g.base.rank(method='first'),3,labels=['small','middle','large'])
        lo=g.E1_low
        ew=(~lo).astype(float)/(~lo).sum()-lo.astype(float)/lo.sum()
        iw=g.base.where(~lo,0)/g.loc[~lo,'base'].sum()-g.base.where(lo,0)/g.loc[lo,'base'].sum()
        g['equal']=ew*r['shift']
        g['index']=iw*r['shift']
        g['sealed']=g.E1_target-g.base
        contests=[]
        for other,control in [('RANK',False),('REV',False),('RANK',True)]:
            found,eligible_budget=matches(g,other,control)
            contests.append((other,control,found,eligible_budget))
        j=m.symbols.get_indexer(g.index)
        assert j.min()>=0
        g['ret']=marks[m.days.get_loc(r.exit_date),j]/marks[m.days.get_loc(r.entry_date),j]-1
        assert np.isfinite(g.ret).all()
        for other,control,found,eligible_budget in contests:
            for rec in found:
                rec['gap']=g.at[rec['other_avoided'],'ret']-g.at[rec['e1_avoided'],'ret']
                rec['contribution']=rec['gap']*rec['budget']
                pairs.append(dict(signal_date=date,section=scope,other=other,control_rev=control,**rec))
            positive=[x for x in found if x['budget']>0]
            budget=sum(x['budget'] for x in positive)
            gross=sum(x['contribution'] for x in positive)
            coverage.append(dict(signal_date=date,section=scope,other=other,control_rev=control,
                count=len(found),funded=len(positive),matched_budget=budget,eligible_budget=eligible_budget,
                fraction_of_active=budget/r['shift'],unit_return=gross/budget if budget else np.nan,contribution=gross))
        for method in ['equal','index','sealed']:
            w=pd.Series(1.,index=g.index) if method=='equal' else g.base
            ind=(w*g.ret).groupby(g.industry).transform('sum')/w.groupby(g.industry).transform('sum')
            delta=g[method]
            gross=delta*g.ret
            between=delta*ind
            within=delta*(g.ret-ind)
            assert np.isclose(gross.sum(),between.sum()+within.sum(),atol=1e-14)
            old={'equal':'equal_same_budget','index':'index_same_budget_unconstrained','sealed':'sealed_industry_tilt'}[method]
            np.testing.assert_allclose(gross.sum(),ref.at[date,old],rtol=0,atol=1e-12)
            rows.append(dict(signal_date=date,section=scope,method=method,total=gross.sum(),between=between.sum(),
                             within=within.sum(),budget=r['shift']))
            all_stock.append(pd.DataFrame(dict(signal_date=date,section=scope,method=method,base=g.base,
                industry=g.industry,size=g['size'],low=g.E1_low,transfer=delta,received=delta.clip(lower=0),
                reduced=(-delta).clip(lower=0),ret=g.ret,between=between,within=within,gross=gross)).reset_index())
    stocks=pd.concat(all_stock,ignore_index=True)
    stocks.to_parquet(D/'stock_attribution.parquet',index=False)
    dates=pd.DataFrame(rows)
    dates.to_csv(D/'industry_by_date.csv',index=False)
    sizes=stocks.groupby(['section','method','signal_date','size'],observed=True).agg(
        names=('instrument','size'),weak_names=('low','sum'),index_weight=('base','sum'),received=('received','sum'),
        reduced=('reduced','sum'),within=('within','sum'),total=('gross','sum')).reset_index()
    sizes.groupby(['section','method','size'],observed=True).mean(numeric_only=True).to_csv(D/'weight_strata.csv')
    cov=pd.DataFrame(coverage)
    cov.to_csv(D/'match_dates.csv',index=False)
    pd.DataFrame(pairs).to_parquet(D/'pairs.parquet',index=False)
    summary=[]
    for (sec,other,ctrl),g in cov.groupby(['section','other','control_rev']):
        support=g.matched_budget.sum()
        summary.append(dict(section=sec,other=other,control_rev=ctrl,dates=len(g),supported=g.funded.gt(0).sum(),pairs=g.funded.sum(),
            avg_budget=g.matched_budget.mean(),share_eligible=support/g.eligible_budget.sum(),share_total=g.fraction_of_active.mean(),
            weighted_unit=g.contribution.sum()/support,**bootstrap(g.contribution.values)))
    pd.DataFrame(summary).to_csv(D/'match_summary.csv',index=False)
    dates.groupby(['section','method']).mean(numeric_only=True).to_csv(D/'industry_summary.csv')
    print(pd.read_csv(D/'industry_summary.csv').to_string(index=False))


if __name__=='__main__':
    run()
