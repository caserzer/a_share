"""Fresh versus one-week-old Q5, identical phase2 execution and starting state."""
import json,sys
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json,protocol
from portfolio import trade
from backtest import Inputs
from suspension_sensitivity import marks
from evaluate_ranking import predictions,block_ci
from q5_followup import DEST as SOURCE
from q5_phase_delay_control import DEST as DELAY
from q5_trade_leg_investigation import DEST as LEGS
from q5_followup_engine import select_target

RUN='q5_signal_age_matched_20261116';DEST=OUT/'diagnostics'/RUN;CONFIG=EP/'configs'/f'{RUN}.json'

def freeze():
    if CONFIG.exists():raise RuntimeError('Already frozen')
    DEST.mkdir(parents=True)
    save_json(CONFIG,dict(created_at=datetime.now(timezone.utc).isoformat(),authorization='Continue same-execution old/new-score investigation',posthoc=True,control='Clone the actual delayed B account state immediately before each phase2 execution. OLD uses frozen phase1 Q5 and NEW fresh phase2 Q5; same entry open, capital, cash, member filter, costs and gates; no later trades in window.',windows=[1,5,10,20],gap_policy='all held daily closes and ending open required in both alternatives; no repairs; missing matched outcome stays unavailable',scope='3models x 3costs; original H10 predictions only',statistics='paired mean episode NEW minus OLD and 3-month time-block intervals; no CAGR, no stitched strategy, no independent confirmation'))
    events=pd.read_csv(LEGS/'events.csv',parse_dates=['signal_date','entry_date','phase2_date']);schedule=pd.read_csv(SOURCE/'schedule.csv',parse_dates=['signal_date','execution_date']);schedule=schedule.loc[schedule.frequency.eq('1m')&schedule.phase.eq(2)].set_index('execution_date')
    pred,consumption=predictions('expanding');pred=pred.loc[pred.model_id.isin(['E1','E2','E3'])&pred.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
    members=pd.read_parquet(PRIVATE/'daily_members.parquet');old=pd.read_csv(LEGS/'targets.csv');targets=[];plans=[]
    for e in events.itertuples():
        signal=schedule.loc[e.phase2_date,'signal_date'];member=members.loc[signal]
        stale=old.loc[old.event.eq(e.event),'instrument'];stale=stale[stale.isin(member.index[member])]
        score=pred.loc[pred.model_id.eq(e.model)&pred.signal_date.eq(signal)].set_index('instrument').score.reindex(members.columns).to_numpy()
        chosen=select_target(score,member.to_numpy(bool),np.zeros(len(score),bool),members.columns)
        plans.append(dict(event=e.event,model=e.model,month=e.month,old_signal_date=e.signal_date,signal_date=signal,entry_date=e.phase2_date))
        for policy,names in [('OLD',list(stale)),('NEW',list(members.columns[chosen]))]:
            for name in names:targets.append(dict(event=e.event,policy=policy,instrument=name,weight=1/len(names)))
    pd.DataFrame(plans).to_csv(DEST/'events.csv',index=False);pd.DataFrame(targets).to_csv(DEST/'targets.csv',index=False)
    parent=json.loads((LEGS/'freeze.json').read_text());save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),events_sha256=sha(DEST/'events.csv'),targets_sha256=sha(DEST/'targets.csv'),inputs=parent['inputs'],predictions=consumption,source_sha256=sha(EP/'src/q5_signal_age_matched.py')))
    print('Frozen signal-age matched control')

def run():
    frozen=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==frozen['config_sha256'];assert sha(DEST/'events.csv')==frozen['events_sha256'];assert sha(DEST/'targets.csv')==frozen['targets_sha256']
    for x in frozen['inputs']:assert sha(x['path'])==x['sha256']
    events=pd.read_csv(DEST/'events.csv',parse_dates=['signal_date','old_signal_date','entry_date']);targets=pd.read_csv(DEST/'targets.csv');inp=Inputs();marks(inp,0.)
    ends=pd.read_csv(DELAY/'metrics.csv');ends=ends.loc[ends.scope.eq('model_common')].groupby('model').end.first().map(pd.Timestamp).to_dict();rows=[];checks=[]
    def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
    for model in ['E1','E2','E3']:
        for cost in ['zero','main','stress']:
            rp=DELAY/'accounts'/f'{model}__{cost}.json';r=json.loads(rp.read_text());f=pd.read_csv(rp.with_suffix('.csv'),parse_dates=['date']).set_index('date');hold=pd.read_parquet(r['holdings_path']);bf,sf=np.array(protocol()['costs_bps'][cost])/10000
            for e in events.loc[events.model.eq(model)].itertuples():
                ei=inp.days.get_loc(e.entry_date);si=inp.days.get_loc(e.signal_date);prev=inp.days[ei-1];reason='';states={}
                if prev not in f.index:reason='BASELINE_ALREADY_BLOCKED'
                else:
                    h=hold.loc[hold.date.eq(prev)];units=np.zeros(inp.n);units[inp.symbols.get_indexer(h.instrument)]=h.synthetic_units.to_numpy();cash=f.loc[prev,'nav']*f.loc[prev,'cash_weight']
                    if np.any((units>0)&~np.isfinite(inp.o[ei])):reason='ENTRY_HELD_OPEN_UNKNOWN'
                if not reason:
                    member,_,_,_,_,buy,sell,_=inp.context(si,ei);buy=buy&member;initial=cash+np.sum(units*np.nan_to_num(inp.o[ei]))
                    for policy in ['OLD','NEW']:
                        t=targets.loc[targets.event.eq(e.event)&targets.policy.eq(policy)];target=np.zeros(inp.n+1);target[inp.symbols.get_indexer(t.instrument)]=t.weight.to_numpy()
                        new,c,info=trade(units.copy(),cash,inp.o[ei],target,buy,sell,bf,sf);states[policy]=(new,c);dq=new-units
                        bv=dq.clip(min=0)*np.nan_to_num(inp.o[ei]);sv=(-dq).clip(min=0)*np.nan_to_num(inp.o[ei]);prefix=e.event+cost+policy
                        check(prefix+'_cash',c>=-1e-10 and np.isclose(c,cash+sv.sum()*(1-sf)-bv.sum()*(1+bf),atol=1e-10))
                        check(prefix+'_gates',not np.any((dq>1e-10)&~buy) and not np.any((dq< -1e-10)&~sell))
                        check(prefix+'_fees',np.isclose(info['fees'],(bv*bf+sv*sf).sum(),atol=1e-10))
                    held=np.any(np.stack([u>0 for u,c in states.values()]),axis=0)
                    assert e.old_signal_date<=e.signal_date<e.entry_date
                for horizon in [1,5,10,20]:
                    end_i=ei+horizon;end=inp.days[end_i] if end_i<len(inp.days) else pd.NaT
                    base=dict(event=e.event,model=model,cost=cost,month=e.month,horizon=horizon,entry_date=e.entry_date,exit_date=end,primary_eligible=pd.notna(end) and end<=pd.Timestamp('2025-03-03'),full_eligible=pd.notna(end) and end<=ends[model]);bad=reason
                    if not bad and not base['full_eligible']:bad='END_OUTSIDE_MATCHED_DATA'
                    if not bad and (np.any(held&~np.isfinite(inp.o[end_i])) or np.any(~np.isfinite(inp.c[ei:end_i,held]))):bad='MATCHED_PAIR_VALUATION_UNKNOWN'
                    if bad:rows.append({**base,'status':'BLOCKED','reason':bad});continue
                    ret={k:(c+np.sum(u*np.nan_to_num(inp.o[end_i])))/initial-1 for k,(u,c) in states.items()};rows.append({**base,'status':'OBSERVED','reason':'','old_return':ret['OLD'],'new_return':ret['NEW'],'new_minus_old':ret['NEW']-ret['OLD']})
    f=pd.DataFrame(rows);f.to_csv(DEST/'episodes.csv',index=False);summary=[]
    for scope,flag in [('primary','primary_eligible'),('full','full_eligible')]:
        for (model,cost,horizon),g in f.loc[f[flag]&f.status.eq('OBSERVED')].groupby(['model','cost','horizon']):
            x=g.sort_values('month').new_minus_old;lo,hi=block_ci(x.to_numpy(),L=3);summary.append(dict(scope=scope,model=model,cost=cost,horizon=horizon,episodes=len(x),old_return=g.old_return.mean(),new_return=g.new_return.mean(),mean_difference=x.mean(),ci_low=lo,ci_high=hi))
    pd.DataFrame(summary).to_csv(DEST/'summary.csv',index=False);check('planned_rows',len(rows)==len(events)*3*4)
    save_json(DEST/'validation.json',dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',checks=checks,rows=len(rows),note='same starting holdings, capital and phase2 execution; no new rule search'))
    assert all(x['passed'] for x in checks);print('PASS matched signal age',len(checks),'checks')

if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()
