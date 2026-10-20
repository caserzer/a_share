"""Fixed positive worlds and one conditional-permutation realization; never retry seeds."""
from scipy.special import expit
from core import *
from conditional import conditional_auc
from run import freeze


def permute_conditionally(frame):
    out=frame.copy()
    for (date,industry),g in out.groupby(['date','industry_id'],sort=True):
        g=g[g.y_6.notna()]
        seed=int(hashlib.sha256(f"{C['controls']['permutation_seed']}:{date}:{industry}".encode()).hexdigest()[:12],16)
        out.loc[g.index,'y_6']=np.random.default_rng(seed).permutation(g.y_6.to_numpy())
    return out


def synthetic(world):
    number=['common_tail','individual','distress_change'].index(world)
    rng=np.random.default_rng(C['controls']['seed']+number);stocks=C['controls']['stocks_per_month']
    months=C['controls']['train_months']+6+C['controls']['test_months'];n=months*stocks
    dates=np.repeat(pd.date_range('2000-01-31',periods=months,freq='ME'),stocks)
    signal=np.repeat(rng.choice([-1.,1.],months),stocks) if world=='common_tail' else rng.choice([-1.,1.],n)
    f=pd.DataFrame(dict(date=dates,instrument=[f'S{i%stocks:04}' for i in range(n)],log_cap=rng.normal(24,.5,n),vol63=np.exp(rng.normal(-1,.2,n)),static_distress=rng.normal(0,1,n),signal=signal))
    f['oracle']=expit(-1.3+1.7*signal);y=rng.random(n)<f.oracle
    f['y_6']=np.where(y,-.25,.05);f['end_6']=f.date+pd.DateOffset(months=6)
    tr=f.iloc[:80*stocks];te=f.iloc[86*stocks:].copy();assert tr.end_6.max()<te.date.min()
    baseline=['log_cap','vol63']+(['static_distress'] if world=='distress_change' else [])
    rows=[];saved=te.copy()
    for name,cols in [('base',baseline),('signal',baseline+['signal'])]:
        model=CatBoostClassifier(**C['catboost']);model.fit(tr[cols],labels(tr.y_6),sample_weight=weights(tr))
        p=model.predict_proba(te[cols])[:,1];saved[name]=p;model.save_model(str(CACHE/f'positive_{world}_{name}.cbm'))
        z=te.assign(probability=p)
        for date,g in z.groupby('date'):rows.append(dict(world=world,model=name,date=date,**metrics(g.probability,g.y_6)))
    saved.to_parquet(CACHE/f'positive_{world}_predictions.parquet',index=False)
    m=pd.DataFrame(rows);m.to_csv(OUT/f'positive_{world}_monthly.csv',index=False)
    result=ci(paired(m[m.model.eq('signal')],m[m.model.eq('base')],'brier'),6)
    return dict(world=world,**result,passed=bool(result['high95']<-C['controls']['positive_min_brier_gain']))


def negative():
    panel=load_panel();rows=[];audits=[]
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        outpath=CACHE/f'negative_{quarter}.parquet';auditpath=EP/f'outputs/audits/negative_{quarter}.json'
        if auditpath.exists():
            r=json.loads(auditpath.read_text());assert digest(outpath)==r['sha256'];rows.append(pd.read_parquet(outpath));audits.append(r);continue
        tr,te=split(panel,6,quarter);train=permute_conditionally(tr);test=permute_conditionally(te)
        for a,b in [(tr,train),(te,test)]:
            pd.testing.assert_frame_equal(a.assign(event=labels(a.y_6)).groupby(['date','industry_id']).event.agg(['sum','count']),b.assign(event=labels(b.y_6)).groupby(['date','industry_id']).event.agg(['sum','count']))
            np.testing.assert_array_equal(a.y_6.isna(),b.y_6.isna())
        rr=[]
        for name in ['M_R','L1','L2','L4']:
            model=fit_model(train,name,6);p=predict(model,test,name)
            model.save_model(str(CACHE/f'negative_{quarter}_{name}.cbm'))
            z=test.copy();z['probability']=p;z['actual']=z.y_6;z['model']=name;rr.append(z[['date','instrument','industry_id','actual','probability','model']])
        z=pd.concat(rr,ignore_index=True);z.to_parquet(outpath,index=False);rows.append(z)
        r=dict(quarter=str(quarter),sha256=digest(outpath),models_fit=4,training_labels_before=str(quarter.start_time),group_event_counts_and_missing_positions_preserved=True)
        write_json(auditpath,r);audits.append(r);print('negative',quarter,flush=True)
    full=pd.concat(rows,ignore_index=True);monthly=[]
    for (name,date),g in full.groupby(['model','date']):
        r=metrics(g.probability,g.actual)
        if r is not None:
            s,_=conditional_auc(g);monthly.append(dict(model=name,date=date,industry_auc=s['conditional_auc'],industry_coverage=s['coverage'],**r))
    m=pd.DataFrame(monthly);m.to_csv(OUT/'negative_monthly.csv',index=False);checks=[]
    for name in ['M_R','L1','L2','L4']:
        r=ci(m[m.model.eq(name)].sort_values('date').industry_auc-.5,6)
        checks.append(dict(model=name,industry_auc_minus_half=r,passed=bool(r['low_family']<=0<=r['high_family'] and abs(r['estimate'])<.05)))
    write_json(EP/'outputs/audits/negative_fit_audit.json',audits)
    assert sum(x['models_fit'] for x in audits)==C['maximum_permutation_fits']
    return dict(checks=checks,passed=all(x['passed'] for x in checks),warning='common and industry rates preserved; overall Brier may still improve')


def main():
    freeze();positive=[synthetic(w) for w in ['common_tail','individual','distress_change']];neg=negative()
    result=dict(positive=positive,negative=neg,all_passed=all(x['passed'] for x in positive) and neg['passed'])
    write_json(EP/'outputs/audits/controls.json',result)
    print(json.dumps(result,indent=2),flush=True)
    assert result['all_passed'],'Audit control failure; do not change seed or specifications'


if __name__=='__main__':main()
