"""Two-ETF, lagged-share sensitivity on the contiguous registered later account."""
from pathlib import Path
import sys
HERE6=Path(__file__).resolve().parent
REG=HERE6.parents[1];sys.path.insert(0,str(REG/'u2'))
from common import *
OUT=HERE6/'results';SUB=OUT/'segment'
def main():
    s=Study();s.style();m=s.m
    source=pd.read_parquet(REG/'p2/results/scores.parquet')
    dates=m.days;i0,x=m.days.get_indexer(['2025-03-03','2026-10-12'])
    source=source[source.entry_idx.between(i0,x-10)]
    z=pd.concat([pd.read_parquet(SUB/(f'etf_{exchange}_cons.parquet')) for exchange in ['sh','sz']])
    byday={pd.Timestamp(t):g for t,g in z.groupby('trade_date')}
    amount=pd.read_parquet(OUT/'fund_share.parquet').pivot(index='trade_date',columns='ts_code',values='fd_share')
    amount.index=pd.DatetimeIndex(amount.index);amount=amount.reindex(dates)
    flows=amount.diff(5)*10000 # fund_share is 10,000 fund units
    fundnav=pd.read_parquet(OUT/'fund_nav.parquet').pivot(index='nav_date',columns='ts_code',values='unit_nav')
    fundnav.index=pd.DatetimeIndex(fundnav.index)
    nav=fundnav.reindex(dates)
    # Discontinuities are an audit proxy; this threshold does not determine returns.
    rows=[]
    for col in amount:
        a=amount[col].pct_change(fill_method=None).iloc[i0-6:x]
        b=nav[col].pct_change(fill_method=None).iloc[i0-6:x]
        jumps=(a.abs()>.2)&(b.abs()>.2)&(a*b<0)
        rows.append(dict(fund=col,max_abs_share_change=a.abs().max(),max_abs_unit_nav_change=b.abs().max(),
                         share_and_inverse_nav_jumps_20pct=int(jumps.sum())))
    splits=pd.DataFrame(rows)
    splits.to_csv(SUB/'split_checks.csv',index=False)
    iw=pd.read_parquet(SUB/'index_weight.parquet')
    iw['instrument']=iw.con_code.str[-2:]+iw.con_code.str[:6]
    ix=iw.pivot(index='trade_date',columns='instrument',values='weight').fillna(0)
    ix.index=pd.DatetimeIndex(ix.index)
    delta=ix.diff()
    # Holdings in an index-weight file outside the universe contribute no weight.
    dd=delta.reindex(columns=m.symbols,fill_value=0)
    plans={a:s.blank(31) for a in ['ridge','etf_allowed','etf_with_refund','index_change','sector_flow']}
    info=[];target=[];progress=[]
    for e,g in source.groupby('entry_idx'):
        signal=dates[e-1];dateidx=e-1
        g=g.sort_values(['R','instrument'],ascending=False)
        ids=m.symbols.get_indexer(g.instrument);k=len(ids)//10;h=k//5
        top=np.arange(k);res=np.arange(k,2*k);rb=res[:h]
        tr=np.lexsort((-ids,-g['T'].to_numpy()));rm=tr[np.isin(tr,top)][-h:]
        core=top[~np.isin(top,rm)]
        plans['ridge'][e,:k]=ids[np.r_[core,rb]]
        caprank=pct(s.cap[dateidx,ids])
        momrank=pct(m.c[dateidx,ids]/m.c[dateidx-20,ids]-1)
        sector=s.sectors[dateidx,ids]
        pts=byday[signal].copy()
        assert set(pts.ts_code)==set(amount.columns) and not pts.duplicated(['ts_code','con_code']).any()
        pts['instrument']=pts.con_code.str[-2:]+pts.con_code.str[:6]
        pts['j']=m.symbols.get_indexer(pts.instrument)
        pts=pts[pts.j>=0].copy()
        pts['money_per_unit']=pts.qty*s.raw.iloc[dateidx-1].to_numpy()[pts.j]/900000
        adv=s.adv.iloc[dateidx,ids].to_numpy()
        cap_proxy=float((flows.iloc[dateidx-1]*nav.iloc[dateidx-1]).sum(min_count=2))
        vs={}
        for arm,flag in [('etf_allowed',pts.sub_flag.eq('允许')),('etf_with_refund',pts.sub_flag.str.contains('允许|退补'))]:
            sub=pts[flag & pts.qty.gt(0)].copy()
            per=sub.ts_code.map(flows.iloc[dateidx-1])
            sub['flow']=sub.money_per_unit*per
            nominal=sub.groupby('instrument').flow.sum(min_count=1).reindex(g.instrument).to_numpy()
            vs[arm]=nominal/adv
            if arm=='etf_allowed':
                coverage=np.isfinite(vs[arm])
                sf=pd.DataFrame(dict(sector=sector,flow=nominal,adv=adv)).dropna()
                aggregate=sf.groupby('sector').flow.sum()/sf.groupby('sector').adv.sum()
                vs['sector_flow']=pd.Series(sector).map(aggregate).to_numpy()
        last=dd.index.searchsorted(signal,side='left')-1
        assert last>=1
        vs['index_change']=dd.iloc[last].to_numpy()[ids]
        cov=np.isfinite(caprank)&np.isfinite(momrank)&(sector>=0)&coverage&np.isfinite(vs['index_change'])
        counts={}
        for arm,val in vs.items():
            # One matched budget seat per original reserve buy. Every seat can keep itself.
            ok=(sector[rb,None]==sector[res]) & (abs(caprank[rb,None]-caprank[res])<=.1) & (abs(momrank[rb,None]-momrank[res])<=.1)
            ok &= cov[rb,None]&cov[res]
            ident=rb[:,None]==res
            strict_gain=(val[res]-val[rb,None])>0
            can_replace=ok&~ident&strict_gain
            ranks=pct(val[res])
            cost=np.where(can_replace,-np.nan_to_num(ranks[None,:])+np.nan_to_num(pct(val[res])[np.searchsorted(res,rb),None]),1e5)
            cost[ident]=0.
            ii,jj=linear_sum_assignment(cost)
            assert np.array_equal(ii,np.arange(h))
            chosen=res[jj]
            changes=(chosen!=rb)
            counts[arm]=int(changes.sum())
            plans[arm][e,:k]=ids[np.r_[core,chosen]]
            rr=m.o[e+10,ids]/m.o[e,ids]-1
            realized=pct(rr)
            for a,b in zip(rb,chosen):
                target.append((signal,arm,m.symbols[ids[a]],m.symbols[ids[b]],val[a],val[b],a!=b,1/k,
                               realized[a],realized[b],int(s.valid_buy[e,ids[a]]),int(s.valid_buy[e,ids[b]])))
        info.append(dict(signal_date=signal,reserve_n=k,scored_reserve=int(cov[res].sum()),buy_n=h,scored_buy=int(cov[rb].sum()),
                         two_fund_estimated_5d_flow=cap_proxy,latest_share_date=dates[dateidx-1],index_weight_date=dd.index[last],**counts))
    fc=pd.DataFrame(info);fc.to_csv(SUB/'support.csv',index=False)
    pc=pd.DataFrame(target,columns='signal_date arm original chosen score_old score_new changed weight realized_rank_old realized_rank_new buyable_old buyable_new'.split())
    pc.to_parquet(SUB/'marginal_decisions.parquet',index=False)
    paths=[];orders=[];months=[]
    for a,p in plans.items():
        d,o,gap=s.replay(p,PERIODS['later'],keep_orders=True)
        assert gap is None
        paths.append(d.reset_index().assign(arm=a));orders.append(o.assign(arm=a))
        for month,v in monthly(d,dates).items():
            if month!='2025-03':
                months.append((a,month,v))
    mo=pd.DataFrame(months,columns='arm month net'.split()).pivot(index='month',columns='arm',values='net')
    mo.to_csv(SUB/'monthly_net.csv')
    print((mo.sub(mo.ridge,axis=0)*1e4).mean().to_string(),fc.select_dtypes('number').drop(columns='two_fund_estimated_5d_flow').sum().to_string(),flush=True)
    pd.concat(paths).to_parquet(SUB/'daily.parquet',index=False)
    pd.concat(orders).to_parquet(SUB/'orders.parquet',index=False)
    ref=pd.read_parquet(REG/'p2/results/funded_daily.parquet').query('scope=="later" and arm=="rank" and mul==1').set_index('date')
    d=paths[0].set_index('date')
    np.testing.assert_allclose(ref.loc[d.index,['nav','cash','fee']],d[['nav','cash','fee']],atol=1e-10,rtol=0)
    files=[Path(__file__),HERE6/'fetch_segment.py',REG/'u2/common.py',REG/'u2/book.cpp',REG/'p2/results/scores.parquet',OUT/'fund_share.parquet',OUT/'fund_nav.parquet']
    (SUB/'verification.json').write_text(json.dumps({str(f):sha(f) for f in files+sorted(p for p in SUB.iterdir() if p.name!='verification.json')},indent=2)+'\n')
if __name__=='__main__':main()
