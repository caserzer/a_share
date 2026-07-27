from pathlib import Path

import numpy as np
import pandas as pd

FACTOR_NAME = "Smoothed_Lagged_VolumeReturn_Correlation_20D_5D"
CORRELATION_WINDOW = 20
SMOOTHING_WINDOW = 5
SOURCE_WINDOW = 26
SMOOTHING_WEIGHTS_CHRONOLOGICAL = np.array(
    [0.08, 0.12, 0.15, 0.25, 0.40], dtype=np.float64
)


def _calculate_instrument_factor(group: pd.DataFrame) -> np.ndarray:
    close = group["$close"].to_numpy(dtype=np.float64, copy=True)
    volume = group["$volume"].to_numpy(dtype=np.float64, copy=True)
    observation_count = len(group)

    factor_values = np.full(observation_count, np.nan, dtype=np.float64)
    if observation_count < SOURCE_WINDOW:
        return factor_values

    valid_close = np.isfinite(close) & (close > 0.0)
    valid_volume = np.isfinite(volume) & (volume > 0.0)
    valid_source = valid_close & valid_volume

    close_returns = np.full(observation_count, np.nan, dtype=np.float64)
    return_source_valid = valid_close[1:] & valid_close[:-1]
    return_positions = np.flatnonzero(return_source_valid) + 1
    close_returns[return_positions] = np.log(
        close[1:][return_source_valid] / close[:-1][return_source_valid]
    )

    lagged_volume_changes = np.full(observation_count, np.nan, dtype=np.float64)
    volume_change_source_valid = valid_volume[1:-1] & valid_volume[:-2]
    volume_change_positions = np.flatnonzero(volume_change_source_valid) + 2
    lagged_volume_changes[volume_change_positions] = np.log(
        volume[1:-1][volume_change_source_valid]
        / volume[:-2][volume_change_source_valid]
    )

    volume_windows = np.lib.stride_tricks.sliding_window_view(
        lagged_volume_changes, CORRELATION_WINDOW
    )
    return_windows = np.lib.stride_tricks.sliding_window_view(
        close_returns, CORRELATION_WINDOW
    )

    valid_pair_windows = (
        np.isfinite(volume_windows).all(axis=1)
        & np.isfinite(return_windows).all(axis=1)
    )

    correlations = np.full(observation_count, np.nan, dtype=np.float64)
    valid_window_starts = np.flatnonzero(valid_pair_windows)

    if valid_window_starts.size > 0:
        valid_volume_windows = volume_windows[valid_window_starts]
        valid_return_windows = return_windows[valid_window_starts]

        mean_volume_change = valid_volume_windows.mean(axis=1)
        mean_return = valid_return_windows.mean(axis=1)

        centered_volume = valid_volume_windows - mean_volume_change[:, None]
        centered_return = valid_return_windows - mean_return[:, None]

        volume_variance = np.mean(centered_volume * centered_volume, axis=1)
        return_variance = np.mean(centered_return * centered_return, axis=1)
        covariance = np.mean(centered_volume * centered_return, axis=1)

        volume_std = np.sqrt(volume_variance)
        return_std = np.sqrt(return_variance)
        denominator = volume_std * return_std

        valid_moments = (
            np.isfinite(volume_std)
            & (volume_std > 0.0)
            & np.isfinite(return_std)
            & (return_std > 0.0)
            & np.isfinite(covariance)
            & np.isfinite(denominator)
            & (denominator > 0.0)
        )

        component_values = np.full(valid_window_starts.size, np.nan, dtype=np.float64)
        component_values[valid_moments] = (
            covariance[valid_moments] / denominator[valid_moments]
        )
        component_values[~np.isfinite(component_values)] = np.nan

        correlation_endpoints = valid_window_starts + CORRELATION_WINDOW - 1
        correlations[correlation_endpoints] = component_values

    correlation_smoothing_windows = np.lib.stride_tricks.sliding_window_view(
        correlations, SMOOTHING_WINDOW
    )
    all_components_valid = np.isfinite(correlation_smoothing_windows).all(axis=1)

    smoothed_values = np.full(
        correlation_smoothing_windows.shape[0], np.nan, dtype=np.float64
    )
    smoothed_values[all_components_valid] = (
        correlation_smoothing_windows[all_components_valid]
        @ SMOOTHING_WEIGHTS_CHRONOLOGICAL
    )

    complete_source_windows = np.lib.stride_tricks.sliding_window_view(
        valid_source, SOURCE_WINDOW
    ).all(axis=1)

    source_complete_by_endpoint = np.zeros(observation_count, dtype=bool)
    source_complete_by_endpoint[SOURCE_WINDOW - 1 :] = complete_source_windows

    smoothing_endpoints = np.arange(
        SMOOTHING_WINDOW - 1, observation_count, dtype=np.int64
    )
    valid_outputs = (
        all_components_valid
        & source_complete_by_endpoint[smoothing_endpoints]
        & np.isfinite(smoothed_values)
    )
    factor_values[smoothing_endpoints[valid_outputs]] = smoothed_values[valid_outputs]

    return factor_values


def calculate_smoothed_lagged_volume_return_correlation_20d_5d() -> pd.DataFrame:
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "daily_pv.h5"
    output_path = base_path / "result.h5"

    data = pd.read_hdf(data_path, key="data").sort_index()
    data.index = data.index.set_names(["datetime", "instrument"])
    data = data[["$close", "$volume"]]

    factor = pd.Series(np.nan, index=data.index, dtype=np.float64)

    for _, group in data.groupby(level="instrument", sort=False):
        instrument_values = _calculate_instrument_factor(group)
        factor.loc[group.index] = instrument_values

    factor = factor.where(np.isfinite(factor))
    result = factor.to_frame(name=FACTOR_NAME)
    result.index = result.index.set_names(["datetime", "instrument"])
    result.to_hdf(output_path, key="data", mode="w")
    return result


if __name__ == "__main__":
    calculate_smoothed_lagged_volume_return_correlation_20d_5d()
