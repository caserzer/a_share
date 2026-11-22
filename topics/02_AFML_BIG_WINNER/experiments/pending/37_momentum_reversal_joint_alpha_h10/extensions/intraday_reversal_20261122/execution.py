"""Net same-open executable rollover orders while preserving EP37 expiry and gates."""
import numpy as np
import pandas as pd
from accounts import buy_amounts


def net_account(m, targets, end, mode, bf, sf):
    plans={e:g for e,g in targets.groupby("entry_idx") if e<end}
    om,cm=m.marks[mode]
    units=np.zeros(m.n)
    due=np.full(m.n,-1)
    cash=1.
    daily,orders=[],[]
    fail=None
    for i in range(min(plans),end+1):
        expired=(units>0)&(due<=i)
        fees=buy=sell=saved=0.
        if expired.any() or i in plans or i==end:
            held=units>0
            unknown=held & ~np.isfinite(om[i])
            if unknown.any():
                fail={"date":m.days[i],"reason":"HELD_OPEN_VALUATION_UNKNOWN","instruments":m.symbols[unknown].tolist()}
                break
            price=np.nan_to_num(om[i])
            sold=expired & m.sell[i]
            sales=np.where(sold,units*price,0.)
            # Same full-exit budget as the original contract on this account's current NAV.
            # Include last round's saved cash; this round's savings stay in cash until next buy.
            cash_after_full_sale=cash+sales.sum()*(1-sf)
            retained=(units>0)&~sold
            purchases=np.zeros(m.n)
            if i in plans:
                g=plans[i]
                w=np.zeros(m.n)
                w[m.symbols.get_indexer(g.instrument)]=g.weight
                allow=m.buy[i]&m.members[i-1]&~retained
                purchases=buy_amounts(w*allow,cash_after_full_sale,(units[retained]*price[retained]).sum(),bf)
            overlap=np.minimum(sales,purchases)
            net_buy=purchases-overlap
            net_sell=sales-overlap
            buy,sell=net_buy.sum(),net_sell.sum()
            saved=overlap.sum()*(bf+sf)
            fees=buy*bf+sell*sf
            cash+=sell-buy-fees
            if abs(cash)<1e-12:
                cash=0.
            assert cash>=-1e-10
            units[sold]=0.
            due[sold]=-1
            new=purchases>0
            units[new]=purchases[new]/price[new]
            due[new]=i+10
            for j in np.flatnonzero((sales+purchases)>0):
                orders.append(dict(date=m.days[i],instrument=m.symbols[j],price=price[j],buy=net_buy[j],sell=net_sell[j],
                                   overlap=overlap[j],fee=net_buy[j]*bf+net_sell[j]*sf))
        held=units>0
        mark=om[i] if i==end else cm[i]
        if (~np.isfinite(mark[held])).any():
            fail={"date":m.days[i],"reason":"HELD_VALUATION_UNKNOWN","instruments":m.symbols[held&~np.isfinite(mark)].tolist()}
            break
        nav=cash+np.dot(units[held],mark[held])
        daily.append(dict(date=m.days[i],nav=nav,cash=cash,fees=fees,buy=buy,sell=sell,direct_saving=saved))
    return pd.DataFrame(daily),pd.DataFrame(orders),dict(valuation_complete=fail is None,terminal_liquidated=not held.any() if fail is None else False,failure=fail)
