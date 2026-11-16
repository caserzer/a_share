"""Replace new-entry purchases with equal-budget market/industry/price-profile controls."""
import json,sys
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json,protocol
from backtest import Inputs
from portfolio import trade
from suspension_sensitivity import marks
from q5_trade_leg_investigation import DEST as LEGS
from q5_phase_delay_control import DEST as DELAY

RUN='q5_entry_matched_controls_20261116';DEST=OUT/'diagnostics'/RUN;LEDGER=PRIVATE/RUN;CONFIG=EP/'configs'/f'{RUN}.json'
CONTROLS=['market_ew','industry_ew','industry_r20_ew']

def buckets(industries,past,eligible,symbols):
    """Contemporaneous within-industry quintiles; missing returns stay explicit."""
    result=np.full(len(past),'INELIGIBLE',dtype=object)
    for industry in sorted(set(industries[eligible])):
        idx=np.where(eligible&(industries==industry))[0];known=idx[np.isfinite(past[idx])];unknown=idx[~np.isfinite(past[idx])]
        known=known[np.lexsort((np.asarray(symbols)[known],past[known]))]
        for ordinal,j in enumerate(known):result[j]=str(industry)+'|Q'+str(int(np.floor(5*ordinal/max(1,len(known)))))
        result[unknown]=str(industry)+'|UNKNOWN_RETURN'
    return result

def allocation(model_budget,eligible,groups=None):
    """Preserve cash spent overall, and per matching group when specified."""
    out=np.zeros(len(model_budget));total=model_budget.sum()
    if total==0:return out
    if groups is None:
        assert eligible.any();out[eligible]=total/eligible.sum();return out
    for group in set(groups[model_budget>0]):
        ix=eligible&(groups==group);assert ix.any()
        out[ix]=model_budget[groups==group].sum()/ix.sum()
    return out

def freeze():
    if CONFIG.exists():raise RuntimeError('Already frozen')
    DEST.mkdir(parents=True);LEDGER.mkdir(parents=True)
    cfg=dict(created_at=datetime.now(timezone.utc).isoformat(),authorization='Continue investigating model-specific new-entry advantage versus simple matched purchases',posthoc=True,source='Original frozen phase1 target and B delayed-account pre-entry holdings/cash; reconstruct same actual fills as preceding trade-leg experiment',controls=CONTROLS,eligible='Current phase1 signal members, not already held (units<=1e-12), actually buyable at execution open under original gates. Include original new entries; never use future returns to choose or drop controls.',budget='Only replace actual new-entry purchase principal, keeping actual sells, retained-stock topups, total buy principal and fees/cash identical. Fractional synthetic units, same as source.',industry='Historical original L1 mapping at signal date; UNKNOWN explicit, not strict-PIT certified',price_matching='Within each industry and eligible pool, sort known prior20-session raw qfq close returns then instrument; floor(5*ordinal/N) quintile. Unknown returns separate. Small groups retained and disclosed, not replaced with broader favourable matches.',matching_self_overlap='Original selected entries remain eligible; disclose benchmark budget overlapping selected entrants, effective number and small-group coverage; no claim of independent controls when self-overlap is high',valuation='Original suspend_flat and held-close/end-open requirements unchanged; missing entire matched pair stays unknown; no repair or future quote filtering',windows=['actual_phase2_open','1_sessions','5_sessions','10_sessions','20_sessions'],periods='primary endpoint<=2025-03-03; full limited by original same-model A/B/C common end; common valid events across all three controls for main tables',statistics='Ordered monthly episode paired differences; 3-observation circular blocks,2000 resamples,seed20261116. Primary family=9 main-cost model/control contrasts at actual_phase2 endpoint in primary period; two-sided centered-bootstrap p and Holm. Other windows/costs/full scopes descriptive; posthoc not independent confirmation.',no_search=True)
    save_json(CONFIG,cfg)
    parent=json.loads((LEGS/'freeze.json').read_text());sources=[EP/'src'/x for x in ['q5_entry_matched_controls.py','backtest.py','portfolio.py','suspension_sensitivity.py']]
    files=[LEGS/'events.csv',LEGS/'targets.csv',PRIVATE/'industry.parquet',DELAY/'metrics.csv',LEGS/'episodes.csv']
    save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),inputs=parent['inputs']+[dict(path=str(x),sha256=sha(x)) for x in files],sources=[dict(path=str(x),sha256=sha(x)) for x in sources],predictions=parent['predictions'],new_control_outcomes_seen=False))
    print('Frozen 3 fixed matched-purchase controls')

def run():
    frozen=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==frozen['config_sha256']
    for x in frozen['inputs']+frozen['sources']:assert sha(x['path'])==x['sha256']
    events=pd.read_csv(LEGS/'events.csv',parse_dates=['signal_date','entry_date','phase2_date']);targets=pd.read_csv(LEGS/'targets.csv')
    previous=pd.read_csv(LEGS/'episodes.csv').set_index(['event','cost','window'])
    raw=pd.read_parquet(PRIVATE/'qfq_close.parquet').to_numpy(copy=True);inp=Inputs();marks(inp,0.)
    end_frame=pd.read_csv(DELAY/'metrics.csv');ends=end_frame.loc[end_frame.scope.eq('model_common')].groupby('model').end.first().map(pd.Timestamp).to_dict()
    rows=[];coverage=[];allocation_rows=[];checks=[]
    def check(name,value):checks.append(dict(check=name,passed=bool(value)))
    for model in ['E1','E2','E3']:
        for cost in ['zero','main','stress']:
            rp=DELAY/'accounts'/f'{model}__{cost}.json';r=json.loads(rp.read_text());f=pd.read_csv(rp.with_suffix('.csv'),parse_dates=['date']).set_index('date');hold=pd.read_parquet(r['holdings_path']);bf,sf=np.array(protocol()['costs_bps'][cost])/10000
            for e in events.loc[events.model.eq(model)].itertuples():
                ei=inp.days.get_loc(e.entry_date);si=inp.days.get_loc(e.signal_date);prev=inp.days[ei-1];reason=''
                if prev not in f.index:reason='BASELINE_ALREADY_BLOCKED'
                else:
                    h=hold.loc[hold.date.eq(prev)];old=np.zeros(inp.n);old[inp.symbols.get_indexer(h.instrument)]=h.synthetic_units.to_numpy();cash=f.loc[prev,'nav']*f.loc[prev,'cash_weight']
                    if np.any((old>0)&~np.isfinite(inp.o[ei])):reason='ENTRY_HELD_OPEN_UNKNOWN'
                if not reason:
                    member,_,_,_,industry,buy,sell,_=inp.context(si,ei);buy=buy&member
                    target=np.zeros(inp.n+1);t=targets.loc[targets.event.eq(e.event)];target[inp.symbols.get_indexer(t.instrument)]=t.weight.to_numpy()
                    full,fullcash,info=trade(old.copy(),cash,inp.o[ei],target,buy,sell,bf,sf);delta=full-old
                    entry=(old<=1e-12)&(delta>1e-12);eligible=(old<=1e-12)&buy
                    initial=cash+np.sum(old*np.nan_to_num(inp.o[ei]));model_budget=np.where(entry,delta*np.nan_to_num(inp.o[ei]),0.);budget=model_budget.sum()
                    if budget<=0:reason='NO_NEW_ENTRY_BUDGET'
                if not reason:
                    past=np.divide(raw[si],raw[si-20],out=np.full(inp.n,np.nan),where=np.isfinite(raw[si])&np.isfinite(raw[si-20])&(raw[si-20]>0))-1
                    bucket=buckets(industry,past,eligible,inp.symbols);common=full.copy();common[entry]-=delta[entry]
                    cashflows={'model':model_budget,'market_ew':allocation(model_budget,eligible),'industry_ew':allocation(model_budget,eligible,industry),'industry_r20_ew':allocation(model_budget,eligible,bucket)}
                    positions={k:common+np.divide(a,inp.o[ei],out=np.zeros(inp.n),where=np.isfinite(inp.o[ei])&(inp.o[ei]>0)) for k,a in cashflows.items()}
                    prefix=e.event+cost
                    check(prefix+'_original_rebuilt',np.allclose(positions['model'],full,atol=1e-12))
                    check(prefix+'_budget_cash_fees',all(np.isclose(a.sum(),budget,atol=1e-10) for a in cashflows.values()) and fullcash>=-1e-10)
                    check(prefix+'_no_unbuyable_controls',all(not np.any((a>0)&~eligible) for a in cashflows.values()))
                    for name,groups in [('industry_ew',industry),('industry_r20_ew',bucket)]:
                        check(prefix+'_'+name+'_matched_distribution',all(np.isclose(cashflows[name][groups==g].sum(),model_budget[groups==g].sum(),atol=1e-10) for g in set(groups[eligible])))
                    for name,a in cashflows.items():
                        weights=a/budget;positive=np.where(a>0)[0]
                        groups=bucket if name=='industry_r20_ew' else industry
                        group_sizes={g:int(np.sum(eligible&(groups==g))) for g in set(groups[eligible])}
                        coverage.append(dict(event=e.event,model=model,cost=cost,month=e.month,control=name,entry_date=e.entry_date,entry_budget_fraction=budget/initial,candidate_count=len(positive),effective_number=1/np.square(weights).sum(),selected_overlap=weights[entry].sum(),singleton_budget=sum(weights[j] for j in positive if group_sizes.get(groups[j],0)==1) if name!='market_ew' else 0.,small_group_budget=sum(weights[j] for j in positive if group_sizes.get(groups[j],0)<=3) if name!='market_ew' else 0.,unknown_industry_budget=weights[industry=='UNKNOWN'].sum(),unknown_r20_budget=weights[~np.isfinite(past)].sum()))
                        if cost=='main':
                            for j in positive:allocation_rows.append(dict(event=e.event,control=name,instrument=inp.symbols[j],signal_date=e.signal_date,entry_date=e.entry_date,allocation_fraction=a[j]/initial,weight_of_entry_budget=weights[j],industry=industry[j],r20_bucket=bucket[j],past_r20=past[j],selected_entry=bool(entry[j]),eligible=True))
                windows={'actual_phase2_open':inp.days.get_loc(e.phase2_date),**{f'{x}_sessions':ei+x for x in [1,5,10,20]}}
                for window,exit_i in windows.items():
                    end=inp.days[exit_i] if exit_i<len(inp.days) else pd.NaT
                    base=dict(event=e.event,model=model,cost=cost,month=e.month,window=window,entry_date=e.entry_date,exit_date=end,sessions=exit_i-ei,primary_eligible=pd.notna(end) and end<=pd.Timestamp('2025-03-03'),full_eligible=pd.notna(end) and end<=ends[model])
                    for name in CONTROLS:
                        bad=reason
                        if not bad and not base['full_eligible']:bad='END_OUTSIDE_MATCHED_DATA'
                        if not bad:
                            union=(positions['model']>0)|(positions[name]>0)
                            if np.any(union&~np.isfinite(inp.o[exit_i])) or np.any(~np.isfinite(inp.c[ei:exit_i,union])):bad='MATCHED_PAIR_VALUATION_UNKNOWN'
                        if bad:rows.append({**base,'control':name,'status':'BLOCKED','reason':bad});continue
                        ratio=np.divide(inp.o[exit_i],inp.o[ei],out=np.zeros(inp.n),where=np.isfinite(inp.o[exit_i])&np.isfinite(inp.o[ei])&(inp.o[ei]>0))-1
                        own=(np.sum(model_budget*ratio)-budget*bf)/initial;bench=(np.sum(cashflows[name]*ratio)-budget*bf)/initial
                        model_return=(fullcash+np.sum(positions['model']*np.nan_to_num(inp.o[exit_i])))/initial-1;control_return=(fullcash+np.sum(positions[name]*np.nan_to_num(inp.o[exit_i])))/initial-1
                        check(prefix+window+name+'_replacement_reconciles',np.isclose(model_return-control_return,own-bench,atol=1e-10))
                        old_result=previous.loc[(e.event,cost,window)]
                        if old_result.status=='OBSERVED':check(prefix+window+name+'_old_account_unchanged',np.isclose(model_return,old_result.full_return,atol=1e-10))
                        rows.append({**base,'control':name,'status':'OBSERVED','reason':'','entry_budget_fraction':budget/initial,'model_entry_contribution':own,'control_entry_contribution':bench,'increment':own-bench,'model_return':model_return,'replacement_return':control_return,'selected_basket_return':own/(budget/initial),'control_basket_return':bench/(budget/initial)})
    pd.DataFrame(rows).to_csv(DEST/'episodes.csv',index=False);pd.DataFrame(coverage).to_csv(DEST/'matching_coverage.csv',index=False)
    allocations=LEDGER/'allocations_main.parquet';pd.DataFrame(allocation_rows).to_parquet(allocations,index=False)
    check('all_planned_rows',len(rows)==len(events)*3*5*3)
    save_json(DEST/'validation.json',dict(status='PASS' if all(c['passed'] for c in checks) else 'FAIL',checks=checks,rows=len(rows),allocation_path=str(allocations),allocation_sha256=sha(allocations),note='Only entry purchases replaced; same budget and fees; historical industry proxy; no future outcome selection'))
    assert all(c['passed'] for c in checks);print('PASS',len(checks),'checks;',len(rows),'planned comparisons')

def interval(x):
    x=np.asarray(x,float);n=len(x);B=2000;L=3
    if n<2*L:return np.nan,np.nan,np.nan
    rng=np.random.default_rng(20261116);starts=rng.integers(0,n,(B,int(np.ceil(n/L))));idx=((starts[:,:,None]+np.arange(L))%n).reshape(B,-1)[:,:n];means=x[idx].mean(axis=1)
    lo,hi=np.quantile(means,[.025,.975]);p=(1+np.sum(np.abs(means-x.mean())>=abs(x.mean())))/(B+1)
    return lo,hi,p

def analyze():
    f=pd.read_csv(DEST/'episodes.csv');summary=[];years=[];used=[]
    for scope,flag in [('primary','primary_eligible'),('full','full_eligible')]:
        for (model,cost,window),g in f.loc[f[flag]].groupby(['model','cost','window']):
            good=g.loc[g.status.eq('OBSERVED')];common=set.intersection(*[set(good.loc[good.control.eq(c),'event']) for c in CONTROLS])
            for control in CONTROLS:
                h=good.loc[good.control.eq(control)&good.event.isin(common)].sort_values('month');x=h.increment;lo,hi,p=interval(x.to_numpy())
                summary.append(dict(scope=scope,model=model,cost=cost,window=window,control=control,planned_events=g.event.nunique(),paired_events=len(h),mean_model_contribution=h.model_entry_contribution.mean(),mean_control_contribution=h.control_entry_contribution.mean(),mean_increment=x.mean(),median_increment=x.median(),positive_fraction=x.gt(0).mean(),ci_low=lo,ci_high=hi,p_raw=p,mean_entry_budget_fraction=h.entry_budget_fraction.mean(),mean_basket_difference=(h.selected_basket_return-h.control_basket_return).mean()))
                for year,z in h.groupby(h.month.str[:4]):years.append(dict(scope=scope,model=model,cost=cost,window=window,control=control,year=year,paired_events=len(z),mean_increment=z.increment.mean(),model_contribution=z.model_entry_contribution.mean(),control_contribution=z.control_entry_contribution.mean()))
                used.extend(dict(scope=scope,model=model,cost=cost,window=window,control=control,event=e) for e in sorted(common))
    s=pd.DataFrame(summary);s['primary_holm_p']=np.nan
    mask=s.scope.eq('primary')&s.cost.eq('main')&s.window.eq('actual_phase2_open');p=s.loc[mask,'p_raw'].dropna().sort_values();s.loc[p.index,'primary_holm_p']=np.maximum.accumulate(p.to_numpy()*np.arange(len(p),0,-1)).clip(0,1)
    s.to_csv(DEST/'summary.csv',index=False);pd.DataFrame(years).to_csv(DEST/'annual_summary.csv',index=False);pd.DataFrame(used).to_csv(DEST/'comparison_events.csv',index=False)
    print(s.loc[mask,['model','control','paired_events','mean_increment','ci_low','ci_high','primary_holm_p']].to_string(index=False))

if __name__=='__main__':{'freeze':freeze,'run':run,'analyze':analyze}[sys.argv[1]]()
