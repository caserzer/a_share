"""Paired summaries and common calendar-block uncertainty for corrected accounting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,CACHE,sha


def main():
    root=EP/'outputs/v2_revaluation01';out=root/'comparison'
    if out.exists():raise FileExistsError('Preserve comparison')
    out.mkdir();s=pd.read_csv(root/'all_run_summary.csv');s['family']=s.run_id.str.split('/').str[0]
    s['grid']=s.run_id.str.split('/').str[-2];s['arm']=s.run_id.str.split('/').str[-1]
    cols=['new_total','new_unknown','new_effective_rate','new_all_lower','new_all_upper','parent_covered','parent_coverage','parent_timely','parent_late','child_covered','child_coverage','new_repeat','updates','pool_median']
    means=s[s.family.ne('v2_b01')].groupby(['family','grid','arm'])[cols].mean().reset_index()
    means.to_csv(out/'all_grid_means.csv',index=False)
    pairs=[]
    for run in s[s.arm.eq('A')].run_id:
        a=s[s.run_id.eq(run)].iloc[0];b=s[s.run_id.eq(run[:-1]+'B')].iloc[0]
        wa=pd.read_csv(root/'runs'/run/'workload.csv');wb=pd.read_csv(root/'runs'/(run[:-1]+'B')/'workload.csv')
        assert wa.NEW.equals(wb.NEW)
        pairs.append(dict(pair=run[:-2],family=a.family,grid=a.grid,**{k:float(a[k]-b[k]) for k in cols}))
    pd.DataFrame(pairs).to_csv(out/'all_pair_differences.csv',index=False)
    # Use common market-calendar blocks, not sector or random-seed independence.
    week_dates=pd.read_csv(root/'runs/v2_b01/workload.csv').iloc[:,0]
    week_keys=pd.to_datetime(week_dates).dt.to_period('W-SUN').astype(str).tolist();weekmap={v:i for i,v in enumerate(week_keys)};n=len(week_keys)
    rng=np.random.default_rng(3411);weights=[]
    for _ in range(2000):
        starts=rng.integers(0,n,size=int(np.ceil(n/13)))
        idx=((starts[:,None]+np.arange(13))%n).ravel()[:n]
        weights.append(np.bincount(idx,minlength=n))
    weights=np.array(weights)
    def series(dates,values):
        w=pd.to_datetime(dates).dt.to_period('W-SUN').astype(str).map(weekmap)
        assert w.notna().all()
        return np.bincount(w.to_numpy(int),weights=np.asarray(values,float),minlength=n)
    def matrix(run):
        path=root/'runs'/run
        p=pd.read_parquet(path/'parent_coverage.parquet');c=pd.read_parquet(path/'child_coverage.parquet');e=pd.read_parquet(path/'event_quality.parquet');e=e[e.kind.eq('NEW')]
        return np.array([series(p.start,np.ones(len(p))),series(p.start,p.covered),series(p.start,p.timing.eq('TIMELY')),
            series(c.start,np.ones(len(c))),series(c.start,c.covered),series(e.date,~e.status.str.contains('UNKNOWN')),series(e.date,e.status.eq('COVERED'))])
    def metrics(x):return np.array([x[...,1]/x[...,0],x[...,2]/x[...,0],x[...,4]/x[...,3],x[...,6]/x[...,5]]).T
    boot={}
    for fam in ['v2_b02','v2_b03','v2_b04','v2_b05']:
        aa=s[s.family.eq(fam)&s.grid.eq('q5_d0')&s.arm.eq('A')].run_id.tolist();diffs=[];points=[]
        for a in aa:
            ma=matrix(a);mb=matrix(a[:-1]+'B')
            diffs.append(metrics(weights@ma.T)-metrics(weights@mb.T))
            points.append(metrics(ma.sum(axis=1))-metrics(mb.sum(axis=1)))
        dd=np.mean(diffs,axis=0);pt=np.mean(points,axis=0)
        boot[fam]={name:dict(a_minus_b=float(pt[j]),interval95=np.quantile(dd[:,j],[.025,.975]).tolist()) for j,name in enumerate(['parent_coverage','timely_parent_coverage','child_coverage','new_effectiveness'])}
    (out/'paired_bootstrap.json').write_text(json.dumps(dict(block_weeks=13,repetitions=2000,seed=3411,main_grid='q5_d0',
        meaning='Historical paired calendar-block uncertainty; seeds share history and weights; not independent validation',results=boot),indent=2)+'\n')
    # Actual observed options at the user reference level, without interpolation.
    eligible=means[means.new_effective_rate.ge(.5)].copy()
    eligible['quality_reference']=.5
    eligible.to_csv(out/'options_meeting_point_reference_only.csv',index=False)
    frontier=[]
    for fam,g in means.groupby('family'):
        for row in g.itertuples():
            dominated=((g.new_effective_rate>=row.new_effective_rate)&(g.parent_coverage>=row.parent_coverage)&
                      ((g.new_effective_rate>row.new_effective_rate)|(g.parent_coverage>row.parent_coverage))).any()
            frontier.append(dict(family=fam,grid=row.grid,arm=row.arm,dominated=bool(dominated),
                effectiveness=row.new_effective_rate,parent_coverage=row.parent_coverage,actual_new=row.new_total,
                note='Descriptive observed frontier, varying actual workload; no interpolated equal-accuracy claim'))
    pd.DataFrame(frontier).to_csv(out/'observed_frontier.csv',index=False)
    # Confirmation changes selection as well as timing; keep lost and gained sets.
    costs=[]
    for run in s[s.grid.eq('q5_d0')].run_id:
        wait=run.replace('q5_d0','q5_d1');a=pd.read_parquet(root/'runs'/run/'parent_coverage.parquet');b=pd.read_parquet(root/'runs'/wait/'parent_coverage.parquet')
        ac=set(a.loc[a.covered,'process_id']);bc=set(b.loc[b.covered,'process_id'])
        common=a[a.process_id.isin(ac&bc)].merge(b[['process_id','first_date']],on='process_id',suffixes=('_now','_wait'))
        delta=(pd.to_datetime(common.first_date_wait)-pd.to_datetime(common.first_date_now)).dt.days
        costs.append(dict(run=run,wait_run=wait,lost=len(ac-bc),gained=len(bc-ac),common=len(common),
            common_calendar_delay_median=float(delta.median()),common_delayed=int(delta.gt(0).sum()),common_earlier=int(delta.lt(0).sum())))
    pd.DataFrame(costs).to_csv(out/'confirmation_cost.csv',index=False)
    # Timing and evidence maturity remain separate from finding a process.
    timing=[]
    for run in ['v2_b01']+s[s.grid.eq('q5_d0')].run_id.tolist():
        e=pd.read_parquet(root/'runs'/run/'event_quality.parquet');x=e[e.kind.eq('NEW')&e.status.eq('COVERED')]
        for field in ['lag_days','pre_gain','confirmation_delay']:
            timing.append(dict(run=run,field=field,count=len(x),**{f'q{int(q*100)}':float(x[field].quantile(q)) for q in [.1,.5,.9,.99]},
                already_confirmed=int(x.confirmation_delay.eq(0).sum()),timely_new=int(x.timing.eq('TIMELY').sum()),late_new=int(x.timing.eq('LATE').sum())))
    pd.DataFrame(timing).to_csv(out/'effective_new_timing.csv',index=False)
    # Parent start-date market environment; no signal market filter introduced.
    marketpath=CACHE/'forecast_v5/CSI_ALL.parquet';market=pd.read_parquet(marketpath).sort_index()
    market_ret=market.close/market.close.shift(60)-1
    if not isinstance(market_ret.index,pd.DatetimeIndex):raise AssertionError('Market date index required')
    regimes=[];annual=[]
    for run in s.run_id:
        p=pd.read_parquet(root/'runs'/run/'parent_coverage.parquet')
        val=pd.to_datetime(p.start).map(market_ret)
        p['market_regime']=np.where(val.isna(),'UNKNOWN',np.where(val.gt(0),'PRIOR60_POSITIVE','PRIOR60_NONPOSITIVE'))
        for regime,g in p.groupby('market_regime'):
            regimes.append(dict(run=run,regime=regime,processes=len(g),covered=int(g.covered.sum()),timely=int(g.timing.eq('TIMELY').sum())))
        p['year']=p.start.str[:4]
        for (era,year),g in p.groupby(['era','year']):annual.append(dict(run=run,era=era,year=year,processes=len(g),covered=int(g.covered.sum()),timely=int(g.timing.eq('TIMELY').sum())))
    pd.DataFrame(regimes).to_csv(out/'market_regimes.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual_all_runs.csv',index=False)
    (out/'receipt.json').write_text(json.dumps(dict(inputs={str(root/'receipt.json'):sha(root/'receipt.json'),str(marketpath):sha(marketpath),str(Path(__file__)):sha(Path(__file__))},
        artifacts={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    print(json.dumps(boot,indent=2));print(pd.DataFrame(timing).query("run=='v2_b01'").to_string(index=False))


if __name__=='__main__':main()
