from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import scoring


def fixture(monkeypatch, missing_selected_open=False):
    monkeypatch.setattr(scoring, 'detail', lambda *args: None)
    months = pd.period_range('2020-01', periods=7, freq='M')
    dates = pd.to_datetime(['2020-01-31','2020-02-28','2020-03-31','2020-04-30','2020-05-29','2020-06-30','2020-07-31'])
    rows=[]
    for i,sid in enumerate(['a','b','c','d','e']):
        for j,m in enumerate(months):
            rows.append(dict(month=m,date=dates[j],entry_date=pd.Timestamp('2020-02-03'),security_id=sid,
                instrument=sid,name=sid,qfq_close=130.,close_chain='chain',entry_open=np.nan if missing_selected_open and sid=='a' else 100.,
                entry_chain='chain',cap=np.nan if sid=='e' else 100.-i*10,unresolved=0))
    panel=pd.DataFrame(rows)
    joined=panel[panel.month.eq(months[0])].assign(era='SW2014',level='L2',industry_code='industry',industry_name='Industry')
    marks=joined[['security_id','month','cap']].copy()
    marks['EXACT']=marks.cap;marks['MARK_7D']=marks.cap.fillna(10.);marks['MARK_31D']=marks['MARK_7D'];marks['mark_age_days']=3
    phases=pd.DataFrame([dict(phase_id='phase',era='SW2014',level='L2',industry_code='industry',industry_name='Industry',
        start_month='2020-01',end_month='2020-07',start_date=dates[0],end_date=dates[-1],duration_months=6,
        drawdown_threshold=.15,length_class='IN_RANGE_6_18',status='CONFIRMED',left_censored=False,right_censored=False,
        end_is_partial=False,industry_return=.5)])
    index=pd.DataFrame({'open':100.,'close':110.},index=pd.DatetimeIndex(list(dates)+[pd.Timestamp('2020-02-03')]))
    scores,stocks,paths=scoring.stage_scores(phases,panel,joined,marks,{'CSI300':index})
    return scores,stocks


def test_missing_small_member_rank_does_not_remove_the_industry_stage(monkeypatch):
    s,_=fixture(monkeypatch)
    assert len(s)==3 and s.primary_stage.all()
    exact=s[s.policy.eq('EXACT')].iloc[0]
    diagnostic=s[s.policy.eq('MARK_7D')].iloc[0]
    assert not exact.rank_complete and exact.status=='UNKNOWN_RANK'
    assert diagnostic.rank_complete and diagnostic.top3=='a;b;c'
    assert np.isclose(diagnostic.portfolio_excess,.2)


def test_valuation_mark_never_creates_missing_trade_entry(monkeypatch):
    s,_=fixture(monkeypatch,True)
    diagnostic=s[s.policy.eq('MARK_31D')].iloc[0]
    assert diagnostic.rank_complete and not diagnostic.complete
    assert diagnostic.status=='UNKNOWN_TRADE_ENDPOINT' and pd.isna(diagnostic.portfolio_excess)
