import os
import numpy as np
import pandas as pd


def calculate_lower_wick_fraction_1d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    open_price = data["$open"].astype("float64")
    close_price = data["$close"].astype("float64")
    high_price = data["$high"].astype("float64")
    low_price = data["$low"].astype("float64")

    valid = (
        np.isfinite(open_price)
        & np.isfinite(close_price)
        & np.isfinite(high_price)
        & np.isfinite(low_price)
        & (open_price > 0.0)
        & (close_price > 0.0)
        & (high_price > 0.0)
        & (low_price > 0.0)
        & (high_price > low_price)
    )

    lower_wick_length = np.minimum(open_price, close_price) - low_price
    daily_range = high_price - low_price
    factor = (lower_wick_length / daily_range).where(valid, np.nan)

    result = factor.to_frame(name="Lower_Wick_Fraction_1D")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_lower_wick_fraction_1d()
