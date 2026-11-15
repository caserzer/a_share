import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from events_r14 import revision_events,window_context

def source(values):
    return pd.DataFrame(dict(stock_code='a',broker='x',basis='profit_cny',fiscal_year=2026,
        publication_proxy_date=pd.to_datetime(['2025-01-01','2025-02-01','2025-03-01']),value=values))

def test_missing_intervening_report_is_not_skipped():
    events,ledger=revision_events(source([100,np.nan,130]))
    assert events.empty
    assert ledger.status.tolist()==['no_prior_cached_report','conflicting_current_or_prior','conflicting_current_or_prior']

def test_same_date_known_and_unknown_reports_are_conflicting():
    q=source([100,110,130]);extra=q.iloc[[1]].copy();extra['value']=np.nan
    events,ledger=revision_events(pd.concat([q,extra]))
    assert events.empty

def test_same_year_signed_revision_and_flat_are_retained():
    events,_=revision_events(source([-100,100,100]))
    assert events.revision.tolist()==[1,0]
    assert events.fiscal_year.eq(2026).all()

def test_event_reaction_excluded_from_future_entry_return():
    dates=pd.bdate_range('2025-01-01',periods=65)
    p=np.arange(100.,165.);p[1]=200
    g=pd.DataFrame(dict(era='x',level='L3',industry_code='a',block=0,date=dates,nav=p))
    result=window_context(g,pd.Series(100.,index=dates))
    assert np.isclose(result.reaction.iloc[1],1)
    assert np.isclose(result.post20.iloc[1],p[22]/p[2]-1)
    assert result.entry_date.iloc[1]==dates[2]
    assert result.post60.iloc[-1]!=result.post60.iloc[-1]
    assert np.isclose(result.pre20.iloc[21],p[20]/p[0]-1)
