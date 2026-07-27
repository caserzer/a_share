import os
import numpy as np
import pandas as pd


def calculate_overnight_intraday_spread_20d_lag1():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["instrument", "datetime"])

    open_price = data["$open"].astype("float64")
    close_price = data["$close"].astype("float64")

    instrument = data.index.get_level_values("instrument")
    previous_close = close_price.groupby(instrument, sort=False).shift(1)

    valid_session = (
        np.isfinite(open_price)
        & np.isfinite(close_price)
        & np.isfinite(previous_close)
        & (open_price > 0.0)
        & (close_price > 0.0)
        & (previous_close > 0.0)
    )

    session_spread = (
        np.log(open_price.where(valid_session))
        - np.log(previous_close.where(valid_session))
        - np.log(close_price.where(valid_session))
        + np.log(open_price.where(valid_session))
    )

    factor = session_spread.groupby(instrument, sort=False).transform(
        lambda series: series.rolling(window=20, min_periods=20).mean().shift(1)
    )

    result = factor.to_frame(name="Overnight_Intraday_Spread_20D_Lag1")
    result.index = result.index.set_names(["datetime", "instrument"])
    result = result.sort_index(level=["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_overnight_intraday_spread_20d_lag1()
