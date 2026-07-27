from pathlib import Path

import numpy as np
import pandas as pd


def calculate_daily_close_location_value():
    data_path = Path(__file__).resolve().parent / "daily_pv.h5"
    output_path = Path(__file__).resolve().parent / "result.h5"

    data = pd.read_hdf(data_path, key="data")

    close = data["$close"].astype("float64")
    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")

    daily_range = high - low
    factor = (2.0 * close - high - low) / daily_range.where(daily_range != 0.0)
    factor = factor.where(close.notna() & high.notna() & low.notna())
    factor = factor.replace([np.inf, -np.inf], np.nan)

    result = factor.to_frame(name="daily_close_location_value")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_daily_close_location_value()
