from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Downside_Volatility_20D_Lag1"
RETURN_WINDOW = 20
REQUIRED_CLOSE_WINDOW = 21
SIGNAL_DATA_LAG = 1


def calculate_downside_volatility_20d_lag1() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    close = data["$close"].astype("float64")

    valid_close = close.gt(0.0) & np.isfinite(close)
    safe_close = close.where(valid_close)

    log_close = np.log(safe_close)
    log_return = log_close.groupby(level="instrument", sort=False).diff()
    downside_squared = log_return.clip(upper=0.0).pow(2)

    lagged_downside_squared = downside_squared.groupby(
        level="instrument", sort=False
    ).shift(SIGNAL_DATA_LAG)

    mean_downside_squared = lagged_downside_squared.groupby(
        level="instrument", sort=False
    ).transform(
        lambda values: values.rolling(
            window=RETURN_WINDOW,
            min_periods=RETURN_WINDOW,
        ).mean()
    )

    lagged_valid_close = valid_close.groupby(
        level="instrument", sort=False
    ).shift(SIGNAL_DATA_LAG)

    valid_close_count = lagged_valid_close.groupby(
        level="instrument", sort=False
    ).transform(
        lambda values: values.rolling(
            window=REQUIRED_CLOSE_WINDOW,
            min_periods=REQUIRED_CLOSE_WINDOW,
        ).sum()
    )

    downside_volatility = np.sqrt(mean_downside_squared)
    downside_volatility = downside_volatility.where(
        valid_close_count.eq(REQUIRED_CLOSE_WINDOW)
    )

    result = downside_volatility.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_downside_volatility_20d_lag1()
