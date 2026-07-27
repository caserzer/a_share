from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

FACTOR_NAME = "ML_OHLCV_WalkForward_5D"
FEATURE_NAMES = [
    "Overnight_Gap_1D",
    "Close_Location_Value_1D",
    "Close_Momentum_20D",
    "Intraday_Return_1D",
    "Close_Momentum_5D",
    "Log_High_Low_Range_1D",
    "Volume_Surprise_20D",
    "Realized_Close_Volatility_20D",
    "Lower_Wick_Fraction_1D",
    "Upper_Wick_Fraction_1D",
]

PREDICTION_HORIZON = 5
TRAINING_WINDOW = 504
MINIMUM_TRAINING_SESSIONS = 252
REFIT_FREQUENCY = 20
VOLUME_LOOKBACK = 20
VOLATILITY_LOOKBACK = 20


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
    volume = data["$volume"].astype("float64")

    open_valid = np.isfinite(open_price) & (open_price > 0.0)
    close_valid = np.isfinite(close) & (close > 0.0)
    high_valid = np.isfinite(high) & (high > 0.0)
    low_valid = np.isfinite(low) & (low > 0.0)
    volume_valid = np.isfinite(volume) & (volume >= 0.0)

    close_lag_1 = _instrument_shift(close, 1)
    close_lag_5 = _instrument_shift(close, 5)
    close_lag_20 = _instrument_shift(close, 20)

    overnight_valid = (
        open_valid & np.isfinite(close_lag_1) & (close_lag_1 > 0.0)
    )
    overnight_gap = open_price.div(close_lag_1).sub(1.0).where(overnight_valid)

    high_low_range = high.sub(low)
    range_valid = high_valid & low_valid & close_valid & (high > low)
    close_location = (
        close.mul(2.0).sub(high).sub(low).div(high_low_range).where(range_valid)
    )

    momentum_20_valid = (
        close_valid & np.isfinite(close_lag_20) & (close_lag_20 > 0.0)
    )
    close_momentum_20 = (
        close.div(close_lag_20).sub(1.0).where(momentum_20_valid)
    )

    intraday_valid = open_valid & close_valid
    intraday_return = close.div(open_price).sub(1.0).where(intraday_valid)

    momentum_5_valid = (
        close_valid & np.isfinite(close_lag_5) & (close_lag_5 > 0.0)
    )
    close_momentum_5 = close.div(close_lag_5).sub(1.0).where(momentum_5_valid)

    log_high_low_range = np.log(high.div(low)).where(
        high_valid & low_valid & (high > low)
    )

    log_volume = np.log1p(volume).where(volume_valid)
    prior_volume_mean = log_volume.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.shift(1).rolling(
            window=VOLUME_LOOKBACK,
            min_periods=VOLUME_LOOKBACK,
        ).mean()
    )
    volume_surprise = log_volume.sub(prior_volume_mean)

    previous_close = _instrument_shift(close, 1)
    log_return_valid = (
        close_valid & np.isfinite(previous_close) & (previous_close > 0.0)
    )
    close_log_return = np.log(close.div(previous_close)).where(log_return_valid)
    realized_volatility = close_log_return.groupby(
        level="instrument", sort=False, group_keys=False
    ).transform(
        lambda values: values.rolling(
            window=VOLATILITY_LOOKBACK,
            min_periods=VOLATILITY_LOOKBACK,
        ).std(ddof=0)
    )

    wick_valid = open_valid & close_valid & high_valid & low_valid & (high > low)
    lower_wick = (
        pd.concat([open_price, close], axis=1)
        .min(axis=1)
        .sub(low)
        .div(high_low_range)
        .where(wick_valid)
    )
    upper_wick = (
        high.sub(pd.concat([open_price, close], axis=1).max(axis=1))
        .div(high_low_range)
        .where(wick_valid)
    )

    raw_features = pd.DataFrame(
        {
            FEATURE_NAMES[0]: overnight_gap,
            FEATURE_NAMES[1]: close_location,
            FEATURE_NAMES[2]: close_momentum_20,
            FEATURE_NAMES[3]: intraday_return,
            FEATURE_NAMES[4]: close_momentum_5,
            FEATURE_NAMES[5]: log_high_low_range,
            FEATURE_NAMES[6]: volume_surprise,
            FEATURE_NAMES[7]: realized_volatility,
            FEATURE_NAMES[8]: lower_wick,
            FEATURE_NAMES[9]: upper_wick,
        },
        index=data.index,
        dtype="float64",
    )
    return _cross_sectional_percentile_rank(raw_features)


def _build_forward_returns_and_endpoints(
    close: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    future_close = _instrument_shift(close, -PREDICTION_HORIZON)

    observation_dates = pd.Series(
        close.index.get_level_values("datetime"),
        index=close.index,
        dtype="datetime64[ns]",
    )
    endpoint_dates = _instrument_shift(observation_dates, -PREDICTION_HORIZON)

    target_valid = (
        np.isfinite(close)
        & (close > 0.0)
        & np.isfinite(future_close)
        & (future_close > 0.0)
        & endpoint_dates.notna()
    )
    forward_return = future_close.div(close).sub(1.0).where(target_valid)
    forward_return = forward_return.where(np.isfinite(forward_return))
    endpoint_dates = endpoint_dates.where(forward_return.notna())
    return forward_return, endpoint_dates


def _make_model() -> LGBMRegressor:
    return LGBMRegressor(
        objective="regression_l1",
        learning_rate=0.03,
        n_estimators=200,
        num_leaves=7,
        max_depth=3,
        min_child_samples=200,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )


def calculate_ml_ohlcv_walkforward_5d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    ranked_features = _build_ranked_features(data)
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
    valid_target = (
        forward_return.notna().to_numpy()
        & (endpoint_session_positions >= 0)
    )

    minimum_endpoint_by_feature_session = np.full(
        session_count, np.inf, dtype="float64"
    )
    valid_endpoint_positions = pd.Series(
        endpoint_session_positions[valid_target],
        index=data.index[valid_target],
        dtype="int64",
    )
    minimum_endpoints = valid_endpoint_positions.groupby(
        level="datetime", sort=False
    ).min()
    minimum_endpoint_locations = sessions.get_indexer(minimum_endpoints.index)
    minimum_endpoint_by_feature_session[minimum_endpoint_locations] = (
        minimum_endpoints.to_numpy(dtype="float64")
    )

    anchor_position = None
    for refit_position in range(PREDICTION_HORIZON, session_count):
        training_end_position = refit_position - PREDICTION_HORIZON
        training_start_position = max(
            0, training_end_position - TRAINING_WINDOW + 1
        )
        window_minimum_endpoints = minimum_endpoint_by_feature_session[
            training_start_position : training_end_position + 1
        ]
        eligible_count = int(
            np.count_nonzero(window_minimum_endpoints <= refit_position)
        )
        if eligible_count >= MINIMUM_TRAINING_SESSIONS:
            anchor_position = refit_position
            break

    predictions = pd.Series(np.nan, index=data.index, dtype="float64")

    if anchor_position is not None:
        for refit_position in range(
            anchor_position, session_count, REFIT_FREQUENCY
        ):
            training_end_position = refit_position - PREDICTION_HORIZON
            training_start_position = max(
                0, training_end_position - TRAINING_WINDOW + 1
            )

            window_minimum_endpoints = minimum_endpoint_by_feature_session[
                training_start_position : training_end_position + 1
            ]
            eligible_count = int(
                np.count_nonzero(window_minimum_endpoints <= refit_position)
            )
            if eligible_count < MINIMUM_TRAINING_SESSIONS:
                continue

            training_mask = (
                (row_session_positions >= training_start_position)
                & (row_session_positions <= training_end_position)
                & valid_target
                & (endpoint_session_positions <= refit_position)
            )

            eligible_forward_returns = forward_return.loc[training_mask]
            ranked_target = _cross_sectional_percentile_rank(
                eligible_forward_returns
            )
            finite_rank_mask = ranked_target.notna().to_numpy()

            training_index = eligible_forward_returns.index[finite_rank_mask]
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
    calculate_ml_ohlcv_walkforward_5d()
