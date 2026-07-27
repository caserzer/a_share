import os
import numpy as np
import pandas as pd


def calculate_volsurprise20():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data").sort_index()
    volume = data["$volume"].astype("float64")

    baseline = volume.groupby(level="instrument", sort=False).transform(
        lambda series: series.shift(1).rolling(window=20, min_periods=20).mean()
    )
    baseline = baseline.mask(baseline == 0.0)

    factor = volume.div(baseline).sub(1.0)
    factor = factor.replace([np.inf, -np.inf], np.nan)

    result = factor.to_frame(name="VOLSURPRISE20")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_volsurprise20()
