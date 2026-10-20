"""P2 scoring, conditional discrimination, matched risks and isolated Oracle accounting."""
from core import *
from conditional import conditional_auc,make_pairs,error_decomposition
CONTRASTS=[('B1','B0'),('M_R','B0'),('M_R','B1'),('M_RM','M_R'),('M_RMI','M_RM'),('M_RMIV','M_RMI'),('M_RMIF','M_RMI'),('M_RMIVF','M_RMI'),('M_RMIVF','M_RMIV'),('M_RMIVF','M_RMIF')]


def variance_accounting(frame,value):
    monthly=[]
    for date,raw in frame.groupby('date'):
        g=risk_cells(raw);g=g[g.actual.notna()].copy()
        if not len(g):continue
        g['value']=labels(g.actual) if value=='oracle_outcome' else g[value]
        mean=float(g.value.mean());industry=g.groupby('industry_id').value.transform('mean');cell=g.groupby('risk_cell').value.transform('mean')
        monthly.append(dict(date=date,mean=mean,second=float((g.value**2).mean()),industry=float(np.mean((industry-mean)**2)),risk_cell=float(np.mean((cell-industry)**2)),individual=float(np.mean((g.value-cell)**2))))
    t=pd.DataFrame(monthly);grand=t['mean'].mean();common=float(np.mean((t['mean']-grand)**2));total=float(t.second.mean()-grand**2)
    parts=dict(common=common,industry=float(t.industry.mean()),risk_cell=float(t.risk_cell.mean()),individual=float(t.individual.mean()))
    assert np.isclose(sum(parts.values()),total,atol=1e-12)
    return [dict(component=k,variance=v,share=v/total if total>0 else np.nan,total_variance=total,months=len(t)) for k,v in parts.items()]


def main():
    assert json.loads((OUT/'p1_gate.json').read_text())['passed']
    full=pd.read_parquet(CACHE/'all_predictions.parquet');records=[];groups=[];decomp=[]
    for (h,model,date),raw in full.groupby(['horizon','model','date'],sort=True):
        g=risk_cells(raw.reset_index(drop=True));flags={str(int(f*100)):warning(g.probability,g.instrument,f) for f in [.1,.2]};r=metrics(g.probability,g.actual,flags)
        if r is None:continue
        entry=dict(horizon=h,model=model,date=date,**r)
        if h==6:
            for group,label in [('industry_id','industry'),('risk_cell','matched_cell')]:
                stats,gg=conditional_auc(g,group=group)
                entry.update({label+'_auc':stats['conditional_auc'],label+'_coverage':stats['coverage'],label+'_eligible_groups':stats['eligible_groups']})
                for row in gg:groups.append(dict(model=model,date=date,group_type=label,**row))
            decomp.append(dict(model=model,date=date,**error_decomposition(g)))
        records.append(entry)
    monthly=pd.DataFrame(records);monthly.to_csv(OUT/'monthly_scores.csv',index=False);pd.DataFrame(groups).to_csv(OUT/'conditional_group_audit.csv',index=False);pd.DataFrame(decomp).to_csv(OUT/'error_decomposition.csv',index=False)
    measures=[c for c in monthly if c not in ['horizon','model','date','rows','events']]
    summary=monthly.groupby(['horizon','model'])[measures].mean().reset_index();counts=monthly.groupby(['horizon','model']).agg(months=('date','size'),stock_months=('rows','sum'),events=('events','sum')).reset_index()
    summary=summary.merge(counts,on=['horizon','model']);summary.to_csv(OUT/'summary.csv',index=False)
    intervals=[]
    for h,g in monthly.groupby('horizon'):
        for a,b in CONTRASTS:
            for metric in ['brier','auc','pr_auc','common_brier','relative_brier','industry_auc','matched_cell_auc','recall20','enrichment20']:
                if metric not in g:continue
                delta=paired(g[g.model.eq(a)],g[g.model.eq(b)],metric)
                if not np.isfinite(delta).any():continue
                for block in [6,12]:
                    result=ci(delta,block);baseline=float(g[g.model.eq(b)][metric].mean())
                    intervals.append(dict(horizon=h,candidate=a,baseline=b,metric=metric,relative_brier_improvement_percent=-result['estimate']/baseline*100 if metric=='brier' and baseline>0 else np.nan,**result))
    pd.DataFrame(intervals).to_csv(OUT/'paired_intervals.csv',index=False)
    # Every model uses identical stock/date/outcome keys, including the SZ30 evaluation sensitivity.
    reference=full[full.model.eq('B1')].sort_values(['horizon','date','instrument']).reset_index(drop=True)
    for name,g in full.groupby('model'):
        z=g.sort_values(['horizon','date','instrument']).reset_index(drop=True);pd.testing.assert_frame_equal(z[['horizon','date','instrument','actual','label_end']],reference[['horizon','date','instrument','actual','label_end']])
    main=full[full.horizon.eq(6)].copy();conditional=[]
    for population,subset in [('EP26_fixed',main),('SZ30_evaluation_only',main[main.instrument.str.startswith('SZ30')])]:
        for dimension in ['all','year','phase','regime','vol_regime','industry_stale','age_group']:
            sub=subset.copy();sub['condition']='all' if dimension=='all' else sub.date.dt.year.astype(str) if dimension=='year' else sub[dimension].astype(str)
            for (name,date,condition),g in sub.groupby(['model','date','condition']):
                result=metrics(g.probability,g.actual)
                if result is not None:conditional.append(dict(population=population,model=name,date=date,dimension=dimension,condition=condition,**result))
    conditional=pd.DataFrame(conditional);conditional.to_csv(OUT/'conditional_monthly_scores.csv',index=False)
    conditional.groupby(['population','model','dimension','condition']).agg(brier=('brier','mean'),auc=('auc','mean'),pr_auc=('pr_auc','mean'),bias=('bias','mean'),base_rate=('base_rate','mean'),months=('date','size'),stock_months=('rows','sum'),events=('events','sum')).reset_index().to_csv(OUT/'conditional_scores.csv',index=False)
    # Matched pair construction never receives outcomes as a matching criterion.
    base=main[main.model.eq('M_RMI')].copy().rename(columns={'probability':'p_base'});add=main[main.model.eq('M_RMIVF')][['date','instrument','probability']].rename(columns={'probability':'p_full'})
    joint=base.merge(add,on=['date','instrument'],validate='one_to_one');pair_records=[];match_months=[]
    for date,g in joint.groupby('date',sort=True):
        pairs=make_pairs(g);lookup=g.set_index('instrument');nknown=high_events=low_events=discordant=concordant=0
        for row in pairs.to_dict('records'):
            a=lookup.loc[row['high']];b=lookup.loc[row['low']];both=pd.notna(a.actual)&pd.notna(b.actual)
            high=float(a.actual<-.2) if pd.notna(a.actual) else np.nan;low=float(b.actual<-.2) if pd.notna(b.actual) else np.nan
            pair_records.append(dict(date=date,**row,actual_high=a.actual,actual_low=b.actual,event_high=high,event_low=low,base_probability_gap=a.p_base-b.p_base,full_probability_gap=a.p_full-b.p_full,both_known=bool(both)))
            if both:
                nknown+=1;high_events+=int(high);low_events+=int(low);discordant+=int(high!=low);concordant+=int(high>low)
        match_months.append(dict(date=date,target_pairs=C['matching']['target_pairs_per_month'],formed_pairs=len(pairs),known_pairs=nknown,missing_pairs=len(pairs)-nknown,
            high_events=high_events,low_events=low_events,event_difference=(high_events-low_events)/nknown if nknown else np.nan,pair_concordance=concordant/discordant if discordant else np.nan,discordant_pairs=discordant,
            log_cap_gap_mean=float(pairs.log_cap_gap.mean()) if len(pairs) else np.nan,log_vol_gap_mean=float(pairs.log_vol_gap.mean()) if len(pairs) else np.nan))
    pairrows=pd.DataFrame(pair_records);pairrows.to_csv(OUT/'matched_pairs.csv',index=False);matches=pd.DataFrame(match_months);matches.to_csv(OUT/'matched_monthly.csv',index=False)
    evaldates=set(monthly[(monthly.horizon==6)&monthly.model.eq('B1')].date);matched_scored=matches[matches.date.isin(evaldates)]
    mci=[]
    for metric in ['event_difference','pair_concordance']:
        values=matched_scored.sort_values('date')[metric]
        if np.isfinite(values).any():
            for block in [6,12]:mci.append(dict(metric=metric,**ci(values,block)))
    pd.DataFrame(mci).to_csv(OUT/'matched_intervals.csv',index=False)
    # Error-component changes: exact accounting, not newly fitted probability models.
    comp=pd.DataFrame(decomp);components=[]
    for a,b in CONTRASTS:
        for metric in ['common_error','industry_error','risk_cell_error','individual_error']:
            delta=paired(comp[comp.model.eq(a)],comp[comp.model.eq(b)],metric)
            for block in [6,12]:components.append(dict(candidate=a,baseline=b,component=metric,**ci(delta,block)))
    pd.DataFrame(components).to_csv(OUT/'component_intervals.csv',index=False)
    # EP26 score structure and Oracle outcome structure are never forecast inputs.
    old=pd.read_parquet(EP26/'outputs/local_cache/all_predictions.parquet');mapping=main[main.model.eq('B1')][['date','instrument','industry_id','board','log_cap','vol63']]
    variance=[]
    for model in ['M_R','M_VF','M_VFS']:
        g=old[old.model.eq(model)].drop(columns=['industry_id','board','log_cap','vol63'],errors='ignore').merge(mapping,on=['date','instrument'],validate='one_to_one')
        g['probability']=g.p_loss20
        variance += [dict(source='EP26_'+model,**r) for r in variance_accounting(g,'probability')]
    pd.DataFrame(variance).to_csv(OUT/'ep26_prediction_variance_structure.csv',index=False)
    oracle=main[main.model.eq('B1')].copy();pd.DataFrame(variance_accounting(oracle,'oracle_outcome')).to_csv(OUT/'oracle_outcome_variance_not_a_forecast.csv',index=False)
    # Uniform frozen-probability rescore on same ordinary-action reconstruction subset.
    sensitivity=pd.read_parquet(CACHE/'label_sensitivity.parquet');sensitivity=sensitivity[sensitivity.status.eq('ok')&sensitivity.reinvested_return.notna()]
    sr=main.merge(sensitivity[['date','instrument','reinvested_return']],on=['date','instrument'],validate='many_to_one',how='inner');rows=[]
    for (model,date),g in sr.groupby(['model','date']):
        for name,y in [('qfq_same_valid_subset',g.actual),('ordinary_action_reinvested_proxy',g.reinvested_return)]:
            result=metrics(g.probability,y)
            if result is not None:rows.append(dict(model=model,date=date,definition=name,**result))
    pd.DataFrame(rows).to_csv(OUT/'return_sensitivity_monthly.csv',index=False)
    robust=[];phases=[]
    m=monthly[monthly.horizon.eq(6)]
    for a,b in CONTRASTS:
        aa=m[m.model.eq(a)].sort_values('date');bb=m[m.model.eq(b)].sort_values('date');delta=paired(aa,bb,'brier');dates=pd.DatetimeIndex(aa.date)
        for name,mask in [('2021-2023',dates.year<2024),('2024-2026',dates.year>=2024)]:phases.append(dict(candidate=a,baseline=b,phase=name,**ci(delta[mask],6)))
        for i,date in enumerate(dates):robust.append(dict(candidate=a,baseline=b,removal='month',removed=str(date.date()),estimate=float(np.delete(delta,i).mean())))
        for year in set(dates.year):robust.append(dict(candidate=a,baseline=b,removal='year',removed=str(year),estimate=float(delta[dates.year!=year].mean())))
    pd.DataFrame(phases).to_csv(OUT/'phase_intervals.csv',index=False);pd.DataFrame(robust).to_csv(OUT/'leave_out_robustness.csv',index=False)
    bounds=[]
    for (h,model,date),g in full.groupby(['horizon','model','date']):
        z=g[g.label_end.notna()];n=len(z)
        if not n:continue
        known=z.actual.notna();p=z.probability.to_numpy();y=labels(z.actual);u=p[~known];loss=float(np.sum((p[known]-y[known])**2))
        bounds.append(dict(horizon=h,model=model,date=date,mature=n,missing=int((~known).sum()),brier_lower=(loss+np.minimum(u*u,(1-u)**2).sum())/n,brier_upper=(loss+np.maximum(u*u,(1-u)**2).sum())/n))
    pd.DataFrame(bounds).to_csv(OUT/'missing_brier_bounds.csv',index=False)
    write_json(OUT/'p2_gate.json',dict(phase='P2',passed=True,all_preregistered_models_scored=True,paired_same_population=True,conditional_auc_exclusions_recorded=True,matched_observable_pairs_formed=True,
        matched_shortfalls=int((matches.formed_pairs<C['matching']['target_pairs_per_month']).sum()),oracle_strictly_explanatory=True,performance_not_a_gate=True))
    print(summary[summary.horizon.eq(6)][['model','brier','auc','industry_auc','matched_cell_auc']].to_string(index=False),flush=True)

if __name__=='__main__':main()
