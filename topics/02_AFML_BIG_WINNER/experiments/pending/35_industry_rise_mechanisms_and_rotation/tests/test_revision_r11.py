import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
from coverage_r11 import revisions_at

def fixture():
    return pd.DataFrame(dict(stock_code=['000001']*3,broker=['a']*3,fiscal_year=[2025,2025,2026],basis=['profit_cny']*3,
        publication_proxy_date=pd.to_datetime(['2025-01-01','2025-02-01','2025-01-01']),value=[100,120,900]))

def test_same_fiscal_year_and_strict_publication_cutoff():
    d=fixture()
    assert revisions_at(d,pd.Timestamp('2025-02-01')).empty
    r=revisions_at(d,pd.Timestamp('2025-02-02'))
    assert len(r)==1 and abs(r.revision.iloc[0]-20/220)<1e-12
    assert r.fiscal_year.iloc[0]==2025

def test_simultaneous_conflicting_reports_are_unknown():
    d=fixture();extra=d.iloc[[1]].copy();extra['value']=130
    assert revisions_at(pd.concat([d,extra]),pd.Timestamp('2025-02-02')).empty

def test_negative_profit_sign_crossing_is_not_percent_growth():
    d=fixture();d.loc[0,'value']=-100;d.loc[1,'value']=100
    r=revisions_at(d,pd.Timestamp('2025-02-02'))
    assert r.revision.iloc[0]==1

def test_broker_mismatch_cannot_form_revision():
    d=fixture();d.loc[1,'broker']='b'
    assert revisions_at(d,pd.Timestamp('2025-02-02')).empty
