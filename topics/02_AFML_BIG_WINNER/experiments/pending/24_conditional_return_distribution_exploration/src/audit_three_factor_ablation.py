"""R15 completion audit: factor timing, matched population, 2^3 contrasts and scores."""
import hashlib
import json
import numpy as np
import pandas as pd
from build_three_factor_panel import DEST,PANEL,EP
from run_three_factor_ablation import VARIANTS
from run_four_horizons import BIN_NAMES,BINS


def audit():
    panel=pd.read_parquet(PANEL);p=panel[panel.common_eligible]
    spec=json.loads((DEST/'run_spec.json').read_text())
    assert spec['panel_sha256']==hashlib.sha256(PANEL.read_bytes()).hexdigest()
    assert spec['plan_sha256']==hashlib.sha256((EP/'notes/r15_three_factor_ablation.md').read_bytes()).hexdigest()
    assert (p.financial_available_date<p.date).all() and (p.yield_observation_date<p.date).all()
    assert (p.prior_pe_last_date<p.date).all() and p.prior_pe_count.ge(252).all()
    assert p.current_pe.gt(0).all() and p.forward_return_12m.gt(-1).all()
    assert p.growth_assumption.between(-.3,.3).all()
    np.testing.assert_allclose(p.forward_return_12m,(1+p.growth_assumption)*p.prior_pe_median/p.current_pe-1)
    fits=pd.read_csv(DEST/'fit_audit.csv');assert len(fits)==64*3
    for _,f in fits.iterrows():
        date=pd.Timestamp(f.date);h=f.months
        train=p[(p[f'end_{h}']<date)&p[f'y_{h}'].notna()&(p.date<date)]
        test=p[p.date==date]
        assert len(train)==f.training_rows and len(test)==f.prediction_rows
        assert train[f'end_{h}'].max()==pd.Timestamp(f.last_training_label)
        assert hashlib.sha256(train[['date','instrument']].sort_values(['date','instrument']).to_csv(index=False).encode()).hexdigest()==f.train_key_sha256
        assert hashlib.sha256(test[['date','instrument']].to_csv(index=False).encode()).hexdigest()==f.test_key_sha256
    coverage=[]
    for h in [1,3,6]:
        d=pd.read_parquet(DEST/f'predictions_{h}m.parquet')
        assert set(d.model)=={'historical',*VARIANTS}
        assert not d.duplicated(['date','instrument','model']).any()
        expected=p[p.date>='2021-01-01'][['date','instrument',f'y_{h}']].rename(columns={f'y_{h}':'source_actual'})
        for name,g in d.groupby('model'):
            j=g.merge(expected,on=['date','instrument'],validate='one_to_one')
            assert len(j)==len(expected)==len(g)
            np.testing.assert_allclose(j.actual,j.source_actual,equal_nan=True)
        np.testing.assert_allclose(d[[f'p_{n}' for n in BIN_NAMES]].sum(axis=1),1)
        np.testing.assert_allclose(d[['p_up','p_down','p_zero']].sum(axis=1),1)
        valid=d.actual.notna();y=d.loc[valid,'actual'].to_numpy()
        np.testing.assert_allclose(d.loc[valid,'brier'],(d.loc[valid,'p_up']-(y>0))**2)
        probs=d.loc[valid,[f'p_{n}' for n in BIN_NAMES]].to_numpy()
        expected_brier=((probs-np.eye(5)[np.searchsorted(BINS,y,side='right')])**2).sum(axis=1)
        np.testing.assert_allclose(d.loc[valid,'multiclass_brier'],expected_brier)
        assert d.loc[~valid,'brier'].isna().all()
        coverage.append(dict(months=h,models=d.model.nunique(),predicted_per_model=len(expected),observed_per_model=int(expected.source_actual.notna().sum())))
    effects=pd.read_csv(DEST/'factor_effects.csv')
    assert len(effects)==3*3*3*12*2
    assert set(effects.factor)=={'C','P','F'} and set(effects.block_months)=={6,12}
    for _,r in effects[['factor','without','with_model']].drop_duplicates().iterrows():
        assert set(VARIANTS[r.with_model])-set(VARIANTS[r.without])=={r.factor}
    cal=pd.read_csv(DEST/'probability_calibration.csv');assert set(cal.event)=={'up','down',*BIN_NAMES}
    assert set(cal.model)=={'historical',*VARIANTS}
    for name in ['summary.csv','phase_scores.csv','annual_scores.csv','baseline_comparisons.csv','feature_coverage.csv']:
        assert (DEST/name).exists()
    assert (EP/'three_factor_ablation_report.md').exists()
    extension=pd.read_parquet(DEST/'newly_matured_sensitivity/scored_predictions.parquet')
    assert set(extension.model)=={'historical',*VARIANTS}
    assert extension.groupby('months').date.nunique().to_dict()=={1:1,3:2,6:4}
    for h in [1,3,6]:
        original=pd.read_parquet(DEST/f'predictions_{h}m.parquet')
        j=extension[extension.months==h].merge(original,on=['date','instrument','months','model'],suffixes=('_new','_original'),validate='one_to_one')
        assert len(j)==len(extension[extension.months==h]) and j.actual_original.isna().all()
        for col in ['p_up','p_down','p_zero',*[f'p_{n}' for n in BIN_NAMES]]:
            np.testing.assert_array_equal(j[col+'_new'],j[col+'_original'])
        ref=set(map(tuple,j[j.model=='B'][['date','instrument']].to_numpy()))
        for _,g in j.groupby('model'):
            assert set(map(tuple,g[['date','instrument']].to_numpy()))==ref
    result=dict(status='complete',scope='1/3/6 month monthly walk-forward, credit/PE/forward-anchor full factorial ablation',
        coverage=coverage,feature_timing_checks_passed=True,identical_samples_across_variants=True,
        groups=['credit_spread_and_change','historical_positive_PE_percentile','scenario_forward_return_anchor'],
        ablation_edges=12,bootstrap_blocks=[6,12],periods=['all','2021_2023','2024_plus'],
        limitation='Forward return is a capped historical-profit-growth plus median-PE scenario, not point-in-time analyst consensus; reports may be stale',
        no_portfolio_metrics=True,new_label_sensitivity='posthoc, identical probability forecasts, only 1/2/4 origin months',report='three_factor_ablation_report.md')
    (DEST/'completion_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':audit()
