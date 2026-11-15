import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from v3_m04_train import training_weights


def panel():
    return pd.DataFrame(dict(date=pd.to_datetime(['2019-01-04','2019-01-04','2019-01-11','2019-01-18']),
        target_available_date=pd.to_datetime(['2019-03-01']*4),eligible=True,
        parent_coverage_target=[1.,0.,1.,1.],child_coverage_target=[0.,0.,0.,1.],
        parent_early_target=[1.,0.,1.,0.],child_early_target=[0.,0.,0.,1.],
        parent_reference=['a',None,'a','b'],child_reference=[None,None,None,'bc']))


def test_group_mass_and_class_totals_preserved():
    tr,y,ref,old,new=training_weights(panel(),2020,'COVER');pos=y.eq(1)
    np.testing.assert_allclose(new[pos].sum(),old[pos].sum())
    np.testing.assert_array_equal(new[~pos],old[~pos])
    masses=new[pos].groupby(ref[pos]).sum()
    np.testing.assert_allclose(masses,masses.iloc[0])
    assert not np.allclose(new,old)


def test_future_rows_cannot_change_historical_weights():
    original=panel();future=panel();future['target_available_date']=pd.Timestamp('2022-01-01')
    extended=pd.concat([original,future],ignore_index=True)
    a=training_weights(original,2020,'EARLY');b=training_weights(extended,2020,'EARLY')
    for i in [1,2,3,4]:pd.testing.assert_series_equal(a[i],b[i])


def test_child_primary_reference_used_once():
    tr,y,ref,old,new=training_weights(panel(),2020,'EARLY')
    assert ref.iloc[-1]=='C|bc'
    assert int(y.sum())==3 and len(new)==4


def test_unknown_label_excluded_not_negative():
    d=panel();d.loc[1,['parent_coverage_target','child_coverage_target']]=np.nan
    tr,y,ref,old,new=training_weights(d,2020,'COVER')
    assert len(tr)==3 and 1 not in y.index
