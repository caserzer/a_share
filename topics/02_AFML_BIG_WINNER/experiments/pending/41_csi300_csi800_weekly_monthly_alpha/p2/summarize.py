from inputs import *

def save(name,rows):
    pd.DataFrame(rows).to_csv(OUT/(name+'.csv'),index=False)

def monthly(g):
    g=g.sort_values('date').copy()
    g['month']=g.date.dt.strftime('%Y-%m')
    g['opening']=g.nav.shift().fillna(1.)
    a=g.groupby('month').agg(opening=('opening','first'),closing=('nav','last'),
        fee=('fee','sum'),buy=('buy','sum'),sell=('sell','sum'),crossed=('crossed','sum'))
    a['net']=a.closing/a.opening-1
    for c in ['fee','buy','sell','crossed']:a[c]/=a.opening
    a['gross']=a.net+a.fee
    return a.iloc[1:-1].reset_index()

def main():
    d=pd.read_parquet(OUT/'funded_daily.parquet')
    x=json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    idx=pd.DataFrame(x['items'],columns=x['fields']).set_index('trade_date').close
    idx.index=pd.to_datetime(idx.index)
    idx=idx.sort_index()
    month_index=idx.groupby(idx.index.strftime('%Y-%m')).last().pct_change()
    mo=[];stats=[];annual=[]
    for (scope,arm,mul),g in d.groupby(['scope','arm','mul']):
        g=g.sort_values('date')
        z=monthly(g).assign(scope=scope,arm=arm,mul=mul)
        z['index']=z.month.map(month_index)
        mo.append(z)
        stats.append(dict(scope=scope,arm=arm,mul=mul,terminal=g.nav.iloc[-1],mdd=(g.nav/g.nav.cummax().clip(lower=1)-1).min(),
                          index=idx.loc[g.date.iloc[-1]]/idx.loc[g.date.iloc[0]]-1,
                          fee=g.fee.sum(),crossed=g.crossed.sum()))
        g['prev']=g.nav.shift().fillna(1)
        for y,f in g.groupby(g.date.dt.year):
            annual.append(dict(scope=scope,arm=arm,mul=mul,year=y,start=f.date.iloc[0],end=f.date.iloc[-1],net=f.nav.iloc[-1]/f.prev.iloc[0]-1))
    save('accounts',stats);save('annual',annual)
    mo=pd.concat(mo)
    save('full_months',mo)
    contrast=[]
    for (scope,mul),g in mo.groupby(['scope','mul']):
        z=g.pivot(index='month',columns='arm',values=['net','gross','fee'])
        for a,b in [('tree','rank'),('tree','hold'),('rank','hold')]:
            f=pd.DataFrame({c:z[c][a]-z[c][b] for c in ['net','gross','fee']})
            best=f.net.nlargest(3).index
            remaining=z['net'].drop(best)
            contrast.append(dict(scope=scope,mul=mul,a=a,b=b,months=len(f),net_bp=f.net.mean()*1e4,gross_bp=f.gross.mean()*1e4,fee_bp=f.fee.mean()*1e4,
                excluded=','.join(best),rest_bp=f.drop(best).net.mean()*1e4,rest_compound_pp=100*((1+remaining[a]).prod()-(1+remaining[b]).prod())))
    save('contrasts',contrast)
    cs=pd.read_parquet(OUT/'common_start.parquet')
    save('common_periods',cs)
    a=cs.copy()
    for c in ['gross','fee','net']:a[c+'_per_budget']=a[c]*a.nav0/a.planned_budget
    save('common_summary',a.groupby(['scope','arm']).agg({k:'mean' for k in ['gross','fee','net','net_per_budget','gross_per_budget','fee_per_budget','terminal_fee']}).reset_index())
    pos=pd.read_parquet(OUT/'common_positions.parquet')
    pos['band']=np.select([pos.decile.isna(),pos.decile.eq(1),pos.decile.le(5),pos.decile.lt(10)],['unknown','D1','D2-D5','D6-D9'],default='D10')
    pos=pos.groupby(['scope','arm','role','band'])[['gross','fee','filled']].sum().reset_index()
    save('by_position',pos)
    co=pd.read_parquet(OUT/'corners.parquet')
    decomposition=[]
    for metric in ['whole_net','net','gross','fee']:
        w=co.pivot(index=['scope','entry_idx'],columns=['state','rule'],values=metric)*1e4
        rr=w['rank','rank'];tt=w['tree','tree'];tr=w['tree','rank'];rt=w['rank','tree']
        a=(rt-rr+tt-tr)/2;b=(tr-rr+tt-rt)/2
        np.testing.assert_allclose(a+b,tt-rr,atol=1e-9)
        decomposition.append(pd.DataFrame(dict(decision_bp=a,state_bp=b,interaction_bp=tt-tr-rt+rr,total_bp=tt-rr)).reset_index().assign(metric=metric))
    save('decomposition',pd.concat(decomposition))
    leg=pd.read_parquet(OUT/'next_rebalance.parquet')
    summary=[]
    for (scope,arm),g in leg.groupby(['scope','arm']):
        v=g[g.next_status!='end'];at=v.held_before.astype(bool)
        summary.append(dict(scope=scope,arm=arm,seats=len(g),end_seats=len(g)-len(v),ineligible=(v.next_status=='ineligible').sum(),
                   planned=g.planned.sum(),filled=g.bought.sum(),weighted_filled=g.bought.sum()/g.planned.sum(),
                   promoted_count=v.promoted.mean(),promoted_capital=v.loc[v.promoted.eq(True),'next_pre_value'].sum()/v.next_pre_value.sum(),
                   target_kept_count=v.target_kept.mean(),actual_held=(v.actual_continued_value>0).mean(),
                   actual_continued_capital=v.actual_continued_value.sum()/v.next_pre_value.sum(),
                   legacy_seats=v.forced_legacy.sum(),linked_fees=v.next_fee.sum(),
                   total_fees=d.query('scope==@scope and arm==@arm and mul==1').fee.sum()))
    save('next_summary',summary)
    paths=pd.read_parquet(OUT/'random_paths.parquet')
    effects=mo.query('arm=="tree" and mul==1')[['scope','month','net']].merge(paths,on=['scope','month'],suffixes=('_tree','_random'),validate='1:m')
    effects['delta']=(effects.net_tree-effects.net_random)*1e4
    means=effects.groupby(['mode','scope','seed']).delta.mean()
    save('random_summary',means.groupby(['mode','scope']).agg(['median','min','max']).reset_index())
    win=pd.read_parquet(OUT/'phase_windows.parquet')
    w=win.pivot(index=['scope','phase','entry_idx'],columns='arm',values='net')
    save('phase_comparison',((w.tree-w['rank'])*1e4).groupby(['scope','phase']).agg(['mean','size']).reset_index())
    validate=(leg.loc[leg.next_status!='end'].groupby(['scope','arm']).next_fee.sum())
    total=pd.DataFrame(stats).query('mul==1').set_index(['scope','arm']).fee
    bridge=pd.DataFrame(dict(linked_next_fee=validate,all_fees=total.reindex(validate.index)))
    bridge['other_fees']=bridge.all_fees-bridge.linked_next_fee
    save('fee_bridge',bridge.reset_index())
if __name__=='__main__':main()
