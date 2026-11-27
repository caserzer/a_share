"""Attribute the daily 78+tail challenger to true OOS outcomes and actual stock fills."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'p2'))
from inputs import market,pd,np,SEGMENTS
from book import State,step
OUT=HERE/'results'
KEY=['scope','arm','count','role','outcome']

def plans(m):
    gates=pd.read_csv(OUT/'veto_gates.csv')
    v=gates.pivot(index='quarter',columns='model',values=['auc','brier','ece','events','non_events'])
    passed=(v.auc['tail']>=.55)&(v.auc['tail']>v.auc.inc)&(v.brier['tail']<v.brier.inc)&(v.brier['tail']<v.brier.history)&(v.ece['tail']<v.ece.inc)&(v.events['tail']>=20)&(v.non_events['tail']>=20)
    assert set(passed[passed].index)=={'2022Q3','2022Q4','2023Q2'}
    g=pd.read_parquet(OUT/'quarterly_scores.parquet',columns=['signal_date','entry_idx','instrument','R','risk','h10'])
    out={}
    for e,z in g.groupby('entry_idx'):
        z=z.sort_values(['R','instrument'],ascending=False)
        k=len(z)//10
        core=m.symbols.get_indexer(z.instrument.iloc[:k])
        extra=m.symbols.get_indexer(z.instrument.iloc[k:k+3])
        riskorder=m.symbols.get_indexer(z.iloc[:k].sort_values(['risk','instrument'],ascending=False).instrument)
        enabled=bool(passed[str(z.signal_date.iloc[0].to_period('Q'))])
        valid=z.dropna(subset='h10').sort_values(['h10','instrument'])
        y=np.zeros(m.n,int)
        y[m.symbols.get_indexer(valid.instrument)]=1+np.floor(10*np.arange(len(valid))/len(valid)).astype(int)
        out[e]=(core,extra,riskorder,enabled,y)
    return out

def main():
    m,actions=market();targets=plans(m)
    daily=[];alloc=[];tickets=[]
    for scope,begin,enddate in SEGMENTS:
        lo,hi=m.days.get_indexer([begin,enddate])
        for count in [2,3]:
            for arm in ['R','V_risk_'+str(count)]:
                state=State.empty(m.n)
                # Labels follow the ownership window across overnight marks and
                # restricted carry. Non-traded cash has no gross stock P&L.
                role=np.zeros((10,m.n),int)
                category=np.zeros_like(role)
                gross_sums=np.zeros((4,11));fee_sums=np.zeros_like(gross_sums)
                previous_nav=1.;previous_price=np.zeros(m.n)
                for i in range(lo,hi+1):
                    ph=(i-lo)%10
                    selected=None
                    if i+10<=hi:
                        core,adds,riskorder,enabled,dec=targets[i]
                        removed=riskorder[:count] if enabled else np.array([],int)
                        extras=adds[:count] if enabled else np.array([],int)
                        selected=core if arm=='R' else np.r_[core[~np.isin(core,removed)],extras]
                    price=np.nan_to_num(m.marks['flat'][0][i])
                    prev=state.units.copy()
                    pre_role=role.copy();pre_cat=category.copy()
                    gross1=prev*(price-previous_price)
                    row,info=step(m,actions,state,lo,hi,i,selected,1,True)
                    od,fee,buy,ticket,nav=info
                    if selected is not None:
                        # Every selected sleeve is rebalanced. Give selected legacy
                        # holdings a new target class, independent of net order size.
                        role[ph,selected]=1
                        category[ph,selected]=dec[selected]
                        chosen_special=removed if arm=='R' else extras
                        role[ph,chosen_special]=2 if arm=='R' else 3
                        if enabled:
                            for jj,group in [(removed,'veto'),(extras,'replacement')]:
                                for j in jj:
                                    y=dec[j]
                                    tickets.append(dict(scope=scope,arm=arm,count=count,entry_idx=i,
                                        instrument=m.symbols[j],role=group,realized_decile=y,
                                        target=ticket*(j in selected),counterfactual_ticket=ticket,
                                        bought=buy[j],post_value=state.units[ph,j]*price[j],
                                        net_order=od[ph,j],actual_fee=fee[ph,j]))
                    mark=np.nan_to_num(m.marks['flat'][0 if i==hi else 1][i])
                    gross2=state.units*(mark-price)
                    # Fees follow net direction. Prior labels own sells, new labels buys.
                    for value,lab,decile,res in [(gross1,pre_role,pre_cat,gross_sums),
                            (gross2,role,category,gross_sums),
                            (fee,np.where(od<0,pre_role,role),np.where(od<0,pre_cat,category),fee_sums)]:
                        mask=value!=0
                        np.add.at(res,(lab[mask],decile[mask]),value[mask])
                    err=row['nav']-previous_nav-(gross1.sum()+gross2.sum()-fee.sum())
                    assert abs(err)<1e-11
                    daily.append(dict(scope=scope,arm=arm,count=count,date=m.days[i],nav=row['nav'],fee=row['fee']))
                    previous_nav=row['nav'];previous_price=mark
                np.testing.assert_allclose((gross_sums-fee_sums).sum(),previous_nav-1,atol=1e-10)
                for k,key in enumerate(['legacy_or_successor','core','retained_would_veto','replacement']):
                    for band,indices in [('unknown',[0]),('D1',[1]),('D2-D5',range(2,6)),('D6-D9',range(6,10)),('D10',[10])]:
                        alloc.append(dict(scope=scope,arm=arm,count=count,role=key,outcome=band,gross=gross_sums[k,indices].sum(),fee=fee_sums[k,indices].sum()))
    d=pd.DataFrame(daily);d.to_parquet(OUT/'veto_impact_daily.parquet',index=False)
    t=pd.DataFrame(tickets);t.to_parquet(OUT/'veto_impact_tickets.parquet',index=False)
    a=pd.DataFrame(alloc);a['net']=a.gross-a.fee;a.to_csv(OUT/'veto_impact.csv',index=False)
    # Certify agreement with the corrected canonical replay, including non-veto quarters.
    src=pd.read_parquet(OUT/'funded_daily.parquet',columns=['arm','segment','date','nav','fee','hold']).query('hold==10')
    for count,g in d.groupby('count'):
        z=g.merge(src.rename(columns={'segment':'scope'}),on=['arm','scope','date'],validate='1:1')
        assert len(z)==len(g)
        for key in ['nav','fee']:np.testing.assert_allclose(z[key+'_x'],z[key+'_y'],rtol=0,atol=1e-11)
if __name__=='__main__':main()
