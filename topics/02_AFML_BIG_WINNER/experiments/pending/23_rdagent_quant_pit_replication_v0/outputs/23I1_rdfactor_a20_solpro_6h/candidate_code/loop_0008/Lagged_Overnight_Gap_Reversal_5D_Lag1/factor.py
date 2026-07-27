import os
import numpy as np
import pandas as pd


def calculate_lagged_overnight_gap_reversal_5d_lag1():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    original_index = data.index
    data = data.sort_index(level=["instrument", "datetime"])

    open_price = data["$open"].astype("float64")
    close_price = data["$close"].astype("float64")

    preceding_close = close_price.groupby(level="instrument", sort=False).shift(1)

    valid_gap = (
        np.isfinite(open_price)
        & np.isfinite(preceding_close)
        & (open_price > 0.0)
        & (preceding_close > 0.0)
    )
    overnight_gap_return = (open_price / preceding_close - 1.0).where(valid_gap, np.nan)

    lagged_gap = overnight_gap_return.groupby(level="instrument", sort=False).shift(1)
    five_day_mean = lagged_gap.groupby(level="instrument", sort=False).transform(
        lambda values: values.rolling(window=5, min_periods=5).mean()
    )
    factor = (-five_day_mean).astype("float64")

    result = factor.to_frame(name="Lagged_Overnight_Gap_Reversal_5D_Lag1")
    result = result.reindex(original_index)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_lagged_overnight_gap_reversal_5d_lag1()
