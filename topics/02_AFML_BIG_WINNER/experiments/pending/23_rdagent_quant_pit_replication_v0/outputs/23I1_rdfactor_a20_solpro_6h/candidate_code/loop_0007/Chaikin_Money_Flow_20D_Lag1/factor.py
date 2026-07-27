import os
import numpy as np
import pandas as pd


def calculate_chaikin_money_flow_20d_lag1():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["datetime", "instrument"])

    open_price = data["$open"].astype("float64")
    high_price = data["$high"].astype("float64")
    low_price = data["$low"].astype("float64")
    close_price = data["$close"].astype("float64")
    volume = data["$volume"].astype("float64")

    valid_session = (
        np.isfinite(open_price)
        & np.isfinite(high_price)
        & np.isfinite(low_price)
        & np.isfinite(close_price)
        & np.isfinite(volume)
        & (high_price > low_price)
        & (volume >= 0.0)
    )

    money_flow_volume = pd.Series(np.nan, index=data.index, dtype="float64")
    money_flow_multiplier = (
        (2.0 * close_price.loc[valid_session]
         - high_price.loc[valid_session]
         - low_price.loc[valid_session])
        / (high_price.loc[valid_session] - low_price.loc[valid_session])
    )
    money_flow_volume.loc[valid_session] = (
        volume.loc[valid_session] * money_flow_multiplier
    )

    valid_volume = volume.where(valid_session)
    valid_indicator = valid_session.astype("float64")

    numerator = money_flow_volume.groupby(
        level="instrument", sort=False
    ).transform(
        lambda series: series.shift(1).rolling(window=20, min_periods=20).sum()
    )
    denominator = valid_volume.groupby(
        level="instrument", sort=False
    ).transform(
        lambda series: series.shift(1).rolling(window=20, min_periods=20).sum()
    )
    valid_count = valid_indicator.groupby(
        level="instrument", sort=False
    ).transform(
        lambda series: series.shift(1).rolling(window=20, min_periods=20).sum()
    )

    complete_window = (
        (valid_count == 20.0)
        & np.isfinite(numerator)
        & np.isfinite(denominator)
        & (denominator > 0.0)
    )

    factor = pd.Series(np.nan, index=data.index, dtype="float64")
    factor.loc[complete_window] = (
        numerator.loc[complete_window] / denominator.loc[complete_window]
    )
    factor = factor.where(np.isfinite(factor))

    factor_name = "Chaikin_Money_Flow_20D_Lag1"
    result = factor.to_frame(name=factor_name)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_chaikin_money_flow_20d_lag1()
