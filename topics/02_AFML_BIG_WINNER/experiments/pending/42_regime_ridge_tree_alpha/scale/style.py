"""S5: sector seats, matched differences and the fold-frozen construction of Z1."""
from collections import Counter
from scale_common import *
sys.path.insert(0,str(EP41/'p1'))
from engine import load
from matching import covariates, assign

def quantiles(x,weights,probs):
    order=np.argsort(x)
    x=x[order];w=weights[order]
    mid=(np.cumsum(w)-.5*w)/w.sum()
    return np.interp(probs,mid,x)

def keep_budget(g,rank,budgets):
    order=g.sort_values([rank,'instrument'],ascending=False)
    return order.loc[order.groupby('sector').cumcount()<order.sector.map(budgets).fillna(0)]

def main():
    market=load(False)
    cap,adv,vol,industry,source=covariates(market)
    cols=['signal_date','instrument','entry_idx','vol_live','vol_fixed']
    df=pd.read_parquet(RES/'scale_scores.parquet',columns=cols)
    ridge=pd.read_parquet(SCORES,columns=KEY+['R'])
    df=df.merge(ridge,on=KEY,validate='1:1')
    plans=[];pairs=[];coverage=[]
    for dt,g in df.groupby('signal_date',sort=True):
        e=int(g.entry_idx.iloc[0]);j=market.symbols.get_indexer(g.instrument)
        assert min(j)>=0 and market.days[e-1]==dt
        g=g.assign(sector=industry(e-1)[j],cap=pd.Series(cap[e-1,j]).rank(pct=True).to_numpy(),adv=pd.Series(adv[e-1,j]).rank(pct=True).to_numpy())
        k=len(g)//10
        ridge_head=g.sort_values(['R','instrument'],ascending=False).head(k)
        budgets=ridge_head.sector.value_counts()
        a=keep_budget(g,'vol_live',budgets).set_index('instrument')
        b=keep_budget(g,'vol_fixed',budgets).set_index('instrument')
        common=a.index.intersection(b.index).tolist()
        a0=a.loc[a.index.difference(common)];b0=b.loc[b.index.difference(common)]
        x=a0[['cap','adv']].to_numpy(); y=b0[['cap','adv']].to_numpy()
        diff=np.abs(x[:,None,:]-y[None,:,:])
        allow=(a0.sector.to_numpy()[:,None]==b0.sector.to_numpy()[None,:])&(a0.sector.to_numpy()[:,None]!='未知')&(diff<=.1).all(axis=2)
        if len(a0):i,jj=assign(allow,diff.sum(axis=2));ns=len(i)
        else:i=jj=np.zeros(0,dtype=int);ns=0
        for ii,j1 in zip(i,jj):pairs.append((dt,a0.index[ii],b0.index[j1],a0.sector.iloc[ii],*diff[ii,j1]))
        for name,targets in [('sector_live',a.index.tolist()),('sector_fixed',b.index.tolist()),('paired_live',common+a0.index[i].tolist()),('paired_fixed',common+b0.index[jj].tolist())]:
            plans.append((dt,e,name,k,targets))
            if name.startswith('paired'):
                plans.append((dt,e,name+'_invested',len(targets),targets))
        coverage.append((dt,k,len(common),len(a0),ns,int(allow.sum()),len(x)-np.isfinite(x).all(axis=1).sum(),len(y)-np.isfinite(y).all(axis=1).sum()))
    atomic_parquet(pd.DataFrame(plans,columns='signal_date entry_idx arm denominator instruments'.split()),RES/'S5_targets.parquet')
    atomic_parquet(pd.DataFrame(pairs,columns='signal_date live fixed sector cap_distance adv_distance'.split()),RES/'S5_pairs.parquet')
    pd.DataFrame(coverage,columns='signal_date K common disputed matched feasible_edges missing_live missing_fixed'.split()).to_csv(RES/'S5_coverage.csv',index=False)
    eligible=pd.read_parquet(RES/'eligible.parquet').reindex(index=market.days,columns=market.symbols).fillna(False).to_numpy()
    c=pd.read_parquet(ep.PRIVATE/'qfq_close.parquet').reindex(index=market.days,columns=market.symbols)
    returns=c.pct_change(fill_method=None).to_numpy()
    cells={};weights={};valid_cap={};by_day={}
    for i in range(len(market.days)):
        ids=np.flatnonzero(eligible[i]); known=np.isfinite(cap[i,ids])
        rank=pd.Series(cap[i,ids]).rank(pct=True).to_numpy()
        sec=industry(i)[ids]
        ok=known & (sec!='未知')
        cell=np.array([f'{s}|{int(np.ceil(3*r))}' if flag else '' for s,r,flag in zip(sec,rank,ok)])
        cells[i]=cell;by_day[i]=returns[i,ids]
        valid_cap[i]=ok.sum()/max(1,len(ids))
        weights[i]={k:v/max(1,ok.sum()) for k,v in Counter(cell[ok]).items()}
    out=[]
    for q in sorted(df.signal_date.dt.to_period('Q').unique()):
        prior=np.flatnonzero(market.days.to_period('Q')==q-1)
        ref=pd.DataFrame([weights[i] for i in prior]).fillna(0).mean().to_dict()
        ref={k:v for k,v in ref.items() if v>0}
        if ref:
            sw=sum(ref.values());ref={k:w/sw for k,w in ref.items()}
        first=market.days.searchsorted(q.start_time)
        end=market.days.searchsorted(q.end_time,side='right')
        subset=list(range(max(0,first-272),end));iqr=[];supp=[];obs=[]
        for i in subset:
            cell=cells[i];ret=by_day[i];valid=np.isfinite(ret)&(cell!='');counts=Counter(cell[valid])
            supported=sum(w for k,w in ref.items() if counts.get(k,0)>0)
            supp.append(supported);obs.append(valid.sum())
            if valid.sum()<100 or supported<1-1e-9:
                iqr.append(np.nan);continue
            weights_i=np.asarray([ref.get(k,0)/counts[k] for k in cell[valid]])
            ok=weights_i>0
            q1,q3=quantiles(ret[valid][ok],weights_i[ok],[.25,.75]);iqr.append(q3-q1)
        smooth=pd.Series(iqr).rolling(20).mean().to_numpy()
        for j,i in enumerate(subset):
            if i<first:continue
            win=smooth[j-252:j] if j>=252 else []
            val=np.nan
            if len(win)==252 and np.isfinite(win).all() and np.isfinite(smooth[j]):val=((win<smooth[j]).sum()+.5*(win==smooth[j]).sum())/252
            out.append((str(q),market.days[i],len(ref),np.mean([valid_cap[i0] for i0 in prior]),obs[j],supp[j],iqr[j],smooth[j],val))
    pd.DataFrame(out,columns='quarter signal_date reference_cells reference_known_share stocks reference_weight_supported fixed_IQR fixed_raw fixed_Z1'.split()).to_csv(RES/'S5_state.csv',index=False)
if __name__=='__main__':main()
