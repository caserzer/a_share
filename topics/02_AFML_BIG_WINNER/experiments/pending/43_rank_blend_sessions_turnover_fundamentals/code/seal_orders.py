from accounts43 import *
import accounts43,bl,fund_fit
GOAL=np.dtype([('day','i4'),('phase','i4'),('stock','i4'),('target_weight','f8')])
def emit(m,p,pool,family,arm,mode=0,cap=.05,tau=.01,trace=False):
    dest=O/f'accounts/{pool}/{family}/{arm}'
    for seg,span in enumerate(SEG800 if pool==800 else SEG300,1):
        where=dest/str(seg)
        if not (dest/'done').exists():raise ValueError('account pending '+str(dest))
        if (where/'cash_2fee.parquet').exists():continue
        for fee in [1,2]:
            with tempfile.NamedTemporaryFile() as tar,tempfile.NamedTemporaryFile() as executions:
                m.lib.goal_log(tar.name.encode())
                d=mode_run(m,p,span,mode,cap,tau,fee,executions.name if fee==2 else None)
                m.lib.goal_log(b'')
                goals=pd.DataFrame(np.fromfile(tar.name,dtype=GOAL));last=m.days.get_loc(d.index[-1]);goals=goals[goals.day<=last]
                goals.to_parquet(where/('targets'+('' if fee==1 else '_2fee')+'.parquet'),index=False)
                if fee==2:
                    z=read_trace(executions.name);z=z[(z.day<=last)&((z.new_units!=z.old_units)|(z.fee>0)|(z.target>0))]
                    cf=np.zeros((len(d),10));np.add.at(cf,(z.day.to_numpy()-m.days.get_loc(d.index[0]),z.phase),z.flow+z.fee);cash=.1-cf.cumsum(axis=0)
                    assert np.max(abs(cash.sum(axis=1)-d.cash))<1e-9
                    z.to_parquet(where/'transactions_2fee.parquet',index=False);pd.DataFrame(cash,index=d.index,columns=['sleeve'+str(n) for n in range(10)]).to_parquet(where/'cash_2fee.parquet')
                prev=pd.read_parquet(dest/'daily.parquet',filters=[('segment','=',seg),('multiple','=',fee)]).set_index('date')
                assert d.index.equals(prev.index) and np.max(abs(d.nav-prev.nav))<1e-9,(pool,family,arm,fee)
    print(pool,family,arm,flush=True)
def run(pool,family):
    accounts43.account=emit;bl.account=emit;fund_fit.account=emit
    if family=='W':accounts43.runw(pool)
    elif family in ('B','L'):
        bl.fitgrid=lambda m,f,scores,grid,name,pool:pd.read_csv(O/f'cal_{name}_{pool}.csv').drop_duplicates('quarter').set_index('quarter').chosen
        bl.run(pool,family)
        m=book(pool==800)
        if family=='L':
            f=pd.read_parquet(O/f'diagnostics_{pool}/daily_labels_and_tree.parquet');emit(m,pack(m,f,f.tree_total),pool,'L','tree_total')
        elif pool==800:
            kk=frozen(False).groupby('entry_idx').size()//10
            f=pd.concat(pd.read_parquet(p,columns=KEY+['T','T_mask_trading']) for p in (E/'scale/a4/results/scores_800').glob('*.parquet'))
            for a in ['T','T_mask_trading']:emit(m,pack(m,f,f[a],kk),pool,'B_A4_head',a)
    else:
        fund_fit.accounts();m=book(True);r=frozen(True);emit(m,pack(m,r,r.refit_R),800,'Fstrict','neutral')
        s=pd.read_parquet(O/'fundamental/strict/raw_scores.parquet')
        for a in ['raw']+fund_fit.A:emit(m,pack(m,s,s[a]),800,'Fstrict_raw',a)
if __name__=='__main__':run(int(sys.argv[1]),sys.argv[2])
