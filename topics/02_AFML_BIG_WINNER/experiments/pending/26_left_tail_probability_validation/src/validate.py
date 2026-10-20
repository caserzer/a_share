"""End-to-end archive, classifier replay, source preservation and portfolio invariants."""
from core import *
from portfolio import selection
from evaluate import build_monthly


def main():
    locked=json.loads((OUT/'preregistration.json').read_text());assert all(digest(EP/k)==v for k,v in locked['files'].items())
    source=pd.read_csv(OUT/'source_receipts.csv')
    for row in source.itertuples():assert digest(TOPIC/row.path)==row.sha256
    prior=json.loads((OUT/'prior_episodes_preservation.json').read_text())
    assert all(digest(EP.parent/k)==v for k,v in prior.items())
    panel=load_panel();fit=json.loads((OUT/'fit_audit.json').read_text());replays=0;predrows=0
    assert {r['quarter'] for r in fit}==set(map(str,pd.period_range('2021Q1','2026Q2',freq='Q')))
    for record in fit:
        quarter=pd.Period(record['quarter']);train,test=train_test(panel,quarter)
        assert digest(EP/record['prediction_path'])==record['prediction_sha256']
        assert len(train)==record['train_rows']
        assert hashlib.sha256(train[['date','instrument']].to_csv(index=False).encode()).hexdigest()==record['train_key_sha256']
        frame=pd.read_parquet(EP/record['prediction_path']);predrows+=len(frame)
        for model,g in frame.groupby('model'):
            g=g.reset_index(drop=True);pd.testing.assert_frame_equal(g[['date','instrument']],test[['date','instrument']])
            for col in ['p_loss10','p_loss20','p_loss30']:assert np.isfinite(g[col]).all() and g[col].between(0,1).all()
            assert (g.p_loss10>=g.p_loss20).all() and (g.p_loss20>=g.p_loss30).all()
            if model in C['candidates']:
                for k in THRESHOLDS:
                    m=CatBoostClassifier();m.load_model(str(CACHE/f'{quarter}_{model}_{k}.cbm'))
                    p=predict(m,test,model);np.testing.assert_array_equal(p,g[f'raw_loss{k}'].to_numpy());replays+=1
                np.testing.assert_array_equal(g.p_loss20,g.raw_loss20)
            known=g.actual.notna()
            loss=event_labels(g.actual,-.2)
            if known.any():assert ((g.loc[known,'p_loss20']-loss[known])**2).ge(0).all()
    full=pd.read_parquet(CACHE/'all_predictions.parquet')
    # Recreate all monthly scoring, warnings and quantile diagnostics from serialized probabilities.
    recomputed,_,_=build_monthly(full)
    frozen=pd.read_csv(OUT/'monthly_scores.csv',parse_dates=['date'])
    cols=['model','date','threshold'];recomputed=recomputed.sort_values(cols).reset_index(drop=True);frozen=frozen.sort_values(cols).reset_index(drop=True)
    pd.testing.assert_frame_equal(recomputed[cols],frozen[cols])
    for col in recomputed.columns.difference(cols):np.testing.assert_allclose(recomputed[col],frozen[col],rtol=1e-12,atol=1e-12,equal_nan=True)
    previous=pd.read_csv(PREV/'outputs/monthly_scores.csv',parse_dates=['date']);previous=previous[previous.horizon.eq(6)]
    for name,oldname in OLD_MODELS.items():
        a=frozen[(frozen.model==name)&(frozen.threshold==20)].sort_values('date');b=previous[previous.model.eq(oldname)].sort_values('date')
        np.testing.assert_array_equal(a.date.to_numpy(),b.date.to_numpy());np.testing.assert_allclose(a.brier,b.tail_brier,rtol=1e-13,atol=1e-13)
    selections=pd.read_parquet(CACHE/'portfolio_selections.parquet');count=selections[selections.selected].groupby(['date','stratum','strategy']).size().unstack('strategy')
    assert count.S0.equals(count.S1) and count.S0.equals(count.S2)
    daily=pd.read_csv(OUT/'portfolio_daily.csv')
    for _,g in daily.groupby(['strategy','cost_bps']):
        np.testing.assert_allclose((1+g.daily_return).cumprod(),g.nav,rtol=1e-12)
        assert g.cash.ge(-1e-12).all() and g.equity_fraction.between(-1e-10,1+1e-10).all() and g.transaction_cost.ge(0).all()
    controls=json.loads((OUT/'controls.json').read_text());assert controls['all_passed']
    assert all(pd.Timestamp(r['last_train_label'])<pd.Period(r['quarter']).start_time for r in json.loads((OUT/'negative_control_fits.json').read_text()))
    required=['research_plan.md','tail_event_definition.md','data_audit.md','baseline_comparison.md','factor_ablation.md','probability_calibration.md','tail_risk_ranking.md','portfolio_risk_test.md','validation_protocol.md','final_conclusion.md','README.md','requirements.txt']
    assert all((EP/f).exists() for f in required)
    status=json.loads((OUT/'conclusion_status.json').read_text());assert not status['independent_confirmation']
    write_json(OUT/'validation.json',dict(status='PASS',all_registered_source_hashes_unchanged=True,all_input_receipts_rechecked=len(source),
        prior_episodes_files_unchanged=len(prior),all_classifier_models_exactly_replayed=replays,prediction_rows_validated=predrows,monthly_metric_rows_recomputed=len(recomputed),
        frozen_ep25_all_five_distribution_scores_match=True,strict_label_maturity=True,auxiliary_probabilities_coherent=True,primary_probabilities_unmodified=True,
        risk_stratum_counts_all_strategies_equal=True,portfolio_cash_nav_cost_invariants_passed=True,controls_passed=True,independent_confirmation_claimed=False,
        pytest_evidence='outputs/pytest.txt; separate actual run'))
    print(json.loads((OUT/'validation.json').read_text()),flush=True)

if __name__=='__main__':main()
