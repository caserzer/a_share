import os
import numpy as np
import pandas as pd


def calculate_gap_confirmation_volume_20d():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "daily_pv.h5")
    output_path = os.path.join(base_dir, "result.h5")

    data = pd.read_hdf(input_path, key="data")
    data = data.sort_index(level=["datetime", "instrument"])

    open_price = data["$open"].astype("float64")
    close_price = data["$close"].astype("float64")
    high_price = data["$high"].astype("float64")
    low_price = data["$low"].astype("float64")
    volume = data["$volume"].astype("float64")

    previous_close = close_price.groupby(
        level="instrument", sort=False
    ).shift(1)

    valid_volume = volume.where(np.isfinite(volume) & (volume >= 0.0))
    prior_volume_mean = valid_volume.groupby(
        level="instrument", sort=False
    ).transform(
        lambda series: series.shift(1).rolling(
            window=20, min_periods=20
        ).mean()
    )

    gap = open_price / previous_close - 1.0
    close_location_value = (
        (2.0 * close_price - high_price - low_price)
        / (high_price - low_price)
    )
    confirmation_weight = (
        1.0 + np.sign(gap) * close_location_value
    ) / 2.0
    volume_weight = volume / prior_volume_mean

    factor = gap * confirmation_weight * volume_weight

    valid_current_prices = (
        np.isfinite(open_price)
        & np.isfinite(close_price)
        & np.isfinite(high_price)
        & np.isfinite(low_price)
        & (open_price > 0.0)
        & (close_price > 0.0)
        & (high_price > 0.0)
        & (low_price > 0.0)
        & (high_price > low_price)
    )
    valid_previous_close = (
        np.isfinite(previous_close) & (previous_close > 0.0)
    )
    valid_current_volume = np.isfinite(volume) & (volume >= 0.0)
    valid_prior_volume = (
        np.isfinite(prior_volume_mean) & (prior_volume_mean > 0.0)
    )
    valid_factor = (
        valid_current_prices
        & valid_previous_close
        & valid_current_volume
        & valid_prior_volume
        & np.isfinite(factor)
    )

    factor_name = "Gap_Confirmation_Volume_20D"
    result = factor.where(valid_factor).to_frame(name=factor_name)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")


if __name__ == "__main__":
    calculate_gap_confirmation_volume_20d()
