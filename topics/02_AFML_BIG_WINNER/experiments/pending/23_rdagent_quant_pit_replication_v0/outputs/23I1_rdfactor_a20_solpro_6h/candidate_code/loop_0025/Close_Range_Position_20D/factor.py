from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Close_Range_Position_20D"
RANGE_WINDOW = 20


def calculate_close_range_position_20d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")
    close = data["$close"].astype("float64")

    high_valid = np.isfinite(high) & (high > 0.0)
    low_valid = np.isfinite(low) & (low > 0.0)
    close_valid = np.isfinite(close) & (close > 0.0)

    valid_high = high.where(high_valid)
    valid_low = low.where(low_valid)

    rolling_high_max = valid_high.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=RANGE_WINDOW,
            min_periods=RANGE_WINDOW,
        ).max()
    )

    rolling_low_min = valid_low.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=RANGE_WINDOW,
            min_periods=RANGE_WINDOW,
        ).min()
    )

    price_range = rolling_high_max.sub(rolling_low_min)
    range_valid = np.isfinite(price_range) & (price_range > 0.0)
    extrema_valid = np.isfinite(rolling_high_max) & np.isfinite(rolling_low_min)
    factor_valid = close_valid & extrema_valid & range_valid

    factor = close.sub(rolling_low_min).div(price_range).where(factor_valid)
    factor = factor.where(np.isfinite(factor))

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_close_range_position_20d()
