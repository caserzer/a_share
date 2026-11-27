"""Replay both orderings on the identical original EP41 N6 reserve opportunities."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
REG=next(HERE.parents[1].glob('41_*'))
sys.path.insert(0,str(REG/'u2'))
from common import Study, PERIODS, np, pd, pct, monthly
def main():
    s=Study();s.style();m=s.m;dates=m.days
    old=REG/'sources/n6/results/segment'
    dest=HERE/'results/etf_original_reserve';dest.mkdir(exist_ok=True)
    checks=[];paths=[];orders=[];mo=[]
    source=pd.read_parquet(REG/'p2/results/scores.parquet');lo,hi=dates.get_indexer(['2025-03-03','2026-10-12'])
    source=source[source.entry_idx.between(lo,hi-10)]
    d=pd.concat([pd.read_parquet(HERE/'results'/('basket_'+c+'_later.parquet')) for c in ['510300','159919']])
    d['instrument']=d.con_code.str[-2:]+d.con_code.str[:6];d['j']=m.symbols.get_indexer(d.instrument)
    byday={pd.Timestamp(k):g for k,g in d.groupby('trade_date')}
    flow={}
    for c in ['510300','159919']:
        v=pd.read_parquet(HERE/'results'/('shares_'+c+'.parquet')).drop_duplicates('trade_date')
        flow[c]=v.set_index(pd.to_datetime(v.trade_date)).fd_share.reindex(dates).diff(5)*10000
    iw=pd.read_parquet(old/'index_weight.parquet');iw['instrument']=iw.con_code.str[-2:]+iw.con_code.str[:6]
    weights=iw.pivot(index='trade_date',columns='instrument',values='weight').fillna(0);weights.index=pd.to_datetime(weights.index)
    delta=weights.diff().reindex(columns=m.symbols,fill_value=0)
    plans={a:s.blank(31) for a in ['ridge','flow','reverse','weight']}
    for e,g in source.groupby('entry_idx'):
        i=e-1;dt=dates[i];g=g.sort_values(['R','instrument'],ascending=False)
        ids=m.symbols.get_indexer(g.instrument);k=len(g)//10;h=k//5;top=np.arange(k);res=np.arange(k,2*k);rb=res[:h]
        tr=np.lexsort((-ids,-g['T'].to_numpy()));core=top[~np.isin(top,tr[np.isin(tr,top)][-h:])]
        z=byday[dt];z=z[z.sub_flag.eq('允许')&z.qty.gt(0)&z.j.ge(0)].copy()
        z['val']=z.qty*s.raw.iloc[i-1].to_numpy()[z.j]*z.ts_code.str[:6].map({c:flow[c].iloc[i-1] for c in flow})/900000
        val=z.groupby('instrument').val.sum(min_count=1).reindex(g.instrument).to_numpy()/s.adv.iloc[i,ids].to_numpy()
        ref=delta.iloc[delta.index.searchsorted(dt,side='left')-1].to_numpy()[ids]
        cap=pct(s.cap[i,ids]);mom=pct(m.c[i,ids]/m.c[i-20,ids]-1);sec=s.sectors[i,ids]
        cov=np.isfinite(cap)&np.isfinite(mom)&np.isfinite(ref)&np.isfinite(val)&(sec>=0)
        altered={a:rb.copy() for a in plans}
        candidates=np.setdiff1d(res,rb)
        for j,b in enumerate(rb):
            if not cov[b]:continue
            members=candidates[cov[candidates]&(abs(cap[candidates]-cap[b])<=.1)&(abs(mom[candidates]-mom[b])<=.1)&(sec[candidates]==sec[b])]
            hi_n=members[(val[members]>val[b])&~np.isin(members,altered['flow'])]
            low_n=members[(val[members]<val[b])&~np.isin(members,altered['reverse'])]
            peers=members[~np.isin(members,altered['weight'])]
            if not len(hi_n) or not len(low_n) or not len(peers):continue
            altered['flow'][j]=hi_n[np.argmax(val[hi_n])];altered['reverse'][j]=low_n[np.argmin(val[low_n])]
            altered['weight'][j]=peers[np.argmax(ref[peers])]
        checks.append((e,h,int(sum(altered['flow']!=rb)),int(cov[rb].sum())))
        for arm,v in altered.items():plans[arm][e,:k]=ids[np.r_[core,v]]
    for arm,plan in plans.items():
        d,o,gap=s.replay(plan,PERIODS['later'],keep_orders=True);assert gap is None
        paths.append(d.reset_index().assign(arm=arm));orders.append(o.assign(arm=arm))
        for t,v in monthly(d,dates).items():
            if t!='2025-03':mo.append((t,arm,v))
        if arm=='ridge':
            ref=pd.read_parquet(REG/'p2/results/funded_daily.parquet').query('scope=="later" and arm=="rank" and mul==1').set_index('date')
            np.testing.assert_allclose(d[['nav','cash','fee']],ref.loc[d.index,['nav','cash','fee']],rtol=0,atol=1e-10)
    pd.concat(paths).to_parquet(dest/'daily.parquet',index=False)
    pd.concat(orders).to_parquet(dest/'orders.parquet',index=False)
    pd.DataFrame(checks,columns=['entry_idx','buy_budget','changed','covered']).to_csv(dest/'opportunities.csv',index=False)
    mc=pd.DataFrame(mo,columns=['month','arm','net']).pivot(index='month',columns='arm',values='net');mc.to_csv(dest/'months.csv')
    (mc.sub(mc.ridge,axis=0)*1e4).mean().rename('bp_month').to_csv(dest/'mean.csv')
    print((mc.sub(mc.ridge,axis=0)*1e4).mean(),sum(v[2] for v in checks),flush=True)
if __name__=='__main__':main()
