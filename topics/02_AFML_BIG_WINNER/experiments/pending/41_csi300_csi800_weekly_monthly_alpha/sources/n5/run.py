"""Read disclosed, dated edges. Reorder only the covered part of the fixed buy budget."""
from pathlib import Path
import hashlib
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'models'))
from ep41inputs import CACHE, KEY, SEG, ep, pd, read

def main():
    edges=pd.read_csv(HERE/'relationships.csv',parse_dates=['disclosure_date','active_start','active_end'])
    raw=read('qfq_close')
    cands=pd.read_parquet(ep.DEST/'daily_scores.parquet',columns=KEY+['entry_idx','R'])
    industry=pd.read_parquet(CACHE/'panel.parquet',columns=KEY+['l1_name'])
    tree=pd.read_parquet(HERE.parents[1]/'p2/results/scores.parquet')
    col='T69' if 'T69' in tree else 'T'
    cands=cands.merge(tree[KEY+[col]],on=KEY,validate='1:1').merge(industry,on=KEY,validate='1:1')
    rets={n:raw/raw.shift(n)-1 for n in [5,10]}
    ep.ledger.accounts.OUT=CACHE
    market,actions=ep.ledger.setup('flat')
    cov=[];rows=[];plans={}
    for day,g in cands.groupby('signal_date'):
        g=g.sort_values(['R','instrument'],ascending=False).set_index('instrument')
        e=g.entry_idx.iloc[0];k=len(g)//10;m=k//5;top=g.iloc[:k];r=g.iloc[k:2*k]
        core=top.index.difference(top.sort_values(col,kind='stable',ascending=False).index[-m:])
        permitted=edges[(edges.disclosure_date<day)&(edges.active_start<=day)&(edges.active_end>=day)]
        for n in [5,10]:
            ret=rets[n].loc[day];signals=[]
            for s,rr in r.iterrows():
                partners=set(permitted.loc[permitted.supplier.eq(s),'buyer'])|set(permitted.loc[permitted.buyer.eq(s),'supplier'])
                partners.discard(s);peers=g.index[g.l1_name.eq(rr.l1_name)].difference([s])
                links=ret.reindex(sorted(partners)).dropna()
                if not len(links):continue
                controls=peers.difference(sorted(partners))
                controls=[p for p in controls if pd.notna(ret.get(p))]
                order=sorted(controls,key=lambda p:hashlib.sha256(f'4101|{s}|{p}'.encode()).digest())
                if len(order)<len(links):continue
                signals.append((s,links.mean(),ret.reindex(peers).mean(),ret.reindex(order[:len(links)]).mean(),','.join(links.index)))
            z=pd.DataFrame(signals,columns=['instrument','real','sector','pseudo','partners']).set_index('instrument')
            rank=r.index[:m];supported=rank.intersection(z.index);budget=len(supported)
            cov.append((day,n,len(r),len(z),budget,k,len(permitted),len(z)>budget>0))
            for arm in ['base','real','sector','pseudo']:
                picks=rank if arm=='base' or not budget else rank.difference(supported).append(z.sort_values(arm,ascending=False,kind='stable').index[:budget])
                ids=core.append(picks)
                assert len(ids.unique())==k
                plans.setdefault((n,arm),{})[e]=market.symbols.get_indexer(ids)
            if len(z):rows.append(z.reset_index().assign(date=day,lookback=n))
    pd.DataFrame(cov,columns='date lookback reserve supported supported_buy K active_edges discriminable'.split()).to_csv(HERE/'coverage.csv',index=False)
    if rows:pd.concat(rows).to_csv(HERE/'signals.csv',index=False)
    import replay_models as engine
    engine.M=market;engine.ACTIONS=actions
    out=[];orders=[]
    for (n,arm),plan in plans.items():
        for seg,start,end in SEG:
            a,b=market.days.get_indexer([start,end])
            frame,trades=engine.account(arm,plan,10,a,b,seg)
            out.append(frame.assign(lookback=n))
            trades['instrument']=market.symbols[trades.symbol_id]
            trades['date']=market.days[trades.entry_idx]
            orders.append(trades.assign(lookback=n))
    pd.concat(orders).to_parquet(HERE/'net_orders.parquet',index=False,compression='zstd')
    d=pd.concat(out);d.to_parquet(HERE/'daily.parquet',index=False)
    months=[]
    for (n,arm,seg),g in d.groupby(['lookback','arm','segment']):
        z=g.set_index('date').nav
        z=z.groupby(z.index.to_period('M')).last().pct_change().iloc[1:-1]
        months.append(z.rename('net').rename_axis('month').reset_index().assign(lookback=n,arm=arm,segment=seg))
    pd.concat(months).to_csv(HERE/'months.csv',index=False)
if __name__=='__main__':main()
