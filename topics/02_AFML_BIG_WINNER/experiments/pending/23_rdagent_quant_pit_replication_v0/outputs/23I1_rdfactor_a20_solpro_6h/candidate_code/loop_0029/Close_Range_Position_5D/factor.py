from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Close_Range_Position_5D"
RANGE_WINDOW = 5


def calculate_close_range_position_5d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")
    close = data["$close"].astype("float64")

    valid_high = high.where(np.isfinite(high) & (high > 0.0))
    valid_low = low.where(np.isfinite(low) & (low > 0.0))
    close_valid = np.isfinite(close) & (close > 0.0)

    rolling_max_high = valid_high.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=RANGE_WINDOW,
            min_periods=RANGE_WINDOW,
        ).max()
    )

    rolling_min_low = valid_low.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=RANGE_WINDOW,
            min_periods=RANGE_WINDOW,
        ).min()
    )

    envelope_width = rolling_max_high.sub(rolling_min_low)
    factor_valid = (
        close_valid
        & np.isfinite(rolling_max_high)
        & np.isfinite(rolling_min_low)
        & np.isfinite(envelope_width)
        & (envelope_width > 0.0)
    )

    factor = close.sub(rolling_min_low).div(envelope_width).where(factor_valid)
    factor = factor.where(np.isfinite(factor))

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_close_range_position_5d()
