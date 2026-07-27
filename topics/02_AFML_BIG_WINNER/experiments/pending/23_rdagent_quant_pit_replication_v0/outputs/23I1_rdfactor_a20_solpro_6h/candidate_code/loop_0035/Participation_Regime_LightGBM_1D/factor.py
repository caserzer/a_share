from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

FACTOR_NAME = "Participation_Regime_LightGBM_1D"
FEATURE_NAMES = [
    "Lagged_VolumeChange_Return_Correlation_20D",
    "Lagged_LogVolume_Surprise_20D",
    "Current_Close_LogReturn_1D",
    "Realized_Close_Volatility_20D",
    "Mean_Amihud_Illiquidity_20D",
]

PREDICTION_HORIZON = 1
CORRELATION_WINDOW = 20
CORRELATION_SOURCE_WINDOW = 22
VOLUME_SURPRISE_BASELINE_WINDOW = 20
REALIZED_VOLATILITY_WINDOW = 20
ILLIQUIDITY_WINDOW = 20
TRAINING_WINDOW = 504
MINIMUM_TRAINING_SESSIONS = 252
REFIT_FREQUENCY = 5


def _cross_sectional_percentile_rank(
    values: pd.DataFrame | pd.Series,
) -> pd.DataFrame | pd.Series:
    finite_values = values.where(np.isfinite(values))
    return finite_values.groupby(level="datetime", sort=False).rank(
        method="average", pct=True
    )


def _rolling_transform(
    values: pd.Series,
    window: int,
    operation: str,
) -> pd.Series:
    grouped = values.groupby(level="instrument", sort=False)
    if operation == "mean":
        return grouped.transform(
            lambda series: series.rolling(
                window=window, min_periods=window
            ).mean()
        )
    if operation == "sum":
        return grouped.transform(
            lambda series: series.rolling(
                window=window, min_periods=window
            ).sum()
        )
    if operation == "std_ddof0":
        return grouped.transform(
            lambda series: series.rolling(
                window=window, min_periods=window
            ).std(ddof=0)
        )
    raise ValueError(f"Unsupported rolling operation: {operation}")


def _instrument_shift(values: pd.Series, periods: int) -> pd.Series:
    return values.groupby(level="instrument", sort=False).shift(periods)


def _build_ranked_features(data: pd.DataFrame) -> pd.DataFrame:
    instrument_sorted = data.sort_index(level=["instrument", "datetime"])
    close = instrument_sorted["$close"].astype("float64")
    volume = instrument_sorted["$volume"].astype("float64")

    valid_close = np.isfinite(close) & (close > 0.0)
    valid_volume = np.isfinite(volume) & (volume > 0.0)

    log_close = np.log(close.where(valid_close))
    log_volume = np.log(volume.where(valid_volume))

    close_log_return = log_close.sub(_instrument_shift(log_close, 1))
    lagged_volume_change = _instrument_shift(log_volume, 1).sub(
        _instrument_shift(log_volume, 2)
    )

    mean_lagged_volume_change = _rolling_transform(
        lagged_volume_change, CORRELATION_WINDOW, "mean"
    )
    mean_return = _rolling_transform(
        close_log_return, CORRELATION_WINDOW, "mean"
    )
    mean_product = _rolling_transform(
        lagged_volume_change.mul(close_log_return),
        CORRELATION_WINDOW,
        "mean",
    )
    mean_volume_change_squared = _rolling_transform(
        lagged_volume_change.pow(2), CORRELATION_WINDOW, "mean"
    )
    mean_return_squared = _rolling_transform(
        close_log_return.pow(2), CORRELATION_WINDOW, "mean"
    )

    covariance = mean_product.sub(
        mean_lagged_volume_change.mul(mean_return)
    )
    volume_change_variance = mean_volume_change_squared.sub(
        mean_lagged_volume_change.pow(2)
    )
    return_variance = mean_return_squared.sub(mean_return.pow(2))

    source_valid = valid_close & valid_volume
    valid_source_count = _rolling_transform(
        source_valid.astype("float64"), CORRELATION_SOURCE_WINDOW, "sum"
    )
    correlation_valid = (
        (valid_source_count == CORRELATION_SOURCE_WINDOW)
        & np.isfinite(covariance)
        & np.isfinite(volume_change_variance)
        & np.isfinite(return_variance)
        & (volume_change_variance > 0.0)
        & (return_variance > 0.0)
    )
    lagged_correlation = covariance.div(
        np.sqrt(volume_change_variance.mul(return_variance))
    ).where(correlation_valid)
    lagged_correlation = lagged_correlation.where(
        np.isfinite(lagged_correlation)
    )

    lagged_log_volume = _instrument_shift(log_volume, 1)
    baseline_log_volume = _rolling_transform(
        _instrument_shift(log_volume, 2),
        VOLUME_SURPRISE_BASELINE_WINDOW,
        "mean",
    )
    prior_volume_valid_count = _rolling_transform(
        _instrument_shift(valid_volume.astype("float64"), 1),
        VOLUME_SURPRISE_BASELINE_WINDOW + 1,
        "sum",
    )
    volume_surprise_valid = (
        prior_volume_valid_count == VOLUME_SURPRISE_BASELINE_WINDOW + 1
    )
    lagged_volume_surprise = lagged_log_volume.sub(
        baseline_log_volume
    ).where(volume_surprise_valid)
    lagged_volume_surprise = lagged_volume_surprise.where(
        np.isfinite(lagged_volume_surprise)
    )

    current_return = close_log_return.where(np.isfinite(close_log_return))

    realized_volatility = _rolling_transform(
        close_log_return, REALIZED_VOLATILITY_WINDOW, "std_ddof0"
    )
    realized_volatility = realized_volatility.where(
        np.isfinite(realized_volatility)
    )

    denominator = close.mul(volume)
    daily_illiquidity_valid = (
        np.isfinite(close_log_return)
        & valid_close
        & valid_volume
        & np.isfinite(denominator)
        & (denominator > 0.0)
    )
    daily_illiquidity = close_log_return.abs().div(denominator).where(
        daily_illiquidity_valid
    )
    mean_illiquidity = _rolling_transform(
        daily_illiquidity, ILLIQUIDITY_WINDOW, "mean"
    )
    mean_illiquidity = mean_illiquidity.where(np.isfinite(mean_illiquidity))

    raw_features = pd.DataFrame(
        {
            FEATURE_NAMES[0]: lagged_correlation,
            FEATURE_NAMES[1]: lagged_volume_surprise,
            FEATURE_NAMES[2]: current_return,
            FEATURE_NAMES[3]: realized_volatility,
            FEATURE_NAMES[4]: mean_illiquidity,
        },
        index=instrument_sorted.index,
        dtype="float64",
    )
    raw_features = raw_features.reindex(data.index)
    return _cross_sectional_percentile_rank(raw_features)


def _build_exact_next_global_return(
    close: pd.Series,
    sessions: pd.Index,
) -> pd.Series:
    row_dates = close.index.get_level_values("datetime")
    instruments = close.index.get_level_values("instrument")
    row_session_positions = sessions.get_indexer(row_dates)

    next_dates = np.full(len(close), np.datetime64("NaT"), dtype="datetime64[ns]")
    has_next_session = (
        row_session_positions + PREDICTION_HORIZON < len(sessions)
    )
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
        learning_rate=0.02,
        n_estimators=150,
        num_leaves=7,
        max_depth=3,
        min_child_samples=500,
        subsample=1.0,
        colsample_bytree=1.0,
        reg_alpha=0.2,
        reg_lambda=2.0,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )


def calculate_participation_regime_lightgbm_1d() -> pd.DataFrame:
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

    feature_values = ranked_features[FEATURE_NAMES].to_numpy(dtype="float64")
    complete_features = np.isfinite(feature_values).all(axis=1)
    target_values = ranked_target.to_numpy(dtype="float64")
    finite_target = np.isfinite(target_values)
    complete_training_rows = complete_features & finite_target

    eligible_training_sessions = np.zeros(session_count, dtype=bool)
    if np.any(complete_training_rows):
        eligible_positions = np.unique(
            row_session_positions[complete_training_rows]
        )
        eligible_training_sessions[eligible_positions] = True

    anchor_position = None
    for refit_position in range(PREDICTION_HORIZON, session_count):
        training_start = max(0, refit_position - TRAINING_WINDOW)
        training_end = refit_position - 1
        eligible_count = int(
            np.count_nonzero(
                eligible_training_sessions[training_start : training_end + 1]
            )
        )
        if eligible_count >= MINIMUM_TRAINING_SESSIONS:
            anchor_position = refit_position
            break

    raw_predictions = pd.Series(np.nan, index=data.index, dtype="float64")

    if anchor_position is not None:
        current_model = None

        for refit_position in range(
            anchor_position, session_count, REFIT_FREQUENCY
        ):
            training_start = max(0, refit_position - TRAINING_WINDOW)
            training_end = refit_position - 1
            eligible_count = int(
                np.count_nonzero(
                    eligible_training_sessions[training_start : training_end + 1]
                )
            )

            if eligible_count >= MINIMUM_TRAINING_SESSIONS:
                training_mask = (
                    (row_session_positions >= training_start)
                    & (row_session_positions <= training_end)
                    & complete_training_rows
                )
                x_train = ranked_features.loc[training_mask, FEATURE_NAMES]
                y_train = ranked_target.loc[training_mask]

                current_model = _make_model()
                current_model.fit(x_train, y_train)

            if current_model is not None:
                prediction_end = min(
                    refit_position + REFIT_FREQUENCY, session_count
                )
                prediction_mask = (
                    (row_session_positions >= refit_position)
                    & (row_session_positions < prediction_end)
                    & complete_features
                )
                x_prediction = ranked_features.loc[
                    prediction_mask, FEATURE_NAMES
                ]
                if len(x_prediction) > 0:
                    raw_predictions.loc[prediction_mask] = current_model.predict(
                        x_prediction
                    )

    ranked_predictions = _cross_sectional_percentile_rank(raw_predictions)
    result = ranked_predictions.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_participation_regime_lightgbm_1d()
