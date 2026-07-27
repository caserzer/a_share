from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Skip5_Momentum_60D"
HISTORY_WINDOW = 60
RECENT_SKIP = 5


def calculate_skip5_momentum_60d() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    close = data["$close"].astype("float64")
    grouped_close = close.groupby(level="instrument", sort=False)

    close_t_minus_5 = grouped_close.shift(RECENT_SKIP)
    close_t_minus_60 = grouped_close.shift(HISTORY_WINDOW)

    valid_close = close.gt(0.0) & np.isfinite(close)
    prior_valid_count = valid_close.groupby(
        level="instrument", sort=False
    ).transform(
        lambda values: values.shift(1).rolling(
            window=HISTORY_WINDOW,
            min_periods=HISTORY_WINDOW,
        ).sum()
    )
    complete_valid_history = prior_valid_count.eq(HISTORY_WINDOW)

    momentum = close_t_minus_5.div(close_t_minus_60).sub(1.0)
    momentum = momentum.where(complete_valid_history)

    result = momentum.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_skip5_momentum_60d()
