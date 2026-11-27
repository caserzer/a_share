"""E1 on CSI800: funded Ridge and frozen-tree swaps, same estimator as 300."""
import importlib.util
import hashlib
from pathlib import Path
import sys
HERE1=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE1.parent/'u2'))
from common import *
spec=importlib.util.spec_from_file_location('p2_account',REG/'p2/book.py')
book=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=book
spec.loader.exec_module(book)
OUT=HERE1/'results'
OUT.mkdir(exist_ok=True)

def calibrate(s):
    z=s.ranks.copy()
    i=z.entry_idx.to_numpy()
    j=s.symbols.get_indexer(z.instrument)
    z['ret']=s.m.o[i+10,j]/s.m.o[i,j]-1
    z=z[np.isfinite(z.ret)].copy()
    yc=z.ret-z.groupby('entry_idx').ret.transform('mean')
    fit={}
    for arm,col in [('ridge','refit_R'),('tree','refit_T')]:
        xc=z[col]-z.groupby('entry_idx')[col].transform('mean')
        num=(xc*yc).groupby(z.entry_idx).sum().rolling(252,min_periods=1).sum()
        den=(xc**2).groupby(z.entry_idx).sum().rolling(252,min_periods=1).sum()
        fit[arm]=num/den.where(den>0)
    result=pd.DataFrame(fit)
    result['latest_mature_exit']=result.index+10
    result.index+=11
    assert (result.latest_mature_exit<=result.index-1).all()
    result.rename_axis('first_usable_entry_idx').to_csv(OUT/'calibration.csv')
    return result

def estimate_fee(x):
    return .001*max(x,0)+.002*max(-x,0)

def main():
    s=Study();m=s.m;m.members=s.members
    fit=calibrate(s)
    scores={};plans={};pairs=[];days=[];orders=[];records=[];miss=[]
    for e,g in s.ranks.groupby('entry_idx'):
        ids=m.symbols.get_indexer(g.instrument)
        k=s.ks[e];n=k//5;top=ids[:k];res=ids[k:2*k]
        t=ids[np.lexsort((-ids,-g.refit_T.to_numpy()))]
        rem=t[np.isin(t,top)][-n:];add=t[np.isin(t,res)][:n]
        for arm,plan,col in [('ridge',top,'refit_R'),('tree',np.r_[top[~np.isin(top,rem)],add],'refit_T')]:
            plans[e,arm]=plan
            sc=np.full(m.n,np.nan);sc[ids]=g[col]
            scores[e,arm]=sc
    for seg,period in PERIODS.items():
        lo,stop,end=m.days.get_indexer(period)
        for arm in ['ridge','tree']:
            for label,gate,control in [('base',None,False),('cost',0,False),('same_count',0,True),
                                       ('cost_plus10',.001,False),('same_count_plus10',.001,True)]:
                state=book.State.empty(m.n)
                for i in range(lo,stop+1):
                    plan=plans[i,arm].copy() if i+10<=end else None
                    phase=(i-lo)%10
                    if plan is not None and gate is not None:
                        sc=scores[i,arm];at=state.units[phase]>0
                        eligible=at & np.isfinite(sc) & m.members[i-1]
                        old=np.flatnonzero(eligible & ~np.isin(np.arange(m.n),plan))
                        new=plan[~at[plan]]
                        old=sorted(old,key=lambda j:(sc[j],m.symbols[j]))
                        new=sorted(new,key=lambda j:(sc[j],m.symbols[j]),reverse=True)
                        matched=list(zip(old,new))
                        mark=np.nan_to_num(m.marks['flat'][1][i-1])
                        ticket=(state.cash[phase]+state.units[phase]@mark)/len(plan)
                        other=(state.units>0)&(state.due<=i)&m.sell[i-1]
                        other[phase]=False
                        crossed_sells=(state.units*other).sum(axis=0)*mark
                        slope=fit.at[i,arm] if i in fit.index else np.nan
                        n=0
                        paired_n=counts.get(i,0) if control else None
                        if control:
                            matched.sort(key=lambda ij:hashlib.sha256(f'4101|{m.days[i-1]}|{m.symbols[ij[0]]}{m.symbols[ij[1]]}'.encode()).digest())
                        for k,(a,b) in enumerate(matched):
                            oldval=state.units[phase,a]*mark[a]
                            oa=-crossed_sells[a];ob=-crossed_sells[b]
                            fee=estimate_fee(oa-oldval)+estimate_fee(ob+ticket)-estimate_fee(oa+ticket-oldval)-estimate_fee(ob)
                            gain=ticket*slope*(sc[b]-sc[a])
                            accept=(k<paired_n) if control else (not np.isfinite(slope) or gain>=fee+ticket*gate)
                            n+=int(accept)
                            if not accept:plan[plan==b]=a
                            pairs.append((seg,arm,label,m.days[i-1],m.symbols[a],m.symbols[b],ticket,slope,gain,fee,accept))
                        records.append((seg,arm,label,i,len(matched),n,ticket,n*ticket,paired_n))
                        if not control:counts[i]=n
                    try:row,info=book.step(m,s.actions,state,lo,end,i,plan,1,detail=True)
                    except ValueError as err:
                        if 'missing held' not in str(err):raise
                        miss.append((seg,arm,label,m.days[i],str(err)));break
                    days.append(dict(segment=seg,arm=arm,test=label,**row))
                    od,fees=info[:2]
                    val=od.sum(axis=0)
                    for j in np.flatnonzero(val):
                        orders.append((seg,arm,label,m.days[i],m.symbols[j],val[j],fees[:,j].sum()))
                    if gate is None:counts={}
                print(seg,arm,label,flush=True)
    daily=pd.DataFrame(days)
    daily.to_parquet(OUT/'daily.parquet',index=False)
    o=pd.DataFrame(orders,columns='segment arm test date instrument net_order fee'.split())
    np.testing.assert_allclose(o.groupby(['segment','arm','test','date']).fee.sum().reindex(daily.set_index(['segment','arm','test','date']).index,fill_value=0),daily.fee,atol=1e-12)
    o.to_parquet(OUT/'orders.parquet',index=False)
    pd.DataFrame(pairs,columns='segment model test signal_date old new ticket slope expected_gain estimated_incremental_fee accepted'.split()).to_parquet(OUT/'pairs.parquet',index=False)
    pd.DataFrame(records,columns='segment model test entry_idx eligible_pairs accepted ticket accepted_budget mechanical_target_n'.split()).to_parquet(OUT/'decisions.parquet',index=False)
    pd.DataFrame(miss,columns='segment model test date reason'.split()).to_csv(OUT/'gaps.csv',index=False)
    months=[]
    base=pd.read_parquet(OUT800/'strict_daily.parquet').query('size=="same300" and mode=="refit" and path=="common"')
    for (seg,model,test),g in daily.groupby(['segment','arm','test']):
        d=g.set_index('date').sort_index()
        if test=='base':
            scope='later' if seg=='later' else 'primary';idx=1 if seg=='restart' else 0;arm='R' if model=='ridge' else 'swap'
            ref=base.query('scope==@scope and segment==@idx and arm==@arm').set_index('date')
            np.testing.assert_allclose(ref.loc[d.index,['nav','fee','cash','crossed']],d[['nav','fee','cash','crossed']],atol=1e-10,rtol=0)
        d['opening_nav']=d.nav.shift().fillna(1.)
        d['fee_rate']=d.fee/d.opening_nav
        d['gross_return']=(d.nav+d.fee)/d.opening_nav-1
        for month,r in monthly(d,s.days).items():
            group=d[d.index.to_period('M')==pd.Period(month)]
            # Link gross P&L and actual fees to opening equity, not a zero-fee path.
            denom=group.opening_nav.iloc[0]
            expense=group.fee.sum()/denom
            months.append(dict(segment=seg,model=model,test=test,month=month,net=r,fee=expense,gross=r+expense))
    z=pd.DataFrame(months)
    base=z[z.test=='base'].drop(columns='test').rename(columns={k:k+'_base' for k in ['net','fee','gross']})
    z=z.merge(base,on=['segment','model','month'])
    for col in ['net','fee','gross']:z[col+'_gap_bp']=(z[col]-z[col+'_base'])*1e4
    np.testing.assert_allclose(z.net_gap_bp,z.gross_gap_bp-z.fee_gap_bp,atol=1e-10)
    z['registered_month']=~((z.segment=='later')&(z.month=='2025-03'))
    z.to_csv(OUT/'monthly.csv',index=False)
    z.groupby(['segment','model','test'])[['net_gap_bp','fee_gap_bp','gross_gap_bp']].mean().to_csv(OUT/'including_start_month.csv')
    z=z[z.registered_month]
    z.groupby(['segment','model','test'])[['net_gap_bp','fee_gap_bp','gross_gap_bp']].mean().to_csv(OUT/'summary.csv')
    files=[Path(__file__),HERE/'common.py',REG/'p2/book.py',REG/'config.yaml',OUT800/'scores.parquet']
    (OUT/'receipt.json').write_text(json.dumps({str(f):sha(f) for f in files+sorted(p for p in OUT.iterdir() if p.suffix!='.json')},indent=2)+'\n')

if __name__=='__main__':main()
