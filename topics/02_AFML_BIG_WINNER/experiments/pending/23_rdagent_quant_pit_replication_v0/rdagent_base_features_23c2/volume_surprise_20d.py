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
    historical_mean = volume.groupby(level="instrument", sort=False).transform(
        lambda series: series.shift(1).rolling(window=20, min_periods=20).mean()
    )

    factor = np.log((volume + 1.0) / (historical_mean + 1.0))
    result = factor.to_frame(name="volume_surprise_20d")
    result = result.sort_index(level=["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_volume_surprise_20d()
