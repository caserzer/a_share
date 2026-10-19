"""Small, regularized calibrators fitted only on already matured predictions."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax
from run_direct_probability import classes
from run_prequential_search import combine_distributions

IDENTITY = np.r_[1., np.zeros(7)]
PENALTY = .01


def class_probabilities(frame):
    p = np.column_stack([frame.p_loss_over20, frame.p_loss5_20,
        frame.p_down-frame.p_loss_over20-frame.p_loss5_20, frame.p_zero,
        frame.p_up-frame.p_gain5_20-frame.p_gain_over20, frame.p_gain5_20, frame.p_gain_over20])
    assert np.isfinite(p).all() and p.min() >= -1e-10
    p = np.maximum(p, 0); p /= p.sum(axis=1, keepdims=True)
    return p


def calibration_history(predictions, date, window=None):
    history = predictions[(predictions.date < date) & (predictions.label_end < date) & predictions.actual.notna()]
    if window is not None:
        dates = sorted(history.date.unique())[-window:]
        history = history[history.date.isin(dates)]
    return history


def monthly_weights(dates):
    dates = pd.Series(np.asarray(dates))
    weights = 1/dates.groupby(dates).transform('size').to_numpy()
    return weights/weights.sum()


def transform(probabilities, parameters):
    logs = np.log(np.clip(probabilities, 1e-6, 1.))
    return softmax(parameters[0]*logs+parameters[1:], axis=1)


def fit_calibrator(probabilities, labels, dates):
    logs = np.log(np.clip(probabilities, 1e-6, 1.)); weights = monthly_weights(dates)
    def objective(parameters):
        logits = parameters[0]*logs+parameters[1:]
        loss = np.sum(weights*(logsumexp(logits, axis=1)-logits[np.arange(len(labels)), labels]))
        delta = parameters-IDENTITY; loss += PENALTY*np.dot(delta, delta)
        residual = softmax(logits, axis=1); residual[np.arange(len(labels)), labels] -= 1
        residual *= weights[:, None]
        gradient = np.r_[(residual*logs).sum(), residual.sum(axis=0)] + 2*PENALTY*delta
        return loss, gradient
    fit = minimize(objective, IDENTITY.copy(), jac=True, method='L-BFGS-B',
        bounds=[(.25, 4.)]+[(-2., 2.)]*7, options=dict(maxiter=300, ftol=1e-12, gtol=1e-7))
    if not fit.success:
        raise RuntimeError(f'Calibration failed: {fit.message}')
    assert fit.fun <= objective(IDENTITY)[0]+1e-8
    return fit.x, dict(iterations=int(fit.nit), penalized_loss=float(fit.fun),
        identity_penalized_loss=float(objective(IDENTITY)[0]))


def replace_class_mass(atoms, weights, target, backup_atoms):
    labels = classes(atoms)
    mass = np.column_stack([(weights*(labels == k)).sum(axis=1) for k in range(7)])
    row_mass = np.take_along_axis(mass, labels, axis=1)
    conditional = np.divide(weights, row_mass, out=np.zeros_like(weights), where=row_mass > 0)
    updated = conditional*np.take_along_axis(target, labels, axis=1)
    missing = np.where(mass == 0, target, 0)
    if missing.any():
        backup = np.broadcast_to(backup_atoms, (len(atoms), len(backup_atoms)))
        np.testing.assert_array_equal(classes(backup_atoms), np.repeat(np.arange(7), 32))
        return combine_distributions([(atoms, updated), (backup, np.repeat(missing/32, 32, axis=1))], [1., 1.])
    np.testing.assert_allclose(updated.sum(axis=1), 1, atol=1e-10)
    return atoms, updated


def fit_mixture(probabilities, labels, dates):
    """Simplex mixture of B and two frozen streams, with a fixed B prior."""
    weights = monthly_weights(dates); prior = np.array([1., 0., 0.])
    target = np.eye(7)[labels]
    def objective(coefficients):
        prediction = np.einsum('nmc,m->nc', probabilities, coefficients)
        residual = prediction-target; delta = coefficients-prior
        loss = np.sum(weights[:, None]*residual**2)+PENALTY*np.dot(delta, delta)
        gradient = 2*np.einsum('nmc,nc,n->m', probabilities, residual, weights)+2*PENALTY*delta
        return loss, gradient
    fit = minimize(objective, prior.copy(), jac=True, method='SLSQP', bounds=[(0., 1.)]*3,
        constraints=[dict(type='eq', fun=lambda x: x.sum()-1, jac=lambda x: np.ones(3))],
        options=dict(maxiter=200, ftol=1e-12))
    if not fit.success:
        raise RuntimeError(f'Mixture fit failed: {fit.message}')
    coefficients = np.maximum(fit.x, 0); coefficients /= coefficients.sum()
    assert objective(coefficients)[0] <= objective(prior)[0]+1e-8
    return coefficients
