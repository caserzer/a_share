from engine import *
import json

def months(g,cal):
    g=g.set_index('date').sort_index()
    denominator=g.nav.shift().fillna(1.)
    rows=[]
    for label,d in g.groupby(g.index.to_period('M')):
        dates=cal[cal.to_period('M')==label]
        if len(dates)!=len(d) or not (d.index==dates).all() or d.index[0]==g.index[0]:continue
        base=denominator.loc[d.index[0]]
        net=d.nav.iloc[-1]/base-1
        fee=d.fee.sum()/base
        assert abs(net+fee-d.gross_pnl.sum()/base)<1e-10
        rows.append(dict(month=str(label),net=net,fee=fee,gross=net+fee,buy=d.buy.sum()/base,sell=d.sell.sum()/base))
    return pd.DataFrame(rows)

def grouped(d,keys,cal):
    return pd.concat([months(g,cal).assign(**dict(zip(keys,k))) for k,g in d.groupby(keys)],ignore_index=True)

def samples(arr,rng):
    n=len(arr); k=3
    start=rng.integers(0,n-k+1,size=(10000,(n+k-1)//k))
    idx=(start[:,:,None]+np.arange(k)).reshape(10000,-1)[:,:n]
    return arr[idx].mean(axis=1)

def stats(z,cols=('net','gross','fee')):
    out=[]
    for col in cols:
        chunks=[];counts=[];av=[]
        rng=np.random.default_rng(4101)
        for seg,g in z.groupby('segment'):
            x=g[col].to_numpy()*10000
            boot=samples(x,rng);chunks.append(boot);counts.append(len(x));av.append(x.mean())
            out.append(dict(segment=seg,metric=col,months=len(x),bp=x.mean(),lo=np.quantile(boot,.025),hi=np.quantile(boot,.975),drop_best3=np.sort(x)[:-3].mean()))
        boot=np.average(chunks,axis=0,weights=counts);point=np.average(av,weights=counts)
        out.append(dict(segment='all',metric=col,months=sum(counts),bp=point,lo=np.quantile(boot,.025),hi=np.quantile(boot,.975),
            p_one_sided=(1+np.sum(boot-point>=point))/(1+len(boot))))
    return pd.DataFrame(out)

def main():
    d=pd.read_parquet(RESULT/'daily.parquet')
    cal=pd.read_parquet(LOCAL/'open.parquet',columns=[]).index
    idxraw=pd.read_parquet(STORE/'index800.parquet')
    index=idxraw.set_index(pd.to_datetime(idxraw.trade_date)).close.sort_index()
    monthly=grouped(d,['model','bucket','segment','kind','phase'],cal)
    for g in ['nav','cash','fee','buy','sell','gross_pnl']:
        strict=d.query('kind=="strict" and phase>=0').groupby(['segment','model','bucket','date'])[g].mean()
        before=d.query('kind=="prenetted" and bucket!="pool"').set_index(['segment','model','bucket','date'])[g].reindex(strict.index)
        assert (strict-before).abs().max()<1e-10,(g,(strict-before).abs().max())
    monthly.to_parquet(RESULT/'months.parquet',index=False)
    z=monthly.query('model=="refit" and phase==-1 and kind=="strict" and bucket in ("head","runner")')
    z=z.set_index(['bucket','segment','month'])[['net','gross','fee','buy','sell']].sort_index()
    gap=(z.loc['head']-z.loc['runner']).reset_index()
    gap.to_csv(RESULT/'monthly_pair.csv',index=False)
    summary=stats(gap)
    summary.to_csv(RESULT/'primary.csv',index=False)
    print(summary,flush=True)
    summary2=[];phases=[]
    metrics=['net','fee','gross','buy','sell']
    for (kind,phase),g in monthly.groupby(['kind','phase']):
        v=g.set_index(['model','bucket','segment','month'])[metrics]
        if not all((model,bucket) in v.index.droplevel(['segment','month']) for model in ['refit','transfer'] for bucket in ['head','runner','decile']):continue
        contrasts={}
        for model in ['refit','transfer']:
            contrasts[model+'_head_minus_runner']=v.loc[model,'head']-v.loc[model,'runner']
            contrasts[model+'_head_minus_decile']=v.loc[model,'head']-v.loc[model,'decile']
        for bucket in ['head','runner','decile']:
            contrasts['refit_minus_transfer_'+bucket]=v.loc['refit',bucket]-v.loc['transfer',bucket]
        contrasts['training_difference_in_head_minus_runner']=contrasts['refit_head_minus_runner']-contrasts['transfer_head_minus_runner']
        for key,h in contrasts.items():
            for seg,a in h.groupby(level='segment'):
                phases.append(dict(kind=kind,phase=phase,contrast=key,segment=seg,months=len(a),mean_net_bp=1e4*a.net.mean()))
            if phase==-1:
                summary2.append(stats(h.reset_index(),('net',)).assign(kind=kind,contrast=key))
    pd.concat(summary2).to_csv(RESULT/'model_bridge.csv',index=False)
    pd.DataFrame(phases).to_csv(RESULT/'phase_summary.csv',index=False)
    daily=[]
    for (model,bucket,segment,kind,phase),a in d.groupby(['model','bucket','segment','kind','phase']):
        a=a.set_index('date')
        for year,g in [('all',a),*list(a.groupby(a.index.year))]:
            opening=1 if g.index[0]==a.index[0] else a.nav.iloc[a.index.get_loc(g.index[0])-1]
            i=g.index[0] if g.index[0]==a.index[0] else a.index[a.index.get_loc(g.index[0])-1]
            cost=g.fee.sum()/opening;buy=g.buy.sum()/opening;sell=g.sell.sum()/opening
            assert abs(cost-(.001*buy+.002*sell)*({'double_fee':2,'zero_fee':0}.get(kind,1)))<1e-10
            dd=np.r_[opening,g.nav.values];dd=(dd/np.maximum.accumulate(dd)-1).min()
            daily.append(dict(model=model,bucket=bucket,segment=segment,kind=kind,phase=phase,year=year,
                start=g.index[0],end=g.index[-1],days=len(g),net=g.nav.iloc[-1]/opening-1,gross=g.gross_pnl.sum()/opening,
                fee=cost,buy=buy,sell=sell,fee_per_10000=cost*1e4/(buy+sell) if buy+sell else np.nan,
                crossed=g.crossed.sum()/opening,index_return=index.at[g.index[-1]]/index.at[i]-1,max_drawdown=dd,
                avg_hhi=g.hhi.mean(),max_position=g.max_weight.max(),blocked_budget=g.blocked_budget.sum()/opening))
    pd.DataFrame(daily).to_csv(RESULT/'segments_years.csv',index=False)
    orders=pd.read_parquet(RESULT/'orders.parquet')
    orders['buy']=orders.net.clip(lower=0);orders['sell']=(-orders.net).clip(lower=0)
    orders['crossed_buy']=(orders.within.clip(lower=0)-orders.buy)
    adv=pd.read_parquet(LOCAL/'money.parquet').rolling(20,min_periods=20).mean().shift()
    lookup=adv.index.get_indexer(orders.date),adv.columns.get_indexer(orders.instrument)
    orders['prior_adv20']=adv.to_numpy()[lookup]
    orders['participation_at_1m_yuan']=abs(orders.net)*1e6/orders.prior_adv20
    orders.groupby(['bucket','segment','event'])[['target','buy','sell','fee','blocked','crossed_buy']].sum().to_csv(RESULT/'boundary_orders.csv')
    broker=orders.groupby(['bucket','segment','date','instrument']).agg(net=('net','sum'),prior_adv20=('prior_adv20','first')).reset_index()
    broker=broker[broker.net.abs()>1e-15].copy()
    broker['participation_at_1m_yuan']=broker.net.abs()*1e6/broker.prior_adv20
    broker.groupby(['bucket','segment']).participation_at_1m_yuan.quantile([.5,.95,.99,1]).to_csv(RESULT/'participation.csv')
    broker.to_parquet(RESULT/'broker_orders.parquet',index=False)
    # Compare nominal target dollars at consecutive same-sleeve decision times. Keep
    # the execution path separate because share price moves and blocked lots matter.
    key=['bucket','segment','sleeve','instrument','entry_idx']
    active=orders.copy()
    marketdays=cal
    starts=active.segment.map({i+1:marketdays.get_loc(pd.Timestamp(z[0])) for i,z in enumerate(RANGES)})
    active=active[(active.entry_idx-starts)%10==active.sleeve]
    now=active[active.target>0][key+['target']].copy()
    old=now.rename(columns={'target':'previous_target'}).copy()
    old['entry_idx']+=10
    turnover=now.merge(old,on=key,how='outer',validate='1:1')
    ends={i+1:marketdays.get_loc(pd.Timestamp(z[2])) for i,z in enumerate(RANGES)}
    turnover=turnover[turnover.entry_idx<=turnover.segment.map(ends)].copy()
    turnover=turnover.merge(active[key+['event']],on=key,how='left',validate='1:1')
    # A blocked entry from the prior period may have no order now. Recover its
    # exit destination directly from all eligible frozen scores at this decision.
    gaps=turnover.event.isna()
    if gaps.any():
        frozen=pd.read_parquet(OUT800/'scores.parquet',columns=['entry_idx','instrument','refit_R']).sort_values(['entry_idx','refit_R','instrument'],ascending=[True,False,False])
        fgt=frozen.groupby('entry_idx');frozen['rank']=fgt.cumcount()+1;frozen['l']=fgt.instrument.transform('size')//10
        ksmall=pd.read_parquet(DEST/'daily_scores.parquet',columns=['entry_idx']).groupby('entry_idx').size()//10
        frozen['k']=frozen.entry_idx.map(ksmall)
        frozen['exit_to']=np.select([frozen['rank']<=frozen.k,frozen['rank']<=frozen.l],['exit_to_head','exit_to_runner'],default='exit_to_below_L')
        missing=turnover.loc[gaps,['entry_idx','instrument']].merge(frozen[['entry_idx','instrument','exit_to']],how='left',on=['entry_idx','instrument'],validate='m:1')
        termination=turnover.loc[gaps].entry_idx.gt(turnover.loc[gaps].segment.map({i+1:marketdays.get_loc(pd.Timestamp(z[1]))-10 for i,z in enumerate(RANGES)}))
        turnover.loc[gaps,'event']=np.where(termination,'wind_down',missing.exit_to.fillna('exit_to_ineligible'))
    turnover[['target','previous_target']]=turnover[['target','previous_target']].fillna(0)
    change=turnover.target-turnover.previous_target
    turnover['target_increase']=change.clip(lower=0);turnover['target_decrease']=(-change).clip(lower=0)
    turnover.groupby(['bucket','segment','event'])[['previous_target','target','target_increase','target_decrease']].sum().to_csv(RESULT/'target_rotation.csv')
    check=orders.groupby(['bucket','segment','date'])[['buy','sell','fee']].sum()
    q=d.query('model=="refit" and kind=="strict" and phase==-1 and bucket!="pool"').set_index(['bucket','segment','date'])[['buy','sell','fee']]
    np.testing.assert_allclose(check.reindex(q.index).fillna(0),q,atol=1e-10)
    ep38=pd.read_csv(RESULT/'ep38_replay.csv')
    assert abs(ep38.error).max()<1e-10
    print(ep38.groupby(['segment','model']).net.mean().unstack().diff(axis=1)*1e4)
if __name__=='__main__':main()
