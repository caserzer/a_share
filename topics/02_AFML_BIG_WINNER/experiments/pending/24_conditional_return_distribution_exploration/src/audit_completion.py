"""Verify episode execution and record scientific limitations separately."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
from run_price_pilot import OUT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    ep=OUT.parent
    report=OUT/'report'
    report.mkdir(exist_ok=True)
    checks={}
    original=Path('/home/xiaolv/.codex/attachments/5bdf581f-262c-4ec1-ae03-47a32f0f158c/Pasted text.txt')
    archived=ep/'notes/original_discussion_20261019.txt'
    checks['original_discussion_byte_identical']=original.exists() and original.read_bytes()==archived.read_bytes()
    directories=['r01_price_pilot','r02_calibration_probe','r03_information_probe','r04_peer_probe','r05_holdout',
                 'r06_portfolio_probe','r07_sensitivities','r08_excess_probe','r09_total_return_sensitivity']
    checks['nine_rounds_have_results']=all((OUT/d).is_dir() and any((OUT/d).glob('*.csv')) for d in directories)
    required=[ep/'research_plan.md',ep/'notes/data_gaps.md',ep/'notes/round_log.md',ep/'EP24_research_report.md',
              report/'historical_prediction_example.json',report/'allocation_comparison.png',report/'probability_drift.png']
    checks['required_deliverables_present']=all(p.is_file() and p.stat().st_size>0 for p in required)
    frozen=json.loads((OUT/'r05_holdout/run_spec.json').read_text())
    checks['holdout_spec_matches_retained_hash']=frozen['preregistered_spec_sha256']==sha(ep/'notes/r05_preregistered_validation.md')
    source=pd.read_parquet(OUT/'local_cache/monthly_panel.parquet')
    rebuilt=pd.read_parquet(OUT/'local_cache/reinvested_labels.parquet')
    checks['total_return_gap_audit_covers_all_source_targets']=len(rebuilt)==2*len(source) and not rebuilt.duplicated(['date','instrument','horizon']).any()
    vals=pd.read_csv(OUT/'valuation_fetch_progress.csv')
    fins=pd.read_csv(OUT/'financial_fetch_progress.csv')
    checks['public_data_coverage_measured']=len(vals)==1647 and len(fins)==1647
    holdings=pd.read_csv(OUT/'r06_portfolio_probe/summary.csv')
    checks['portfolio_all_planned_scenarios_present']=len(holdings)==20 and set(holdings.fee)=={.001,.003}
    checks['no_terminal_stale_mark_exposure']=bool((holdings.terminal_stale_value==0).all())
    # Reconcile reported scores to retained row predictions, separately for each target.
    for directory in ['r05_holdout','r08_excess_probe']:
        p=pd.read_parquet(OUT/directory/'predictions.parquet')
        observed=p[p.mature & p.actual.notna()]
        metrics=['crps','brier','below_q05','coverage90']
        actual=observed.groupby(['horizon','model','date'])[metrics].mean().groupby(['horizon','model']).mean().sort_index()
        stored=pd.read_csv(OUT/directory/'summary.csv').set_index(['horizon','model']).sort_index()
        checks[directory+'_scores_reconcile']=bool(np.allclose(actual[metrics],stored[metrics],equal_nan=True))
        checks[directory+'_six_models_both_horizons']=len(stored)==12
    test=subprocess.run([sys.executable,'-m','pytest','-q',str(ep/'tests')],capture_output=True,text=True)
    (report/'test_results.txt').write_text(test.stdout+test.stderr)
    checks['meaningful_tests_pass']=test.returncode==0
    links=[]
    import re
    for file in [ep/'README.md',ep/'EP24_research_report.md']:
        for target in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            if not target.startswith(('https://','http://','#')):
                links.append((file.parent/target).exists())
    checks['local_report_links_resolve']=all(links)
    checks['source_compiles']=subprocess.run([sys.executable,'-m','compileall','-q',str(ep/'src')],capture_output=True).returncode==0
    files=[p for p in ep.rglob('*') if p.is_file() and 'local_cache' not in p.parts and '__pycache__' not in p.parts
           and p.suffix in {'.py','.md','.json','.csv','.txt','.png','.parquet'} and p.name not in {'completion_audit.json','artifact_hashes.json'}]
    hashes={str(p.relative_to(ep)):sha(p) for p in sorted(files)}
    (report/'artifact_hashes.json').write_text(json.dumps(hashes,indent=2,ensure_ascii=False)+'\n')
    result={
        'execution_audit_passed':bool(all(checks.values())), 'checks':checks,
        'task_outcome':'Nine-round exploratory episode executed; stable probability and sizing advantage not established',
        'hypothesis_supported':False,
        'not_claimed':['complete unbiased A-share universe','original-vintage financial/valuation/industry PIT verification',
                       'all-corporate-action total-return database','exact broker execution','validated joint-tail portfolio optimizer',
                       'new prospective investment evidence'],
        'limitations_are_reported_research_outcomes_not_positive_validation':True,
        'input_hashes':{name:sha(OUT/'local_cache'/name) for name in ['monthly_panel.parquet','enriched_panel.parquet','reinvested_labels.parquet']},
        'versions':{name:importlib.metadata.version(name) for name in ['numpy','pandas','scikit-learn','catboost','pyarrow']},
        'test_output':'test_results.txt', 'artifact_hashes':'artifact_hashes.json',
    }
    (report/'completion_audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'execution_audit_passed':result['execution_audit_passed'],'checks':checks},indent=2))
    print(test.stdout)
    if not result['execution_audit_passed']:
        raise SystemExit(1)


if __name__=='__main__':
    run()
