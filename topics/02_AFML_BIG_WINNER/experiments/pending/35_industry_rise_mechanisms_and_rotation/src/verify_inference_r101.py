"""Independent comparison against frozen formal outputs; validate sealed inputs."""
import pandas as pd
from common import *
from versioned_observations import verify_bundle

def run():
    out=ROOT/'outputs/r101';bundles=json.loads((out/'bundles.json').read_text());frames=[]
    provenance=json.loads((out/'feature_provenance.json').read_text())
    for path,digest in provenance['reads'].items():assert sha(path)==digest
    columns=KEY+['date','price_ready','mom20','mom60','vol20','dd60','past_excess20','past_excess60','members','breadth21','breadth63']
    source=pd.concat([pd.read_parquet(p,columns=columns) for p in provenance['reads']],ignore_index=True)
    for b in bundles:
        path=Path(b['path']);assert sha(path/'manifest.json')==b['manifest_sha256']
        m=verify_bundle(path);assert m['bundle_id']==b['bundle_id']
        for name,p in [('code','src/inference_bundle_r101.py'),('common','src/common.py'),('seal_code','src/versioned_observations.py'),('protocol','protocols/r101.json')]:assert m['sources'][name]['sha256']==sha(ROOT/p)
        assert m['capture_kind']=='historical_replay'
        for i,round_ in enumerate(['r02','r16']):
            assert m['sources'][f'model_{i}']['sha256']==sha(ROOT/f'outputs/{round_}/model_parameters.json')
            assert m['sources'][f'fold_{i}']['sha256']==sha(ROOT/f'outputs/{round_}/fold_ledger.csv')
        assert m['sources']['catalog']['sha256']==sha(ROOT/'outputs/universe_current.csv')
        assert m['sources']['provenance']['sha256']==sha(out/'feature_provenance.json')
        features=pd.read_parquet(m['sources']['features']['path']);assert list(features)==columns
        expected=source[source.era.eq('SW2021')&source.date.eq(pd.Timestamp(b['asof']))].sort_values(KEY).reset_index(drop=True)
        pd.testing.assert_frame_equal(features,expected)
        c=pd.read_csv(m['sources']['catalog']['path']);valid=set(map(tuple,c[c.era.eq('SW2021')][KEY].to_numpy()))
        outside=features[~features[KEY].apply(tuple,axis=1).isin(valid)]
        pd.testing.assert_frame_equal(pd.read_parquet(path/'rank_only_outside_catalogue.parquet').reset_index(drop=True),outside.reset_index(drop=True))
        frame=pd.read_parquet(path/'predictions.parquet');assert len(frame)==len(valid)*12
        assert set(map(tuple,frame[KEY].drop_duplicates().to_numpy()))==valid
        frames.append(frame)
    actual=pd.concat(frames,ignore_index=True)
    original=pd.read_csv(ROOT/'outputs/r22/task_monitor.csv',parse_dates=['asof'])
    keys=KEY+['asof','cohort','method','task','horizon']
    assert not actual.duplicated(keys).any() and not original.duplicated(keys).any()
    both=actual.merge(original,on=keys,how='outer',suffixes=('_new','_old'),indicator=True,validate='one_to_one')
    assert both._merge.eq('both').all()
    assert both.status_new.eq(both.status_old).all()
    assert both.prediction_new.isna().equals(both.prediction_old.isna())
    known=both.prediction_new.notna()
    np.testing.assert_allclose(both.loc[known,'prediction_new'],both.loc[known,'prediction_old'],rtol=0,atol=1e-10)
    assert both.loc[known,'model_sha256_new'].eq(both.loc[known,'model_sha256_old']).all()
    result=dict(status='PASS',rows=len(both),formal=int(known.sum()),maximum_absolute_difference=float((both.prediction_new-both.prediction_old).abs().max()),reference_sha256=sha(ROOT/'outputs/r22/task_monitor.csv'),bundles_sha256=sha(out/'bundles.json'),prospective_records=0)
    js(out/'verification.json',result);print(result)

if __name__=='__main__':run()
