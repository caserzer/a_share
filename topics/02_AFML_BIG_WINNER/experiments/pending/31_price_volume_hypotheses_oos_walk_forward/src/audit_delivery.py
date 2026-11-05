"""Requirement-by-requirement receipts, not a file-existence-only completion gate."""
from __future__ import annotations

import json
import subprocess

import numpy as np
import pandas as pd

from common import EP, OUT, REPO, cache, config, frozen, sha, utc_now, write_json
from ep30_adapter import EP30Adapter
from multiple_testing import bh


def main():
    checks=[]
    def check(name, success, evidence):
        checks.append(dict(check=name,status='PASS' if success else 'FAIL',evidence=evidence))
        if not success:raise AssertionError(name+': '+str(evidence))
    prereg=frozen()
    revision=json.loads((OUT/'manifests/revision_01.json').read_text())
    check('P0_original_and_R01_immutable',sha(EP/revision['file'])==revision['sha256'],revision)
    old=json.loads((cache()/'predecessor_hashes.json').read_text())
    changed=[name for name,digest in old.items() if not (REPO/name).is_file() or sha(REPO/name)!=digest]
    check('EP01_EP30_repository_bytes_unchanged',not changed,dict(files=len(old),changed=changed))
    EP30Adapter().verify_all()
    check('EP30_all_release_files_unchanged',True,json.loads((OUT/'audits/ep30_release_verification.json').read_text()))
    data_root=cache()/'data'
    manifest=json.loads((data_root/'COMPLETE.json').read_text())
    bad=[name for name,digest in manifest['files'].items() if sha(data_root/name)!=digest]
    check('all_feature_label_market_partitions_unchanged',not bad,dict(partitions=len(manifest['files']),changed=bad))
    full=pd.read_csv(OUT/'audits/monthly_reconciliation_full.csv')
    check('all_four_monthly_labels_rederived',int(full.rows.sum())==2103048 and int(full.mismatches.sum())==0,full.to_dict('records'))
    replay=json.loads((OUT/'audits/feature_replay.json').read_text())
    check('full_feature_reconstruction_after_chain_guard',replay['status']=='PASS' and replay['rows']>1000000,replay)
    alias=json.loads((OUT/'audits/alias_deduplication.json').read_text())
    check('all_policy_aliases_equal_used_once',alias['status']=='PASS' and alias['independent_policy_samples']==1,alias)
    model_code=json.loads((OUT/'manifests/model_code_v2.json').read_text())
    check('fitting_code_frozen',all(sha(EP/'src'/n)==h for n,h in model_code['files'].items()),model_code)
    scored=json.loads((OUT/'audits/scoring_start.json').read_text())
    check('all_prediction_indexes_precede_scoring',all(sha(OUT/n)==h for n,h in scored['prediction_indexes'].items()),scored)
    optimization=json.loads((OUT/'audits/scoring_optimization_replay.json').read_text())
    first_score=pd.Timestamp(optimization['first_outer_score_started_at'])
    check('scoring_optimization_changes_no_results_or_predictions',optimization['status']=='PASS' and optimization['byte_equal'] and optimization['frozen_prediction_indexes_identical'],optimization)
    auxiliary_payloads=0
    for name in ['big_winner','H02_turnover_sensitivity','H12_independence','auxiliary_baselines','constant_baseline']:
        index=json.loads((OUT/f'manifests/{name}.json').read_text())
        if pd.Timestamp(index['frozen_at'])>=first_score:raise AssertionError('auxiliary predictions frozen after first scoring')
        for r in index['folds']:
            digest=r.get('sha256',r.get('predictions_sha256'))
            if sha(r['prediction_path'])!=digest:raise AssertionError('auxiliary prediction payload changed')
            if 'model_path' in r and sha(r['model_path'])!=r['model_sha256']:raise AssertionError('auxiliary model changed')
            cutoff=r.get('fit_cutoff',r.get('cutoff'))
            maturity=r.get('max_train_mature_at',r.get('max_mature_at',r.get('max_maturity')))
            if cutoff and maturity and pd.Timestamp(maturity)>=pd.Timestamp(cutoff):raise AssertionError('auxiliary maturity violation')
            auxiliary_payloads+=1
    check('all_required_baseline_sensitivity_payloads_frozen',True,dict(payloads=auxiliary_payloads))
    total_folds,total_predictions,minimum_months=0,0,1000.
    public_index=[]
    expected={str(q) for q in pd.period_range('2021Q1','2026Q4',freq='Q')}
    for h in config()['primary']:
        if h=='H09':continue
        index=json.loads((OUT/f'manifests/{h}_folds.json').read_text())
        check(h+'_prediction_freeze_before_scoring',pd.Timestamp(index['prediction_freeze_completed_at'])<first_score,index['prediction_freeze_completed_at'])
        for scheme in ['expanding','rolling36']:
            ready={r['fold'] for r in index['folds'] if r['scheme']==scheme}
            blocked={r['fold'] for r in index['blocked'] if r['scheme']==scheme}
            check(h+'_'+scheme+'_all_quarters_accounted',ready|blocked==expected and not ready&blocked,dict(ready=sorted(ready),blocked=sorted(blocked)))
            keys=[]
            for r in [r for r in index['folds'] if r['scheme']==scheme]:
                if sha(r['predictions_path'])!=r['predictions_sha256'] or sha(r['model_path'])!=r['model_sha256']:raise AssertionError('changed frozen fold')
                cutoff=pd.Timestamp(r['fit_cutoff'])
                if pd.Timestamp(r['max_train_mature_at'])>=cutoff:raise AssertionError('outer maturity leak')
                duration=(pd.Timestamp(r['train_end'])-pd.Timestamp(r['train_start'])).days/365.25*12
                minimum_months=min(minimum_months,duration)
                if pd.Timestamp(r['train_start'])+pd.DateOffset(months=24)>pd.Timestamp(r['train_end']):raise AssertionError('outer training shorter than 24 calendar months')
                for inner in r['inner_timeline']:
                    if not inner['ready'] or pd.Timestamp(inner['max_maturity'])>=pd.Timestamp(inner['start']):raise AssertionError('inner purge/history leak')
                    if pd.Timestamp(inner['train_min'])+pd.DateOffset(months=24)>pd.Timestamp(inner['train_max']):raise AssertionError('inner training shorter than 24 calendar months')
                p=pd.read_parquet(r['predictions_path'])
                if {'value','y','mature_at','exit_date','future_variance'}&set(p):raise AssertionError('outcome in frozen predictions')
                if not p.date.dt.to_period('Q').astype(str).eq(r['fold']).all():raise AssertionError('wrong test fold')
                if not p.date.ge(cutoff).all():raise AssertionError('test before fit cutoff')
                if r['model_replay']!='PASS':raise AssertionError('model replay not validated')
                keys.append(p[['date','security_id']])
                total_folds+=1;total_predictions+=len(p)
                public_index.append({k:r[k] for k in ['hypothesis','scheme','fold','predictions_path','predictions_sha256','model_path','model_sha256','test_rows']})
            if pd.concat(keys).duplicated(['date','security_id']).any():raise AssertionError('cross-fold duplicate episode')
    check('all_nested_timelines_and_outer_prediction_payloads',True,dict(folds=total_folds,predictions=total_predictions,minimum_outer_train_months=minimum_months))
    full_replay=json.loads((OUT/'audits/all_prediction_columns_replay.json').read_text())
    check('every_admitted_model_all_output_columns_replay',full_replay['status']=='PASS' and full_replay['folds']==total_folds and full_replay['rows']==total_predictions and full_replay['all_columns_exact'],full_replay)
    pd.DataFrame(public_index).to_csv(OUT/'fold_predictions/index.csv',index=False)
    pooled=pd.read_csv(OUT/'metrics/pooled_oos_metrics.csv')
    for scheme in ['expanding','rolling36']:
        group=pooled.loc[pooled.scheme.eq(scheme)]
        check('BH_seven_primary_endpoints_'+scheme,len(group)==7 and np.allclose(group.q_bh,bh(group.p_one_sided),equal_nan=True),group[['hypothesis','p_one_sided','q_bh']].to_dict('records'))
    left=pooled.loc[pooled.scheme.eq('expanding')].set_index('hypothesis')
    right=pooled.loc[pooled.scheme.eq('rolling36')].set_index('hypothesis')
    check('same_coverage_for_expanding_rolling_comparison',left.rows.equals(right.rows) and left.total_rows.equals(right.total_rows),dict(expanding=left.rows.to_dict(),rolling=right.rows.to_dict()))
    verdict=pd.read_csv(OUT/'metrics/hypothesis_verdicts.csv')
    check('eight_independent_verdicts_H09_blocked',len(verdict)==8 and verdict.loc[verdict.hypothesis.eq('H09'),'verdict'].iloc[0]=='BLOCKED_DATA',verdict[['hypothesis','verdict']].to_dict('records'))
    forward=json.loads((OUT/'forward_shadow/status.json').read_text())
    check('forward_not_fabricated',forward['actual_forward_predictions']==0 and forward['independently_matured_forward_labels']==0 and forward['confirmation']=='FORWARD_PENDING',forward['reason'])
    check('forward_final_source_freeze_current',all(sha(EP/p)==h for p,h in forward['frozen_sources'].items()),'all source/config/test hashes match forward status')
    replay_data=json.loads((OUT/'audits/independent_data_replay.json').read_text())
    check('independent_full_data_replay',replay_data['status']=='PASS' and replay_data['parquet_files']==len(manifest['files']),replay_data)
    tests=json.loads((OUT/'audits/tests.json').read_text())
    check('adversarial_test_suite',tests['returncode']==0 and tests['passed']>=35,tests)
    required=['README.md','research_plan.md','reports/data_quality.md','reports/hypothesis_scorecard.md','reports/oos_walk_forward.md','reports/big_winner_incremental_value.md','reports/final_conclusion.md']
    check('required_reports_present',all((EP/p).is_file() and (EP/p).stat().st_size>100 for p in required),required)
    changed_scope=subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=normal'],cwd=REPO).decode().splitlines()
    check('exact_EP31_worktree_scope',all('31_price_volume_hypotheses_oos_walk_forward/' in line for line in changed_scope),changed_scope)
    write_json(OUT/'audits/delivery_check.json',dict(status='PASS',checked_at=utc_now(),checks=checks,
               frozen_model_folds=total_folds,outer_prediction_rows=total_predictions,
               task_complete_with_disclosed_data_and_forward_branches=True,
               strict_PIT_industry_alpha='BLOCKED_DATA',H09='BLOCKED_DATA',forward='FORWARD_PENDING',trading='TRADING_NOT_AUTHORIZED'))
    print('delivery PASS',total_folds,'folds',total_predictions,'predictions')


if __name__=='__main__':
    (OUT/'fold_predictions').mkdir(parents=True,exist_ok=True)
    main()
