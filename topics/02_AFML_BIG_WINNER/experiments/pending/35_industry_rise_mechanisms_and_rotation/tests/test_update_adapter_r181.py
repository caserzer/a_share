import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import pytest
from update_adapter_r181 import adapt


def inputs():
    cal=pd.to_datetime(['2026-05-29','2026-06-01','2026-06-02','2026-06-03'])
    d=pd.DataFrame(dict(era='SW2021',level='L2',industry_code='a',date=cal[[0,1,3]],known_at=cal[[1,1,3]],source_kind=['anchor','observed','observed'],nav=[1.,1.1,1.2],members=1))
    a=pd.DataFrame(dict(era=['SW2021'],level=['L2'],industry_code=['a'],month=[pd.Period('2026-05')],date=[cal[0]],security_id=['s']))
    return d,a,cal


def test_future_anchor_excluded_and_calendar_gap_restarts():
    d,a,c=inputs()
    with pytest.raises(ValueError,match='no available'):adapt(d,a,c,'2026-05-29')
    f=adapt(d,a,c,'2026-06-03')
    assert f.day_i.tolist()==[0,1,3]
    assert f.block.tolist()==[20260529,20260529,20260603]
    assert f.membership_asof.eq(pd.Timestamp('2026-05-29')).all()
    assert len(adapt(d,a,c,'2026-06-01'))==2


def test_missing_clock_and_unmatched_membership_fail_closed():
    d,a,c=inputs();d.loc[0,'known_at']=pd.NaT
    with pytest.raises(ValueError,match='unknown availability'):adapt(d,a,c,'2026-06-03')
    d,a,c=inputs();d.loc[1,'members']=2
    with pytest.raises(ValueError,match='provenance mismatch'):adapt(d,a,c,'2026-06-03')
