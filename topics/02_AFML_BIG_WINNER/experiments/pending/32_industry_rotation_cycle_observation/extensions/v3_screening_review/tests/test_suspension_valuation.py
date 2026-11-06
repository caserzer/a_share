from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from review import diagnostic_cap


def row():
    return SimpleNamespace(instrument='SH688313', cap=np.nan, total_shares=100., entry_open=np.nan)


def bars():
    return pd.DataFrame(dict(date=pd.to_datetime(['2025-06-27', '2025-07-11']),
        close=[38.05, 43.70], close_conflict=[False, False]))


def test_halt_mark_uses_only_past_trade_and_never_creates_entry():
    r = row()
    cap, status, date = diagnostic_cap(r, pd.Timestamp('2025-06-30'), bars())
    assert np.isclose(cap, 3805.)
    assert date == pd.Timestamp('2025-06-27')
    assert status == 'DOCUMENTED_HALT_LAST_TRADE_MARK_ONLY'
    assert pd.isna(r.cap) and pd.isna(r.entry_open)


def test_future_quote_change_cannot_change_halt_valuation():
    b = bars()
    a = diagnostic_cap(row(), pd.Timestamp('2025-06-30'), b)
    b.loc[1, 'close'] = 999999.
    assert diagnostic_cap(row(), pd.Timestamp('2025-06-30'), b) == a


def test_unknown_gap_without_document_is_still_unknown():
    cap, status, date = diagnostic_cap(row(), pd.Timestamp('2025-06-30'), bars(), evidence={})
    assert pd.isna(cap) and pd.isna(date)
    assert status == 'UNKNOWN_NO_APPROVED_VALUATION_EVIDENCE'


def test_halt_rule_does_not_extend_beyond_resume_date():
    cap, status, date = diagnostic_cap(row(), pd.Timestamp('2025-07-11'), bars())
    assert pd.isna(cap) and status == 'OUTSIDE_DOCUMENTED_HALT'
