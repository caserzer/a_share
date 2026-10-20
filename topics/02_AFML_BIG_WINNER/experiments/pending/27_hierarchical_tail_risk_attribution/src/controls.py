"""Source-separated positive controls and month-industry conditional permutation."""
from scipy.special import expit
from core import *
from conditional import conditional_auc


def permute_conditionally(frame,h=6):
    out=frame.copy()
    for (date,industry),g in out.groupby(['date','industry_id'],sort=True):
        g=g[g[f'y_{h}'].notna()];seed=int(hashlib.sha256(f"{C['controls']['conditional_permutation_seed']}:{date}:{industry}".encode()).hexdigest()[:12],16)
        out.loc[g.index,f'y_{h}']=np.random.default_rng(seed).permutation(g[f'y_{h}'].to_numpy())
    return out


def synthetic(world):
    world_index=['market','industry','individual'].index(world);rng=np.random.default_rng(C['controls']['seed']+world_index)
    months=146;stocks=C['controls']['stocks_per_month'];dates=np.repeat(pd.date_range('2000-01-31',periods=months,freq='ME'),stocks);n=len(dates)
    industry=np.tile(np.arange(stocks)%5,months);signal=rng.choice([-1.,1.],n);market=np.repeat(rng.choice([-1.,1.],months),stocks)
    f=pd.DataFrame({col:rng.normal(0,.2,n) for col in sorted(set(sum([feature_names(name) for name in C['candidates']],[]))-set(C['categorical_features']))})
    f['date']=dates;f['instrument']=[f'S{j%stocks:04d}' for j in range(n)];f['board']=0;f['vol63']=np.exp(rng.normal(-1,.2,n));f['log_cap']=rng.normal(24,.5,n)
    f['industry_id']=['synthetic:'+str(j) for j in industry];f['industry_sector']='SYNTHETIC';f['industry_age_days']=180;f['industry_stale']=0;f['industry_peer_count']=31
    f['industry_mom63']=0.;f['industry_mom126']=0.;f['industry_breadth63']=.5
    for col in C['market_features']:f[col]=0.
    f['market_mom126']=market;f['market_vol63']=.2;f['state_breadth63']=.5
    f['earnings_yield']=signal;f['financial_age_days']=456.;f['financial_available']=1.
    logits=np.full(n,-1.3)
    if world=='market':logits+=1.7*market
    elif world=='industry':logits+=1.3*np.array([-1.5,-.5,0.,.7,1.3])[industry]
    else:logits+=1.8*signal
    f['oracle_probability']=expit(logits);event=rng.random(n)<f.oracle_probability;f['y_6']=np.where(event,-.25,.05);f['end_6']=f.date+pd.DateOffset(months=6)
    train=f.iloc[:80*stocks].copy();test=f.iloc[86*stocks:].copy();assert train.end_6.max()<test.date.min()
    predictions={};models=['M_R','M_RM','M_RMI','M_RMIVF']
    for name in models:
        model=fit_model(train,name,6);predictions[name]=predict(model,test,name);model.save_model(str(CACHE/f'synthetic_{world}_{name}.cbm'))
    rows=[]
    for name,p in predictions.items():
        z=test.copy();z['probability']=p;z['actual']=z.y_6
        for date,g in z.groupby('date'):
            result=metrics(g.probability,g.actual);inside,_=conditional_auc(g)
            rows.append(dict(world=world,model=name,date=date,industry_auc=inside['conditional_auc'],**result))
    monthly=pd.DataFrame(rows);monthly.to_csv(OUT/f'positive_{world}_monthly.csv',index=False)
    before,after={'market':('M_R','M_RM'),'industry':('M_RM','M_RMI'),'individual':('M_RMI','M_RMIVF')}[world]
    contrast=ci(paired(monthly[monthly.model.eq(after)],monthly[monthly.model.eq(before)],'brier'),6)
    independent=ci(paired(monthly[monthly.model.eq('M_RMIVF')],monthly[monthly.model.eq('M_RMI')],'industry_auc'),6)
    correct=contrast['high95']<-C['controls']['minimum_source_brier_gain']
    no_false_independent=True if world=='individual' else bool(independent['low_family']<=0 and abs(independent['estimate'])<.05)
    test[['date','instrument','industry_id','oracle_probability','y_6']].assign(**{name:p for name,p in predictions.items()}).to_parquet(CACHE/f'synthetic_{world}_predictions.parquet',index=False)
    return dict(world=world,comparison=after+'-'+before,correct_source_gain=contrast,no_false_independent_signal=no_false_independent,independent_auc_difference=independent,passed=bool(correct and no_false_independent))


def negative():
    panel=load_panel();records=[];audits=[]
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        train,test=split(panel,6,quarter);tr=permute_conditionally(train);te=permute_conditionally(test)
        for a,b in [(train,tr),(test,te)]:
            old=a.assign(event=labels(a.y_6)).groupby(['date','industry_id']).event.agg(['sum','count']);new=b.assign(event=labels(b.y_6)).groupby(['date','industry_id']).event.agg(['sum','count']);pd.testing.assert_frame_equal(old,new)
            np.testing.assert_array_equal(a.y_6.isna(),b.y_6.isna())
        for name in ['M_RMI','M_RMIVF']:
            model=fit_model(tr,name,6);p=predict(model,te,name);model.save_model(str(CACHE/f'negative_{quarter}_{name}.cbm'))
            z=te.copy();z['probability']=p;z['actual']=z.y_6
            for date,g in z.groupby('date'):
                result=metrics(g.probability,g.actual)
                if result is not None:
                    conditional,_=conditional_auc(g);records.append(dict(model=name,date=date,industry_auc=conditional['conditional_auc'],industry_coverage=conditional['coverage'],**result))
        audits.append(dict(quarter=str(quarter),train_rows=len(tr),max_label=str(tr.end_6.max().date()),month_industry_counts_and_missing_positions_preserved=True))
    monthly=pd.DataFrame(records);monthly.to_csv(OUT/'negative_conditional_monthly.csv',index=False);write_json(OUT/'negative_fits.json',audits)
    auc=ci(monthly[monthly.model.eq('M_RMIVF')].sort_values('date').industry_auc-.5,6)
    difference=ci(paired(monthly[monthly.model.eq('M_RMIVF')],monthly[monthly.model.eq('M_RMI')],'industry_auc'),6)
    passed=auc['low_family']<=0<=auc['high_family'] and abs(auc['estimate'])<.05 and difference['low_family']<=0
    return dict(control='month_industry_label_permutation',passed=bool(passed),full_industry_auc_minus_half=auc,full_minus_base_industry_auc=difference,group_event_rates_and_missingness_preserved=True)


def main():
    assert json.loads((OUT/'p0_audit.json').read_text())['pass_for_limited_exploration']
    originals={name:digest(path/'outputs/controls.json') for name,path in [('EP25',EP25),('EP26',EP26)]}
    assert all(json.loads((path/'outputs/controls.json').read_text())['all_passed'] for path in [EP25,EP26])
    positives=[synthetic(world) for world in ['market','industry','individual']];neg=negative()
    result=dict(positive_controls=positives,negative_control=neg,prior_controls_retained_sha256=originals,all_passed=all(r['passed'] for r in positives) and neg['passed'])
    write_json(OUT/'controls.json',result);print(result,flush=True);assert result['all_passed'],'Control failed: audit, do not change seeds or search favorable controls'

if __name__=='__main__':main()
