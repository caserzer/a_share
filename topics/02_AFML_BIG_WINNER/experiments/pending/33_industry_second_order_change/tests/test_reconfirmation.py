import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
from single_reconfirmation_pool import reconfirm

def frame(flags,weeks=None):
    n=len(flags);weeks=list(range(n)) if weeks is None else weeks
    return pd.DataFrame({'era':['x']*n,'industry_code':['a']*n,'block':[1]*n,'week_i':weeks,'day_i':[w*5 for w in weeks],
        'date':[pd.Timestamp('2024-01-05')+pd.Timedelta(weeks=w) for w in weeks],'admitted':flags,'fold':['2024Q1']*n,'row_id':list(range(n))})

def test_second_confirmation_counts_once_and_is_prefix_stable():
    p=frame([False,True,False,True,True,False,True]);z=reconfirm(p)
    assert z.index[z.entry].tolist()==[3]
    assert z.index[z.admitted].tolist()==[3,4,6]
    assert z.state_edge.sum()==2 and z.entry.sum()==1
    pd.testing.assert_series_equal(reconfirm(p.iloc[:5]).entry,z.entry.iloc[:5])

def test_expiry_does_not_create_new_entry_or_pool_membership():
    p=frame([False,True,False,True,True,True],[0,1,2,3,26,27]);z=reconfirm(p)
    assert not z.admitted.iloc[-2:].any() and z.entry.sum()==1

def test_unknown_gap_cannot_reconfirm_old_opportunity():
    z=reconfirm(frame([False,True,False,True],[0,1,4,5]))
    assert z.entry.sum()==0 and z.raw_entry.sum()==2
