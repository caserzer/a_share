import numpy as np
import pytest
from sklearn.ensemble import ExtraTreesRegressor
from probability_loss_forests import loss_targets, leaf_means, leaf_probabilities


def test_normalized_joint_loss_has_equal_unconditional_contributions():
    y = np.array([-.4, -.2, -.05, -.001, 0, .001, .05, .2, 1.]); w = np.arange(1., 10)
    t, meta = loss_targets(y, w, 'joint'); normalized = w/w.sum()
    errors = normalized@((t-normalized@t)**2)
    np.testing.assert_allclose([errors[0], errors[1:6].sum(), errors[6:].sum()], [1, 1, 1])
    unscaled = t/meta['scales']
    np.testing.assert_array_equal(unscaled[:, 0], y > 0)
    assert unscaled[1, 2] == 1 and unscaled[2, 3] == 1 and unscaled[-2, 5] == 1
    assert np.all(np.diff(unscaled[:, 6:], axis=1) >= 0)
    assert meta['widths'].sum() == pytest.approx(y.max()-y.min())


def test_leaf_probability_uses_weights_and_preserves_zero():
    tr = np.array([[1, 1], [1, 1], [2, 1]]); te = np.array([[1, 1], [2, 1]])
    p = leaf_probabilities(tr, te, [-.3, 0, .3], [1., 3., 6.])
    np.testing.assert_allclose(p[0, [0, 3, 6]], [.175, .525, .3])
    np.testing.assert_allclose(p[1, [0, 3, 6]], [.05, .15, .8])


@pytest.mark.parametrize('kind', ['ordinal', 'joint'])
def test_sklearn_multioutput_leaf_reconstruction(kind):
    rng = np.random.default_rng(24); x = rng.normal(size=(80, 3)); y = np.round(x[:, 0]/5, 1)
    w = np.linspace(.2, 2, 80); t, meta = loss_targets(y, w, kind)
    m = ExtraTreesRegressor(n_estimators=5, max_depth=3, min_samples_leaf=3, bootstrap=False, random_state=24)
    m.fit(x, t, sample_weight=w); query = rng.normal(size=(7, 3))
    tr, te = m.apply(x), m.apply(query)
    np.testing.assert_allclose(leaf_means(tr, te, t, w), m.predict(query), atol=1e-12)
    p = leaf_probabilities(tr, te, y, w)
    if kind == 'ordinal': np.testing.assert_allclose(p.cumsum(axis=1)[:, :6], m.predict(query), atol=1e-12)
    else:
        expected = np.column_stack([p[:, 4:].sum(axis=1), p[:, 0], p[:, 1], p[:, 2:5].sum(axis=1), p[:, 5], p[:, 6]])
        np.testing.assert_allclose(expected, m.predict(query)[:, :6]/meta['scales'][:6], atol=1e-12)
    np.testing.assert_allclose(p.sum(axis=1), 1)


def test_training_grid_constant_labels_and_invalid_input():
    t, meta = loss_targets(np.zeros(12), np.ones(12), 'joint')
    assert np.isfinite(t).all() and len(meta['grid']) == 0
    with pytest.raises(ValueError): loss_targets([np.nan], [1], 'joint')
    with pytest.raises(ValueError): loss_targets([.1], [0], 'joint')
    with pytest.raises(ValueError): leaf_means(np.array([[1]]), np.array([[2]]), np.array([[1.]]), [1.])
