import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from build_domestic_macro import transform,align,ACTIVITY,CREDIT


def monthly():
    ix=pd.period_range('2018-01','2022-12',freq='M',name='period')
    return pd.DataFrame(dict(pmi=50.,nonmanufacturing=51.,cpi=2.,ppi=3.,m2_yoy=8.,m2_stock=100.,tsf=1.),index=ix)


def test_observation_period_is_not_publication_date():
    raw=monthly();raw.loc['2020-12','pmi']=60
    out=align(raw,pd.to_datetime(['2021-02-14','2021-02-15']))
    # Dec 31 +45 days = Feb 14: exactly on assumed availability is still excluded.
    assert out.iloc[0].macro_observation_end==pd.Timestamp('2020-11-30')
    assert out.iloc[1].macro_observation_end==pd.Timestamp('2020-12-31')
    np.testing.assert_allclose(out.iloc[1].macro_pmi,.1)


def test_monthly_gap_not_skipped_in_change_or_flow():
    raw=monthly();raw.loc['2020-04','pmi']=60;raw=raw.drop(pd.Period('2020-01'))
    f=transform(raw)
    assert np.isnan(f.loc['2020-04','macro_pmi_change3'])
    assert np.isnan(f.loc['2020-12','macro_tsf_to_m2'])


def test_flow_stock_units_and_annual_growth():
    raw=monthly();raw.loc[raw.index.year==2021,'tsf']=2
    f=transform(raw)
    np.testing.assert_allclose(f.loc['2021-12',['macro_tsf_to_m2','macro_tsf_ttm_growth','macro_ppi_cpi_gap']].astype(float),[.24,1.,.01])
    np.testing.assert_allclose(f.loc['2021-12','macro_tsf_to_m2_change3'],.03)
    raw.loc['2021-12','m2_stock']=0
    assert np.isnan(transform(raw).loc['2021-12','macro_tsf_to_m2'])


def test_future_values_cannot_change_past_prediction_inputs():
    raw=monthly();date=pd.Timestamp('2021-02-28');a=align(raw,[date]);raw.loc[raw.index>pd.Period('2020-12')]=99999
    pd.testing.assert_frame_equal(a,align(raw,[date]))
    assert a[ACTIVITY+CREDIT].notna().all().all()
