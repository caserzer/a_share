"""Validate R12 chronology, prediction reproducibility and metric reconciliation."""
import json
import joblib
import numpy as np
import pandas as pd
from probability_pool import EP,OUT,SOURCE,ARMS,KEY,data,sha,calibrated

def main():
    seal=json.loads((OUT/'prediction_seal.json').read_text())
    for f,h in seal['inputs'].items():assert sha(f)==h,f
    for f,h in seal['artifacts'].items():assert sha(OUT/f)==h,f
    p=data();pred=pd.read_parquet(OUT/'sealed_predictions.parquet');folds=pd.read_csv(OUT/'folds.csv',parse_dates=['cutoff','cal_start'])
    ix=pd.read_csv(OUT/'split_indices.csv.gz');checks=0
    assert not pred.duplicated(['model','row_id']).any()
    assert not any(c.startswith(('win','return','excess','end','status')) for c in pred.columns)
    assert pred.probability.between(0,1).all()
    for _,f in folds.iterrows():
        ids=ix[ix.fold.eq(f.fold)]
        train=p.loc[ids[ids.role.eq('train')].row_id];cal=p.loc[ids[ids.role.eq('calibration')].row_id];test=p.loc[ids[ids.role.eq('test')].row_id]
        assert train.end126.lt(f.cal_start).all() and cal.end126.lt(f.cutoff).all()
        assert cal.date.ge(f.cal_start).all() and test.date.ge(f.cutoff).all()
        assert set(test.index)==set(p.index[p.eligible&p.date.ge(f.cutoff)&p.date.lt(f.cutoff+pd.DateOffset(months=3))])
        assert not set(train.index)&set(cal.index) and not set(cal.index)&set(test.index)
        assert set(train.index)==set(p.index[p.eligible&p.end126.lt(f.cal_start)&p.win126.notna()])
        assert set(cal.index)==set(p.index[p.eligible&p.date.ge(f.cal_start)&p.end126.lt(f.cutoff)&p.win126.notna()])
        for name,features in ARMS.items():
            a=pred[pred.fold.eq(f.fold)&pred.model.eq(name)]
            assert set(a.row_id)==set(test.index)
            sampled=a.sample(min(7,len(a)),random_state=3312);model=joblib.load(OUT/f'models/{f.fold}_{name}.joblib')
            if name=='matured_base':
                hist=p[p.eligible&p.end126.lt(f.cutoff)&p.win126.notna()]
                actual=hist.groupby('date').win126.mean().mean()
                assert np.isclose(actual,model['model']['constant']);prob=np.repeat(actual,len(sampled));raw=prob
            else:
                assert features==model['metadata']['features']
                raw=model['model'].predict_proba(p.loc[sampled.row_id,features])[:,1]
                prob=calibrated(raw,model['metadata']['calibration'])
            np.testing.assert_allclose(raw,sampled.raw_probability,atol=1e-12)
            np.testing.assert_allclose(prob,sampled.probability,atol=1e-12);checks+=len(sampled)
    means=pred.groupby(['model','date']).probability.transform('mean');np.testing.assert_allclose(means,pred.reference_probability)
    assert ((pred.probability>=.6)&(pred.probability-means>=.05)).equals(pred.admitted)
    outcomes=pd.read_parquet(OUT/'scored_outcomes.parquet');summary=pd.read_csv(OUT/'summary.csv');core=summary[summary.unit.eq('entry')&summary.horizon.eq(126)]
    for _,r in core.iterrows():
        g=outcomes[outcomes.model.eq(r.model)];z=g[g.entry];k=z[z.win126.notna()]
        assert len(z)==r.total and len(k)==r.known and k.win126.sum()==r.wins
        if len(k):
            base=p[p.eligible].groupby('date').win126.mean();delta=(k.win126-k.date.map(base)).mean()
            assert np.isclose(k.win126.mean(),r.win_rate) and np.isclose(delta,r.uplift)
            assert np.isclose(abs(k.probability.mean()-k.win126.mean()),r.calibration_gap)
        recall=g.loc[g.admitted,'win126'].sum()/g.win126.sum()
        assert np.isclose(recall,r.success_week_recall)
        expected=bool(r.win_rate>=.6 and r.uplift>=.05 and r.success_week_recall>=.1 and r.known>=100 and r.uplift_lo>0 and r.calibration_gap<=.05)
        assert bool(r.accepted)==expected
    out={'status':'PASS','scope':'chronology/reproducibility/metric arithmetic, not model efficacy','folds':len(folds),'models':len(ARMS),'prediction_rows':len(pred),'reproduced_predictions':checks,'source_and_sealed_artifact_hashes':len(seal['inputs'])+len(seal['artifacts']),'unit_tests':17,'accepted_models':core.loc[core.accepted.eq(True),'model'].tolist(),'original_goal_complete':False}
    (OUT/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
