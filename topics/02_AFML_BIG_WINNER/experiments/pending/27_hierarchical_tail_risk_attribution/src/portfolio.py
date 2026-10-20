"""P4: exact published-industry target neutrality with matching risk styles and liquidity caps."""
from core import *


def select(frame):
    f=risk_cells(frame.copy()).reset_index(drop=True)
    f=f[f.log_money21>=np.log1p(C['portfolio']['minimum_past21_money_cny'])].copy().reset_index(drop=True)
    kept={s:np.zeros(len(f),bool) for s in ['S0','S1','S2']}
    for _,g in f.groupby('risk_cell',sort=True):
        keep=len(g) if g.industry_id.iloc[0]=='UNKNOWN' else len(g)-int(np.floor(len(g)*C['portfolio']['excluded_fraction']))
        hashed=tie(g.instrument);orders={'S0':np.argsort(hashed),'S1':np.lexsort((hashed,g.p_base)),'S2':np.lexsort((hashed,g.p_full))}
        for name,order in orders.items():kept[name][g.index[order[:keep]]]=True
    counts=[f.loc[mask].groupby('risk_cell').size() for mask in kept.values()]
    assert all(counts[0].equals(s) for s in counts[1:]);return f,kept


def trade(hold,cash,quotes,marked,target,capacity,cost):
    nav=cash+float(np.dot(hold,marked));desired=nav*target;valid=np.isfinite(quotes)&(quotes>0)
    requested_sell=np.maximum(hold*marked-desired,0);sell_value=np.minimum(requested_sell,np.maximum(capacity,0))
    sell=np.divide(sell_value,marked,out=np.zeros_like(hold),where=(marked>0)&valid);sell=np.minimum(sell,hold)
    revenue=float(np.dot(sell,np.nan_to_num(quotes)));cash+=revenue*(1-cost);hold=hold-sell
    requested_buy=np.maximum(desired-hold*marked,0);need=np.where(valid,np.minimum(requested_buy,np.maximum(capacity,0)),0)
    budget=min(float(need.sum()),cash/(1+cost));allocation=need/need.sum()*budget if need.sum()>0 else np.zeros_like(need)
    bought=np.divide(allocation,quotes,out=np.zeros_like(hold),where=valid);hold+=bought;cash-=budget*(1+cost)
    assert cash>=-1e-10 and (hold>=-1e-12).all()
    limited=int(((requested_sell>capacity+1e-12)|(requested_buy>capacity+1e-12)).sum())
    return hold,max(float(cash),0.),revenue+budget,(revenue+budget)*cost,limited


def simulate(prices,money,calendar,targets,cost,capture_weights=False):
    hold=np.zeros(prices.shape[1]);cash=1.;last=np.zeros(prices.shape[1]);rows=[];weight_rows=[]
    for date in calendar:
        quote=prices.loc[date].to_numpy(float);valid=np.isfinite(quote)&(quote>0);last[valid]=quote[valid]
        traded=fees=0.;limited=0
        if date in targets:
            capacity=np.nan_to_num(money.loc[date].to_numpy(float))*C['portfolio']['participation_cap']/C['portfolio']['capital_cny']
            hold,cash,traded,fees,limited=trade(hold,cash,quote,last,targets[date],capacity,cost)
        nav=cash+float(np.dot(hold,last));assert nav>0
        rows.append(dict(date=date,nav=nav,cash=cash,equity_fraction=(nav-cash)/nav,holdings=int((hold>1e-12).sum()),stale_fraction=float(np.dot(hold[~valid],last[~valid]))/nav,turnover=traded/nav,fees=fees/nav,liquidity_limited_orders=limited))
        if capture_weights:weight_rows.append(hold*last/nav)
    f=pd.DataFrame(rows);f['daily_return']=f.nav.pct_change(fill_method=None);f.loc[0,'daily_return']=f.nav.iloc[0]-1;f['drawdown']=f.nav/f.nav.cummax().clip(lower=1)-1
    return (f,np.stack(weight_rows)) if capture_weights else f


def es(values):
    x=np.asarray(values,float);x=x[np.isfinite(x)];return float(np.sort(x)[:max(1,int(np.ceil(len(x)*.05)))].mean()) if len(x) else np.nan


def drawdown_duration(values):
    longest=current=0
    for v in values:
        current=current+1 if v< -1e-10 else 0;longest=max(longest,current)
    return longest


def main():
    assert json.loads((OUT/'p3_gate.json').read_text())['passed'];assert json.loads((OUT/'controls.json').read_text())['all_passed']
    full=pd.read_parquet(CACHE/'all_predictions.parquet');full=full[full.horizon.eq(6)]
    base=full[full.model.eq('M_RMI')].copy().rename(columns={'probability':'p_base'});add=full[full.model.eq('M_RMIVF')][['date','instrument','probability']].rename(columns={'probability':'p_full'})
    reference=base.merge(add,on=['date','instrument'],validate='one_to_one');instruments=sorted(reference.instrument.unique());calendar=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(TOPIC/'data/qlib/cn_data_pit_largecap/calendars/day.txt',header=None)[0]))
    price=[];money=[]
    for stock in instruments:
        b=pd.read_csv(TOPIC/f'data/raw/akshare/day/qfq/{stock}.csv',usecols=['date','close','money'],parse_dates=['date']).set_index('date').reindex(calendar)
        price.append(b.close.rename(stock));money.append(b.money.rolling(21,min_periods=21).mean().shift(1).rename(stock))
    price=pd.concat(price,axis=1).reindex(columns=instruments);money=pd.concat(money,axis=1).reindex(columns=instruments)
    targets={s:{} for s in ['S0','S1','S2']};lists=[];cohorts=[];exposures=[];opportunities=[];industry_weights=[]
    for date,g in reference.groupby('date'):
        f,keep=select(g);assert len(f);trade_idx=calendar.searchsorted(date,side='right')
        if trade_idx>=len(calendar):continue
        for strategy,mask in keep.items():
            selected=f[mask];excluded=f[~mask];weights_=pd.Series(0.,index=instruments);weights_.loc[selected.instrument]=1/len(selected);targets[strategy][calendar[trade_idx]]=weights_.to_numpy()
            lists.append(f[['date','instrument','industry_id','risk_cell']].assign(strategy=strategy,selected=mask))
            known=selected.actual.notna();events=int((selected.loc[known,'actual']<-.2).sum());mature=selected.label_end.notna();n=int(mature.sum());missing=int((mature&~known).sum())
            if known.any():cohorts.append(dict(date=date,strategy=strategy,holdings=len(selected),known=int(known.sum()),events=events,missing=missing,loss_rate=float((selected.loc[known,'actual']<-.2).mean()),cohort_return=float(selected.actual.mean()),event_rate_lower=events/n,event_rate_upper=(events+missing)/n,stock_tail_es05=es(selected.actual)))
            iw=selected.industry_id.value_counts(normalize=True)
            for industry,weight in iw.items():industry_weights.append(dict(date=date,strategy=strategy,industry_id=industry,target_weight=weight))
            e=dict(date=date,strategy=strategy,holdings=len(selected),target_equity=1.,pool_before_liquidity=len(g),tradable_proxy_rows=len(f),unknown_industry_rows=int(selected.industry_id.eq('UNKNOWN').sum()),stale_industry_fraction=float(selected.industry_stale.mean()))
            for col in ['log_cap','vol63']:
                mean0=f.loc[keep['S0'],col].mean();scale=f[col].std();e[col+'_mean']=float(selected[col].mean());e[col+'_std_diff_vs_s0']=float((selected[col].mean()-mean0)/scale) if scale>0 else 0.
            exposures.append(e)
            if excluded.actual.notna().any():opportunities.append(dict(date=date,strategy=strategy,excluded_rows=len(excluded),observed=int(excluded.actual.notna().sum()),excluded_mean_return=float(excluded.actual.mean()),excluded_gain20_rate=float((excluded.loc[excluded.actual.notna(),'actual']>.2).mean()),selected_mean_return=float(selected.actual.mean())))
    selected=pd.concat(lists,ignore_index=True);selected.to_parquet(CACHE/'portfolio_selections.parquet',index=False);pd.DataFrame(cohorts).to_csv(OUT/'portfolio_cohorts.csv',index=False);pd.DataFrame(exposures).to_csv(OUT/'portfolio_exposures.csv',index=False);pd.DataFrame(industry_weights).to_csv(OUT/'portfolio_industry_targets.csv',index=False);pd.DataFrame(opportunities).to_csv(OUT/'portfolio_opportunity_cost.csv',index=False)
    iw=pd.DataFrame(industry_weights).pivot_table(index=['date','industry_id'],columns='strategy',values='target_weight',fill_value=0)
    np.testing.assert_allclose(iw.S0,iw.S1,atol=1e-14);np.testing.assert_allclose(iw.S0,iw.S2,atol=1e-14)
    days=calendar[calendar>=min(targets['S0'])];daily=[];summary=[];monthly=[]
    for cost in C['portfolio']['cost_bps']:
        for strategy in targets:
            f,w=simulate(price,money,days,targets[strategy],cost/10000,capture_weights=True);f['strategy']=strategy;f['cost_bps']=cost;daily.append(f)
            np.savez_compressed(CACHE/f'portfolio_{strategy}_{cost}_weights.npz',weights=w,dates=days.to_numpy(),instruments=np.array(instruments))
            ret=f.daily_return.to_numpy();vol=float(np.std(ret,ddof=1)*np.sqrt(252));monthnav=f.set_index('date').nav.resample('ME').last();mr=monthnav.pct_change(fill_method=None);mr.iloc[0]=monthnav.iloc[0]-1
            monthly.extend(dict(strategy=strategy,cost_bps=cost,date=date,return_value=float(v)) for date,v in mr.items())
            summary.append(dict(strategy=strategy,cost_bps=cost,cumulative_return=float(f.nav.iloc[-1]-1),annual_return=float(f.nav.iloc[-1]**(252/len(f))-1),annual_vol=vol,sharpe_zero_cash=float(np.mean(ret)*252/vol),daily_es05=es(ret),monthly_es05=es(mr),max_drawdown=float(f.drawdown.min()),drawdown_duration_sessions=drawdown_duration(f.drawdown),mean_equity=float(f.equity_fraction.mean()),min_equity=float(f.equity_fraction.min()),max_stale=float(f.stale_fraction.max()),mean_holdings=float(f.holdings.mean()),turnover=float(f.turnover.sum()),fees=float(f.fees.sum()),liquidity_limited_orders=int(f.liquidity_limited_orders.sum())))
    daily=pd.concat(daily,ignore_index=True);daily.to_csv(OUT/'portfolio_daily.csv',index=False);monthly=pd.DataFrame(monthly);monthly.to_csv(OUT/'portfolio_monthly.csv',index=False);pd.DataFrame(summary).to_csv(OUT/'portfolio_summary.csv',index=False)
    interval=[]
    for metric in ['loss_rate','cohort_return']:
        c=pd.DataFrame(cohorts)
        for a,b in [('S1','S0'),('S2','S0'),('S2','S1')]:
            for block in [6,12]:interval.append(dict(comparison=a+'-'+b,metric=metric,cost_bps=0,**ci(paired(c[c.strategy.eq(a)],c[c.strategy.eq(b)],metric),block)))
    for cost,g in monthly.groupby('cost_bps'):
        for a,b in [('S1','S0'),('S2','S0'),('S2','S1')]:
            for block in [6,12]:interval.append(dict(comparison=a+'-'+b,metric='monthly_return',cost_bps=cost,**ci(paired(g[g.strategy.eq(a)],g[g.strategy.eq(b)],'return_value'),block)))
    pd.DataFrame(interval).to_csv(OUT/'portfolio_intervals.csv',index=False)
    table=daily[daily.cost_bps.eq(10)].pivot(index='date',columns='strategy',values='equity_fraction');cashgap=float((table.max(axis=1)-table.min(axis=1)).max())
    write_json(OUT/'p4_portfolio_audit.json',dict(phase='P4',completed=True,target_published_industry_weights_exactly_equal=True,target_risk_cell_counts_exactly_equal=True,target_equity_one=True,
        maximum_daily_equity_difference=cashgap,equity_difference_within_tolerance=cashgap<=C['portfolio']['equity_difference_tolerance'],stale_valuation_present=bool(daily.stale_fraction.max()>0),
        liquidity_cap_uses_only_previous_session_rolling_money=True,next_session_close_execution=True,future_outcome_selection=False,
        limitations=['published classification may be stale or unknown','realized industry weights drift between rebalances','missing quotes and delisting settlements','qfq-unit price proxy; not exact executable total return']))
    print(pd.DataFrame(summary).to_string(index=False),flush=True)

if __name__=='__main__':main()
