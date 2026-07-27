import os
import pandas as pd


def calculate_mom20():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["datetime", "instrument"])

    close = data["$close"].astype("float64")
    lagged_close = close.groupby(level="instrument", sort=False).shift(20)

    mom20 = close.div(lagged_close).sub(1.0)
    mom20 = mom20.mask(lagged_close.eq(0.0))

    result = mom20.to_frame(name="MOM20")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_mom20()
