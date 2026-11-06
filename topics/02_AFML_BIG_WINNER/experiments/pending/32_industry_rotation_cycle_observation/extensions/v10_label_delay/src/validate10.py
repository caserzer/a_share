import json,re,sys
import numpy as np
import pandas as pd
from context10 import ROOT,V5,V6,V7,V8,V9,CACHE,OUT,FEATURES,KEY,sha,js


def run():
    checks=[]
    def check(name,value):
        assert bool(value),name
        checks.append(name)
    previous=json.loads((OUT/'predecessors.json').read_text())
    check('all previous versions unchanged',all(sha(p)==h for p,h in previous.items()))
    frozen=json.loads((OUT/'frozen_candidates.json').read_text())
    check('experiment code frozen',sha(ROOT/'src/experiment10.py')==frozen['code_sha256'])
    check('plan frozen',sha(ROOT/'research_plan.md')==frozen['plan_sha256'])
    check('only predefined causal features',frozen['features']==FEATURES and not any('future' in x for x in FEATURES))
    rec=json.loads((OUT/'prediction_receipt.json').read_text())
    old=json.loads((V9/'outputs/prediction_receipt.json').read_text())
    source={r['task']:r for r in old['tasks']}
    check('all eighteen tasks',len(rec['tasks'])==18 and set(source)=={r['task'] for r in rec['tasks']})
    check('model specifications frozen',rec['frozen_sha256']==sha(OUT/'frozen_candidates.json'))
    check('frozen scores',sha(CACHE/'delay_scores.parquet')==rec['scores_sha256'])
    folds=pd.DataFrame(rec['folds'])
    check('all model training labels mature at fit time',pd.to_datetime(folds.latest_training_label).lt(pd.to_datetime(folds.quarter)).all())
    for name,g in folds.groupby('model'):
        lag=24 if name=='lag24_tree' else 12
        check(name+' required origin delay',pd.to_datetime(g.latest_training_origin).lt(pd.to_datetime(g.quarter)-pd.DateOffset(months=lag)).all())
        check(name+' historical delay reference',pd.to_datetime(g.latest_reference_origin).lt(pd.to_datetime(g.quarter)-pd.DateOffset(months=24)).all())
        check(name+' bounded inverse probability',g.max_delay_weight.between(1,5).all())
    score=pd.read_parquet(CACHE/'delay_scores.parquet')
    check('no future outcomes in shared scores','y' not in score and 'label_available_at' not in score)
    check('unique shared forecast identities',not score.duplicated(KEY+['date','threshold','benchmark']).any())
    rows=0
    for r in rec['tasks']:
        name=r['task'];p=pd.read_parquet(r['path']);rows+=len(p)
        check(name+' saved prediction hash',sha(r['path'])==r['sha256'])
        base=pd.read_parquet(source[name]['path'])
        check(name+' thirteen original methods byte-equivalent values',base.equals(p.head(len(base))))
        check(name+' same observation population',p.groupby('row_id').model.nunique().eq(16).all() and not p.duplicated(['row_id','model']).any())
        w=p.pivot(index='row_id',columns='model',values='prob')
        eligible=p.drop_duplicates('row_id').set_index('row_id').state_eligible.reindex(w.index).eq(1)
        check(name+' structural gate preserved',w.loc[~eligible,['lag12_tree','lag24_tree','delay_weighted_tree']].eq(0).all().all())
        check(name+' valid probabilities',p.prob.between(0,1).all())
    m=pd.read_csv(OUT/'metrics.csv');before=pd.read_csv(V9/'outputs/metrics.csv')
    sort=['cohort','frequency','threshold','benchmark','level','model']
    after=m[m.model.isin(before.model.unique())].sort_values(sort).reset_index(drop=True)
    before=before.sort_values(sort).reset_index(drop=True)
    check('all old evaluation metrics reproduced',after.equals(before))
    c=pd.read_csv(OUT/'coverage.csv')
    check('unknown labels retained',c.unknown.sum()>0 and c.observations.eq(c.known+c.unknown).all())
    check('same known observations across methods',c.groupby(['cohort','frequency','threshold','benchmark','level','year']).known.nunique().eq(1).all())
    check('all scored observations accounted for',m.n.sum()==c.known.sum())
    tests=pd.read_csv(OUT/'primary_tests.csv')
    history=np.r_[pd.read_csv(V6/'outputs/primary_tests.csv').p_one_sided,pd.read_csv(V7/'outputs/primary_tests.csv').p_one_sided,pd.read_csv(V8/'outputs/primary_tests.csv').p_one_sided,pd.read_csv(V9/'outputs/primary_tests.csv').p_one_sided]
    sys.path.insert(0,str(V6/'src'));from statistics6 import bh
    check('cumulative eighteen-test correction',tests.family_size.eq(18).all() and np.allclose(tests.q_bh,bh(np.r_[history,tests.p_one_sided])[-3:]))
    verdict=json.loads((OUT/'verdict.json').read_text())
    check('all candidate gates present',len(verdict['task_gates'])==54)
    check('PIT and independence gaps preserved',verdict['strict_PIT']=='BLOCKED_DATA' and verdict['independent_confirmation'] is False)
    generated=[]
    for p in ROOT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://' in target or target.startswith('#'):continue
            link=(p.parent/target.split('#')[0]).resolve()
            if link in [(OUT/'validation.json').resolve(),(OUT/'manifest.json').resolve()]:generated.append(link);continue
            check('link '+str(p.relative_to(ROOT))+' '+target,link.exists())
    deliver=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.parts for x in ['__pycache__','.pytest_cache'])]
    check('private data not delivered',not any(p.suffix in ['.parquet','.pkl','.env'] for p in deliver))
    check('credential markers absent',not any(marker in p.read_text(errors='ignore') for p in deliver if p.suffix in ['.json','.md','.csv'] for marker in ['sk-or-v1-','PRIVATE KEY-----','Bearer sk-']))
    js(OUT/'validation.json',dict(status='PASS',checks_count=len(checks),checks=checks,prediction_rows=rows,strict_PIT='BLOCKED_DATA'))
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*'))
        if p.is_file() and p.name!='manifest.json' and not any(x in p.parts for x in ['__pycache__','.pytest_cache'])]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files),bytes=sum(r['bytes'] for r in files)))
    assert all(p.exists() for p in generated)
    print('V10 validation PASS',len(checks),'checks;',len(files),'files',flush=True)


if __name__=='__main__':run()
