"""Replay identical-date controls; candidate simulation is conditional on the preregistered gate."""
from settings import *
sys.path.insert(0,str(ALLOC))
import simulate as engine


def run():
    winner=json.loads((D/'gate.json').read_text())['selected']
    f=pd.read_csv(ALLOC/'results/signals.csv',parse_dates=['signal_date','entry_date','exit_date']).set_index('signal_date')
    pred=pd.read_csv(D/'predictions.csv',parse_dates=['signal_date'])
    start=pred.signal_date.min()
    h=f[(f.index>=start)&f.exit_date.le(MAIN)].copy()
    engine.accounts.OUT=D
    market=engine.market_with_index(engine.accounts.Market())
    panel=pd.read_parquet(engine.TARGETS)
    weights={'balanced':pd.Series(.5,index=h.index),'old_dynamic':h.allocation}
    if winner:
        weights['candidate']=pred[pred.spec.eq(winner)].set_index('signal_date').weight.reindex(h.index).ffill().fillna(.5)
    anchor=weights.get('candidate',weights['old_dynamic']).mean()
    weights['matched']=pd.Series(anchor,index=h.index)
    rows=[]
    periods=[]
    for name,w in weights.items():
        plan=engine.positions(panel,w)
        for cost,bf,sf in [('main',.001,.002),('zero',0.,0.)]:
            d,o,status=engine.net_account(market,plan,market.days.get_loc(MAIN),'flat',bf,sf)
            assert status['valuation_complete']
            marks,holds,err,close=engine.verify(market,d,o,MAIN,'flat',h,cost)
            assert err<1e-9
            nav=d.nav.iloc[-1]
            dd,*_=engine.drawdown(d.nav.values)
            rows.append(dict(model=name,cost=cost,start=d.date.min(),end=MAIN,n=len(h),terminal=nav,
                cagr=nav**(252/(len(d)-1))-1,drawdown=dd,fees=d.fees.sum(),mean_target=w.mean(),
                terminal_liquidated=status['terminal_liquidated'],ledger_error=err))
            for day,r in h.iterrows():
                closing=nav if r.exit_date==MAIN else marks.at[r.exit_date,'opening']
                periods.append(dict(model=name,cost=cost,signal_date=day,target=w.at[day],
                    actual_d10=marks.at[r.entry_date,'actual_d10'],net=closing/marks.at[r.entry_date,'opening']-1))
            assert np.isclose(np.prod([1+x['net'] for x in periods if x['model']==name and x['cost']==cost]),nav)
    pd.DataFrame(rows).to_csv(D/'account_review.csv',index=False)
    pd.DataFrame(periods).to_csv(D/'account_periods.csv',index=False)
    print(pd.DataFrame(rows).round(5).to_string(index=False))


if __name__=='__main__':
    run()
