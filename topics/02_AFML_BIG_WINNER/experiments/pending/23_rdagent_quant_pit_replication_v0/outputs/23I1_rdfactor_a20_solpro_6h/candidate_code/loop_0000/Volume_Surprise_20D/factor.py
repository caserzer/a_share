import os
import numpy as np
import pandas as pd


def calculate_volume_surprise_20d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["datetime", "instrument"])

    log_volume = np.log1p(data["$volume"].astype("float64"))
    prior_mean = log_volume.groupby(level="instrument", sort=False).transform(
        lambda series: series.shift(1).rolling(window=20, min_periods=20).mean()
    )

    factor_name = "Volume_Surprise_20D"
    result = (log_volume - prior_mean).to_frame(name=factor_name)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_volume_surprise_20d()
