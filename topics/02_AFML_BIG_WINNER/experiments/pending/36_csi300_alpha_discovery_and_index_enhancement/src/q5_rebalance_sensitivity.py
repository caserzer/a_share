"""Frozen-prediction Q5 rebalance experiment: calendar 1w/2w/1m, no retraining."""
from datetime import datetime, timezone
import json, sys
import numpy as np
import pandas as pd
from common import EP, OUT, PRIVATE, sha, save_json, protocol
from backtest import Inputs, run_account
from suspension_sensitivity import marks
from evaluate_ranking import predictions

RUN='q5_rebalance_20261116'
DEST=OUT/'sensitivity'/RUN
LEDGER=PRIVATE/RUN
CONFIG=EP/'configs'/(RUN+'.json')
MODELS=['E1','E2','E3']
FREQUENCIES=['1w','2w','1m']
VALUATIONS=['strict','suspend_flat','suspend_haircut20']
COSTS=['zero','main','stress']

def scheduled_dates(dates, frequency):
    dates=pd.DatetimeIndex(sorted(pd.unique(dates)))
    if not len(dates):return dates
    if frequency=='1w':return dates
    if frequency=='2w':
        weeks=dates.to_period('W-FRI').asi8
        return dates[(weeks-weeks[0])%2==0]
    if frequency=='1m':
        return dates[~dates.to_period('M').duplicated()]
    raise ValueError('Unknown frequency: '+frequency)

def freeze():
    if CONFIG.exists():raise RuntimeError('Run already frozen; do not overwrite')
    DEST.mkdir(parents=True,exist_ok=True);LEDGER.mkdir(parents=True,exist_ok=True)
    p,consumption=predictions('expanding')
    p=p.loc[p.model_id.isin(MODELS)&p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
    dates=pd.DatetimeIndex(sorted(p.signal_date.unique()))
    for model in MODELS:assert np.array_equal(np.sort(p.loc[p.model_id.eq(model),'signal_date'].unique()),dates.to_numpy())
    days=pd.read_parquet(PRIVATE/'qfq_close.parquet').index
    rows=[]
    for frequency in FREQUENCIES:
        for d in scheduled_dates(dates,frequency):
            i=days.get_loc(d)
            rows.append(dict(frequency=frequency,signal_date=d,execution_date=days[i+1] if i+1<len(days) else pd.NaT))
    pd.DataFrame(rows).to_csv(DEST/'schedule.csv',index=False)
    config=dict(run_id=RUN,created_at=datetime.now(timezone.utc).isoformat(),authorization='User requested E1/E2/E3 Q5 equal-weight, 1-week/2-week/1-month sensitivity and complete report',models=MODELS,scheme='expanding',model_horizon='H10 unchanged',training='reuse all original sealed predictions; no retraining',seed_selection='E1 fixed; E2/E3 fixed equal ensemble of 17/42/2026',frequencies=dict(one_week='all original weekly signal dates',two_weeks='W-FRI calendar-week distance from initial signal week divisible by 2; empty holiday weeks do not reset phase',one_month='first available weekly signal of each natural calendar month, not every 4 weeks and not exact month-end'),initial_signal=str(dates[0]),execution='next actual market-session open; no intervening retargeting or retry of failed orders',portfolio='original Q5 floor(5*ordinal/N)==4, ascending score then instrument; target equal weight; cash and legacy positions retained on failed fills',valuations=VALUATIONS,main_valuation='suspend_flat, continuing preceding disclosed net-excess diagnostic',mark_rule='Only verified full-day suspension permits last observed qfq-close mark for <=20 sessions; haircut20 applies 20% haircut; no invented corporate-action terminal value; strict branch uses actual quotes only',costs_bps=protocol()['costs_bps'],first_build_cost=True,annualization_sessions=252,benchmarks=['CSI300_TOTAL_RETURN closes H00300.CSI','CSI300_PRICE closes 000300.SH'],benchmark_clock='initial signal close, strategy capital in cash until next open; no total-return open imputation',comparison='main common end=min available account end across 9 suspend_flat/main combinations; common across 27 flat cost branches separately; global common across all 54 proxy-valuation branches separately; native intervals separately; no cherry-picked end dates',yearly='calendar returns on common and available intervals; blocked years explicit, no zero returns after failure',uncertainty=dict(method='circular paired time blocks of 65 market sessions, 2000 replicates, seed20261116; interval for annualized mean daily active return, not CAGR',minimum_days=130),selection='report every 3x3 combination; no optimizer chooses model/frequency',prior_weekly_outcomes_seen=True,frequency_results_seen_at_freeze=False,evidence='historical_simulated_oos',forward='FORWARD_PENDING',data_end=str(days.max()),scope_accounts=81)
    save_json(CONFIG,config)
    files=[PRIVATE/(x+'.parquet') for x in ['qfq_open','qfq_close','open','opening_trade_status_v2','daily_members','market']]
    files += [PRIVATE/'limits/daily.parquet',PRIVATE/'suspensions/daily.parquet',PRIVATE/'net_excess_20261116/H00300.CSI.json']
    sources=[EP/'src'/x for x in ['backtest.py','portfolio.py','suspension_sensitivity.py','common.py','q5_rebalance_sensitivity.py']]
    save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),schedule_sha256=sha(DEST/'schedule.csv'),predictions=consumption,inputs=[dict(path=str(x),sha256=sha(x)) for x in files],source_files=[dict(path=str(x),sha256=sha(x)) for x in sources],outcomes_read=False))
    print(pd.DataFrame(rows).groupby('frequency').size().to_string())

def run(valuation):
    assert valuation in VALUATIONS
    frozen=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==frozen['config_sha256']
    for x in frozen['inputs']:assert sha(x['path'])==x['sha256']
    for x in frozen['source_files']:assert sha(x['path'])==x['sha256']
    inp=Inputs()
    if valuation!='strict':
        m=marks(inp,0. if valuation=='suspend_flat' else .2)
        m.to_csv(DEST/(valuation+'_marks.csv'),index=False)
    p,consumption=predictions('expanding');assert consumption==frozen['predictions']
    p=p.loc[p.model_id.isin(MODELS)&p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
    schedule=pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date','execution_date'])
    dest=DEST/'accounts';dest.mkdir(exist_ok=True);ledger=LEDGER/'accounts';ledger.mkdir(parents=True,exist_ok=True)
    for model in MODELS:
        for frequency in FREQUENCIES:
            dates=schedule.loc[schedule.frequency.eq(frequency),'signal_date']
            scores=p.loc[p.model_id.eq(model)&p.signal_date.isin(dates)]
            for cost in COSTS:
                key=f'{valuation}__{model}__{frequency}__{cost}'
                target=dest/(key+'.csv');receipt=dest/(key+'.json')
                if target.exists() and receipt.exists():
                    r=json.loads(receipt.read_text());assert sha(target)==r['nav_sha256'];assert r['config_sha256']==frozen['config_sha256'];continue
                # Dates already selected. Do not use run_account's older observed-row biweekly filter.
                daily,orders,holdings,fail=run_account(inp,scores,'A',cost,'q5_'+frequency,model,'expanding')
                pd.DataFrame(daily).to_csv(target,index=False)
                op=ledger/(key+'_orders.parquet');hp=ledger/(key+'_holdings.parquet')
                pd.DataFrame(orders).to_parquet(op,index=False)
                pd.DataFrame(holdings,columns=['date','instrument','synthetic_units','valuation_close','weight']).to_parquet(hp,index=False)
                save_json(receipt,dict(account=key,model=model,frequency=frequency,cost=cost,valuation=valuation,days=len(daily),failures=fail,completed_to_data_end=not fail,nav_sha256=sha(target),orders_path=str(op),orders_sha256=sha(op),holdings_path=str(hp),holdings_sha256=sha(hp),config_sha256=frozen['config_sha256'],predictions=consumption,scheduled_rebalances=len(dates),quality='strict_observed_quotes' if valuation=='strict' else 'explicit_suspension_valuation_proxy'))
                print(key,'days',len(daily),'fail',fail,flush=True)
if __name__=='__main__':
    if len(sys.argv)<2:raise SystemExit('freeze | strict | suspend_flat | suspend_haircut20')
    if sys.argv[1]=='freeze':freeze()
    else:run(sys.argv[1])
