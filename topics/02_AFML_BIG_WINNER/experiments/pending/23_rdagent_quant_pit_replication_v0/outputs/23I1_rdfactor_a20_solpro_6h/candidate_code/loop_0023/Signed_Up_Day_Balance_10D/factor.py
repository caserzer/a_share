from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Signed_Up_Day_Balance_10D"
RETURN_WINDOW = 10
CLOSE_WINDOW = 11


def calculate_signed_up_day_balance_10d() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    close = data["$close"].astype("float64")

    valid_close = close.gt(0.0) & np.isfinite(close)
    safe_close = close.where(valid_close)
    previous_close = safe_close.groupby(level="instrument", sort=False).shift(1)

    log_return = np.log(safe_close.div(previous_close))
    return_sign = np.sign(log_return)

    sign_sum = return_sign.groupby(level="instrument", sort=False).transform(
        lambda values: values.rolling(
            window=RETURN_WINDOW,
            min_periods=RETURN_WINDOW,
        ).sum()
    )

    valid_close_count = valid_close.astype("int64").groupby(
        level="instrument", sort=False
    ).transform(
        lambda values: values.rolling(
            window=CLOSE_WINDOW,
            min_periods=CLOSE_WINDOW,
        ).sum()
    )

    factor = sign_sum.div(float(RETURN_WINDOW))
    factor = factor.where(valid_close_count.eq(CLOSE_WINDOW))

    result = factor.astype("float64").to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_signed_up_day_balance_10d()
