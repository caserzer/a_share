from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Continuous_Close_Breakout_Strength_1D_Lag1"
LOOKBACK_PERIOD = 1
SIGNAL_AVAILABILITY_LAG = 1
LOWER_CLIP_BOUND = -3.0
UPPER_CLIP_BOUND = 3.0


def calculate_continuous_close_breakout_strength_1d_lag1() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()

    close = data["$close"].astype("float64")
    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")

    previous_high = high.groupby(level="instrument", sort=False).shift(LOOKBACK_PERIOD)
    previous_low = low.groupby(level="instrument", sort=False).shift(LOOKBACK_PERIOD)
    previous_range = previous_high - previous_low

    valid = (
        np.isfinite(close)
        & np.isfinite(previous_high)
        & np.isfinite(previous_low)
        & (close > 0.0)
        & (previous_high > 0.0)
        & (previous_low > 0.0)
        & (previous_range > 0.0)
    )

    source_signal = pd.Series(np.nan, index=data.index, dtype="float64")

    inside_range = valid & (close >= previous_low) & (close <= previous_high)
    upper_breakout = valid & (close > previous_high)
    lower_breakout = valid & (close < previous_low)

    source_signal.loc[inside_range] = 0.0
    source_signal.loc[upper_breakout] = (
        (close.loc[upper_breakout] - previous_high.loc[upper_breakout])
        / previous_range.loc[upper_breakout]
    )
    source_signal.loc[lower_breakout] = (
        (close.loc[lower_breakout] - previous_low.loc[lower_breakout])
        / previous_range.loc[lower_breakout]
    )
    source_signal = source_signal.clip(
        lower=LOWER_CLIP_BOUND,
        upper=UPPER_CLIP_BOUND,
    )

    factor = source_signal.groupby(level="instrument", sort=False).shift(
        SIGNAL_AVAILABILITY_LAG
    )

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_continuous_close_breakout_strength_1d_lag1()
