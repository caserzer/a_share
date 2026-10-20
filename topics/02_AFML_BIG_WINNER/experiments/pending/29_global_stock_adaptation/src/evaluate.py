"""Same-row hierarchical comparisons: pooled, month and issuer weighting, with block inference."""
from sklearn.metrics import roc_auc_score,average_precision_score
from common import *
from issuer_adaptation import nonoverlap_count,merged_event_stages
CONTRASTS=[('GPI','G'),('GP','G'),('GI','G'),('GPI','GP'),('GPI','GI'),('L','G')]
DIAGNOSTIC=[('GPI_strong','GP'),('GPI','GPI_strong'),('L_unshrunk','L'),('L_unshrunk','G')]


def score(g,name):
    z=g[g.actual.notna()].copy()
    if not len(z):return None
    y=labels(z.actual);p=z[name].to_numpy();bias=float(np.mean(p-y))
    r=dict(rows=len(z),events=int(y.sum()),base_rate=float(y.mean()),predicted=float(p.mean()),bias=bias,
        brier=float(np.mean((p-y)**2)),common_brier=bias*bias,relative_brier=float(np.mean(((p-p.mean())-(y-y.mean()))**2)),
        auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else np.nan,
        pr_auc=float(average_precision_score(y,p)) if y.sum() else np.nan)
    z['bin']=np.minimum((p*10).astype(int),9);z['event']=y
    bins=z.groupby('bin').agg(count=('event','size'),predicted=(name,'mean'),observed=('event','mean'))
    r['ece']=float((bins['count']*abs(bins.predicted-bins.observed)).sum()/len(z))
    for fraction in [.05,.1,.2]:
        label=str(int(fraction*100));flag=z[f'flag_{name}_{label}'].to_numpy(bool);tp=y[flag].sum()
        r['recall'+label]=float(tp/y.sum()) if y.sum() else np.nan
        r['precision'+label]=float(y[flag].mean()) if flag.any() else np.nan
        r['enrichment'+label]=r['precision'+label]/y.mean() if y.mean() else np.nan
        r['FP'+label]=int((1-y[flag]).sum());r['FN'+label]=int(y[~flag].sum())
    numerator=denominator=used=events=0
    for industry,a in z.groupby('industry_id'):
        e=int(a.event.sum());n=len(a)-e
        if industry=='UNKNOWN' or len(a)<C['conditional_auc']['min_rows'] or e<C['conditional_auc']['min_events'] or n<C['conditional_auc']['min_nonevents']:continue
        numerator+=roc_auc_score(a.event,a[name])*e*n;denominator+=e*n;used+=len(a);events+=e
    r.update(industry_auc=float(numerator/denominator) if denominator else np.nan,
        industry_coverage=used/len(z),industry_rows=used,industry_events=events)
    return r


def annotate(frame,names):
    f=frame.copy()
    for name in names:
        for fraction in [.05,.1,.2]:
            col=f'flag_{name}_{int(fraction*100)}';f[col]=False
            for _,g in f.groupby('date'):f.loc[g.index,col]=warnings(g[name],g.instrument,fraction)
    f['year']=f.date.dt.year.astype(str);f['phase']=np.where(f.date.dt.year<2024,'2021-2023','2024+')
    f['listing_group']=pd.cut(f.listing_age_years,[-np.inf,5,15,np.inf],right=False,labels=['under5','5to15','15plus']).astype(str)
    f['industry_stability_group']=np.where(f.known_industry_stability>=.8,'stable_identity','changed_or_short')
    return f


def weighted_intervals(g,a,b,block,two_way=False):
    z=g[g.actual.notna()].copy();y=labels(z.actual);z['delta']=(z[a]-y)**2-(z[b]-y)**2
    matrix=z.pivot(index='date',columns='instrument',values='delta').sort_index().to_numpy()
    valid=np.isfinite(matrix);values=np.nan_to_num(matrix);n=len(matrix);idx=bootstrap_indices(n,block)
    counts=np.zeros((len(idx),n),float)
    np.add.at(counts,(np.repeat(np.arange(len(idx)),n),idx.ravel()),1.)
    numerator=counts@values;denominator=counts@valid.astype(float)
    means=np.divide(numerator,denominator,out=np.full_like(numerator,np.nan),where=denominator>0)
    monthly=np.nanmean(matrix,axis=1)
    draw_month=np.mean(monthly[idx],axis=1);draw_pool=numerator.sum(axis=1)/denominator.sum(axis=1);draw_company=np.nanmean(means,axis=1)
    baseline=dict(month=float(g[g.actual.notna()].assign(loss=(g.loc[g.actual.notna(),b]-y)**2).groupby('date').loss.mean().mean()),
        pooled=float(np.mean((z[b]-y)**2)),
        company=float(z.assign(loss=(z[b]-y)**2).groupby('instrument').loss.mean().mean()))
    out=[]
    for weighting,draw,value in [('month',draw_month,np.nanmean(monthly)),('pooled',draw_pool,np.nanmean(matrix)),('company',draw_company,np.nanmean(np.nanmean(matrix,axis=0)))]:
        out.append(dict(weighting=weighting,relative_improvement_percent=-value/baseline[weighting]*100 if baseline[weighting]>0 else np.nan,
            **interval(draw,value,block,n)))
    if two_way:
        rng=np.random.default_rng(C['bootstrap']['seed']+37);k=matrix.shape[1]
        company_counts=rng.multinomial(k,np.full(k,1/k),size=len(idx))
        num=np.sum(np.nan_to_num(means)*company_counts,axis=1);den=np.sum(np.isfinite(means)*company_counts,axis=1)
        draw=np.divide(num,den,out=np.full(len(num),np.nan),where=den>0)
        out.append(dict(weighting='company_and_time_clusters',relative_improvement_percent=-np.nanmean(np.nanmean(matrix,axis=0))/baseline['company']*100 if baseline['company']>0 else np.nan,
            **interval(draw,np.nanmean(np.nanmean(matrix,axis=0)),block,n)))
    return out


def main():
    cohorts=json.loads((EP/'configs/target_cohort.yaml').read_text());stocks=[x['instrument'] for x in cohorts['companies']]
    monthly=[];summary=[];intervals=[];conditional=[];company=[];company_ci=[];reliability=[];robust=[];bounds=[];corrections=[];aux=[];phases=[]
    for foundation in ['M_R','L2']:
        names=C['formal_models']+(C['diagnostic_models'] if foundation=='M_R' else [])
        raw=pd.read_parquet(CACHE/f'real_{foundation}_all.parquet');f=annotate(raw[raw.date>=C['prediction_start']].reset_index(drop=True),names)
        assert len(f)==29596 and f.actual.notna().sum()==27230 and int(np.nansum(labels(f.actual)))==4581
        f.to_parquet(CACHE/f'evaluation_{foundation}.parquet',index=False)
        f[f.instrument.eq(cohorts['single_stock'])].to_csv(EP/f'outputs/predictions/single_stock_{foundation}.csv',index=False)
        selected=f[f.instrument.isin(stocks)]
        selected.to_parquet(CACHE/f'cohort_predictions_{foundation}.parquet',index=False)
        for population,g in [('D0',f),('cohort40',selected)]:
            local_month=[]
            for (date),z in g.groupby('date'):
                for name in names:
                    r=score(z,name)
                    if r is None:continue
                    record=dict(foundation=foundation,population=population,model=name,date=date,**r);monthly.append(record);local_month.append(record)
            m=pd.DataFrame(local_month)
            for name,z in m.groupby('model'):
                row=z.drop(columns=['foundation','population','model','date']).mean().to_dict()
                known=g[g.actual.notna()];loss=(known[name]-labels(known.actual))**2
                row.update(months=len(z),companies=known.instrument.nunique(),stock_months=len(known),events=int((known.actual<-.2).sum()),
                    pooled_brier=float(loss.mean()),company_equal_brier=float(known.assign(loss=loss).groupby('instrument').loss.mean().mean()))
                summary.append(dict(foundation=foundation,population=population,model=name,**row))
            contrasts=CONTRASTS+(DIAGNOSTIC if foundation=='M_R' else [])
            for a,b in contrasts:
                for block in C['bootstrap']['blocks']:
                    for result in weighted_intervals(g,a,b,block,two_way=(a,b)==('GPI','G')):
                        intervals.append(dict(foundation=foundation,population=population,candidate=a,baseline=b,**result))
                aa=m[m.model==a].set_index('date').sort_index();bb=m[m.model==b].set_index('date').sort_index()
                delta=aa.brier-bb.brier
                if (a,b) in CONTRASTS:
                    for metric in ['auc','pr_auc','industry_auc','ece','bias','common_brier','relative_brier','recall5','recall10','recall20','enrichment5','enrichment10','enrichment20']:
                        d=aa[metric]-bb[metric]
                        if np.isfinite(d).any():
                            for block in C['bootstrap']['blocks']:aux.append(dict(foundation=foundation,population=population,candidate=a,baseline=b,metric=metric,**ci(d,block)))
                    for phase,mask in [('2021-2023',delta.index.year<2024),('2024+',delta.index.year>=2024)]:
                        for block in C['bootstrap']['blocks']:phases.append(dict(foundation=foundation,population=population,candidate=a,baseline=b,phase=phase,**ci(delta[mask],block)))
                for date in delta.index:robust.append(dict(foundation=foundation,population=population,candidate=a,baseline=b,removal='month',removed=str(date.date()),estimate=float(delta.drop(date).mean())))
                for year in sorted(set(delta.index.year)):robust.append(dict(foundation=foundation,population=population,candidate=a,baseline=b,removal='year',removed=year,estimate=float(delta[delta.index.year!=year].mean())))
        for dimension in ['phase','year','regime','industry_id','listing_group','history_group','event_group','industry_stability_group','adaptability_group']:
            for (date,condition),z in f.groupby(['date',dimension]):
                for name in C['formal_models']:
                    r=score(z,name)
                    if r is not None:conditional.append(dict(foundation=foundation,dimension=dimension,condition=condition,model=name,date=date,**r))
        for name in names:
            for date,g in f[f.actual.notna()].groupby('date'):
                z=g.assign(bin=np.minimum((g[name]*10).astype(int),9),event=labels(g.actual))
                for binno,a in z.groupby('bin'):reliability.append(dict(foundation=foundation,model=name,date=date,bin=binno,rows=len(a),origin_rows=len(z),predicted=float(a[name].mean()),observed=float(a.event.mean())))
        calendar=sorted(f.loc[f.actual.notna(),'date'].unique())
        for stock,g in selected.groupby('instrument'):
            z=g[g.actual.notna()].copy();z['event']=labels(z.actual);stage=merged_event_stages(z)
            for name in names:
                y=z.event.to_numpy();p=z[name].to_numpy()
                company.append(dict(foundation=foundation,instrument=stock,model=name,months=len(z),events=int(y.sum()),risk_stages=stage,
                    nonoverlap_events=nonoverlap_count(z,1),nonoverlap_labels=nonoverlap_count(z),brier=float(np.mean((p-y)**2)),
                    bias=float(np.mean(p-y)),temporal_auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else np.nan,
                    inference='descriptive only; repeated history and few independent stages'))
            d=(z.GPI-z.event)**2-(z.G-z.event)**2;v=pd.Series(d.to_numpy(),index=z.date).reindex(calendar)
            for block in C['bootstrap']['blocks']:company_ci.append(dict(foundation=foundation,instrument=stock,**ci(v,block),single_stock_significance_claim=False))
        for (date),z in f[f.label_end.notna()].groupby('date'):
            known=z.actual.notna();y=labels(z.actual);a=z.GPI.to_numpy();b=z.G.to_numpy()
            loss=float(np.sum((a[known]-y[known])**2-(b[known]-y[known])**2));d0=a[~known]**2-b[~known]**2;d1=(1-a[~known])**2-(1-b[~known])**2
            bounds.append(dict(foundation=foundation,date=date,rows=len(z),missing=int((~known).sum()),lower=(loss+np.minimum(d0,d1).sum())/len(z),upper=(loss+np.maximum(d0,d1).sum())/len(z)))
        for date,g in f.groupby('date'):
            corrections.append(dict(foundation=foundation,date=date,rows=len(g),individual_adapted=int(g.individual_reason.eq('adapted').sum()),
                peer_adapted=int(g.peer_reason.str.startswith('adapted').sum()),global_fallback=int(g.adaptability_group.eq('global_fallback').sum()),
                mean_abs_delta_G=float(abs(g.delta_G).mean()),mean_abs_delta_GP=float(abs(g.delta_GP).mean()),
                tau_G=float(g.tau_G.iloc[0]),tau_GP=float(g.tau_GP.iloc[0]),mean_individual_sd=float(g.individual_sd.mean()),
                mean_effective_months=float(g.individual_effective_months.mean())))
        print('Scored',foundation,flush=True)
    for name,rows in [('monthly_scores',monthly),('summary',summary),('paired_intervals',intervals),('conditional_monthly',conditional),
                      ('company_scores',company),('company_intervals',company_ci),('reliability',reliability),('leave_out',robust),('missing_bounds',bounds),('corrections',corrections),
                      ('auxiliary_intervals',aux),('phase_intervals',phases)]:
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False)
    con=pd.DataFrame(conditional)
    con.groupby(['foundation','dimension','condition','model']).agg(months=('date','size'),stock_months=('rows','sum'),events=('events','sum'),
        brier=('brier','mean'),auc=('auc','mean'),pr_auc=('pr_auc','mean'),bias=('bias','mean'),ece=('ece','mean')).reset_index().to_csv(OUT/'conditional_summary.csv',index=False)
    write_json(AUDIT/'scoring.json',dict(passed=True,matched_rows=True,formal_models_per_foundation=5,secondary_foundation='L2',
        single_case=cohorts['single_stock'],cohort_companies=len(stocks),real_independent_confirmation=False))
    print(pd.DataFrame(summary)[['foundation','population','model','brier','pooled_brier','company_equal_brier']].to_string(index=False),flush=True)


if __name__=='__main__':main()
