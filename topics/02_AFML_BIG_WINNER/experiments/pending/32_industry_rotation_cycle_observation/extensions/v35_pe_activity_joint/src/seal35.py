"""Reconcile legacy predictions/economics and preserve all previous artifacts."""
import ast
from common35 import *

def run():
    checks=json.loads((OUT/'feature_validation.json').read_text())['checks']
    def ck(name,ok):
        assert bool(ok),name;checks.append(name)
    receipt=json.loads((OUT/'prediction_receipt.json').read_text())
    frozen=json.loads((OUT/'model_freeze.json').read_text())
    ck('four Q1 models exactly replayed',set(receipt['q1_exact_replays'])==set(['baseline']+list(ACTIVITY)))
    ck('model plan unchanged',sha(ROOT/'research_plan.md')==frozen['plan_sha256'])
    ck('training code unchanged',sha(ROOT/'src/train35.py')==frozen['code_sha256'])
    ck('PE features unchanged since training',sha(CACHE/'features.parquet')==frozen['features_sha256'])
    ck('scores hash',sha(CACHE/'scores.parquet')==receipt['scores_sha256'])
    ck('labels unchanged',sha(OLD/'stage_b_labels.parquet')==frozen['labels_sha256'])
    for fold in receipt['folds']:
        if fold['test']:ck('mature training '+fold['quarter'],pd.Timestamp(fold['latest_training_label'])<pd.Timestamp(fold['quarter']))
    ck('original forward outcomes unchanged',sha(ECON/'outcomes.parquet')==json.loads((EXT/'v31_all_signal_economics/outputs/input_receipt.json').read_text())['outcomes_sha256'])
    economics=pd.read_csv(OUT/'economics_primary.csv')
    old=pd.read_csv(EXT/'v34_multiscale_expansion/outputs/economics_primary.csv')
    control=['accepted','baseline','momentum']+list(ACTIVITY)
    got=economics[economics.method.isin(control)].merge(old,on=['frequency','method','unit','months'],validate='one_to_one',suffixes=('_new','_old'))
    ck('all economic control rows retained',len(got)==len(economics[economics.method.isin(control)]))
    for c in ['signals','known_returns','mean_return','mean_excess','median_excess','mean_max_drawdown']:
        ck('unchanged V34 economics '+c,np.allclose(got[c+'_new'],got[c+'_old'],equal_nan=True,rtol=1e-12,atol=1e-12))
    classification=pd.read_csv(OUT/'classification_all_tasks.csv')
    old=pd.read_csv(EXT/'v34_multiscale_expansion/outputs/classification_all_tasks.csv')
    got=classification[classification.method.isin(control)].merge(old,on=['frequency','threshold','benchmark','level','method'],suffixes=('_new','_old'),validate='one_to_one')
    ck('all legacy classification tasks retained',len(got)==36*len(control))
    for c in ['precision','point_recall','cycle_recall','median_delay']:
        ck('unchanged V34 classification '+c,np.allclose(got[c+'_new'],got[c+'_old'],equal_nan=True))
    intervals=pd.read_csv(OUT/'paired_intervals.csv')
    ck('nine primary comparisons',len(intervals.query("scope=='full' and unit=='six_month_launches'"))==9)
    calendar=pd.DatetimeIndex(pd.read_parquet(OLD/'CSI_ALL.parquet').index).sort_values()
    for frequency in ['W','BW','M']:
        f=pd.read_parquet(CACHE/'evaluation_frames'/f'{frequency}_0.15_CSI_ALL.parquet')
        for family in ACTIVITY:
            for name in [family,'joint_'+family,'missing_'+family]:
                ck('same alarm budget '+frequency+' '+name,f.groupby(['date','level'])['selected_'+name].sum().equals(f.groupby(['date','level']).selected_baseline.sum()))
                for cutoff in ['2021-12-31','2022-12-31','2023-12-31']:
                    s=f[f.level.eq('L3')&f['selected_'+name]&f.date.le(cutoff)]
                    ck('causal episode accounting '+frequency+' '+name+' '+cutoff,np.array_equal(episode_starts(s,calendar),s['first_'+name]))
            masks=[f['selected_complete_'+family+'_'+n] for n in ['baseline',family,'pe','joint_'+family,'missing_'+family]]
            ck('common eligibility '+frequency+' '+family,all(not (mask&~f[family+'_joint_complete']).any() for mask in masks))
            ck('common matched budgets '+frequency+' '+family,all(mask.groupby([f.date,f.level]).sum().equals(masks[0].groupby([f.date,f.level]).sum()) for mask in masks))
        # Recompute from the whole eligible pool: changing cell cannot reset lockout.
        eligible=f.level.eq('L3')&f.state_eligible.eq(1)&f.market_up
        ck('four cells share one causal launch clock '+frequency,np.array_equal(episode_starts(f[eligible],calendar),f.loc[eligible,'mechanism_first']))
        ck('four-cell unknown explicitly retained '+frequency,f.expansion_cell.eq('UNKNOWN').any())
    hashes=json.loads((OUT/'feature_receipt.json').read_text())['source_hashes']
    ck('all source bytes unchanged',all(sha(p)==h for p,h in hashes.items()))
    prior=json.loads((OUT/'predecessors.json').read_text())
    ck('all old research including D2 V6 unchanged',all(sha(p)==h for p,h in prior.items()))
    for p in (ROOT/'src').glob('*.py'):ast.parse(p.read_text());checks.append('syntax '+p.name)
    checkpoints=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted((CACHE/'quarters').glob('*'))]
    js(OUT/'checkpoint_manifest.json',dict(files=checkpoints))
    js(OUT/'validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),strict_PIT='BLOCKED_DATA',baseline_reconciliation=True))
    print('PASS',len(checks),'checks;',len(checkpoints),'private checkpoints',flush=True)

if __name__=='__main__':run()
