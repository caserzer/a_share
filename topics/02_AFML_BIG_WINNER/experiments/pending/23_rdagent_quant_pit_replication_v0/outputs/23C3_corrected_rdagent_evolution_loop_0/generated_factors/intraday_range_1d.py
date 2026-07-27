from pathlib import Path

import numpy as np
import pandas as pd


def calculate_intraday_range_1d() -> pd.DataFrame:
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data")

    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")
    close = data["$close"].astype("float64")

    factor = (high - low).div(close.where(close != 0.0))
    factor = factor.replace([np.inf, -np.inf], np.nan)

    result = factor.to_frame(name="intraday_range_1d")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")

    return result


if __name__ == "__main__":
    calculate_intraday_range_1d()
