from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Recency_Weighted_Close_Location_3D"
AGGREGATION_WINDOW = 3
CURRENT_SESSION_WEIGHT = 0.6
ONE_SESSION_LAG_WEIGHT = 0.3
TWO_SESSION_LAG_WEIGHT = 0.1


def calculate_recency_weighted_close_location_3d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")
    close = data["$close"].astype("float64")

    session_range = high.sub(low)
    session_valid = (
        np.isfinite(high)
        & (high > 0.0)
        & np.isfinite(low)
        & (low > 0.0)
        & np.isfinite(close)
        & (close > 0.0)
        & np.isfinite(session_range)
        & (session_range > 0.0)
    )

    close_location_value = (
        close.mul(2.0).sub(high).sub(low).div(session_range).where(session_valid)
    )
    close_location_value = close_location_value.where(
        np.isfinite(close_location_value)
    )

    grouped_clv = close_location_value.groupby(
        level="instrument", sort=False, group_keys=False
    )
    clv_lag_1 = grouped_clv.shift(1)
    clv_lag_2 = grouped_clv.shift(2)

    factor = (
        close_location_value.mul(CURRENT_SESSION_WEIGHT)
        .add(clv_lag_1.mul(ONE_SESSION_LAG_WEIGHT))
        .add(clv_lag_2.mul(TWO_SESSION_LAG_WEIGHT))
    )
    factor = factor.where(np.isfinite(factor))

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_recency_weighted_close_location_3d()
