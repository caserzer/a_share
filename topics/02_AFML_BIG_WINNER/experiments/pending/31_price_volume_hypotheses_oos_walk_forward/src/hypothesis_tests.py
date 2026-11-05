"""Post-freeze evaluation: date clusters, monthly moments, paired diagnostics."""
import numpy as np
import pandas as pd

from baselines import prediction_loss
from multiple_testing import infer_effect


def date_statistics(frame, endpoint):
    f = frame.loc[frame.y.notna() & frame.applicable].copy()
    if f.empty:
        return pd.DataFrame()
    f["residual"] = f.y-f.baseline
    f["xc"] = f.partial_x-f.groupby("date").partial_x.transform("mean")
    f["yc"] = f.residual-f.groupby("date").residual.transform("mean")
    f["numerator"] = f.xc*f.yc
    f["denominator"] = f.xc*f.xc
    f["base_loss"] = prediction_loss(f.y, f.baseline, endpoint)
    f["aug_loss"] = prediction_loss(f.y, f.augmented, endpoint)
    f["loss_gain"] = f.base_loss-f.aug_loss
    for prefix, base, aug in [("shuffle", "baseline", "shuffled_augmented"),
                              ("permlabel", "label_permuted_base", "label_permuted_augmented"),
                              ("lag", "lagged_base", "lagged_augmented")]:
        if aug in f:
            f[prefix+"_gain"] = prediction_loss(f.y, f[base], endpoint)-prediction_loss(f.y, f[aug], endpoint)
            if prefix == "lag":
                f.loc[~f.lag_available, prefix+"_gain"] = np.nan
    fields = ["numerator", "denominator", "base_loss", "aug_loss", "loss_gain"] + [c for c in f if c.endswith("_gain") and c != "loss_gain"]
    result = f.groupby("date")[fields].mean()
    result["rows"] = f.groupby("date").size()
    rank_x = f.groupby("date").factor_raw.rank()
    rank_y = f.groupby("date").residual.rank()
    centered_x = rank_x-rank_x.groupby(f.date).transform("mean")
    centered_y = rank_y-rank_y.groupby(f.date).transform("mean")
    ic = pd.DataFrame(dict(date=f.date, xy=centered_x*centered_y, xx=centered_x**2, yy=centered_y**2)).groupby("date").sum()
    result["rank_ic"] = ic.xy/np.sqrt(ic.xx*ic.yy).replace(0, np.nan)
    sorts = f.groupby(["date", "sort_group"]).residual.mean().unstack("sort_group")
    result["high_minus_low"] = sorts.get(1, np.nan)-sorts.get(-1, np.nan)
    result["y_mean"] = f.groupby("date").y.mean()
    result["y_median"] = f.groupby("date").y.median()
    result["worst_5pct"] = f.groupby("date").y.quantile(0.05)
    if "value" in f:
        result["return_skew"] = f.groupby("date").value.skew()
    if endpoint == "log_variance_mse":
        variance = np.exp(f.y).clip(lower=1e-12)
        pb = np.exp(np.clip(f.baseline, -30, 20))
        pa = np.exp(np.clip(f.augmented, -30, 20))
        f["qlike_gain"] = (variance/pb+np.log(pb))-(variance/pa+np.log(pa))
        result["qlike_gain"] = f.groupby("date").qlike_gain.mean()
    return result.reset_index()


def monthly_statistics(frame, endpoint):
    daily = date_statistics(frame, endpoint)
    if daily.empty:
        return daily
    return daily.groupby(daily.date.dt.to_period("M")).mean(numeric_only=True).reset_index().rename(columns={"date": "month"})


def summarize(frame, spec):
    months = monthly_statistics(frame, spec["endpoint"])
    ratio = spec["endpoint"] == "adjusted_return"
    direction = spec["direction"] if ratio else 1
    result = infer_effect(months, direction, ratio) if len(months) else dict(estimate=None, ci_low=None, ci_high=None, p_one_sided=None, months=0)
    result.update(rows=int(frame.y.notna().sum()), total_rows=len(frame), unknown=int(frame.y.isna().sum()))
    for field in ["rank_ic", "high_minus_low", "base_loss", "aug_loss", "qlike_gain", "y_mean", "y_median", "worst_5pct", "return_skew"]:
        result[field] = float(months[field].mean()) if field in months and months[field].notna().any() else None
    return result, months
