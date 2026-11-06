import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from experiment10 import admitted,inverse_delay_weights


def test_unknown_and_future_labels_never_enter_training():
    q=pd.Timestamp('2024-01-01')
    g=pd.DataFrame({'date':pd.to_datetime(['2022-01-01','2022-01-01','2022-01-01','2023-07-01']),
        'label_available_at':pd.to_datetime(['2023-12-01','2024-02-01',None,'2023-12-01']),'y':[1.,1.,np.nan,0.]})
    assert admitted(g,q,12).index.tolist()==[0]


def test_late_labels_excluded_even_when_currently_known():
    g=pd.DataFrame({'date':pd.to_datetime(['2020-01-01','2020-01-01']),
        'label_available_at':pd.to_datetime(['2022-01-01','2022-01-02']),'y':[1.,0.]})
    assert admitted(g,pd.Timestamp('2024-01-01'),24).index.tolist()==[0]


def test_delay_correction_is_bounded_and_full_followup_has_weight_one():
    q=pd.Timestamp('2024-01-01')
    ref=pd.DataFrame({'date':[pd.Timestamp('2018-01-01')]*20,
        'label_available_at':[pd.Timestamp('2018-01-01')+pd.Timedelta(days=x) for x in np.linspace(500,700,20)],
        'threshold':[.1]*20,'benchmark':['CSI300']*20,'y':[1.]*20})
    train=pd.DataFrame({'date':pd.to_datetime(['2022-12-01','2021-01-01']),
        'threshold':[.1,.1],'benchmark':['CSI300','CSI300'],'y':[1.,1.]})
    w=inverse_delay_weights(train,ref,q)
    assert w[0]==5 and w[1]==1
