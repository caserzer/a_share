"""R12/R13 audit tables, exact R13 mapping checks, historical score inventory."""
import json
import numpy as np
import pandas as pd
from pool_evaluation import EP,sha

def main():
    r12=EP/'outputs/r12';r13=EP/'outputs/r13'
    old=pd.read_parquet(r12/'sealed_predictions.parquet');new=pd.read_parquet(r13/'sealed_predictions.parquet')
    seal=json.loads((r13/'prediction_seal.json').read_text())
    for f,h in seal['inputs'].items():assert sha(f)==h
    for f,h in seal['artifacts'].items():assert sha(r13/f)==h
    assert not any(c.startswith(('win','return','excess','end','status')) for c in new.columns)
    count=0
    for name,g in new.groupby('model'):
        base,variant=name.split('__');paired=g.merge(old[old.model.eq(base)][['row_id','probability','raw_probability']],on='row_id',suffixes=('','_old'),validate='one_to_one')
        expected=paired.raw_probability_old if variant=='identity' else (paired.raw_probability_old+paired.probability_old)/2
        np.testing.assert_allclose(paired.probability,expected,atol=1e-12);count+=len(paired)
    means=new.groupby(['model','date']).probability.transform('mean')
    np.testing.assert_allclose(new.reference_probability,means)
    assert ((new.probability>=.6)&(new.probability-means>=.05)).equals(new.admitted)
    pdict=[];quarter=[];releases=[];snapshots=[];latest_registry=pd.read_csv(EP/'outputs/r09/universe_registry.csv.gz',parse_dates=['date'])
    latest_registry=latest_registry[latest_registry.date.eq(latest_registry.date.max())]
    for round_id in ['r12','r13']:
        out=EP/'outputs'/round_id;s=pd.read_csv(out/'summary.csv');p=pd.read_parquet(out/'scored_outcomes.parquet')
        for name,g in p.groupby('model'):
            k=g[g.win126.notna()];r=s[s.model.eq(name)&s.unit.eq('entry')&s.horizon.eq(126)].iloc[0]
            entries=g[g.entry];known=entries[entries.win126.notna()]
            assert len(entries)==r.total and len(known)==r.known and known.win126.sum()==r.wins
            assert r.known+r.immature+r.missing==r.total
            if len(known):
                assert np.isclose(known.win126.mean(),r.win_rate)
                assert np.isclose(abs(known.probability.mean()-known.win126.mean()),r.calibration_gap)
            expected=bool(r.win_rate>=.6 and r.uplift>=.05 and r.success_week_recall>=.1 and r.known>=100 and r.uplift_lo>0 and r.calibration_gap<=.05)
            assert bool(r.accepted)==expected
            pdict.append(dict(round=round_id,model=name,known=len(k),raw_brier=((k.raw_probability-k.win126)**2).mean(),score_brier=((k.probability-k.win126)**2).mean(),overall_actual=k.win126.mean(),mean_prediction=k.probability.mean()))
            for fold,a in g.groupby('fold'):
                b=a[a.win126.notna()]
                quarter.append(dict(round=round_id,model=name,fold=fold,total=len(a),known=len(b),mean_pred_known=b.probability.mean(),mean_raw_known=b.raw_probability.mean(),actual_known=b.win126.mean(),admitted=int(a.admitted.sum()),entries=int(a.entry.sum())))
            releases.append(dict(round=round_id,model=name,historical_metric_pass=expected,production_authorized=False,failed_gates=r.failed_gates,known_entries=int(r.known),success_rate=None if pd.isna(r.win_rate) else float(r.win_rate)))
            recent=g[g.date.eq(latest_registry.date.max())]
            columns=['date','era','industry_code','score','reference_probability','predicted_uplift','admitted','entry','fold']
            snap=latest_registry.merge(recent[columns],on=['date','era','industry_code'],how='left',validate='one_to_one')
            snap['round']=round_id;snap['model']=name;snap['historical_metric_pass']=expected;snap['production_authorized']=False
            snap['score_status']=np.where(snap.score.isna(),'UNKNOWN_NO_VALID_INPUT','EXPERIMENTAL_NOT_CERTIFIED_PROBABILITY')
            snapshots.append(snap)
    pd.DataFrame(pdict).to_csv(EP/'outputs/probability_model_diagnostics.csv',index=False)
    pd.DataFrame(quarter).to_csv(EP/'outputs/probability_quarter_diagnostics.csv',index=False)
    pd.concat(snapshots,ignore_index=True).to_csv(EP/'outputs/probability_latest_industry_scores.csv',index=False)
    (EP/'outputs/probability_release_gate.json').write_text(json.dumps({'protocol':'pool_metric_v1','models':releases,'no_automatic_deployment':True},ensure_ascii=False,indent=2)+'\n')
    (r13/'validation.json').write_text(json.dumps({'status':'PASS','mapping_predictions_verified':count,'sealed_hashes_checked':len(seal['inputs'])+len(seal['artifacts']),'summary_acceptance_reconciled':True,'independent_forward_validation':False},indent=2)+'\n')
    print('R13 mapping and gates validated; diagnostics and full-industry scores saved.')
if __name__=='__main__':main()
