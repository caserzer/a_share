"""Aggregate the reconciled E1 paths without treating blocked opportunity P&L as NAV."""
from pathlib import Path
import numpy as np, pandas as pd
HERE=Path(__file__).resolve().parent; OLD=next(HERE.parents[2].glob('41_*'))
def full_calendar(pool):
    if pool==300:
        z=pd.read_csv(OLD/'e1_e2/300/results/full_months.csv').rename(columns={'scope':'segment'})
    else:
        z=pd.read_csv(OLD/'e1_800/results/monthly.csv').query('registered_month')
    return z[['segment','month']].drop_duplicates()
def read(name):
    return pd.concat([pd.read_parquet(HERE/f'{name}_{k}.parquet').assign(pool=k) for k in [300,800]],ignore_index=True)
def groups(z,keys):
    cols='pairs dates day_opportunities ticket executable_capital actual_switched matched_ticket expected realized error realized_bp expected_bp fee'.split()
    out=[]
    for k,g in z.groupby(keys,observed=True):
        valid=g.realized.notna()&g.expected.notna()
        d=g[valid];days=g.drop_duplicates('idx')
        E=d.expected.sum(min_count=1);R=d.realized.sum(min_count=1);K=d.ticket.sum(min_count=1)
        out.append((*k,len(g),len(days),days.same_day_pairs.sum(),g.ticket.sum(),g.executable_capital.sum(),g.actual_switched.sum(),K,E,R,R-E,R/K*1e4,E/K*1e4,g.fees.sum()))
    return pd.DataFrame(out,columns=keys+cols)
def main():
    op=read('opportunities')
    for name in ['old','new']:
        op[name+'_rank']=pd.cut(op[name+'_pct'],[-.01,1/3,2/3,1.01],labels=['low','mid','high'])
    op['prior']=np.select([op.old_h10_excess.isna(),op.old_h10_excess.gt(0),op.old_h10_excess.lt(0)],['unknown','up','down'],default='flat')
    basic=['pool','segment','model','test','accepted']
    root=groups(op,basic)
    root.to_csv(HERE/'opportunity_summary.csv',index=False)
    grid=groups(op,basic+['new_rank','old_rank','dispersion'])
    frame=root[basic].merge(pd.MultiIndex.from_product([['low','mid','high'],['low','mid','high'],['low','mid','high','short_history']],names=['new_rank','old_rank','dispersion']).to_frame(index=False),how='cross')
    frame.merge(grid,how='left').to_csv(HERE/'opportunity_grid.csv',index=False)
    groups(op,basic+['new_rank','old_rank','dispersion','prior']).to_csv(HERE/'opportunity_old_path_grid.csv',index=False)
    groups(op,basic+['prior']).to_csv(HERE/'opportunity_old_path.csv',index=False)
    fees=read('fees');fees['month']=fees.date.dt.strftime('%Y-%m')
    pack=[]
    for (pool,sg,model,test),g in fees.groupby(['pool','segment','model','test']):
        g=g.sort_values('idx').copy();g['previous']=g.nav.shift().fillna(1)
        g['cash_ratio']=g.cash/g.nav
        for month,t in g.groupby('month'):
            base=t.previous.iloc[0];paid=t.fee.sum()/base;net=t.nav.iloc[-1]/base-1
            pack.append((pool,sg,model,test,month,net,net+paid,paid,(t.buy+t.sell).sum()/base,t.cash_ratio.mean(),t.within_sleeve_saved.sum()/base,t.across_sleeve_saved.sum()/base))
    monthly=pd.DataFrame(pack,columns='pool segment model test month net gross fee turnover cash_ratio within across'.split())
    monthly=monthly.merge(pd.concat([full_calendar(k).assign(pool=k) for k in [300,800]]),validate='m:1')
    monthly.to_csv(HERE/'accounts_monthly.csv',index=False)
    annual=[];diff=[]
    for (pool,seg,model),g in monthly.groupby(['pool','segment','model']):
        for real,ref in [('cost','base'),('same_count','base'),('cost','same_count'),('cost_plus10','base'),('cost_plus10','same_count_plus10')]:
            a=g[g.test.eq(real)].set_index('month').sort_index();b=g[g.test.eq(ref)].set_index('month').sort_index();z=(a.select_dtypes('number')-b.select_dtypes('number'))*1e4
            for yr,df in [('all',z),*z.groupby(z.index.str[:4])]:
                dates=df.index;m=len(df)
                cumulative_bp=((1+a.loc[dates,'net']).prod()-(1+b.loc[dates,'net']).prod())*1e4
                diff.append((pool,seg,model,real,ref,yr,m,df.net.mean(),df.gross.mean(),df.fee.mean(),df.turnover.mean(),df.cash_ratio.mean(),df.net.nsmallest(m-3).mean() if m>3 else np.nan,cumulative_bp))
    diff=pd.DataFrame(diff,columns='pool segment model test ref year months net_bp gross_bp fee_bp turnover_bp cash_bp trim_best3_bp compounded_gap_bp'.split())
    diff.to_csv(HERE/'comparisons.csv',index=False)
    fifo=read('lifecycle')
    fifo['age']=np.select([fifo.days.lt(10),fifo.days.eq(10),fifo.days.le(30)],['under1','1','2to3'],default='over3')
    fifo.groupby(['pool','segment','model','test','age','outcome']).agg(lots=('shares','size'),minimum_days=('days','min'),maximum_days=('days','max'),buy_principal=('cost_basis','sum'),sell_proceeds=('sell_value',lambda x:x.sum(min_count=1)),buy_fee=('buy_fee','sum'),sell_fee=('sell_fee','sum')).to_csv(HERE/'fifo_summary.csv')
    f=fees.groupby(['pool','segment','model','test']).agg(trading_dates=('idx','size'),real=('fee','sum'),gross=('theoretical_unnetted','sum'),by_sleeve=('theoretical_by_sleeve','sum'),within=('within_sleeve_saved','sum'),across=('across_sleeve_saved','sum'),max_parity=('parity_error','max'))
    v=fifo.groupby(['pool','segment','model','test'])[['buy_fee','sell_fee']].sum()
    f=f.join(v);f['fifo_resid']=f.real-f.buy_fee-f.sell_fee
    assert f.fifo_resid.abs().max()<1e-9
    assert (f.gross-f.within-f.across-f.real).abs().max()<1e-9
    f.to_csv(HERE/'fee_reconciliation.csv')
    sb=read('same_budget')
    c=sb.pivot(index=['pool','segment','model','test','idx'],columns='rule',values=['net','gross','fee','named_budget','portfolio_purchases'])
    assert (c.named_budget.real-c.named_budget.mechanical).abs().max()==0
    d=(c.xs('real',level=1,axis=1)-c.xs('mechanical',level=1,axis=1))*1e4
    d['dates']=1;summary=d.groupby(level=['pool','segment','model','test']).agg({'net':'mean','gross':'mean','fee':'mean','portfolio_purchases':'mean','dates':'sum'})
    summary.to_csv(HERE/'same_budget_summary.csv')
    ref=pd.read_csv(OLD/'e1_e2/300/results/same_budget_summary.csv')
    for r in ref[ref.arm.str.startswith('E1')].itertuples():
        _,a,n=r.arm.split('_')
        x=summary.loc[(300,r.scope,a,'cost' if n=='0' else 'cost_plus10')]
        np.testing.assert_allclose(x[['net','gross','fee']],[r.net,r.gross,r.fee],atol=1e-9)
    for po in [300,800]:
        ref=monthly[monthly.pool==po]
        if po==800:
            z=pd.read_csv(OLD/'e1_800/results/monthly.csv').query('registered_month')
            z['model']=z.model.replace({'ridge':'hold'})
            m=ref.merge(z,on=['segment','model','test','month']);assert len(m)==len(ref)
            np.testing.assert_allclose(m.net_x,m.net_y,atol=1e-10)
    print(diff[(diff.year=='all')&(diff.test=='cost')][['pool','segment','model','ref','months','net_bp','gross_bp','fee_bp','trim_best3_bp']].round(2).to_string(index=False))
    print(summary.round(2).to_string())
if __name__=='__main__':main()
