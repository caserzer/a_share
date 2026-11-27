"""Build comparable benchmarks, actual signal-cohort P&L and accounting diagnostics."""
from sessions import *
from collections import defaultdict
from engine import STORE

def benchmarks(d):
    matched=[];full=[];benchmarks={}
    x=json.loads((ep.PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    a=pd.DataFrame(x['items'],columns=x['fields'])
    idx300=a.set_index(pd.to_datetime(a.trade_date)).close.sort_index()
    a=pd.read_parquet(STORE/'index800.parquet')
    idx800=a.set_index(pd.to_datetime(a.trade_date)).close.sort_index()
    p2=pd.read_parquet(EP41/'p2/results/funded_daily.parquet',filters=[('arm','=','equal'),('mul','=',1)],columns=['date','scope','nav'])
    p2['segment']=p2.scope.map({'primary':1,'later':2})
    p1=pd.read_parquet(EP41/'p1/results/daily.parquet',filters=[('kind','=','strict'),('phase','=',-1),('model','=','refit'),('bucket','=','pool')],columns=['date','segment','nav'])
    for (pool,n,arm),g in d[d.fee_multiple.eq(1)].groupby(['pool','segment','arm']):
        eq=(p1 if pool=='800' else p2)
        eq=eq[eq.segment.eq(n)].set_index('date').nav
        idx=idx800 if pool=='800' else idx300
        g=g.set_index('date').sort_index()
        base=g.prev
        for typ,end in [('whole',g.index[-1]),('shared_equal',min(eq.index[-1],g.index[-1]))]:
            chunk=g.loc[:end]
            for y,h in [('all',chunk),*chunk.groupby(chunk.index.year)]:
                t0=h.index[0];dt=h.index[-1];entry=g.index.get_loc(t0)
                index_open=g.index[entry-1] if entry else t0
                eqvalue=np.nan
                if dt<=eq.index[-1]:
                    eqstart=eq.iloc[eq.index.get_loc(t0)-1] if t0!=eq.index[0] else 1.
                    eqvalue=eq.at[dt]/eqstart-1
                net=h.nav.iloc[-1]/base.at[t0]-1
                iv=idx.at[dt]/idx.at[index_open]-1
                drawdown=(h.nav/h.nav.cummax().clip(lower=base.at[t0])-1).min()
                matched.append((pool,n,arm,typ,str(y),t0,dt,len(h),net,iv,eqvalue,net-iv,net-eqvalue,drawdown))
    pd.DataFrame(matched,columns='pool segment arm window year start end days net index_total_return equal_net net_minus_index net_minus_equal maxdd'.split()).to_csv(OUT/'benchmarks.csv',index=False)

def contrasts():
    m=pd.read_csv(OUT/'monthly.csv')
    res=[]
    for (pool,cost),g in m.groupby(['pool','fee_multiple']):
        others=sorted(set(g.arm)-{'R','T'})
        for a,b in [('T','R')]+[(c[0],c) for c in others]:
            res.append(core.contrast(g,a,b).assign(pool=pool,fee_multiple=cost))
    pd.concat(res,ignore_index=True).to_csv(OUT/'contrasts.csv',index=False)

def signal_time(d):
    st=pd.read_parquet(EP42/'state/results/states.parquet').set_index('signal_date').Z1
    out=[];agefee=[];stocks=[];qualities=[];par=[]
    for pool in ['300','800']:
        m=core.market(pool=='800')
        raw_close=pd.read_parquet((LOCAL if pool=='800' else ep.PRIVATE)/'qfq_close.parquet').reindex(index=m.days,columns=m.symbols).to_numpy()
        raw_open=pd.read_parquet((LOCAL if pool=='800' else ep.PRIVATE)/'qfq_open.parquet').reindex(index=m.days,columns=m.symbols).to_numpy()
        op,cl=m.planes[:2];action_table=m.planes[-1]
        for n,span in enumerate(core.SEG800 if pool=='800' else core.SEG300,1):
            for arm in ['R','T']:
                f=OUT/f'trace_{pool}_{arm}_{n}.parquet' if pool=='800' else EP42/'state/results/main'/f'trace_{arm}_{n}.parquet'
                tr=pd.read_parquet(f)
                day=tr.day.to_numpy();iid=tr.stock.to_numpy();start=m.days.get_loc(span[0])
                ages=assign_ages(tr,m,start);age_overn,age_day=ages
                entered=np.where(tr.flow.to_numpy()>0,np.where(age_day>0,day-age_day+1,day),np.where(age_overn>0,day-age_overn,day))
                feeage=np.where(tr.flow.to_numpy()>0,age_day,age_overn)
                dates=m.days[day]
                bucket=np.where(feeage>10,11,feeage)
                for (y,age),amount in tr.groupby([dates.year,bucket]).fee.sum().items():agefee.append((pool,n,arm,y,age,amount))
                stats=defaultdict(lambda:np.zeros(3))
                for key,signal,v in [('overnight',day-age_overn,tr.overnight),('intraday',day-age_day+1,tr.intraday),('fee',entered,tr.fee)]:
                    ix=['overnight','intraday','fee'].index(key)
                    for e,a in v[v!=0].groupby(signal[v!=0]).sum().items():stats[int(e)][ix]+=a
                for e,amts in stats.items():
                    zz=st.get(m.days[e-1],np.nan)
                    out.append((pool,n,arm,m.days[e-1],zz,*amts))
                g=tr.assign(month=dates.to_period('M').astype(str),symbol=m.symbols[iid]).groupby(['month','symbol'])[['overnight','intraday','fee']].sum().reset_index().assign(pool=pool,segment=n,arm=arm)
                stocks.append(g)
                b=d[d.pool.eq(pool)&d.segment.eq(n)&d.arm.eq(arm)&d.fee_multiple.eq(1)].set_index('date')
                amounts=tr.groupby('day')[['overnight','intraday','fee']].sum().reindex(m.days.get_indexer(b.index),fill_value=0)
                gross_err=np.max(abs((amounts.overnight+amounts.intraday).to_numpy()-b.gross_pnl.to_numpy()))
                net_err=np.max(abs((amounts.overnight+amounts.intraday-amounts.fee).to_numpy()-(b.nav-b.prev).to_numpy()))
                assert max(gross_err,net_err)<1e-10
                par.append((pool,n,arm,len(b),len(tr),gross_err,net_err))
                act=np.zeros(len(tr),bool)
                for src,dest,early in action_table.reshape(-1,3):
                    act |= (iid==src)&(day>=early)
                for name,sel in [('opening_position_missing_provider_open',(tr.old_units>0)&~np.isfinite(raw_open[day,iid])),('closing_position_missing_provider_close',(tr.new_units>0)&~np.isfinite(raw_close[day,iid])),('action_predecessor_post_effective',act),('actual_last_session',day==day.max()),('first_session',day==day.min())]:
                    z=tr.loc[sel]
                    qualities.append((pool,n,arm,name,len(z),z.day.nunique(),z.stock.nunique(),z.overnight.sum(),z.intraday.sum(),z.fee.sum()))
    pd.DataFrame(out,columns='pool segment arm signal_date Z1 overnight intraday fee'.split()).to_parquet(OUT/'sessions_signal_cohort.parquet',index=False)
    pd.concat(stocks).to_parquet(OUT/'stock_month.parquet',index=False)
    pd.DataFrame(agefee,columns='pool segment arm year age fee'.split()).to_csv(OUT/'fee_age.csv',index=False)
    pd.DataFrame(qualities,columns='pool segment arm condition stock_sleeve_rows days stocks overnight intraday fee'.split()).to_csv(OUT/'quality.csv',index=False)
    pd.DataFrame(par,columns='pool segment arm days stock_sleeve_rows max_gross_error max_net_error'.split()).to_csv(OUT/'session_parity.csv',index=False)

def main():
    d=pd.read_parquet(OUT/'daily.parquet')
    benchmarks(d)
    contrasts()
    signal_time(d)
if __name__=='__main__':main()
