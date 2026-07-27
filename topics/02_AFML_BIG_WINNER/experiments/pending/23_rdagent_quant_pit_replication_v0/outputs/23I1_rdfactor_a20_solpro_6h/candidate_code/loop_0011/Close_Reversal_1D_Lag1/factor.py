from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Close_Reversal_1D_Lag1"
RETURN_HORIZON = 1
SIGNAL_AVAILABILITY_LAG = 1


def calculate_close_reversal_1d_lag1() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    close = data["$close"].astype("float64")

    previous_close = close.groupby(level="instrument", sort=False).shift(RETURN_HORIZON)
    valid_source = (
        np.isfinite(close)
        & np.isfinite(previous_close)
        & close.gt(0.0)
        & previous_close.gt(0.0)
    )

    source_reversal = close.div(previous_close).sub(1.0).mul(-1.0)
    source_reversal = source_reversal.where(valid_source)

    factor = source_reversal.groupby(level="instrument", sort=False).shift(
        SIGNAL_AVAILABILITY_LAG
    )

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_close_reversal_1d_lag1()
