"""R14 audit of conditional calibration, unchanged protocol and opportunity IDs."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import probability_pool as base
from market_calibration_pool import OUT,MARKET,FIELDS,apply_mapping,market_features
from pool_evaluation import EP,sha,KEY

def main():
    seal=json.loads((OUT/'prediction_seal.json').read_text())
    for name,h in seal['inputs'].items():assert sha(name)==h,name
    for name,h in seal['artifacts'].items():assert sha(OUT/name)==h,name
    oldseal=json.loads((EP/'outputs/r12/prediction_seal.json').read_text());protocol=str(EP/'configs/pool_metric_v1.json')
    assert sha(protocol)==oldseal['inputs'][protocol]
    p=base.data();m=pd.read_parquet(OUT/'market_features.parquet');pred=pd.read_parquet(OUT/'sealed_predictions.parquet')
    params=json.loads((OUT/'mapping_parameters.json').read_text());folds=pd.read_csv(EP/'outputs/r12/folds.csv',parse_dates=['cutoff'])
    old=pd.read_parquet(EP/'outputs/r12/sealed_predictions.parquet');checks=0
    assert not pred.duplicated(['model','row_id']).any()
    assert not any(c.startswith(('win','end','return','excess','status')) for c in pred.columns)
    for r in params:
        f=folds[folds.fold.eq(r['fold'])].iloc[0];train,cal,test,start=base.split(p,f.cutoff)
        assert cal.end126.lt(f.cutoff).all() and train.end126.lt(start).all()
        z=pred[pred.model.eq(r['model']+'__'+r['variant'])&pred.fold.eq(r['fold'])]
        assert set(z.row_id)==set(test.index)
        z=z.sample(min(7,len(z)),random_state=3314)
        bundle=joblib.load(EP/f"outputs/r12/models/{r['fold']}_{r['model']}.joblib")
        raw=bundle['model'].predict_proba(p.loc[z.row_id,bundle['metadata']['features']])[:,1]
        np.testing.assert_allclose(raw,z.raw_probability,atol=1e-12)
        if r['variant']=='identity':actual=raw
        else:
            actual,outside=apply_mapping(raw,r['mapping'],m.loc[z.row_id] if r['variant']=='ridge_market' else None)
            assert np.array_equal(outside,z.market_outside_cal_range)
            if r['variant']=='ridge_market':
                w=base.date_weights(cal);w=w/w.sum();mean=(w[:,None]*m.loc[cal.index].to_numpy()).sum(axis=0)
                np.testing.assert_allclose(mean,r['mapping']['mean'],atol=1e-12)
        np.testing.assert_allclose(actual,z.probability,atol=1e-12);checks+=len(z)
    # Independent prefix reconstruction of benchmark features.
    close=pd.read_parquet(MARKET).close.sort_index()
    for _,r in p[p.eligible].sample(40,random_state=3314).iterrows():
        prefix=close.loc[:r.date];expected=[prefix.iloc[-1]/prefix.iloc[-22]-1,prefix.iloc[-1]/prefix.iloc[-127]-1,np.log(prefix).diff().iloc[-63:].std()*np.sqrt(252)]
        np.testing.assert_allclose(m.loc[r.name,FIELDS[:3]],expected,atol=1e-12)
    for model,g in pred.groupby('model'):
        np.testing.assert_allclose(g.reference_probability,g.groupby('date').probability.transform('mean'),atol=1e-12)
        assert base.gate(g.probability,g.reference_probability).equals(g.admitted)
    summary=pd.read_csv(OUT/'summary.csv');scores=pd.read_parquet(OUT/'scored_outcomes.parquet')
    for _,r in summary[summary.unit.eq('entry')&summary.horizon.eq(126)].iterrows():
        g=scores[scores.model.eq(r.model)];z=g[g.entry];k=z[z.win126.notna()]
        assert len(z)==r.total and len(k)==r.known and k.win126.sum()==r.wins
        if len(k):
            assert np.isclose(k.win126.mean(),r.win_rate)
            ref=p[p.eligible].groupby('date').win126.mean();assert np.isclose((k.win126-k.date.map(ref)).mean(),r.uplift)
        expected=bool(r.win_rate>=.6 and r.uplift>=.05 and r.success_week_recall>=.1 and r.known>=100 and r.uplift_lo>0 and r.calibration_gap<=.05)
        assert bool(r.accepted)==expected
    events=pd.read_csv(OUT/'opportunity_registry.csv.gz');e=events[events.entry]
    assert not e.duplicated(['model','row_id']).any()
    assert (e.groupby(['model','opportunity_id']).cluster_first126.sum()==1).all()
    assert not (events.rearm4&~events.entry).any()
    receipt=json.loads((OUT/'evaluation_receipt.json').read_text());assert receipt['primary_bootstrap_weeks']==26 and receipt['wrapper_sha256']==sha(receipt['evaluation_wrapper'])
    result={'status':'PASS','protocol_unchanged':True,'source_and_prediction_hashes':len(seal['inputs'])+len(seal['artifacts']),'reproduced_predictions':checks,'market_prefix_checks':40,'opportunity_entries_checked':len(e),'tests_passed':23,'independent_forward_validation':False}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
