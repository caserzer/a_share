"""Fixed month-level scoring, calibration, ablation and robustness tables."""
import json
import numpy as np
import pandas as pd
from core import *

METRICS=['crps','brier','tail_brier','tail_error','tail_absolute_error','p_up','p_tail','observed_up','observed_tail','direction','pit','coverage90','cover05','cover10','cover50','cover90','cover95','relative_crps']
CONTRASTS=[(m,b) for m in CONFIG['candidates'] for b in ['B0','B1']]+[('M_V','M_R'),('M_F','M_R'),('M_VF','M_R'),('M_VF','M_F'),('M_VF','M_V')]


def correlation(x,y):
    return float(pd.Series(x).corr(pd.Series(y),method='spearman')) if pd.Series(x).nunique()>1 and pd.Series(y).nunique()>1 else np.nan


def main():
    receipts=json.loads((OUT/'fit_audit.json').read_text())
    allrows=[];cohorts=[]
    for receipt in receipts:
        df=pd.read_parquet(EP/receipt['predictions']['path'])
        allrows.append(df)
        with np.load(EP/receipt['atoms']['path']) as data:
            for model,g in df.groupby('model',sort=True):
                # Cache rows follow test keys; metric rows follow date then original key order.
                s=data[model]
                for date,part in g.reset_index(drop=True).groupby('date',sort=True):
                    obs=part.actual.notna().to_numpy()
                    if not obs.any():continue
                    a=s[part.index.to_numpy()][obs]
                    cohorts.append(dict(horizon=receipt['horizon'],model=model,date=date,
                        common_cdf_distance=cohort_distance(a,part.loc[obs,'actual'])))
    full=pd.concat(allrows,ignore_index=True)
    full.to_parquet(CACHE/'all_predictions.parquet',index=False)
    d=full[full.actual.notna() & full.label_end.le(pd.Timestamp(CONFIG['cutoff']))].copy()
    assert not d.duplicated(['horizon','model','date','instrument']).any()
    for h,g in d.groupby('horizon'):
        ref=g[g.model=='B1'].sort_values(['date','instrument']).reset_index(drop=True)
        for m,z in g.groupby('model'):
            z=z.sort_values(['date','instrument']).reset_index(drop=True)
            pd.testing.assert_frame_equal(z[['date','instrument','actual']],ref[['date','instrument','actual']])
    monthly=d.groupby(['horizon','model','date'])[METRICS].mean().reset_index()
    monthly=monthly.merge(pd.DataFrame(cohorts),on=['horizon','model','date'],validate='one_to_one')
    ranking=[];sorts=[]
    for (h,m,date),g in d.groupby(['horizon','model','date']):
        ic=correlation(g['mean'].to_numpy(),g.actual.to_numpy());mi=correlation(g.q50.to_numpy(),g.actual.to_numpy())
        spread=np.nan
        if g['mean'].nunique()>1:
            # Keep prediction ties together; empty quintiles are reported, not broken using outcomes.
            bucket=np.minimum((g['mean'].rank(method='average',pct=True)*5).astype(int),4)
            ret=g.groupby(bucket).actual.mean()
            spread=ret.get(4,np.nan)-ret.get(0,np.nan)
            for b in range(5):sorts.append(dict(horizon=h,model=m,date=date,bucket=b,rows=int((bucket==b).sum()),return_mean=float(ret.get(b,np.nan))))
        ranking.append(dict(horizon=h,model=m,date=date,rank_ic=ic,median_rank_ic=mi,top_bottom_spread=spread))
    monthly=monthly.merge(pd.DataFrame(ranking),on=['horizon','model','date'],validate='one_to_one')
    monthly.to_csv(OUT/'monthly_scores.csv',index=False)
    pd.DataFrame(sorts).to_csv(OUT/'return_sorting.csv',index=False)
    measures=METRICS+['common_cdf_distance','rank_ic','median_rank_ic','top_bottom_spread']
    summary=monthly.groupby(['horizon','model'])[measures].mean().reset_index()
    summary.to_csv(OUT/'summary.csv',index=False)
    # Confidence intervals: same month paired rows; entire cross section already collapsed.
    intervals=[]
    for h,g in monthly.groupby('horizon'):
        for a,b in CONTRASTS:
            for metric in ['crps','brier','tail_brier','relative_crps','common_cdf_distance','cover05','cover10','cover50','cover90','cover95']:
                diff=paired(g[g.model==a],g[g.model==b],metric)
                for block in [max(6,h),2*max(6,h)]:
                    intervals.append(dict(horizon=h,candidate=a,baseline=b,metric=metric,**interval(diff,h,block)))
    pd.DataFrame(intervals).to_csv(OUT/'paired_intervals.csv',index=False)
    # Predeclared phases, available market state and population subgroups.
    strata=[]
    for col in ['phase','regime','board','size_group','risk_group']:
        t=d.groupby(['horizon','model',col,'date'])[METRICS].mean().reset_index()
        for (h,m,label),g in t.groupby(['horizon','model',col]):
            record=dict(horizon=h,model=m,dimension=col,group=str(label),months=g.date.nunique(),**{c:float(g[c].mean()) for c in METRICS})
            strata.append(record)
    pd.DataFrame(strata).to_csv(OUT/'stratum_scores.csv',index=False)
    annual=monthly.assign(year=monthly.date.dt.year).groupby(['horizon','model','year'])[measures].mean().reset_index()
    annual.to_csv(OUT/'annual_scores.csv',index=False)
    robustness=[]
    phase_ci=[]
    for h,g in monthly.groupby('horizon'):
        for a,b in CONTRASTS:
            aa=g[g.model==a].sort_values('date');bb=g[g.model==b].sort_values('date')
            diff=paired(aa,bb,'crps');dates=pd.DatetimeIndex(aa.date)
            for label,mask in [('2021-2023',dates.year<2024),('2024-2026',dates.year>=2024)]:
                phase_ci.append(dict(horizon=h,candidate=a,baseline=b,phase=label,**interval(diff[mask],h)))
            for i,date in enumerate(dates):
                robustness.append(dict(horizon=h,candidate=a,baseline=b,removal='month',removed=str(date.date()),delta=float(np.delete(diff,i).mean())))
            for year in sorted(set(dates.year)):
                robustness.append(dict(horizon=h,candidate=a,baseline=b,removal='year',removed=str(year),delta=float(diff[dates.year!=year].mean())))
    pd.DataFrame(phase_ci).to_csv(OUT/'phase_intervals.csv',index=False)
    pd.DataFrame(robustness).to_csv(OUT/'leave_out_robustness.csv',index=False)
    reliability=[];pits=[]
    for dimension in ['all','regime','phase','board']:
        z=d.copy();z['condition']='all' if dimension=='all' else z[dimension].astype(str)
        for event,prob,truth in [('up','p_up','observed_up'),('tail','p_tail','observed_tail')]:
            z['bin']=np.minimum((z[prob]*10).astype(int),9)
            # Equal-month weights globally within each condition, including bin occupancy.
            z['weight']=1/z.groupby(['horizon','model','condition','date']).date.transform('size')
            z['wp']=z[prob]*z.weight;z['wy']=z[truth]*z.weight
            table=z.groupby(['horizon','model','condition','bin']).agg(rows=('actual','size'),weight=('weight','sum'),wp=('wp','sum'),wy=('wy','sum')).reset_index()
            for r in table.to_dict('records'):
                reliability.append(dict(horizon=r['horizon'],model=r['model'],dimension=dimension,condition=r['condition'],event=event,bin=r['bin'],rows=r['rows'],month_weight=r['weight'],predicted=r['wp']/r['weight'],observed=r['wy']/r['weight']))
        z['bin']=np.minimum((z.pit*10).astype(int),9)
        table=z.groupby(['horizon','model','condition','bin']).agg(rows=('actual','size'),weight=('weight','sum')).reset_index()
        for (h,m,condition),g in table.groupby(['horizon','model','condition']):
            for r in g.to_dict('records'):
                pits.append(dict(horizon=h,model=m,dimension=dimension,condition=condition,bin=r['bin'],rows=r['rows'],probability=r['weight']/g.weight.sum()))
    pd.DataFrame(reliability).to_csv(OUT/'reliability.csv',index=False)
    pd.DataFrame(pits).to_csv(OUT/'pit_histograms.csv',index=False)
    # Missing outcomes: event-rate identification bounds, no invented returns or CRPS.
    bounds=[]
    for (h,m,date),g in full.groupby(['horizon','model','date']):
        mature=g[g.label_end.notna() & g.label_end.le(pd.Timestamp(CONFIG['cutoff']))]
        if mature.empty:continue
        n=len(mature);known=mature.actual.notna();miss=int((~known).sum())
        bounds.append(dict(horizon=h,model=m,date=date,mature=n,missing=miss,predicted_up=mature.p_up.mean(),
            observed_up_lower=int((mature.actual>0).sum())/n,observed_up_upper=(int((mature.actual>0).sum())+miss)/n,
            tail_lower=int((mature.actual<CONFIG['tail_threshold']).sum())/n,tail_upper=(int((mature.actual<CONFIG['tail_threshold']).sum())+miss)/n))
    pd.DataFrame(bounds).to_csv(OUT/'missing_event_bounds.csv',index=False)
    before=json.loads((OUT/'ep24_preservation_before.json').read_text())
    preserved=all(digest(OLD/k)==v for k,v in before.items())
    assert preserved,'EP24 was modified'
    write_json(OUT/'execution_audit.json',dict(all_preregistered_models_completed=True,candidates=list(CONFIG['candidates']),horizons=CONFIG['horizons'],
        scored_rows=len(d),prediction_rows=len(full),fit_quarters=len(receipts),models_fit=len(receipts)*len(CONFIG['candidates']),
        same_stock_date_label_pairs=True,ep24_all_manifest_files_unchanged=preserved,baseline_max_error=max(r['frozen_baseline_max_error'] for r in receipts),independent_holdout=False))
    print(summary[['horizon','model','crps','brier','tail_brier','rank_ic']].to_string(index=False))

if __name__=='__main__':main()
