from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

FACTOR_NAME = "MultiHorizon_PriceStructure_Ridge_1D"
SOURCE_NAMES = [
    "Overnight_Gap_1D",
    "Close_Location_Value_1D",
    "Close_Momentum_20D",
]
PREDICTOR_LAGS = [0, 1, 2, 5, 10]
PREDICTOR_NAMES = [
    f"{source}_lag_{lag}"
    for source in SOURCE_NAMES
    for lag in PREDICTOR_LAGS
]
TARGET_HORIZONS = [1, 3, 5]

OVERNIGHT_GAP_LOOKBACK = 1
CLOSE_MOMENTUM_LOOKBACK = 20
TRAINING_WINDOW = 504
MINIMUM_TRAINING_SESSIONS = 252
REFIT_FREQUENCY = 5
MAXIMUM_LABEL_HORIZON = 5

RIDGE_ALPHA = 100.0
RIDGE_TOLERANCE = 1e-6
RIDGE_MAX_ITERATIONS = 1000


def _instrument_shift(series: pd.Series, periods: int) -> pd.Series:
    return series.groupby(level="instrument", sort=False).shift(periods)


def _cross_sectional_percentile_rank(
    values: pd.DataFrame | pd.Series,
) -> pd.DataFrame | pd.Series:
    finite_values = values.where(np.isfinite(values))
    return finite_values.groupby(level="datetime", sort=False).rank(
        method="average",
        pct=True,
    )


def _build_ranked_sources(data: pd.DataFrame) -> pd.DataFrame:
    open_price = data["$open"].astype("float64")
    close = data["$close"].astype("float64")
    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")

    open_valid = np.isfinite(open_price) & (open_price > 0.0)
    close_valid = np.isfinite(close) & (close > 0.0)
    high_valid = np.isfinite(high) & (high > 0.0)
    low_valid = np.isfinite(low) & (low > 0.0)

    previous_close = _instrument_shift(close, OVERNIGHT_GAP_LOOKBACK)
    overnight_valid = (
        open_valid
        & np.isfinite(previous_close)
        & (previous_close > 0.0)
    )
    overnight_gap = (
        open_price.div(previous_close)
        .sub(1.0)
        .where(overnight_valid)
    )

    high_low_range = high.sub(low)
    close_location_valid = (
        high_valid
        & low_valid
        & close_valid
        & (high > low)
    )
    close_location = (
        close.mul(2.0)
        .sub(high)
        .sub(low)
        .div(high_low_range)
        .where(close_location_valid)
    )

    close_lag_20 = _instrument_shift(close, CLOSE_MOMENTUM_LOOKBACK)
    momentum_valid = (
        close_valid
        & np.isfinite(close_lag_20)
        & (close_lag_20 > 0.0)
    )
    close_momentum_20 = (
        close.div(close_lag_20)
        .sub(1.0)
        .where(momentum_valid)
    )

    raw_sources = pd.DataFrame(
        {
            SOURCE_NAMES[0]: overnight_gap,
            SOURCE_NAMES[1]: close_location,
            SOURCE_NAMES[2]: close_momentum_20,
        },
        index=data.index,
        dtype="float64",
    )
    return _cross_sectional_percentile_rank(raw_sources)


def _build_lagged_predictors(ranked_sources: pd.DataFrame) -> pd.DataFrame:
    predictors = {}

    for source_name in SOURCE_NAMES:
        source = ranked_sources[source_name]
        for lag in PREDICTOR_LAGS:
            predictor_name = f"{source_name}_lag_{lag}"
            if lag == 0:
                predictors[predictor_name] = source
            else:
                predictors[predictor_name] = _instrument_shift(source, lag)

    return pd.DataFrame(
        predictors,
        index=ranked_sources.index,
        columns=PREDICTOR_NAMES,
        dtype="float64",
    )


def _build_exact_global_forward_return(
    close: pd.Series,
    sessions: pd.Index,
    horizon: int,
) -> pd.Series:
    row_dates = close.index.get_level_values("datetime")
    instruments = close.index.get_level_values("instrument")
    row_session_positions = sessions.get_indexer(row_dates)

    endpoint_dates = np.full(
        len(close),
        np.datetime64("NaT"),
        dtype="datetime64[ns]",
    )
    has_endpoint = row_session_positions + horizon < len(sessions)
    endpoint_dates[has_endpoint] = sessions.to_numpy()[
        row_session_positions[has_endpoint] + horizon
    ]

    endpoint_index = pd.MultiIndex.from_arrays(
        [endpoint_dates, instruments],
        names=["datetime", "instrument"],
    )
    endpoint_close_values = close.reindex(endpoint_index).to_numpy(
        dtype="float64"
    )
    endpoint_close = pd.Series(
        endpoint_close_values,
        index=close.index,
        dtype="float64",
    )

    valid = (
        has_endpoint
        & np.isfinite(close)
        & (close > 0.0)
        & np.isfinite(endpoint_close)
        & (endpoint_close > 0.0)
    )
    forward_return = endpoint_close.div(close).sub(1.0).where(valid)
    return forward_return.where(np.isfinite(forward_return))


def _build_ranked_targets(
    close: pd.Series,
    sessions: pd.Index,
) -> tuple[pd.DataFrame, pd.Series]:
    ranked_horizon_targets = {}

    for horizon in TARGET_HORIZONS:
        forward_return = _build_exact_global_forward_return(
            close,
            sessions,
            horizon,
        )
        ranked_horizon_targets[f"target_rank_{horizon}G"] = (
            _cross_sectional_percentile_rank(forward_return)
        )

    target_components = pd.DataFrame(
        ranked_horizon_targets,
        index=close.index,
        dtype="float64",
    )
    component_values = target_components.to_numpy(dtype="float64")
    complete_labels = np.isfinite(component_values).all(axis=1)

    target = target_components.mean(axis=1).where(complete_labels)
    target = target.where(np.isfinite(target))
    return target_components, target


def _make_model() -> Ridge:
    return Ridge(
        alpha=RIDGE_ALPHA,
        fit_intercept=True,
        solver="lsqr",
        tol=RIDGE_TOLERANCE,
        max_iter=RIDGE_MAX_ITERATIONS,
    )


def calculate_multihorizon_pricestructure_ridge_1d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    sessions = pd.Index(
        data.index.get_level_values("datetime").unique()
    ).sort_values()
    session_count = len(sessions)

    ranked_sources = _build_ranked_sources(data)
    predictors = _build_lagged_predictors(ranked_sources)

    close = data["$close"].astype("float64")
    target_components, target = _build_ranked_targets(close, sessions)

    predictor_values = predictors.to_numpy(dtype="float64")
    target_component_values = target_components.to_numpy(dtype="float64")
    target_values = target.to_numpy(dtype="float64")

    complete_predictors = np.isfinite(predictor_values).all(axis=1)
    complete_labels = np.isfinite(target_component_values).all(axis=1)
    complete_training_rows = (
        complete_predictors
        & complete_labels
        & np.isfinite(target_values)
    )

    row_dates = data.index.get_level_values("datetime")
    row_session_positions = sessions.get_indexer(row_dates)

    eligible_feature_sessions = np.zeros(session_count, dtype=bool)
    complete_row_dates = row_dates[complete_training_rows]
    if len(complete_row_dates) > 0:
        complete_date_positions = sessions.get_indexer(
            pd.Index(complete_row_dates).unique()
        )
        eligible_feature_sessions[complete_date_positions] = True

    anchor_position = None
    for refit_position in range(MAXIMUM_LABEL_HORIZON, session_count):
        training_start_position = max(
            0,
            refit_position - TRAINING_WINDOW,
        )
        observable_end_position = refit_position - MAXIMUM_LABEL_HORIZON

        eligible_session_count = int(
            np.count_nonzero(
                eligible_feature_sessions[
                    training_start_position : observable_end_position + 1
                ]
            )
        )
        if eligible_session_count >= MINIMUM_TRAINING_SESSIONS:
            anchor_position = refit_position
            break

    raw_predictions = np.full(len(data), np.nan, dtype="float64")

    if anchor_position is not None:
        active_model = None

        for refit_position in range(
            anchor_position,
            session_count,
            REFIT_FREQUENCY,
        ):
            training_start_position = max(
                0,
                refit_position - TRAINING_WINDOW,
            )
            observable_end_position = refit_position - MAXIMUM_LABEL_HORIZON

            eligible_session_count = int(
                np.count_nonzero(
                    eligible_feature_sessions[
                        training_start_position : observable_end_position + 1
                    ]
                )
            )

            if eligible_session_count >= MINIMUM_TRAINING_SESSIONS:
                training_mask = (
                    (row_session_positions >= training_start_position)
                    & (row_session_positions <= observable_end_position)
                    & complete_training_rows
                )

                x_train = predictor_values[training_mask]
                y_train = target_values[training_mask]

                active_model = _make_model()
                active_model.fit(x_train, y_train)

            prediction_end_position = min(
                refit_position + REFIT_FREQUENCY,
                session_count,
            )
            prediction_mask = (
                (row_session_positions >= refit_position)
                & (row_session_positions < prediction_end_position)
                & complete_predictors
            )

            if active_model is not None and np.any(prediction_mask):
                raw_predictions[prediction_mask] = active_model.predict(
                    predictor_values[prediction_mask]
                )

    raw_prediction_series = pd.Series(
        raw_predictions,
        index=data.index,
        dtype="float64",
    ).where(np.isfinite(raw_predictions))

    ranked_predictions = _cross_sectional_percentile_rank(
        raw_prediction_series
    )
    result = ranked_predictions.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result[FACTOR_NAME] = result[FACTOR_NAME].astype("float64")
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_multihorizon_pricestructure_ridge_1d()
