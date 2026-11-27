"""Check the rank-bucket gross identity and aggregate target and realized match coverage."""
from matching import *
def main():
    m=load();plans,_=selections(m);op=m.o
    cal=m.days
    shares={e:len(t) for e,t in plans['refit','head'].items()}
    cap,adv,vol,industry,snapshot=covariates(m)
    identity=[];exp=[]
    pairs=pd.read_parquet(RESULT/'pairs.parquet')
    for e in shares:
        head,runner,dec=[plans['refit',b][e] for b in ['head','runner','decile']]
        assert np.array_equal(dec,np.r_[head,runner])
        if e+10<len(cal):
            ret=op[e+10,dec]/op[e,dec]-1
            eligible=m.buy[e,dec]&m.sell[e+10,dec]&np.isfinite(ret)
            if eligible.all():
                k=len(head);gap=(ret[:k].sum()+ret[k:].sum())/len(ret)-ret.mean()
                assert abs(gap)<1e-12
                identity.append(dict(entry_idx=e,k=k,l=len(dec),error=gap))
    for (e,tol),g in pairs.groupby(['entry_idx','caliper']):
        pool=plans['refit','pool'][e];i=e-1
        c=pd.DataFrame(dict(cap=cap[i,pool],adv=adv[i,pool],vol=vol[i,pool]),index=m.symbols[pool]).rank(pct=True)
        diff=c.loc[g['head']].to_numpy()-c.loc[g.runner].to_numpy()
        exp.append(dict(entry_idx=e,caliper=tol,seats=len(g),head_seats=shares[e],head_buy_allowed=g.head_buy_allowed.sum(),runner_buy_allowed=g.runner_buy_allowed.sum(),
            cap_diff=np.nanmean(diff[:,0]),adv_diff=np.nanmean(diff[:,1]),vol_diff=np.nanmean(diff[:,2]),snapshot_lag=i-int(snapshot.iloc[i])))
    pd.DataFrame(exp).to_csv(RESULT/'match_exposures.csv',index=False)
    pd.DataFrame(identity).to_csv(RESULT/'gross_identity.csv',index=False)
    match=pd.read_parquet(RESULT/'matched_daily.parquet')
    head=pd.read_parquet(RESULT/'daily.parquet').query('bucket=="head" and model=="refit" and phase==-1 and kind=="strict"')
    full=head.groupby('segment').agg(full_target=('planned','sum'),full_blocked=('blocked_budget','sum'))
    z=match.groupby(['segment','caliper','bucket']).agg(target=('planned','sum'),blocked=('blocked_budget','sum')).join(full,on='segment')
    z['relative_filled_budget']=(z.target-z.blocked)/(z.full_target-z.full_blocked)
    z.to_csv(RESULT/'match_funded_coverage.csv')
    print(len(identity),'eligible rank identities')
if __name__=='__main__':main()
