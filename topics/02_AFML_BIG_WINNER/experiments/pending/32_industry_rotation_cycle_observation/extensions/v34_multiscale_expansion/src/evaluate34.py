"""Matched selection budgets, full-label denominators and all-alert economics."""
from common34 import *
from evaluate31 import summarize


def interval(dates,values):
    g=pd.DataFrame(dict(month=pd.DatetimeIndex(dates).to_period('M'),value=np.asarray(values)))
    a=g.groupby('month').value.agg(['sum','count'])
    if a.empty:return dict(estimate=np.nan,lower95=np.nan,upper95=np.nan,lower9=np.nan,upper9=np.nan,span_months=0)
    a=a.reindex(pd.period_range(a.index.min(),a.index.max(),freq='M'),fill_value=0).to_numpy(float)
    rng=np.random.default_rng(32);draws=[]
    for _ in range(5000):
        starts=rng.integers(0,len(a),size=int(np.ceil(len(a)/12)))
        ids=np.concatenate([(s+np.arange(12))%len(a) for s in starts])[:len(a)]
        sums=a[ids].sum(axis=0)
        if sums[1]:draws.append(sums[0]/sums[1])
    return dict(estimate=a[:,0].sum()/a[:,1].sum(),lower95=np.quantile(draws,.025),upper95=np.quantile(draws,.975),
        lower9=np.quantile(draws,.05/18),upper9=np.quantile(draws,1-.05/18),span_months=len(a))


def run():
    receipt=json.loads((OUT/'prediction_receipt.json').read_text())
    assert sha(CACHE/'scores.parquet')==receipt['scores_sha256']
    scores=pd.read_parquet(CACHE/'scores.parquet')
    labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    outcomes=pd.read_parquet(ECON/'outcomes.parquet')
    market=pd.read_parquet(OLD/'CSI_ALL.parquet').close.sort_index();calendar=pd.DatetimeIndex(market.index)
    phases=pd.read_parquet(OLD/'daily_phases.parquet').set_index('phase_id')
    predictions=[];classification=[];economics=[];annual=[];daily=[];coverage=[];details=[];checks=[]
    for path in sorted((ECON/'frames').glob('*.parquet')):
        task=path.stem;f=pd.read_parquet(path)
        f=f.merge(scores,on=IDENTITY,validate='many_to_one')
        assert f[list(GROUPS)].notna().all().all()
        eligible=f.state_eligible.eq(1)&f.market_up
        k=f.select_accepted.groupby([f.date,f.level]).transform('sum')
        select={'accepted':f.select_accepted,'momentum':f.select_momentum_matched,
                'baseline':top_k(f,f.diffusion_tree,k,eligible)}
        for family in GROUPS:
            select[family]=top_k(f,f[family],k,eligible)
            select[family+'_fixed']=f.risk_score.ge(.11)&f[family].ge(.11)&f.market_up
            mask=eligible&f[family+'_complete']
            kc=(f.select_accepted&mask).groupby([f.date,f.level]).transform('sum')
            select['baseline_complete_'+family]=top_k(f,f.diffusion_tree,kc,mask)
            select[family+'_complete']=top_k(f,f[family],kc,mask)
            assert np.array_equal(select[family].groupby([f.date,f.level]).sum(),select['baseline'].groupby([f.date,f.level]).sum())
        f=f.copy()
        for name,mask in select.items():
            f['selected_'+name]=mask;f['first_'+name]=False
            s=f[mask];f.loc[s.index,'first_'+name]=episode_starts(s,calendar)
        destination=CACHE/'evaluation_frames';destination.mkdir(exist_ok=True)
        f.to_parquet(destination/(task+'.parquet'),index=False)
        predictions.append(dict(task=task,path=str(destination/(task+'.parquet')),sha256=sha(destination/(task+'.parquet'))))
        f=f.merge(labels,on=['row_id','threshold','benchmark'],validate='one_to_one')
        f.loc[f.label_available_at.gt(f.date+pd.DateOffset(months=24)),'y']=np.nan
        for level,g in f.groupby('level'):
            sig=dict(task=task,frequency=g.frequency.iloc[0],threshold=g.threshold.iloc[0],benchmark=g.benchmark.iloc[0],level=level)
            primary=level=='L3' and sig['threshold']==.15 and sig['benchmark']=='CSI_ALL'
            known=g[g.y.notna()];positive=known[known.y.eq(1)];events=positive.event_or_witness_id.nunique()
            for name in select:
                hit=known[known['selected_'+name]]
                first=positive[positive['selected_'+name]].groupby('event_or_witness_id').date.min()
                delay=(first-phases.start_date.reindex(first.index)).dt.days
                score=g[name] if name in GROUPS else g.diffusion_tree if name=='baseline' else np.minimum(g.risk_score,g.diffusion_tree) if name=='accepted' else None
                brier=np.mean((score[g.y.notna()]-known.y)**2) if score is not None else np.nan
                classification.append(dict(**sig,method=name,known_observations=len(known),positive_observations=len(positive),
                    all_alerts=int(g['selected_'+name].sum()),known_alerts=len(hit),unknown_alerts=int(g['selected_'+name].sum())-len(hit),
                    precision=hit.groupby('date').y.mean().mean(),point_recall=hit.y.sum()/len(positive),
                    cycle_recall=len(first)/events,evaluable_cycles=events,detected_cycles=len(first),median_delay=delay.median(),brier=brier))
            if not primary:continue
            g=g.merge(outcomes[outcomes.benchmark.eq(sig['benchmark'])].drop(columns='benchmark'),on='row_id',validate='one_to_many')
            for name in select:
                for unit,prefix in [('all_alerts','selected_'),('six_month_launches','first_')]:
                    for months,h in g[g[prefix+name]].groupby('months'):
                        economics.append(dict(**sig,method=name,unit=unit,months=months,**summarize(h)))
                        for status,part in h.groupby('outcome_status'):
                            coverage.append(dict(**sig,method=name,unit=unit,months=months,status=status,count=len(part)))
                        if months!=6:continue
                        for year,part in h.groupby(h.date.dt.year):
                            annual.append(dict(**sig,method=name,unit=unit,year=year,**summarize(part)))
                        good=h[h.outcome_status.eq('OK')]
                        dates=good.groupby('date').excess_return.mean().rename('excess').reset_index()
                        dates['frequency']=sig['frequency'];dates['method']=name;dates['unit']=unit;daily.append(dates)
                        if unit=='six_month_launches' and name in ['accepted','baseline','levels','paths','stage','momentum']:
                            cols=['row_id','date','era','level','industry_code','industry_name','block','frequency','y','entry_date','end_date',
                                'outcome_status','industry_return','excess_return','max_drawdown']
                            details.append(h[cols].assign(method=name))
            checks.append('matched budgets and full event denominator '+task)
        print('evaluated fixed three-family experiment',task,flush=True)
    c=pd.DataFrame(classification);c.to_csv(OUT/'classification_all_tasks.csv',index=False)
    c.query("level=='L3' and threshold==0.15 and benchmark=='CSI_ALL'").to_csv(OUT/'classification_primary.csv',index=False)
    pd.DataFrame(economics).to_csv(OUT/'economics_primary.csv',index=False)
    pd.DataFrame(annual).to_csv(OUT/'annual_economics.csv',index=False)
    pd.DataFrame(coverage).to_csv(OUT/'outcome_coverage.csv',index=False)
    pd.concat(details).to_csv(OUT/'primary_six_month_launches.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    dates=pd.concat(daily,ignore_index=True);dates.to_csv(OUT/'daily_excess.csv',index=False)
    intervals=[]
    for (frequency,unit),g in dates.groupby(['frequency','unit']):
        p=g.pivot(index='date',columns='method',values='excess')
        for family in GROUPS:
            for scope,left,right in [('full',family,'baseline'),('complete',family+'_complete','baseline_complete_'+family)]:
                pair=p[[left,right]].dropna();diff=pair[left]-pair[right]
                intervals.append(dict(frequency=frequency,unit=unit,family=family,scope=scope,paired_dates=len(pair),
                    **interval(pair.index,diff)))
    pd.DataFrame(intervals).to_csv(OUT/'paired_intervals.csv',index=False)
    js(OUT/'evaluation_receipt.json',dict(predictions=predictions,checks=checks,
        primary_comparisons=9,primary_horizon_months=6,bootstrap_repeats=5000,block_months=12,
        strict_PIT='BLOCKED_DATA',independent_forward_validation='FORWARD_PENDING'))
    print(pd.DataFrame(economics).query("unit=='six_month_launches' and months==6 and method in ['accepted','baseline','levels','paths','stage']")
        [['frequency','method','signals','known_returns','mean_return','mean_excess','median_excess']].to_string(index=False))


if __name__=='__main__':run()
