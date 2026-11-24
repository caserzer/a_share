"""Exact EP38 narrow-pool replay, with a position-level bridge to each H10 return."""
import numpy as np
import pandas as pd
from train import OUT, ARMS, KEY, PRIVATE, TRACK
from shared import labels, setup, accounts, assign_deciles
from experiment import Experiment


class RankedAccount(Experiment):
    def __init__(self, market, actions, panel):
        self.m, self.actions = market, actions
        self.open, self.close = market.marks['flat']
        self.groups = list(panel.sort_values(KEY).groupby('entry_idx'))
        self.entries = np.array([e for e,_ in self.groups])
        self.ids = [market.symbols.get_indexer(g.instrument) for _,g in self.groups]
        assert all(min(ids)>=0 for ids in self.ids)
        self.y = [g.h10.to_numpy() for _,g in self.groups]

    def calibration(self, arm):
        return [(g[arm].to_numpy(), None, None, None) for _,g in self.groups]


def attribution(account, books, plans, orders, windows, groups, industries):
    m, op = account.m, account.open
    byday = dict(list(orders.groupby('idx')))
    details, coverage = [], []
    for t, plan, (e, net, fee, _) in zip(groups, plans, windows):
        x = e+10
        u, cash, _ = books[t]
        u = u.copy()
        price = np.nan_to_num(op[e])
        nav = cash+u@price
        pnl, fees = np.zeros(m.n), np.zeros(m.n)
        for i in range(e, x+1):
            if i not in [e,x] and i not in byday and not any(j==i for _,_,j in account.actions):
                continue
            held = u>1e-12
            assert np.isfinite(op[i,held]).all()
            mark = np.nan_to_num(op[i])
            pnl += u*(mark-price)
            for old,new,j in account.actions:
                if (i==j or (i==e and e>j)) and u[old]>0:
                    u[new] += u[old]*mark[old]/mark[new]
                    u[old] = 0
            if i in byday and (i<x or t==groups[-1]):
                order = byday[i]
                ids = m.symbols.get_indexer(order.instrument)
                flow = order.net_amount.to_numpy()
                u[ids] += flow/mark[ids]
                fees[ids] += np.where(flow>0, .001*flow, -.002*flow)
            price = mark
            if i==e:
                weight = u*mark/nav
                cash_weight = 1-weight.sum()-fees.sum()/nav
        np.testing.assert_allclose([pnl.sum()/nav,fees.sum()/nav],[net+fee,fee],rtol=0,atol=1e-9)
        chosen = plan['selected']
        signal = plan['signal_date']
        active = np.flatnonzero((abs(pnl)+fees+abs(weight))>1e-12)
        ids = np.union1d(chosen, active)
        selected = np.isin(ids, chosen)
        d = pd.DataFrame(dict(signal_date=signal,instrument=m.symbols[ids],target=selected,
                              weight=weight[ids],gross=pnl[ids]/nav,fee=fees[ids]/nav))
        d['industry'] = industries[signal].reindex(d.instrument).fillna('未知').to_numpy()
        details.append(d)
        coverage.append(dict(signal_date=signal, seats=len(chosen), actual=(weight>1e-10).sum(),
                             unfilled_seats=(weight[chosen]<1e-10).sum(),
                             unfilled_target_weight=(weight[chosen]<1e-10).mean(), cash=cash_weight))
    return pd.concat(details),pd.DataFrame(coverage)


def main():
    scores = pd.read_parquet(OUT/'scores.parquet')
    # Ranking uses all scored rows. Endpoint labels are attached for attribution.
    panel = scores.merge(labels(),on=KEY,how='left',validate='1:1')
    known = panel[panel.h10.notna()]
    for _,g in known.groupby('signal_date'):
        panel.loc[g.index,'decile'] = assign_deciles(g,'h10')
    accounts.OUT = OUT
    market, actions = setup('flat')
    ex = RankedAccount(market, actions, panel)
    industry = pd.read_parquet(PRIVATE/'industry.parquet')
    industry['instrument'] = industry.ts_code.str[-2:]+industry.ts_code.str[:6]
    industries = {}
    for signal in panel.signal_date.unique():
        date = pd.Timestamp(signal).strftime('%Y%m%d')
        active = industry[industry.in_date.le(date)&(industry.out_date.isna()|industry.out_date.gt(date))]
        active = active[['instrument','l1_name']].drop_duplicates()
        industries[signal] = active[~active.instrument.duplicated(False)].set_index('instrument').l1_name
    windows, daily, positions, fills, coverage, ranks = [], [], [], [], [], []
    for arm in ARMS:
        for scope,ix in [('primary',np.arange(100)),('later',np.arange(100,139))]:
            for cost,mul in [('base',1),('zero',0),('double',2)]:
                meta = dict(arm=arm,scope=scope,cost=cost)
                books = {}
                w,d,p,r,o = ex.run(ix[0],ix[-1]+1,'original',arm,.001*mul,.002*mul,True,books=books)
                windows.append(pd.DataFrame(w,columns=['entry_idx','net','fee','turnover']).assign(**meta))
                daily.append(pd.DataFrame(d,columns=['idx','date','nav','cash','buy','sell','fees']).assign(**meta))
                if cost=='base':
                    orders = pd.DataFrame(o,columns=['idx','instrument','net_amount','pretrade_nav'])
                    fills.append(orders.assign(**meta))
                    dt,cov = attribution(ex,books,p,orders,w,ix,industries)
                    positions.append(dt.assign(**meta))
                    coverage.append(cov.assign(**meta))
                    rank_low_first = r.groupby('signal_date').score.rank(method='first')
                    r['rank'] = (r.groupby('signal_date').score.transform('size')+1-rank_low_first).astype(int)
                    ranks.append(r.assign(**meta))
        print(arm,flush=True)
    info = panel[KEY+['decile','vol20','entry_idx']]
    rank = pd.concat(ranks).merge(info,on=KEY,how='left',validate='m:1')
    pos = pd.concat(positions).merge(info,on=KEY,how='left',validate='m:1')
    items = dict(windows=pd.concat(windows),daily=pd.concat(daily),positions=pos,orders=pd.concat(fills),
                 coverage=pd.concat(coverage),rankings=rank)
    for name,data in items.items():
        data.to_parquet(OUT/f'{name}.parquet',index=False)
    ref = pd.read_parquet(TRACK/'results/rankings.parquet',filters=[('model','=','original'),('cost','=','base')])
    check = rank.query('arm=="baseline"').merge(ref,on=KEY,validate='1:1',how='outer',indicator=True)
    assert check._merge.eq('both').all() and (check.selected_x==check.selected_y).all()
    w = items['windows'].query('arm=="baseline"')
    ref = pd.read_parquet(TRACK/'results/windows.parquet',filters=[('model','=','original')])
    check = w.merge(ref,on=['cost','scope','entry_idx'],how='outer',validate='1:1',indicator=True)
    assert len(check)==3*139 and check._merge.eq('both').all()
    for col in ['net','fee','turnover']:
        np.testing.assert_allclose(check[col+'_x'],check[col+'_y'],atol=1e-10,rtol=0)


if __name__=='__main__':
    main()
