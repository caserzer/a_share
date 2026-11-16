"""Post-hoc diagnosis of frozen monthly-phase accounts; no new strategy search."""
import json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from common import EP,OUT,PRIVATE,sha,save_json
from q5_followup import DEST as SOURCE
from evaluate_ranking import predictions,block_ci
from summarize import returns

RUN='q5_phase_investigation_20261116'
DEST=OUT/'diagnostics'/RUN
CONFIG=EP/'configs'/f'{RUN}.json'

def freeze():
    if CONFIG.exists():raise RuntimeError('Already frozen')
    DEST.mkdir(parents=True)
    files=[SOURCE/'metrics.csv',SOURCE/'schedule.csv',SOURCE/'comparison_periods.json',OUT/'path_a/expanding_ranking_weekly.csv',PRIVATE/'industry.parquet']
    for model in ['EW','E1','E2','E3']:
        for phase in [1,2,3,4]:
            for cost in ['zero','main','stress']:
                rp=SOURCE/'accounts'/f'{model}__1m__p{phase}__b0__{cost}.json';r=json.loads(rp.read_text());files += [rp,rp.with_suffix('.csv')]
                if cost=='main':files += [r['orders_path'],r['holdings_path']]
    _,pred=predictions('expanding')
    cfg=dict(created_at=datetime.now(timezone.utc).isoformat(),authorization='Continue investigating monthly-phase dependence; no gap repair',status='post_hoc_diagnostic_after_phase_outcomes_seen',tests=['annual and monthly concentration, leave-one-year-out and largest-three-month exclusion as descriptive influence only','exact daily stock PnL minus fees, converted to additive log-wealth contributions','frozen H5/H10/H20 rankIC and Q5 outcomes by signal ordinal on balanced full calendar months','phase holding duration and score/basket overlap','zero/main/stress cost-gap comparison'],primary_end='2025-03-03',supplement='model-common horizon across all four phases; signal diagnostics full months ending before October2026',policy='No new models, parameters, dates or accounts. No imputation or data repairs. Do not interpret post-hoc exclusions as tradable rules. Intervals descriptive without independent hypothesis confirmation.',log_attribution='daily stock contribution=(change in marked stock value-net trade cash)/prior NAV; fee=-actual fee/prior NAV; multiply by log(1+r)/r and sum to recover log NAV exactly',mean_other='mean log return across phase2/3/4 as a diagnostic reference, not a rebalanced investable portfolio')
    save_json(CONFIG,cfg);save_json(DEST/'freeze.json',dict(config_sha256=sha(CONFIG),source_sha256=sha(EP/'src/q5_phase_investigation.py'),inputs=[dict(path=str(f),sha256=sha(f)) for f in files],predictions=pred))
    print('Frozen',len(files),'inputs')

def main():
    freeze_record=json.loads((DEST/'freeze.json').read_text());assert sha(CONFIG)==freeze_record['config_sha256']
    for x in freeze_record['inputs']:assert sha(x['path'])==x['sha256']
    accounts={};receipts={};checks=[]
    def check(name,ok):checks.append(dict(check=name,passed=bool(ok)))
    for model in ['EW','E1','E2','E3']:
        for phase in [1,2,3,4]:
            for cost in ['zero','main','stress']:
                k=(model,phase,cost);rp=SOURCE/'accounts'/f'{model}__1m__p{phase}__b0__{cost}.json';r=json.loads(rp.read_text())
                f=pd.read_csv(rp.with_suffix('.csv'),parse_dates=['date']).set_index('date');accounts[k]=f;receipts[k]=r
                check(str(k)+'_nav_hash',sha(rp.with_suffix('.csv'))==r['nav_sha256'])
    primary=pd.Timestamp('2025-03-03');model_end={model:min(accounts[(model,p,'main')].index.max() for p in [1,2,3,4]) for model in ['EW','E1','E2','E3']}
    annual=[];monthly=[];influence=[];costs=[];daily=[]
    for model in ['EW','E1','E2','E3']:
        for scope,end in [('primary',primary),('model_common',model_end[model])]:
            frame=pd.DataFrame({phase:np.log1p(returns(accounts[(model,phase,'main')].loc[:end,'nav'])) for phase in [1,2,3,4]})
            for phase in [2,3,4,'mean_other']:
                baseline=frame[[2,3,4]].mean(axis=1) if phase=='mean_other' else frame[phase]
                gap=frame[1]-baseline
                for d,value in gap.items():daily.append(dict(model=model,scope=scope,baseline=str(phase),date=d,log_gap=value))
                for year,g in gap.groupby(gap.index.year):
                    ids=g.index;annual.append(dict(model=model,scope=scope,baseline=str(phase),year=year,start=ids.min(),end=ids.max(),days=len(ids),phase1_return=np.expm1(frame.loc[ids,1].sum()),other_return=np.expm1(baseline.loc[ids].sum()),log_gap=g.sum(),relative_return=np.expm1(g.sum())))
                grouped=gap.groupby(gap.index.to_period('M')).sum()
                for month,value in grouped.items():monthly.append(dict(model=model,scope=scope,baseline=str(phase),month=str(month),log_gap=value,relative_return=np.expm1(value)))
                best=grouped.nlargest(3);remaining=gap.loc[~gap.index.to_period('M').isin(best.index)]
                influence.append(dict(model=model,scope=scope,baseline=str(phase),test='full',removed='',days=len(gap),log_gap=gap.sum(),relative_cagr=np.expm1(gap.sum()*252/len(gap)),top3_positive_share=best.sum()/gap.sum() if gap.sum()!=0 else np.nan,positive_months=int(grouped.gt(0).sum()),months=len(grouped)))
                influence.append(dict(model=model,scope=scope,baseline=str(phase),test='exclude_largest_3_months_posthoc',removed='|'.join(map(str,best.index)),days=len(remaining),log_gap=remaining.sum(),relative_cagr=np.expm1(remaining.sum()*252/len(remaining))))
                for year in sorted(gap.index.year.unique()):
                    g=gap.loc[gap.index.year!=year];influence.append(dict(model=model,scope=scope,baseline=str(phase),test='leave_one_year_out',removed=str(year),days=len(g),log_gap=g.sum(),relative_cagr=np.expm1(g.sum()*252/len(g))))
            for phase in [2,3,4]:
                row=dict(model=model,scope=scope,phase=phase,end=end)
                for cost in ['zero','main','stress']:
                    a=accounts[(model,1,cost)].loc[:end];b=accounts[(model,phase,cost)].loc[a.index];n=len(a)
                    row[cost+'_cagr_gap']=a.nav.iloc[-1]**(252/n)-b.nav.iloc[-1]**(252/n)
                    row[cost+'_log_gap']=np.log(a.nav.iloc[-1]/b.nav.iloc[-1])
                row['main_minus_zero_gap']=row['main_cagr_gap']-row['zero_cagr_gap'];costs.append(row)
        initial=accounts[(model,1,'main')].loc[:'2021-01-29','nav']
        for phase in [2,3,4]:check(model+str(phase)+'_shared_january',np.allclose(initial,accounts[(model,phase,'main')].loc[initial.index,'nav'],atol=1e-12))
    for name,rows in [('annual_gaps',annual),('monthly_gaps',monthly),('influence',influence),('cost_decomposition',costs),('daily_log_gaps',daily)]:pd.DataFrame(rows).to_csv(DEST/(name+'.csv'),index=False)
    # Exact stock/fee attribution on the same primary clock.
    stock=[];stock_month=[];pnl_by_account={}
    for model in ['E1','E2','E3']:
        for phase in [1,2,3,4]:
            f=accounts[(model,phase,'main')].loc[:primary];r=receipts[(model,phase,'main')]
            h=pd.read_parquet(r['holdings_path']);h=h.loc[h.date<=primary].copy();h['value']=h.synthetic_units*h.valuation_close
            values=h.pivot(index='date',columns='instrument',values='value').reindex(f.index).fillna(0)
            orders=pd.read_parquet(r['orders_path']);orders=orders.loc[orders.date<=primary].copy();orders['trade_cash']=(orders.units_after-orders.units_before)*orders.qfq_open
            traded=orders.groupby(['date','instrument']).trade_cash.sum().unstack().reindex(index=f.index,columns=values.columns).fillna(0)
            change=values.diff();change.iloc[0]=values.iloc[0]
            prior=f.nav.shift();prior.iloc[0]=1.
            contribution=(change-traded).div(prior,axis=0);contribution['__FEES__']=-f.fees/prior
            ret=returns(f.nav);check(model+str(phase)+'_stock_pnl_reconciles_daily',np.allclose(contribution.sum(axis=1),ret,atol=1e-10))
            scale=pd.Series(1.,index=f.index);nz=ret.abs()>1e-14;scale.loc[nz]=np.log1p(ret.loc[nz])/ret.loc[nz]
            logc=contribution.mul(scale,axis=0);check(model+str(phase)+'_log_wealth',np.isclose(logc.to_numpy().sum(),np.log(f.nav.iloc[-1]),atol=1e-10))
            pnl_by_account[(model,phase)]=logc
        base=pnl_by_account[(model,1)]
        for phase in [2,3,4,'mean_other']:
            if phase=='mean_other':
                other=pnl_by_account[(model,2)].add(pnl_by_account[(model,3)],fill_value=0).add(pnl_by_account[(model,4)],fill_value=0)/3
            else:other=pnl_by_account[(model,phase)]
            delta=base.subtract(other,fill_value=0)
            for instrument,value in delta.sum().items():stock.append(dict(model=model,baseline=str(phase),instrument=instrument,log_gap_contribution=value))
            for month,g in delta.groupby(delta.index.to_period('M')):
                for instrument,value in g.sum().items():stock_month.append(dict(model=model,baseline=str(phase),month=str(month),instrument=instrument,log_gap_contribution=value))
    st=pd.DataFrame(stock);st.to_csv(DEST/'stock_contributions.csv',index=False);pd.DataFrame(stock_month).to_csv(DEST/'stock_month_contributions.csv',index=False)
    inf=pd.DataFrame(influence)
    for model in ['E1','E2','E3']:
        for phase in ['2','3','4','mean_other']:
            actual=st.loc[st.model.eq(model)&st.baseline.eq(phase),'log_gap_contribution'].sum();expected=inf.loc[inf.model.eq(model)&inf.scope.eq('primary')&inf.baseline.astype(str).eq(phase)&inf.test.eq('full'),'log_gap'].iloc[0]
            check(model+phase+'_paired_attribution',np.isclose(actual,expected,atol=1e-10))
    # Fixed horizon ranking, matched by calendar month; no account NAV is synthesized from labels.
    ranking=pd.read_csv(OUT/'path_a/expanding_ranking_weekly.csv',parse_dates=['signal_date'])
    ranking=ranking.loc[ranking.model.isin(['E1','E2','E3'])&ranking.seed.isin(['fixed','equal_seed_ensemble'])&ranking.horizon.isin(['h5','h10','h20'])].copy()
    dates=pd.DataFrame({'signal_date':sorted(ranking.signal_date.unique())});dates['month']=dates.signal_date.dt.to_period('M').astype(str);dates['phase']=dates.groupby('month').cumcount()+1
    ranking=ranking.merge(dates,on='signal_date',validate='many_to_one');ranking=ranking.loc[ranking.phase.le(4)]
    signal=[];signal_pairs=[]
    for scope,last in [('primary','2025-02'),('full_complete_months','2026-09')]:
        part=ranking.loc[ranking.month.between('2021-02',last)]
        for (model,horizon),g in part.groupby(['model','horizon']):
            for metric in ['rank_ic','q5','q5_q1']:
                pivot=g.pivot(index='month',columns='phase',values=metric).reindex(columns=[1,2,3,4]);balanced=pivot.dropna()
                for phase in [1,2,3,4]:
                    x=balanced[phase];signal.append(dict(scope=scope,model=model,horizon=horizon,metric=metric,phase=phase,calendar_months=len(pivot),balanced_months=len(x),all_phase_available=int(pivot[phase].notna().sum()),mean=x.mean(),positive_fraction=x.gt(0).mean()))
                for phase in [2,3,4]:
                    delta=balanced[1]-balanced[phase];lo,hi=block_ci(delta.to_numpy(),L=3)
                    signal_pairs.append(dict(scope=scope,model=model,horizon=horizon,metric=metric,other_phase=phase,months=len(delta),mean_difference=delta.mean(),ci_low=lo,ci_high=hi,interpretation='posthoc descriptive interval, no independent significance claim'))
    pd.DataFrame(signal).to_csv(DEST/'signal_quality.csv',index=False);pd.DataFrame(signal_pairs).to_csv(DEST/'signal_quality_paired.csv',index=False)
    ranking.to_csv(DEST/'signal_quality_source.csv',index=False)
    # Actual schedule duration and rank/basket overlap.
    schedule=pd.read_csv(SOURCE/'schedule.csv',parse_dates=['signal_date','execution_date']);schedule=schedule.loc[schedule.frequency.eq('1m')]
    days=pd.read_parquet(PRIVATE/'qfq_close.parquet').index;durations=[]
    for phase,g in schedule.groupby('phase'):
        ds=g.sort_values('execution_date').execution_date.tolist()
        for a,b in zip(ds[:-1],ds[1:]):durations.append(dict(phase=phase,start=a,next_execution=b,holding_sessions=days.get_loc(b)-days.get_loc(a),calendar_days=(b-a).days,initial_shared_interval=a==ds[0]))
    pd.DataFrame(durations).to_csv(DEST/'holding_durations.csv',index=False)
    pred,consumption=predictions('expanding');assert consumption==freeze_record['predictions']
    pred=pred.loc[pred.model_id.isin(['E1','E2','E3'])&pred.seed_or_ensemble.isin(['fixed','equal_seed_ensemble'])].merge(dates,on='signal_date',validate='many_to_one')
    overlap=[]
    for (model,month),g in pred.loc[pred.month.ge('2021-02')].groupby(['model_id','month']):
        groups={phase:h.dropna(subset=['score']).sort_values(['score','instrument']) for phase,h in g.groupby('phase')}
        if 1 not in groups:continue
        def top(h):return set(h.loc[np.floor(5*np.arange(len(h))/max(1,len(h))).astype(int)==4,'instrument'])
        a=groups[1];ta=top(a)
        for phase in [2,3,4]:
            if phase not in groups:continue
            b=groups[phase];tb=top(b);joined=a[['instrument','score']].merge(b[['instrument','score']],on='instrument',suffixes=('_a','_b'))
            overlap.append(dict(model=model,month=month,phase=phase,common_scored=len(joined),rank_correlation=spearmanr(joined.score_a,joined.score_b).statistic,q5_retention=len(ta&tb)/len(ta) if ta else np.nan,q5_jaccard=len(ta&tb)/len(ta|tb) if ta|tb else np.nan))
    pd.DataFrame(overlap).to_csv(DEST/'score_and_selection_overlap.csv',index=False)
    check('inputs_unchanged',all(sha(x['path'])==x['sha256'] for x in freeze_record['inputs']))
    save_json(DEST/'validation.json',dict(status='PASS' if all(x['passed'] for x in checks) else 'FAIL',checks=checks,models_common_ends=model_end,primary_end=primary,scope='diagnostic only; no newly optimized strategy'))
    assert all(x['passed'] for x in checks)
    print('PASS',len(checks),'checks',flush=True)

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='freeze':freeze()
    else:main()
