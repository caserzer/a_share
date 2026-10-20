"""Immutable registration and finite quarterly experiments, without score-based selection."""
import time
from core import *


def freeze():
    path=EP/'outputs/manifests/preregistration.json'
    if path.exists():
        old=json.loads(path.read_text())
        for name,sha in old['files'].items():assert digest(EP/name)==sha,name
        assert digest(PANEL)==old['panel_sha256']
    else:
        assert json.loads((EP/'outputs/audits/pit_truncation.json').read_text())['passed']
        assert json.loads((EP/'outputs/audits/unit_tests.json').read_text())['passed']
        files=[EP/'research_plan.md',EP/'configs/preregistered_experiments.yaml']
        files+=sorted((EP/'src').glob('*.py'))+sorted((EP/'tests').glob('*.py'))+sorted((EP/'literature').glob('*.md'))
        files+=sorted((EP/'outputs/audits').glob('*gate.json'))
        write_json(path,dict(created_utc=pd.Timestamp.now(tz='UTC').isoformat(),
            files={str(p.relative_to(EP)):digest(p) for p in files},panel_sha256=digest(PANEL),
            historical_exploration_only=True,no_scores_before_registration=True,
            maximum_new_classification_fits=C['maximum_classification_fits']))
    return digest(path)


def main():
    lock=freeze();panel=load_panel();audit=[]
    for quarter in pd.period_range('2021Q1','2026Q2',freq='Q'):
        receipt=EP/f'outputs/audits/fit_{quarter}.json'
        if receipt.exists():
            r=json.loads(receipt.read_text());assert r['registration_sha256']==lock and digest(EP/r['path'])==r['sha256']
            audit.append(r);continue
        start=time.monotonic();tr,te=split(panel,6,quarter)
        oldpath=EP27/f'outputs/local_cache/P2_6_{quarter}_predictions.parquet'
        old=pd.read_parquet(oldpath);old=old[old.model.isin(['B0','B1','M_R','M_RMI'])].copy()
        template=old[old.model.eq('M_R')].reset_index(drop=True)
        pd.testing.assert_frame_equal(template[['date','instrument']],te[['date','instrument']])
        np.testing.assert_allclose(template.actual,te.y_6,rtol=0,atol=0,equal_nan=True)
        rows=[old]
        for name in C['fitted_candidates']:
            model=fit_model(tr,name,6);z=template.copy();z['model']=name;z['probability']=predict(model,te,name)
            z['model_version']='EP28-fixed-v1';z['data_version']=digest(PANEL)
            z['delta_b1']=z.probability-z.b1_probability;rows.append(z)
            model.save_model(str(CACHE/f'{quarter}_{name}.cbm'))
        path=CACHE/f'{quarter}_predictions.parquet';pd.concat(rows,ignore_index=True).to_parquet(path,index=False)
        r=dict(quarter=str(quarter),train_rows=len(tr),train_months=tr.date.nunique(),test_rows=len(te),
            max_training_label=str(tr.end_6.max()),train_keys_sha256=keys_hash(tr),test_keys_sha256=keys_hash(te),
            path=str(path.relative_to(EP)),sha256=digest(path),source_baseline_sha256=digest(oldpath),
            registration_sha256=lock,models_fit=len(C['fitted_candidates']),seconds=time.monotonic()-start)
        write_json(receipt,r);audit.append(r);print(quarter,'fits',r['models_fit'],'seconds',round(r['seconds'],1),flush=True)
    pd.concat([pd.read_parquet(EP/r['path']) for r in audit],ignore_index=True).to_parquet(CACHE/'all_predictions.parquet',index=False)
    write_json(EP/'outputs/audits/fit_audit.json',audit)
    assert sum(r['models_fit'] for r in audit)==C['maximum_classification_fits']


if __name__=='__main__':main()
