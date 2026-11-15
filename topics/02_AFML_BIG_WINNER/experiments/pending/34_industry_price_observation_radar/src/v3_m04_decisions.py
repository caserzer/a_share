"""Reconstruct online decisions, then attach retrospective miss diagnostics."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def main():
    replay=EP/'outputs/v3_m04_replay';evaluation=EP/'outputs/evaluation_versions/v3_m04';out=EP/'outputs/v3_m04_decisions'
    if out.exists():raise FileExistsError(out)
    out.mkdir();scorepath=EP/'outputs/v3_m04_models/scored_catalog.parquet'
    arms=['ORIGINAL20','DATE_COVER','DATE_EARLY','DATE_BALANCED','PROCESS_COVER','PROCESS_EARLY','PROCESS_BALANCED']
    cols=['date','era','industry_code','block','nav','r5','r20','r40','week','eligible','eligible_original','confirmed','confirmed_original']+['score_'+a for a in arms if a!='ORIGINAL20']
    c=pd.read_parquet(scorepath,columns=cols);c['score_ORIGINAL20']=c.r20
    inventory=pd.read_csv(replay/'run_inventory.csv');summaries=[];misses=[];transitions=[]
    parents=pd.read_parquet(EP/'outputs/v2_s12_full_directory_duration/processes.parquet').set_index('process_id')
    wpath=EP/'outputs/v2_s12_full_directory_duration/boundary_audit/weekly_evaluation_states.parquet'
    states=pd.read_parquet(wpath,columns=['era','industry_code','block','week','process_id']).rename(columns={'week':'calendar_week'})
    rawpath=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawpath,columns=['era','industry_code','block','date','nav'])
    raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['calendar_week']=raw.date.dt.to_period('W-SUN').astype(str);raw['lognav']=np.log(raw.nav)
    med=raw.groupby(['era','industry_code','block','calendar_week']).lognav.median().to_dict()
    baseline={pid:float(np.exp(med[(r.era,r.industry_code,r.block,str(pd.Timestamp(r.start_date).to_period('W-SUN')))])) for pid,r in parents.iterrows()}
    base=pd.read_parquet(evaluation/'runs/solo_ORIGINAL20/parent_coverage.parquet').set_index('process_id')
    for run in inventory.itertuples():
        evpath=replay/run.run_id/'events.parquet';ev=pd.read_parquet(evpath);events={d:g for d,g in ev.groupby('date')};pool=set();exits={};rows=[]
        for date,g in c.groupby('date',sort=True):
            week=int(g.week.iloc[0]);e=events.get(date,ev.iloc[:0]);expired=set(map(tuple,e.loc[e.kind.eq('EXIT'),['era','industry_code']].values))
            assert expired<=pool
            pool-=expired
            for key in expired:exits[key]=week
            updated=set(map(tuple,e.loc[e.kind.eq('UPDATE'),['era','industry_code']].values));assert updated==pool
            column=('confirmed_original' if run.arm=='ORIGINAL20' else 'confirmed') if run.delay else ('eligible_original' if run.arm=='ORIGINAL20' else 'eligible')
            ranked=g[g[column]].sort_values(['score_'+run.arm,'industry_code'],ascending=[False,True])
            ordered=[(r.era,r.industry_code) for r in ranked.itertuples() if (r.era,r.industry_code) not in pool and week-exits.get((r.era,r.industry_code),-100)>=4]
            rank={k:i+1 for i,k in enumerate(ordered)};free=20-len(pool);own=min(run.quota,free,len(ordered))
            added=set(map(tuple,e.loc[e.kind.eq('NEW'),['era','industry_code']].values));q=len(added)
            assert q<=own and added==set(ordered[:q]),(run.run_id,date)
            if run.mode=='solo':assert q==own
            actual={(r.era,r.industry_code):r.kind for r in e.itertuples()}
            for r in g.itertuples():
                key=(r.era,r.industry_code)
                rows.append(dict(date=date,era=r.era,industry_code=r.industry_code,block=r.block,nav=r.nav,r5=r.r5,r20=r.r20,
                    known_support=bool(np.isfinite(r.r40) and np.isfinite(r.r5)),eligible=bool(getattr(r,column)),in_pool_before=key in pool,
                    cooldown=week-exits.get(key,-100)<4,candidate_rank=rank.get(key),free_slots=free,own_quota=own,actual_quota=q,actual_kind=actual.get(key,'NONE')))
            pool|=added;assert len(pool)<=20
        trace=pd.DataFrame(rows);assert len(trace)==len(c)
        trace.to_parquet(out/(run.run_id+'_online_decisions.parquet'),index=False)
        # Labels are attached only now; they never influence reconstructed admissions.
        trace['calendar_week']=trace.date.dt.to_period('W-SUN').astype(str)
        labeled=trace.merge(states,on=['era','industry_code','block','calendar_week'],how='left',validate='one_to_one')
        groups={pid:g for pid,g in labeled.groupby('process_id')}
        pc=pd.read_parquet(evaluation/'runs'/run.run_id/'parent_coverage.parquet')
        for p in pc[~pc.covered].itertuples():
            g=groups.get(p.process_id)
            if g is None:
                reason='NO_SUPPORTED_DIRECTORY_REVIEW';n=0;seen=0
            else:
                n=len(g);positive=g[g.known_support&g.r5.gt(0)&g.nav.gt(baseline[p.process_id])];seen=len(positive);blocked=set()
                assert not positive.actual_kind.isin(['NEW','UPDATE']).any(),(run.run_id,p.process_id,'uncredited positive event')
                if positive.empty:blocked.add('NO_SUPPORTED_POSITIVE_ALIGNMENT')
                for z in positive.itertuples():
                    if not z.eligible:blocked.add('ADMISSION_GATE');continue
                    if z.cooldown:blocked.add('COOLDOWN');continue
                    assert not z.in_pool_before and pd.notna(z.candidate_rank)
                    if z.candidate_rank>run.quota:blocked.add('RANK_BELOW_WEEKLY_CAP')
                    if z.candidate_rank>z.free_slots:blocked.add('POOL_CAPACITY')
                    if z.actual_quota<z.own_quota and z.actual_quota<z.candidate_rank<=z.own_quota:blocked.add('PAIRED_THROTTLE')
                    assert z.candidate_rank>z.actual_quota
                assert blocked;reason='|'.join(sorted(blocked))
            misses.append(dict(run_id=run.run_id,process_id=p.process_id,review_rows=n,positive_aligned_rows=seen,observed_constraints=reason))
        q=pc.set_index('process_id');assert set(q.index)==set(base.index)
        for pid,r in q.iterrows():
            b=base.loc[pid];kind='BOTH' if r.covered and b.covered else 'MODEL_ONLY' if r.covered else 'BASE_ONLY' if b.covered else 'NEITHER'
            transitions.append(dict(run_id=run.run_id,process_id=pid,coverage_transition=kind,base_timing=b.timing,model_timing=r.timing,
                discovery_change_days=r.lag_days-b.lag_days if kind=='BOTH' else None,base_source=b.source,model_source=r.source))
        summaries.append(dict(run_id=run.run_id,rows=len(trace),new=int(ev.kind.eq('NEW').sum()),exits=int(ev.kind.eq('EXIT').sum()),
            exit_reasons=ev.loc[ev.kind.eq('EXIT'),'reason'].value_counts().to_dict(),missed=int((~pc.covered).sum()),all_admissions_reconstructed=True))
        print('Decision audit',run.run_id,flush=True)
    mm=pd.DataFrame(misses);mm.to_parquet(out/'all_missed_processes.parquet',index=False)
    mm.groupby(['run_id','observed_constraints']).size().rename('processes').to_csv(out/'miss_constraint_counts.csv')
    tt=pd.DataFrame(transitions);tt.to_parquet(out/'all_coverage_transitions.parquet',index=False)
    tt.groupby(['run_id','coverage_transition']).size().rename('processes').to_csv(out/'coverage_transition_counts.csv')
    (out/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    sources=[scorepath,replay/'receipt.json',evaluation/'receipt.json',wpath,rawpath,EP/'outputs/v2_s12_full_directory_duration/processes.parquet',EP/'protocols/v3_r00/m04_process_weight_plan.md',Path(__file__)]
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in sources},artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()},limits='Observed restrictions only, not counterfactual capture. Retrospective labels attached after causal decisions.'),indent=2)+'\n')


if __name__=='__main__':main()
