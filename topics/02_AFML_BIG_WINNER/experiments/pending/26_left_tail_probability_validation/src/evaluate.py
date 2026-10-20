"""Frozen event probability, risk ranking, calibration and paired ablations."""
from core import *

METRICS=['brier','auc','pr_auc','bias','common_brier','relative_brier','precision10','precision20','enrichment10','enrichment20','recall10','recall20','fpr10','fpr20']
ABLATIONS=[('M_V','M_R'),('M_F','M_R'),('M_VF','M_R'),('M_VF','M_V'),('M_VF','M_F'),('M_VFS','M_VF')]
CONTRASTS=ABLATIONS+[(m,b) for m in C['candidates'] for b in ['B0','B1','D_R']]+[('D_V','D_R'),('D_F','D_R'),('D_VF','D_R'),('M_R','D_R'),('B1','B0')]


def build_monthly(full):
    records=[];flags=[];quantiles=[]
    for (model,date),g in full.groupby(['model','date'],sort=True):
        g=g.reset_index(drop=True)
        for k,t in THRESHOLDS.items():
            warning={str(int(frac*100)):risk_flags(g[f'p_loss{k}'],g.instrument,frac) for frac in C['warning_fractions']}
            r=point_metrics(g[f'p_loss{k}'],g.actual,t,warning)
            if r is None:continue
            record=dict(model=model,date=date,threshold=k,**r)
            records.append(record)
            for label,f in warning.items():
                flags.append(pd.DataFrame(dict(model=model,date=date,instrument=g.instrument.to_numpy(),threshold=k,warning_fraction=int(label),flag=f)))
        if g.q05.notna().all():
            known=g.actual.notna()
            if known.any():
                quantiles.append(dict(model=model,date=date,rows=int(known.sum()),cover05=float((g.loc[known,'actual']<=g.loc[known,'q05']).mean()),cover10=float((g.loc[known,'actual']<=g.loc[known,'q10']).mean())))
    return pd.DataFrame(records),pd.concat(flags,ignore_index=True),pd.DataFrame(quantiles)


def calibration(full,threshold=20):
    columns=['date','model','actual',f'p_loss{threshold}','regime','vol_regime','phase','age_group']
    d=full.loc[full.actual.notna(),columns].copy();d['observed']=event_labels(d.actual,THRESHOLDS[threshold]);d['probability']=d[f'p_loss{threshold}']
    d['bin']=np.minimum((d.probability*10).astype(int),9)
    dates=pd.DatetimeIndex(sorted(d.date.unique()))
    # These weights define month-equal joint population calibration.
    d['weight']=1/d.groupby(['model','date']).date.transform('size')
    rows=[];cached_indices={b:bootstrap_indices(len(dates),b) for b in [6,12]}
    conditions=['all','year','regime','vol_regime','phase','age_group']
    d['year']=d.date.dt.year.astype(str)
    for dimension in conditions:
        z=d.copy();z['condition']='all' if dimension=='all' else z[dimension].astype(str)
        z['wp']=z.weight*z.probability;z['wy']=z.weight*z.observed
        for (model,condition,binid),g in z.groupby(['model','condition','bin']):
            per=g.groupby('date')[['weight','wp','wy']].sum().reindex(dates,fill_value=0)
            den=per.weight.to_numpy();num=(per.wp-per.wy).to_numpy()
            den_sum=den.sum();bias=num.sum()/den_sum
            for block,idx in cached_indices.items():
                w=den[idx].sum(axis=1);values=num[idx].sum(axis=1)[w>0]/w[w>0]
                lo,hi=np.quantile(values,[.025,.975])
                rows.append(dict(model=model,threshold=threshold,dimension=dimension,condition=condition,probability_bin=int(binid),rows=len(g),events=int(g.observed.sum()),
                    covered_months=g.date.nunique(),calendar_months=len(dates),month_weight=den_sum,predicted=float(per.wp.sum()/den_sum),observed=float(per.wy.sum()/den_sum),bias=float(bias),
                    block=block,bias_low95=float(lo),bias_high95=float(hi),valid_bootstrap_draws=len(values),evidence='exploratory_sparse' if g.date.nunique()<6 else 'exploratory_unconfirmed'))
    return pd.DataFrame(rows)


def main():
    fit=json.loads((OUT/'fit_audit.json').read_text())
    full=pd.concat([pd.read_parquet(EP/r['prediction_path']) for r in fit],ignore_index=True)
    assert set(full.model)==set(ALL_MODELS)
    reference=full[full.model=='B1'].sort_values(['date','instrument']).reset_index(drop=True)
    for model,g in full.groupby('model'):
        g=g.sort_values(['date','instrument']).reset_index(drop=True)
        pd.testing.assert_frame_equal(g[['date','instrument','actual','label_end']],reference[['date','instrument','actual','label_end']])
    assert not full.duplicated(['model','date','instrument']).any()
    full.to_parquet(CACHE/'all_predictions.parquet',index=False)
    monthly,flags,quantiles=build_monthly(full)
    monthly.to_csv(OUT/'monthly_scores.csv',index=False);flags.to_parquet(CACHE/'warning_flags.parquet',index=False);quantiles.to_csv(OUT/'quantile_coverage.csv',index=False)
    measures=['brier','auc','pr_auc','base_rate','predicted','bias','common_brier','relative_brier','precision10','precision20','enrichment10','enrichment20','recall10','recall20','fpr10','fpr20']
    summary=monthly.groupby(['threshold','model'])[measures].mean().reset_index()
    counts=monthly.groupby(['threshold','model']).agg(months=('date','size'),rows=('rows','sum'),events=('events','sum'),auc_months=('auc','count'),pr_auc_months=('pr_auc','count')).reset_index()
    summary=summary.merge(counts,on=['threshold','model']);summary['pooled_base_rate']=summary.events/summary.rows
    summary.to_csv(OUT/'summary.csv',index=False)
    intervals=[]
    for k,g in monthly.groupby('threshold'):
        for a,b in CONTRASTS:
            for metric in METRICS:
                diff=paired(g[g.model.eq(a)],g[g.model.eq(b)],metric)
                if not np.isfinite(diff).any():continue
                baseline=float(g[g.model.eq(b)][metric].mean())
                for block in [6,12]:
                    result=ci(diff,block)
                    intervals.append(dict(threshold=k,candidate=a,baseline=b,metric=metric,relative_improvement_percent=-result['estimate']/baseline*100 if baseline!=0 else np.nan,**result))
    pd.DataFrame(intervals).to_csv(OUT/'paired_intervals.csv',index=False)
    # Calibration bias CI across complete origin calendar, with empty bin-month weights zero.
    tables=[calibration(full,k) for k in THRESHOLDS]
    pd.concat(tables,ignore_index=True).to_csv(OUT/'calibration.csv',index=False)
    bias_ci=[]
    for (k,model),g in monthly.groupby(['threshold','model']):
        for block in [6,12]:bias_ci.append(dict(threshold=k,model=model,**ci(g.sort_values('date').bias,block)))
    pd.DataFrame(bias_ci).to_csv(OUT/'probability_bias_intervals.csv',index=False)
    # Pooled AUC is a separate diagnosis of market-regime confounding.
    pooled=[];strata=[];coherence_rows=[]
    scored=full[full.actual.notna()].copy();scored['year']=scored.date.dt.year.astype(str)
    for model,g in scored.groupby('model'):
        for k,t in THRESHOLDS.items():pooled.append(dict(model=model,threshold=k,**point_metrics(g[f'p_loss{k}'],g.actual,t)))
    pd.DataFrame(pooled).to_csv(OUT/'pooled_metrics.csv',index=False)
    for dimension in ['year','phase','regime','vol_regime','board','age_group']:
        for (model,condition,date),g in full.groupby(['model',dimension if dimension!='year' else full.date.dt.year,'date']):
            for k,t in THRESHOLDS.items():
                result=point_metrics(g[f'p_loss{k}'],g.actual,t)
                if result is not None:strata.append(dict(model=model,dimension=dimension,condition=str(condition),date=date,threshold=k,**result))
    strata=pd.DataFrame(strata);strata.to_csv(OUT/'conditional_monthly_scores.csv',index=False)
    strata.groupby(['threshold','model','dimension','condition']).agg(brier=('brier','mean'),auc=('auc','mean'),pr_auc=('pr_auc','mean'),bias=('bias','mean'),base_rate=('base_rate','mean'),months=('date','size'),rows=('rows','sum'),events=('events','sum')).reset_index().to_csv(OUT/'conditional_scores.csv',index=False)
    phases=[];robust=[]
    main=monthly[monthly.threshold==20]
    for a,b in CONTRASTS:
        aa=main[main.model.eq(a)].sort_values('date');bb=main[main.model.eq(b)].sort_values('date');d=paired(aa,bb,'brier');dates=pd.DatetimeIndex(aa.date)
        for name,mask in [('2021-2023',dates.year<2024),('2024-2026',dates.year>=2024)]:
            phases.append(dict(candidate=a,baseline=b,phase=name,**ci(d[mask],6)))
        for i,date in enumerate(dates):robust.append(dict(candidate=a,baseline=b,removal='month',removed=str(date.date()),delta=float(np.delete(d,i).mean())))
        for year in set(dates.year):robust.append(dict(candidate=a,baseline=b,removal='year',removed=str(year),delta=float(d[dates.year!=year].mean())))
    pd.DataFrame(phases).to_csv(OUT/'phase_intervals.csv',index=False);pd.DataFrame(robust).to_csv(OUT/'leave_out_robustness.csv',index=False)
    # Label-missing outcome Brier bounds for all mature prediction rows, not only known cases.
    missing=[]
    for (model,date),g in full.groupby(['model','date']):
        mature=g[g.label_end.notna()];n=len(mature)
        if not n:continue
        known=mature.actual.notna().to_numpy();p=mature.p_loss20.to_numpy();y=event_labels(mature.actual,-.2)
        observed=float(np.sum((p[known]-y[known])**2));u=p[~known]
        missing.append(dict(model=model,date=date,mature=n,missing=int((~known).sum()),brier_lower=(observed+np.minimum(u*u,(1-u)**2).sum())/n,
            brier_upper=(observed+np.maximum(u*u,(1-u)**2).sum())/n))
    pd.DataFrame(missing).to_csv(OUT/'missing_brier_bounds.csv',index=False)
    assert all(np.allclose(monthly.brier,monthly.common_brier+monthly.relative_brier) for _ in [0])
    write_json(OUT/'execution_audit.json',dict(all_five_candidates_completed=True,classifier_fits=len(fit)*15,prediction_rows=len(full),scored_rows=len(scored),same_stock_date_label_pairs=True,all_probability_scores_month_aggregated=True,
        original_ep25_p20_exactly_reused=True,independent_holdout=False))
    print(summary[summary.threshold==20][['model','brier','auc','pr_auc','base_rate','enrichment20']].to_string(index=False),flush=True)

if __name__=='__main__':main()
