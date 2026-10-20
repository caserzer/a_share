"""Supplemental reliability, economic exposure and ES uncertainty; no new forecasts or selection."""
from core import *
from portfolio import es


def calibration_tables():
    full=pd.read_parquet(CACHE/'main_with_calibration.parquet');records=[]
    # Risk alerts are assigned to all predicted stocks before outcomes are inspected.
    for (name,date),g in full.groupby(['model','date']):
        z=g.copy();z['alert20']=warning(z.probability,z.instrument,.2);records.append(z)
    d=pd.concat(records,ignore_index=True);d=d[d.actual.notna()].copy();d['observed']=labels(d.actual);d['bin']=np.minimum((d.probability*10).astype(int),9)
    d['weight']=1/d.groupby(['model','date']).date.transform('size');d['year']=d.date.dt.year.astype(str)
    dates=pd.DatetimeIndex(sorted(d.date.unique()));indices={b:bootstrap_indices(len(dates),b) for b in [6,12]};tables=[];conditions=[]
    for dimension in ['all','year','phase','regime','vol_regime','alert20']:
        z=d.copy();z['condition']='all' if dimension=='all' else z[dimension].astype(str);z['wp']=z.weight*z.probability;z['wy']=z.weight*z.observed
        for (model,condition,date),g in z.groupby(['model','condition','date']):
            flags={str(int(f*100)):warning(g.probability,g.instrument,f) for f in [.1,.2]};result=metrics(g.probability,g.actual,flags)
            conditions.append(dict(model=model,dimension=dimension,condition=condition,date=date,**result))
        for (model,condition,binid),g in z.groupby(['model','condition','bin']):
            monthly=g.groupby('date')[['weight','wp','wy']].sum().reindex(dates,fill_value=0);den=monthly.weight.to_numpy();num=(monthly.wp-monthly.wy).to_numpy()
            for block,idx in indices.items():
                weights_=den[idx].sum(axis=1);valid=weights_>0;draw=num[idx].sum(axis=1)[valid]/weights_[valid];lo,hi=np.quantile(draw,[.025,.975])
                tables.append(dict(model=model,dimension=dimension,condition=condition,probability_bin=int(binid),rows=len(g),events=int(g.observed.sum()),covered_months=g.date.nunique(),calendar_months=len(dates),
                    predicted=float(monthly.wp.sum()/den.sum()),observed=float(monthly.wy.sum()/den.sum()),bias=float(num.sum()/den.sum()),block=block,bias_low95=float(lo),bias_high95=float(hi),
                    evidence='exploratory_sparse' if g.date.nunique()<6 else 'exploratory_not_independently_confirmed'))
    pd.DataFrame(tables).to_csv(OUT/'reliability.csv',index=False);conditions=pd.DataFrame(conditions);conditions.to_csv(OUT/'calibrated_conditional_monthly.csv',index=False)
    conditions.groupby(['model','dimension','condition']).agg(brier=('brier','mean'),auc=('auc','mean'),bias=('bias','mean'),base_rate=('base_rate','mean'),months=('date','size'),rows=('rows','sum'),events=('events','sum')).reset_index().to_csv(OUT/'calibrated_conditional_scores.csv',index=False)
    monthly=pd.read_csv(OUT/'calibration_monthly_scores.csv',parse_dates=['date']);bias=[]
    for name,g in monthly.groupby('model'):
        for block in [6,12]:bias.append(dict(model=name,**ci(g.sort_values('date').bias,block)))
    pd.DataFrame(bias).to_csv(OUT/'probability_bias_intervals.csv',index=False)
    # Transformations are common within month and must not change risk ordering.
    checks=[]
    for name in C['calibration']['models']:
        raw=full[full.model.eq(name)].sort_values(['date','instrument']).reset_index(drop=True)
        for method in ['global','state']:
            z=full[full.model.eq(name+'__'+method)].sort_values(['date','instrument']).reset_index(drop=True)
            pd.testing.assert_frame_equal(raw[['date','instrument']],z[['date','instrument']])
            rank_changes=0;alert_changes=0;maximum_tie_spread=0.;maximum_order_reversal=0.
            for date,g in raw.groupby('date'):
                ix=g.index;original=g.probability.to_numpy();after=z.loc[ix,'probability'].to_numpy()
                rank_changes+=int(not np.array_equal(pd.Series(original).rank(method='average'),pd.Series(after).rank(method='average')))
                alert_changes+=int(np.sum(warning(original,g.instrument,.2)!=warning(after,g.instrument,.2)))
                order=np.argsort(original,kind='stable');maximum_order_reversal=max(maximum_order_reversal,float(np.maximum(-np.diff(after[order]),0).max()))
                for value in np.unique(original):
                    tied=after[original==value]
                    maximum_tie_spread=max(maximum_tie_spread,float(tied.max()-tied.min()))
            checks.append(dict(model=name,method=method,months_with_bitwise_tie_rank_changes=rank_changes,warning_membership_changes=alert_changes,
                maximum_tie_probability_spread=maximum_tie_spread,maximum_order_reversal=maximum_order_reversal,numerical_tolerance=1e-14))
    pd.DataFrame(checks).to_csv(OUT/'calibration_rank_invariance.csv',index=False)
    assert all(r['maximum_tie_probability_spread']<=1e-14 and r['maximum_order_reversal']<=1e-14 and r['warning_membership_changes']==0 for r in checks)


def current_tags(instruments,date,releases,cache):
    available=[r for r in releases if pd.Timestamp(r['published'])<date]
    if not available:return np.full(len(instruments),'UNKNOWN')
    item=max(available,key=lambda r:r['published']);key=item['table_path']
    if key not in cache:
        table=pd.read_parquet(key).set_index('code');table.index=table.index.astype(str).str.zfill(6);era='legacy' if pd.Timestamp(item['published']).year<=2021 else 'revised'
        cache[key]={code:era+':'+major if re.fullmatch('[A-S][0-9]{2}',str(major)) else 'UNKNOWN' for code,major in table.major.items()}
    return np.array([cache[key].get(stock[2:],'UNKNOWN') for stock in instruments])


def economic_tables():
    daily=pd.read_csv(OUT/'portfolio_daily.csv',parse_dates=['date']);monthly=pd.read_csv(OUT/'portfolio_monthly.csv',parse_dates=['date']);cohorts=pd.read_csv(OUT/'portfolio_cohorts.csv',parse_dates=['date'])
    indexpath=TOPIC/'data/processed/index/benchmark_indices_daily.csv';idx=pd.read_csv(indexpath,parse_dates=['date']);idx=idx[idx.index_alias.eq('csi300')].set_index('date').sort_index().close.pct_change(fill_method=None)
    betas=[]
    for (name,cost),g in daily.groupby(['strategy','cost_bps']):
        z=g.set_index('date').join(idx.rename('benchmark_return')).dropna(subset=['daily_return','benchmark_return'])
        beta=float(np.cov(z.daily_return,z.benchmark_return,ddof=1)[0,1]/z.benchmark_return.var(ddof=1));betas.append(dict(strategy=name,cost_bps=cost,days=len(z),realized_csi300_beta=beta))
    pd.DataFrame(betas).to_csv(OUT/'portfolio_beta.csv',index=False)
    esrows=[];datasets=[('six_month_static_cohort',cohorts.pivot(index='date',columns='strategy',values='cohort_return'))]
    datasets += [(f'monthly_rebalance_{cost}bp',g.pivot(index='date',columns='strategy',values='return_value')) for cost,g in monthly.groupby('cost_bps')]
    for name,table in datasets:
        for a,b in [('S1','S0'),('S2','S0'),('S2','S1')]:
            for block in [6,12]:
                bootstrap=bootstrap_indices(len(table),block);x=table[a].to_numpy();y=table[b].to_numpy();k=max(1,int(np.ceil(len(x)*.05)))
                draws=np.sort(x[bootstrap],axis=1)[:,:k].mean(axis=1)-np.sort(y[bootstrap],axis=1)[:,:k].mean(axis=1);lo,hi=np.quantile(draws,[.025,.975])
                esrows.append(dict(dataset=name,comparison=a+'-'+b,months=len(table),block=block,delta_es05=es(x)-es(y),low95=float(lo),high95=float(hi),positive_means='less-negative tail return'))
    pd.DataFrame(esrows).to_csv(OUT/'portfolio_es_intervals.csv',index=False)
    releases=json.loads((EP24/'outputs/local_cache/r32_industry/parse_manifest.json').read_text());cache={};imbalance=[]
    for cost in C['portfolio']['cost_bps']:
        matrices={};dates=None;instruments=None
        for strategy in ['S0','S1','S2']:
            with np.load(CACHE/f'portfolio_{strategy}_{cost}_weights.npz') as f:
                matrices[strategy]=f['weights'];dates=pd.DatetimeIndex(f['dates']);instruments=f['instruments']
        for row,date in enumerate(dates):
            tags=current_tags(instruments,date,releases,cache);sectors=np.unique(tags);weights_={}
            for strategy in matrices:weights_[strategy]=np.array([matrices[strategy][row,tags==tag].sum() for tag in sectors])
            for a,b in [('S1','S0'),('S2','S0'),('S2','S1')]:
                difference=weights_[a]-weights_[b];imbalance.append(dict(date=date,cost_bps=cost,comparison=a+'-'+b,industry_total_variation=float(np.abs(difference).sum()/2),maximum_industry_weight_gap=float(np.abs(difference).max()),unknown_weight_left=float(matrices[a][row,tags=='UNKNOWN'].sum()),unknown_weight_right=float(matrices[b][row,tags=='UNKNOWN'].sum())))
    pd.DataFrame(imbalance).to_csv(OUT/'portfolio_actual_industry_imbalance.csv',index=False)


def main():
    calibration_tables();economic_tables();write_json(OUT/'supplemental_diagnostics_audit.json',dict(calibration_rank_changes_bounded_by_1e14_probability_precision=True,calibration_alerts_exactly_unchanged=True,
        raw_registered_probability_files_unmodified=True,actual_published_industry_drift_measured=True,benchmark_beta_is_posthoc_only=True,es_intervals_resample_origin_months=True,new_models_or_selection_changes=False))
    print('Reliability and economic diagnostics complete.',flush=True)

if __name__=='__main__':main()
