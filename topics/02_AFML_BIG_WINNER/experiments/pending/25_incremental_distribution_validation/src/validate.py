"""Independent archive validation and serialized-model replay, without refitting."""
import json
from catboost import CatBoostRegressor
import numpy as np
import pandas as pd
from core import *


def main():
    lock=json.loads((OUT/'preregistration.json').read_text())
    assert all(digest(EP/k)==v for k,v in lock['files'].items())
    before=json.loads((OUT/'ep24_preservation_before.json').read_text())
    assert all(digest(OLD/k)==v for k,v in before.items())
    receipts=json.loads((OUT/'fit_audit.json').read_text())
    expected={(h,str(q)) for h in CONFIG['horizons'] for q in pd.period_range('2021Q1','2026Q2',freq='Q')}
    assert {(r['horizon'],r['quarter']) for r in receipts}==expected
    panel=load_panel();checked=0;model_replays=0
    for r in receipts:
        for key in ['predictions','atoms']:assert digest(EP/r[key]['path'])==r[key]['sha256']
        frame=pd.read_parquet(EP/r['predictions']['path'])
        assert set(frame.model)==set(['B0','B1']+list(CONFIG['candidates']))
        assert pd.Timestamp(r['max_training_label'])<pd.Period(r['quarter']).start_time
        with np.load(EP/r['atoms']['path']) as atoms:
            for name,g in frame.groupby('model'):
                g=g.reset_index(drop=True);a=atoms[name]
                assert a.shape==(len(g),CONFIG['atoms']) and np.isfinite(a).all()
                assert (np.diff(a,axis=1)>=0).all() and (a>=-1).all()
                recomputed=score(a,g.actual)
                for c in ['crps','brier','tail_brier','p_up','p_tail','pit','cover05','cover10','cover50','cover90','cover95']:
                    np.testing.assert_allclose(recomputed[c],g[c],rtol=1e-12,atol=1e-12,equal_nan=True)
                checked+=len(g)
            # Replay final quarter of every horizon from actual serialized tree model.
            if r['quarter']=='2026Q2':
                _,test=train_test(panel,pd.Period(r['quarter']).start_time,r['horizon'],pd.Period(r['quarter']))
                for name in CONFIG['candidates']:
                    model=CatBoostRegressor();model.load_model(str(CACHE/f"{r['horizon']}_{r['quarter']}_{name}.cbm"))
                    predicted,_=predict_atoms(model,test,name)
                    np.testing.assert_array_equal(predicted,atoms[name]);model_replays+=1
    controls=json.loads((OUT/'controls.json').read_text());assert controls['all_passed']
    conclusion=json.loads((OUT/'conclusion_status.json').read_text());assert not conclusion['independent_confirmation']
    files=['research_plan.md','data_audit.md','baseline_comparison.md','factor_ablation.md','calibration_report.md','final_conclusion.md','README.md','config.json','requirements.txt']
    assert all((EP/p).is_file() for p in files)
    write_json(OUT/'validation.json',dict(status='PASS',all_prediction_rows_recomputed=checked,serialized_model_exact_replays=model_replays,
        expected_horizon_quarters=len(expected),registered_source_hashes_unchanged=True,ep24_manifest_files_unchanged=len(before),
        all_atoms_finite_monotone_and_simple_return_bounded=True,controls_passed=True,independent_confirmation_claimed=False,
        pytest_receipt='outputs/pytest.txt; run separately, not inferred from this validation'))
    print(json.dumps(json.loads((OUT/'validation.json').read_text()),indent=2))

if __name__=='__main__':main()
