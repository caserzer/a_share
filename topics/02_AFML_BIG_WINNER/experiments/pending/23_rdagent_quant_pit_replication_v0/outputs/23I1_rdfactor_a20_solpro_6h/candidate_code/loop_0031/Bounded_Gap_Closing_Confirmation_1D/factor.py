from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Bounded_Gap_Closing_Confirmation_1D"
GAP_LOOKBACK = 1
GAP_CLIP_LOWER_BOUND = -0.10
GAP_CLIP_UPPER_BOUND = 0.10


def calculate_bounded_gap_closing_confirmation_1d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    open_price = data["$open"].astype("float64")
    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")
    close = data["$close"].astype("float64")

    previous_close = close.groupby(
        level="instrument", sort=False
    ).shift(GAP_LOOKBACK)

    source_valid = (
        np.isfinite(open_price)
        & (open_price > 0.0)
        & np.isfinite(high)
        & (high > 0.0)
        & np.isfinite(low)
        & (low > 0.0)
        & np.isfinite(close)
        & (close > 0.0)
        & np.isfinite(previous_close)
        & (previous_close > 0.0)
        & (high > low)
    )

    raw_gap = open_price.div(previous_close).sub(1.0)
    close_location_value = (
        close.mul(2.0).sub(high).sub(low).div(high.sub(low))
    )
    confirmation_weight = (
        1.0 + np.sign(raw_gap) * close_location_value
    ) / 2.0
    clipped_gap = raw_gap.clip(
        lower=GAP_CLIP_LOWER_BOUND,
        upper=GAP_CLIP_UPPER_BOUND,
    )
    factor = clipped_gap.mul(confirmation_weight)

    factor_valid = (
        source_valid
        & np.isfinite(raw_gap)
        & np.isfinite(close_location_value)
        & np.isfinite(confirmation_weight)
        & np.isfinite(factor)
    )
    factor = factor.where(factor_valid)

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_bounded_gap_closing_confirmation_1d()
