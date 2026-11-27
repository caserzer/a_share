"""Evaluate an added source on EP41 P2's frozen core and Ridge reserve buy orders."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'p1'))
from engine import *
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"p1"))
from summarize import months,stats
from scipy.optimize import linear_sum_assignment
from accounts_followup import industries

def prepare():
    m=load(False)
    narrow=HERE.parent/'p2/results/scores.parquet'
    df=pd.read_parquet(narrow)
    daily=pd.read_parquet(DEST/'daily_scores.parquet',columns=['entry_idx','instrument','vol20','mom5'])
    df=df.merge(daily,on=['instrument','entry_idx'],validate='1:1')
    df['adv20']=pd.read_parquet(PRIVATE/'money.parquet').rolling(20,min_periods=20).mean().to_numpy()[m.days.get_indexer(df.signal_date),m.symbols.get_indexer(df.instrument)]
    ind=industries(df.signal_date.unique())
    cards=[]
    for e,g in df.groupby('entry_idx'):
        g=g.sort_values(['R','instrument'],ascending=False).copy()
        k=len(g)//10;n=k//5
        t=g.iloc[:k].sort_values(['T','instrument'],ascending=False)
        core=t.instrument.iloc[:-n].to_numpy()
        g['industry']=ind[g.signal_date.iloc[0]].reindex(g.instrument).fillna('未知').to_numpy()
        for key in ['mom5','vol20','adv20']:g[key+'_pct']=g[key].rank(pct=True)
        p=g.iloc[k:2*k].copy()
        cards.append((int(e),core,p.reset_index(drop=True),n))
    return m,cards

def choose(pool,n,score,source):
    # Unknown baseline buy slots keep their original target. Each scored slot always
    # has itself as a fallback, with selection among feasible names ranked by score.
    score=np.asarray(score,float);ids=np.flatnonzero(np.isfinite(score[:n]))
    if not len(ids):return np.arange(n)
    valid=np.flatnonzero(np.isfinite(score))
    cost=pd.Series(score[valid]).rank(ascending=False,method='min').to_numpy()/(len(valid)+1)
    mask=np.ones((len(ids),len(valid)),bool)
    for column in (['mom5_pct','adv20_pct','vol20_pct'] if source=='n1' else ['mom5_pct']):
        x=pool[column].to_numpy();mask &= abs(x[ids,None]-x[None,valid])<=.20
    if source=='n2':
        industry=pool.industry.to_numpy()
        mask &= industry[ids,None]==industry[None,valid]
        freq=pool.brokers.to_numpy()
        mask &= freq[ids,None]==freq[None,valid]
    mask|=ids[:,None]==valid[None,:]
    objective=np.where(mask,cost[None,:]+valid[None,:]*1.e-7,1e6)
    a,b=linear_sum_assignment(objective)
    assert mask[a,b].all()
    selected=np.arange(n); selected[ids[a]]=valid[b]
    assert len(set(selected))==n
    return selected

def evaluate(m,plans,spans,out):
    rows=[];orders=[]
    for name,plan in plans.items():
        packed=pack(m,plan)
        for seg,(start,end) in enumerate(spans,1):
            with tempfile.NamedTemporaryFile() as f:
                z=simulate(m,packed,(start,end,end),orderfile=f.name)
                o=pd.read_csv(f.name,names='entry_idx sleeve id target within net fee blocked'.split())
                o['instrument']=m.symbols[o.id]
                orders.append(o.drop(columns='id').assign(arm=name,segment=seg))
            rows.append(z.assign(segment=seg,arm=name))
    d=pd.concat(rows).reset_index()
    d.to_parquet(out/'daily.parquet',index=False)
    pd.concat(orders,ignore_index=True).to_parquet(out/'orders.parquet',index=False)
    mm=pd.concat([months(g,m.days).assign(arm=arm,segment=seg) for (arm,seg),g in d.groupby(['arm','segment'])])
    mm.to_csv(out/'monthly.csv',index=False)
    diff=[]
    for arm in plans:
        if arm in ['ridge','rank']:continue
        for base in ['ridge','rank']:
            a=mm[mm.arm==arm].set_index(['segment','month'])[['net','gross','fee']]
            b=mm[mm.arm==base].set_index(['segment','month'])[['net','gross','fee']]
            v=(a-b).dropna().reset_index()
            for seg,g in v.groupby('segment'):
                diff.append(dict(arm=arm,base=base,segment=seg,months=len(g),net_bp=g.net.mean()*1e4,gross_bp=g.gross.mean()*1e4,fee_bp=g.fee.mean()*1e4))
    pd.DataFrame(diff).to_csv(out/'comparisons.csv',index=False)
    return d
