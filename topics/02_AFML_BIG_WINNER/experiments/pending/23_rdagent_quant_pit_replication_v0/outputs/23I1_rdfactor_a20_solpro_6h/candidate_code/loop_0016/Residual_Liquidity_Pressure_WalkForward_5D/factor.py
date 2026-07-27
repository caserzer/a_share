from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

FACTOR_NAME = "Residual_Liquidity_Pressure_WalkForward_5D"
FEATURE_NAMES = [
    "Signed_Volume_Pressure_Mean_5D",
    "Signed_Volume_Pressure_Mean_20D",
    "Illiquidity_Pressure_Mean_20D",
    "Negative_Return_Positive_Volume_Shock_1D",
]
SOTA_NAMES = [
    "Overnight_Gap_1D",
    "Close_Location_Value_1D",
    "Close_Momentum_20D",
]

PREDICTION_HORIZON = 5
VOLUME_BASELINE_WINDOW = 20
FEATURE_1_WINDOW = 5
FEATURE_2_WINDOW = 20
FEATURE_3_WINDOW = 20
TRAINING_WINDOW = 504
MINIMUM_TRAINING_SESSIONS = 252
REFIT_FREQUENCY = 20
VOLUME_SURPRISE_LOWER_BOUND = -3.0
VOLUME_SURPRISE_UPPER_BOUND = 3.0


def _instrument_shift(series: pd.Series, periods: int) -> pd.Series:
    return series.groupby(level="instrument", sort=False).shift(periods)


def _instrument_rolling_mean(series: pd.Series, window: int) -> pd.Series:
    return series.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=window,
            min_periods=window,
        ).mean()
    )


def _cross_sectional_percentile_rank(
    values: pd.DataFrame | pd.Series,
) -> pd.DataFrame | pd.Series:
    finite_values = values.where(np.isfinite(values))
    return finite_values.groupby(level="datetime", sort=False).rank(
        method="average", pct=True
    )


def _build_ranked_liquidity_features(data: pd.DataFrame) -> pd.DataFrame:
    close = data["$close"].astype("float64")
    volume = data["$volume"].astype("float64")

    close_valid = np.isfinite(close) & (close > 0.0)
    volume_nonnegative = np.isfinite(volume) & (volume >= 0.0)
    volume_positive = np.isfinite(volume) & (volume > 0.0)

    previous_close = _instrument_shift(close, 1)
    log_return_valid = (
        close_valid
        & np.isfinite(previous_close)
        & (previous_close > 0.0)
    )
    close_log_return = np.log(close.div(previous_close)).where(log_return_valid)
    close_log_return = close_log_return.where(np.isfinite(close_log_return))

    log_volume = np.log1p(volume).where(volume_nonnegative)
    prior_log_volume_mean = log_volume.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.shift(1).rolling(
            window=VOLUME_BASELINE_WINDOW,
            min_periods=VOLUME_BASELINE_WINDOW,
        ).mean()
    )
    volume_surprise = log_volume.sub(prior_log_volume_mean)
    volume_surprise = volume_surprise.where(np.isfinite(volume_surprise)).clip(
        lower=VOLUME_SURPRISE_LOWER_BOUND,
        upper=VOLUME_SURPRISE_UPPER_BOUND,
    )

    signed_volume_pressure = (
        np.sign(close_log_return).mul(volume_surprise)
    ).where(close_log_return.notna() & volume_surprise.notna())

    pressure_mean_5 = _instrument_rolling_mean(
        signed_volume_pressure, FEATURE_1_WINDOW
    )
    pressure_mean_20 = _instrument_rolling_mean(
        signed_volume_pressure, FEATURE_2_WINDOW
    )

    illiquidity_component = close_log_return.abs().div(close.mul(volume)).where(
        close_log_return.notna() & close_valid & volume_positive
    )
    illiquidity_component = illiquidity_component.where(
        np.isfinite(illiquidity_component)
    )
    illiquidity_mean_20 = _instrument_rolling_mean(
        illiquidity_component, FEATURE_3_WINDOW
    )

    negative_return_positive_volume_shock = close_log_return.mul(-1.0).mul(
        volume_surprise.clip(lower=0.0)
    )
    negative_return_positive_volume_shock = (
        negative_return_positive_volume_shock.where(
            close_log_return.notna() & volume_surprise.notna()
        )
    )

    raw_features = pd.DataFrame(
        {
            FEATURE_NAMES[0]: pressure_mean_5,
            FEATURE_NAMES[1]: pressure_mean_20,
            FEATURE_NAMES[2]: illiquidity_mean_20,
            FEATURE_NAMES[3]: negative_return_positive_volume_shock,
        },
        index=data.index,
        dtype="float64",
    )
    return _cross_sectional_percentile_rank(raw_features)


def _build_ranked_sota_factors(data: pd.DataFrame) -> pd.DataFrame:
    open_price = data["$open"].astype("float64")
    close = data["$close"].astype("float64")
    high = data["$high"].astype("float64")
    low = data["$low"].astype("float64")

    open_valid = np.isfinite(open_price) & (open_price > 0.0)
    close_valid = np.isfinite(close) & (close > 0.0)
    high_valid = np.isfinite(high) & (high > 0.0)
    low_valid = np.isfinite(low) & (low > 0.0)

    close_lag_1 = _instrument_shift(close, 1)
    close_lag_20 = _instrument_shift(close, 20)

    overnight_valid = (
        open_valid
        & np.isfinite(close_lag_1)
        & (close_lag_1 > 0.0)
    )
    overnight_gap = open_price.div(close_lag_1).sub(1.0).where(overnight_valid)

    high_low_range = high.sub(low)
    close_location_valid = (
        close_valid & high_valid & low_valid & (high > low)
    )
    close_location = (
        close.mul(2.0).sub(high).sub(low).div(high_low_range)
    ).where(close_location_valid)

    momentum_valid = (
        close_valid
        & np.isfinite(close_lag_20)
        & (close_lag_20 > 0.0)
    )
    close_momentum_20 = close.div(close_lag_20).sub(1.0).where(momentum_valid)

    raw_sota = pd.DataFrame(
        {
            SOTA_NAMES[0]: overnight_gap,
            SOTA_NAMES[1]: close_location,
            SOTA_NAMES[2]: close_momentum_20,
        },
        index=data.index,
        dtype="float64",
    )
    return _cross_sectional_percentile_rank(raw_sota)


def _build_forward_returns_and_endpoints(
    close: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    future_close = _instrument_shift(close, -PREDICTION_HORIZON)

    observation_dates = pd.Series(
        close.index.get_level_values("datetime").to_numpy(),
        index=close.index,
        dtype="datetime64[ns]",
    )
    endpoint_dates = _instrument_shift(
        observation_dates, -PREDICTION_HORIZON
    )

    return_valid = (
        np.isfinite(close)
        & (close != 0.0)
        & np.isfinite(future_close)
        & endpoint_dates.notna()
    )
    forward_return = future_close.div(close).sub(1.0).where(return_valid)
    forward_return = forward_return.where(np.isfinite(forward_return))
    endpoint_dates = endpoint_dates.where(forward_return.notna())
    return forward_return, endpoint_dates


def _calculate_residual_targets(
    forward_return: pd.Series,
    endpoint_session_positions: np.ndarray,
    ranked_sota: pd.DataFrame,
    row_session_positions: np.ndarray,
    training_start_position: int,
    refit_position: int,
) -> pd.Series:
    observable_mask = (
        (row_session_positions >= training_start_position)
        & (row_session_positions <= refit_position)
        & forward_return.notna().to_numpy()
        & (endpoint_session_positions >= 0)
        & (endpoint_session_positions <= refit_position)
    )

    observable_returns = forward_return.loc[observable_mask]
    ranked_forward_returns = _cross_sectional_percentile_rank(
        observable_returns
    )

    ols_data = ranked_sota.loc[
        ranked_forward_returns.index, SOTA_NAMES
    ].copy()
    ols_data["target"] = ranked_forward_returns
    complete_mask = np.isfinite(ols_data.to_numpy(dtype="float64")).all(axis=1)
    ols_data = ols_data.loc[complete_mask]

    residuals = pd.Series(np.nan, index=ranked_forward_returns.index, dtype="float64")
    for _, date_data in ols_data.groupby(level="datetime", sort=False):
        predictors = date_data[SOTA_NAMES].to_numpy(dtype="float64")
        target = date_data["target"].to_numpy(dtype="float64")
        design = np.column_stack(
            [np.ones(len(date_data), dtype="float64"), predictors]
        )
        coefficients = np.linalg.lstsq(design, target, rcond=None)[0]
        fitted = design @ coefficients
        residuals.loc[date_data.index] = target - fitted

    return residuals.where(np.isfinite(residuals))


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


def calculate_residual_liquidity_pressure_walkforward_5d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    ranked_features = _build_ranked_liquidity_features(data)
    ranked_sota = _build_ranked_sota_factors(data)

    close = data["$close"].astype("float64")
    forward_return, endpoint_dates = _build_forward_returns_and_endpoints(close)

    sessions = pd.Index(
        data.index.get_level_values("datetime").unique()
    ).sort_values()
    session_count = len(sessions)

    row_dates = data.index.get_level_values("datetime")
    row_session_positions = sessions.get_indexer(row_dates)
    endpoint_session_positions = sessions.get_indexer(
        pd.DatetimeIndex(endpoint_dates)
    )

    complete_sota = np.isfinite(
        ranked_sota[SOTA_NAMES].to_numpy(dtype="float64")
    ).all(axis=1)
    eligible_for_residual = (
        forward_return.notna().to_numpy()
        & (endpoint_session_positions >= 0)
        & complete_sota
    )

    minimum_endpoint_by_feature_session = np.full(
        session_count, np.inf, dtype="float64"
    )
    eligible_endpoint_series = pd.Series(
        endpoint_session_positions[eligible_for_residual],
        index=data.index[eligible_for_residual],
        dtype="int64",
    )
    minimum_endpoints = eligible_endpoint_series.groupby(
        level="datetime", sort=False
    ).min()
    minimum_endpoint_locations = sessions.get_indexer(minimum_endpoints.index)
    minimum_endpoint_by_feature_session[minimum_endpoint_locations] = (
        minimum_endpoints.to_numpy(dtype="float64")
    )

    anchor_position = None
    for refit_position in range(session_count):
        training_start_position = max(
            0, refit_position - TRAINING_WINDOW + 1
        )
        window_minimum_endpoints = minimum_endpoint_by_feature_session[
            training_start_position : refit_position + 1
        ]
        eligible_session_count = int(
            np.count_nonzero(window_minimum_endpoints <= refit_position)
        )
        if eligible_session_count >= MINIMUM_TRAINING_SESSIONS:
            anchor_position = refit_position
            break

    predictions = pd.Series(np.nan, index=data.index, dtype="float64")

    if anchor_position is not None:
        for refit_position in range(
            anchor_position, session_count, REFIT_FREQUENCY
        ):
            training_start_position = max(
                0, refit_position - TRAINING_WINDOW + 1
            )
            window_minimum_endpoints = minimum_endpoint_by_feature_session[
                training_start_position : refit_position + 1
            ]
            eligible_session_count = int(
                np.count_nonzero(window_minimum_endpoints <= refit_position)
            )
            if eligible_session_count < MINIMUM_TRAINING_SESSIONS:
                continue

            residual_targets = _calculate_residual_targets(
                forward_return=forward_return,
                endpoint_session_positions=endpoint_session_positions,
                ranked_sota=ranked_sota,
                row_session_positions=row_session_positions,
                training_start_position=training_start_position,
                refit_position=refit_position,
            )
            finite_target_mask = residual_targets.notna()
            training_index = residual_targets.index[finite_target_mask]

            x_train = ranked_features.loc[training_index, FEATURE_NAMES]
            y_train = residual_targets.loc[training_index]

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
    calculate_residual_liquidity_pressure_walkforward_5d()
