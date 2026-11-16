"""One post-hoc controlled extension: phase1 basket executed at phase2."""
import json,sys
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json
from backtest import Inputs
from suspension_sensitivity import marks
from evaluate_ranking import predictions,block_ci
from q5_followup import DEST as SOURCE
from q5_phase_investigation import DEST as DIAGNOSTIC
from q5_phase_delayed_engine import run_account,select_target
from summarize import returns

RUN='q5_phase_delay_control_20261116'
DEST=OUT/'diagnostics'/RUN
CONFIG=EP/'configs'/f'{RUN}.json'

def freeze():
    if CONFIG.exists():raise RuntimeError('Already frozen')
    DEST.mkdir(parents=True)
    save_json(CONFIG,dict(created_at=datetime.now(timezone.utc).isoformat(),authorization='Continue investigation; one mechanism control motivated by prior diagnostic, not independent confirmation',parent_diagnostic=str(DIAGNOSTIC),prior_results_seen=True,scope='9 new accounts: E1/E2/E3 x zero/main/stress',treatment='Select original Q5 at phase1 signal close, hold that fixed membership list, execute at phase2 next-market open; initial Jan8 shared, next phases from February. No replacement with later scores.',membership='At later signal remove names no longer current members, no replacement; equal-weight remaining fixed names; actual blocked sells/buys unchanged',contrasts='A=phase1 immediate, B=phase1 fixed basket delayed to phase2, C=phase2 fresh basket. A-B timing-and-holding-path effect, B-C earlier-vs-later selection at same execution clock; not causal economic mechanism.',valuation='unchanged suspend_flat; no gaps repaired',comparison='primary end min(2025-03-03, available end of all 27 A/B/C costs/models); plus each model shared full available end; all initial fees retained',statistics='descriptive paired 65-session time-block 2000 replicate intervals; posthoc, not confirmatory',no_search=True))
    p,consumption=predictions('expanding');p=p.loc[p.model_id.isin(['E1','E2','E3'])&p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
    schedule=pd.read_csv(SOURCE/'schedule.csv',parse_dates=['signal_date','execution_date']);schedule=schedule.loc[schedule.frequency.eq('1m')]
    members=pd.read_parquet(PRIVATE/'daily_members.parquet');rows=[];mapping=[]
    first=schedule.loc[schedule.phase.eq(1)].copy();first['month']=first.signal_date.dt.to_period('M');source_dates=first.set_index('month').signal_date
    for later in schedule.loc[schedule.phase.eq(2)].itertuples():
        early=source_dates.loc[later.signal_date.to_period('M')]
        assert early<=later.signal_date
        for model in ['E1','E2','E3']:
            scores=p.loc[p.model_id.eq(model)&p.signal_date.eq(early)].set_index('instrument').score.reindex(members.columns).to_numpy()
            chosen=select_target(scores,members.loc[early].to_numpy(bool),np.zeros(len(scores),bool),members.columns)
            for i in chosen:rows.append(dict(model=model,signal_date=later.signal_date,source_signal_date=early,instrument=members.columns[i],score=1.))
            mapping.append(dict(model=model,source_signal_date=early,signal_date=later.signal_date,execution_date=later.execution_date,chosen=len(chosen),dropped_nonmembers=int((~members.loc[later.signal_date].iloc[chosen]).sum())))
    pd.DataFrame(rows).to_csv(DEST/'frozen_baskets.csv',index=False);pd.DataFrame(mapping).to_csv(DEST/'schedule_mapping.csv',index=False)
    parent=json.loads((SOURCE/'freeze.json').read_text())
    save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),baskets_sha256=sha(DEST/'frozen_baskets.csv'),mapping_sha256=sha(DEST/'schedule_mapping.csv'),predictions=consumption,inputs=parent['inputs'],sources=[dict(path=str(EP/'src'/x),sha256=sha(EP/'src'/x)) for x in ['q5_phase_delay_control.py','q5_phase_delayed_engine.py']],prior_diagnostic_sha256=sha(DIAGNOSTIC/'validation.json')))
    print('Frozen 9 delayed-basket accounts')

def run():
    frozen=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==frozen['config_sha256']
    for x in frozen['inputs']+frozen['sources']:assert sha(x['path'])==x['sha256']
    assert sha(DEST/'frozen_baskets.csv')==frozen['baskets_sha256']
    p=pd.read_csv(DEST/'frozen_baskets.csv',parse_dates=['signal_date','source_signal_date']);assert (p.source_signal_date<=p.signal_date).all()
    inp=Inputs();marks(inp,0.);ledger=PRIVATE/RUN;ledger.mkdir(exist_ok=True);(DEST/'accounts').mkdir(exist_ok=True)
    for model in ['E1','E2','E3']:
        for cost in ['zero','main','stress']:
            name=f'{model}__{cost}';cp=DEST/'accounts'/(name+'.csv');rp=cp.with_suffix('.json')
            if rp.exists():assert sha(cp)==json.loads(rp.read_text())['nav_sha256'];continue
            daily,orders,holdings,fail=run_account(inp,p.loc[p.model.eq(model)],'A',cost,'phase1_basket_phase2_execution','FROZEN_Q5','expanding')
            pd.DataFrame(daily).to_csv(cp,index=False);op=ledger/(name+'_orders.parquet');hp=ledger/(name+'_holdings.parquet')
            pd.DataFrame(orders).to_parquet(op,index=False);pd.DataFrame(holdings,columns=['date','instrument','synthetic_units','valuation_close','weight']).to_parquet(hp,index=False)
            save_json(rp,dict(model=model,cost=cost,config_sha256=frozen['config_sha256'],nav_sha256=sha(cp),orders_path=str(op),orders_sha256=sha(op),holdings_path=str(hp),holdings_sha256=sha(hp),failures=fail));print(name,len(daily),fail,flush=True)

def analyze():
    from common import protocol
    accounts={};checks=[]
    def check(name,value):checks.append(dict(check=name,passed=bool(value)))
    members=pd.read_parquet(PRIVATE/'daily_members.parquet');mapping=pd.read_csv(DEST/'schedule_mapping.csv',parse_dates=['signal_date','source_signal_date','execution_date']);baskets=pd.read_csv(DEST/'frozen_baskets.csv',parse_dates=['signal_date','source_signal_date'])
    for model in ['E1','E2','E3']:
        for cost in ['zero','main','stress']:
            for tag,phase in [('A',1),('C',2)]:accounts[(model,cost,tag)]=pd.read_csv(SOURCE/'accounts'/f'{model}__1m__p{phase}__b0__{cost}.csv',parse_dates=['date']).set_index('date')
            cp=DEST/'accounts'/f'{model}__{cost}.csv';r=json.loads(cp.with_suffix('.json').read_text());f=pd.read_csv(cp,parse_dates=['date']).set_index('date');accounts[(model,cost,'B')]=f
            check(model+cost+'_hashes',sha(cp)==r['nav_sha256'] and sha(r['orders_path'])==r['orders_sha256'] and sha(r['holdings_path'])==r['holdings_sha256'])
            z=pd.read_parquet(r['orders_path']);delta=z.units_after-z.units_before
            check(model+cost+'_gates',not ((delta>1e-10)&(~z.can_buy|~z.current_member)).any() and not ((delta< -1e-10)&~z.can_sell).any())
            bf,sf=np.array(protocol()['costs_bps'][cost])/10000;z['bv']=delta.clip(lower=0)*z.qfq_open;z['sv']=(-delta).clip(lower=0)*z.qfq_open
            g=z.groupby('date').agg(bv=('bv','sum'),sv=('sv','sum'),cb=('cash_before','first'),ca=('cash_after','last'))
            check(model+cost+'_cash',(g.cb+g.sv*(1-sf)-g.bv*(1+bf)-g.ca).abs().max()<1e-8)
            ix=f.index.intersection(g.index);check(model+cost+'_fees',np.allclose(f.loc[ix,'fees'],g.loc[ix,'bv']*bf+g.loc[ix,'sv']*sf,atol=1e-10))
            h=pd.read_parquet(r['holdings_path']);value=(h.synthetic_units*h.valuation_close).groupby(h.date).sum().reindex(f.index,fill_value=0)
            check(model+cost+'_nav',np.allclose(value+f.cash_weight*f.nav,f.nav,atol=1e-10))
            planned=mapping.loc[mapping.model.eq(model)].set_index('execution_date')
            for date,g in z.groupby('date'):
                late=planned.loc[date,'signal_date'];early=planned.loc[date,'source_signal_date'];expected=set(baskets.loc[baskets.model.eq(model)&baskets.signal_date.eq(late),'instrument']);expected &= set(members.columns[members.loc[late]])
                assert set(g.loc[g.target_weight>0,'instrument'])==expected
                assert early<=late<date
            check(model+cost+'_fixed_basket_no_lookahead',True)
            check(model+cost+'_shared_january',np.allclose(f.loc[:'2021-01-29','nav'],accounts[(model,cost,'A')].loc[:'2021-01-29','nav'],atol=1e-12))
    common=min(pd.Timestamp('2025-03-03'),min(f.index.max() for f in accounts.values()));rows=[];contrasts=[]
    for model in ['E1','E2','E3']:
        end=min(f.index.max() for (m,c,t),f in accounts.items() if m==model)
        for scope,last in [('primary',common),('model_common',end)]:
            for cost in ['zero','main','stress']:
                series={t:accounts[(model,cost,t)].loc[:last] for t in ['A','B','C']};n=len(series['A'])
                for t,f in series.items():rows.append(dict(model=model,cost=cost,scope=scope,end=last,tag=t,sessions=n,cagr=f.nav.iloc[-1]**(252/n)-1,total_return=f.nav.iloc[-1]-1,annual_one_way_turnover=.5*((f.buy+f.sell).sum()-(f.buy+f.sell).loc[lambda x:x>1e-12].iloc[0])*252/n))
                for a,b in [('A','B'),('B','C'),('A','C')]:
                    delta=returns(series[a].nav)-returns(series[b].nav);lo,hi=block_ci(delta.to_numpy(),L=65)
                    contrasts.append(dict(model=model,cost=cost,scope=scope,end=last,contrast=a+'-'+b,cagr_difference=series[a].nav.iloc[-1]**(252/n)-series[b].nav.iloc[-1]**(252/n),annual_mean_difference=delta.mean()*252,ci_low=lo*252,ci_high=hi*252,log_gap=np.log(series[a].nav.iloc[-1]/series[b].nav.iloc[-1])))
    pd.DataFrame(rows).to_csv(DEST/'metrics.csv',index=False);pd.DataFrame(contrasts).to_csv(DEST/'contrasts.csv',index=False)
    save_json(DEST/'validation.json',dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL',checks=checks,primary_end=common,total_membership_drops=int(mapping.dropped_nonmembers.sum()),note='posthoc diagnostic; no claim of causal identification or independent confirmation'))
    assert all(c['passed'] for c in checks);print('PASS delayed control',len(checks),'checks')

if __name__=='__main__':
    {'freeze':freeze,'run':run,'analyze':analyze}[sys.argv[1]]()
