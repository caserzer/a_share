import os
import numpy as np
import pandas as pd


def calculate_overnight_gap_1d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data").sort_index()
    open_price = data["$open"].astype("float64")
    close_price = data["$close"].astype("float64")

    previous_close = close_price.groupby(level="instrument", sort=False).shift(1)

    valid = (
        open_price.notna()
        & previous_close.notna()
        & np.isfinite(open_price)
        & np.isfinite(previous_close)
        & (open_price > 0)
        & (previous_close > 0)
    )
    factor = (open_price / previous_close - 1.0).where(valid, np.nan)

    result = factor.to_frame(name="Overnight_Gap_1D")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_overnight_gap_1d()
