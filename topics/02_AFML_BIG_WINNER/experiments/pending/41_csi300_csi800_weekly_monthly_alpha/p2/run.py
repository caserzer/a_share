"""Replay signed funded orders and restricted openings. Run inputs.py first."""
from inputs import *
from book import funded, step
from accounts_followup import replay

def trial(m,actions,snapshot,e,start,end,book,chosen,ticket=None,positions=False):
    state=snapshot.copy()
    op=m.marks['flat'][0]
    phase=(e-start)%10
    initial=state.cash[phase]+state.units[phase]@np.nan_to_num(op[e])
    total=state.cash.sum()+state.units.sum(axis=0)@np.nan_to_num(op[e])
    fee=totalfee=terminal=0.
    bystock=np.zeros(m.n)
    posfee=np.zeros(m.n)
    last=np.nan_to_num(op[e])
    for i in range(e,e+11):
        price=np.nan_to_num(op[i])
        bystock+=state.units[phase]*(price-last)
        last=price
        if i==e+10 and i!=end:break
        plan=chosen if i==e else (book[i] if i+10<=end else None)
        row,detail=step(m,actions,state,start,end,i,plan,1,True,ticket if i==e else None)
        orders,fees,buy,seat,_=detail
        fee+=fees[phase].sum()
        totalfee+=fees.sum()
        posfee+=fees[phase]
        if i==end:terminal=fees[phase].sum()
        if i==e:
            budget=seat
            filled=buy.copy()
    final=state.cash[phase]+state.units[phase]@last
    net=(final-initial)/initial
    np.testing.assert_allclose(net,(bystock.sum()-posfee.sum())/initial,rtol=0,atol=2e-12)
    fullnav=state.cash.sum()+state.units.sum(axis=0)@last
    return dict(nav0=initial,net=net,fee=fee/initial,gross=bystock.sum()/initial,
                terminal_fee=terminal/initial,per_seat=budget,whole_open=total,
                whole_end=fullnav,whole_fee=totalfee,whole_net=fullnav/total-1), (bystock,posfee,filled)

def run():
    m,actions=market()
    plans,books=targets(m)
    daily=[];od=[];legs=[];common=[];corners=[];positions=[];windows=[];phasem=[]
    for scope,begin,finish in SEGMENTS:
        start,end=m.days.get_indexer([begin,finish])
        snapshots={}
        for arm in ARMS+['equal']:
            for mul in ([0,1,2] if arm!='equal' else [1]):
                d,orders,ls,states=funded(m,actions,plans[arm],start,end,mul,arm,
                        books if mul==1 and arm!='equal' else None,mul==1 and arm!='equal')
                daily.append(d.assign(scope=scope,arm=arm,mul=mul))
                if states:snapshots[arm]=states
                if orders:od.append(pd.DataFrame(orders,columns=['idx','phase','instrument','order','fee']).assign(scope=scope,arm=arm))
                if ls:legs.append(pd.DataFrame(ls).drop(columns='j').assign(scope=scope,arm=arm))
            if arm=='equal':continue
            for phase in range(10):
                subset={e:plans[arm][e] for e in range(start+phase,end-9,10)}
                w,d,_,_=replay(m,actions,subset,10,1,False)
                windows.append(pd.DataFrame(w,columns=['entry_idx','net','fee','turnover']).assign(scope=scope,arm=arm,phase=phase))
                phasem.append(pd.DataFrame(d,columns=['idx','date','nav','cash','buy','sell','fee']).assign(scope=scope,arm=arm,phase=phase))
        for e in range(start,end-9,10):
            ids,r,pool,removed,adds,_=books[e]
            # Both counterfactuals start in the baseline and use the same target ticket.
            # The baseline's signal-date decision is equal weight. Funding is haircutted
            # using the same conservative full-trade fee reserve, before testing fills.
            snapshot=snapshots['hold'][e]
            price=np.nan_to_num(m.marks['flat'][0][e])
            initial=snapshot.cash[0]+snapshot.units[0]@price
            ticket=initial*(1-.002)/(1+.001)/len(r)
            yopen=m.o[e,ids]
            yend=m.o[e+10,ids]
            known=np.isfinite(yopen)&(yopen>0)&np.isfinite(yend)&(yend>0)
            y=yend[known]/yopen[known]-1
            d=np.full(m.n,np.nan)
            # EP40's realized deciles assign equal-size buckets after ascending
            # return, ties ordered by instrument.
            yy=pd.DataFrame({'instrument':m.symbols[ids[known]],'h10':y,'j':ids[known]})
            yy=yy.sort_values('instrument')
            d[yy.j]=ledger.assign_deciles(yy,'h10')
            for arm in ['tree','rank']:
                cs,(stock,fee,fill)=trial(m,actions,snapshot,e,start,end,plans['hold'],plans[arm][e],ticket)
                extra=adds if arm=='tree' else pool[:len(adds)]
                common.append(dict(scope=scope,entry_idx=e,arm=arm,**cs,planned_budget=ticket*len(extra),filled=fill[extra].sum()))
                for j in np.union1d(np.r_[plans[arm][e],removed],np.flatnonzero(abs(stock)+fee>0)):
                    role='incoming' if j in extra else ('removed' if j in removed else ('core' if j in plans[arm][e] else 'legacy'))
                    positions.append(dict(scope=scope,entry_idx=e,arm=arm,instrument=m.symbols[j],role=role,
                         decile=d[j],gross=stock[j]/initial,fee=fee[j]/initial,filled=fill[j]/initial))
            for state_arm in ['tree','rank']:
                for rule in ['tree','rank']:
                    result,_=trial(m,actions,snapshots[state_arm][e],e,start,end,plans[state_arm],plans[rule][e])
                    corners.append(dict(scope=scope,entry_idx=e,state=state_arm,rule=rule,**result))
        print(scope,'done',flush=True)
    frames=dict(funded_daily=pd.concat(daily),orders=pd.concat(od),next_rebalance=pd.concat(legs),
                common_start=pd.DataFrame(common),corners=pd.DataFrame(corners),
                common_positions=pd.DataFrame(positions),phase_windows=pd.concat(windows),phase_daily=pd.concat(phasem))
    for name,f in frames.items():f.to_parquet(OUT/(name+'.parquet'),index=False)
    actual=frames['funded_daily'].query('mul==1')
    for arm,file,old in [('tree','market_challenge_stagger','X1169'),('hold','stagger','R')]:
        ref=pd.read_parquet(FOLLOW/'results'/(file+'.parquet')).query('arm==@old')
        if 'netting' in ref:ref=ref[ref.netting]
        keys=['scope','date']
        d=actual.query('arm==@arm').merge(ref,on=keys,validate='1:1')
        assert len(d)==len(ref)
        for col in ['nav','fee','cash','crossed']:
            np.testing.assert_allclose(d[col+'_x'],d[col+'_y'],atol=1e-10,rtol=0)
    for row in frames['corners'].query('state==rule').itertuples():
        d=actual.query('scope==@row.scope and arm==@row.rule').set_index('idx')
        exit_idx=row.entry_idx+10
        ending=d.loc[exit_idx, 'pre' if exit_idx<d.index.max() else 'nav']
        np.testing.assert_allclose([row.whole_open,row.whole_end],[d.loc[row.entry_idx,'pre'],ending],atol=1e-11,rtol=0)
    print('Frozen 300 account and all real corner checks passed')
if __name__=='__main__':run()
