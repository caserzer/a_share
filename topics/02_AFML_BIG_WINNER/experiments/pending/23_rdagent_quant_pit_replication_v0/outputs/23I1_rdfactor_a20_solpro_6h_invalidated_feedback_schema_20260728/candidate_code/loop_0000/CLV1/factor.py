import os
import pandas as pd


def calculate_clv1():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    daily_pv = pd.read_hdf(input_path, key="data")

    close = daily_pv["$close"].astype("float64")
    high = daily_pv["$high"].astype("float64")
    low = daily_pv["$low"].astype("float64")

    daily_range = high - low
    clv1 = (2.0 * close - high - low) / daily_range.mask(daily_range == 0.0)

    result = clv1.to_frame(name="CLV1")
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_clv1()
