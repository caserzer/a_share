from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Liquidity_Stress_Acceleration_5D_20D"
RECENT_WINDOW = 5
PRIOR_WINDOW = 20
SOURCE_WINDOW = 26


def calculate_liquidity_stress_acceleration_5d_20d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    close = data["$close"].astype("float64")
    volume = data["$volume"].astype("float64")

    valid_close = np.isfinite(close) & (close > 0.0)
    valid_volume = np.isfinite(volume) & (volume > 0.0)
    valid_source = valid_close & valid_volume

    complete_source_window = valid_source.astype("int64").groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=SOURCE_WINDOW,
            min_periods=SOURCE_WINDOW,
        ).sum()
    ).eq(SOURCE_WINDOW)

    previous_close = close.groupby(
        level="instrument", sort=False, group_keys=False
    ).shift(1)

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_return = np.log(close.div(previous_close))
        traded_value = close.mul(volume)
        stress = log_return.abs().div(traded_value)

    valid_stress = (
        valid_close
        & valid_volume
        & np.isfinite(previous_close)
        & (previous_close > 0.0)
        & np.isfinite(log_return)
        & np.isfinite(traded_value)
        & (traded_value > 0.0)
        & np.isfinite(stress)
    )
    stress = stress.where(valid_stress)

    recent_stress_mean = stress.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=RECENT_WINDOW,
            min_periods=RECENT_WINDOW,
        ).mean()
    )

    prior_stress_mean = stress.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.shift(RECENT_WINDOW).rolling(
            window=PRIOR_WINDOW,
            min_periods=PRIOR_WINDOW,
        ).mean()
    )

    valid_means = (
        complete_source_window
        & np.isfinite(recent_stress_mean)
        & (recent_stress_mean > 0.0)
        & np.isfinite(prior_stress_mean)
        & (prior_stress_mean > 0.0)
    )

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        mean_ratio = recent_stress_mean.div(prior_stress_mean)
        factor = np.log(mean_ratio)

    factor_valid = (
        valid_means
        & np.isfinite(mean_ratio)
        & (mean_ratio > 0.0)
        & np.isfinite(factor)
    )
    factor = factor.where(factor_valid)

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_liquidity_stress_acceleration_5d_20d()
