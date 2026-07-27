import os
import numpy as np
import pandas as pd


def calculate_intraday_return_1d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    open_price = data["$open"].astype("float64")
    close_price = data["$close"].astype("float64")

    valid = open_price.notna() & close_price.notna() & (open_price > 0)
    factor = (close_price / open_price - 1.0).where(valid, np.nan)

    result = factor.to_frame(name="Intraday_Return_1D")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_intraday_return_1d()
