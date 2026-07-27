from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Robust_CS_Overnight_Gap_ZScore_1D"
GAP_LOOKBACK = 1
MINIMUM_CROSS_SECTIONAL_OBSERVATIONS = 30
MAD_SCALE_CONSTANT = 1.4826
LOWER_CLIP_BOUND = -3.0
UPPER_CLIP_BOUND = 3.0


def _instrument_shift(series: pd.Series, periods: int) -> pd.Series:
    return series.groupby(level="instrument", sort=False).shift(periods)


def calculate_robust_cs_overnight_gap_zscore_1d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    open_price = data["$open"].astype("float64")
    close_price = data["$close"].astype("float64")
    previous_close = _instrument_shift(close_price, GAP_LOOKBACK)

    valid_prices = (
        np.isfinite(open_price)
        & (open_price > 0.0)
        & np.isfinite(previous_close)
        & (previous_close > 0.0)
    )

    raw_gap = open_price.div(previous_close).sub(1.0).where(valid_prices)
    raw_gap = raw_gap.where(np.isfinite(raw_gap))

    date_groups = raw_gap.groupby(level="datetime", sort=False)
    valid_count = date_groups.transform("count")
    cross_sectional_median = date_groups.transform("median")

    absolute_deviation = raw_gap.sub(cross_sectional_median).abs()
    mad = absolute_deviation.groupby(level="datetime", sort=False).transform(
        "median"
    )
    robust_scale = mad.mul(MAD_SCALE_CONSTANT)

    eligible_date = (
        (valid_count >= MINIMUM_CROSS_SECTIONAL_OBSERVATIONS)
        & np.isfinite(mad)
        & (mad > 0.0)
        & np.isfinite(robust_scale)
        & (robust_scale > 0.0)
    )

    robust_zscore = raw_gap.sub(cross_sectional_median).div(robust_scale)
    factor = robust_zscore.where(
        raw_gap.notna() & eligible_date & np.isfinite(robust_zscore)
    )
    factor = factor.clip(
        lower=LOWER_CLIP_BOUND,
        upper=UPPER_CLIP_BOUND,
    ).astype("float64")

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_robust_cs_overnight_gap_zscore_1d()
