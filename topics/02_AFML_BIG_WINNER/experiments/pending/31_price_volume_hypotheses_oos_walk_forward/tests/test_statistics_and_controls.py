import numpy as np
import pandas as pd

from multiple_testing import bh, infer_effect, stationary_indices
from walk_forward import permute_within_date_board


def test_bh_keeps_blocked_hypothesis_out_of_family():
    actual = bh([0.01, 0.04, 0.03, np.nan])
    np.testing.assert_allclose(actual[:3], [0.03, 0.04, 0.04])
    assert np.isnan(actual[3])


def test_time_bootstrap_uses_one_draw_for_both_paired_moments():
    n = 72
    f = pd.DataFrame(dict(numerator=np.arange(n)+1., denominator=(np.arange(n)+1.)*2))
    result = infer_effect(f, direction=1, ratio=True)
    assert result["estimate"] == 0.5
    assert result["ci_low"] == 0.5
    assert result["ci_high"] == 0.5
    assert result["p_one_sided"] < 0.01


def test_positive_control_and_wrong_direction_distinguished():
    f = pd.DataFrame({"loss_gain": np.random.default_rng(31).normal(1, 0.1, 72)})
    assert infer_effect(f)["p_one_sided"] < 0.01
    assert infer_effect(f, direction=-1)["p_one_sided"] > 0.9


def test_zero_effect_is_not_significant():
    f = pd.DataFrame({"loss_gain": np.zeros(72)})
    result = infer_effect(f)
    assert result["estimate"] == 0
    assert result["p_one_sided"] == 1


def test_stationary_blocks_retain_adjacent_months():
    a = stationary_indices(100, replicates=100)
    continuation = (a[:, 1:] == ((a[:, :-1]+1) % 100)).mean()
    assert 0.75 < continuation < 0.9


def test_permutation_preserves_each_date_board_population():
    f = pd.DataFrame(dict(date=[1]*8+[2]*8, board=["A"]*4+["B"]*4+["A"]*4+["B"]*4, factor=np.arange(16)))
    shuffled = permute_within_date_board(f, "factor", np.random.default_rng(31))
    for indices in f.groupby(["date", "board"]).indices.values():
        np.testing.assert_array_equal(np.sort(shuffled[indices]), f.factor.iloc[indices])
    assert not np.array_equal(shuffled, f.factor)


def test_model_positive_and_negative_controls():
    from baselines import Ridge
    rng = np.random.default_rng(31)
    x = pd.DataFrame({'signal':rng.normal(size=5000), 'nuisance':rng.normal(size=5000)})
    dates = pd.date_range('2017-01-01', periods=5000)
    y = 2*x.signal+rng.normal(0,0.1,5000)
    model = Ridge().fit(x.iloc[:4000],y.iloc[:4000],dates[:4000],1)
    pred=model.predict(x.iloc[4000:])
    assert np.corrcoef(pred,y.iloc[4000:])[0,1] > 0.99
    noise=rng.normal(size=5000)
    negative=Ridge().fit(x.iloc[:4000],noise[:4000],dates[:4000],1)
    assert abs(np.corrcoef(negative.predict(x.iloc[4000:]),noise[4000:])[0,1]) < 0.10
