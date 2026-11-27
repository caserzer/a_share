from book43 import *
from fifo43 import allocate
from collections import deque,defaultdict
from types import SimpleNamespace
def trace_analysis(m,binary,frame,span,out,packed):
    t=read_trace(binary);t=t[t.day<=m.days.get_loc(frame.index[-1])].copy()
    daily=t.groupby('day')[['overnight','intraday','fee']].sum().reindex(m.days.get_indexer(frame.index),fill_value=0)
    err=max(abs(daily.overnight.values+daily.intraday.values-frame.gross_pnl).max(),abs(daily.fee.values-frame.fee).max())
    assert err<1e-9
    c=t[(t.old_units!=t.new_units)|(t.target>0)|(t.fee!=0)].copy()
    c.to_parquet(out/'transactions.parquet',index=False)
    daily.assign(date=frame.index).to_parquet(out/'session.parquet')
    del t
    life=allocate(c,m,span)
    assert abs(life.buy_fee.sum()+life.sell_fee.sum()-frame.fee.sum())<1e-9
    life.to_parquet(out/'fifo.parquet',index=False)
    one=life[(life.age==10)&~life.still_open]
    return dict(session_error=err,intraday=daily.intraday.sum(),overnight=daily.overnight.sum(),totalfee=frame.fee.sum(),fifo_fee_error=life.buy_fee.sum()+life.sell_fee.sum()-frame.fee.sum(),one_fee=one.buy_fee.sum()+one.sell_fee.sum(),one_fee_ex_settle=(one.buy_fee+one.sell_fee)[~one.settlement].sum(),one_cap=one.principal.sum(),one_n=len(one),open_fee=life.loc[life.still_open,'buy_fee'].sum(),gross=frame.gross_pnl.sum(),cash=(frame.cash/frame.nav).mean(),mean_hhi=frame.hhi.mean(),maximum_weight=frame.max_weight.max())
def account(m,p,pool,family,arm,mode=0,cap=.05,tau=.01,trace=False):
    dest=O/'accounts'/str(pool)/family/arm;dest.mkdir(parents=True,exist_ok=True)
    nseg=3 if pool==800 else 2
    if (dest/'done').exists() and all((dest/str(n)/'transactions.parquet').exists() for n in range(1,nseg+1)):return
    months=[];days=[];details=[]
    for seg,span in enumerate(SEG800 if pool==800 else SEG300,1):
        for fee in [1,2]:
            where=dest/str(seg);where.mkdir(exist_ok=True)
            with tempfile.NamedTemporaryFile() as tmp:
                traced=fee==1
                frame=mode_run(m,p,span,mode,cap,tau,fee,tmp.name if traced else None)
                meta=trace_analysis(m,tmp.name,frame,span,where,p) if traced else {}
            details.append(dict(segment=seg,fee=fee,first=frame.index.min(),last=frame.index.max(),days=len(frame),**meta))
            months.append(monthly(frame,m.days).reset_index().assign(segment=seg,multiple=fee))
            days.append(frame.reset_index().assign(segment=seg,multiple=fee))
    pd.concat(months).to_csv(dest/'monthly.csv',index=False);pd.concat(days).to_parquet(dest/'daily.parquet',index=False)
    pd.DataFrame(details).to_csv(dest/'detail.csv',index=False);(dest/'done').touch()
    print(pool,family,arm,flush=True)
def runw(pool):
    wide=pool==800;m=book(wide);f=frozen(wide)
    p=pack(m,f,f.refit_R if wide else f.R)
    for arm,md,cap,tau in [('R',0,.05,0),('buf',1,.05,0),('LP',3,.05,.01),('QP',4,.05,.01),('mechanical',5,.05,.01),('capK',3,-1,0),('cap5',3,.05,0),('cap6',3,.06,0),('tau005',3,.05,.005),('tau02',3,.05,.02),('LP6',3,.06,.01)]:
        account(m,p,pool,'W',arm,md,cap,tau,arm in ('R','buf','LP','QP','mechanical','cap5','capK'))
    if not wide:account(m,p,pool,'W','K40',2)
    else:
        k=frozen(False).groupby('entry_idx').size()//10
        p=pack(m,f,f.refit_R,k)
        for a,md in [('head',0),('buf_head',1),('LP_head',3)]:account(m,p,pool,'W',a,md)
if __name__=='__main__':runw(int(sys.argv[1]))
