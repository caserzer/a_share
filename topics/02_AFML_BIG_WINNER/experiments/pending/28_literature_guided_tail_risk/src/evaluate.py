"""Month-paired inference and explicitly covered conditional diagnostics."""
from core import *
from conditional import conditional_auc,make_pairs,error_decomposition
CONTRASTS=[('B1','B0'),('M_R','B0'),('M_R','B1'),('M_RMI','M_R')]
CONTRASTS += [(n,'M_R') for n in ['L1','L2','L4']]
CONTRASTS += [(n,'M_RMI') for n in ['RMI_L1','RMI_L2','RMI_L4']]
CONTRASTS += [('L1','L1_common'),('L2','L2_systematic'),('L4','L4_price_history')]


def calibration(g):
    z=g[g.actual.notna()].copy();z['event']=labels(z.actual);z['bin']=np.minimum((z.probability*10).astype(int),9)
    table=z.groupby('bin').agg(rows=('event','size'),predicted=('probability','mean'),observed=('event','mean')).reset_index()
    ece=float(np.sum(table.rows*abs(table.predicted-table.observed))/len(z)) if len(z) else np.nan
    return ece,table


def main():
    full=pd.read_parquet(CACHE/'all_predictions.parquet');records=[];groups=[];decomp=[];reliability=[]
    reference=full[full.model.eq('M_R')].sort_values(['date','instrument']).reset_index(drop=True)
    for name,g in full.groupby('model'):
        z=g.sort_values(['date','instrument']).reset_index(drop=True)
        pd.testing.assert_frame_equal(z[['date','instrument','actual','label_end']],reference[['date','instrument','actual','label_end']])
    for (model,date),raw in full.groupby(['model','date'],sort=True):
        g=risk_cells(raw.reset_index(drop=True));flags={str(int(f*100)):warning(g.probability,g.instrument,f) for f in [.05,.1,.2]}
        r=metrics(g.probability,g.actual,flags)
        if r is None:continue
        ece,rel=calibration(g);entry=dict(model=model,date=date,ece=ece,**r)
        reliability.extend(rel.assign(model=model,date=date).to_dict('records'))
        for group,label in [('industry_id','industry'),('risk_cell','matched_cell')]:
            stats,gg=conditional_auc(g,group=group)
            entry.update({label+'_auc':stats['conditional_auc'],label+'_coverage':stats['coverage'],label+'_eligible_groups':stats['eligible_groups']})
            groups.extend([dict(model=model,date=date,group_type=label,**row) for row in gg])
        records.append(entry);decomp.append(dict(model=model,date=date,**error_decomposition(g)))
    monthly=pd.DataFrame(records);monthly.to_csv(OUT/'monthly_scores.csv',index=False)
    pd.DataFrame(groups).to_csv(OUT/'conditional_group_audit.csv',index=False)
    pd.DataFrame(reliability).to_csv(OUT/'reliability_monthly.csv',index=False)
    comp=pd.DataFrame(decomp);comp.to_csv(OUT/'error_decomposition.csv',index=False)
    cols=[c for c in monthly if c not in ['model','date','rows','events']]
    summary=monthly.groupby('model')[cols].mean().reset_index().merge(monthly.groupby('model').agg(months=('date','size'),stock_months=('rows','sum'),events=('events','sum')).reset_index())
    summary.to_csv(OUT/'summary.csv',index=False)
    intervals=[];components=[];robust=[];phases=[]
    for a,b in CONTRASTS:
        aa=monthly[monthly.model.eq(a)].sort_values('date');bb=monthly[monthly.model.eq(b)].sort_values('date')
        for metric in ['brier','auc','pr_auc','common_brier','relative_brier','industry_auc','matched_cell_auc','recall5','recall10','recall20','enrichment5','enrichment10','enrichment20','ece','bias']:
            delta=paired(aa,bb,metric)
            if not np.isfinite(delta).any():continue
            for block in C['bootstrap']['blocks']:
                result=ci(delta,block)
                intervals.append(dict(candidate=a,baseline=b,metric=metric,relative_brier_improvement_percent=-result['estimate']/bb.brier.mean()*100 if metric=='brier' else np.nan,**result))
        for metric in ['common_error','industry_error','risk_cell_error','individual_error']:
            delta=paired(comp[comp.model.eq(a)],comp[comp.model.eq(b)],metric)
            for block in C['bootstrap']['blocks']:components.append(dict(candidate=a,baseline=b,component=metric,**ci(delta,block)))
        delta=paired(aa,bb,'brier');dates=pd.DatetimeIndex(aa.date)
        for name,mask in [('2021-2023',dates.year<2024),('2024-2026',dates.year>=2024)]:
            for block in C['bootstrap']['blocks']:phases.append(dict(candidate=a,baseline=b,phase=name,**ci(delta[mask],block)))
        for i,date in enumerate(dates):robust.append(dict(candidate=a,baseline=b,removal='month',removed=str(date.date()),estimate=float(np.delete(delta,i).mean())))
        for year in sorted(set(dates.year)):robust.append(dict(candidate=a,baseline=b,removal='year',removed=str(year),estimate=float(delta[dates.year!=year].mean())))
    for name,table in [('paired_intervals',intervals),('component_intervals',components),('phase_intervals',phases),('leave_out_robustness',robust)]:
        pd.DataFrame(table).to_csv(OUT/f'{name}.csv',index=False)
    conditional=[]
    for dimension in ['all','year','phase','regime','vol_regime','industry_id','industry_stale','age_group']:
        sub=full.copy();sub['condition']='all' if dimension=='all' else sub.date.dt.year.astype(str) if dimension=='year' else sub[dimension].astype(str)
        for (name,date,condition),g in sub.groupby(['model','date','condition']):
            result=metrics(g.probability,g.actual)
            if result is not None:
                ece,_=calibration(g);conditional.append(dict(model=name,date=date,dimension=dimension,condition=condition,ece=ece,**result))
    conditional=pd.DataFrame(conditional);conditional.to_csv(OUT/'conditional_monthly_scores.csv',index=False)
    conditional.groupby(['model','dimension','condition']).agg(brier=('brier','mean'),auc=('auc','mean'),pr_auc=('pr_auc','mean'),bias=('bias','mean'),ece=('ece','mean'),base_rate=('base_rate','mean'),months=('date','size'),stock_months=('rows','sum'),events=('events','sum')).reset_index().to_csv(OUT/'conditional_scores.csv',index=False)
    pairs_all=[];match_months=[]
    for name in ['L1','L2','L4','RMI_L1','RMI_L2','RMI_L4']:
        base='M_RMI' if name.startswith('RMI') else 'M_R'
        joint=full[full.model.eq(base)].rename(columns={'probability':'p_base'}).merge(full[full.model.eq(name)][['date','instrument','probability']].rename(columns={'probability':'p_full'}),on=['date','instrument'],validate='one_to_one')
        for date,g in joint.groupby('date',sort=True):
            pp=make_pairs(g);lookup=g.set_index('instrument');known=high=low=discordant=concordant=0
            for row in pp.to_dict('records'):
                a=lookup.loc[row['high']];b=lookup.loc[row['low']]
                ea=float(a.actual<-.2) if pd.notna(a.actual) else np.nan;eb=float(b.actual<-.2) if pd.notna(b.actual) else np.nan
                both=np.isfinite(ea+eb)
                pairs_all.append(dict(model=name,date=date,**row,event_high=ea,event_low=eb,both_known=both))
                if both:known+=1;high+=ea;low+=eb;discordant+=int(ea!=eb);concordant+=int(ea>eb)
            match_months.append(dict(model=name,date=date,target_pairs=20,formed_pairs=len(pp),known_pairs=known,
                stock_coverage=2*known/g.actual.notna().sum() if g.actual.notna().any() else np.nan,
                high_events=high,low_events=low,event_difference=(high-low)/known if known else np.nan,
                pair_concordance=concordant/discordant if discordant else np.nan,discordant_pairs=discordant))
    pd.DataFrame(pairs_all).to_csv(OUT/'matched_pairs.csv',index=False)
    mm=pd.DataFrame(match_months);mm.to_csv(OUT/'matched_monthly.csv',index=False);mi=[]
    evaldates=set(monthly.date)
    for name,g in mm[mm.date.isin(evaldates)].groupby('model'):
        for metric in ['event_difference','pair_concordance']:
            for block in C['bootstrap']['blocks']:mi.append(dict(model=name,metric=metric,**ci(g.sort_values('date')[metric],block)))
    pd.DataFrame(mi).to_csv(OUT/'matched_intervals.csv',index=False)
    bounds=[]
    for name in ['L1','L2','L4']:
        g=full[full.model.eq(name)].merge(reference[['date','instrument','probability']].rename(columns={'probability':'base'}),on=['date','instrument'],validate='one_to_one')
        for date,z in g[g.label_end.notna()].groupby('date'):
            y=labels(z.actual);known=np.isfinite(y);p=z.probability.to_numpy();b=z.base.to_numpy()
            loss=np.sum((p[known]-y[known])**2-(b[known]-y[known])**2)
            d0=p[~known]**2-b[~known]**2;d1=(1-p[~known])**2-(1-b[~known])**2
            bounds.append(dict(model=name,date=date,mature=len(z),missing=int((~known).sum()),delta_lower=(loss+np.minimum(d0,d1).sum())/len(z),delta_upper=(loss+np.maximum(d0,d1).sum())/len(z)))
    pd.DataFrame(bounds).to_csv(OUT/'missing_paired_brier_bounds.csv',index=False)
    pooled=[dict(model=name,**metrics(g.probability,g.actual)) for name,g in full.groupby('model')]
    pd.DataFrame(pooled).to_csv(OUT/'pooled_diagnostic.csv',index=False)
    write_json(EP/'outputs/audits/scoring.json',dict(passed=True,same_keys_labels=True,models=len(summary),months=int(summary.months.min()),no_performance_gate=True))
    print(summary[['model','brier','auc','industry_auc','matched_cell_auc','bias','ece']].to_string(index=False),flush=True)


if __name__=='__main__':main()
