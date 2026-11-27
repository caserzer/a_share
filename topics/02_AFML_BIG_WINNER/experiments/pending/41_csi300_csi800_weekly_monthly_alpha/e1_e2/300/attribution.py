"""Economic diagnostics on stocks traded or protected by the measured E2 arm."""
from run import *
def main():
    m,actions=market();plans,books=targets(m)
    switches=pd.read_parquet(DEST/'pairs.parquet').query('arm=="E2_hold"')
    expected=pd.read_parquet(DEST/'daily.parquet').query('arm=="E2_hold"')
    result=[]
    for scope,beg,fin in SEGMENTS:
        lo,hi=m.days.get_indexer([beg,fin])
        tickets={e:list(zip(m.symbols.get_indexer(q.old),m.symbols.get_indexer(q.new))) for e,q in switches[switches.scope==scope].groupby('entry_idx')}
        def policy(e,ph,base,state):
            v=base.copy()
            for original,replacement in tickets.get(e,[]):v[v==original]=replacement
            return v
        def observe(e,ph,chosen,state,prior,detail):
            orders,fees,buy,ticket,nav=detail
            first=np.nan_to_num(m.marks['flat'][0][e]);last=m.marks['flat'][0][e+10]
            def record(j,group,amount):
                r=last[j]/first[j]-1 if first[j]>0 and np.isfinite(last[j]) else np.nan
                result.append((scope,e,m.symbols[j],group,amount,r,amount*r,orders[ph,j],fees[ph,j],nav))
            for old,new in tickets.get(e,[]):
                record(new,'incoming_actual',buy[new])
                record(old,'displaced_planned_opportunity',ticket)
            for j in chosen:
                if prior[j]>0 and j in books[e][3]:
                    record(j,'retained_vs_forced_candidate',min(prior[j],state.units[ph,j])*first[j])
        d,*_=funded(m,actions,plans['hold'],lo,hi,arm='E2',books=books,policy=policy,observer=observe)
        np.testing.assert_allclose(d.nav,expected.loc[expected.scope==scope,'nav'],atol=1e-10)
    z=pd.DataFrame(result,columns='scope entry_idx instrument group amount h10_mark_return gross_on_amount actual_net_order fee start_sleeve_nav'.split())
    z.to_parquet(DEST/'opportunity.parquet',index=False)
    z=z[z.h10_mark_return.notna()].copy()
    z['gain_if_positive']=z.gross_on_amount.clip(lower=0)
    z.groupby(['scope','group'])[['amount','gross_on_amount','gain_if_positive','fee']].sum().to_csv(DEST/'opportunity_summary.csv')
if __name__=='__main__':main()
