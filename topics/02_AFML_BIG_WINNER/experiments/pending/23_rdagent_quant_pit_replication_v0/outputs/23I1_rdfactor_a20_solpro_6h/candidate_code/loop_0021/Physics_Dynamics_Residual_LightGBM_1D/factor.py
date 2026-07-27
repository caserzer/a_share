from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

FACTOR_NAME = "Physics_Dynamics_Residual_LightGBM_1D"
PHYSICS_FEATURE_NAMES = [
    "Physics_Level_1D",
    "Physics_Change_1D",
    "Physics_Change_5D",
    "Physics_Innovation_ZScore_20D",
]
SOTA_FEATURE_NAMES = [
    "Overnight_Gap_1D",
    "Close_Location_Value_1D",
    "Close_Momentum_20D",
]

PREDICTION_HORIZON = 1
PHYSICS_CHANGE_1D_LOOKBACK = 1
PHYSICS_CHANGE_5D_LOOKBACK = 5
PHYSICS_ZSCORE_WINDOW = 20
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


def _build_ranked_physics_features(data: pd.DataFrame) -> pd.DataFrame:
    physics = data["$factor"].astype("float64")
    finite_physics = physics.where(np.isfinite(physics))

    physics_level = finite_physics.copy()

    physics_lag_1 = _instrument_shift(finite_physics, PHYSICS_CHANGE_1D_LOOKBACK)
    physics_change_1 = finite_physics.sub(physics_lag_1)
    physics_change_1 = physics_change_1.where(np.isfinite(physics_change_1))

    physics_lag_5 = _instrument_shift(finite_physics, PHYSICS_CHANGE_5D_LOOKBACK)
    physics_change_5 = finite_physics.sub(physics_lag_5)
    physics_change_5 = physics_change_5.where(np.isfinite(physics_change_5))

    grouped_physics = finite_physics.groupby(level="instrument", sort=False)
    rolling_mean = (
        grouped_physics.rolling(
            window=PHYSICS_ZSCORE_WINDOW,
            min_periods=PHYSICS_ZSCORE_WINDOW,
        )
        .mean()
        .reset_index(level=0, drop=True)
        .reindex(data.index)
    )
    rolling_std = (
        grouped_physics.rolling(
            window=PHYSICS_ZSCORE_WINDOW,
            min_periods=PHYSICS_ZSCORE_WINDOW,
        )
        .std(ddof=0)
        .reset_index(level=0, drop=True)
        .reindex(data.index)
    )

    zscore_valid = np.isfinite(rolling_mean) & np.isfinite(rolling_std) & (
        rolling_std > 0.0
    )
    physics_zscore_20 = finite_physics.sub(rolling_mean).div(rolling_std)
    physics_zscore_20 = physics_zscore_20.where(
        zscore_valid & np.isfinite(physics_zscore_20)
    )

    raw_features = pd.DataFrame(
        {
            PHYSICS_FEATURE_NAMES[0]: physics_level,
            PHYSICS_FEATURE_NAMES[1]: physics_change_1,
            PHYSICS_FEATURE_NAMES[2]: physics_change_5,
            PHYSICS_FEATURE_NAMES[3]: physics_zscore_20,
        },
        index=data.index,
        dtype="float64",
    )
    return _cross_sectional_percentile_rank(raw_features)


def _build_ranked_sota_features(data: pd.DataFrame) -> pd.DataFrame:
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
    close_momentum_20 = close.div(close_lag_20).sub(1.0).where(momentum_valid)

    raw_features = pd.DataFrame(
        {
            SOTA_FEATURE_NAMES[0]: overnight_gap,
            SOTA_FEATURE_NAMES[1]: close_location,
            SOTA_FEATURE_NAMES[2]: close_momentum_20,
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
    has_next_session = row_session_positions < len(sessions) - PREDICTION_HORIZON
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


def _build_residual_target(
    ranked_target: pd.Series,
    ranked_sota_features: pd.DataFrame,
) -> pd.Series:
    target_values = ranked_target.to_numpy(dtype="float64")
    sota_values = ranked_sota_features[SOTA_FEATURE_NAMES].to_numpy(
        dtype="float64"
    )
    residual_values = np.full(len(ranked_target), np.nan, dtype="float64")

    date_groups = ranked_target.groupby(level="datetime", sort=False).indices
    for positions in date_groups.values():
        positions = np.asarray(positions, dtype=np.int64)
        date_target = target_values[positions]
        date_sota = sota_values[positions]
        valid = np.isfinite(date_target) & np.isfinite(date_sota).all(axis=1)

        if not np.any(valid):
            continue

        valid_positions = positions[valid]
        design = np.column_stack(
            [
                np.ones(np.count_nonzero(valid), dtype="float64"),
                date_sota[valid],
            ]
        )
        response = date_target[valid]
        coefficients = np.linalg.lstsq(design, response, rcond=None)[0]
        date_residuals = response - design @ coefficients
        residual_values[valid_positions] = date_residuals

    residual_target = pd.Series(
        residual_values,
        index=ranked_target.index,
        dtype="float64",
    )
    return residual_target.where(np.isfinite(residual_target))


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


def calculate_physics_dynamics_residual_lightgbm_1d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    sessions = pd.Index(
        data.index.get_level_values("datetime").unique()
    ).sort_values()
    session_count = len(sessions)

    ranked_physics_features = _build_ranked_physics_features(data)
    ranked_sota_features = _build_ranked_sota_features(data)

    close = data["$close"].astype("float64")
    forward_return = _build_exact_next_global_return(close, sessions)
    ranked_target = _cross_sectional_percentile_rank(forward_return)
    residual_target = _build_residual_target(
        ranked_target,
        ranked_sota_features,
    )

    row_dates = data.index.get_level_values("datetime")
    row_session_positions = sessions.get_indexer(row_dates)
    residual_values = residual_target.to_numpy(dtype="float64")
    finite_residual = np.isfinite(residual_values)

    residual_session_positions = np.zeros(session_count, dtype=bool)
    residual_dates = residual_target.index.get_level_values("datetime")[
        finite_residual
    ]
    if len(residual_dates) > 0:
        residual_date_positions = sessions.get_indexer(
            pd.Index(residual_dates).unique()
        )
        residual_session_positions[residual_date_positions] = True

    anchor_position = None
    for refit_position in range(PREDICTION_HORIZON, session_count):
        training_start_position = max(0, refit_position - TRAINING_WINDOW)
        training_end_position = refit_position - 1
        eligible_session_count = int(
            np.count_nonzero(
                residual_session_positions[
                    training_start_position : training_end_position + 1
                ]
            )
        )
        if eligible_session_count >= MINIMUM_TRAINING_SESSIONS:
            anchor_position = refit_position
            break

    predictions = pd.Series(np.nan, index=data.index, dtype="float64")

    if anchor_position is not None:
        active_model = None

        for refit_position in range(
            anchor_position,
            session_count,
            REFIT_FREQUENCY,
        ):
            training_start_position = max(0, refit_position - TRAINING_WINDOW)
            training_end_position = refit_position - 1
            eligible_session_count = int(
                np.count_nonzero(
                    residual_session_positions[
                        training_start_position : training_end_position + 1
                    ]
                )
            )

            if eligible_session_count >= MINIMUM_TRAINING_SESSIONS:
                training_mask = (
                    (row_session_positions >= training_start_position)
                    & (row_session_positions <= training_end_position)
                    & finite_residual
                )
                training_index = data.index[training_mask]
                x_train = ranked_physics_features.loc[
                    training_index,
                    PHYSICS_FEATURE_NAMES,
                ]
                y_train = residual_target.loc[training_index]

                active_model = _make_model()
                active_model.fit(x_train, y_train)

            if active_model is not None:
                prediction_end_position = min(
                    refit_position + REFIT_FREQUENCY,
                    session_count,
                )
                prediction_mask = (
                    (row_session_positions >= refit_position)
                    & (row_session_positions < prediction_end_position)
                )
                x_prediction = ranked_physics_features.loc[
                    prediction_mask,
                    PHYSICS_FEATURE_NAMES,
                ]
                predictions.loc[prediction_mask] = active_model.predict(
                    x_prediction
                )

    result = predictions.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_physics_dynamics_residual_lightgbm_1d()
