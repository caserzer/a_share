import os
import numpy as np
import pandas as pd


def calculate_log_high_low_range_1d():
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
        & (high > low)
    )

    session_range = pd.Series(np.nan, index=data.index, dtype=np.float64)
    session_range.loc[valid] = (
        np.log(high.loc[valid]) - np.log(low.loc[valid])
    )

    factor = session_range.groupby(
        level="instrument", sort=False
    ).shift(1)

    result = factor.to_frame(name="Log_High_Low_Range_1D")
    result = result.sort_index(level=["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_log_high_low_range_1d()
