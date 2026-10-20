from pathlib import Path
import sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from controls import sparse_evaluation_rows,monthly_brier
from strict_local_diagnostic import empirical_rate


def test_sparse_flag_column_does_not_resolve_pandas_accessor():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31','2020-02-28','2021-02-26']),sparse=[True,False,True]))
    selected=sparse_evaluation_rows(f,pd.Timestamp('2020-01-31'))
    assert selected.index.tolist()==[0]


def test_exact_unshrunk_rate_is_not_weak_prior():
    f=pd.DataFrame(dict(individual_months=[0,2,10],individual_events=[0,1,0],G=[.2,.2,.2]))
    p=empirical_rate(f)
    assert p[0]==.2 and p[1]==.5 and p[2]==1e-6


def test_entirely_unmatured_control_months_are_not_evaluated():
    f=pd.DataFrame(dict(date=pd.to_datetime(['2020-01-31','2020-02-28']),G=[.2,.3],actual=[-.3,float('nan')]))
    scored=monthly_brier(f,['G'])
    assert len(scored)==1 and abs(scored.brier.iloc[0]-.64)<1e-12
