"""Disjoint peer extension after finding substantial self-overlap in matching."""
import json,sys
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from common import EP,OUT,PRIVATE,sha,save_json,protocol
from backtest import Inputs
from suspension_sensitivity import marks
from q5_entry_matched_controls import DEST as SOURCE,interval

RUN='q5_entry_disjoint_controls_20261116';DEST=OUT/'diagnostics'/RUN;LEDGER=PRIVATE/RUN;CONFIG=EP/'configs'/f'{RUN}.json'

def disjoint_allocation(budget,groups):
    """Keep unmatched source groups identical; swap all matched budget to nonentries."""
    selected=budget>0;out=budget.copy();matched=np.zeros(len(budget),bool)
    for group in set(groups[selected]):
        own=selected&(groups==group);peers=(~selected)&(groups==group)
        if peers.any():out[own]=0.;out[peers]+=budget[own].sum()/peers.sum();matched[own]=True
    return out,matched

def freeze():
    if CONFIG.exists():raise RuntimeError('Already frozen')
    DEST.mkdir(parents=True);LEDGER.mkdir(parents=True)
    source=json.loads((SOURCE/'validation.json').read_text());assert source['status']=='PASS' and sha(source['allocation_path'])==source['allocation_sha256']
    allocation=pd.read_parquet(source['allocation_path']);rows=[];cover=[]
    save_json(CONFIG,dict(created_at=datetime.now(timezone.utc).isoformat(),authorization='Continue investigating; independent-overlap check motivated by 65-69 percent selected-name weight in fine matching',prior_control_results_seen=True,source=str(SOURCE),scope='main cost only; fixed industry and industry+prior20-return quintile peers, same original bins; no new bin/threshold search',rule='For each source group, exclude every originally purchased new-entry name from peers. If peers exist, replace that entire group buy principal equally among nonentry peers; otherwise keep original group unchanged in both portfolios and disclose unmatched budget. Never replace with cash or a broader group.',estimand='Full-capital contribution difference and matched-capital basket-return difference; no claim for unmatched capital. Same fees and total principal; all other holdings/trades unchanged.',uncertainty='3-observation circular blocks,2000 reps,seed20261116; primary family6 tests (3models x2controls) at actual-phase2 endpoint; centered-bootstrap p/Holm descriptive, posthoc not independent validation',data_policy='Use original eligible pool determined at entry, no forward-price filtering; match allocations frozen before new outcomes; inherited unavailable windows stay unavailable'))
    for event,g in allocation.groupby('event'):
        pool=g.loc[g.control.eq('market_ew')].sort_values('instrument').set_index('instrument')
        budget=g.loc[g.control.eq('model')].set_index('instrument').allocation_fraction.reindex(pool.index,fill_value=0).to_numpy();assert budget.sum()>0
        model=event.split('_')[0]
        for control,column in [('industry_disjoint','industry'),('industry_r20_disjoint','r20_bucket')]:
            weights,matched=disjoint_allocation(budget,pool[column].to_numpy());total=budget.sum();m=budget[matched].sum()
            assert np.isclose(weights.sum(),total) and not np.any((weights>0)&matched)
            cover.append(dict(event=event,model=model,month=event.split('_',1)[1],control=control,entry_date=pool.entry_date.iloc[0],original_entry_budget=total,matched_budget=m,matched_fraction=m/total,unmatched_fraction=1-m/total,peer_count=int(((weights>0)&(budget==0)).sum()),matched_original_names=int(matched.sum()),original_names=int((budget>0).sum())))
            for j,(instrument,r) in enumerate(pool.iterrows()):
                if budget[j]>0 or weights[j]>0:rows.append(dict(event=event,model=model,control=control,instrument=instrument,entry_date=r.entry_date,model_weight=budget[j],control_weight=weights[j],matched_source=bool(matched[j]),unmatched_source=bool(budget[j]>0 and not matched[j]),group=r[column]))
    weights=LEDGER/'allocations.parquet';pd.DataFrame(rows).to_parquet(weights,index=False);pd.DataFrame(cover).to_csv(DEST/'coverage.csv',index=False)
    parent=json.loads((SOURCE/'freeze.json').read_text());save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),coverage_sha256=sha(DEST/'coverage.csv'),allocation_path=str(weights),allocation_sha256=sha(weights),inputs=parent['inputs']+[dict(path=str(SOURCE/'episodes.csv'),sha256=sha(SOURCE/'episodes.csv')),dict(path=source['allocation_path'],sha256=source['allocation_sha256'])],source_sha256=sha(EP/'src/q5_entry_disjoint_controls.py')))
    print('Frozen disjoint peer allocations')

def run():
    frozen=json.loads((DEST/'freeze.json').read_text());assert sha(EP/'src/q5_entry_disjoint_controls.py')==frozen['source_sha256'];assert sha(CONFIG)==frozen['config_sha256'];assert sha(frozen['allocation_path'])==frozen['allocation_sha256'];assert sha(DEST/'coverage.csv')==frozen['coverage_sha256']
    for x in frozen['inputs']:assert sha(x['path'])==x['sha256']
    weights=pd.read_parquet(frozen['allocation_path']);coverage=pd.read_csv(DEST/'coverage.csv').set_index(['event','control']);source=pd.read_csv(SOURCE/'episodes.csv',parse_dates=['entry_date','exit_date']);source=source.loc[source.cost.eq('main')&source.control.eq('market_ew')]
    inp=Inputs();marks(inp,0.);bf=protocol()['costs_bps']['main'][0]/10000;rows=[];checks=[]
    def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
    for (event,control),g in weights.groupby(['event','control']):
        c=coverage.loc[(event,control)];indices=inp.symbols.get_indexer(g.instrument);assert (indices>=0).all();model=g.model_weight.to_numpy();peer=g.control_weight.to_numpy();matched=g.matched_source.to_numpy(bool);unmatched=g.unmatched_source.to_numpy(bool)
        check(event+control+'_no_overlap_for_matched',not np.any(peer[matched]>0) and np.allclose(model[unmatched],peer[unmatched]))
        check(event+control+'_group_budget',all(np.isclose(g.loc[g.group.eq(k),'model_weight'].sum(),g.loc[g.group.eq(k),'control_weight'].sum(),atol=1e-12) for k in g.group.unique()))
        for r in source.loc[source.event.eq(event)].itertuples():
            base=dict(event=event,model=r.model,month=r.month,control=control,window=r.window,entry_date=r.entry_date,exit_date=r.exit_date,primary_eligible=r.primary_eligible,full_eligible=r.full_eligible,matched_budget=c.matched_budget,matched_fraction=c.matched_fraction)
            if r.status!='OBSERVED' or c.matched_budget<=0:
                rows.append({**base,'status':'BLOCKED','reason':r.reason if r.status!='OBSERVED' else 'NO_INDEPENDENT_MATCH'});continue
            ei=inp.days.get_loc(r.entry_date);end=inp.days.get_loc(r.exit_date);valid=(model>0)|(peer>0)
            if np.any(~np.isfinite(inp.o[end,indices[valid]])) or np.any(~np.isfinite(inp.c[ei:end,indices[valid]])):
                rows.append({**base,'status':'BLOCKED','reason':'MATCHED_PAIR_VALUATION_UNKNOWN'});continue
            ret=inp.o[end,indices]/inp.o[ei,indices]-1
            own=np.dot(model,ret)-model.sum()*bf;bench=np.dot(peer,ret)-peer.sum()*bf;delta=own-bench
            ownmatched=np.dot(model[matched],ret[matched])-c.matched_budget*bf
            independent=(model==0)&(peer>0);peermatched=np.dot(peer[independent],ret[independent])-c.matched_budget*bf
            check(event+control+r.window+'_matched_decomposition',np.isclose(delta,ownmatched-peermatched,atol=1e-10))
            rows.append({**base,'status':'OBSERVED','reason':'','increment':delta,'matched_capital_difference':delta/c.matched_budget,'model_entry_contribution':own,'control_entry_contribution':bench,'matched_model_return':ownmatched/c.matched_budget,'matched_peer_return':peermatched/c.matched_budget})
    f=pd.DataFrame(rows);f.to_csv(DEST/'episodes.csv',index=False);summary=[];years=[]
    for scope,flag in [('primary','primary_eligible'),('full','full_eligible')]:
        for (model,window),g in f.loc[f[flag]].groupby(['model','window']):
            good=g.loc[g.status.eq('OBSERVED')];common=set(good.loc[good.control.eq('industry_disjoint'),'event'])&set(good.loc[good.control.eq('industry_r20_disjoint'),'event'])
            for control in ['industry_disjoint','industry_r20_disjoint']:
                h=good.loc[good.control.eq(control)&good.event.isin(common)].sort_values('month');lo,hi,p=interval(h.increment.to_numpy());ml,mh,mp=interval(h.matched_capital_difference.to_numpy())
                summary.append(dict(scope=scope,model=model,window=window,control=control,paired_events=len(h),mean_increment=h.increment.mean(),ci_low=lo,ci_high=hi,p_raw=p,mean_matched_fraction=h.matched_fraction.mean(),mean_matched_capital_difference=h.matched_capital_difference.mean(),matched_capital_ci_low=ml,matched_capital_ci_high=mh))
                for year,z in h.groupby(h.month.str[:4]):years.append(dict(scope=scope,model=model,window=window,control=control,year=year,events=len(z),mean_increment=z.increment.mean(),matched_capital_difference=z.matched_capital_difference.mean()))
    s=pd.DataFrame(summary);s['primary_holm_p']=np.nan;mask=s.scope.eq('primary')&s.window.eq('actual_phase2_open');p=s.loc[mask,'p_raw'].dropna().sort_values();s.loc[p.index,'primary_holm_p']=np.maximum.accumulate(p.to_numpy()*np.arange(len(p),0,-1)).clip(0,1)
    s.to_csv(DEST/'summary.csv',index=False);pd.DataFrame(years).to_csv(DEST/'annual_summary.csv',index=False)
    check('planned_rows',len(rows)==207*5*2);save_json(DEST/'validation.json',dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',checks=checks,rows=len(rows),note='unmatched allocation unchanged, no matched selected-name overlap; no claims for unmatched budget'))
    assert all(x['passed'] for x in checks);print('PASS',len(checks),'checks');print(s.loc[mask].to_string(index=False))

if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()
