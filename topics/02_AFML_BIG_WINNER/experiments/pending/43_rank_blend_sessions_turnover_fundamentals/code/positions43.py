"""Reconstruct all 10 sleeve cash lines and daily stock exposures from sparse verified changes."""
from accounts43 import *
from fund_panel import F
def run(pool):
    m=book(pool==800);panel=pd.read_parquet(F/'panel.parquet',columns=['signal_date','instrument','capital','industry'])
    caps=panel.pivot(index='signal_date',columns='instrument',values='capital').reindex(index=m.days,columns=m.symbols).to_numpy()
    sector=panel.pivot(index='signal_date',columns='instrument',values='industry').reindex(index=m.days,columns=m.symbols)
    names=sorted(panel.industry.dropna().unique());ind=np.stack([pd.Categorical(sector[col],categories=names).codes for col in sector],axis=1)
    syms=m.symbols.to_series().reset_index(drop=True);syms.to_csv(O/f'symbols_{pool}.csv',index_label='stock')
    rf=[];mixed=[]
    for marker in sorted((O/f'accounts/{pool}').glob('*/*/done')):
        dest=marker.parent;arm=dest.parent.name+'/'+dest.name
        if not (dest/'1/transactions.parquet').exists():continue
        daily=pd.read_parquet(dest/'daily.parquet',filters=[('multiple','=',1)])
        for seg,span in enumerate(SEG800 if pool==800 else SEG300,1):
            td=dest/str(seg);f=td/'transactions.parquet'
            if not f.exists():continue
            x=pd.read_parquet(f);d=daily[daily.segment.eq(seg)].set_index('date')
            q=m.days.get_indexer(d.index);nd=len(q);j=x.day.to_numpy()-q[0];k=x.stock.to_numpy()
            cf=np.zeros((nd,10));np.add.at(cf,(j,x.phase),x.flow+x.fee);cash=.1-cf.cumsum(axis=0)
            ddc=pd.DataFrame(cash,index=d.index,columns=['sleeve'+str(j) for j in range(10)])
            ddc.to_parquet(td/'cash.parquet')
            pos=np.zeros((nd,m.n));np.add.at(pos,(j,k),x.new_units-x.old_units);pos=pos.cumsum(axis=0)
            mark=m.planes[1][q].copy()
            if d.index[-1]==pd.Timestamp(span[1]):mark[-1]=m.planes[0][q[-1]]
            value=pos*np.nan_to_num(mark);nav=cash.sum(axis=1)+value.sum(axis=1)
            err=max(np.max(abs(nav-d.nav)),np.max(abs(cash.sum(axis=1)-d.cash)))
            assert err<1e-9,(pool,arm,seg,err)
            w=value/d.nav.to_numpy()[:,None];wc=w*(caps[q-1]>0);cover=wc.sum(axis=1)
            wsize=np.divide((wc*np.log(np.where(caps[q-1]>0,caps[q-1],1))).sum(axis=1),cover,out=np.zeros(nd),where=cover>0)
            metrics=pd.DataFrame(dict(date=d.index,invest=w.sum(axis=1),cap_coverage=cover,weighted_log_cap=wsize,top10=-np.sort(-w,axis=1)[:,:10].sum(axis=1),effective_names=1/np.maximum(d.hhi.values,1e-20)))
            metrics['effective_names']=metrics.effective_names.where(d.hhi.values>1e-12)
            for ci,c in enumerate(names):metrics['sector_'+c]=(w*(ind[q-1]==ci)).sum(axis=1)
            metrics.to_parquet(td/'exposures.parquet',index=False)
            rf.append((pool,arm,seg,nd,err,metrics.invest.mean(),cover.mean(),metrics.weighted_log_cap.mean(),metrics.top10.mean(),metrics.effective_names.mean()))
    pd.DataFrame(rf,columns='pool arm segment days reconciliation_error invested cap_coverage log_cap top10 effective_names'.split()).to_csv(O/f'portfolio_{pool}.csv',index=False)
if __name__=='__main__':run(int(sys.argv[1]))
