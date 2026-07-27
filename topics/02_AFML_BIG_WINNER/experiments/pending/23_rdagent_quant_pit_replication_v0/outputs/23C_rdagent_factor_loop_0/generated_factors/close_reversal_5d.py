from pathlib import Path

import numpy as np
import pandas as pd


def calculate_close_reversal_5d():
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data")
    data = data.sort_index(level=["datetime", "instrument"])

    close = data["$close"].astype("float64")
    lagged_close = close.groupby(level="instrument", sort=False).shift(5)

    factor = -(close / lagged_close - 1.0)
    factor = factor.mask(close.isna() | lagged_close.isna() | lagged_close.eq(0.0))
    factor = factor.replace([np.inf, -np.inf], np.nan)

    result = factor.to_frame(name="close_reversal_5d")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")

    return result


if __name__ == "__main__":
    calculate_close_reversal_5d()
