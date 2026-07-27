from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "MAX_Return_Reversal_20D"
RETURN_WINDOW = 20
CLOSE_WINDOW = 21


def calculate_max_return_reversal_20d() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    close = data["$close"].astype("float64")

    valid_close = close.notna() & np.isfinite(close) & close.gt(0.0)
    validated_close = close.where(valid_close)

    previous_close = validated_close.groupby(
        level="instrument", sort=False
    ).shift(1)
    simple_return = validated_close.div(previous_close).sub(1.0)

    maximum_return = simple_return.groupby(
        level="instrument", sort=False
    ).transform(
        lambda series: series.rolling(
            window=RETURN_WINDOW,
            min_periods=RETURN_WINDOW,
        ).max()
    )

    valid_close_count = valid_close.astype("int64").groupby(
        level="instrument", sort=False
    ).transform(
        lambda series: series.rolling(
            window=CLOSE_WINDOW,
            min_periods=CLOSE_WINDOW,
        ).sum()
    )

    factor = maximum_return.mul(-1.0).where(valid_close_count.eq(CLOSE_WINDOW))
    factor = factor.astype("float64")

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_max_return_reversal_20d()
