from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRanker

FACTOR_NAME = "PriceStructure_LambdaRank_1D"
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
LABEL_COUNT = 5


def _instrument_shift(series: pd.Series, periods: int) -> pd.Series:
    return series.groupby(level="instrument", sort=False).shift(periods)


def _cross_sectional_percentile_rank(
    values: pd.DataFrame | pd.Series,
) -> pd.DataFrame | pd.Series:
    finite_values = values.where(np.isfinite(values))
    return finite_values.groupby(level="datetime", sort=False).rank(
        method="average",
        pct=True,
        ascending=True,
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
        open_valid
        & np.isfinite(close_lag_1)
        & (close_lag_1 > 0.0)
    )
    overnight_gap = (
        open_price.div(close_lag_1).sub(1.0).where(overnight_valid)
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

    next_dates = np.full(
        len(close),
        np.datetime64("NaT"),
        dtype="datetime64[ns]",
    )
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
    future_close_values = close.reindex(endpoint_index).to_numpy(
        dtype="float64"
    )
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


def _build_ordinal_labels(forward_return: pd.Series) -> pd.Series:
    return_percentile = _cross_sectional_percentile_rank(forward_return)
    percentile_values = return_percentile.to_numpy(dtype="float64")
    finite_mask = np.isfinite(percentile_values)

    label_values = np.full(len(return_percentile), np.nan, dtype="float64")
    label_values[finite_mask] = np.minimum(
        LABEL_COUNT - 1,
        np.ceil(LABEL_COUNT * percentile_values[finite_mask]) - 1.0,
    )
    return pd.Series(
        label_values,
        index=return_percentile.index,
        dtype="float64",
    )


def _make_model() -> LGBMRanker:
    return LGBMRanker(
        objective="lambdarank",
        label_gain=[0, 1, 2, 3, 4],
        learning_rate=0.03,
        n_estimators=100,
        num_leaves=7,
        max_depth=3,
        min_child_samples=200,
        subsample=1.0,
        colsample_bytree=1.0,
        reg_alpha=0.2,
        reg_lambda=2.0,
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )


def calculate_pricestructure_lambdarank_1d() -> pd.DataFrame:
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
    ordinal_labels = _build_ordinal_labels(forward_return)

    row_dates = data.index.get_level_values("datetime")
    row_session_positions = sessions.get_indexer(row_dates)

    feature_values = ranked_features[FEATURE_NAMES].to_numpy(dtype="float64")
    label_values = ordinal_labels.to_numpy(dtype="float64")
    complete_feature_mask = np.isfinite(feature_values).all(axis=1)
    finite_label_mask = np.isfinite(label_values)
    retained_training_row_mask = complete_feature_mask & finite_label_mask

    retained_session_flags = np.zeros(session_count, dtype=bool)
    retained_positions = row_session_positions[retained_training_row_mask]
    if retained_positions.size > 0:
        retained_session_flags[np.unique(retained_positions)] = True

    anchor_position = None
    for refit_position in range(PREDICTION_HORIZON, session_count):
        training_start_position = max(
            0,
            refit_position - TRAINING_WINDOW,
        )
        eligible_session_count = int(
            np.count_nonzero(
                retained_session_flags[
                    training_start_position:refit_position
                ]
            )
        )
        if eligible_session_count >= MINIMUM_TRAINING_SESSIONS:
            anchor_position = refit_position
            break

    raw_predictions = pd.Series(np.nan, index=data.index, dtype="float64")

    if anchor_position is not None:
        fitted_model = None

        for block_start in range(
            anchor_position,
            session_count,
            REFIT_FREQUENCY,
        ):
            training_start_position = max(
                0,
                block_start - TRAINING_WINDOW,
            )
            training_mask = (
                (row_session_positions >= training_start_position)
                & (row_session_positions < block_start)
                & retained_training_row_mask
            )

            training_positions = row_session_positions[training_mask]
            distinct_training_positions, group_sizes = np.unique(
                training_positions,
                return_counts=True,
            )

            if (
                len(distinct_training_positions)
                >= MINIMUM_TRAINING_SESSIONS
            ):
                x_train = feature_values[training_mask]
                y_train = label_values[training_mask].astype("int32")

                fitted_model = _make_model()
                fitted_model.fit(
                    x_train,
                    y_train,
                    group=group_sizes.astype("int32").tolist(),
                )

            if fitted_model is None:
                continue

            block_end = min(
                block_start + REFIT_FREQUENCY,
                session_count,
            )
            prediction_mask = (
                (row_session_positions >= block_start)
                & (row_session_positions < block_end)
                & complete_feature_mask
            )

            if np.any(prediction_mask):
                raw_predictions.iloc[np.flatnonzero(prediction_mask)] = (
                    fitted_model.predict(feature_values[prediction_mask])
                )

    ranked_predictions = _cross_sectional_percentile_rank(raw_predictions)
    result = ranked_predictions.to_frame(name=FACTOR_NAME).astype("float64")
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_pricestructure_lambdarank_1d()
