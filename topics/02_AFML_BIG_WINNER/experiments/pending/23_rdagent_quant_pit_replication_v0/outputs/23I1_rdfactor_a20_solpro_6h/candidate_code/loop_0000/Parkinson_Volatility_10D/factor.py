import os
import numpy as np
import pandas as pd


def calculate_parkinson_volatility_10d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["instrument", "datetime"])

    high = data["$high"].astype(np.float64)
    low = data["$low"].astype(np.float64)

    valid = (
        high.notna()
        & low.notna()
        & np.isfinite(high)
        & np.isfinite(low)
        & (high > 0.0)
        & (low > 0.0)
    )

    log_range = pd.Series(np.nan, index=data.index, dtype=np.float64)
    log_range.loc[valid] = np.log(high.loc[valid]) - np.log(low.loc[valid])
    squared_log_range = log_range.pow(2)

    rolling_mean = squared_log_range.groupby(
        level="instrument", sort=False
    ).transform(
        lambda values: values.rolling(window=10, min_periods=10).mean()
    )

    factor = np.sqrt(rolling_mean / (4.0 * np.log(2.0)))
    result = factor.to_frame(name="Parkinson_Volatility_10D")
    result = result.sort_index(level=["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_parkinson_volatility_10d()
