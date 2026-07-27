from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Volatility_Scaled_Overnight_Gap_20D"
VOLATILITY_WINDOW = 20
GAP_LOOKBACK = 1
LOWER_CLIP_BOUND = -3.0
UPPER_CLIP_BOUND = 3.0


def _instrument_shift(series: pd.Series, periods: int) -> pd.Series:
    return series.groupby(level="instrument", sort=False).shift(periods)


def _prior_range_mean_square(range_squared: pd.Series) -> pd.Series:
    return range_squared.groupby(level="instrument", sort=False).transform(
        lambda values: values.shift(1).rolling(
            window=VOLATILITY_WINDOW,
            min_periods=VOLATILITY_WINDOW,
        ).mean()
    )


def calculate_volatility_scaled_overnight_gap_20d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    open_price = data["$open"].astype("float64")
    close = data["$close"].astype("float64")
    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")

    open_valid = np.isfinite(open_price) & (open_price > 0.0)

    previous_close = _instrument_shift(close, GAP_LOOKBACK)
    previous_close_valid = np.isfinite(previous_close) & (previous_close > 0.0)

    gap_valid = open_valid & previous_close_valid
    overnight_gap = open_price.div(previous_close).sub(1.0).where(gap_valid)
    overnight_gap = overnight_gap.where(np.isfinite(overnight_gap))

    prior_range_source_valid = (
        np.isfinite(high)
        & (high > 0.0)
        & np.isfinite(low)
        & (low > 0.0)
        & (high > low)
    )

    range_return = pd.Series(np.nan, index=data.index, dtype="float64")
    range_return.loc[prior_range_source_valid] = np.log(
        high.loc[prior_range_source_valid]
        / low.loc[prior_range_source_valid]
    )
    range_return = range_return.where(np.isfinite(range_return))

    range_squared = range_return.pow(2.0)
    prior_mean_squared_range = _prior_range_mean_square(range_squared)
    range_volatility = np.sqrt(prior_mean_squared_range)

    denominator_valid = (
        np.isfinite(range_volatility) & (range_volatility > 0.0)
    )
    factor_valid = gap_valid & denominator_valid

    standardized_gap = overnight_gap.div(range_volatility).where(factor_valid)
    standardized_gap = standardized_gap.where(np.isfinite(standardized_gap))
    factor = standardized_gap.clip(
        lower=LOWER_CLIP_BOUND,
        upper=UPPER_CLIP_BOUND,
    )

    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_volatility_scaled_overnight_gap_20d()
