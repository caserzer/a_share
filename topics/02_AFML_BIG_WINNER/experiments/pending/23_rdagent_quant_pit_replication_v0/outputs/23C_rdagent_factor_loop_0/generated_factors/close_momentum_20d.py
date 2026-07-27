import os

import numpy as np
import pandas as pd


def calculate_close_momentum_20d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["datetime", "instrument"])

    close = data["$close"].astype("float64")
    lagged_close = close.groupby(level="instrument", sort=False).shift(20)

    momentum = close / lagged_close - 1.0
    valid = close.notna() & lagged_close.notna() & lagged_close.ne(0.0)
    momentum = momentum.where(valid)

    result = momentum.to_frame(name="close_momentum_20d")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")

    return result


if __name__ == "__main__":
    calculate_close_momentum_20d()
