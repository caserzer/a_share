import sys,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import v3_local_refresh_v2 as refresh

def sample(tmp_path):
    dates=pd.bdate_range('2019-09-02','2020-01-17')
    raw=pd.DataFrame(dict(date=dates,day_i=np.arange(len(dates)),era='X',industry_code='A',block=1,nav=np.exp(-np.arange(len(dates))*.001)))
    selected=[pd.Timestamp('2017-01-06')]+list(dates[dates.weekday==4])
    cat=pd.DataFrame(dict(date=selected,era='X',industry_code='A',industry_name='Example'))
    fit=pd.DataFrame([dict(year=2020,model=m,latest_label_available='2019-12-27',fitted_before='2020-01-01') for m in ['LR_COVER','LR_EARLY_UNION']]);fit.to_csv(tmp_path/'fit_audit.csv',index=False)
    (tmp_path/'2020').mkdir()
    for m in fit.model:(tmp_path/'2020'/(m+'.joblib')).write_bytes(b'unit-test-model')
    hashes={str(p.relative_to(tmp_path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()}
    (tmp_path/'receipt.json').write_text(json.dumps(dict(artifacts=hashes)))
    return raw,cat,pd.DataFrame(dict(date=dates))

def test_no_candidates_is_valid_empty_observation_period(tmp_path,monkeypatch):
    raw,cat,cal=sample(tmp_path)
    class NoPredict:
        def predict_proba(self,x):raise AssertionError('No rows must not call inference')
    monkeypatch.setattr(refresh.joblib,'load',lambda _:NoPredict())
    panel,_,_=refresh.build_signals(raw,cat,cal,tmp_path,'2020-01-17')
    assert len(panel)>0 and not panel.eligible.any() and panel.score_BALANCED.isna().all()

def test_unregistered_year_not_silently_reused(tmp_path):
    raw,cat,cal=sample(tmp_path)
    (tmp_path/'2020/LR_COVER.joblib').unlink()
    with pytest.raises(ValueError,match='No registered model'):
        refresh.build_signals(raw,cat,cal,tmp_path,'2020-01-17')
