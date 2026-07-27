from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Bounded_Overnight_Gap_Fade_1D"
LOOKBACK_PERIOD = 1
GAP_CLIP_LOWER_BOUND = -0.10
GAP_CLIP_UPPER_BOUND = 0.10
DENOMINATOR_STABILIZER = 1e-12
RECOVERY_RATIO_CAP = 1.0


def _instrument_shift(series: pd.Series, periods: int) -> pd.Series:
    return series.groupby(level="instrument", sort=False).shift(periods)


def calculate_bounded_overnight_gap_fade_1d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data")
    data.index = data.index.set_names(["datetime", "instrument"])
    data = data.sort_index()

    open_price = data["$open"].astype("float64")
    close_price = data["$close"].astype("float64")
    previous_close = _instrument_shift(close_price, LOOKBACK_PERIOD)

    price_valid = (
        np.isfinite(open_price)
        & (open_price > 0.0)
        & np.isfinite(close_price)
        & (close_price > 0.0)
        & np.isfinite(previous_close)
        & (previous_close > 0.0)
    )

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        overnight_gap = open_price.div(previous_close).sub(1.0)
        intraday_return = close_price.div(open_price).sub(1.0)

    calculation_valid = (
        price_valid
        & np.isfinite(overnight_gap)
        & np.isfinite(intraday_return)
    )

    clipped_gap = overnight_gap.clip(
        lower=GAP_CLIP_LOWER_BOUND,
        upper=GAP_CLIP_UPPER_BOUND,
    )

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        recovery_ratio = intraday_return.abs().div(
            overnight_gap.abs().add(DENOMINATOR_STABILIZER)
        )
    recovery_ratio = recovery_ratio.clip(upper=RECOVERY_RATIO_CAP)

    fade_indicator = (
        ((overnight_gap > 0.0) & (intraday_return < 0.0))
        | ((overnight_gap < 0.0) & (intraday_return > 0.0))
    )

    factor = pd.Series(np.nan, index=data.index, dtype="float64")
    factor.loc[calculation_valid] = 0.0

    fade_valid = calculation_valid & fade_indicator
    factor.loc[fade_valid] = (
        -clipped_gap.loc[fade_valid] * recovery_ratio.loc[fade_valid]
    )
    factor = factor.where(np.isfinite(factor))

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_bounded_overnight_gap_fade_1d()
