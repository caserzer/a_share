import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from q5_followup_engine import select_target
from q5_followup import phase_dates,specs

def test_buffer_retains_borderline_holding_and_exits_beyond_cutoff():
    score=np.arange(100,dtype=float);member=np.ones(100,bool);held=np.zeros(100,bool);symbols=np.array([f'S{i:03}' for i in range(100)])
    held[75]=True;held[60]=True
    got=select_target(score,member,held,symbols,.3)
    assert len(got)==20 and 75 in got and 60 not in got and 80 not in got
    member[75]=False;score[99]=np.nan
    got=select_target(score,member,held,symbols,.4)
    assert 75 not in got and 99 not in got and 60 in got

def test_buffer_initial_equals_q5_and_caps_retained_names():
    for n in [0,1,99,299,300]:
        score=np.ones(n);member=np.ones(n,bool);symbols=np.array([f'S{i:03}' for i in range(n)])
        plain=select_target(score,member,np.zeros(n,bool),symbols)
        for buffer in [.3,.4]:
            assert set(select_target(score,member,np.zeros(n,bool),symbols,buffer))==set(plain)
            assert set(select_target(score,member,np.ones(n,bool),symbols,buffer))==set(plain)

def test_phase_skips_short_month_without_future_fallback():
    ds=pd.to_datetime(['2021-01-08','2021-01-15','2021-01-22','2021-01-29','2021-02-05','2021-02-19','2021-02-26','2021-03-05','2021-03-12','2021-03-19','2021-03-26'])
    assert list(phase_dates(ds,4))==list(pd.to_datetime(['2021-01-08','2021-03-26']))
    for phase in [1,2,3,4]:
        full=phase_dates(ds,phase);prefix=phase_dates(ds[:9],phase)
        assert list(full[full<=ds[8]])==list(prefix)

def test_fixed_scope_unique():
    rows=specs();assert len(rows)==126 and len(set(r['account'] for r in rows))==126
    assert sum(r['reuse'] for r in rows)==27
