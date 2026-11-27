from accounts43 import *
from scipy.optimize import linprog
def wtest(pool):
    wide=pool==800;m=book(wide);f=frozen(wide);p=pack(m,f,f.refit_R if wide else f.R)
    m.lib.fork_config.argtypes=[ct.c_int]*4;m.lib.fork_nav.restype=ct.c_double;m.lib.fork_start.restype=ct.c_double;m.lib.fork_l1.restype=ct.c_double
    ans=[];buckets=[];checks=[]
    for seg,span in enumerate(SEG800 if wide else SEG300,1):
        lo,end,stop=m.days.get_indexer(pd.to_datetime(span))
        m.lib.fork_config(1,lo,-1,3)
        d=mode_run(m,p,span,3)
        for i in range(lo,min(m.days.get_loc(d.index[-1]),end)-9):
            vals=[];turn=[]
            for md in [3,5]:
                m.lib.fork_config(0,lo,i,md)
                sub=mode_run(m,p,(i,end,i+10),3)
                turn.append(m.lib.fork_l1())
                vals.append(m.lib.fork_nav() if len(sub)==11 else np.nan)
            initial=m.lib.fork_start();ans.append((pool,seg,m.days[i],initial,*vals,vals[1]-vals[0],(vals[1]-vals[0])/initial,*turn,turn[1]-turn[0]))
        m.lib.fork_config(0,-1,-1,3)
        for arm in ['R','buf','LP','QP','cap5','mechanical']:
            t=pd.read_parquet(O/f'accounts/{pool}/W/{arm}/{seg}/transactions.parquet')
            op=m.planes[0];cl=m.planes[1];sell=m.planes[3]
            held=np.zeros((10,m.n))
            for day,dd in t.groupby('day'):
                phase=(day-lo)%10
                sub=dd[dd.phase==phase].copy()
                absent=np.flatnonzero(held[phase]>0)
                absent=absent[~np.isin(absent,sub.stock)]
                if len(absent):
                    missing=pd.DataFrame(dict(phase=phase,stock=absent,old_units=held[phase,absent],new_units=held[phase,absent],fee=0.))
                    sub=pd.concat([sub,missing],ignore_index=True)
                held[dd.phase,dd.stock]=dd.new_units
                if day+10>end or p[1][day]==0:continue
                ids=p[0][day];order={j:k for k,j in enumerate(ids) if j>=0}
                if sub.empty:continue
                old=sub.old_units.to_numpy();new=sub.new_units.to_numpy();stock=sub.stock.to_numpy()
                for bucket,low,hi in [('1-10',1,10),('11-24',11,24),('25-40',25,40),('41+',41,10000),('out',10001,10001)]:
                    rank=np.array([order.get(j,10000)+1 for j in stock]);ok=(rank>=low)&(rank<=hi)&(old>0)
                    if ok.any():
                        bucks=old[ok]*cl[day-1,stock[ok]]
                        buckets.append((pool,seg,arm,day,bucket,ok.sum(),(new[ok]==0).sum(),((new[ok]>0)&(new[ok]<old[ok]-1e-14)).sum(),((new[ok]>0)&(new[ok]>=old[ok]-1e-14)).sum(),bucks.sum(),sub.fee.to_numpy()[ok].sum()))
    pd.DataFrame(ans,columns='pool segment date start_sleeve LP_open_H10 mechanical_open_H10 paired_wealth paired_return lp_L1 mechanical_L1 delta_L1'.split()).to_csv(O/f'W4_same_start_{pool}.csv',index=False)
    pd.DataFrame(buckets,columns='pool segment arm day rank_bucket old_names full_sales partial_sales retained old_value fees'.split()).to_parquet(O/f'W5_ranks_{pool}.parquet',index=False)
if __name__=='__main__':wtest(int(sys.argv[1]))
