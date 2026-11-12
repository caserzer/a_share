"""Event calibration audit, same-date parent comparison and candidate diagnostics."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import probability_pool as engine
from event_probability_pool import PARENT,mature_sets,apply_admission_policy
from market_calibration_pool import apply_mapping
from pool_evaluation import EP,sha

def main(round_id='r16'):
    out=EP/'outputs'/round_id;seal=json.loads((out/'prediction_seal.json').read_text())
    for f,h in seal['inputs'].items():assert sha(f)==h,f
    for f,h in seal['artifacts'].items():assert sha(out/f)==h,f
    protocol=EP/'configs/pool_metric_v1.json';old=json.loads((EP/'outputs/r12/prediction_seal.json').read_text());assert sha(protocol)==old['inputs'][str(protocol)]
    p=engine.data();parent_path=Path(seal.get('candidate_source',str(PARENT)));parent=pd.read_parquet(parent_path);history=parent.merge(p[['win126','end126']],left_on='row_id',right_index=True,validate='many_to_one');history['candidate_event']=history.entry
    pred=pd.read_parquet(out/'sealed_predictions.parquet');params=json.loads((out/'mapping_parameters.json').read_text());folds=pd.read_csv(out/'calibration_folds.csv',parse_dates=['cutoff'])
    indices=pd.read_csv(out/'calibration_rows.csv.gz');verified=0
    assert not any(c.startswith(('win','end','return','excess','status')) for c in pred.columns)
    assert not pred.duplicated(['model','row_id']).any()
    for r in params:
        f=folds[folds.base_model.eq(r['base_model'])&folds.fold.eq(r['fold'])].iloc[0];g=history[history.model.eq(r['base_model'])]
        ev,st,ok=mature_sets(g,f.cutoff);assert ok==r['supported']
        for role,z in [('event',ev),('state',st)]:
            saved=indices[indices.base_model.eq(r['base_model'])&indices.fold.eq(r['fold'])&indices.role.eq(role)]
            assert set(saved.row_id)==set(z.row_id)
            assert z.end126.lt(f.cutoff).all() and z.fit_cutoff.le(z.date).all()
        selection=pred.model.eq(r['model'])&pred.calibration_fold.eq(r['fold']) if 'calibration_fold' in pred else pred.model.eq(r['model'])&pred.fold.eq(r['fold'])
        test=pred[selection];assert test.date.ge(f.cutoff).all()
        sample=pd.concat([test.sample(min(12,len(test)),random_state=3316),test[test.candidate_event].head(5)]).drop_duplicates('row_id')
        if not ok:assert sample.probability.isna().all() and not sample.admitted.any();continue
        expected,_=apply_mapping(sample.raw_probability.to_numpy(),r['global_mapping'])
        event=sample.candidate_event.to_numpy()
        if r['event_mapping'].get('mean'):
            from event_context_pool import event_features
            context=event_features(sample,p)
            expected[event],_=apply_mapping(sample.loc[sample.candidate_event,'raw_probability'].to_numpy(),r['event_mapping'],context.loc[sample.index[sample.candidate_event]])
            fit_features=event_features(ev,p)
            np.testing.assert_allclose(fit_features.mean().to_numpy(),r['event_mapping']['mean'],atol=1e-12)
        else:expected[event],_=apply_mapping(sample.loc[sample.candidate_event,'raw_probability'].to_numpy(),r['event_mapping'])
        np.testing.assert_allclose(sample.probability,expected,atol=1e-12);verified+=len(sample)
    for model,g in pred.groupby('model'):
        expected=g.groupby('date').probability.transform('mean');np.testing.assert_allclose(g.reference_probability,expected,equal_nan=True)
        assert not g[g.entry].duplicated('opportunity_id').any()
        assert not (g.entry&~g.candidate_event).any()
        assert not (g.admitted&~g.parent_admitted).any()
        assert not g.loc[~g.calibration_supported,'admitted'].any()
    scores=pd.read_parquet(out/'scored_outcomes.parquet');summary=pd.read_csv(out/'summary.csv');diagnostics=[];comparisons=[]
    for model,g in scores.groupby('model'):
        oldmodel=model.split('__')[0]+'__identity';par=history[history.model.eq(oldmodel)]
        supported_dates=set(g.loc[g.calibration_supported,'date']);known_dates=set(g.loc[g.win126.notna(),'date'])
        for scope,mask in [('all_supported',g.calibration_supported),('unique_candidates',g.calibration_supported&g.candidate_event),('admitted',g.entry)]:
            k=g[mask&g.win126.notna()&g.probability.notna()]
            diagnostics.append(dict(model=model,scope=scope,known=len(k),predicted=k.probability.mean(),actual=k.win126.mean(),gap=abs(k.probability.mean()-k.win126.mean()),brier=((k.probability-k.win126)**2).mean()))
        ref=p[p.eligible].groupby('date').win126.mean()
        for label,z in [('parent_full',par[par.entry]),('parent_supported_dates',par[par.entry&par.date.isin(supported_dates)]),('new_admitted',g[g.entry])]:
            k=z[z.win126.notna()];comparisons.append(dict(model=model,comparison=label,total=len(z),known=len(k),wins=k.win126.sum(),win_rate=k.win126.mean(),reference=k.date.map(ref).mean(),uplift=(k.win126-k.date.map(ref)).mean()))
        r=summary[summary.model.eq(model)&summary.unit.eq('entry')&summary.horizon.eq(126)].iloc[0];z=g[g.entry];k=z[z.win126.notna()]
        assert len(z)==r.total and len(k)==r.known and k.win126.sum()==r.wins
        if len(k):assert np.isclose(k.win126.mean(),r.win_rate) and np.isclose((k.win126-k.date.map(ref)).mean(),r.uplift)
        expected=bool(r.win_rate>=.6 and r.uplift>=.05 and r.success_week_recall>=.1 and r.known>=100 and r.uplift_lo>0 and r.calibration_gap<=.05)
        assert bool(r.accepted)==expected
    pd.DataFrame(diagnostics).to_csv(out/'event_calibration_diagnostics.csv',index=False);pd.DataFrame(comparisons).to_csv(out/'same_period_comparison.csv',index=False)
    result={'status':'PASS','protocol_unchanged':True,'predictions':len(pred),'sample_predictions_reproduced':verified,'calibration_rows_reconciled':len(indices),'future_labels_in_calibration':False,'support_unknown_retained':True,'independent_forward_validation':False}
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--round',default='r16');a=parser.parse_args();main(a.round)
