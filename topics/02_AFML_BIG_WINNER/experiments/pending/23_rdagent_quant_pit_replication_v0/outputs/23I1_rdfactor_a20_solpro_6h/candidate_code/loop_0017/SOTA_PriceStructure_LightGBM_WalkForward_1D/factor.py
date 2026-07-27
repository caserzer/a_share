from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

FACTOR_NAME = "SOTA_PriceStructure_LightGBM_WalkForward_1D"
FEATURE_NAMES = [
    "Overnight_Gap_1D",
    "Close_Location_Value_1D",
    "Close_Momentum_20D",
]

PREDICTION_HORIZON = 1
OVERNIGHT_GAP_LOOKBACK = 1
CLOSE_MOMENTUM_LOOKBACK = 20
TRAINING_WINDOW = 504
MINIMUM_TRAINING_SESSIONS = 252
REFIT_FREQUENCY = 5


def _instrument_shift(series: pd.Series, periods: int) -> pd.Series:
    return series.groupby(level="instrument", sort=False).shift(periods)


def _cross_sectional_percentile_rank(
    values: pd.DataFrame | pd.Series,
) -> pd.DataFrame | pd.Series:
    finite_values = values.where(np.isfinite(values))
    return finite_values.groupby(level="datetime", sort=False).rank(
        method="average", pct=True
    )


def _build_ranked_features(data: pd.DataFrame) -> pd.DataFrame:
    open_price = data["$open"].astype("float64")
    close = data["$close"].astype("float64")
    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")

    open_valid = np.isfinite(open_price) & (open_price > 0.0)
    close_valid = np.isfinite(close) & (close > 0.0)
    high_valid = np.isfinite(high) & (high > 0.0)
    low_valid = np.isfinite(low) & (low > 0.0)

    close_lag_1 = _instrument_shift(close, OVERNIGHT_GAP_LOOKBACK)
    overnight_valid = (
        open_valid & np.isfinite(close_lag_1) & (close_lag_1 > 0.0)
    )
    overnight_gap = open_price.div(close_lag_1).sub(1.0).where(overnight_valid)

    high_low_range = high.sub(low)
    close_location_valid = high_valid & low_valid & close_valid & (high > low)
    close_location = (
        close.mul(2.0)
        .sub(high)
        .sub(low)
        .div(high_low_range)
        .where(close_location_valid)
    )

    close_lag_20 = _instrument_shift(close, CLOSE_MOMENTUM_LOOKBACK)
    momentum_valid = (
        close_valid & np.isfinite(close_lag_20) & (close_lag_20 > 0.0)
    )
    close_momentum_20 = (
        close.div(close_lag_20).sub(1.0).where(momentum_valid)
    )

    raw_features = pd.DataFrame(
        {
            FEATURE_NAMES[0]: overnight_gap,
            FEATURE_NAMES[1]: close_location,
            FEATURE_NAMES[2]: close_momentum_20,
        },
        index=data.index,
        dtype="float64",
    )
    return _cross_sectional_percentile_rank(raw_features)


def _build_exact_next_global_return(
    close: pd.Series,
    sessions: pd.Index,
) -> pd.Series:
    row_dates = close.index.get_level_values("datetime")
    instruments = close.index.get_level_values("instrument")
    row_session_positions = sessions.get_indexer(row_dates)

    next_dates = np.full(len(close), np.datetime64("NaT"), dtype="datetime64[ns]")
    has_next_session = row_session_positions < len(sessions) - 1
    next_dates[has_next_session] = sessions.to_numpy()[
        row_session_positions[has_next_session] + PREDICTION_HORIZON
    ]

    endpoint_index = pd.MultiIndex.from_arrays(
        [next_dates, instruments],
        names=["datetime", "instrument"],
    )
    future_close_values = close.reindex(endpoint_index).to_numpy(dtype="float64")
    future_close = pd.Series(
        future_close_values,
        index=close.index,
        dtype="float64",
    )

    target_valid = (
        np.isfinite(close)
        & (close > 0.0)
        & has_next_session
        & np.isfinite(future_close)
        & (future_close > 0.0)
    )
    forward_return = future_close.div(close).sub(1.0).where(target_valid)
    return forward_return.where(np.isfinite(forward_return))


def _make_model() -> LGBMRegressor:
    return LGBMRegressor(
        objective="regression_l2",
        learning_rate=0.03,
        n_estimators=100,
        num_leaves=4,
        max_depth=2,
        min_child_samples=500,
        subsample=1.0,
        colsample_bytree=1.0,
        reg_alpha=0.2,
        reg_lambda=2.0,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )


def calculate_sota_pricestructure_lightgbm_walkforward_1d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    sessions = pd.Index(
        data.index.get_level_values("datetime").unique()
    ).sort_values()
    session_count = len(sessions)

    ranked_features = _build_ranked_features(data)
    close = data["$close"].astype("float64")
    forward_return = _build_exact_next_global_return(close, sessions)
    ranked_target = _cross_sectional_percentile_rank(forward_return)

    row_dates = data.index.get_level_values("datetime")
    row_session_positions = sessions.get_indexer(row_dates)
    finite_target = ranked_target.notna().to_numpy() & np.isfinite(
        ranked_target.to_numpy(dtype="float64")
    )

    target_session_positions = np.zeros(session_count, dtype=bool)
    target_dates = ranked_target.index.get_level_values("datetime")[finite_target]
    if len(target_dates) > 0:
        target_date_positions = sessions.get_indexer(pd.Index(target_dates).unique())
        target_session_positions[target_date_positions] = True

    anchor_position = None
    for refit_position in range(PREDICTION_HORIZON, session_count):
        training_start_position = max(0, refit_position - TRAINING_WINDOW)
        training_end_position = refit_position - 1
        eligible_session_count = int(
            np.count_nonzero(
                target_session_positions[
                    training_start_position : training_end_position + 1
                ]
            )
        )
        if eligible_session_count >= MINIMUM_TRAINING_SESSIONS:
            anchor_position = refit_position
            break

    predictions = pd.Series(np.nan, index=data.index, dtype="float64")

    if anchor_position is not None:
        for refit_position in range(
            anchor_position, session_count, REFIT_FREQUENCY
        ):
            training_start_position = max(0, refit_position - TRAINING_WINDOW)
            training_end_position = refit_position - 1

            eligible_session_count = int(
                np.count_nonzero(
                    target_session_positions[
                        training_start_position : training_end_position + 1
                    ]
                )
            )
            if eligible_session_count < MINIMUM_TRAINING_SESSIONS:
                continue

            training_mask = (
                (row_session_positions >= training_start_position)
                & (row_session_positions <= training_end_position)
                & finite_target
            )
            training_index = data.index[training_mask]
            x_train = ranked_features.loc[training_index, FEATURE_NAMES]
            y_train = ranked_target.loc[training_index]

            model = _make_model()
            model.fit(x_train, y_train)

            prediction_end_position = min(
                refit_position + REFIT_FREQUENCY, session_count
            )
            prediction_mask = (
                (row_session_positions >= refit_position)
                & (row_session_positions < prediction_end_position)
            )
            x_prediction = ranked_features.loc[prediction_mask, FEATURE_NAMES]
            predictions.loc[prediction_mask] = model.predict(x_prediction)

    result = predictions.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_sota_pricestructure_lightgbm_walkforward_1d()
