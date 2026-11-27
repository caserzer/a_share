"""Reconcile historical E1 books and trace their actual shares, costs and decision pairs."""
from pathlib import Path
from collections import defaultdict,deque
import hashlib, sys, tempfile, json, importlib.util
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent; OLD=next(HERE.parents[2].glob('41_*'))
WIDE=sys.argv[1]=='800'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    out=importlib.util.module_from_spec(spec);sys.modules[name]=out;spec.loader.exec_module(out)
    return out

def data():
    if WIDE:
        x=module('e1wide',OLD/'e1_800/run.py');s=x.Study();m=s.m;m.members=s.members
        groups=s.ranks; ks=s.ks;actions=s.actions;book=x.book
        src=OLD/'e1_800/results';p=pd.read_parquet(src/'pairs.parquet').rename(columns={'estimated_incremental_fee':'estimated_fee'})
        p['idx']=m.days.get_indexer(p.signal_date)+1
        days=pd.read_parquet(src/'daily.parquet').rename(columns={'arm':'model'})
        p['model']=p.model.replace({'ridge':'hold'});days['model']=days.model.replace({'ridge':'hold'})
        groups=groups.rename(columns={'refit_R':'R','refit_T':'T'})
        periods=x.PERIODS
        private=x.LOCAL
    else:
        sys.path.insert(0,str(OLD/'p2'))
        import inputs as x
        import book
        with tempfile.TemporaryDirectory() as tmp:
            x.ledger.accounts.OUT=Path(tmp);m,actions=x.ledger.setup('flat')
        groups=pd.read_parquet(OLD/'p2/results/scores.parquet');ks=groups.groupby('entry_idx').size()//10
        periods={n:(a,b,b) for n,a,b in x.SEGMENTS}
        private=x.PRIVATE
        src=OLD/'e1_e2/300/results';p=pd.read_parquet(src/'pairs.parquet').rename(columns={'entry_idx':'idx','planned_ticket':'ticket','scope':'segment'})
        days=pd.read_parquet(src/'daily.parquet').rename(columns={'scope':'segment'})
        def trans(g):
            orig=g.arm.str.split('_')
            g['model']=orig.str[1]
            g['test']=np.select([g.arm.str.startswith('baseline'),g.arm.str.endswith('_0'),g.arm.str.endswith('_10'),g.arm.str.endswith('_0_mechanical')],['base','cost','cost_plus10','same_count'],default='same_count_plus10')
            return g[g.arm.str.startswith(('E1_','baseline_'))].copy()
        p=trans(p);days=trans(days)
    return m,actions,book,groups,ks,periods,p,days,private

def cohort(p):
    date=p[0];name=p[1]+p[2]
    return hashlib.sha256(f'4101|{date}|{name}'.encode()).digest()

def main():
    m,actions,book,groups,ks,periods,pairs,known,private=data()
    qclose=pd.read_parquet(private/'qfq_close.parquet').reindex(index=m.days,columns=m.symbols)
    ret=qclose.pct_change(fill_method=None).to_numpy();cur=qclose.to_numpy()
    totalpath=next(OLD.parent.glob('36_*/private/net_excess_20261116/H00300.CSI.json'))
    if WIDE:
        ix=pd.read_parquet(next(OLD.parent.rglob('index800.parquet')))
    else:
        packet=json.loads(totalpath.read_text())['data'];ix=pd.DataFrame(packet['items'],columns=packet['fields'])
    index_return=pd.Series(ix.close.to_numpy(float),index=pd.to_datetime(ix.trade_date)).sort_index().reindex(m.days).pct_change(10,fill_method=None).to_numpy()
    opp=[];lots=[];receipts=[];budget=[];errors=[]
    bases={'hold':{},'tree':{}};sc={a:{} for a in bases}; disp=[];symbols=m.symbols.to_numpy()
    for e,g in groups.groupby('entry_idx'):
        g=g.sort_values(['R','instrument'],ascending=False); ids=m.symbols.get_indexer(g.instrument); k=int(ks[e]); n=k//5
        tr=ids[np.lexsort((-ids,-g['T'].to_numpy()))]; core=ids[:k];pool=ids[k:k*2];rem=tr[np.isin(tr,core)][-n:];adds=tr[np.isin(tr,pool)][:n]
        bases['hold'][e]=core; bases['tree'][e]=np.r_[core[~np.isin(core,rem)],adds]
        for arm,col in [('hold','R'),('tree','T')]:
            values=np.full(m.n,np.nan);values[ids]=g[col];sc[arm][e]=values
        disp.append((e,np.nanstd(ret[e-1,ids],ddof=1)))
    ds=pd.Series(dict(disp)).sort_index();prev=ds.dropna().rolling(252,min_periods=252)
    bounds=pd.DataFrame({'disp':ds,'lo':prev.quantile(1/3).shift(),'hi':prev.quantile(2/3).shift()})
    bounds['disp_group']=np.select([bounds.lo.isna()|bounds.disp.isna(),bounds.disp<=bounds.lo,bounds.disp<=bounds.hi],['short_history','low','mid'],default='high')
    bounds.to_csv(HERE/f'dispersion_{sys.argv[1]}.csv')
    for seg,(a,b,c) in periods.items():
      lo,stop,hi=m.days.get_indexer([a,b,c])
      for model,base in bases.items():
       for name in ['base','cost','same_count','cost_plus10','same_count_plus10']:
        actual=known.query('segment==@seg and model==@model and test==@name').set_index('idx')
        raw=pairs.query('segment==@seg and model==@model and test==@name')
        ps={e:list(g.itertuples(index=False)) for e,g in raw.groupby('idx')};native={}
        for e,group in ps.items():
            plan=base[e].copy()
            for r in group:
                if not r.accepted:
                    jo,jn=m.symbols.get_indexer([r.old,r.new]);plan[plan==jn]=jo
            native[e]=plan
        full={e:native.get(e,v) for e,v in base.items()}
        state=book.State.empty(m.n);fifo=defaultdict(deque);totalfee=0.; alloc=0.
        for i in actual.index:
            ph=(i-lo)%10;price=np.nan_to_num(m.marks['flat'][0][i]);target=full[i] if i+10<=hi else None
            initial=state.units.copy();due_before=state.due.copy()
            gr=ps.get(i,[]); direct=name=='cost' or name=='cost_plus10'
            if gr and direct:
                baseline=base[i];vals=sc[model][i];atu=initial[ph]>0
                old=np.flatnonzero(atu&np.isfinite(vals)&m.members[i-1]&~np.isin(np.arange(m.n),baseline))
                new=baseline[~atu[baseline]]
                opct={j:v for j,v in zip(old,pd.Series(vals[old]).rank(pct=True))};npct={j:v for j,v in zip(new,pd.Series(vals[new]).rank(pct=True))}
                _,hyp=book.step(m,actions,state.copy(),lo,hi,i,baseline,1,True)
            if direct and ph==0 and target is not None and i+10<=stop:
                mech=base[i].copy();n=sum(int(r.accepted) for r in gr)
                for r in sorted(gr,key=lambda v:cohort((m.days[i-1],v.old,v.new)))[n:]:
                    jo,jn=m.symbols.get_indexer([r.old,r.new]);mech[mech==jn]=jo
                ticket=(state.cash[ph]+state.units[ph]@price)*(1-.002)/1.001/len(mech)
                for rule,pl in [('real',target),('mechanical',mech)]:
                    st=state.copy();begin=st.cash[ph]+st.units[ph]@price;fee=0.;filled=0.
                    try:
                        for t in range(i,i+11):
                            if t==i+10 and t!=hi:break
                            ctl=pl if t==i else (full[t] if t+10<=hi else None)
                            _,info=book.step(m,actions,st,lo,hi,t,ctl,1,True,ticket if t==i else None)
                            fee+=info[1][ph].sum()
                            if t==i:filled=info[2].sum()
                        end=st.cash[ph]+st.units[ph]@np.nan_to_num(m.marks['flat'][0][i+10])
                        net=end/begin-1
                        budget.append((seg,model,name,i,rule,n,ticket,n*ticket,filled,net+fee/begin,fee/begin,net))
                    except ValueError as err:errors.append((seg,model,name,i,rule,str(err)))
            row,info=book.step(m,actions,state,lo,hi,i,target,1,True);signed,paid,buy,_,_=info
            err=max(abs(row[f]-actual.at[i,f]) for f in ['nav','cash','fee','crossed','buy','sell']);assert err<1e-10,(seg,model,name,i,err)
            before=initial.copy()
            for src,dst,listing in actions:
                if i<listing:continue
                for sleeve in np.flatnonzero((initial[:,src]>0)&(state.units[:,src]==0)):
                    ratio=price[src]/price[dst]
                    if (sleeve,src) in fifo:
                        to=fifo[(sleeve,dst)]
                        for born,qty,px,fr in fifo.pop((sleeve,src)):
                            to.append((born,qty*ratio,px/ratio,fr/ratio))
                        fifo[(sleeve,dst)]=deque(sorted(to,key=lambda z:z[0]))
                    before[sleeve,dst]+=initial[sleeve,src]*ratio;before[sleeve,src]=0.
            if gr and direct:
                for r in gr:
                    jo,jn=m.symbols.get_indexer([r.old,r.new]);p0=m.o[i,[jo,jn]];p1=m.o[i+10,[jo,jn]]
                    valid=np.isfinite(p0).all() and np.isfinite(p1).all() and (p0>0).all() and i+10<=stop
                    realized=(p1[1]/p0[1]-p1[0]/p0[0])*r.ticket if valid else np.nan
                    old_rel=cur[i-1,jo]/cur[i-11,jo]-1-index_return[i-1]
                    exec_cap=min(max(0,-hyp[0][ph,jo]),max(0,hyp[0][ph,jn]));actual_cap=min(max(0,-signed[ph,jo]),max(0,signed[ph,jn])) if r.accepted else 0.
                    opp.append((seg,model,name,i,m.days[i-1],r.old,r.new,r.accepted,len(gr),r.ticket,exec_cap,actual_cap,r.expected_gain,realized,paid[ph,[jo,jn]].sum(),npct[jn],opct[jo],old_rel,bounds.at[i,'disp_group']))
            for ph0,j in zip(*np.nonzero(abs(signed)>1e-15)):
                count=state.units[ph0,j]-before[ph0,j];fee=paid[ph0,j];q=fifo[(ph0,j)]
                if count>0:
                    q.append((i,count,price[j],fee/count))
                elif count<0:
                    left=-count; sf=fee/left
                    while left>max(1e-18,-count*1e-12) and q:
                        born,qty,px,bf=q.popleft();sold=min(qty,left);left-=sold
                        why='restricted_legacy' if 0<=due_before[ph0,j]<i else 'scheduled'
                        if target is None and i>=hi-9:why='segment_settlement' if why=='scheduled' else why
                        lots.append((seg,model,name,ph0,symbols[j],born,i,i-born,why,sold,px*sold,price[j]*sold,bf*sold,sf*sold))
                        alloc+=(bf+sf)*sold
                        if qty>sold:q.appendleft((born,qty-sold,px,bf))
                    assert left*price[j]<1e-10
            pre_sleeve=(signed.clip(min=0)*.001+(-signed).clip(min=0)*.002).sum()
            # Same-sleeve roll trades cancel out before orders are sent across sleeves.
            grossbuy=buy.sum();grosssell=grossbuy-signed.sum()
            pre_raw=.001*grossbuy+.002*grosssell
            assert abs(pre_sleeve-row['fee']-.003*row['crossed'])<1e-11
            receipts.append((seg,model,name,i,row['date'],row['nav'],row['cash'],row['buy'],row['sell'],row['fee'],pre_raw,pre_sleeve,pre_raw-pre_sleeve,pre_sleeve-row['fee'],err))
            totalfee+=row['fee']
        for (sl,j),q in fifo.items():
            for born,qty,px,bf in q:
                lots.append((seg,model,name,sl,symbols[j],born,stop,stop-born,'open_at_boundary',qty,qty*px,np.nan,qty*bf,0.));alloc+=qty*bf
        assert abs(totalfee-alloc)<1e-9,(seg,model,name,totalfee,alloc)
        print(sys.argv[1],seg,model,name,flush=True)
    for fn,rows,col in [('lifecycle',lots,'segment model test sleeve symbol entry exit days outcome shares cost_basis sell_value buy_fee sell_fee'),('opportunities',opp,'segment model test idx signal_date old new accepted same_day_pairs ticket executable_capital actual_switched expected realized fees new_pct old_pct old_h10_excess dispersion'),('fees',receipts,'segment model test idx date nav cash buy sell fee theoretical_unnetted theoretical_by_sleeve within_sleeve_saved across_sleeve_saved parity_error'),('same_budget',budget,'segment model test idx rule accepted ticket named_budget portfolio_purchases gross fee net'),('gaps',errors,'segment model test idx rule error')]:
        pd.DataFrame(rows,columns=col.split()).to_parquet(HERE/f'{fn}_{sys.argv[1]}.parquet',index=False)
if __name__=='__main__':main()
