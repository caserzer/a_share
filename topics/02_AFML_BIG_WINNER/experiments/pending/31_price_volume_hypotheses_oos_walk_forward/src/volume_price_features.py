"""Causal daily features from a single security's sealed bars only."""
from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-12
FACTOR_COLUMNS = ["atr", "mavd", "abnormal_volume", "relative_volume", "trend_decay"]


def clean_field(b, field):
    a = pd.to_numeric(b[field], errors="coerce").astype(float)
    conflict = b.get(field.removeprefix("qfq_") + "_conflict", pd.Series(False, index=b.index))
    a = a.mask(conflict.astype("boolean").fillna(True).astype(bool))
    return a.where(np.isfinite(a))


def build_features(bars, days):
    if bars.date.duplicated().any():
        raise ValueError("duplicate bar dates")
    b = bars.set_index("date").reindex(days).copy()
    # No imputation of price/volume/turnover across suspended or missing dates.
    close = clean_field(b, "qfq_close").where(lambda x: x > 0)
    raw_close = clean_field(b, "close").where(lambda x: x > 0)
    raw_open, high, low = [clean_field(b, k) for k in ["open", "high", "low"]]
    vol = clean_field(b, "volume").where(lambda x: x > 0)
    turnover = clean_field(b, "turnover_rate").where(lambda x: x > 0)
    money = clean_field(b, "money").where(lambda x: x > 0)
    lr = np.log(close / close.shift())
    # A discontinuous, unreconciled identity/factor chain cannot define returns.
    if "factor_chain_id" in b:
        lr = lr.where(b.factor_chain_id.eq(b.factor_chain_id.shift()))
    ret = close / close.shift() - 1
    out = pd.DataFrame(index=days)
    out["observed"] = raw_close.notna() & vol.notna()
    out["valid_count"] = out.observed.cumsum()
    out["warmup"] = out.valid_count.ge(250)
    for n in [20, 60, 120]:
        out[f"mom{n}"] = close / close.shift(n) - 1
        if "factor_chain_id" in b:
            out[f"mom{n}"] = out[f"mom{n}"].where(b.factor_chain_id.eq(b.factor_chain_id.shift(n)))
    for n in [5, 20, 60]:
        out[f"rv{n}"] = lr.pow(2).rolling(n, min_periods=n).mean()
    out["atr"] = turnover.rolling(20).mean() / turnover.rolling(250).mean()
    out["mavd"] = vol.rolling(21).mean() / vol.rolling(200).mean() - 1
    out["mavd_turnover"] = turnover.rolling(21).mean() / turnover.rolling(200).mean() - 1
    out["relative_volume"] = vol / vol.rolling(20).mean()
    out["abnormal_volume"] = np.log(out.relative_volume)
    out["relative_turnover"] = turnover / turnover.rolling(20).mean()
    out["turnover20"] = turnover.rolling(20).mean()
    out["log_turnover"] = np.log(turnover)
    out["log_money"] = np.log(money)
    out["log_float_cap_proxy"] = np.log(raw_close * vol / turnover)
    out["eff"] = (raw_close - raw_open).abs() / (high - low).clip(lower=EPS)
    out["amplitude"] = (high - low) / raw_close
    out["day_return"] = raw_close / raw_open - 1
    out["breakthrough_strength"] = close / close.shift().rolling(120).max() - 1
    if "factor_chain_id" in b:
        chain_codes = pd.Series(pd.factorize(b.factor_chain_id)[0], index=b.index).where(close.notna())
        chain_same = chain_codes.rolling(121, min_periods=1).max().eq(chain_codes.rolling(121, min_periods=1).min())
        out["breakthrough_strength"] = out.breakthrough_strength.where(chain_same)
    out["breakout"] = out.breakthrough_strength.gt(0) & out.warmup
    # slope of log(turnover), using a fixed centered time regressor.
    weights = np.arange(20, dtype=float) - 9.5
    slope = np.log(turnover).rolling(20).apply(lambda x: np.dot(x, weights) / np.dot(weights, weights), raw=True)
    out["turnover_slope"] = slope
    out["trend_decay"] = out.mom20.clip(lower=0) * (-slope).clip(lower=0)
    out["momentum_turnover"] = out.mom60 * out.turnover20  # replaced by train-only percentile at fit.
    out["high_turnover_low_eff"] = np.nan  # train-only quantiles at fit.
    out["vendor_st"] = pd.to_numeric(b.get("vendor_is_st", pd.Series(index=days, dtype=float)), errors="coerce")
    out["vendor_suspended"] = pd.to_numeric(b.get("vendor_trade_status", pd.Series(index=days, dtype=float)), errors="coerce").eq(0)
    divisor = pd.to_numeric(b.qfq_divisor, errors="coerce")
    jumps = divisor.div(divisor.shift()).sub(1).abs().gt(1e-8)
    out["factor_step_20"] = jumps.rolling(20, min_periods=1).max().astype(bool)
    out["factor_step_200"] = jumps.rolling(200, min_periods=1).max().astype(bool)
    float_shares = vol / turnover
    out["share_proxy_step_20"] = float_shares.pct_change(fill_method=None).abs().gt(0.10).rolling(20, min_periods=1).max().astype(bool)
    out["one_price_bar"] = high.eq(low) & high.notna()
    out["daily_log_return"] = lr
    out["date"] = days
    out["feature_start"] = pd.Series(days, index=days).shift(249)
    out["known_at"] = days + pd.Timedelta(hours=15)
    return out.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)
