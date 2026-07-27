import os
import numpy as np
import pandas as pd


def calculate_close_location_value_1d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    close_price = data["$close"].astype("float64")
    high_price = data["$high"].astype("float64")
    low_price = data["$low"].astype("float64")

    daily_range = high_price - low_price
    valid = (
        np.isfinite(close_price)
        & np.isfinite(high_price)
        & np.isfinite(low_price)
        & (daily_range > 0.0)
    )

    factor = ((2.0 * close_price - high_price - low_price) / daily_range).where(
        valid, np.nan
    )

    result = factor.to_frame(name="Close_Location_Value_1D")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_close_location_value_1d()
