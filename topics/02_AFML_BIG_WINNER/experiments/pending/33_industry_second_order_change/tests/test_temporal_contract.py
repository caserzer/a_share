from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from financial_experiment import stock_events
from price_experiment import features, outcomes, select


def financial_fixture():
    periods=pd.period_range('2018Q1',periods=16,freq='Q')
    end=periods.to_timestamp(how='end').normalize()
    quarter=np.arange(16)*10.+100
    cumulative=pd.Series(quarter).groupby(periods.year).cumsum().to_numpy()
    return pd.DataFrame({'REPORT_DATE':end,'NOTICE_DATE':end+pd.Timedelta(days=30),
                         'UPDATE_DATE':end+pd.Timedelta(days=30),'TOTALOPERATEREVE':cumulative})


def test_financial_future_revision_cannot_enter_earlier(tmp_path):
    f=financial_fixture();calendar=pd.bdate_range('2018-01-01','2023-12-31')
    p=tmp_path/'sample.parquet';f.to_parquet(p);a,_=stock_events(p,calendar)
    f.loc[15,'TOTALOPERATEREVE']*=100
    f.to_parquet(p);b,_=stock_events(p,calendar)
    cutoff=pd.Timestamp('2021-09-01')
    pd.testing.assert_frame_equal(a[a.known_date<cutoff],b[b.known_date<cutoff])
    # A revision to a denominator delays every dependent signal.
    f=financial_fixture();f.loc[4,'UPDATE_DATE']=pd.Timestamp('2023-01-01')
    f.to_parquet(p);b,_=stock_events(p,calendar)
    dependent=b[b.period_end.between('2020-01-01','2020-06-30')]
    assert dependent.empty or dependent.known_date.ge('2023-01-02').all()


def test_missing_publication_not_replaced_by_period_end(tmp_path):
    f=financial_fixture();f['NOTICE_DATE']=pd.NaT
    p=tmp_path/'sample.parquet';f.to_parquet(p)
    events,_=stock_events(p,pd.bdate_range('2018-01-01','2024-01-01'))
    assert events.empty


def test_labels_start_next_session_and_never_cross_block():
    dates=pd.bdate_range('2020-01-01',periods=140)
    g=pd.DataFrame({'date':dates,'nav':np.exp(np.arange(140)*.001),
                    'day_i':np.arange(140),'breadth21':.5})
    market=pd.Series(1.,index=dates)
    f=outcomes(features(g,market),market)
    assert np.isclose(f.excess126.iloc[0],np.exp(.126)-1)
    assert f.end126.iloc[0]==dates[127]
    assert f.excess126.iloc[13:].isna().all()
    short=outcomes(features(g.iloc[:50],market),market)
    assert short.excess126.isna().all()


def test_selection_does_not_use_future_values():
    n=30
    panel=pd.DataFrame({'date':pd.Timestamp('2020-01-03'),'era':'TEST',
        'industry_code':[str(i) for i in range(n)],'coverage':1.,'members':10,
        'velocity':np.linspace(-.1,.1,n),'acceleration':np.linspace(.03,.01,n),
        'excess126':np.linspace(-1,1,n)})
    a,_=select(panel)
    for col in panel:
        if col.startswith(('return','excess','adverse')):
            panel[col]=np.arange(len(panel))*999.
    b,_=select(panel)
    keys=['date','era','industry_code','pool','strategy','rank']
    pd.testing.assert_frame_equal(a[keys],b[keys])
