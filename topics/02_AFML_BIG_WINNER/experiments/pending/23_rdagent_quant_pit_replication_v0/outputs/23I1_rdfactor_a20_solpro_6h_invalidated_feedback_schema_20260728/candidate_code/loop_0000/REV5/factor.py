import os
import numpy as np
import pandas as pd


def calculate_rev5():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    close = data["$close"].astype("float64").sort_index(level=["instrument", "datetime"])

    lagged_close = close.groupby(level="instrument", sort=False).shift(5)
    valid = close.notna() & lagged_close.notna() & lagged_close.ne(0.0)

    rev5 = pd.Series(np.nan, index=close.index, dtype="float64", name="REV5")
    rev5.loc[valid] = -(close.loc[valid] / lagged_close.loc[valid] - 1.0)

    result = rev5.to_frame().sort_index(level=["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_rev5()
