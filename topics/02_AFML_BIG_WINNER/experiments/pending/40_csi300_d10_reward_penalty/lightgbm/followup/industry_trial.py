from accounts_followup import *
from stagger import simulate
def within(g):
    g=g.sort_values(['R','instrument'],ascending=False).set_index('instrument')
    k=len(g)//10;top=g.iloc[:k];second=g.iloc[k:2*k];pairs=[]
    for sector,x in top.groupby('industry'):
        y=second[second.industry==sector].sort_values(['T','instrument'],ascending=False)
        x=x.sort_values(['T','instrument'])
        for a,b in zip(x.index,y.index):
            gain=y.at[b,'T']-x.at[a,'T']
            if gain>0:pairs.append((gain,a,b))
    swaps=sorted(pairs,reverse=True)[:k//5]
    ids=top.index.difference([a for _,a,b in swaps]).append(pd.Index([b for _,a,b in swaps]))
    assert len(ids)==k and g.loc[ids].industry.value_counts().sort_index().equals(top.industry.value_counts().sort_index())
    return ids

def main():
    ledger.accounts.OUT=DEST
    m,actions=ledger.setup('flat')
    scores=pd.read_parquet(DEST/'daily_scores.parquet')
    ind=industries(scores.signal_date.unique())
    plans={};rows=[];st=[]
    for e,g in scores.groupby('entry_idx'):
        ids=within(g.assign(industry=g.instrument.map(ind[g.signal_date.iloc[0]]).fillna('未知')))
        plans[e]=m.symbols.get_indexer(ids)
    for scope,start,end in [('primary','2021-01-11','2025-03-03'),('later','2025-03-03','2026-10-12')]:
        a,b=m.days.get_indexer([start,end])
        for ph in range(10):
            w,_,_,_=replay(m,actions,{i:plans[i] for i in range(a+ph,b-9,10)},10,1,False)
            rows.append(pd.DataFrame(w,columns='entry_idx net fee turnover'.split()).assign(scope=scope,phase=ph))
        st.append(simulate(m,actions,plans,a,b,True).assign(scope=scope))
    pd.concat(rows).to_parquet(DEST/'industry_trial.parquet',index=False)
    pd.concat(st).to_parquet(DEST/'industry_trial_stagger.parquet',index=False)
if __name__=='__main__':main()
