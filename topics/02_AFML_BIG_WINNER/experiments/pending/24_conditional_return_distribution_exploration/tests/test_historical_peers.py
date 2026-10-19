import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from build_historical_peers import formation_history
from probe_lagged_peer_information import peer_features


def fixture():
    rng = np.random.default_rng(24)
    dates = pd.bdate_range('2019-01-01', periods=420)
    groups = rng.normal(0, .01, (420, 2))
    returns = np.repeat(groups, 13, axis=1)+rng.normal(0, .0005, (420, 26))
    names = [f's{i:02d}' for i in range(26)]
    daily = pd.DataFrame(returns, index=dates, columns=names)
    current = pd.DataFrame({f'mom{n}': np.ones(26) for n in [21, 63, 126]}, index=names)
    return daily, current


def test_future_bars_do_not_change_past_peer_features():
    daily, current = fixture(); date = daily.index[350]
    a = peer_features(formation_history(daily, date, current.index, 0), current)
    changed = daily.copy(); changed.loc[changed.index > date] *= -100
    b = peer_features(formation_history(changed, date, current.index, 0), current)
    pd.testing.assert_frame_equal(a, b)


def test_gap63_excludes_the_recent_63_return_observations():
    daily, current = fixture(); date = daily.index[-1]
    a = formation_history(daily, date, current.index, 63)
    assert len(a) == 252 and a.index.max() == daily.index[-64]
    changed = daily.copy(); changed.iloc[-63:] *= -50
    b = formation_history(changed, date, current.index, 63)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(peer_features(a, current), peer_features(b, current))


def test_own_extreme_momentum_not_in_its_peer_mean_and_short_history_missing():
    daily, current = fixture(); stock = current.index[0]
    current.loc[stock, ['mom21', 'mom63', 'mom126']] = 99
    result = peer_features(daily.tail(252), current)
    assert stock not in result.loc[stock, 'peer_instruments'].split(';')
    assert result.loc[stock, 'available']
    np.testing.assert_allclose(result.loc[stock, ['peer_mom21', 'peer_mom63', 'peer_mom126']].astype(float), 1.)
    short = peer_features(daily.head(20), current)
    assert short.neighbors.eq(0).all() and short.peer_mom21.isna().all()
