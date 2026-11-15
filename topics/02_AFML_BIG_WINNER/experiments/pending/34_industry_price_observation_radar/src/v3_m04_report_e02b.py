"""Complete fixed-grid reporting, paired time blocks and descriptive followup."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha


def main():
    root=EP/'outputs/evaluation_versions/v3_m04_e02b';replay=EP/'outputs/v3_m04_replay';out=EP/'outputs/v3_m04_comparison_e02b'
    if out.exists():raise FileExistsError(out)
    rec=json.loads((root/'receipt.json').read_text())
    for rel,digest in rec['artifacts'].items():assert sha(root/rel)==digest,rel
    out.mkdir();summary=pd.read_csv(root/'all_run_summary.csv');extra=[];strata=[];weekly={};qualities={};coverages={}
    parents=pd.read_parquet(EP/'outputs/v2_e02_context/strata/parent_strata.parquet')
    pmap=parents.set_index('process_id');children=pd.read_parquet(EP/'outputs/v2_s13_duration_enhancements/children.parquet').set_index('child_id')
    dates=pd.DatetimeIndex(pd.read_csv(replay/'calendar_coverage.csv',parse_dates=['date']).date)
    periods=dates.to_period('W-SUN');positions={str(w):i for i,w in enumerate(periods)}
    def index_for(d):
        w=str(pd.Timestamp(d).to_period('W-SUN'))
        return positions[w] if w in positions else 0 if pd.Timestamp(d)<dates[0] else len(dates)-1
    for r in summary.itertuples():
        dest=root/'runs'/r.run_id;pc=pd.read_parquet(dest/'parent_coverage.parquet');q=pd.read_parquet(dest/'event_quality.parquet');new=q[q.kind.eq('NEW')]
        coverages[r.run_id]=pc;qualities[r.run_id]=new
        pc=pc.merge(parents[['process_id','prior_state','market_state','year']],on='process_id',validate='one_to_one')
        cov=pc[pc.covered];stages=[]
        for row in new[new.status.eq('COVERED')].itertuples():
            confirm=pmap.loc[row.primary_id,'confirm_date'] if row.primary_type=='PARENT' else children.loc[row.primary_id,'confirm_date']
            stages.append('BEFORE' if row.date<confirm else 'ON' if row.date==confirm else 'AFTER')
        extra.append(dict(run_id=r.run_id,lag_p50=cov.lag_days.median(),lag_p90=cov.lag_days.quantile(.9),pre_gain_p50=cov.pre_gain.median(),pre_gain_p90=cov.pre_gain.quantile(.9),
            new_before_confirmation=stages.count('BEFORE'),new_on_confirmation=stages.count('ON'),new_after_confirmation=stages.count('AFTER'),
            left_scope_parents=int(pd.to_datetime(pc.start).lt(dates[0]).sum()),left_scope_covered=int((pd.to_datetime(pc.start).lt(dates[0])&pc.covered).sum())))
        for column in ['prior_state','market_state','year']:
            for value,g in pc.groupby(column):
                hit=g[g.covered];strata.append(dict(run_id=r.run_id,stratification=column,stratum=value,processes=len(g),covered=int(g.covered.sum()),timely=int(g.timing.eq('TIMELY').sum()),late=int(g.timing.eq('LATE').sum()),lag_p50=hit.lag_days.median(),pre_gain_p50=hit.pre_gain.median()))
        arr=np.zeros((len(dates),7))
        for row in pc.itertuples():
            i=index_for(row.start);arr[i,0]+=1;arr[i,1]+=int(row.covered);arr[i,2]+=int(row.timing=='TIMELY')
        for row in new.itertuples():
            i=index_for(row.date);arr[i,3]+=int('UNKNOWN' not in row.status);arr[i,4]+=int(row.status=='COVERED')
        cc=pd.read_parquet(dest/'child_coverage.parquet')
        for row in cc.itertuples():
            i=index_for(row.start);arr[i,5]+=1;arr[i,6]+=int(row.covered)
        weekly[r.run_id]=arr
    summary=summary.merge(pd.DataFrame(extra),on='run_id',validate='one_to_one')
    summary.to_csv(out/'all_grid_metrics.csv',index=False);pd.DataFrame(strata).to_csv(out/'all_grid_strata.csv',index=False)
    main=summary[summary.run_id.str.startswith(("q5_d0_","solo_"))].copy();main.to_csv(out/'main_metrics.csv',index=False)
    rng=np.random.default_rng(34104);N=len(dates);sample=(rng.integers(0,N,size=(2000,int(np.ceil(N/13))))[:,:,None]+np.arange(13)[None,None,:])%N
    sample=sample.reshape(2000,-1)[:,:N]
    def metrics(a):
        return np.stack([a[...,1]/a[...,0],a[...,2]/a[...,0],a[...,4]/a[...,3],a[...,6]/a[...,5]],axis=-1)
    results=[]
    contrasts=[('PROCESS_COVER','DATE_COVER'),('PROCESS_EARLY','DATE_EARLY'),('PROCESS_BALANCED','DATE_BALANCED'),('PROCESS_BALANCED','ORIGINAL20')]
    for a,b in [(prefix+a,prefix+b) for prefix in ['q5_d0_','solo_'] for a,b in contrasts]:
        aa=weekly[a];bb=weekly[b]
        delta=metrics(aa[sample].sum(axis=1))-metrics(bb[sample].sum(axis=1));point=metrics(aa.sum(axis=0))-metrics(bb.sum(axis=0))
        for j,m in enumerate(['parent_coverage','timely_coverage','new_matching_rate','child_coverage']):
            results.append(dict(comparison=a+' minus '+b,metric=m,difference=point[j],lo95=float(np.quantile(delta[:,j],.025)),hi95=float(np.quantile(delta[:,j],.975))))
    pd.DataFrame(results).to_csv(out/'paired_intervals.csv',index=False)
    waits=[]
    arms=['ORIGINAL20','DATE_COVER','DATE_EARLY','DATE_BALANCED','PROCESS_COVER','PROCESS_EARLY','PROCESS_BALANCED']
    for qcap in [1,3,5]:
        for arm in arms:
            zero=summary.set_index('run_id').loc[f'q{qcap}_d0_{arm}'];one=summary.set_index('run_id').loc[f'q{qcap}_d1_{arm}']
            waits.append(dict(quota=qcap,arm=arm,new_change=int(one.new_total-zero.new_total),coverage_change=int(one.parent_covered-zero.parent_covered),timely_change=int(one.parent_timely-zero.parent_timely),quality_change=float(one.new_effective_rate-zero.new_effective_rate)))
    pd.DataFrame(waits).to_csv(out/'waiting_costs.csv',index=False)
    summary.to_csv(out/'actual_quality_coverage_points.csv',index=False)
    rawpath=PRIOR/'daily_industries.parquet';marketpath=CACHE/'forecast_v5/CSI_ALL.parquet'
    raw=pd.read_parquet(rawpath,columns=['date','day_i','era','industry_code','block','nav']);market=pd.read_parquet(marketpath).close
    groups={k:g.set_index('day_i').sort_index() for k,g in raw.groupby(['era','industry_code'])};di=raw[['date','day_i']].drop_duplicates().set_index('date').day_i.to_dict();last=int(raw.day_i.max());records=[]
    for run in main.loc[main.run_id.str.startswith("solo_"),"run_id"]:
        ev=pd.read_parquet(replay/run/'events.parquet')
        for row in ev[ev.kind.eq('NEW')].itertuples():
            day=int(di[row.date]);g=groups[row.era,row.industry_code]
            for h in [20,60,90,180]:
                p=g.reindex(range(day,day+h+1));valid=p.nav.gt(0).all() and p.block.eq(row.block).all();m=market.reindex(pd.DatetimeIndex(p.date));mk=valid and m.notna().all() and m.gt(0).all();nav=p.nav.to_numpy()
                absolute=float(nav[-1]/nav[0]-1) if valid else None
                records.append(dict(run_id=run,event_id=row.event_id,horizon=h,status='MATURE' if valid else 'IMMATURE' if day+h>last else 'DATA_OR_CLASSIFICATION_GAP',absolute_return=absolute,
                    excess_return=absolute-float(m.iloc[-1]/m.iloc[0]-1) if mk else None,drawdown=float((nav/np.maximum.accumulate(nav)-1).min()) if valid else None))
        print('Followup',run,flush=True)
    paths=pd.DataFrame(records);paths.to_parquet(out/'all_main_new_paths.parquet',index=False);fs=[]
    for (run,h),g in paths.groupby(['run_id','horizon']):
        good=g[g.status.eq('MATURE')]
        fs.append(dict(run_id=run,horizon=h,total=len(g),mature=len(good),immature=int(g.status.eq('IMMATURE').sum()),gap=int(g.status.eq('DATA_OR_CLASSIFICATION_GAP').sum()),absolute_mean=good.absolute_return.mean(),absolute_median=good.absolute_return.median(),excess_mean=good.excess_return.mean(),excess_median=good.excess_return.median(),positive_fraction=good.absolute_return.gt(0).mean(),drawdown_median=good.drawdown.median()))
    pd.DataFrame(fs).to_csv(out/'main_followup.csv',index=False)
    inputs=[root/'receipt.json',replay/'receipt.json',rawpath,marketpath,EP/'outputs/v2_e02_context/strata/parent_strata.parquet',EP/'outputs/v2_s13_duration_enhancements/children.parquet',Path(__file__)]
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(p):sha(p) for p in inputs},artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()},limits='Reused-history descriptive simulation. Bounded parent/child target versions, not immutable final labels. Conditional 13-week intervals; model/label choice uncertainty not covered. Independent and paired workloads differ; no claim of independent validation.'),indent=2)+'\n')
    print(main[['run_id','new_total','new_effective_rate','parent_covered','parent_timely','parent_late','child_covered','lag_p50','pre_gain_p50']].to_string(index=False))


if __name__=='__main__':main()
