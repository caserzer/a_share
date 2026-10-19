import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from build_financial_quality import FIELDS,prepare_reports,select_features,ratios


def report(period='2020-12-31',notice='2021-03-01',update='2021-03-01',**values):
    row={c:np.nan for c in FIELDS}
    row.update(REPORT_DATE=period,NOTICE_DATE=notice,UPDATE_DATE=update,CURRENCY='CNY')
    row.update(values)
    return row


def test_strict_availability_and_late_revision():
    f=prepare_reports(pd.DataFrame([report(ROEJQ=10,update='2021-05-01')]))
    for date in ['2021-04-01','2021-05-01']:
        assert np.isnan(select_features(f,pd.Timestamp(date))['fq_roe'])
    assert select_features(f,pd.Timestamp('2021-05-02'))['fq_roe']==.1


def test_latest_report_missing_is_not_filled_from_old():
    f=prepare_reports(pd.DataFrame([report(ROEJQ=10),report('2021-03-31','2021-04-20','2021-04-20')]))
    got=select_features(f,pd.Timestamp('2021-05-01'))
    assert np.isnan(got['fq_roe']) and got['fq_report_date']==pd.Timestamp('2021-03-31')


def test_exact_annual_prior_and_both_available():
    rows=[report('2019-12-31','2020-04-01','2020-04-01',ROEKCJQ=5),report(ROEKCJQ=12)]
    got=select_features(prepare_reports(pd.DataFrame(rows)),pd.Timestamp('2021-04-01'))
    assert got['fq_prior_available']==1
    np.testing.assert_allclose(got['fq_core_roe_annual_change'],.07)
    rows[0]['UPDATE_DATE']='2021-04-01'
    got=select_features(prepare_reports(pd.DataFrame(rows)),pd.Timestamp('2021-04-01'))
    assert got['fq_prior_available']==0 and np.isnan(got['fq_core_roe_annual_change'])
    rows[0].update(REPORT_DATE='2019-09-30',UPDATE_DATE='2020-04-01')
    assert select_features(prepare_reports(pd.DataFrame(rows)),pd.Timestamp('2021-04-01'))['fq_prior_available']==0


def test_units_and_invalid_denominators():
    r=report(ROEJQ=10,EPSJB=-2,MGJYXJJE=4,BPS=10,TOTALOPERATEREVE=100,PARENTNETPROFIT=20,KCFJCXSYJLR=15,LD=2)
    got=ratios(r)
    assert got['fq_roe']==.1 and got['fq_ocf_eps']==-2 and got['fq_current_ratio']==2
    assert got['fq_nonrecurring_margin']==.05 and got['fq_cash_earnings_gap_book']==.6
    r.update(BPS=0,TOTALOPERATEREVE=-1,EPSJB=.01)
    got=ratios(r)
    assert all(np.isnan(got[c]) for c in ['fq_core_margin','fq_ocf_eps','fq_ocf_book'])


def test_staleness_and_prefix():
    f=prepare_reports(pd.DataFrame([report(ROEJQ=10),report('2021-12-31','2022-04-01','2022-04-01',ROEJQ=20)]))
    date=pd.Timestamp('2021-04-01')
    pd.testing.assert_series_equal(pd.Series(select_features(f,date)),pd.Series(select_features(f[f.available_date<date],date)))
    assert np.isnan(select_features(f,pd.Timestamp('2024-01-01'))['fq_roe'])
