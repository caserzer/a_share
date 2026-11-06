"""Audit frozen inputs, temporal admission, matched comparisons and delivery."""
import json,re
from pathlib import Path
import numpy as np
import pandas as pd
from context6 import ROOT,V5,CACHE,OLD,OUT,GROUPS,sha,js,unchanged
from statistics6 import bh


def run():
    checks=[]
    def check(name,ok):
        assert bool(ok),name
        checks.append(name)
    check('all predecessor research bytes unchanged',unchanged())
    a=json.loads((OUT/'feature_audit.json').read_text())
    check('all consumed stock partitions and membership hashes unchanged',all(sha(p)==h for p,h in a['reads'].items()))
    f=pd.read_parquet(CACHE/'mechanism_features.parquet')
    y=pd.read_parquet(CACHE/'forward_peer_outcomes.parquet')
    check('feature hash',sha(CACHE/'mechanism_features.parquet')==a['features_sha256'])
    check('future outcome hash',sha(CACHE/'forward_peer_outcomes.parquet')==a['forward_outcomes_sha256'])
    check('no future outcomes in feature frame',not any('future' in c or c in ['y','label_available_at'] for c in f))
    check('unique feature keys',not f.duplicated(['row_id','benchmark']).any())
    check('exactly two benchmark copies',f.groupby('row_id').size().eq(2).all())
    check('unique separate future outcomes',not y.row_id.duplicated().any())
    check('no feature row lost in future table',set(y.row_id)==set(f.row_id))
    ranked=f[f.rank_complete]
    check('ranking precedes observation',ranked.rank_asof.lt(ranked.date).all())
    check('three distinct leaders and at least three peers',ranked.leader_codes.map(lambda s:len(set(s.split(';')))==3).all() and ranked.peer_count.ge(3).all())
    check('common cohort has complete ranking',f.loc[f.common_complete,'rank_complete'].all())
    check('common features are finite',np.isfinite(f.loc[f.common_complete,sum(GROUPS.values(),[])].to_numpy()).all())
    z=y.merge(f[['row_id','date']].drop_duplicates(),on='row_id',validate='one_to_one')
    available=z[['leader_future21','peer_future21']].notna().any(axis=1)
    check('future outcomes mature after origins',z.loc[available,'outcome_available_at'].gt(z.loc[available,'date']).all())
    check('future outcome cutoff',z.loc[available,'outcome_available_at'].max()<=pd.Timestamp('2026-10-21'))
    check('right censored future outcomes remain unknown',z.loc[z.outcome_available_at.isna(),['leader_future21','peer_future21']].isna().all().all())
    frozen=json.loads((OUT/'frozen_models.json').read_text())
    prior=json.loads((V5/'outputs/stage_b/frozen_selection.json').read_text())['winner']['spec']
    check('frozen RD-Agent model unchanged',frozen['spec']==prior)
    check('frozen evaluation code unchanged',sha(ROOT/'src/evaluate6.py')==frozen['evaluation_code_sha256'])
    check('frozen source features unchanged',frozen['source_feature_sha256']==a['features_sha256'])
    protocol=json.loads((OUT/'protocol.json').read_text())
    check('hypothesis protocol unchanged',sha(ROOT/'research_plan.md')==frozen['plan_sha256']==protocol['plan_sha256'])
    receipt=json.loads((OUT/'prediction_receipt.json').read_text())
    check('predictions frozen before scoring',sha(receipt['path'])==receipt['sha256'])
    check('frozen model receipt matches',sha(OUT/'frozen_models.json')==receipt['frozen_models_sha256'])
    folds=pd.DataFrame(receipt['folds'])
    check('training label maturity strictly before each fold',pd.to_datetime(folds.latest_training_label).lt(pd.to_datetime(folds.quarter)).all())
    check('all eighteen tasks evaluated',len(folds[['frequency','threshold','benchmark']].drop_duplicates())==18)
    p=pd.read_parquet(receipt['path'])
    keys=['row_id','threshold','benchmark','cohort']
    check('prediction keys unique',not p.duplicated(keys+['model']).any())
    check('predictions contain no outcomes','y' not in p and 'label_available_at' not in p)
    check('valid probabilities',p.prob.between(0,1).all())
    for cohort,n in [('common',7),('h3_full',2)]:
        part=p[p.cohort.eq(cohort)]
        check(cohort+' identical rows for every model',part.groupby(keys).size().eq(n).all())
        check(cohort+' identical prior for every model',part.groupby(keys).prior.nunique().eq(1).all())
    labels=pd.read_parquet(OLD/'stage_b_labels.parquet')
    scored=p.merge(labels[['row_id','threshold','benchmark','y']],on=['row_id','threshold','benchmark'],validate='many_to_one')
    coverage=pd.read_csv(OUT/'outcome_coverage.csv')
    check('all predictions counted',coverage.predictions.sum()==len(p))
    check('unknown labels not scored as negatives',coverage.known.sum()==scored.y.notna().sum() and coverage.unknown.sum()==scored.y.isna().sum() and coverage.unknown.sum()>0)
    metrics=pd.read_csv(OUT/'ablation_metrics.csv')
    check('known count matches scored metrics',metrics.n.sum()==coverage.known.sum())
    check('all common models evaluated per task',len(metrics)==324)
    annual=pd.read_csv(OUT/'annual_metrics.csv')
    recent=annual[annual.year.eq(2026)&annual.cohort.eq('common')&annual.model.eq('base')]
    check('2026 maturity limitation disclosed',recent.positives.sum()==20 and recent.n.sum()==70980)
    regress=pd.read_csv(OUT/'lead_lag_daily_regressions.csv')
    grouped=regress.groupby(['frequency','benchmark','level','date'])
    check('all three mechanism directions on same dates',grouped.kind.nunique().eq(3).all())
    check('mechanism directions have identical sample count',grouped.n.nunique().eq(1).all())
    check('minimum cross section size',regress.n.ge(10).all())
    tests=pd.read_csv(OUT/'primary_tests.csv')
    check('six prespecified tests',len(tests)==6 and tests.test.nunique()==6)
    check('BH correction reproduced',np.allclose(tests.q_bh,bh(tests.p_one_sided)))
    check('report null findings match primary results',not tests.positive_supported.any())
    finance=json.loads((OUT/'fundamental_audit.json').read_text())
    check('finance source unchanged',sha(finance['source'])==finance['sha256'])
    check('strict PIT and fundamentals remain blocked',finance['status']==a['strict_PIT']=='BLOCKED_DATA')
    for path in ROOT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if '://' in target or target.startswith('#'):continue
            check('local link '+str(path.relative_to(ROOT))+' '+target,(path.parent/target.split('#')[0]).exists())
    forbidden=['PRIVATE KEY-----','sk-or-v1-','Bearer sk-']
    deliver=[q for q in ROOT.rglob('*') if q.is_file() and not any(x in q.parts for x in ['__pycache__','.pytest_cache'])]
    check('no private cache or credential files delivered',not any(q.suffix in ['.parquet','.pkl','.env'] for q in deliver))
    check('credential markers absent',not any(marker in q.read_text(errors='ignore') for q in deliver if q.suffix in ['.md','.json','.csv'] for marker in forbidden))
    js(OUT/'validation.json',dict(status='PASS',checks=checks,checks_count=len(checks),
        consumed_files_verified=len(a['reads']),prediction_rows=len(p),known_prediction_rows=int(scored.y.notna().sum()),
        unknown_prediction_rows=int(scored.y.isna().sum()),strict_PIT='BLOCKED_DATA'))
    files=[dict(path=str(q.relative_to(ROOT)),sha256=sha(q),bytes=q.stat().st_size) for q in sorted(ROOT.rglob('*'))
        if q.is_file() and q.name!='manifest.json' and not any(x in q.parts for x in ['__pycache__','.pytest_cache'])]
    js(OUT/'manifest.json',dict(files=files,file_count=len(files),bytes=sum(q['bytes'] for q in files)))
    print(f'V6 PASS: {len(checks)} checks; {len(files)} manifest files; {len(p)} predictions',flush=True)


if __name__=='__main__':run()
