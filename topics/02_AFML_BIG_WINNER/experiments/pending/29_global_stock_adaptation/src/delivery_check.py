"""Check the completed finite research, without requiring a positive effect."""
from common import *
from global_model import freeze


def main():
    freeze()
    support=json.loads((MANIFEST/'supporting_diagnostics_registration.json').read_text())
    correction=json.loads((MANIFEST/'supporting_diagnostics_correction.json').read_text())
    for path,h in support['files'].items():
        if path in correction['files']:
            r=correction['files'][path]
            assert r['before']==h and digest(EP/r['preserved_before_path'])==h
            h=r['after']
        assert digest(EP/path)==h
    required=['GOAL.md','README.md','research_plan.md','validation_protocol.md','requirements.txt',
        'configs/preregistration.yaml','configs/target_cohort.yaml']
    required+=['reports/'+n+'.md' for n in ['data_audit','peer_similarity','shrinkage_validation','single_stock_case',
        'cross_stock_validation','calibration_report','statistical_validation','final_conclusion','result_tables','design_clarifications']]
    required+=['outputs/metrics/'+n+'.csv' for n in ['summary','monthly_scores','paired_intervals','phase_intervals','company_scores',
        'company_intervals','conditional_summary','reliability','leave_out','missing_bounds','corrections','auxiliary_intervals',
        'fallback_accounting','issuer_adaptation_coverage','synthetic_uncertainty','strict_local_monthly','strict_local_intervals',
        'peer_pair_ranking','peer_pair_intervals']]
    for path in required:assert (EP/path).is_file() and (EP/path).stat().st_size>0,path
    assert json.loads((AUDIT/'validation.json').read_text())['passed']
    assert json.loads((AUDIT/'unit_tests_final.json').read_text())['passed']
    assert json.loads((AUDIT/'synthetic_controls.json').read_text())['all_passed']
    assert not json.loads((AUDIT/'identity_control.json').read_text())['suspicious_individual_gain']
    panel=pd.read_parquet(CACHE/'panel.parquet')
    assert (panel.listing_date<=panel.date).all()
    assert not (panel.delist_date.notna()&(panel.date>panel.delist_date)).any()
    summary=pd.read_csv(OUT/'summary.csv')
    for foundation in ['M_R','L2']:
        for population in ['D0','cohort40']:
            g=summary[(summary.foundation==foundation)&(summary.population==population)]
            assert set(C['formal_models']).issubset(g.model)
            if population=='D0':
                assert g.months.eq(59).all() and g.stock_months.eq(27230).all() and g.events.eq(4581).all()
        f=pd.read_csv(EP/f'outputs/predictions/single_stock_{foundation}.csv')
        assert len(f)==64 and f.actual.notna().sum()==59
        assert all(c in f for c in ['past_G_brier','past_GPI_brier','calibration_history_months','issuer_max_mature_label',
            'GPI_lower','GPI_upper','nonoverlap_events','individual_reason'])
        cohort=pd.read_csv(EP/f'outputs/predictions/cohort40_{foundation}.csv')
        assert len(cohort)==901 and cohort.actual.notna().sum()==866 and cohort.instrument.nunique()==40
        assert 'past_GPI_brier' in cohort and 'issuer_max_mature_label' in cohort
    old=json.loads((MANIFEST/'prior_preservation.json').read_text())
    for path,h in old.items():assert digest(EP.parent/path)==h,path
    conclusion=json.loads((AUDIT/'conclusion_status.json').read_text())
    assert conclusion['independent_confirmation'] is False and conclusion['model_search_stopped'] is True
    r=dict(passed=True,required_files_verified=len(required),old_files_unchanged=len(old),
        listing_and_recorded_delisting_chronology_checked=True,
        same_row_formal_comparisons_complete=True,controls_complete=True,cohort_and_single_path_complete=True,
        forward_validation_not_yet_observed=True,scientific_success_not_a_completion_requirement=True)
    write_json(AUDIT/'delivery_check.json',r);print(json.dumps(r,indent=2))


if __name__=='__main__':main()
