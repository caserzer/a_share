import os

import numpy as np
import pandas as pd


def calculate_volume_surprise_20d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["instrument", "datetime"])

    volume = data["$volume"].astype("float64")
    trailing_mean_20d = volume.groupby(level="instrument", sort=False).transform(
        lambda series: series.rolling(window=20, min_periods=20).mean()
    )

    factor = volume.div(trailing_mean_20d).sub(1.0)
    factor = factor.replace([np.inf, -np.inf], np.nan)

    result = factor.to_frame(name="volume_surprise_20d")
    result = result.reorder_levels(["datetime", "instrument"]).sort_index()
    result.to_hdf(output_path, key="data", mode="w")

    return result


if __name__ == "__main__":
    calculate_volume_surprise_20d()
