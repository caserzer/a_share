"""E02B uniform boundary correction; frozen matching and full-calendar deadlines."""
import json
import argparse
import re
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha


def select_primary(pid,parent_valid,cid,child_valid,child_unknown,seen_parent,seen_child):
    if cid is not None and child_valid and cid not in seen_child:return cid,'CHILD','COVERED'
    if parent_valid and pid not in seen_parent:return pid,'PARENT','COVERED'
    if child_unknown:return None,None,'UNKNOWN_ENHANCEMENT'
    if parent_valid:return None,None,'REPEAT'
    return None,None,'NO_CURRENT_ALIGNMENT'


def checks():
    result=[];sp=set();sc=set()
    assert select_primary('p',False,None,False,False,sp,sc)[2]=='NO_CURRENT_ALIGNMENT'
    result.append('failed event does not claim process')
    assert select_primary('p',True,None,False,False,sp,sc)==('p','PARENT','COVERED')
    sp.add('p');assert select_primary('p',True,None,False,False,sp,sc)[2]=='REPEAT'
    result.append('later NEW or UPDATE claims once; repeated event not credited')
    assert select_primary('p',True,'c',True,False,sp,sc)==('c','CHILD','COVERED')
    sc.add('c');assert select_primary('p',True,'c',True,False,sp,sc)[2]=='REPEAT'
    result.append('new enhancement can be claimed once after parent coverage')
    assert select_primary('q',True,'bad',False,False,sp,sc)==('q','PARENT','COVERED')
    result.append('failed enhancement does not erase valid first parent observation')
    assert select_primary('q',True,'unknown',False,True,sp,sc)==('q','PARENT','COVERED')
    sp.add('q');assert select_primary('q',True,'unknown',False,True,sp,sc)[2]=='UNKNOWN_ENHANCEMENT'
    result.append('unknown enhancement remains unknown after parent already observed')
    sp=set();sc=set();primary,kind,status=select_primary('z',True,'zc',True,False,sp,sc)
    assert (primary,kind,status)==('zc','CHILD','COVERED');sp.add('z');sc.add('zc')
    assert len(sp)==len(sc)==1
    result.append('child main identity yields one primary credit and parent union separately')
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tag',required=True)
    parser.add_argument('--observation-dir',type=Path,required=True)
    parser.add_argument('--parent-dir',type=Path,default=EP/'outputs/v2_s12_full_directory_duration')
    parser.add_argument('--child-dir',type=Path,default=EP/'outputs/v2_s13_duration_enhancements')
    args=parser.parse_args()
    for tag in [args.tag]:
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}',tag):raise ValueError('Invalid immutable version tag')
    out=EP/'outputs/evaluation_versions'/args.tag
    if out.exists():raise FileExistsError('Preserve evaluation version')
    observation=args.observation_dir
    def verify_artifacts(directory):
        receipt=json.loads((directory/'receipt.json').read_text())
        for rel,digest in receipt['artifacts'].items():
            if sha(directory/rel)!=digest:raise ValueError('Artifact hash mismatch: '+rel)
        return receipt
    obsrec=verify_artifacts(observation);parrec=verify_artifacts(args.parent_dir);chrec=verify_artifacts(args.child_dir)
    parfile=args.parent_dir/'processes.parquet';chfile=args.child_dir/'children.parquet';weekfile=args.parent_dir/'boundary_audit/weekly_evaluation_states.parquet'
    boundrec=verify_artifacts(args.parent_dir/'boundary_audit')
    if boundrec['inputs'].get(str(parfile))!=sha(parfile):raise ValueError('Boundary/parent label mismatch')
    rawpath=Path(next(k for k in parrec['inputs'] if k.endswith('/daily_industries.parquet')))
    calpath=Path(next(k for k in parrec['inputs'] if k.endswith('/calendar.parquet')))
    if parrec['inputs'][str(rawpath)]!=sha(rawpath) or parrec['inputs'][str(calpath)]!=sha(calpath):raise ValueError('Parent label source vintage mismatch')
    if chrec['inputs'].get(str(rawpath))!=sha(rawpath) or chrec['inputs'].get(str(parfile))!=sha(parfile):raise ValueError('Child/parent source vintage mismatch')
    if boundrec['inputs'].get(str(rawpath))!=sha(rawpath):raise ValueError('Boundary raw vintage mismatch')
    sources=[EP/'protocols/v3_r00/boundary_timing_correction.md',parfile,chfile,weekfile,rawpath,EP/'protocols/v2_revaluation02/plan.md',Path(__file__),EP/'protocols/v2_s04/plan.md',EP/'protocols/v2_s05/plan.md',calpath,
             observation/'receipt.json',observation/'calendar_coverage.csv',args.parent_dir/'receipt.json',args.child_dir/'receipt.json',args.parent_dir/'boundary_audit/receipt.json',EP/'protocols/v2_e02_context/versioned_workflow_addendum.md']
    runs=sorted(observation.glob('*/events.parquet'));assert len(runs)==2
    assert {p.parent.name for p in runs}=={'solo_BALANCED_COMPETE','solo_BROAD20_COMPETE'}
    support=pd.read_csv(observation/'calendar_coverage.csv',parse_dates=['date'])
    support=support[support.state.eq('SUPPORTED_DIRECTORY')]
    scope_start=str(support.date.min().date());scope_end=str(support.date.max().date())
    def intersects(obj):return obj['start_date']<=scope_end and obj['end_date']>=scope_start
    out.mkdir(parents=True);(out/'accounting_checks.json').write_text(json.dumps(checks(),indent=2)+'\n')
    (out/'version.json').write_text(json.dumps(dict(tag=args.tag,observation_tag=str(observation),parent_dir=str(args.parent_dir),child_dir=str(args.child_dir),
        evaluation_protocol='E02B_FULL_CALENDAR_TIMING',no_process_support_weeks=8,boundary_states=str(weekfile),observation_scope_start=scope_start,observation_scope_end=scope_end,raw_path=str(rawpath),calendar_path=str(calpath),source_data_cutoff=str(pd.read_parquet(rawpath,columns=['date']).date.max().date()),
        observation_event_paths=[str(x) for x in runs],interpretation='Retrospective evaluation; never contemporaneous signal input'),indent=2)+'\n')
    hashes={str(p):sha(p) for p in sources+runs}
    (out/'started.json').write_text(json.dumps(dict(inputs=hashes,runs=len(runs)),indent=2)+'\n')
    parents=pd.read_parquet(parfile);children=pd.read_parquet(chfile);weeks=pd.read_parquet(weekfile)
    raw=pd.read_parquet(rawpath,columns=['era','industry_code','block','date','day_i','nav'])
    raw=raw[raw.nav.gt(0)&raw.block.notna()].copy();raw['week']=raw.date.dt.to_period('W-SUN').astype(str)
    raw['y']=np.log(raw.nav)
    weekly=raw.groupby(['era','industry_code','block','week']).y.median().to_dict()
    prices={(r.era,r.industry_code,int(r.block),str(r.date.date())):(float(r.nav),int(r.day_i)) for r in raw.itertuples()}
    calendar=pd.read_parquet(calpath);calendar['week']=calendar.date.dt.to_period('W-SUN')
    reviews=calendar.groupby('week').date.max()
    if calendar.date.max().weekday()<4:reviews=reviews.iloc[:-1]
    reviewdates=[str(x.date()) for x in reviews if scope_start<=str(x.date())<=scope_end];dayids={str(d.date()):i for i,d in enumerate(calendar.date)}
    full_reviewdates=[str(x.date()) for x in reviews]
    def timely(date):
        j=np.searchsorted(full_reviewdates,date)
        return full_reviewdates[min(j+1,len(full_reviewdates)-1)]
    pmap=parents.set_index('process_id').to_dict('index');cmap=children.set_index('child_id').to_dict('index')
    for p in pmap.values():
        p['baseline']=np.exp(weekly[(p['era'],p['industry_code'],p['block'],str(pd.Timestamp(p['start_date']).to_period('W-SUN')))])
        p['timely_end']=timely(p['visible_date'])
    for c in cmap.values():
        c['baseline']=np.exp(weekly[(c['era'],c['industry_code'],c['block'],str(pd.Timestamp(c['start_date']).to_period('W-SUN')))])
        c['timely_end']=timely(c['start_date'])
    cmap_by_parent={k:g.to_dict('records') for k,g in children.groupby('parent_id')}
    wmap={}
    for key,g in weeks.groupby(['era','industry_code','block']):
        g=g.sort_values('week').copy();g['run']=g.state.eq('PARTIAL_WEEK_UNKNOWN').cumsum()
        for _,ww in g.groupby('run'):
            good=ww[~ww.state.eq('PARTIAL_WEEK_UNKNOWN')]
            remaining={i:len(good)-1-j for j,i in enumerate(good.index)}
            for i,w in ww.iterrows():
                wmap[(*key,w.week)]=(w.state,w.process_id,remaining.get(i,0))
    knownp={k:v for k,v in pmap.items() if v['status']=='CONFIRMED' and not v['left_context_unknown'] and intersects(v)}
    knownc={k:v for k,v in cmap.items() if v['status']=='PATH_SUPPORTED' and v['parent_id'] in knownp and intersects(v)}
    inventory=[]
    for kind,objects,known in [('PARENT',pmap,knownp),('CHILD',cmap,knownc)]:
        for oid,obj in objects.items():
            inventory.append(dict(kind=kind,version_id=oid,era=obj['era'],industry_code=obj['industry_code'],block=obj['block'],
                start_date=obj['start_date'],end_date=obj['end_date'],status=obj['status'],scope_intersects=intersects(obj),
                crosses_scope_start=obj['start_date']<scope_start<=obj['end_date'],in_denominator=oid in known))
    pd.DataFrame(inventory).to_parquet(out/'denominator_inventory.parquet',index=False)
    cache={};summaries=[]
    def context(era,code,block,date):
        key=(era,code,block,date)
        if key in cache:return cache[key]
        price=prices.get(key);state,pid,future=wmap.get((era,code,block,str(pd.Timestamp(date).to_period('W-SUN'))),('MISSING',None,0))
        if pd.isna(pid):pid=None
        cid=None
        if pid is not None:
            matches=[c for c in cmap_by_parent.get(pid,[]) if c['start_date']<=date<=c['end_date']]
            assert len(matches)<=1
            if matches:cid=matches[0]['child_id']
        val=(price,state,pid,cid,future);cache[key]=val;return val
    for path in runs:
        runid=path.parent.name;dest=out/'runs'/runid;dest.mkdir(parents=True)
        ev=pd.read_parquet(path);assert ev.event_id.is_unique
        seenp={};seenc={};ledger=[]
        for row in ev[ev.kind.isin(['NEW','UPDATE'])].sort_values(['date','event_id']).itertuples():
            date=str(row.date.date());block=int(row.block) if pd.notna(row.block) else -1
            price,state,pid,cid,future=context(row.era,row.industry_code,block,date)
            p=pmap.get(pid);c=cmap.get(cid);primary=None;ptype=None;timing=None;gain=None;lag=None;confirm_delay=None
            if price is None or state in ('MISSING','PARTIAL_WEEK_UNKNOWN','CONTEXT_INSUFFICIENT'):
                status='UNKNOWN_DATA_OR_CONTEXT'
            elif pid is None:
                status=state if state in ('DURATION_RIGHT_UNKNOWN','RIGHT_CONTEXT_UNKNOWN') else 'NO_PROCESS' if future>=8 else 'RIGHT_CONTEXT_UNKNOWN'
            elif p['left_context_unknown'] or p['status']=='RIGHT_UNKNOWN':status='UNKNOWN_PROCESS'
            elif p['status']!='CONFIRMED':status='SHORT_OR_UNCONFIRMED_PROCESS'
            elif not bool(row.positive_evidence):status='NO_PRICE_EVIDENCE'
            else:
                parent_valid=price[0]>p['baseline']
                child_alignment=c is not None and bool(row.enhancement_evidence) and price[0]>c['baseline']
                child_valid=child_alignment and cid in knownc
                child_unknown=child_alignment and c['status']=='RIGHT_UNKNOWN'
                primary,ptype,status=select_primary(pid,parent_valid,cid,child_valid,child_unknown,seenp,seenc)
                if status=='COVERED':
                    obj=p if ptype=='PARENT' else c
                    timing='TIMELY' if date<=obj['timely_end'] else 'LATE'
                    gain=price[0]/obj['baseline']-1;lag=price[1]-dayids[obj['start_date']]
                    confirm_delay=max(0,dayids[obj['confirm_date']]-price[1]) if obj['confirm_date'] is not None else None
                    hit=dict(event_id=row.event_id,date=date,kind=row.kind,timing=timing,primary_id=primary,
                             pre_gain=gain,lag_days=lag,confirmation_delay=confirm_delay)
                    if ptype=='CHILD':seenc[cid]=hit
                    if pid not in seenp:
                        phit=hit.copy();phit['timing']='TIMELY' if date<=p['timely_end'] else 'LATE'
                        phit['lag_days']=price[1]-dayids[p['start_date']];phit['pre_gain']=price[0]/p['baseline']-1
                        phit['confirmation_delay']=max(0,dayids[p['confirm_date']]-price[1])
                        seenp[pid]=phit
            ledger.append(dict(run_id=runid,event_id=row.event_id,date=date,era=row.era,industry_code=row.industry_code,
                kind=row.kind,parent_id=pid,child_candidate=cid,child_candidate_status=None if c is None else c['status'],
                primary_id=primary,primary_type=ptype,status=status,timing=timing,pre_gain=gain,
                lag_days=lag,confirmation_delay=confirm_delay,weekly_state=state))
        le=pd.DataFrame(ledger)
        def coverage(objects,hits):
            rows=[]
            for oid,o in objects.items():
                h=hits.get(oid)
                rows.append(dict(process_id=oid,era=o['era'],industry_code=o['industry_code'],start=o['start_date'],
                    right_open=o.get('right_open',o.get('end_unknown')),covered=h is not None,
                    first_date=None if h is None else h['date'],source=None if h is None else h['kind'],
                    timing=None if h is None else h['timing'],primary_id=None if h is None else h['primary_id'],
                    lag_days=None if h is None else h['lag_days'],pre_gain=None if h is None else h['pre_gain'],
                    confirmation_delay=None if h is None else h['confirmation_delay']))
            return pd.DataFrame(rows)
        pc=coverage(knownp,seenp);cc=coverage(knownc,seenc)
        assert set(seenp)<=set(knownp) and set(seenc)<=set(knownc)
        assert le.loc[le.status.eq('COVERED'),'primary_id'].is_unique
        assert len(seenp)==int(pc.covered.sum()) and len(seenc)==int(cc.covered.sum())
        new=le[le.kind.eq('NEW')];unknown=new.status.str.contains('UNKNOWN');eff=new.status.eq('COVERED')
        workload=ev.groupby('date').kind.value_counts().unstack(fill_value=0).reindex(pd.to_datetime(reviewdates),fill_value=0)
        for k in ['NEW','EXIT','UPDATE']:
            if k not in workload:workload[k]=0
        workload['pool']=(workload.NEW-workload.EXIT).cumsum()
        assert workload.NEW.max()<=5 and workload.pool.between(0,20).all(),runid
        summary=dict(run_id=runid,parent_total=len(pc),parent_covered=len(seenp),parent_missed=len(pc)-len(seenp),
            parent_coverage=len(seenp)/len(pc),parent_timely=int(pc.timing.eq('TIMELY').sum()),parent_late=int(pc.timing.eq('LATE').sum()),
            child_total=len(cc),child_covered=len(seenc),child_missed=len(cc)-len(seenc),child_coverage=len(seenc)/len(cc),
            new_total=len(new),new_unknown=int(unknown.sum()),new_evaluable=int((~unknown).sum()),new_effective=int(eff.sum()),
            new_effective_rate=float(eff.sum()/(~unknown).sum()),
            new_all_lower=float(eff.mean()),new_all_upper=float((eff|unknown).mean()),
            new_repeat=int(new.status.eq('REPEAT').sum()),new_status=new.status.value_counts().to_dict(),
            update_status=le[le.kind.eq('UPDATE')].status.value_counts().to_dict(),
            parent_source=pc[pc.covered].source.value_counts().to_dict(),child_source=cc[cc.covered].source.value_counts().to_dict(),
            new_week_median=float(workload.NEW.median()),new_week_p90=float(workload.NEW.quantile(.9)),new_week_max=int(workload.NEW.max()),
            pool_median=float(workload.pool.median()),pool_p90=float(workload.pool.quantile(.9)),pool_max=int(workload.pool.max()),
            updates=int(workload.UPDATE.sum()))
        le.to_parquet(dest/'event_quality.parquet',index=False);pc.to_parquet(dest/'parent_coverage.parquet',index=False);cc.to_parquet(dest/'child_coverage.parquet',index=False)
        support=pd.read_csv(observation/'calendar_coverage.csv',parse_dates=['date']).set_index('date').state
        workload['directory_state']=support.reindex(workload.index).fillna('OUTSIDE_OBSERVATION_SCOPE_UNKNOWN')
        unsupported=workload.directory_state.ne('SUPPORTED_DIRECTORY')
        workload.loc[unsupported,['NEW','EXIT','UPDATE','pool']]=np.nan
        for metric,column,quantile in [('new_week_median','NEW',.5),('new_week_p90','NEW',.9),('pool_median','pool',.5),('pool_p90','pool',.9)]:
            summary[metric]=float(workload[column].quantile(quantile))
        summary['workload_unknown_weeks']=int(unsupported.sum())
        summary['workload_supported_weeks']=int((~unsupported).sum())
        workload.to_csv(dest/'workload.csv')
        pc.assign(year=pc.start.str[:4]).groupby(['era','year']).agg(processes=('process_id','size'),covered=('covered','sum')).to_csv(dest/'parent_annual.csv')
        new.assign(year=new.date.str[:4]).groupby(['era','year','status']).size().rename('count').to_csv(dest/'new_annual.csv')
        (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        summaries.append(summary)
        if len(summaries)%20==0:print(f'Completed {len(summaries)}/{len(runs)} runs',flush=True)
    pd.DataFrame([{k:v for k,v in s.items() if not isinstance(v,dict)} for s in summaries]).to_csv(out/'all_run_summary.csv',index=False)
    for path in runs:assert sha(path)==hashes[str(path)],path
    summary=dict(scope='Uniform retrospective revaluation under preregistered corrected accounting; not independent validation',
                 runs=len(summaries),known_parent_denominator=len(knownp),known_child_denominator=len(knownc),
                 original_event_hashes_unchanged=True,unique_contexts=len(cache),all_runs_capacity_pass=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs=hashes,
        artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}),indent=2)+'\n')
    print(json.dumps(summary,indent=2));print(json.dumps(summaries[0],indent=2))


if __name__=='__main__':main()
