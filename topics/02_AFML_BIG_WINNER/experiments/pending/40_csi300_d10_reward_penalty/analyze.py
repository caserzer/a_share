"""Paired metrics use whole portfolios. All contributions are per opening NAV."""
import json
import numpy as np
import pandas as pd
from train import OUT, ARMS, PRIVATE, KEY

PAIRS = [('both','penalty'),('reward','baseline'),('both','baseline'),('penalty','baseline'),
         ('double_reward','both'),('graded','both'),('magnitude','both'),
         ('graded','baseline'),('magnitude','baseline')]


def save(name, rows):
    pd.DataFrame(rows).to_csv(OUT/(name+'.csv'), index=False)


def interval(a):
    rng = np.random.default_rng(4001)
    starts = rng.integers(len(a),size=(10000,(len(a)+2)//3,1))
    draws = (starts+np.arange(3))%len(a)
    return np.quantile(a[draws.reshape(10000,-1)[:,:len(a)]].mean(axis=1),[.025,.975])


def main():
    def read(name):
        return pd.read_parquet(OUT/(name+'.parquet'))
    w, daily, pos, rank, cov = map(read, ['windows','daily','positions','rankings','coverage'])
    days = pd.read_parquet(PRIVATE/'market.parquet',columns=[]).index
    data = json.loads((PRIVATE/'net_excess_20261116/H00300.CSI.json').read_text())['data']
    index = pd.DataFrame(data['items'],columns=data['fields'])
    index = index.set_index(pd.to_datetime(index.trade_date)).close
    w['gross'] = w.net+w.fee
    w['signal_date'] = days[w.entry_idx-1]
    pos['bucket'] = pos.decile.fillna(0).astype(int)
    ms = ['scope','arm']
    tab = pos.groupby(ms+['bucket']).agg(seats=('target','sum'),capital=('weight','sum'),
                                          gross=('gross','sum'),fee=('fee','sum')).reset_index()
    n = cov.groupby(ms).size()
    count = n.reindex(pd.MultiIndex.from_frame(tab[ms])).to_numpy()
    tab['weight_pct'] = 100*tab.capital/count
    tab['gross_bp'] = 10000*tab.gross/count
    tab['fee_bp'] = 10000*tab.fee/count
    save('decile_flows',tab)
    cash = cov.groupby(ms).agg(windows=('seats','size'),seats=('seats','sum'),actual=('actual','mean'),
                                unfilled=('unfilled_seats','sum'),unfilled_target=('unfilled_target_weight','mean'),
                                cash=('cash','mean')).reset_index()
    save('execution_coverage',cash)
    seats = pos.groupby(ms+['signal_date']).target.transform('sum')
    pos['target_weight'] = pos.target.astype(float)/seats
    ind = pos.groupby(ms+['industry'])[['weight','target_weight']].sum().reset_index()
    ind['mean_target_weight'] = ind.target_weight/n.reindex(pd.MultiIndex.from_frame(ind[ms])).to_numpy()
    ind['mean_weight'] = ind.weight/n.reindex(pd.MultiIndex.from_frame(ind[ms])).to_numpy()
    save('industries',ind)
    winners = rank[rank.decile.eq(10)].groupby(ms+['selected']).h10.agg(
        hits='size',mean='mean',p10=lambda s:s.quantile(.1),median='median',p90=lambda s:s.quantile(.9),maximum='max')
    save('winner_returns',winners.reset_index())
    quality = []
    for (scope,arm,date),g in rank.groupby(ms+['signal_date']):
        top = g[g.selected]
        quality.append(dict(arm=arm,scope=scope,signal_date=date,rankic=g.score.corr(g.h10,'spearman'),
                            eligible=len(g),known=g.h10.count(),seats=len(top),seats_known=top.h10.count(),
                            vol20=top.vol20.mean(),vol20_known=top.vol20.count()))
    quality = pd.DataFrame(quality)
    save('ranking_quality',quality)
    summaries, pairs, months, swaps, stocks, swap_details = [],[],[],[],[],[]
    for (scope,cost),g in w.groupby(['scope','cost']):
        nav = daily[(daily.scope==scope)&(daily.cost==cost)].pivot(index='date',columns='arm',values='nav')
        horizon = days.get_loc(nav.index[-1])-days.get_loc(nav.index[0])
        idx_cagr = (index.at[nav.index[-1]]/index.at[nav.index[0]])**(252/horizon)-1
        monthly_nav = nav.groupby(nav.index.to_period('M')).last()
        mr = monthly_nav/monthly_nav.shift().fillna(1)-1
        for arm,h in g.groupby('arm'):
            v = nav[arm]
            cagr = v.iloc[-1]**(252/horizon)-1
            qq = quality.query('scope==@scope and arm==@arm')
            summaries.append(dict(scope=scope,cost=cost,arm=arm,n=len(h),net_bp=1e4*h.net.mean(),
                                  gross_bp=1e4*h.gross.mean(),fee_bp=1e4*h.fee.mean(),turnover=h.turnover.mean(),
                                  nav=v.iloc[-1],cagr=cagr,mdd=(v/v.cummax().clip(lower=1)-1).min(),
                                  bench_cagr=idx_cagr,excess=cagr-idx_cagr,rankic=qq.rankic.mean(),
                                  label_coverage=qq.known.sum()/qq.eligible.sum(),target_coverage=qq.seats_known.sum()/qq.seats.sum(),
                                  vol20=qq.vol20.mean(),start=nav.index[0],end=nav.index[-1]))
        for arm,ref in PAIRS+[('interaction','factorial')]:
            coeff = {arm:1,ref:-1} if arm!='interaction' else {'both':1,'penalty':-1,'reward':-1,'baseline':1}
            def diff(frame):
                return sum(frame[k]*v for k,v in coeff.items())
            def periods(col):
                return diff(g.pivot(index='entry_idx',columns='arm',values=col))
            arr = periods('net').to_numpy()*1e4
            low,high = interval(arr)
            md = diff(mr).sort_values(ascending=False)
            months.extend(dict(scope=scope,cost=cost,arm=arm,ref=ref,month=str(m),delta_bp=v*1e4) for m,v in md.items())
            def without(k):
                return diff((1+mr.drop(md.index[:k])).prod()-1)*100
            pairs.append(dict(scope=scope,cost=cost,arm=arm,ref=ref,n=len(arr),net_bp=arr.mean(),
                              ci_low=low,ci_high=high,gross_bp=periods('gross').mean()*1e4,
                              fee_bp=periods('fee').mean()*1e4,turnover=periods('turnover').mean(),
                              best3_months=','.join(map(str,md.index[:3])),without_best1_pp=without(1),
                              without_best3_pp=without(3)))
            if arm=='interaction' or cost!='base':
                continue
            pp = pos[pos.scope.eq(scope)]
            stock = pp.groupby(['instrument','arm'])[['gross','fee']].sum().unstack(fill_value=0)
            net = diff(stock['gross']-stock['fee'])*1e4/len(arr)
            stocks.extend(dict(scope=scope,arm=arm,ref=ref,instrument=k,net_delta_bp=v)
                          for k,v in net.sort_values(ascending=False).items())
            rr = rank[rank.scope.eq(scope)&rank.arm.eq(arm)][KEY+['selected','h10','decile']]
            rr = rr.merge(rank[rank.scope.eq(scope)&rank.arm.eq(ref)][KEY+['selected']],on=KEY,suffixes=('','_ref'),validate='1:1')
            changes = rr[rr.selected!=rr.selected_ref].copy()
            for model,flag in [(arm,True),(ref,False)]:
                lookup = pp[pp.arm.eq(model)].set_index(KEY).weight
                mask = changes.selected.eq(flag)
                changes.loc[mask,'weight'] = lookup.reindex(pd.MultiIndex.from_frame(changes.loc[mask,KEY])).to_numpy()
            assert changes.weight.notna().all()
            for date,h in changes.groupby('signal_date'):
                legs = [h[h.selected.eq(flag)] for flag in [True,False]]
                amounts = [s.weight.where(s.h10.notna(),0).sum() for s in legs]
                capital = min(amounts)
                values = [((s.weight*s.h10).sum()/a if a else np.nan) for s,a in zip(legs,amounts)]
                for s,amount in zip(legs,amounts):
                    detail = s.assign(arm=arm,ref=ref,scope=scope,matched_weight=s.weight.where(s.h10.notna(),0)*capital/amount if amount else 0.)
                    swap_details.append(detail)
                swaps.append(dict(scope=scope,arm=arm,ref=ref,signal_date=date,seats=len(legs[0]),matched_weight=capital,
                                  incoming=values[0],outgoing=values[1],delta_gross_bp=1e4*capital*(values[0]-values[1]) if capital else 0,
                                  missing_or_unmatched_weight=sum(s.weight.sum() for s in legs)-2*capital))
    for name,rows in [('accounts',summaries),('paired',pairs),('monthly',months),('swap_windows',swaps),('stock_deltas',stocks)]:
        save(name,rows)
    pd.concat(swap_details).to_parquet(OUT/'swaps.parquet',index=False)


if __name__=='__main__':
    main()
