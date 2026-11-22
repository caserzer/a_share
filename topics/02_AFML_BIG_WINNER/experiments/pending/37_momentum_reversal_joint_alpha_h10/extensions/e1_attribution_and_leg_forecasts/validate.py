"""Independent checks on calendar lags, match roles, frozen inputs and gating."""
from settings import *


def run():
    for path,expected in json.loads((D/'inputs.json').read_text()).items():
        assert sha(path)==expected,path
    f=pd.read_csv(D/'features.csv',parse_dates=['signal_date','exit_date']).set_index('signal_date')
    labels=f[['d10_ex','red_ex']].copy()
    labels.index=pd.DatetimeIndex(f.exit_date)
    labels=labels[labels.index.notna()].sort_index()
    assert labels.index.is_unique
    roll=labels.rolling(6,min_periods=6).mean()
    aligned=roll.reindex(f.index,method='ffill')
    np.testing.assert_allclose(aligned.to_numpy(),f[['prev_d10','prev_red']].values,equal_nan=True,atol=1e-12)
    p=pd.read_csv(D/'predictions.csv',parse_dates=['signal_date','exit_date','cutoff'])
    assert not p.duplicated(['signal_date','spec']).any() and p.groupby('signal_date').size().eq(5).all()
    assert (p.cutoff<=p.signal_date).all()
    cal=f.loc[p.signal_date.min():,['exit_date']]
    weight=p.pivot(index='signal_date',columns='spec',values='weight').reindex(cal.index)
    due=weight.ffill().fillna(.5)
    due['signal_available']=weight.market.notna()
    due.join(cal).to_csv(D/'target_calendar.csv')
    pairs=pd.read_parquet(D/'pairs.parquet')
    ts=pd.read_parquet(WEAK/'results/targets.parquet').set_index(['signal_date','instrument'])
    keys=['signal_date','other','control_rev']
    for col in ['e1_avoided','other_avoided']:
        assert not pairs.duplicated(keys+[col]).any()
    for r in pairs.itertuples():
        a=ts.loc[r.signal_date,r.e1_avoided]
        b=ts.loc[r.signal_date,r.other_avoided]
        assert a.E1_low and not b.E1_low and not a[r.other+'_low'] and b[r.other+'_low']
        assert a.industry==b.industry==r.industry and r.weight_ratio<=1.25+1e-12
        assert not r.control_rev or a.REV_low==b.REV_low
        assert np.isclose(r.budget,min(a.base-a.E1_target,b.base-b[r.other+'_target']))
    # Verify decomposition again with aggregated sector money and its weighted reference return.
    stocks=pd.read_parquet(D/'stock_attribution.parquet')
    stocks['w']=stocks.base.where(stocks.method.ne('equal'),1.)
    stocks['weighted_ret']=stocks.w*stocks.ret
    groups=stocks.groupby(['signal_date','method','industry']).agg(active=('transfer','sum'),w=('w','sum'),r=('weighted_ret','sum'))
    by_sector=(groups.active*groups.r/groups.w).groupby(level=[0,1]).sum()
    obs=pd.read_csv(D/'industry_by_date.csv',parse_dates=['signal_date']).set_index(['signal_date','method'])
    np.testing.assert_allclose(by_sector,obs.between.reindex(by_sector.index),atol=1e-12)
    assert np.allclose(obs.total,obs.between+obs.within,atol=1e-12)
    tests=pd.read_csv(D/'forecast_summary.csv').query("scope=='primary' and spec in ['plus_d10','plus_red','both']")
    valid=tests[(tests.mae_gain>0)&(tests.ex_top2>0)]
    gate=json.loads((D/'gate.json').read_text())
    assert (gate['selected'] is None)==valid.empty
    ac=pd.read_csv(D/'account_review.csv')
    assert bool(ac.model.eq('candidate').any())==(gate['selected'] is not None)
    folds=pd.DataFrame(json.loads((D/'folds.json').read_text()))
    model_stats=[]
    for r in folds.itertuples():
        for leg,coefs in zip(['d10','red'],r.coef):
            for field,val in zip(r.fields,coefs):
                model_stats.append(dict(quarter=r.quarter,cutoff=r.cutoff,model=r.spec,leg=leg,feature=field,
                                        slope_per_training_sd=val))
    pd.DataFrame(model_stats).to_csv(D/'coefficients.csv',index=False)
    dump(D/'validation.json',dict(verified_files=len(json.loads((D/'inputs.json').read_text())),
         matched_pair_rows=len(pairs),verified_sector_portfolios=len(obs),forecast_quarters=folds.quarter.nunique(),
         forecasts=len(p),matched_calendar=True,independent_lag_reconstruction=True,
         candidate_account_started=gate['selected'] is not None,control_account_max_error=ac.ledger_error.max()))


if __name__=='__main__':
    run()
