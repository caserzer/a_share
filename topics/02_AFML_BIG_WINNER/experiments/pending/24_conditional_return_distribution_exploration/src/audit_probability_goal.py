"""Audit the corrected scope; never equates successful code with trustworthy forecasts."""
import json
import hashlib
import numpy as np
import pandas as pd
from run_four_horizons import DEST, BIN_NAMES


def audit():
    evidence=[]
    for h in [1,3,6,12]:
        d=pd.read_parquet(DEST/f'predictions_{h}m.parquet')
        assert set(d.months)=={h}
        assert not d.duplicated(['date','instrument','model']).any()
        probs=d[[f'p_{n}' for n in BIN_NAMES]]
        assert np.isfinite(probs).all().all() and probs.ge(0).all().all() and probs.le(1+1e-12).all().all()
        np.testing.assert_allclose(probs.sum(axis=1),1,atol=1e-10)
        np.testing.assert_allclose(d[['p_up','p_down','p_zero']].sum(axis=1),1,atol=1e-10)
        expected=((d.p_up-(d.actual>0))**2).where(d.actual.notna())
        np.testing.assert_allclose(d.brier,expected,equal_nan=True)
        assert d.loc[d.actual.isna(),'multiclass_brier'].isna().all()
        reference=set(map(tuple,d[d.model=='expanding_empirical'][['date','instrument']].to_numpy()))
        for model,g in d.groupby('model'):
            assert set(map(tuple,g[['date','instrument']].to_numpy()))==reference,model
        fits=pd.read_csv(DEST/f'fit_audit_{h}m.csv')
        for _,r in fits.iterrows():assert pd.Timestamp(r.last_training_label)<pd.Period(r.quarter).start_time
        evidence.append(dict(months=h,models=d.model.nunique(),stock_dates=len(reference),
            mature_outcomes=int(d[d.model=='expanding_empirical'].actual.notna().sum())))
    fits=pd.read_csv(DEST/'direct_probability_fit_audit.csv')
    assert fits.iterations.max()<500,'direct probability optimizer did not converge'
    for _,r in fits.iterrows():assert pd.Timestamp(r.last_training_label)<pd.Period(r.quarter).start_time
    fits=pd.read_csv(DEST/'prequential_calibration_audit.csv')
    active=fits[fits.active]
    assert (pd.to_datetime(active.last_label)<pd.to_datetime(active.date)).all()
    assert active.historical_months.ge(12).all()
    summary=pd.read_csv(DEST/'summary.csv')
    assert set(summary.months)=={1,3,6,12}
    cal=pd.read_csv(DEST/'probability_calibration.csv')
    assert set(cal.event)=={'up',*BIN_NAMES}
    from run_four_horizons import OUT, EP
    from predict_from_snapshot import validate_snapshot
    snapshot=json.loads((OUT/'local_cache/current_snapshots/SH600000_2026-10-19/snapshot.json').read_text())
    validate_snapshot(snapshot)
    folder=OUT/'local_cache/current_snapshots/SH600000_2026-10-19'
    for receipt in snapshot['receipts']:
        assert hashlib.sha256((folder/(receipt['name']+'.json')).read_bytes()).hexdigest()==receipt['sha256']
    current=json.loads((OUT/'current/SH600000_2026-10-19.json').read_text())
    assert current['asof']=='2026-10-19' and current['features']==snapshot['features']
    assert current['input_sha256']==hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()
    assert [h['months'] for h in current['horizons']]==[1,3,6,12]
    for h in current['horizons']:
        atoms=np.asarray(h['distribution']['atoms']); weights=np.asarray(h['distribution']['weights'])
        np.testing.assert_allclose(weights.sum(),1)
        np.testing.assert_allclose(h['p_up'],weights[atoms>0].sum())
        np.testing.assert_allclose(h['p_down'],weights[atoms<0].sum())
        np.testing.assert_allclose(h['p_zero'],weights[atoms==0].sum())
        from run_four_horizons import BINS
        bins=np.searchsorted(BINS,atoms,side='right')
        for i,name in enumerate(BIN_NAMES):np.testing.assert_allclose(h['p_'+name],weights[bins==i].sum())
        assert h['credibility']['status']=='not_established_as_trustworthy'
        assert set(e['event'] for e in h['credibility']['events'])=={'up','down','zero',*BIN_NAMES}
        assert set(h['credibility']['baseline_comparison'])=={'brier','multiclass_brier','crps'}
        assert pd.Timestamp(h['training']['last_observed_label'])<pd.Timestamp(current['asof'])
    for report in ['probability_research_report.md','current_probability_example.md']:
        assert (EP/report).exists() and (EP/report).stat().st_size>1000
    result=dict(probability_pipeline_checks_passed=True,horizons=evidence,
        goal_complete=True, scientific_conclusion='Conditional direction probabilities not established as trustworthy; limited short-horizon amplitude improvements',
        requirements={
            'four_horizon_conditional_distributions':'predictions_1m/3m/6m/12m.parquet plus current/SH600000_2026-10-19.json',
            'direction_and_interval_probabilities':'reconstructed from stored current atoms; sums checked',
            'probability_calibration_and_tails':'probability_calibration.csv and eight dated event assessments per current horizon',
            'historical_baseline_comparison':'baseline_comparisons.csv; dated per-horizon current assessment',
            'known_information_and_data_gaps':'strict label maturity audits; exact-date current snapshot receipts; explicit stale training and scope limitations',
            'actual_returns_only_as_labels':'probability scripts evaluate Brier/CRPS/calibration, no portfolio objective',
            'credible_or_not_judgment':'explicit not-established verdict; insufficient evidence is not passed as trustworthy'},
        limitations=['Research implementation and evidence judgment completed, not proof of a useful predictive edge',
            'Training label panel ends 2026-05-29; current-date refitting is an exploratory extension',
            'No independent new holdout, no all-market coverage, no verified complete total-return labels'],
        outstanding_required_items=[],
        exclusions='No strategy return, NAV, holdings or portfolio profit used as acceptance evidence')
    (DEST/'probability_scope_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':audit()
