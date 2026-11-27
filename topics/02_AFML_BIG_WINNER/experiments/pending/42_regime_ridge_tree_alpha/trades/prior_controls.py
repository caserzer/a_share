"""Bridge to frozen EP41 E2 and P2, and distinguish observable versus future exclusions."""
from pathlib import Path
import numpy as np,pandas as pd
from sources import OUT,OLD,PRIVATE
from measure import draws
def main():
    current=pd.read_parquet(OUT/'direct_months.parquet').query('fees==1');p2=pd.read_parquet(OLD/'p2/results/funded_daily.parquet').query('mul==1 and arm=="tree"').rename(columns={'date':'day'})
    prior=pd.read_csv(OLD/'e1_e2/300/results/full_months.csv').query('arm=="E2_hold"').copy()
    prior['turnover']=prior.buy+prior.sell
    comp=[];detail=[]
    for sc,g in p2.groupby('scope'):
        g=g.sort_values('day').copy();g['opening']=g.nav.shift().fillna(1)
        m=g.groupby(g.day.dt.strftime('%Y-%m')).agg(start=('opening','first'),end=('nav','last'),fee=('fee','sum'),buy=('buy','sum'),sell=('sell','sum')).iloc[1:-1]
        m['net']=m.end/m.start-1;m['fee']/=m.start;m['gross']=m.net+m.fee;m['turnover']=(m.buy+m.sell)/m.start
        for arm in ['N2','NarrowGate','Combo']:
            a=current.query('scope==@sc and arm==@arm').set_index('month')
            for code,b in [('EP41_E2',prior.query('scope==@sc').set_index('month')),('EP41_P2_tree',m)]:
                assert a.index.equals(b.index)
                dif=(a[['net','gross','fee','turnover']]-b[['net','gross','fee','turnover']])*1e4
                np.testing.assert_allclose(dif.net,dif.gross-dif.fee,atol=1.e-10)
                res=dif.net.to_numpy();boots=draws(len(res));ci=np.percentile(res[boots].mean(axis=1),[2.5,97.5])
                comp.append((sc,arm,code,len(dif),dif.net.mean(),*ci,np.sort(res)[:-3].mean(),dif.gross.mean(),dif.fee.mean(),dif.turnover.mean()))
    pd.DataFrame(comp,columns='scope arm baseline months net_bp lo hi trim_best3 gross_bp fee_bp turnover_bp'.split()).to_csv(OUT/'ep41_bridge.csv',index=False)
    m=pd.read_parquet(PRIVATE/'daily_members.parquet').astype(bool)
    changes=m.shift(fill_value=False)&~m
    z=pd.read_parquet(OLD/'p2/results/scores.parquet',columns=['entry_idx','instrument']);eligible=z.groupby('entry_idx').instrument.agg(set).to_dict()
    risk=pd.read_parquet(OUT/'covariates.parquet').set_index(['entry_idx','instrument'])
    for sc,end in [('primary','2025-03-03'),('later','2026-10-12')]:
        hi=m.index.get_loc(end);d=OUT/'books'/sc
        br=pd.read_parquet(d/'Ridge/decisions.parquet');lo=br.entry_idx.min()
        od=pd.read_parquet(d/'Ridge/orders.parquet').query('sleeve==(entry_idx-@lo)%10').set_index(['entry_idx','instrument'])
        for arm in ['N2','N2Boundary','NarrowGate','Safe','Announced','Combo']:
            a=pd.read_parquet(d/arm/'decisions.parquet')
            for r in a.itertuples():
                for role,securities in [('excluded',r.removed),('added',r.added)]:
                    for name in securities:
                        e=r.entry_idx;f=e+10
                        next_member=m.at[m.index[f-1],name] if f+10<=hi else None
                        next_eligible=name in eligible[f] if f+10<=hi else None
                        event=changes[name].iloc[e:min(hi+1,e+20)].any()
                        amount=od.at[(e,name),'broker'] if (e,name) in od.index else 0.
                        detail.append((sc,arm,e,name,role,r.ticket,max(amount,0.),next_member,next_eligible,event,e+19<=hi,bool(risk.at[(e,name),'announced'])))
    frame=pd.DataFrame(detail,columns='scope arm entry_idx instrument role ticket original_actual_buy next_member next_eligible exit20_observed full20 announced'.split())
    frame.to_parquet(OUT/'natural_names_and_membership.parquet',index=False)
    frame['next_member_lost_score']=frame.next_member.eq(True)&frame.next_eligible.eq(False)
    frame.groupby(['scope','arm','role']).agg(seats=('instrument','size'),ticket=('ticket','sum'),original_broker_buys=('original_actual_buy','sum'),next_unknown=('next_member',lambda x:x.isna().sum()),next_member_lost_score=('next_member_lost_score','sum'),next_exit=('next_member',lambda x:x.eq(False).sum()),exit_within20=('exit20_observed','sum'),already_announced=('announced','sum')).to_csv(OUT/'natural_membership_summary.csv')
    x=pd.read_parquet(OUT/'actual_switches.parquet')
    rows=[]
    for key,g in x.groupby(['scope','arm','role']):
        for typ,sub in [('left',g[g.event.eq(1)]),('right',g[g.right.eq(1)]),('all',g)]:
            actual=sub.dollars_actual_new
            rows.append((*key,typ,len(sub),sub.h10.mean(),sub.planned.sum(),(sub.h10*sub.planned).sum(),actual.sum(),(sub.h10.clip(upper=0)*actual).sum(),(sub.h10*actual).sum(),sub.fee.sum()))
    pd.DataFrame(rows,columns='scope arm role tail seats h10_average planned opportunity actual_buy actual_H10_losses actual_H10_gross fees'.split()).to_csv(OUT/'tail_economics.csv',index=False)
if __name__=='__main__':main()
