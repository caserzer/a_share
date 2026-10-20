"""Reused immutable EP28 baselines and 16 additional pre-evaluation OOS fits."""
from catboost import CatBoostClassifier
from common import *


def freeze():
    path=MANIFEST/'preregistration.json'
    if path.exists():
        r=json.loads(path.read_text())
        for name,h in r['files'].items():assert digest(EP/name)==h,name
        assert digest(CACHE/'panel.parquet')==r['panel_sha256']
    else:
        assert json.loads((AUDIT/'data_gate.json').read_text())['passed_for_limited_D0_exploration']
        assert json.loads((AUDIT/'unit_tests_before_scoring.json').read_text())['passed']
        files=[EP/'research_plan.md',EP/'configs/preregistration.yaml',EP/'configs/target_cohort.yaml']
        files+=sorted((EP/'src').glob('*.py'))+sorted((EP/'tests').glob('*.py'))
        files+=[AUDIT/'data_gate.json',MANIFEST/'input_sources.csv']
        write_json(path,dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),files={str(p.relative_to(EP)):digest(p) for p in files},
            panel_sha256=digest(CACHE/'panel.parquet'),no_EP29_scores_before_registration=True,independent_holdout=False))
    return digest(path)


def fit_global(train,name):
    y=labels(train.y_6);assert np.isfinite(y).all() and len(np.unique(y))==2
    w=1/train.groupby('date').date.transform('size').to_numpy();w=w/w.mean()
    model=CatBoostClassifier(**C['catboost']);model.fit(train[C['global_features'][name]],y,sample_weight=w)
    return model


def main():
    lock=freeze();panel=pd.read_parquet(CACHE/'panel.parquet');outputs={name:[] for name in ['M_R','L2']};audits=[]
    keep=['date','instrument','log_cap','vol63','market_beta63','industry_beta63','idiosyncratic_vol63','idiosyncratic_share63','industry_increment_r2_63',
        'board','industry_id','industry_sector','industry_stale','industry_published','industry_age_days','listing_date','delist_date','name','regime',
        'market_mom126','market_vol63','feature_cutoff','y_6','end_6']
    for quarter in pd.period_range('2019Q1','2026Q2',freq='Q'):
        tr=panel[(panel.date<quarter.start_time)&(panel.end_6<quarter.start_time)&panel.y_6.notna()]
        te=panel[panel.date.dt.to_period('Q')==quarter].copy().reset_index(drop=True)
        assert tr.end_6.max()<quarter.start_time
        for name in ['M_R','L2']:
            path=CACHE/f'global_{quarter}_{name}.parquet';receipt=AUDIT/f'global_{quarter}_{name}.json'
            if receipt.exists():
                r=json.loads(receipt.read_text());assert r['registration_sha256']==lock and digest(path)==r['sha256']
                outputs[name].append(pd.read_parquet(path));audits.append(r);continue
            z=te[keep].rename(columns={'y_6':'actual','end_6':'label_end'}).copy()
            if quarter.year<2021:
                model=fit_global(tr,name);z['G']=model.predict_proba(te[C['global_features'][name]])[:,1]
                model.save_model(str(CACHE/f'global_{quarter}_{name}.cbm'));fitted=True
            else:
                old=pd.read_parquet(EP28/f'outputs/local_cache/{quarter}_predictions.parquet')
                old=old[old.model.eq(name)].reset_index(drop=True)
                pd.testing.assert_frame_equal(old[['date','instrument']],te[['date','instrument']])
                np.testing.assert_allclose(old.actual,te.y_6,rtol=0,atol=0,equal_nan=True)
                z['G']=old.probability.to_numpy();fitted=False
            z['global_training_max_label']=tr.end_6.max();z['global_training_cutoff']=quarter.start_time
            z['foundation']=name;z['oos']=True;z.to_parquet(path,index=False);outputs[name].append(z)
            r=dict(quarter=str(quarter),foundation=name,registration_sha256=lock,sha256=digest(path),fitted=fitted,
                train_rows=len(tr),train_keys_sha256=keyhash(tr),test_keys_sha256=keyhash(te),max_train_label=str(tr.end_6.max()))
            write_json(receipt,r);audits.append(r)
        print('global',quarter,'new fits' if quarter.year<2021 else 'reused',flush=True)
    for name,rows in outputs.items():pd.concat(rows,ignore_index=True).to_parquet(CACHE/f'global_oos_{name}.parquet',index=False)
    assert sum(r['fitted'] for r in audits)==C['maximum_warmup_fits']
    write_json(AUDIT/'global_fit_audit.json',audits)


if __name__=='__main__':main()
