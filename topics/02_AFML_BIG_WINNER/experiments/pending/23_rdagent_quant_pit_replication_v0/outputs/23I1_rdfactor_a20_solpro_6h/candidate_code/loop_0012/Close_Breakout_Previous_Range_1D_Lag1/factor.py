from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Close_Breakout_Previous_Range_1D_Lag1"
LOOKBACK = 1
SIGNAL_LAG = 1


def calculate_close_breakout_previous_range_1d_lag1() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()

    close = data["$close"].astype("float64")
    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")

    previous_high = high.groupby(level="instrument", sort=False).shift(LOOKBACK)
    previous_low = low.groupby(level="instrument", sort=False).shift(LOOKBACK)

    valid = (
        np.isfinite(close)
        & np.isfinite(previous_high)
        & np.isfinite(previous_low)
        & (close > 0.0)
        & (previous_high > 0.0)
        & (previous_low > 0.0)
        & (previous_high > previous_low)
    )

    source_signal = pd.Series(np.nan, index=data.index, dtype="float64")
    source_signal.loc[valid] = 0.0
    source_signal.loc[valid & (close > previous_high)] = 1.0
    source_signal.loc[valid & (close < previous_low)] = -1.0

    factor = source_signal.groupby(level="instrument", sort=False).shift(SIGNAL_LAG)

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_close_breakout_previous_range_1d_lag1()
