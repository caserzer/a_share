import os

import numpy as np
import pandas as pd


def calculate_volatility_20d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data").sort_index()
    close = data["$close"].astype(np.float64)

    log_close = np.log(close)
    log_return = log_close.groupby(level="instrument", sort=False).diff()
    volatility = log_return.groupby(level="instrument", sort=False).transform(
        lambda values: values.rolling(window=20, min_periods=20).std(ddof=1)
    )

    result = volatility.to_frame(name="volatility_20d")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_volatility_20d()
