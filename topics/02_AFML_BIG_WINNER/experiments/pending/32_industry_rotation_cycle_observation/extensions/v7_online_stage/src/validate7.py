import json,re,sys
from pathlib import Path
import numpy as np
import pandas as pd
from context7 import ROOT,V5,V6,CACHE,OLD,OUT,STATE,sha,js


def run():
    checks=[]
    def check(name,ok):
        assert bool(ok),name
        checks.append(name)
    previous=json.loads((OUT/'predecessors.json').read_text())
    check('all predecessor bytes unchanged',all(sha(p)==h for p,h in previous.items()))
    sources=json.loads((V5/'outputs/daily_input_audit.json').read_text())
    check('all original stock and membership inputs unchanged',all(sha(p)==h for p,h in sources['reads'].items()))
    sr=json.loads((OUT/'state_receipt.json').read_text())
    check('all consumed derived input hashes unchanged',all(sha(p)==h for p,h in sr['inputs'].items()))
    check('daily NAV is the previously audited version',sha(OLD/'daily_industries.parquet')==sources['daily_sha256'])
    check('base features are previously audited version',sha(OLD/'features.parquet')==json.loads((V5/'outputs/feature_audit.json').read_text())['features_sha256'])
    check('original stage B labels unchanged',sha(OLD/'stage_b_labels.parquet')==json.loads((V5/'outputs/stage_b/label_audit.json').read_text())['labels_sha256'])
    check('state bytes unchanged',sha(sr['path'])==sr['sha256'])
    check('online state code unchanged',sha(ROOT/'src/state7.py')==sr['code_sha256'])
    s=pd.read_parquet(sr['path'])
    check('unique observation and threshold state',not s.duplicated(['row_id','threshold']).any())
    check('no future outcomes in state',not any(c in s for c in ['y','label_available_at','phase_id','end_confirmed_at']))
    check('candidate low never in future',s.candidate_low_date.le(s.date).all())
    check('start confirmation never in future',s.start_confirmed_at.isna().all() or s.loc[s.start_confirmed_at.notna(),'start_confirmed_at'].le(s.loc[s.start_confirmed_at.notna(),'date']).all())
    check('eligibility uses calendar boundary',s.loc[s.state_eligible.eq(1),'candidate_low_date'].gt(s.loc[s.state_eligible.eq(1),'date']-pd.DateOffset(months=3)).all())
    f=pd.read_parquet(OLD/'features.parquet');f=f[f.features_ready]
    check('all original ready observations retained at three thresholds',len(s)==len(f)*3 and set(s.row_id)==set(f.row_id))
    labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    labeled=labels.merge(s[['row_id','threshold','state_eligible']],on=['row_id','threshold'],validate='many_to_one')
    check('no known positive excluded by causal gate',not (labeled.y.eq(1)&labeled.state_eligible.eq(0)).any())
    frozen=json.loads((OUT/'frozen_candidates.json').read_text())
    check('experiment code frozen before predictions',sha(ROOT/'src/experiment7.py')==frozen['code_sha256'])
    check('research plan unchanged',sha(ROOT/'research_plan.md')==frozen['plan_sha256'])
    check('RD-Agent hyperparameters unchanged',frozen['spec']==json.loads((V5/'outputs/stage_b/frozen_selection.json').read_text())['winner']['spec'])
    rec=json.loads((OUT/'prediction_receipt.json').read_text())
    check('all eighteen prediction tasks complete',len(rec['tasks'])==18)
    modelkeys=set(frozen['models']);count=0
    for artifact in rec['tasks']:
        prefix=artifact['task']+' '
        check(prefix+'saved predictions unchanged',sha(artifact['path'])==artifact['sha256'])
        check(prefix+'same frozen candidate definition',artifact['frozen_sha256']==sha(OUT/'frozen_candidates.json'))
        folds=pd.DataFrame(artifact['folds'])
        check(prefix+'all training labels mature before quarter',pd.to_datetime(folds.latest_training_label).lt(pd.to_datetime(folds.quarter)).all())
        p=pd.read_parquet(artifact['path']);count+=len(p)
        check(prefix+'no outcomes in predictions','y' not in p and 'label_available_at' not in p)
        check(prefix+'unique prediction keys',not p.duplicated(['row_id','model']).any())
        check(prefix+'same complete observations across seven models',set(p.model)==modelkeys and p.groupby('row_id').model.nunique().eq(7).all())
        check(prefix+'finite probabilities',p.prob.between(0,1).all())
        wide=p.pivot(index='row_id',columns='model',values='prob')
        elig=p.drop_duplicates('row_id').set_index('row_id').state_eligible.reindex(wide.index).eq(1)
        check(prefix+'gate changes only excluded probabilities',np.allclose(wide.rd_gate,np.where(elig,wide.rd_selected,0)))
        check(prefix+'state and conditional zero only on ineligible subset',wide.loc[~elig,['rd_gate','rd_state','rd_conditional']].eq(0).all().all())
        selected=p.groupby(['date','level','model']).alert.sum()
        expected=np.ceil(p.groupby(['date','level','model']).size()*.1)
        check(prefix+'top decile chosen on full prediction population',np.array_equal(selected,expected))
    coverage=pd.read_csv(OUT/'coverage.csv');metrics=pd.read_csv(OUT/'metrics.csv')
    check('unknown outcomes explicitly retained',coverage.unknown.sum()>0 and coverage.observations.eq(coverage.known+coverage.unknown).all())
    check('all scored rows match known counts',metrics.n.sum()==coverage.known.sum())
    compare=coverage.groupby(['cohort','frequency','threshold','benchmark','level','year'])
    check('same known cohort across models',compare.known.nunique().eq(1).all() and compare.positives.nunique().eq(1).all())
    tests=pd.read_csv(OUT/'primary_tests.csv')
    sys.path.insert(0,str(V6/'src'))
    from statistics6 import bh
    check('three prespecified tests with BH correction',len(tests)==3 and np.allclose(tests.q_bh,bh(tests.p_one_sided)))
    verdict=json.loads((OUT/'verdict.json').read_text())
    check('strict PIT and independent evidence gaps retained',verdict['strict_PIT']=='BLOCKED_DATA' and verdict['independent_confirmation'] is False)
    check('all candidate frequency threshold benchmark gates represented',len(verdict['task_gates'])==54)
    generated_links=[]
    for path in ROOT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if '://' in target or target.startswith('#'):continue
            resolved=(path.parent/target.split('#')[0]).resolve()
            if resolved in [(OUT/'validation.json').resolve(),(OUT/'manifest.json').resolve()]:
                generated_links.append(resolved);continue
            check('link '+str(path.relative_to(ROOT))+' '+target,(path.parent/target.split('#')[0]).exists())
    deliver=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.parts for x in ['__pycache__','.pytest_cache'])]
    check('private panels and credentials excluded',not any(p.suffix in ['.parquet','.pkl','.env'] for p in deliver))
    check('credential markers absent',not any(marker in p.read_text(errors='ignore') for p in deliver if p.suffix in ['.json','.csv','.md'] for marker in ['PRIVATE KEY-----','sk-or-v1-','Bearer sk-']))
    js(OUT/'validation.json',dict(status='PASS',checks_count=len(checks),checks=checks,prediction_rows=count,
        original_positive_rows_checked=int(labeled.y.sum()),causal_gate_excludes_no_known_positive=True,strict_PIT='BLOCKED_DATA'))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.name!='manifest.json' and not any(x in p.parts for x in ['__pycache__','.pytest_cache'])]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files),bytes=sum(p['bytes'] for p in files)))
    assert all(path.exists() for path in generated_links)
    print('V7 validation PASS',len(checks),'checks;',len(files),'files;',count,'predictions',flush=True)


if __name__=='__main__':run()
