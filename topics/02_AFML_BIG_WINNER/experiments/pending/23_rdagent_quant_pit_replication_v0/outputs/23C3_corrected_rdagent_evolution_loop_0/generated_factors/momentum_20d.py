import os

import pandas as pd


def calculate_momentum_20d():
    """Calculate 20-trading-day adjusted close-price momentum."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "daily_pv.h5")
    output_path = os.path.join(script_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["instrument", "datetime"])

    close = data["$close"].astype("float64")
    close_20d_ago = close.groupby(level="instrument", sort=False).shift(20)
    momentum = close.div(close_20d_ago).sub(1.0)

    result = momentum.to_frame(name="momentum_20d")
    result = result.reorder_levels(["datetime", "instrument"]).sort_index()
    result.to_hdf(output_path, key="data", mode="w")

    return result


if __name__ == "__main__":
    calculate_momentum_20d()
