from pathlib import Path
import sys
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from diagnostics import calibration_context


def test_past_calibration_context_excludes_unmatured_outcomes():
    h=pd.DataFrame(dict(date=pd.to_datetime(['2019-01-31','2020-12-31']),instrument=['A','A'],
        label_end=pd.to_datetime(['2019-07-31','2021-06-30']),actual=[-.3,.1],
        G=[.2,.8],GP=[.3,.7],GI=[.3,.8],GPI=[.4,.9],L=[.2,.5]))
    current=pd.DataFrame(dict(date=pd.to_datetime(['2021-01-29']),instrument=['A']))
    a=calibration_context(current,h)
    h.loc[1,'actual']=-.99;b=calibration_context(current,h)
    pd.testing.assert_frame_equal(a,b)
    assert a.calibration_history_months.iloc[0]==1
    assert np.isclose(a.past_GPI_brier.iloc[0],.36)
