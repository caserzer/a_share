"""Predeclared risk-matched filters and transparent qfq-unit portfolio diagnostic."""
from core import *


def selection(frame):
    g=frame.copy().reset_index(drop=True)
    # Fixed current-month terciles; ties stay together, not ranked using outcomes.
    for col,name in [('log_cap','size_bin'),('vol63','risk_bin')]:
        cuts=g[col].quantile([1/3,2/3]).to_numpy();g[name]=np.searchsorted(cuts,g[col].to_numpy(),side='right')
    g['stratum']=g.board.astype(str)+':'+g.size_bin.astype(str)+':'+g.risk_bin.astype(str)
    chosen={s:np.zeros(len(g),bool) for s in ['S0','S1','S2']}
    for _,part in g.groupby('stratum',sort=True):
        keep=len(part)-int(np.floor(C['portfolio']['excluded_fraction']*len(part)))
        hashed=tie_keys(part.instrument)
        order0=np.argsort(hashed)
        order1=np.lexsort((hashed,part.p_r.to_numpy()))
        order2=np.lexsort((hashed,part.p_vf.to_numpy()))
        for name,order in [('S0',order0),('S1',order1),('S2',order2)]:chosen[name][part.index[order[:keep]]]=True
    return g,chosen


def execute_rebalance(holdings,cash,quotes,marked,target,cost):
    nav=cash+float(np.dot(holdings,marked));desired=nav*target
    current=holdings*marked
    sell=np.minimum(holdings,np.maximum(current-desired,0)/np.where(marked>0,marked,1))
    sell=np.where(np.isfinite(quotes)&(quotes>0),sell,0)
    sale=float(np.dot(sell,np.nan_to_num(quotes)));cash+=sale*(1-cost);holdings=holdings-sell
    need=np.maximum(desired-holdings*marked,0)
    need=np.where(np.isfinite(quotes)&(quotes>0),need,0)
    budget=min(float(need.sum()),cash/(1+cost))
    allocation=need/need.sum()*budget if need.sum()>0 else np.zeros_like(need)
    bought=np.divide(allocation,quotes,out=np.zeros_like(allocation),where=np.isfinite(quotes)&(quotes>0))
    holdings=holdings+bought;cash-=budget*(1+cost)
    assert cash>=-1e-10 and (holdings>=-1e-12).all()
    return holdings,max(cash,0),sale+budget,(sale+budget)*cost


def simulate(prices,calendar,targets,cost):
    n=prices.shape[1];hold=np.zeros(n);cash=1.;last=np.zeros(n);records=[]
    for date in calendar:
        quote=prices.loc[date].to_numpy(float);valid=np.isfinite(quote)&(quote>0);last[valid]=quote[valid]
        traded=fees=0.
        if date in targets:hold,cash,traded,fees=execute_rebalance(hold,cash,quote,last,targets[date],cost)
        nav=cash+float(np.dot(hold,last));equity=nav-cash
        stale=float(np.dot(hold[~valid],last[~valid]));assert nav>0
        records.append(dict(date=date,nav=nav,cash=cash,equity_fraction=equity/nav,holdings=int((hold>1e-12).sum()),
            stale_value_fraction=stale/nav,turnover_notional=traded,transaction_cost=fees))
    f=pd.DataFrame(records);f['daily_return']=f.nav.pct_change(fill_method=None);f.loc[0,'daily_return']=f.nav.iloc[0]-1
    f['drawdown']=f.nav/f.nav.cummax().clip(lower=1)-1
    return f


def es(values,alpha=.05):
    x=np.asarray(values,float);x=x[np.isfinite(x)]
    return float(np.sort(x)[:max(1,int(np.ceil(len(x)*alpha)))].mean()) if len(x) else np.nan


def main():
    full=pd.read_parquet(CACHE/'all_predictions.parquet')
    a=full[full.model.eq('M_R')].copy().rename(columns={'p_loss20':'p_r'})
    b=full[full.model.eq('M_VF')][['date','instrument','p_loss20']].rename(columns={'p_loss20':'p_vf'})
    base=a.merge(b,on=['date','instrument'],validate='one_to_one')
    calendar_path=TOPIC/'data/qlib/cn_data_pit_largecap/calendars/day.txt'
    calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(calendar_path,header=None)[0]))
    instruments=sorted(base.instrument.unique());priceframes=[]
    for stock in instruments:
        prices=pd.read_csv(TOPIC/f'data/raw/akshare/day/qfq/{stock}.csv',usecols=['date','close'],parse_dates=['date']).set_index('date').close
        priceframes.append(prices.rename(stock))
    prices=pd.concat(priceframes,axis=1).reindex(calendar).reindex(columns=instruments)
    targets={name:{} for name in ['S0','S1','S2']};selections=[];cohorts=[];exposure=[];opportunity=[]
    for date,g in base.groupby('date',sort=True):
        group,keep=selection(g);idx=calendar.searchsorted(date,side='right')
        if idx>=len(calendar):continue
        trade_date=calendar[idx]
        sample_sd={c:float(group[c].std()) for c in ['log_cap','vol63']}
        baseline_industry=group.loc[keep['S0'],'industry_sector'].value_counts(normalize=True)
        selected_counts=[]
        for strategy,mask in keep.items():
            selected=group.loc[mask];excluded=group.loc[~mask];selected_counts.append(len(selected))
            w=pd.Series(0.,index=instruments);w.loc[selected.instrument]=1/len(selected);targets[strategy][trade_date]=w.to_numpy()
            selections.append(group[['date','instrument','stratum']].assign(strategy=strategy,selected=mask))
            known=selected.actual.notna();miss=selected.label_end.notna()&selected.actual.isna();obs=selected.loc[known,'actual']
            if len(obs):
                events=int((obs<-.2).sum());mature=int((selected.label_end.notna()).sum())
                cohorts.append(dict(date=date,strategy=strategy,target_holdings=len(selected),observed=len(obs),missing=int(miss.sum()),events=events,loss20_rate=float((obs<-.2).mean()),
                    event_rate_lower=events/mature,event_rate_upper=(events+int(miss.sum()))/mature,cohort_return=float(obs.mean()),stock_tail_es05=es(obs)))
            # Realized return used only for diagnostics after prediction-time selection.
            if excluded.actual.notna().any():
                opportunity.append(dict(date=date,strategy=strategy,excluded_rows=len(excluded),observed=int(excluded.actual.notna().sum()),
                    excluded_mean_return=float(excluded.actual.mean()),excluded_gain20_rate=float((excluded.loc[excluded.actual.notna(),'actual']>.2).mean()),
                    selected_mean_return=float(selected.actual.mean())))
            industry=selected.industry_sector.value_counts(normalize=True);sectors=industry.index.union(baseline_industry.index)
            tv=float((industry.reindex(sectors,fill_value=0)-baseline_industry.reindex(sectors,fill_value=0)).abs().sum()/2)
            e=dict(date=date,strategy=strategy,target_holdings=len(selected),target_equity=1.,industry_total_variation_vs_s0=tv,industry_unknown_fraction=float(selected.industry_sector.eq('UNKNOWN').mean()),industry_stale_fraction=float(selected.industry_stale.fillna(1).mean()))
            for col in ['log_cap','vol63']:
                e[col+'_mean']=float(selected[col].mean());e[col+'_standardized_vs_s0']=(selected[col].mean()-group.loc[keep['S0'],col].mean())/sample_sd[col] if sample_sd[col]>0 else 0.
            exposure.append(e)
        assert len(set(selected_counts))==1
        counts={name:group.loc[mask].groupby('stratum').size() for name,mask in keep.items()}
        pd.testing.assert_series_equal(counts['S0'],counts['S1']);pd.testing.assert_series_equal(counts['S0'],counts['S2'])
    pd.concat(selections,ignore_index=True).to_parquet(CACHE/'portfolio_selections.parquet',index=False)
    pd.DataFrame(cohorts).to_csv(OUT/'portfolio_cohort_scores.csv',index=False);pd.DataFrame(exposure).to_csv(OUT/'portfolio_exposures.csv',index=False);pd.DataFrame(opportunity).to_csv(OUT/'portfolio_opportunity_cost.csv',index=False)
    start=min(targets['S0']);days=calendar[calendar>=start];daily=[];summary=[];monthly=[]
    for bps in [C['portfolio']['cost_bps'],C['portfolio']['cost_sensitivity_bps']]:
        for strategy in targets:
            f=simulate(prices,days,targets[strategy],bps/10000);f['strategy']=strategy;f['cost_bps']=bps;daily.append(f)
            returns=f.daily_return.to_numpy();years=len(f)/252;annual=float(f.nav.iloc[-1]**(1/years)-1);vol=float(np.std(returns,ddof=1)*np.sqrt(252))
            monthnav=f.set_index('date').nav.resample('ME').last();monthret=monthnav.pct_change(fill_method=None);monthret.iloc[0]=monthnav.iloc[0]-1
            for date,value in monthret.items():monthly.append(dict(date=date,strategy=strategy,cost_bps=bps,return_value=float(value)))
            summary.append(dict(strategy=strategy,cost_bps=bps,cumulative_return=float(f.nav.iloc[-1]-1),annual_return=annual,annual_vol=vol,sharpe_zero_cash=float(np.mean(returns)*252/vol) if vol else np.nan,
                max_drawdown=float(f.drawdown.min()),daily_es05=es(returns),monthly_es05=es(monthret),mean_equity_fraction=float(f.equity_fraction.mean()),minimum_equity_fraction=float(f.equity_fraction.min()),
                mean_holdings=float(f.holdings.mean()),maximum_stale_fraction=float(f.stale_value_fraction.max()),mean_stale_fraction=float(f.stale_value_fraction.mean()),
                turnover_total_nav_multiple=float((f.turnover_notional/f.nav).sum()),transaction_cost_nav_multiple=float((f.transaction_cost/f.nav).sum()),days=len(f)))
    daily=pd.concat(daily,ignore_index=True);daily.to_csv(OUT/'portfolio_daily.csv',index=False);pd.DataFrame(summary).to_csv(OUT/'portfolio_summary.csv',index=False);monthly=pd.DataFrame(monthly);monthly.to_csv(OUT/'portfolio_monthly.csv',index=False)
    intervals=[]
    for bps,g in monthly.groupby('cost_bps'):
        for left,right in [('S1','S0'),('S2','S0'),('S2','S1')]:
            diff=paired(g[g.strategy.eq(left)],g[g.strategy.eq(right)],'return_value')
            for block in [6,12]:intervals.append(dict(comparison=left+'-'+right,cost_bps=bps,metric='monthly_return',**ci(diff,block)))
    pd.DataFrame(intervals).to_csv(OUT/'portfolio_intervals.csv',index=False)
    main=daily[daily.cost_bps.eq(10)].pivot(index='date',columns='strategy',values='equity_fraction')
    maxcashdiff=float((main.max(axis=1)-main.min(axis=1)).max())
    write_json(OUT/'portfolio_audit.json',dict(target_counts_equal_within_every_stratum=True,target_equity_all_one=True,no_future_outcome_selection=True,next_session_close_execution=True,
        maximum_daily_equity_fraction_difference=maxcashdiff,equity_exposure_within_tolerance=maxcashdiff<=C['portfolio']['cash_exposure_tolerance'],
        stale_valuation_present=bool(daily.stale_value_fraction.max()>0),industry_exactly_matched=False,industry_attribution_available=True,
        limitation='qfq-unit diagnostic; missing-price holdings last observed valuation may hide losses; no exact delisting, corporate-action, tradability or industry-neutral economic confirmation'))
    print(pd.DataFrame(summary).to_string(index=False),flush=True)

if __name__=='__main__':main()
