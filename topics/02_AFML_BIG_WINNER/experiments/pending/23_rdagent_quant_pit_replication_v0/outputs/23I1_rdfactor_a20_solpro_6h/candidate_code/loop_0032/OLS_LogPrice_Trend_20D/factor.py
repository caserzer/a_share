from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "OLS_LogPrice_Trend_20D"
REGRESSION_WINDOW = 20
TIME_INDEX_MEAN = 9.5
OLS_DENOMINATOR = 665.0
TREND_SPAN_MULTIPLIER = 19.0


def calculate_ols_logprice_trend_20d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    close = data["$close"].astype("float64")
    valid_close = close.where(np.isfinite(close) & (close > 0.0))
    log_close = np.log(valid_close)
    log_close = log_close.where(np.isfinite(log_close))

    centered_time_index = (
        np.arange(REGRESSION_WINDOW, dtype="float64") - TIME_INDEX_MEAN
    )

    rolling_numerator = log_close.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=REGRESSION_WINDOW,
            min_periods=REGRESSION_WINDOW,
        ).apply(
            lambda window_values: np.dot(centered_time_index, window_values),
            raw=True,
        )
    )

    slope = rolling_numerator.div(OLS_DENOMINATOR)
    factor = slope.mul(TREND_SPAN_MULTIPLIER)
    factor = factor.where(
        np.isfinite(rolling_numerator)
        & np.isfinite(slope)
        & np.isfinite(factor)
    )

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_ols_logprice_trend_20d()
