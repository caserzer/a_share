from experiment import *
from scipy.stats import spearmanr
def main():
    ex=Experiment();m=ex.m;dates=m.days[ex.entries-1];unit=(1.,)*5
    learned={a:{q:tuple(v) for q,v in z.items()} for a,z in json.loads((OUT/'weights.json').read_text()).items()}
    rows=[];opps=[]
    boards=pd.read_parquet(OUT/'rankings.parquet',filters=[('cost','=','base'),('selected','=',True)])
    targets=boards.groupby(['model','signal_date']).instrument.apply(list).to_dict()
    for arm,weights in [('selection',unit),*learned.items()]:
        for scope,ix in [('primary',np.flatnonzero((dates.year>=2021)&(m.days[ex.entries+10]<=pd.Timestamp('2025-03-03')))),('later',np.flatnonzero(m.days[ex.entries]>=pd.Timestamp('2025-03-03')))]:
            books={}
            win,_,chosen,_,_=ex.run(ix[0],ix[-1]+1,arm,weights,detail=True,books=books)
            for t,record,actual in zip(ix,chosen,win):
                e,g=ex.groups[t]; date=dates[t]; names=ex.ids[t]; u,cash,due=books[t];held=u>0
                w=weights[str(date.to_period('Q'))] if isinstance(weights,dict) else weights
                score=ex.calibration(w)[t][0]; picks=record['selected'];k=len(picks)
                raw=names[np.argsort(score,kind='stable')[-k:]]; old=set(names[held[names]])
                target=np.zeros(m.n);common=old&set(raw)&set(picks)
                entrants=set(picks)-old; fresh=set(raw)-old|entrants
                keep=old-common; nold=k-len(entrants)-len(common)
                if common:target[list(common)]=1/k
                if fresh:target[list(fresh)]=len(entrants)/k/len(fresh)
                if keep:target[list(keep)]=nold/k/len(keep)
                np.testing.assert_allclose([target.sum(),target[~held].sum()],[1.,len(entrants)/k],atol=1e-12)
                control=ex.run(t,t+1,arm,weights,detail=True,initial=books[t],uniform=target,liquidate=t==ix[-1])
                uniform_win=control[0][0]
                rows.append(dict(scope=scope,model=arm,signal_date=date,target_incoming=len(entrants)/k,uniform_incoming=target[~held].sum(),actual_traded=actual[3],uniform_traded=uniform_win[3],actual_net=actual[1],uniform_net=uniform_win[1],actual_fee=actual[2],uniform_fee=uniform_win[2]))
                for comp in (['raw','selection','gross'] if arm=='net' else ['raw']):
                    other=raw if comp=='raw' else m.symbols.get_indexer(targets[(comp,date)])
                    # Pair changed seats by score. The equal-notional total is independent of pairing.
                    order={j:v for j,v in zip(names,score)}
                    buys=sorted(set(other)-set(picks),key=order.get,reverse=True); keeps=sorted(set(picks)-set(other),key=order.get,reverse=True)
                    for a,b in zip(buys,keeps):
                        executable=bool(m.buy[e,a] and m.sell[e,b] and held[b])
                        ra=ex.open[e+10,a]/ex.open[e,a]-1;rb=ex.open[e+10,b]/ex.open[e,b]-1
                        opps.append(dict(scope=scope,model=arm,reference=comp,signal_date=date,reference_stock=m.symbols[a],candidate_stock=m.symbols[b],candidate_already_held=bool(held[b]),weight=1/k,same_cash_purchase_tradeable=bool(m.buy[e,a] and m.buy[e,b]),wait_or_switch_tradeable=executable,exit_sellable=bool(m.sell[e+10,a] and m.sell[e+10,b]),entrant_return=ra,retained_return=rb,wait_minus_switch=(rb-ra)/k))
    pd.DataFrame(rows).to_csv(OUT/'matched_incoming.csv',index=False)
    pd.DataFrame(opps).to_parquet(OUT/'opportunity.parquet',index=False)
if __name__=='__main__':main()
