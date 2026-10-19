import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from predict_from_snapshot import validate_snapshot
from probability_credibility import event_evidence


def snapshot():
    return dict(asof='2026-10-19',feature_available_at='2026-10-19T10:00:00+00:00',source_price_end='2026-10-19',source_status='consistent',features=dict(vol63=.2,log_cap=24))


def test_snapshot_rejects_future_stale_and_unverified():
    s=snapshot();assert validate_snapshot(s)==pd.Timestamp('2026-10-19')
    for key,value in [('feature_available_at','2026-10-20T00:00:00+08:00'),('source_price_end','2026-10-16'),('source_status','unknown')]:
        s=snapshot();s[key]=value
        with pytest.raises(ValueError):validate_snapshot(s)
    s=snapshot();s['features']['vol63']=np.nan
    with pytest.raises(ValueError):validate_snapshot(s)


def test_credibility_rejects_false_70_percent_and_excludes_future():
    dates=pd.date_range('2021-01-31',periods=36,freq='ME')
    frame=pd.DataFrame(dict(date=np.repeat(dates,20),label_end=np.repeat(dates+pd.Timedelta(days=30),20),
        actual=np.tile([.1]*6+[-.1]*14,36),p_up=.7))
    evidence=event_evidence(frame,'up',.7,1,'2025-01-01')
    assert evidence['status']=='miscalibrated'
    assert abs(evidence['historical_observed']-.3)<1e-9
    future=frame.copy();future['label_end']=pd.Timestamp('2027-01-01');future['actual']=.1
    check=event_evidence(pd.concat([frame,future]),'up',.7,1,'2025-01-01')
    assert check==evidence
    sparse=event_evidence(frame.head(10),'up',.7,1,'2025-01-01')
    assert sparse['status']=='insufficient_evidence'


def test_no_rejection_is_not_proof():
    dates=pd.date_range('2021-01-31',periods=36,freq='ME')
    frame=pd.DataFrame(dict(date=np.repeat(dates,20),label_end=np.repeat(dates+pd.Timedelta(days=30),20),
        actual=np.tile([.1]*14+[-.1]*6,36),p_up=.7))
    assert event_evidence(frame,'up',.7,1,'2025-01-01')['status']=='not_rejected_not_proven'
