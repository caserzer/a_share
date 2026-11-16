"""Common-clock performance, paired uncertainty and independent ledger audit."""
import json
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json,protocol
from summarize import metrics,returns
from evaluate_ranking import block_ci
from q5_rebalance_sensitivity import DEST,CONFIG,MODELS,FREQUENCIES,VALUATIONS,COSTS

def main():
    frozen=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==frozen['config_sha256']
    schedule=pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date','execution_date'])
    anchor=schedule.signal_date.min();price=pd.read_parquet(PRIVATE/'market.parquet').close
    raw=PRIVATE/'net_excess_20261116/H00300.CSI.json';source=json.loads(raw.read_text())['data']
    tr=pd.DataFrame(source['items'],columns=source['fields']);tr['date']=pd.to_datetime(tr.trade_date);tr=tr.set_index('date').sort_index().close
    accounts={};checks=[];inventory=[]
    def check(name,value,details=None):checks.append(dict(check=name,passed=bool(value),details=details))
    receipts=sorted((DEST/'accounts').glob('*.json'));check('81_account_receipts',len(receipts)==81)
    for rp in receipts:
        r=json.loads(rp.read_text());key=r['account'];f=pd.read_csv(rp.with_suffix('.csv'),parse_dates=['date']).set_index('date')
        v,model,freq,cost=r['valuation'],r['model'],r['frequency'],r['cost']
        accounts[(v,model,freq,cost)]=(f,r)
        check(key+'_input_freeze',r['config_sha256']==frozen['config_sha256'] and r['predictions']==frozen['predictions'])
        check(key+'_nav_hash',sha(rp.with_suffix('.csv'))==r['nav_sha256'])
        check(key+'_ledger_hashes',sha(r['orders_path'])==r['orders_sha256'] and sha(r['holdings_path'])==r['holdings_sha256'])
        check(key+'_common_first_execution',f.index.min()==schedule.execution_date.min())
        if r['failures']:check(key+'_stop_at_missing_price',f.index.max()<pd.Timestamp(r['failures'][0]['date']))
        expected=set(schedule.loc[schedule.frequency.eq(freq),'execution_date'])
        orders=pd.read_parquet(r['orders_path']);delta=orders.units_after-orders.units_before
        check(key+'_only_scheduled_trades',set(orders.date).issubset(expected))
        check(key+'_blocked_and_nonmember_orders',not ((delta>1e-10)&(~orders.can_buy|~orders.current_member)).any() and not ((delta< -1e-10)&~orders.can_sell).any())
        bf,sf=np.array(protocol()['costs_bps'][cost])/10000
        orders['buy_value']=delta.clip(lower=0)*orders.qfq_open;orders['sell_value']=(-delta).clip(lower=0)*orders.qfq_open
        g=orders.groupby('date').agg(buy_value=('buy_value','sum'),sell_value=('sell_value','sum'),cash_before=('cash_before','first'),cash_after=('cash_after','first'),pretrade_nav=('pretrade_nav','first'))
        cash_err=g.cash_before+g.sell_value*(1-sf)-g.buy_value*(1+bf)-g.cash_after
        check(key+'_cash_conservation',cash_err.abs().max()<1e-8)
        dates=g.index.intersection(f.index);fees=g.loc[dates,'buy_value']*bf+g.loc[dates,'sell_value']*sf
        check(key+'_actual_fees',np.allclose(f.loc[dates,'fees'],fees,atol=1e-10,rtol=1e-8))
        check(key+'_cash_nonnegative',f.cash_weight.min()>=-1e-9)
        hold=pd.read_parquet(r['holdings_path']);hold['value']=hold.synthetic_units*hold.valuation_close
        hv=hold.groupby('date').value.sum().reindex(f.index,fill_value=0.)
        check(key+'_nav_reconciles_holdings_and_cash',np.allclose(hv+f.nav*f.cash_weight,f.nav,atol=1e-9,rtol=1e-8))
        # Each nonzero Q5 target is equal weight. Do not confuse actual weights with targets after fees/nonfills.
        target=orders.loc[orders.target_weight>0].groupby('date').target_weight.agg(['min','max','sum'])
        check(key+'_equal_target_weights',np.allclose(target['min'],target['max'],atol=1e-12) and np.allclose(target['sum'],1.,atol=1e-10))
        if freq=='1w' and cost=='main' and v!='strict':
            old=pd.read_csv(OUT/'sensitivity'/v/('A_'+model+'.csv'),parse_dates=['date']).set_index('date')
            check(key+'_weekly_matches_existing_frozen_account',f.index.equals(old.index) and np.allclose(f.nav,old.nav,atol=1e-12))
        fail=r['failures'][0] if r['failures'] else {}
        inventory.append(dict(account=key,valuation=v,model=model,frequency=freq,cost=cost,start=f.index.min(),end=f.index.max(),days=len(f),complete=r['completed_to_data_end'],scheduled_rebalances=r['scheduled_rebalances'],executed_rebalance_days=int((f.buy+f.sell>1e-12).sum()),failure_date=fail.get('date'),failure_reason=fail.get('reason'),failure_instruments=fail.get('instruments')))
    inv=pd.DataFrame(inventory);inv.to_csv(DEST/'account_inventory.csv',index=False)
    main_keys=[('suspend_flat',m,q,'main') for m in MODELS for q in FREQUENCIES]
    common_end=min(accounts[k][0].index.max() for k in main_keys)
    cost_end=min(f.index.max() for (v,m,q,c),(f,r) in accounts.items() if v=='suspend_flat')
    proxy_end=min(f.index.max() for (v,m,q,c),(f,r) in accounts.items() if v!='strict')
    start=next(iter(accounts.values()))[0].index.min()
    main_idx=price.loc[start:common_end].index
    model_ends={m:min(accounts[('suspend_flat',m,q,'main')][0].index.max() for q in FREQUENCIES) for m in MODELS}
    periods=dict(model_common_ends=model_ends,signal_close_anchor=anchor,first_execution=start,main_common_end=common_end,main_sessions=len(main_idx),all_cost_flat_common_end=cost_end,all_proxy_common_end=proxy_end,input_end=price.index.max())
    save_json(DEST/'comparison_periods.json',periods)
    summaries=[];annual=[];quarterly=[];curves=[]
    def measure(key,end,scope):
        f,r=accounts[key];v,model,freq,cost=key
        if f.index.max()<end:return
        a=f.loc[:end];n=len(a);buy=a.buy.sum();sell=a.sell.sum();trade_days=a.index[(a.buy+a.sell)>1e-12]
        init=trade_days[0] if len(trade_days) else None
        initial_flow=a.loc[init,'buy']+a.loc[init,'sell'] if init is not None else 0.
        initial_turn=a.loc[init,'executed_turnover'] if init is not None else 0.
        for benchmark,series in [('CSI300_TOTAL_RETURN',tr),('CSI300_PRICE',price)]:
            b=series.reindex(a.index)/series.loc[anchor];assert b.notna().all()
            result=dict(valuation=v,model=model,frequency=freq,cost=cost,scope=scope,benchmark=benchmark,start=anchor,end=end,sessions=n,**metrics(a.nav,b))
            result.update(buy_over_nav=buy,sell_over_nav=sell,annual_one_way_traded_ex_initial=.5*(buy+sell-initial_flow)*252/n,annual_cash_inclusive_turnover_ex_initial=(a.executed_turnover.fillna(0).sum()-initial_turn)*252/n,fees_initial_capital_units=a.fees.sum(),trades=len(trade_days),mean_cash=a.cash_weight.mean(),mean_holdings=a.holdings.mean(),max_unfilled_buy=a.get('unfilled_buy',pd.Series([0.])).max(),max_unfilled_sell=a.get('unfilled_sell',pd.Series([0.])).max(),complete_to_input_end=r['completed_to_data_end'],native_end=f.index.max())
            summaries.append(result)
            if scope=='native':
                rr=returns(a.nav);br=returns(b)
                for freq_tag,dest in [('Y',annual),('Q',quarterly)]:
                    observed=set()
                    for period,g in rr.groupby(rr.index.to_period(freq_tag)):
                        observed.add(str(period));x=(1+g).prod()-1;y=(1+br.loc[g.index]).prod()-1
                        full_days=price.index[price.index.to_period(freq_tag)==period]
                        complete=(g.index.min()==full_days.min() and g.index.max()==full_days.max() and period.end_time.normalize()<=price.index.max())
                        dest.append(dict(valuation=v,model=model,frequency=freq,cost=cost,benchmark=benchmark,period=str(period),start=g.index.min(),end=g.index.max(),sessions=len(g),portfolio_return=x,benchmark_return=y,return_difference=x-y,relative_return=(1+x)/(1+y)-1,period_complete=complete,status='OBSERVED_FULL_PERIOD' if complete else 'OBSERVED_PARTIAL_PERIOD'))
                    for period in pd.period_range(anchor,price.index.max(),freq=freq_tag):
                        if str(period) not in observed:dest.append(dict(valuation=v,model=model,frequency=freq,cost=cost,benchmark=benchmark,period=str(period),sessions=0,status='BLOCKED_AFTER_'+str(r['failures'][0]['date']) if r['failures'] else 'OUTSIDE_ACCOUNT_SCOPE'))
            if scope=='main_common' and v=='suspend_flat' and cost=='main' and benchmark=='CSI300_TOTAL_RETURN':
                for d in a.index:curves.append(dict(model=model,frequency=freq,date=d,nav=a.loc[d,'nav'],benchmark_nav=b.loc[d],relative_nav=a.loc[d,'nav']/b.loc[d]))
    for key,(f,r) in accounts.items():
        measure(key,f.index.max(),'native')
        if key[0]!='strict':
            measure(key,common_end,'main_common')
            measure(key,model_ends[key[1]],'model_common')
            if cost_end!=common_end:measure(key,cost_end,'cost_common')
            if proxy_end not in [common_end,cost_end]:measure(key,proxy_end,'all_proxy_common')
    summary=pd.DataFrame(summaries);summary.to_csv(DEST/'all_metrics.csv',index=False)
    primary=summary.loc[summary.valuation.eq('suspend_flat')&summary.cost.eq('main')&summary.scope.eq('main_common')&summary.benchmark.eq('CSI300_TOTAL_RETURN')]
    primary.to_csv(DEST/'model_frequency_comparison.csv',index=False)
    pd.DataFrame(annual).to_csv(DEST/'annual_performance.csv',index=False);pd.DataFrame(quarterly).to_csv(DEST/'quarterly_performance.csv',index=False)
    pd.DataFrame(curves).to_parquet(DEST/'primary_curves.parquet',index=False)
    pairs=[]
    for model in MODELS:
        base=accounts[('suspend_flat',model,'1w','main')][0].loc[main_idx,'nav'];br=returns(base)
        for frequency in ['2w','1m']:
            nav=accounts[('suspend_flat',model,frequency,'main')][0].loc[main_idx,'nav'];delta=returns(nav)-br;lo,hi=block_ci(delta.to_numpy(),L=65)
            n=len(delta);pa=nav.iloc[-1]**(252/n)-1;pb=base.iloc[-1]**(252/n)-1
            pairs.append(dict(scope='main_common',model=model,comparison=frequency+'_minus_1w',end=common_end,sessions=n,cagr_difference=pa-pb,annualized_mean_daily_return_difference=delta.mean()*252,ci_low=lo*252,ci_high=hi*252,bootstrap_block_sessions=65))
    for model,end in model_ends.items():
        if end==common_end:continue
        idx=price.loc[start:end].index
        base=accounts[('suspend_flat',model,'1w','main')][0].loc[idx,'nav'];br=returns(base)
        for frequency in ['2w','1m']:
            nav=accounts[('suspend_flat',model,frequency,'main')][0].loc[idx,'nav'];delta=returns(nav)-br;lo,hi=block_ci(delta.to_numpy(),L=65);n=len(delta)
            pairs.append(dict(scope='model_common',model=model,comparison=frequency+'_minus_1w',end=end,sessions=n,cagr_difference=nav.iloc[-1]**(252/n)-base.iloc[-1]**(252/n),annualized_mean_daily_return_difference=delta.mean()*252,ci_low=lo*252,ci_high=hi*252,bootstrap_block_sessions=65))
    pd.DataFrame(pairs).to_csv(DEST/'paired_frequency_differences.csv',index=False)
    # Annual table aligned on precisely the same dates across all nine primary accounts.
    ay=[]
    for model in MODELS:
        for frequency in FREQUENCIES:
            a=accounts[('suspend_flat',model,frequency,'main')][0].loc[main_idx];b=tr.reindex(main_idx)/tr.loc[anchor]
            ar=returns(a.nav);br=returns(b)
            for year,g in ar.groupby(ar.index.year):
                own=(1+g).prod()-1;bench=(1+br.loc[g.index]).prod()-1
                ay.append(dict(model=model,frequency=frequency,year=year,start=g.index.min(),end=g.index.max(),sessions=len(g),net_return=own,benchmark_return=bench,excess_difference=own-bench,relative_return=(1+own)/(1+bench)-1))
    pd.DataFrame(ay).to_csv(DEST/'primary_annual.csv',index=False)
    # Exact same prediction payload shared by every frequency/cost/valuation branch.
    check('all_original_input_hashes_unchanged',all(sha(x['path'])==x['sha256'] for x in frozen['inputs']))
    check('primary_has_nine_combinations',len(primary)==9)
    check('cagr_algebra',np.allclose(summary.cagr_difference,summary.cagr-summary.benchmark_cagr) and np.allclose(summary.relative_nav_cagr,(1+summary.cagr)/(1+summary.benchmark_cagr)-1))
    save_json(DEST/'validation.json',dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL',accounts=len(accounts),checks=checks))
    print('COMMON',periods)
    print(primary[['model','frequency','cagr','cagr_difference','relative_nav_cagr','max_drawdown','annual_one_way_traded_ex_initial']].to_string(index=False))
    print('VALIDATION',len(checks),all(c['passed'] for c in checks))
    if not all(c['passed'] for c in checks):print([c for c in checks if not c['passed']]);raise SystemExit(1)
if __name__=='__main__':main()
