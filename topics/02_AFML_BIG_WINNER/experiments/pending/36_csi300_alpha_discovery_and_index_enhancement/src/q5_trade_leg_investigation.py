"""Matched-state episode decomposition: old holdings, sells-only, full rebalance."""
import json,sys
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json,protocol
from backtest import Inputs
from portfolio import trade
from suspension_sensitivity import marks
from evaluate_ranking import predictions,block_ci
from q5_followup_engine import select_target
from q5_followup import DEST as FOLLOWUP
from q5_phase_delay_control import DEST as DELAY

RUN='q5_trade_leg_investigation_20261116'
DEST=OUT/'diagnostics'/RUN
CONFIG=EP/'configs'/f'{RUN}.json'

def triplet(units,cash,prices,target,buy,sell,buyfee,sellfee):
    full,fullcash,info=trade(units.copy(),cash,prices,target,buy,sell,buyfee,sellfee)
    onlysell=np.minimum(units,full)
    sale_value=np.sum((units-onlysell)*np.nan_to_num(prices))
    sale_cash=cash+sale_value*(1-sellfee)
    return dict(H=(units.copy(),cash),S=(onlysell,sale_cash),F=(full,fullcash)),info

def freeze():
    if CONFIG.exists():raise RuntimeError('Already frozen')
    DEST.mkdir(parents=True)
    cfg=dict(created_at=datetime.now(timezone.utc).isoformat(),authorization='Continue investigating timely replacement of old holdings vs entry into new holdings; no data repair',evidence='posthoc mechanism diagnostic; outcomes of earlier phase and delayed-basket experiments already seen',controls='For each first monthly signal after Jan2021, clone B delayed-account actual prior-close holdings/cash, mark same next-open initial NAV; H holds unchanged, S executes exactly the sell quantities of F and holds proceeds as cash, F executes the original phase1 Q5 rebalance. No leverage, same gates/costs; no further trades inside episode.',windows=['actual_phase2_open','1_session','5_sessions','10_sessions','20_sessions'],valuation='unchanged existing suspension marks, require every held daily close and final open; any scenario unavailable blocks the matched triple for that window',membership='Q5 selected using original sealed score/current membership at first signal close; execution gates unchanged',periods='primary: endpoint <=2025-03-03; full: each model common A/B/C endpoint from delayed-control receipt. Every planned episode/window retained with unavailable reasons.',statistics='mean episode returns and paired sell/buy increments; not CAGR or stitched NAV; 3-month circular time blocks, 2000 draws fixed seed20261116; descriptive intervals, not independent confirmation',decomposition='F-H=(S-H)+(F-S). Per-stock effect dq*(exit_open-entry_open)-buy_fee-sell_fee, divided by shared start NAV. Classify entries/topups/exits/trims from actual units.',past_return='raw frozen qfq close ratios at original signal date over 5/20 sessions; no suspension valuation marks in these diagnostic features; no thresholds fitted',no_search=True)
    save_json(CONFIG,cfg)
    p,pred=predictions('expanding');p=p.loc[p.model_id.isin(['E1','E2','E3'])&p.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])]
    sched=pd.read_csv(FOLLOWUP/'schedule.csv',parse_dates=['signal_date','execution_date']);sched=sched.loc[sched.frequency.eq('1m')&sched.phase.isin([1,2])].copy();sched['month']=sched.signal_date.dt.to_period('M').astype(str)
    members=pd.read_parquet(PRIVATE/'daily_members.parquet');targets=[];events=[]
    for month,g in sched.groupby('month'):
        if month=='2021-01' or not {1,2}.issubset(set(g.phase)):continue
        a=g.loc[g.phase.eq(1)].iloc[0];b=g.loc[g.phase.eq(2)].iloc[0]
        for model in ['E1','E2','E3']:
            s=p.loc[p.model_id.eq(model)&p.signal_date.eq(a.signal_date)].set_index('instrument').score.reindex(members.columns).to_numpy()
            chosen=select_target(s,members.loc[a.signal_date].to_numpy(bool),np.zeros(len(s),bool),members.columns)
            event=f'{model}_{month}'
            events.append(dict(event=event,model=model,month=month,signal_date=a.signal_date,entry_date=a.execution_date,phase2_date=b.execution_date))
            for j in chosen:targets.append(dict(event=event,instrument=members.columns[j],weight=1/len(chosen)))
    pd.DataFrame(events).to_csv(DEST/'events.csv',index=False);pd.DataFrame(targets).to_csv(DEST/'targets.csv',index=False)
    parent=json.loads((DELAY/'freeze.json').read_text());files=[]
    for model in ['E1','E2','E3']:
        for cost in ['zero','main','stress']:
            rp=DELAY/'accounts'/f'{model}__{cost}.json';r=json.loads(rp.read_text());files += [rp,rp.with_suffix('.csv'),r['holdings_path']]
    sources=[EP/'src'/x for x in ['q5_trade_leg_investigation.py','backtest.py','portfolio.py','suspension_sensitivity.py','q5_followup_engine.py']]
    save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),events_sha256=sha(DEST/'events.csv'),targets_sha256=sha(DEST/'targets.csv'),predictions=pred,inputs=parent['inputs']+[dict(path=str(x),sha256=sha(x)) for x in files],sources=[dict(path=str(x),sha256=sha(x)) for x in sources]))
    print('Frozen',len(events),'model-month episodes x 3 costs x 5 windows')

def run():
    frozen=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==frozen['config_sha256']
    for x in frozen['inputs']+frozen['sources']:assert sha(x['path'])==x['sha256']
    assert sha(DEST/'events.csv')==frozen['events_sha256'];assert sha(DEST/'targets.csv')==frozen['targets_sha256']
    events=pd.read_csv(DEST/'events.csv',parse_dates=['signal_date','entry_date','phase2_date']);targets=pd.read_csv(DEST/'targets.csv')
    raw=pd.read_parquet(PRIVATE/'qfq_close.parquet');raw_values=raw.to_numpy(copy=True)
    inp=Inputs();marks(inp,0.);days=inp.days;n=inp.n
    ends=pd.read_csv(DELAY/'metrics.csv');ends=ends.loc[ends.scope.eq('model_common')&ends.cost.eq('main')].groupby('model').end.first().map(pd.Timestamp).to_dict()
    rows=[];stockrows=[];checks=[];snapshots=[]
    def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
    for model in ['E1','E2','E3']:
        for cost in ['zero','main','stress']:
            rp=DELAY/'accounts'/f'{model}__{cost}.json';r=json.loads(rp.read_text());f=pd.read_csv(rp.with_suffix('.csv'),parse_dates=['date']).set_index('date');h=pd.read_parquet(r['holdings_path'])
            bf,sf=np.array(protocol()['costs_bps'][cost])/10000
            for event in events.loc[events.model.eq(model)].itertuples():
                ei=days.get_loc(event.entry_date);si=days.get_loc(event.signal_date);prev=days[ei-1];startreason=''
                target=np.zeros(n+1);t=targets.loc[targets.event.eq(event.event)];target[inp.symbols.get_indexer(t.instrument)]=t.weight.to_numpy()
                windows={'actual_phase2_open':days.get_loc(event.phase2_date),**{f'{x}_sessions':ei+x for x in [1,5,10,20]}}
                if prev not in f.index:startreason='BASELINE_ALREADY_BLOCKED'
                else:
                    old=np.zeros(n);hp=h.loc[h.date.eq(prev)];old[inp.symbols.get_indexer(hp.instrument)]=hp.synthetic_units.to_numpy();cash=float(f.loc[prev,'nav']*f.loc[prev,'cash_weight'])
                    if np.any((old>0)&~np.isfinite(inp.o[ei])):startreason='ENTRY_HELD_OPEN_UNKNOWN'
                if not startreason:
                    member,_,_,_,_,buy,sell,_=inp.context(si,ei);buy=buy&member
                    initial=cash+np.sum(old*np.nan_to_num(inp.o[ei]));scenarios,info=triplet(old,cash,inp.o[ei],target,buy,sell,bf,sf)
                    delta=scenarios['F'][0]-old;bv=delta.clip(min=0)*np.nan_to_num(inp.o[ei]);sv=(-delta).clip(min=0)*np.nan_to_num(inp.o[ei]);fees=bv*bf+sv*sf
                    prefix=f'{event.event}_{cost}'
                    check(prefix+'_funding',all(c>=-1e-10 and u.min()>=-1e-10 for u,c in scenarios.values()))
                    check(prefix+'_cash_reconciliation',np.isclose(scenarios['F'][1],cash+sv.sum()*(1-sf)-bv.sum()*(1+bf),atol=1e-10) and np.isclose(scenarios['S'][1],cash+sv.sum()*(1-sf),atol=1e-10))
                    check(prefix+'_gates',not np.any((delta>1e-10)&~buy) and not np.any((delta< -1e-10)&~sell))
                    held_union=np.any(np.stack([u>0 for u,c in scenarios.values()]),axis=0)
                    if cost=='main':snapshots.append(dict(event=event.event,entry_date=event.entry_date,initial_nav=initial,buy_fraction=bv.sum()/initial,sell_fraction=sv.sum()/initial,old_holdings=int((old>0).sum()),new_holdings=int((scenarios['F'][0]>0).sum()),cash_after_sells=scenarios['S'][1]/initial,cash_after_full=scenarios['F'][1]/initial))
                for label,exit_i in windows.items():
                    end=days[exit_i] if exit_i<len(days) else pd.NaT
                    base=dict(event=event.event,model=model,cost=cost,month=event.month,signal_date=event.signal_date,entry_date=event.entry_date,window=label,exit_date=end,sessions=exit_i-ei,primary_eligible=pd.notna(end) and end<=pd.Timestamp('2025-03-03'),full_eligible=pd.notna(end) and end<=ends[model])
                    reason=startreason
                    if not reason and (exit_i>=len(days) or not base['full_eligible']):reason='END_OUTSIDE_MATCHED_DATA'
                    if not reason and (np.any(held_union&~np.isfinite(inp.o[exit_i])) or np.any(~np.isfinite(inp.c[ei:exit_i,held_union]))):reason='MATCHED_TRIPLE_VALUATION_UNKNOWN'
                    if reason:rows.append({**base,'status':'BLOCKED','reason':reason});continue
                    outcomes={tag:(c+np.sum(u*np.nan_to_num(inp.o[exit_i])))/initial-1 for tag,(u,c) in scenarios.items()}
                    effect=(delta*(np.nan_to_num(inp.o[exit_i])-np.nan_to_num(inp.o[ei]))-fees)/initial
                    sell_effect=effect[delta<0].sum();buy_effect=effect[delta>0].sum()
                    check(prefix+label+'_legs',np.isclose(sell_effect,outcomes['S']-outcomes['H'],atol=1e-10) and np.isclose(buy_effect,outcomes['F']-outcomes['S'],atol=1e-10) and np.isclose(effect.sum(),outcomes['F']-outcomes['H'],atol=1e-10))
                    rows.append({**base,'status':'OBSERVED','reason':'','hold_return':outcomes['H'],'sell_only_return':outcomes['S'],'full_return':outcomes['F'],'sell_increment':sell_effect,'buy_increment':buy_effect,'full_increment':sell_effect+buy_effect,'buy_fraction':bv.sum()/initial,'sell_fraction':sv.sum()/initial})
                    if cost=='main':
                        for j in np.where(abs(delta)>1e-12)[0]:
                            category=('entry' if old[j]<=1e-12 else 'top_up') if delta[j]>0 else ('exit' if scenarios['F'][0][j]<=1e-12 else 'trim')
                            past={}
                            for horizon in [5,20]:
                                numerator=raw_values[si,j];denominator=raw_values[si-horizon,j] if si>=horizon else np.nan
                                past['past_'+str(horizon)]=numerator/denominator-1 if np.isfinite(numerator) and np.isfinite(denominator) and denominator>0 else np.nan
                            stockrows.append({**base,'instrument':inp.symbols[j],'category':category,'trade_fraction':(bv[j]+sv[j])/initial,'increment':effect[j],'fee_fraction':fees[j]/initial,'holding_return':inp.o[exit_i,j]/inp.o[ei,j]-1,**past})
    pd.DataFrame(rows).to_csv(DEST/'episodes.csv',index=False);pd.DataFrame(stockrows).to_csv(DEST/'stock_leg_contributions.csv',index=False);pd.DataFrame(snapshots).to_csv(DEST/'starting_states.csv',index=False)
    check('all_planned_windows_recorded',len(rows)==len(events)*3*5)
    save_json(DEST/'validation.json',dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',checks=checks,rows=len(rows),state='all observed triples use identical capital and starting positions',scope='independent episodes, not a continuous portfolio'))
    assert all(x['passed'] for x in checks);print('PASS',len(checks),'checks;',len(rows),'episode windows')

def analyze():
    f=pd.read_csv(DEST/'episodes.csv');stocks=pd.read_csv(DEST/'stock_leg_contributions.csv');summary=[];types=[];years=[];exposure=[]
    for scope,flag in [('primary','primary_eligible'),('full','full_eligible')]:
        sample=f.loc[f[flag]&f.status.eq('OBSERVED')]
        for (model,cost,window),g in sample.groupby(['model','cost','window']):
            g=g.sort_values('month')
            for metric in ['hold_return','sell_only_return','full_return','sell_increment','buy_increment','full_increment']:
                x=g[metric];lo,hi=block_ci(x.to_numpy(),L=3)
                summary.append(dict(scope=scope,model=model,cost=cost,window=window,metric=metric,episodes=len(x),mean=x.mean(),median=x.median(),positive_fraction=x.gt(0).mean(),ci_low=lo,ci_high=hi))
            for year,h in g.groupby(g.month.str[:4]):years.append(dict(scope=scope,model=model,cost=cost,window=window,year=year,episodes=len(h),sell_increment=h.sell_increment.mean(),buy_increment=h.buy_increment.mean(),full_increment=h.full_increment.mean()))
        s=stocks.loc[stocks[flag]]
        for (model,window),g in s.groupby(['model','window']):
            valid=set(sample.loc[sample.model.eq(model)&sample.window.eq(window)&sample.cost.eq('main'),'event']);g=g.loc[g.event.isin(valid)]
            for category in ['entry','top_up','exit','trim']:
                h=g.loc[g.category.eq(category)];by=h.groupby('event').increment.sum().reindex(sorted(valid),fill_value=0)
                types.append(dict(scope=scope,model=model,window=window,category=category,episodes=len(valid),mean_increment=by.mean(),sum_increment=by.sum()))
                row=dict(scope=scope,model=model,window=window,category=category,trade_rows=len(h),sum_trade_fraction=h.trade_fraction.sum())
                for past in ['past_5','past_20']:
                    known=h.loc[h[past].notna()];row[past+'_known_trade_fraction']=known.trade_fraction.sum()/h.trade_fraction.sum() if h.trade_fraction.sum()>0 else np.nan
                    row[past+'_weighted_mean']=np.average(known[past],weights=known.trade_fraction) if len(known) else np.nan
                exposure.append(row)
    pd.DataFrame(summary).to_csv(DEST/'summary.csv',index=False);pd.DataFrame(types).to_csv(DEST/'trade_type_summary.csv',index=False);pd.DataFrame(years).to_csv(DEST/'annual_episode_summary.csv',index=False);pd.DataFrame(exposure).to_csv(DEST/'past_return_characteristics.csv',index=False)
    print('Summary written')

if __name__=='__main__':{'freeze':freeze,'run':run,'analyze':analyze}[sys.argv[1]]()
