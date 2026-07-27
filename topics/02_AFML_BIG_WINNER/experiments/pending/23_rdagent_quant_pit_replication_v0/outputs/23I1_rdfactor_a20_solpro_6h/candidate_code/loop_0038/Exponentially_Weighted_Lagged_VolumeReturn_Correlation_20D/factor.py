from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Exponentially_Weighted_Lagged_VolumeReturn_Correlation_20D"
PAIR_COUNT = 20
SOURCE_WINDOW = 22
WEIGHT_HALF_LIFE = 10.0


def _calculate_instrument_factor(
    close_values: np.ndarray,
    volume_values: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    observation_count = close_values.size
    output = np.full(observation_count, np.nan, dtype=np.float64)

    if observation_count < SOURCE_WINDOW:
        return output

    valid_close = np.isfinite(close_values) & (close_values > 0.0)
    valid_volume = np.isfinite(volume_values) & (volume_values > 0.0)
    valid_source = valid_close & valid_volume

    log_close = np.full(observation_count, np.nan, dtype=np.float64)
    log_volume = np.full(observation_count, np.nan, dtype=np.float64)
    log_close[valid_close] = np.log(close_values[valid_close])
    log_volume[valid_volume] = np.log(volume_values[valid_volume])

    close_windows = np.lib.stride_tricks.sliding_window_view(
        log_close, SOURCE_WINDOW
    )
    volume_windows = np.lib.stride_tricks.sliding_window_view(
        log_volume, SOURCE_WINDOW
    )
    validity_windows = np.lib.stride_tricks.sliding_window_view(
        valid_source, SOURCE_WINDOW
    )

    complete_windows = validity_windows.all(axis=1)
    complete_positions = np.flatnonzero(complete_windows)

    if complete_positions.size == 0:
        return output

    selected_close = close_windows[complete_positions]
    selected_volume = volume_windows[complete_positions]

    # Columns are ordered from the oldest pair (lag 19) to the newest
    # pair (lag 0), matching the ordering of weights.
    close_returns = selected_close[:, 2:] - selected_close[:, 1:-1]
    lagged_volume_changes = selected_volume[:, 1:-1] - selected_volume[:, :-2]

    finite_pairs = (
        np.isfinite(close_returns).all(axis=1)
        & np.isfinite(lagged_volume_changes).all(axis=1)
    )

    weighted_mean_return = np.sum(close_returns * weights, axis=1)
    weighted_mean_volume = np.sum(lagged_volume_changes * weights, axis=1)

    centered_returns = close_returns - weighted_mean_return[:, None]
    centered_volume = lagged_volume_changes - weighted_mean_volume[:, None]

    return_variance = np.sum(weights * centered_returns**2, axis=1)
    volume_variance = np.sum(weights * centered_volume**2, axis=1)

    # Ensure mathematically constant input series have exactly zero variance.
    return_constant = np.ptp(close_returns, axis=1) == 0.0
    volume_constant = np.ptp(lagged_volume_changes, axis=1) == 0.0
    return_variance[return_constant] = 0.0
    volume_variance[volume_constant] = 0.0

    return_std = np.sqrt(return_variance)
    volume_std = np.sqrt(volume_variance)
    covariance = np.sum(
        weights * centered_volume * centered_returns,
        axis=1,
    )
    denominator = volume_std * return_std

    valid_moments = (
        finite_pairs
        & np.isfinite(weighted_mean_return)
        & np.isfinite(weighted_mean_volume)
        & np.isfinite(return_variance)
        & np.isfinite(volume_variance)
        & np.isfinite(return_std)
        & np.isfinite(volume_std)
        & (return_std > 0.0)
        & (volume_std > 0.0)
        & np.isfinite(covariance)
        & np.isfinite(denominator)
        & (denominator > 0.0)
    )

    correlations = np.full(complete_positions.size, np.nan, dtype=np.float64)
    correlations[valid_moments] = (
        covariance[valid_moments] / denominator[valid_moments]
    )
    correlations[~np.isfinite(correlations)] = np.nan

    output_positions = complete_positions + SOURCE_WINDOW - 1
    output[output_positions] = correlations
    return output


def calculate_exponentially_weighted_lagged_volume_return_correlation_20d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])

    close_values = data["$close"].to_numpy(dtype=np.float64, copy=True)
    volume_values = data["$volume"].to_numpy(dtype=np.float64, copy=True)

    # Rolling pair arrays are oldest-to-newest, corresponding to lags 19 to 0.
    pair_lags = np.arange(PAIR_COUNT - 1, -1, -1, dtype=np.float64)
    unnormalized_weights = np.power(2.0, -pair_lags / WEIGHT_HALF_LIFE)
    weights = unnormalized_weights / np.sum(unnormalized_weights)

    factor_values = np.full(len(data), np.nan, dtype=np.float64)
    grouped_positions = data.groupby(
        level="instrument", sort=False
    ).indices

    for positions in grouped_positions.values():
        positions = np.sort(np.asarray(positions, dtype=np.int64))
        factor_values[positions] = _calculate_instrument_factor(
            close_values[positions],
            volume_values[positions],
            weights,
        )

    result = pd.DataFrame(
        {FACTOR_NAME: factor_values},
        index=data.index,
    )
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_exponentially_weighted_lagged_volume_return_correlation_20d()
