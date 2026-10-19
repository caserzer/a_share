import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from hierarchical_probabilities import sign_classes, conditional_magnitudes, assemble_classes, stable_sign_scores
from run_direct_probability import weighted_stats


def test_zero_sign_separate_and_unobserved_label_rejected():
    np.testing.assert_array_equal(sign_classes([-.1, 0., .1]), [0, 1, 2])
    with pytest.raises(ValueError): sign_classes([np.nan])


def test_changed_magnitudes_preserve_shared_sign_probabilities():
    s = np.array([[.4, .1, .5], [.5, 0., .5]])
    a = assemble_classes(s, [[.2, .3, .5]]*2, [[.6, .3, .1]]*2)
    b = assemble_classes(s, [[.8, .1, .1]]*2, [[.1, .2, .7]]*2)
    for p in [a, b]:
        np.testing.assert_allclose(p[:, :3].sum(axis=1), s[:, 0])
        np.testing.assert_array_equal(p[:, 3], s[:, 1])
        np.testing.assert_allclose(p[:, 4:].sum(axis=1), s[:, 2])
    assert not np.allclose(a, b)


def test_absent_flat_sign_uses_only_training_prior():
    flat = np.array([[0., 0., 0., .1, .3, .3, .3]])
    prior = np.array([.1, .2, .3, .1, .1, .1, .1])
    neg, pos = conditional_magnitudes(flat, prior)
    np.testing.assert_allclose(neg, [[1/6, 2/6, 3/6]])
    np.testing.assert_allclose(pos, [[1/3]*3])
    result = assemble_classes([[.5, .1, .4]], neg, pos)
    np.testing.assert_allclose(result.sum(axis=1), 1)


def test_analytic_sign_marginals_agree_with_atom_distribution_and_preserve_ties():
    sign = np.array([[.5, 0., .5], [.4, .1, .5]])
    p = assemble_classes(sign, [[.1, .2, .7]]*2, [[.3, .2, .5]]*2)
    atoms = np.tile([-.3, -.1, -.02, 0., .02, .1, .3], (2, 1))
    raw = weighted_stats(atoms, p, [0., np.nan])
    stable = stable_sign_scores(raw, sign, sign, 1., [0., np.nan])
    np.testing.assert_allclose(stable[['p_up', 'p_down', 'p_zero']], raw[['p_up', 'p_down', 'p_zero']], atol=1e-14)
    assert stable.p_up.iloc[0] == stable.p_down.iloc[0]
    assert not (stable.p_up > stable.p_down).iloc[0]
    assert pd.isna(stable.brier.iloc[1])
    np.testing.assert_allclose(stable.brier.iloc[0], .25)
