"""Full artifact provenance, 528 serialized-model replays and registered metric reconstruction."""
from core import *
from conditional import conditional_auc,error_decomposition,make_pairs
from calibrate import mature_calibration_rows,fit_offset,apply_offset


def main():
    reg=json.loads((OUT/'preregistration.json').read_text());assert all(digest(EP/k)==v for k,v in reg['files'].items());assert digest(PANEL)==reg['panel_sha256']
    assert digest(OUT/'p0_audit.json')==reg['p0_sha256'] and digest(OUT/'source_receipts.csv')==reg['source_receipts_sha256']
    source=pd.read_csv(OUT/'source_receipts.csv')
    for row in source.itertuples():assert digest(TOPIC/row.path)==row.sha256,row.path
    prior=json.loads((OUT/'prior_preservation.json').read_text());assert all(digest(EP.parent/k)==v for k,v in prior.items())
    panel=load_panel();fit=json.loads((OUT/'fit_audit.json').read_text());p1=json.loads((OUT/'p1_fit_audit.json').read_text());replayed=0
    assert len(fit)==len(p1)==88
    for record in fit:
        h=record['horizon'];quarter=pd.Period(record['quarter']);train,test=split(panel,h,quarter)
        assert keys_hash(train)==record['train_keys_sha256'] and keys_hash(test)==record['test_keys_sha256']
        assert digest(EP/record['prediction_path'])==record['prediction_sha256']
        frame=pd.read_parquet(EP/record['prediction_path'])
        for name in C['candidates']:
            model=CatBoostClassifier();model.load_model(str(CACHE/f'{h}_{quarter}_{name}.cbm'));p=predict(model,test,name)
            old=frame[frame.model.eq(name)].reset_index(drop=True);pd.testing.assert_frame_equal(old[['date','instrument']],test[['date','instrument']]);np.testing.assert_array_equal(p,old.probability);replayed+=1
            assert train.industry_id.nunique()<=255
        prior25=pd.read_parquet(EP25/f'outputs/local_cache/{h}_{quarter}_predictions.parquet');frozen=prior25[prior25.model.eq('B1')].reset_index(drop=True)
        new=frame[frame.model.eq('B1')].reset_index(drop=True);np.testing.assert_array_equal(new.probability,frozen.p_tail)
        if h==6:
            prior26=pd.read_parquet(EP26/f'outputs/local_cache/{quarter}_predictions.parquet');old=prior26[prior26.model.eq('M_R')].reset_index(drop=True)
            np.testing.assert_allclose(frame[frame.model.eq('M_R')].probability.to_numpy(),old.p_loss20.to_numpy(),rtol=1e-14,atol=1e-14)
    full=pd.read_parquet(CACHE/'all_predictions.parquet');monthly=pd.read_csv(OUT/'monthly_scores.csv',parse_dates=['date']);checked=0
    for (h,name,date),g in full.groupby(['horizon','model','date']):
        flags={str(int(f*100)):warning(g.probability,g.instrument,f) for f in [.1,.2]};r=metrics(g.probability,g.actual,flags)
        if r is None:continue
        row=monthly[monthly.horizon.eq(h)&monthly.model.eq(name)&monthly.date.eq(date)].iloc[0]
        for metric,value in r.items():np.testing.assert_allclose(value,row[metric],rtol=1e-12,atol=1e-12,equal_nan=True)
        if h==6:
            for label,group in [('industry','industry_id'),('matched_cell','risk_cell')]:
                c,_=conditional_auc(risk_cells(g),group=group);np.testing.assert_allclose(c['conditional_auc'],row[label+'_auc'],rtol=1e-12,atol=1e-12,equal_nan=True)
            d=error_decomposition(g);assert np.isclose(d['total'],r['brier'],atol=1e-12)
        checked+=1
    raw=full[full.horizon.eq(6)];calibrated=pd.read_parquet(CACHE/'calibrated_predictions.parquet');calfits=json.loads((OUT/'calibration_fits.json').read_text());cal_count=refits=0
    for record in calfits:
        name=record['base_model'];date=pd.Timestamp(record['date']);g=raw[raw.model.eq(name)];history=mature_calibration_rows(g,date);test=g[g.date.eq(date)]
        assert keys_hash(history)==record['train_keys_sha256'];assert len(history)==record['training_rows']
        if len(history):assert history.label_end.max()<date
        fitvalue=record['fit']
        if fitvalue is not None:
            refit=fit_offset(history.probability,labels(history.actual),history[C['calibration']['state_features']],history.date,state=record['method']=='state')
            np.testing.assert_allclose(refit['coefficients'],fitvalue['coefficients'],atol=1e-7,rtol=1e-7);refits+=1
        expected=apply_offset(test.probability.to_numpy(),test[C['calibration']['state_features']],fitvalue) if record['reason']=='fitted' else test.probability.to_numpy()
        actual=calibrated[calibrated.model.eq(name+'__'+record['method'])&calibrated.date.eq(date)]
        np.testing.assert_allclose(expected,actual.probability.to_numpy(),atol=1e-14,rtol=1e-14);cal_count+=1
    pairrows=pd.read_csv(OUT/'matched_pairs.csv',parse_dates=['date']);base=raw[raw.model.eq('M_RMI')].rename(columns={'probability':'p_base'});add=raw[raw.model.eq('M_RMIVF')][['date','instrument','probability']].rename(columns={'probability':'p_full'});joined=base.merge(add,on=['date','instrument'],validate='one_to_one')
    for date,g in joined.groupby('date'):
        selected=make_pairs(g);opposite=g.copy();opposite.actual=-opposite.actual*100;again=make_pairs(opposite);pd.testing.assert_frame_equal(selected,again)
        recorded=pairrows[pairrows.date.eq(date)]
        assert set(zip(selected.high,selected.low))==set(zip(recorded.high,recorded.low))
    lists=pd.read_parquet(CACHE/'portfolio_selections.parquet');counts=lists[lists.selected].groupby(['date','risk_cell','strategy']).size().unstack('strategy');assert counts.S0.equals(counts.S1) and counts.S0.equals(counts.S2)
    targets=pd.read_csv(OUT/'portfolio_industry_targets.csv').pivot_table(index=['date','industry_id'],columns='strategy',values='target_weight',fill_value=0);np.testing.assert_allclose(targets.S0,targets.S1);np.testing.assert_allclose(targets.S0,targets.S2)
    daily=pd.read_csv(OUT/'portfolio_daily.csv')
    for _,g in daily.groupby(['strategy','cost_bps']):
        np.testing.assert_allclose((1+g.daily_return).cumprod(),g.nav,atol=1e-12,rtol=1e-12);assert g.cash.ge(-1e-12).all() and g.equity_fraction.between(-1e-12,1+1e-12).all() and g.fees.ge(0).all()
    assert json.loads((OUT/'controls.json').read_text())['all_passed']
    assert not json.loads((OUT/'conclusion_status.json').read_text())['independent_confirmation']
    required=['research_plan.md','data_integrity_audit.md','market_risk_decomposition.md','industry_risk_decomposition.md','idiosyncratic_risk_report.md','valuation_financial_ablation.md','conditional_calibration.md','matched_risk_group_test.md','portfolio_tail_risk_test.md','statistical_validation.md','final_conclusion.md','README.md','validation_protocol.md','requirements.txt']
    assert all((EP/name).is_file() for name in required)
    write_json(OUT/'validation.json',dict(status='PASS',registered_sources_unchanged=True,input_receipts_checked=len(source),prior_episode_files_unchanged=len(prior),serialized_models_exact_replays=replayed,
        prediction_rows=len(full),monthly_metric_rows_rebuilt=checked,conditional_AUC_and_error_accounting_rebuilt=True,inherited_B1_and_EP26_MR_matched=True,
        calibration_prediction_groups_replayed=cal_count,calibration_parameter_fits_rebuilt=refits,calibration_prediction_tolerance=1e-14,strict_calibration_label_maturity=True,
        matching_invariant_to_future_labels=True,industry_target_weights_exactly_matched=True,risk_cell_counts_exactly_matched=True,cash_NAV_fee_invariants_passed=True,
        all_controls_passed=True,independent_confirmation_claimed=False,pytest_receipt='outputs/pytest.txt; actual separate run'))
    print(json.loads((OUT/'validation.json').read_text()),flush=True)

if __name__=='__main__':main()
