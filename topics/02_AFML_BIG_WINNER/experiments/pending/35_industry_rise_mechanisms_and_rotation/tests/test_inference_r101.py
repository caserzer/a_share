import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from common import ROOT,KEY
from inference_bundle_r101 import infer,capture
from versioned_observations import verify_bundle

@pytest.fixture
def inputs():
    b=json.loads((ROOT/'outputs/r101/bundles.json').read_text())[0]
    m=verify_bundle(b['path']);s=m['sources']
    models=[]
    for i in range(2):models.extend(json.loads(Path(s[f'model_{i}']['path']).read_text()))
    return pd.read_csv(s['catalog']['path']),pd.read_parquet(s['features']['path']),pd.concat([pd.read_csv(s[f'fold_{i}']['path']) for i in range(2)]),models,s

def test_missing_date_and_duplicates(inputs):
    c,f,l,m,_=inputs
    empty=infer(c,f.iloc[:0],l,m,'2026-10-21')
    assert empty.prediction.isna().all() and empty.status.eq('no_exact_date_feature_snapshot').all()
    with pytest.raises(ValueError,match='exact-date'):infer(c,f,l,m,'2026-10-21')
    with pytest.raises(ValueError,match='duplicate feature'):infer(c,pd.concat([f,f.iloc[:1]]),l,m,'2026-09-30')
    with pytest.raises(ValueError,match='duplicate catalogue'):infer(pd.concat([c,c[c.era.eq('SW2021')].iloc[:1]]),f,l,m,'2026-09-30')
    with pytest.raises(ValueError,match='feature-only'):infer(c,f.assign(excess20=1),l,m,'2026-09-30')

def test_model_gates(inputs):
    c,f,l,m,_=inputs
    base=infer(c,f,l,m,'2026-09-30')
    chosen=base[base.task.eq('onset')&base.prediction.notna()].iloc[0]
    keys=['era','level','cohort','method','task','horizon']
    target=next(x for x in m if x['year']==2026 and all(x[k]==chosen[k] for k in keys))
    for field,value,status in [('calibration_coefficient',None,'uncalibrated_model'),('fit_max_maturity','2026-01-01','invalid_model_maturity'),('cal_max_maturity','2026-01-01','invalid_calibration_maturity')]:
        mutated=copy.deepcopy(m);changed=next(x for x in mutated if x==target);changed[field]=value
        result=infer(c,f,l,mutated,'2026-09-30');affected=base.prediction.notna()
        for k in keys:affected &= base[k].eq(chosen[k])
        assert affected.any() and result.loc[affected,'status'].eq(status).all() and result.loc[affected,'prediction'].isna().all()

def test_immutable_copy_version_and_corruption(inputs,tmp_path):
    c,f,l,m,s=inputs
    feature=tmp_path/'input.parquet';f.to_parquet(feature,index=False)
    args=[s['catalog']['path'],[s[f'fold_{i}']['path'] for i in range(2)],[s[f'model_{i}']['path'] for i in range(2)],s['provenance']['path']]
    store=tmp_path/'store';first=capture(store,'2026-09-30',feature,*args)
    assert capture(store,'2026-09-30',feature,*args)==first
    old=verify_bundle(first);saved=pd.read_parquet(old['sources']['features']['path'])
    f.loc[f.index[0],'mom20']+=.001;f.to_parquet(feature,index=False)
    second=capture(store,'2026-09-30',feature,*args);assert first!=second
    verify_bundle(first);pd.testing.assert_frame_equal(pd.read_parquet(old['sources']['features']['path']),saved)
    with (second/'predictions.parquet').open('ab') as handle:handle.write(b'corruption')
    with pytest.raises(ValueError,match='output integrity'):verify_bundle(second)
    with pytest.raises(ValueError,match='output integrity'):capture(store,'2026-09-30',feature,*args)
