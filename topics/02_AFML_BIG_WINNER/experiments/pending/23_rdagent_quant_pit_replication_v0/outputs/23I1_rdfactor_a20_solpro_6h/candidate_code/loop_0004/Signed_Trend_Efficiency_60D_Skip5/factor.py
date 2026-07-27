from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Signed_Trend_Efficiency_60D_Skip5"
HISTORY_WINDOW = 60
RECENT_SKIP = 5
PATH_RETURN_COUNT = 55


def calculate_signed_trend_efficiency_60d_skip5() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    close = data["$close"].astype("float64")

    valid_close = close.notna() & np.isfinite(close) & (close > 0.0)
    log_close = np.log(close.where(valid_close))

    grouped_log_close = log_close.groupby(level="instrument", sort=False)
    close_t_minus_5 = grouped_log_close.shift(RECENT_SKIP)
    close_t_minus_60 = grouped_log_close.shift(HISTORY_WINDOW)
    numerator = close_t_minus_5 - close_t_minus_60

    one_session_log_return = grouped_log_close.diff()
    skipped_absolute_return = one_session_log_return.abs().groupby(
        level="instrument", sort=False
    ).shift(RECENT_SKIP)
    denominator = skipped_absolute_return.groupby(
        level="instrument", sort=False
    ).transform(
        lambda values: values.rolling(
            window=PATH_RETURN_COUNT,
            min_periods=PATH_RETURN_COUNT,
        ).sum()
    )

    prior_valid = valid_close.groupby(level="instrument", sort=False).shift(1)
    valid_history_count = prior_valid.astype("float64").groupby(
        level="instrument", sort=False
    ).transform(
        lambda values: values.rolling(
            window=HISTORY_WINDOW,
            min_periods=HISTORY_WINDOW,
        ).sum()
    )

    valid_factor = (
        valid_history_count.eq(float(HISTORY_WINDOW))
        & numerator.notna()
        & np.isfinite(numerator)
        & denominator.notna()
        & np.isfinite(denominator)
        & denominator.gt(0.0)
    )

    factor = numerator.div(denominator).where(valid_factor)
    result = factor.astype("float64").to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_signed_trend_efficiency_60d_skip5()
