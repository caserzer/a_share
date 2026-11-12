"""Explain fixed S01 decisions; no altered policy or retrospective signal inputs."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,sha
from v2_b06_replay import prepare


def trace(c,ev,arm):
    pool=set();exits={};records=[];score='r20' if arm=='A' else 'r5'
    eventgroups={d:g for d,g in ev.groupby('date')}
    for date,g in c.groupby('date',sort=True):
        week=int(g.week.iloc[0]);ee=eventgroups.get(date,ev.iloc[:0])
        def keys(kind):return set(zip(ee.loc[ee.kind.eq(kind),'era'],ee.loc[ee.kind.eq(kind),'industry_code']))
        old=pool.copy();removed=keys('EXIT');assert removed<=pool
        pool-=removed
        for key in removed:exits[key]=week
        assert keys('UPDATE')==pool
        free=20-len(pool)
        ranked=g[g.eligible].sort_values([score,'industry_code'],ascending=[False,True])
        candidates=[(r.era,r.industry_code) for r in ranked.itertuples() if (r.era,r.industry_code) not in pool and week-exits.get((r.era,r.industry_code),-100)>=4]
        ranks={key:i+1 for i,key in enumerate(candidates)};q=min(5,free,len(candidates));new=set(candidates[:q]);assert new==keys('NEW')
        for r in g.itertuples():
            key=(r.era,r.industry_code);rank=ranks.get(key)
            reason=('IN_POOL_UPDATE' if key in pool else 'HISTORY_UNKNOWN' if pd.isna(r.r40) or pd.isna(r.r5) else
                    'NONPOSITIVE_5D' if r.r5<=0 else 'NONPOSITIVE_20D' if r.r20<=0 else
                    'COOLDOWN' if week-exits.get(key,-100)<4 else 'SELECTED_NEW' if key in new else
                    'RANK_BEYOND_WEEKLY_FIVE' if rank>5 else 'POOL_SPACE_LIMIT')
            records.append(dict(arm=arm,date=date,era=r.era,industry_code=r.industry_code,block=r.block,nav=r.nav,
                r5=r.r5,r20=r.r20,r40=r.r40,eligible=r.eligible,reason=reason,candidate_rank=rank,
                pool_after_exit=len(pool),free_slots=free,new_quota=q,exited_now=key in removed,
                cooldown_age=None if key not in exits else week-exits[key]))
        pool|=new
        assert len(pool)<=20 and len(new)<=5
    return pd.DataFrame(records)


def main():
    out=EP/'outputs/v2_e02_context/misses'
    if out.exists():raise FileExistsError('Preserve audit version')
    out.mkdir()
    root=EP/'outputs/refresh/s02_chain_safe_v2_20261112';parentroot=EP/'outputs/v2_s12_full_directory_duration'
    paths=[parentroot/'processes.parquet',parentroot/'boundary_audit/weekly_evaluation_states.parquet',PRIOR/'daily_industries.parquet',
           EP/'outputs/r01/weekly_catalog.parquet',EP/'src/v2_b06_replay.py',EP/'protocols/v2_e02_context/plan.md',Path(__file__)]
    ps=pd.read_parquet(paths[0]);ps=ps[ps.status.eq('CONFIRMED')&~ps.left_context_unknown].copy();assert len(ps)==5795
    ws=pd.read_parquet(paths[1]);ws=ws.rename(columns={'week':'calendar_week'})
    raw=pd.read_parquet(paths[2],columns=['era','industry_code','block','date','nav']);raw=raw[raw.nav.gt(0)&raw.block.notna()].copy()
    raw['calendar_week']=raw.date.dt.to_period('W-SUN').astype(str);raw['lognav']=np.log(raw.nav)
    med=raw.groupby(['era','industry_code','block','calendar_week']).lognav.median()
    baselines={r.process_id:np.exp(med.loc[(r.era,r.industry_code,r.block,str(pd.Timestamp(r.start_date).to_period('W-SUN')))]) for r in ps.itertuples()}
    rec=json.loads((PRIOR/'receipt.json').read_text());calpath=Path(next(k for k in rec['inputs'] if k.endswith('/calendar.parquet')));paths.append(calpath)
    cal=pd.read_parquet(calpath).date;reviews=cal.groupby(cal.dt.to_period('W-SUN')).max()
    if cal.max().weekday()<4:reviews=reviews.iloc[:-1]
    reviewdates=pd.DatetimeIndex(reviews)
    timely={r.process_id:reviewdates[min(reviewdates.searchsorted(pd.Timestamp(r.visible_date))+1,len(reviewdates)-1)] for r in ps.itertuples()}
    c=prepare();summaries=[];checks={}
    for arm in ['A','B']:
        evpath=root/arm/'events.parquet';pcpath=EP/'outputs/v2_revaluation02/runs/refresh/s02_chain_safe_v2_20261112'/arm/'parent_coverage.parquet';paths += [evpath,pcpath]
        ev=pd.read_parquet(evpath);pc=pd.read_parquet(pcpath);tr=trace(c,ev,arm)
        assert len(tr)==141872
        tr['calendar_week']=tr.date.dt.to_period('W-SUN').astype(str)
        tr=tr.merge(ws[['era','industry_code','block','calendar_week','process_id','state']],on=['era','industry_code','block','calendar_week'],how='left',validate='many_to_one')
        tr['baseline']=tr.process_id.map(baselines)
        tr['aligned']=tr.baseline.notna()&tr.r40.notna()&tr.r5.gt(0)&tr.nav.gt(tr.baseline)&~tr.state.isin(['PARTIAL_WEEK_UNKNOWN','CONTEXT_INSUFFICIENT'])
        tr['timely']=tr.date.le(tr.process_id.map(timely))
        tr.to_parquet(out/f'{arm}_full_decision_trace.parquet',index=False)
        groups={k:g for k,g in tr[tr.process_id.isin(ps.process_id)].groupby('process_id')}
        coverage=pc.set_index('process_id');rows=[]
        for p in ps.itertuples():
            part=groups.get(p.process_id,tr.iloc[:0]);good=part[part.aligned];admit=good[good.eligible]
            actual=good[good.reason.isin(['SELECTED_NEW','IN_POOL_UPDATE'])]
            covered=bool(coverage.loc[p.process_id,'covered'])
            assert bool(len(actual))==covered,(arm,p.process_id,len(actual),covered)
            blockers=sorted(admit.reason.unique())
            category=('COVERED' if covered else 'NO_ALIGNED_WEEK' if good.empty else 'ALIGNMENT_WITHOUT_ADMISSION' if admit.empty else '|'.join(blockers))
            timelygood=good[good.timely];timelyadmit=timelygood[timelygood.eligible]
            tcat=('TIMELY_ACTUAL' if not actual[actual.timely].empty else 'NO_TIMELY_ALIGNED_WEEK' if timelygood.empty else
                  'TIMELY_ALIGNMENT_WITHOUT_ADMISSION' if timelyadmit.empty else '|'.join(sorted(timelyadmit.reason.unique())))
            rows.append(dict(arm=arm,process_id=p.process_id,era=p.era,industry_code=p.industry_code,covered=covered,right_open=p.right_open,
                weeks=len(part),aligned_weeks=len(good),eligible_aligned_weeks=len(admit),actual_weeks=len(actual),
                category=category,timely_category=tcat,first_aligned=None if good.empty else good.date.min(),
                best_rank=None if admit.candidate_rank.dropna().empty else admit.candidate_rank.min(),
                **{f'weeks_{v}':int(admit.reason.eq(v).sum()) for v in ['COOLDOWN','RANK_BEYOND_WEEKLY_FIVE','POOL_SPACE_LIMIT']}))
        result=pd.DataFrame(rows);result.to_parquet(out/f'{arm}_all_parent_audit.parquet',index=False)
        miss=result[~result.covered]
        assert len(miss)==(4399 if arm=='A' else 4484)
        result.groupby(['covered','category']).size().rename('count').to_csv(out/f'{arm}_category_counts.csv')
        miss.groupby(['era','category']).size().rename('count').to_csv(out/f'{arm}_miss_by_era.csv')
        miss.groupby('timely_category').size().rename('count').to_csv(out/f'{arm}_miss_timely_counts.csv')
        checks[arm]=dict(trace_rows=len(tr),parents=len(result),missed=len(miss),all_new_update_match=True,all_parent_coverage_reconciled=True)
        summaries.append(dict(arm=arm,missing=len(miss),categories=miss.category.value_counts().to_dict(),
            timely_categories=miss.timely_category.value_counts().to_dict()))
    (out/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
    (out/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in paths},artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
