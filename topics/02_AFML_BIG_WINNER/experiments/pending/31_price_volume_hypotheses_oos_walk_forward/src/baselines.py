"""Small weighted Ridge models with explicit train-only preprocessing receipts."""
from __future__ import annotations

import numpy as np
import pandas as pd

CONTROLS = ["mom20", "mom60", "rv5", "rv20", "rv60", "log_turnover", "log_float_cap_proxy",
            "log_money", "amplitude", "day_return", "breakthrough_strength", "market_mom20", "market_rv20"]


def date_weights(dates):
    series = pd.Series(np.asarray(dates))
    counts = series.map(series.value_counts()).to_numpy(float)
    w = 1 / counts
    return w / w.mean()


class Transform:
    def fit(self, frame):
        a = frame.to_numpy(float)
        self.columns = frame.columns.tolist()
        with np.errstate(all="ignore"):
            self.median = np.nanmedian(a, axis=0)
            self.low, self.high = np.nanquantile(a, [0.01, 0.99], axis=0)
        self.median = np.nan_to_num(self.median)
        self.low = np.where(np.isfinite(self.low), self.low, self.median)
        self.high = np.where(np.isfinite(self.high), self.high, self.median)
        z = np.clip(np.where(np.isfinite(a), a, self.median), self.low, self.high)
        self.mean, self.scale = z.mean(axis=0), z.std(axis=0)
        self.scale[self.scale < 1e-12] = 1.0
        return self

    def apply(self, frame):
        a = frame[self.columns].to_numpy(float)
        missing = ~np.isfinite(a)
        z = np.clip(np.where(missing, self.median, a), self.low, self.high)
        return np.c_[np.ones(len(a)), (z-self.mean)/self.scale, missing.astype(float)]

    def record(self):
        return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in vars(self).items()}


class Ridge:
    def fit(self, frame, y, dates, alpha=1.0):
        self.transform = Transform().fit(frame)
        x = self.transform.apply(frame)
        w = date_weights(dates)
        gram = x.T @ (x*w[:, None])
        penalty = np.eye(x.shape[1])*alpha
        penalty[0, 0] = 0
        self.coef = np.linalg.solve(gram + penalty + np.eye(x.shape[1])*1e-10, x.T @ (np.asarray(y)*w))
        self.alpha = float(alpha)
        return self

    def predict(self, frame):
        return self.transform.apply(frame) @ self.coef

    def record(self):
        return dict(alpha=self.alpha, transform=self.transform.record(), coef=self.coef.tolist())


class HypothesisTransform:
    """Thresholds and H03 percentile reference are learned exclusively from train."""
    def fit(self, train):
        self.turnover_reference = np.sort(train.turnover20.dropna().to_numpy(float))
        self.turnover_high = float(train.relative_turnover.quantile(0.8))
        self.eff_low = float(train.eff.quantile(0.2))
        self.momentum_low = float(train.mom60.quantile(0.3))
        self.momentum_high = float(train.mom60.quantile(0.7))
        self.turn_low = float(train.turnover20.quantile(0.3))
        self.turn_high = float(train.turnover20.quantile(0.7))
        self.size_cut = train.log_float_cap_proxy.quantile([1/3, 2/3]).to_numpy(float)
        self.liquidity_cut = train.log_money.quantile([1/3, 2/3]).to_numpy(float)
        return self

    def apply(self, frame, hypothesis):
        f = frame.copy()
        f["high_turnover"] = f.relative_turnover.ge(self.turnover_high).astype(float)
        f["low_eff"] = f.eff.le(self.eff_low).astype(float)
        pct = np.searchsorted(self.turnover_reference, f.turnover20.to_numpy(float), side="right") / max(1, len(self.turnover_reference))
        pct[~np.isfinite(f.turnover20)] = np.nan
        f["turnover_percentile"] = pct
        f["momentum_turnover"] = f.mom60 * pct
        f["high_turnover_low_eff"] = f.high_turnover * f.low_eff
        f["momentum_group"] = np.select([f.mom60.le(self.momentum_low), f.mom60.ge(self.momentum_high)], [-1, 1], default=0)
        f["turnover_group"] = np.select([f.turnover20.le(self.turn_low), f.turnover20.ge(self.turn_high)], [-1, 1], default=0)
        f["size_group"] = np.select([f.log_float_cap_proxy.le(self.size_cut[0]), f.log_float_cap_proxy.ge(self.size_cut[1])], ["small", "large"], default="mid")
        f["liquidity_group"] = np.select([f.log_money.le(self.liquidity_cut[0]), f.log_money.ge(self.liquidity_cut[1])], ["low", "high"], default="mid")
        return f

    def controls(self, hypothesis):
        extra = ["high_turnover", "low_eff"] if hypothesis == "H10" else ["turnover_percentile"] if hypothesis == "H03" else []
        return CONTROLS + extra

    def record(self):
        # Exact empirical reference must be serialized for prediction replay.
        return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in vars(self).items()}


def prediction_loss(y, pred, endpoint):
    p = np.clip(pred, 0, 1) if endpoint == "downside_brier" else pred
    return (np.asarray(y) - p)**2
