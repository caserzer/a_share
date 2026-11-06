from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import core


def test_taxonomy_is_not_backcast_and_transition_is_explicit():
    assert core.era_for_month('2017-01') == 'SW2014'
    assert core.era_for_month('2021-11') == 'SW2014'
    assert core.era_for_month('2021-12') is None
    assert core.era_for_month('2022-01') == 'SW2021'


def test_from_first_month_differs_from_late_recovery():
    assert core.prefix_length([False, True, True, True]) == 0
    assert core.v1.longest_true([False, True, True, True]) == 3


def fixture_score(monkeypatch, missing_middle=False, missing_benchmark=False):
    monkeypatch.setattr(core, 'detail', lambda *a: None)
    months = pd.period_range('2017-01', periods=13, freq='M')
    rows = []
    for i, sid in enumerate(['a', 'b', 'c', 'd', 'e']):
        for m in months:
            price = [130., 115., 90., 120., 110.][i]
            if missing_middle and sid == 'c' and m == months[4]:
                price = np.nan
            rows.append(dict(month=m, security_id=sid, qfq_close=price, close_chain='chain',
                entry_open=100., entry_chain='chain', instrument=sid, name=sid,
                cap=100. - 10 * i, unresolved=0, level='L2', era='SW2014',
                industry_code='industry', industry_name='Industry'))
    panel = pd.DataFrame(rows)
    joined = panel[panel.month.eq(months[0])].copy()
    origins = pd.DataFrame([dict(era='SW2014', level='L2', industry_code='industry',
        month=months[0], benchmark=b, entry_event=True, leader=1.) for b in core.BENCHMARKS])
    futures = {}
    for b in core.BENCHMARKS:
        value = np.full(12, .2)
        if missing_benchmark:
            value[8] = np.nan
        futures[(b, months[0])] = (value, np.isfinite(value).astype(float))
    return core.score(joined, origins, panel, futures)[0]


def test_average_profit_does_not_imply_all_three_beat_market(monkeypatch):
    r = fixture_score(monkeypatch).iloc[0]
    assert r.mean_return == pytest.approx((.30 + .15 - .10) / 3)
    assert r.portfolio_excess == pytest.approx((.30 + .15 - .10) / 3 - .20)
    assert r.worst_excess == pytest.approx(-.30)
    assert not r.all_beat and not r.all_positive
    assert r.top3 == 'a;b;c'


def test_unknown_middle_path_keeps_known_terminal_but_no_duration(monkeypatch):
    r = fixture_score(monkeypatch, missing_middle=True).iloc[0]
    assert r.complete
    assert not r.path_complete
    assert pd.isna(r.joint_excess_run)


def test_missing_index_is_unknown_not_market_zero(monkeypatch):
    r = fixture_score(monkeypatch, missing_benchmark=True)
    nine = r[r.horizon.eq(9)].iloc[0]
    assert nine.mature and not nine.complete
    assert nine.status == 'UNKNOWN'
    assert pd.isna(nine.portfolio_excess) and pd.isna(nine.all_beat)
