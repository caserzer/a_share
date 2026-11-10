"""Reconcile frozen baselines, input identities and final research artifacts."""
import ast
import re
from common34 import *


def run():
    checks=json.loads((OUT/'feature_validation.json').read_text())['checks']
    def ck(name,ok):
        assert bool(ok),name
        checks.append(name)
    receipt=json.loads((OUT/'prediction_receipt.json').read_text())
    ck('original base model exactly replayed',receipt['baseline_q1_exact_replay']=='PASS')
    ck('three-family score hash',sha(CACHE/'scores.parquet')==receipt['scores_sha256'])
    model_freeze=json.loads((OUT/'model_freeze.json').read_text())
    ck('training code unchanged',sha(ROOT/'src/train34.py')==model_freeze['code_sha256'])
    ck('model plan unchanged',sha(ROOT/'research_plan.md')==model_freeze['plan_sha256'])
    ck('new features unchanged since training',sha(CACHE/'expansion_features.parquet')==model_freeze['new_features_sha256'])
    for fold in receipt['folds']:
        if fold['test']:
            ck('mature training labels '+fold['quarter'],pd.Timestamp(fold['latest_training_label'])<pd.Timestamp(fold['quarter']))
    original=json.loads((EXT/'v27_regime_threshold_review/outputs/frozen_policy.json').read_text())
    ck('original labels unchanged',sha(OLD/'stage_b_labels.parquet')==original['labels_sha256'])
    ck('original phases unchanged',sha(OLD/'daily_phases.parquet')==original['phases_sha256'])
    v31refs=json.loads((EXT/'v31_all_signal_economics/outputs/input_receipt.json').read_text())
    ck('fixed forward outcomes unchanged',sha(ECON/'outcomes.parquet')==v31refs['outcomes_sha256'])
    economics=pd.read_csv(OUT/'economics_primary.csv')
    v31=pd.read_csv(EXT/'v31_all_signal_economics/outputs/primary_metrics.csv')
    controls=economics[economics.method.isin(['accepted','baseline','momentum'])].copy()
    controls['method']=controls.method.replace(dict(baseline='diffusion_matched',momentum='momentum_matched'))
    joined=controls.merge(v31,on=['frequency','method','unit','months'],validate='one_to_one',suffixes=('_new','_old'))
    ck('all frozen baseline rows matched',len(joined)==len(controls))
    for c in ['signals','known_returns','mean_return','mean_excess','median_excess','mean_max_drawdown']:
        ck('V31 baseline economics '+c,np.allclose(joined[c+'_new'],joined[c+'_old'],equal_nan=True,rtol=1e-12,atol=1e-12))
    classifications=pd.read_csv(OUT/'classification_all_tasks.csv')
    v28=pd.read_csv(EXT/'v28_aggregate_acceptance/outputs/independent_metrics.csv').query("model=='accepted'")
    got=classifications.query("method=='accepted'").merge(v28,on=['frequency','threshold','benchmark','level'],suffixes=('_new','_old'),validate='one_to_one')
    ck('all 36 original classification tasks retained',len(got)==36)
    for new,old in [('precision','precision'),('cycle_recall','event_recall'),('point_recall','point_recall')]:
        ck('V28 classification reproduced '+new,np.allclose(got[new+'_new'] if new==old else got[new],got[old+'_old'] if new==old else got[old],equal_nan=True))
    ck('nine primary economic comparisons',len(pd.read_csv(OUT/'paired_intervals.csv').query("unit=='six_month_launches' and scope=='full'"))==9)
    for frequency in ['W','BW','M']:
        f=pd.read_parquet(CACHE/'evaluation_frames'/f'{frequency}_0.15_CSI_ALL.parquet')
        for family in GROUPS:
            ck('matched K '+frequency+' '+family,f.groupby(['date','level'])['selected_'+family].sum().equals(f.groupby(['date','level']).selected_baseline.sum()))
            for cutoff in ['2021-12-31','2022-12-31','2023-12-31']:
                s=f[f['selected_'+family]&f.date.le(cutoff)]
                calendar=pd.DatetimeIndex(pd.read_parquet(OLD/'CSI_ALL.parquet').index).sort_values()
                ck('launch prefix '+frequency+' '+family+' '+cutoff,np.array_equal(episode_starts(s,calendar),s['first_'+family]))
    source=json.loads((OUT/'feature_receipt.json').read_text())
    ck('source bytes unchanged after analysis',all(sha(p)==h for p,h in source['source_hashes'].items()))
    previous=json.loads((OUT/'predecessors.json').read_text())
    ck('all previous experiments and overview unchanged',all(sha(p)==h for p,h in previous.items()))
    for p in (ROOT/'src').glob('*.py'):
        ast.parse(p.read_text());checks.append('Python syntax '+p.name)
    for p in ROOT.rglob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://' not in link and not link.startswith('#'):ck('report link '+link,(p.parent/link).exists())
    private=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted((CACHE/'quarters').glob('*'))]
    js(OUT/'checkpoint_manifest.json',dict(files=private,file_count=len(private)))
    js(OUT/'code_receipt.json',dict(files={str(p):sha(p) for p in sorted((ROOT/'src').glob('*.py'))}))
    js(OUT/'validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),
        baseline_reconciliation=True,source_preservation=True,PE_main_test='BLOCKED_DATA'))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files)))
    print('PASS',len(checks),'checks;',len(files),'frozen files;',len(private),'private checkpoints')


if __name__=='__main__':run()
