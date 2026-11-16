"""Frozen EW controls, monthly phases and fixed holding buffers."""
import sys,json
from datetime import datetime,timezone
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json,protocol
from backtest import Inputs
from suspension_sensitivity import marks
from evaluate_ranking import predictions
from q5_rebalance_sensitivity import scheduled_dates,DEST as PREVIOUS
from q5_followup_engine import run_account

RUN='q5_controls_phases_buffers_20261116'
DEST=OUT/'sensitivity'/RUN
LEDGER=PRIVATE/RUN
CONFIG=EP/'configs'/f'{RUN}.json'

def phase_dates(dates,phase):
    dates=pd.DatetimeIndex(sorted(pd.unique(dates)))
    if phase not in [1,2,3,4]:raise ValueError(phase)
    result=[dates[0]]
    for month in dates.to_period('M').unique()[1:]:
        group=dates[dates.to_period('M')==month]
        if len(group)>=phase:result.append(group[phase-1])
    return pd.DatetimeIndex(result)

def specs():
    rows=[]
    for model in ['EW','E1','E2','E3']:
        for freq in ['1w','2w','1m']:
            for cost in ['zero','main','stress']:
                rows.append(dict(group='control',model=model,frequency=freq,phase=1,buffer=None,cost=cost,reuse=model!='EW'))
        for phase in [2,3,4]:
            for cost in ['zero','main','stress']:
                rows.append(dict(group='phase',model=model,frequency='1m',phase=phase,buffer=None,cost=cost,reuse=False))
    for model in ['E1','E2','E3']:
        for freq in ['1w','2w','1m']:
            for buffer in [.3,.4]:
                for cost in ['zero','main','stress']:
                    rows.append(dict(group='buffer',model=model,frequency=freq,phase=1,buffer=buffer,cost=cost,reuse=False))
    for r in rows:r['account']=f"{r['model']}__{r['frequency']}__p{r['phase']}__b{int(100*r['buffer']) if r['buffer'] else 0}__{r['cost']}"
    return rows

def freeze():
    if CONFIG.exists():raise RuntimeError('Already frozen')
    DEST.mkdir(parents=True);LEDGER.mkdir(parents=True)
    p,consumption=predictions('expanding');p=p.loc[p.model_id.eq('E2')&p.seed_or_ensemble.eq('equal_seed_ensemble')]
    dates=pd.DatetimeIndex(sorted(p.signal_date.unique()));days=pd.read_parquet(PRIVATE/'qfq_close.parquet').index
    schedules=[]
    for freq,phase in [('1w',1),('2w',1),('1m',1),('1m',2),('1m',3),('1m',4)]:
        ds=scheduled_dates(dates,freq) if phase==1 else phase_dates(dates,phase)
        for d in ds:schedules.append(dict(frequency=freq,phase=phase,signal_date=d,execution_date=days[days.get_loc(d)+1]))
    pd.DataFrame(schedules).to_csv(DEST/'schedule.csv',index=False)
    cfg=dict(run_id=RUN,created_at=datetime.now(timezone.utc).isoformat(),authorization='User authorizes directions 2/3/4 and explicitly defers data gap repairs',models='fixed original expanding E1/E2/E3 H10 predictions; no training',valuation='existing suspend_flat only; no data repair or mark-rule change',costs=protocol()['costs_bps'],phase='common initial Jan8 signal; starting February choose nth available weekly signal per calendar month, skip months with fewer signals; no retrospective last-week fallback',buffer='rank scored current members descending with original tie convention; target count equals original Q5. Retain actually held names within floor(N*0.3) or floor(N*0.4), cap at K best ranks, then fill remaining slots from best ranked names. Equalize selected targets each scheduled rebalance; blocked orders remain real holdings. No score or nonmember cannot be intentionally retained.',control='all contemporary members equal target weight, identical schedule and fees; score eligibility does not shrink EW universe',comparisons='matched common prefixes only, family-wide primary common end plus same-model pairwise longer prefixes; native horizon separate; initial fees included; calendar monthly/annual returns with missing periods explicit',industry='descriptive historical L1 industry weights vs same-schedule EW; not causal attribution or certified PIT; size exposure only if existing compatible point-in-time data available, no new sourcing',uncertainty='65-session circular paired block bootstrap, 2000 reps, seed20261116; family-level Holm adjustment for two-sided paired mean-return tests; no winner selection',phase_judgment='report all four phases and min/median/max, not select highest phase',evidence='historical_simulated_oos; prior baseline results seen; FORWARD_PENDING',scope=specs())
    save_json(CONFIG,cfg)
    old=json.loads((PREVIOUS/'freeze.json').read_text())
    for x in old['inputs']:assert sha(x['path'])==x['sha256']
    sources=[EP/'src'/x for x in ['backtest.py','portfolio.py','suspension_sensitivity.py','q5_followup_engine.py','q5_followup.py']]
    save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),schedule_sha256=sha(DEST/'schedule.csv'),predictions=consumption,inputs=old['inputs'],sources=[dict(path=str(x),sha256=sha(x)) for x in sources],new_outcomes_seen=False))
    print('Frozen',len(cfg['scope']),'accounts;',sum(not r['reuse'] for r in cfg['scope']),'new')

def run(group):
    frozen=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==frozen['config_sha256']
    for x in frozen['inputs']+frozen['sources']:assert sha(x['path'])==x['sha256']
    p,consumption=predictions('expanding');assert consumption==frozen['predictions']
    p=p.loc[p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
    schedule=pd.read_csv(DEST/'schedule.csv',parse_dates=['signal_date'])
    dest=DEST/'accounts';dest.mkdir(exist_ok=True)
    inp=Inputs();marks(inp,0.)
    for r in specs():
        if r['group']!=group:continue
        key=r['account'];rp=dest/(key+'.json');cp=dest/(key+'.csv')
        if rp.exists():
            previous=json.loads(rp.read_text());assert sha(cp)==previous['nav_sha256'];assert previous['config_sha256']==frozen['config_sha256'];continue
        if r['reuse']:
            source=PREVIOUS/'accounts'/f"suspend_flat__{r['model']}__{r['frequency']}__{r['cost']}.json"
            old=json.loads(source.read_text());assert sha(source.with_suffix('.csv'))==old['nav_sha256']
            cp.write_bytes(source.with_suffix('.csv').read_bytes())
            receipt={**old,**r,'reused_receipt':str(source),'reused_sha256':sha(source)}
        else:
            dates=schedule.loc[schedule.frequency.eq(r['frequency'])&schedule.phase.eq(r['phase']),'signal_date']
            scores=p.loc[p.model_id.eq('E2' if r['model']=='EW' else r['model'])&p.signal_date.isin(dates)]
            daily,orders,holdings,fail=run_account(inp,scores,'A',r['cost'],'followup_'+key,r['model'],'expanding',buffer=r['buffer'])
            pd.DataFrame(daily).to_csv(cp,index=False)
            op=LEDGER/(key+'_orders.parquet');hp=LEDGER/(key+'_holdings.parquet')
            pd.DataFrame(orders).to_parquet(op,index=False)
            pd.DataFrame(holdings,columns=['date','instrument','synthetic_units','valuation_close','weight']).to_parquet(hp,index=False)
            receipt={**r,'days':len(daily),'failures':fail,'completed_to_data_end':not fail,'orders_path':str(op),'orders_sha256':sha(op),'holdings_path':str(hp),'holdings_sha256':sha(hp)}
        receipt.update(config_sha256=frozen['config_sha256'],nav_sha256=sha(cp),predictions=consumption)
        save_json(rp,receipt);print(key,'days',receipt['days'],'fail',receipt['failures'],flush=True)

if __name__=='__main__':
    if sys.argv[1]=='freeze':freeze()
    else:run(sys.argv[1])
