"""Measure realized capital and H10 outcome buckets on source-driven reserve orders."""
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent/sys.argv[1]
sys.path.insert(0,str(OUT.parent))
from reserves import *
def main():
    m=load(False)
    choices=pd.read_parquet(OUT/'choices.parquet')
    ranks=pd.read_parquet(HERE.parent/'p2/results/scores.parquet',columns=['entry_idx','instrument'])
    rankrows=[]
    for e,h in ranks.groupby('entry_idx'):
        if e+10>=len(m.days):continue
        jj=m.symbols.get_indexer(h.instrument)
        y=m.o[e+10,jj]/m.o[e,jj]-1
        q=np.full(len(h),np.nan)
        valid=np.flatnonzero(np.isfinite(y))
        order=valid[np.lexsort((h.instrument.to_numpy()[valid],y[valid]))]
        if len(order):q[order]=1+np.floor(10*np.arange(len(order))/len(order))
        rankrows.append(h.assign(outcome=np.select([~np.isfinite(q),q==1,q<=5,q<10],['unknown','D1','D2-D5','D6-D9'],default='D10'),outcome_return=y))
    choices=choices.merge(pd.concat(rankrows),on=['entry_idx','instrument'],validate='m:1')
    orders=pd.read_parquet(OUT/'orders.parquet').rename(columns={'arm':'spec'})
    daily=pd.read_parquet(OUT/'daily.parquet')
    funds=[]
    for (arm,seg),o in orders.groupby(['spec','segment']):
        if arm not in choices.spec.unique():continue
        start=m.days.get_loc(daily.query('arm==@arm and segment==@seg').date.min())
        o=o[o.sleeve==(o.entry_idx-start)%10].copy()
        z=choices.query('spec==@arm and selected').merge(o[['entry_idx','instrument','net','target','within','blocked']],on=['entry_idx','instrument'],validate='1:1',how='inner')
        # A retained overdue lot is blocked from a new allocation. Actual marginal buy
        # orders include within-sleeve reductions and cross-sleeve netting.
        z['feasible_target']=np.where(z.blocked.gt(0) | ~m.buy[z.entry_idx,m.symbols.get_indexer(z.instrument)],0,z.target)
        z['executed_net_buy']=z.net.clip(lower=0)
        z['changed']=~z.baseline_buy
        z['covered']=z.score.notna()
        funds.append(z.assign(segment=seg))
    f=pd.concat(funds)
    keys=['spec','segment','covered','changed','outcome']
    f.groupby(keys,dropna=False)[['target','feasible_target','executed_net_buy']].sum().reset_index().to_csv(OUT/'outcome_funds.csv',index=False)
if __name__=='__main__':main()
